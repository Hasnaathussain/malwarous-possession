"""Bounded-memory ingestion of the organizer's Metrica FIFA/EPTS tracking export."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


FIELD_SEP = ":"
GROUP_SEP = ";"


@dataclass(frozen=True)
class MetricaTracking:
    """Frame-aligned metric tracking arrays; all coordinates are in metres."""

    frame: np.ndarray  # 0-based video frame indices
    team_by_slot: np.ndarray  # 0 home, 1 away
    player_xy: np.ndarray  # [frame, slot, xy], NaN where unobserved
    player_speed: np.ndarray  # [frame, slot], m/s; NaN where unavailable
    ball_xy: np.ndarray  # [frame, xy], NaN where unobserved
    ball_speed: np.ndarray  # [frame], m/s; NaN where unavailable


def team_slots_from_metadata(meta_path: str | Path) -> np.ndarray:
    """Map track slots to home=0/away=1 in metadata order, without using player identity."""
    root = ET.parse(str(meta_path)).getroot()
    team_ids = [team.get("id") for team in root.iter("Team")]
    if len(team_ids) != 2 or any(team_id is None for team_id in team_ids) or team_ids[0] == team_ids[1]:
        raise ValueError("invalid team metadata")
    slot_team_ids = [player.get("teamId") for player in root.iter("Player")]
    if not slot_team_ids or any(team_id not in team_ids for team_id in slot_team_ids):
        raise ValueError("invalid track-slot team mapping")
    return np.asarray([0 if team_id == team_ids[0] else 1 for team_id in slot_team_ids], dtype=np.int8)


def _number(text: str) -> float:
    try:
        value = float(text)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid tracking number") from exc
    return value if math.isfinite(value) else math.nan


def _group(text: str, pitch_length: float, pitch_width: float) -> tuple[float, float, float]:
    fields = text.split(",")
    if len(fields) != 3:
        raise ValueError("tracking group must contain x, y and speed")
    x, y, speed = (_number(value) for value in fields)
    if not (math.isfinite(x) and math.isfinite(y)):
        x = y = math.nan
    else:
        x *= pitch_length
        y *= pitch_width
    if math.isfinite(speed) and speed < 0:
        speed = math.nan
    return x, y, speed


def load_metrica_tracking(
    raw_path: str | Path,
    team_by_slot: np.ndarray,
    *,
    n_frames: int,
    pitch: tuple[float, float],
) -> MetricaTracking:
    """Stream raw Metrica ATD and require exactly one ordered record per video frame."""
    try:
        raw_teams = np.asarray(team_by_slot)
        valid_teams = raw_teams.ndim == 1 and len(raw_teams) > 0 and np.isin(raw_teams, [0, 1]).all()
    except (TypeError, ValueError):
        valid_teams = False
        raw_teams = np.asarray([])
    if not valid_teams:
        raise ValueError("invalid track-slot team vector")
    teams = raw_teams.astype(np.int8, copy=False)
    pitch_length, pitch_width = pitch
    if not (math.isfinite(pitch_length) and pitch_length > 0 and
            math.isfinite(pitch_width) and pitch_width > 0):
        raise ValueError("invalid pitch dimensions")
    if n_frames < 1:
        raise ValueError("n_frames must be positive")

    player_xy = np.full((n_frames, len(teams), 2), np.nan, dtype=np.float32)
    player_speed = np.full((n_frames, len(teams)), np.nan, dtype=np.float32)
    ball_xy = np.full((n_frames, 2), np.nan, dtype=np.float32)
    ball_speed = np.full(n_frames, np.nan, dtype=np.float32)

    count = 0
    with Path(raw_path).open("r", encoding="utf-8-sig", errors="strict", newline=None) as source:
        for line in source:
            row = line.rstrip("\r\n")
            fields = row.split(FIELD_SEP)
            if len(fields) != 3:
                raise ValueError("invalid tracking row")
            try:
                frame_id = int(fields[0])
            except ValueError as exc:
                raise ValueError("invalid tracking frame id") from exc
            if count >= n_frames or frame_id != count + 1:
                raise ValueError("tracking frame ids are not the expected contiguous sequence")

            players = fields[1].split(GROUP_SEP)
            if len(players) != len(teams):
                raise ValueError("tracking slot count differs from metadata")
            for slot, encoded in enumerate(players):
                x, y, speed = _group(encoded, pitch_length, pitch_width)
                player_xy[count, slot] = (x, y)
                player_speed[count, slot] = speed

            x, y, speed = _group(fields[2], pitch_length, pitch_width)
            ball_xy[count] = (x, y)
            ball_speed[count] = speed
            count += 1

    if count != n_frames:
        raise ValueError("tracking record count differs from video frame count")
    return MetricaTracking(
        frame=np.arange(n_frames, dtype=np.int32),
        team_by_slot=teams.copy(),
        player_xy=player_xy,
        player_speed=player_speed,
        ball_xy=ball_xy,
        ball_speed=ball_speed,
    )
