"""Streaming reader for public DFL/Sportec tracking XML.

Positions and label arrays are separate types. Keep `ExternalLabels` out of every feature
transform; only `ExternalFeatures` is accepted by feature code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import math
import xml.etree.ElementTree as ET

import numpy as np
from lxml import etree


HOME = 0
AWAY = 1
UNKNOWN = -1
DEAD = 0
ALIVE = 1
HOME_OWNER = 0
AWAY_OWNER = 1
DEAD_TARGET = 2

PERIOD_BY_SECTION = {
    "firstHalf": 1,
    "secondHalf": 2,
    "firstHalfExtra": 3,
    "secondHalfExtra": 4,
}


@dataclass(frozen=True)
class ExternalFeatures:
    """Observable tracking only; no ball-state or owner labels are carried here."""

    period_id: int
    frame_ids: np.ndarray
    player_ids: tuple[str, ...]  # match-information roster order, used only for deterministic tie handling
    team_by_player: np.ndarray
    player_xy: np.ndarray  # shape: [frame, player, (x, y)] in metres; NaN means missing
    ball_xy: np.ndarray  # shape: [frame, (x, y)] in metres; NaN means missing


@dataclass(frozen=True)
class ExternalLabels:
    """Ball status and possession owner, stored away from all model features."""

    period_id: int
    frame_ids: np.ndarray
    ball_status: np.ndarray  # -1 unknown, 0 inactive/dead, 1 active/alive
    ball_owner: np.ndarray  # -1 unknown, 0 home, 1 away

    def possession_targets(self) -> np.ndarray:
        """Map valid labels to H/A/D codes; unsupported frames remain -1."""
        target = np.full(len(self.frame_ids), UNKNOWN, dtype=np.int8)
        target[self.ball_status == DEAD] = DEAD_TARGET
        live_and_owned = (self.ball_status == ALIVE) & (self.ball_owner >= 0)
        target[live_and_owned] = self.ball_owner[live_and_owned]
        return target


@dataclass(frozen=True)
class ExternalMatch:
    """Aligned periods; features and labels are parallel, separately typed tuples."""

    features: tuple[ExternalFeatures, ...]
    labels: tuple[ExternalLabels, ...]
    period_bounds: tuple[tuple[int, int, int], ...]  # (period, first_frame, stop_frame)


@dataclass
class _PeriodBounds:
    low: int
    high: int
    player_ids: set[str]


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_tracking_xml(tracking_path: str | Path):
    """Parse local XML without entity resolution or network access."""
    return etree.iterparse(
        str(tracking_path),
        events=("start", "end"),
        huge_tree=True,
        resolve_entities=False,
        no_network=True,
    )


def _clear_and_prune(elem) -> None:
    """Clear a finished lxml node and drop its prior siblings to bound tree memory."""
    elem.clear()
    parent = elem.getparent()
    if parent is not None:
        while elem.getprevious() is not None:
            del parent[0]


def read_sportec_team_map(metadata_path: str | Path) -> dict[str, int]:
    """Read PersonId -> {0 home, 1 guest/away} from a Sportec match-information XML."""
    team_map: dict[str, int] = {}
    current_side: int | None = None
    saw_home = saw_away = False
    for event, elem in ET.iterparse(str(metadata_path), events=("start", "end")):
        tag = _local_tag(elem.tag)
        if event == "start" and tag == "Team":
            role = elem.get("Role")
            if role == "home":
                current_side = HOME
                saw_home = True
            elif role == "guest":
                current_side = AWAY
                saw_away = True
            else:
                current_side = None
        elif event == "end" and tag == "Player" and current_side is not None:
            person_id = elem.get("PersonId")
            if not person_id:
                raise ValueError("player metadata lacks PersonId")
            prior = team_map.get(person_id)
            if prior is not None and prior != current_side:
                raise ValueError("PersonId appears under conflicting teams")
            team_map[person_id] = current_side
        elif event == "end" and tag == "Team":
            current_side = None
            elem.clear()
    if not (saw_home and saw_away) or not team_map:
        raise ValueError("metadata must identify home and guest teams with players")
    return team_map


def _period_for(section: str | None) -> int:
    try:
        return PERIOD_BY_SECTION[section or ""]
    except KeyError as exc:
        raise ValueError("unknown or missing Sportec GameSection") from exc


def _object_for_frameset(elem: ET.Element) -> str:
    if elem.get("TeamId") == "BALL":
        return "ball"
    person_id = elem.get("PersonId")
    if not person_id:
        raise ValueError("frameset lacks ball or PersonId")
    return person_id


def _scan_bounds(tracking_path: str | Path, team_by_player: Mapping[str, int]):
    bounds: dict[int, _PeriodBounds] = {}
    period: int | None = None
    object_id: str | None = None
    keep_object = False
    for event, elem in _iter_tracking_xml(tracking_path):
        tag = _local_tag(elem.tag)
        if event == "start" and tag == "FrameSet":
            period = _period_for(elem.get("GameSection"))
            object_id = _object_for_frameset(elem)
            keep_object = object_id == "ball" or object_id in team_by_player
        elif event == "start" and tag == "Frame" and period is not None and keep_object:
            raw_frame = elem.get("N")
            if raw_frame is None:
                raise ValueError("frame lacks N")
            frame_id = int(raw_frame)
            period_bounds = bounds.get(period)
            if period_bounds is None:
                period_bounds = _PeriodBounds(frame_id, frame_id, set())
                bounds[period] = period_bounds
            period_bounds.low = min(period_bounds.low, frame_id)
            period_bounds.high = max(period_bounds.high, frame_id)
            if object_id != "ball":
                period_bounds.player_ids.add(object_id)
        elif event == "end" and tag == "FrameSet":
            period = None
            object_id = None
            keep_object = False
            _clear_and_prune(elem)
        elif event == "end" and tag == "Frame":
            _clear_and_prune(elem)
    if not bounds:
        raise ValueError("no supported Sportec frames found")
    return bounds


def _xy(attrs: Mapping[str, str]) -> tuple[float, float]:
    x, y = attrs.get("X"), attrs.get("Y")
    if x is None or y is None or x == "" or y == "":
        return math.nan, math.nan
    try:
        values = float(x), float(y)
    except ValueError as exc:
        raise ValueError("invalid coordinate") from exc
    if not all(math.isfinite(value) for value in values):
        return math.nan, math.nan
    return values


def _coded_value(raw: str | None, table: Mapping[str, int], name: str) -> int:
    if raw is None or raw == "":
        return UNKNOWN
    try:
        return table[raw]
    except KeyError as exc:
        raise ValueError(f"unsupported {name} code") from exc


def _parse_ball_labels(attrs: Mapping[str, str]) -> tuple[int, int]:
    status = _coded_value(attrs.get("BallStatus"), {"0": DEAD, "1": ALIVE}, "BallStatus")
    owner = _coded_value(attrs.get("BallPossession"), {"1": HOME_OWNER, "2": AWAY_OWNER}, "BallPossession")
    return status, owner


def load_sportec_match(
    tracking_path: str | Path,
    team_by_player: Mapping[str, int],
    *,
    max_frames_per_period: int | None = None,
) -> ExternalMatch:
    """Read a local Sportec position XML in two streaming passes.

    `max_frames_per_period` is for bounded parser smoke tests only; it truncates each period to
    its lowest frame-id prefix. Production callers should omit it. Frame gaps become NaNs/unknown.
    Unknown tracked PersonIds are skipped as non-player objects; known roster IDs are preserved.
    """
    if max_frames_per_period is not None and max_frames_per_period < 1:
        raise ValueError("max_frames_per_period must be positive")
    normalized_team_map = {str(person): int(side) for person, side in team_by_player.items()}
    if any(side not in (HOME, AWAY) for side in normalized_team_map.values()):
        raise ValueError("team map values must be home=0 or away=1")
    bounds = _scan_bounds(tracking_path, normalized_team_map)

    storage: dict[int, dict[str, object]] = {}
    for period_id, info in bounds.items():
        stop = info.high + 1
        if max_frames_per_period is not None:
            stop = min(stop, info.low + max_frames_per_period)
        n_frames = stop - info.low
        # Keep match-information roster order as the stable source track order. The nearest-player
        # reference uses that order to resolve exact cross-team distance ties like the starter.
        player_ids = tuple(person_id for person_id in normalized_team_map
                           if person_id in info.player_ids)
        storage[period_id] = {
            "low": info.low,
            "stop": stop,
            "player_ids": player_ids,
            "player_index": {player_id: index for index, player_id in enumerate(player_ids)},
            # Preserve source coordinate precision for the nearest-player reference.
            "player_xy": np.full((n_frames, len(player_ids), 2), np.nan, dtype=np.float64),
            "ball_xy": np.full((n_frames, 2), np.nan, dtype=np.float64),
            "ball_status": np.full(n_frames, UNKNOWN, dtype=np.int8),
            "ball_owner": np.full(n_frames, UNKNOWN, dtype=np.int8),
            "seen_player": np.zeros((n_frames, len(player_ids)), dtype=np.bool_),
            "seen_ball": np.zeros(n_frames, dtype=np.bool_),
        }

    period = None
    object_id = None
    keep_object = False
    for event, elem in _iter_tracking_xml(tracking_path):
        tag = _local_tag(elem.tag)
        if event == "start" and tag == "FrameSet":
            period = _period_for(elem.get("GameSection"))
            object_id = _object_for_frameset(elem)
            keep_object = period in storage and (object_id == "ball" or object_id in storage[period]["player_index"])
        elif event == "start" and tag == "Frame" and period is not None and keep_object:
            row = elem.attrib
            if "N" not in row:
                raise ValueError("frame lacks N")
            frame_id = int(row["N"])
            destination = storage[period]
            low, stop = int(destination["low"]), int(destination["stop"])
            if not low <= frame_id < stop:
                continue
            index = frame_id - low
            if object_id == "ball":
                if destination["seen_ball"][index]:
                    raise ValueError("duplicate ball observation for period/frame")
                destination["seen_ball"][index] = True
                destination["ball_xy"][index] = _xy(row)
                status, owner = _parse_ball_labels(row)
                destination["ball_status"][index] = status
                destination["ball_owner"][index] = owner
            else:
                player_index = destination["player_index"][object_id]
                if destination["seen_player"][index, player_index]:
                    raise ValueError("duplicate player observation for period/frame")
                destination["seen_player"][index, player_index] = True
                destination["player_xy"][index, player_index] = _xy(row)
        elif event == "end" and tag == "FrameSet":
            period = None
            object_id = None
            keep_object = False
            _clear_and_prune(elem)
        elif event == "end" and tag == "Frame":
            _clear_and_prune(elem)

    features: list[ExternalFeatures] = []
    labels: list[ExternalLabels] = []
    period_bounds: list[tuple[int, int, int]] = []
    for period_id, destination in sorted(storage.items()):
        frame_ids = np.arange(int(destination["low"]), int(destination["stop"]), dtype=np.int32)
        # Separate copies make it explicit that labels are not part of feature input state.
        feature_frames = frame_ids.copy()
        label_frames = frame_ids.copy()
        player_ids = destination["player_ids"]
        features.append(ExternalFeatures(
            period_id=period_id,
            frame_ids=feature_frames,
            player_ids=player_ids,
            team_by_player=np.asarray([normalized_team_map[player_id] for player_id in player_ids], dtype=np.int8),
            player_xy=destination["player_xy"],
            ball_xy=destination["ball_xy"],
        ))
        labels.append(ExternalLabels(
            period_id=period_id,
            frame_ids=label_frames,
            ball_status=destination["ball_status"],
            ball_owner=destination["ball_owner"],
        ))
        period_bounds.append((period_id, int(frame_ids[0]), int(frame_ids[-1]) + 1))
    return ExternalMatch(tuple(features), tuple(labels), tuple(period_bounds))
