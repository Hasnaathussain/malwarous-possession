"""Identity-independent geometric and motion evidence built without label columns."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np


FEATURE_NAMES = (
    "ball_observed",
    "ball_tracker_speed_mps",
    "ball_tracker_speed_valid",
    "ball_motion_speed_mps",
    "ball_motion_valid",
    "ball_age_seconds",
    "home_nearest_distance_m",
    "away_nearest_distance_m",
    "home_minus_away_distance_m",
    "home_players_within_1m",
    "away_players_within_1m",
    "home_players_within_2m",
    "away_players_within_2m",
    "home_players_within_5m",
    "away_players_within_5m",
    "home_nearest_player_speed_mps",
    "away_nearest_player_speed_mps",
    "home_nearest_speed_valid",
    "away_nearest_speed_valid",
    "home_tracks_observed",
    "away_tracks_observed",
)

_SWAP_PAIRS = (
    ("home_nearest_distance_m", "away_nearest_distance_m"),
    ("home_players_within_1m", "away_players_within_1m"),
    ("home_players_within_2m", "away_players_within_2m"),
    ("home_players_within_5m", "away_players_within_5m"),
    ("home_nearest_player_speed_mps", "away_nearest_player_speed_mps"),
    ("home_nearest_speed_valid", "away_nearest_speed_valid"),
    ("home_tracks_observed", "away_tracks_observed"),
)
_SIGNED_COLUMNS = ("home_minus_away_distance_m",)
_INDEX = {name: index for index, name in enumerate(FEATURE_NAMES)}


def normalize_segments(
    n_frames: int,
    segments: Sequence[tuple[int, int]] | None,
) -> tuple[tuple[int, int], ...]:
    if segments is None:
        return ((0, n_frames),) if n_frames else ()
    checked = []
    for pair in segments:
        if len(pair) != 2:
            raise ValueError("segments must contain half-open pairs")
        start, stop = pair
        if (isinstance(start, (bool, np.bool_)) or isinstance(stop, (bool, np.bool_)) or
                not isinstance(start, (int, np.integer)) or not isinstance(stop, (int, np.integer))):
            raise ValueError("segment bounds must be integers")
        start, stop = int(start), int(stop)
        if not 0 <= start <= stop <= n_frames:
            raise ValueError("segment outside the frame range")
        checked.append((start, stop))
    nonempty = sorted((start, stop) for start, stop in checked if start < stop)
    if any(next_start < prior_stop for (_, prior_stop), (next_start, _) in zip(nonempty, nonempty[1:])):
        raise ValueError("segments must be disjoint")
    return tuple(sorted(checked))


def _matrix(name: str, value: object, shape: tuple[int, ...]) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=np.float32)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.shape != shape:
        raise ValueError(f"{name} must have shape {shape}")
    if np.isinf(array).any():
        # Missing is represented by NaN; infinity usually means corrupt input.
        raise ValueError(f"{name} cannot contain infinity")
    return array


def build_features(
    player_xy: object,
    team_by_slot: object,
    ball_xy: object,
    *,
    player_speed: object | None = None,
    ball_speed: object | None = None,
    pitch: tuple[float, float] = (105.3, 68.0),
    fps: float = 25.0,
    segments: Sequence[tuple[int, int]] | None = None,
    max_ball_age_seconds: float = 5.0,
    max_motion_gap_frames: int = 3,
    chunk_size: int = 512,
) -> np.ndarray:
    """Build dense float32 per-frame evidence. IDs, labels and absolute field coordinates are unused.

    `team_by_slot` maps each anonymous tracking slot to 0=home/1=away. All temporal differencing
    resets at each segment boundary. Local missingness is explicit and NaNs never become (0, 0).
    """
    players = np.asarray(player_xy, dtype=np.float32)
    ball = np.asarray(ball_xy, dtype=np.float32)
    sides = np.asarray(team_by_slot)
    if players.ndim != 3 or players.shape[2] != 2:
        raise ValueError("player_xy must have shape [frame, slot, 2]")
    n_frames, n_slots, _ = players.shape
    if n_slots == 0 or ball.shape != (n_frames, 2):
        raise ValueError("ball/player frame dimensions disagree")
    if np.isinf(players).any() or np.isinf(ball).any():
        raise ValueError("positions cannot contain infinity")
    if sides.shape != (n_slots,) or not np.isin(sides, (0, 1)).all():
        raise ValueError("team_by_slot must map every slot to 0 or 1")
    if not all(np.any(sides == side) for side in (0, 1)):
        raise ValueError("both teams must have at least one tracking slot")

    if player_speed is None:
        speeds = np.full((n_frames, n_slots), np.nan, dtype=np.float32)
    else:
        speeds = _matrix("player_speed", player_speed, (n_frames, n_slots))
    if ball_speed is None:
        ball_speeds = np.full(n_frames, np.nan, dtype=np.float32)
    else:
        ball_speeds = _matrix("ball_speed", ball_speed, (n_frames,))

    length, width = pitch
    if not (math.isfinite(length) and length > 0 and math.isfinite(width) and width > 0):
        raise ValueError("pitch dimensions must be finite and positive")
    integer_settings = (max_motion_gap_frames, chunk_size)
    if any(isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer))
           for value in integer_settings):
        raise ValueError("motion gap and chunk size must be integers")
    if not (math.isfinite(fps) and fps > 0 and math.isfinite(max_ball_age_seconds) and
            max_ball_age_seconds > 0 and max_motion_gap_frames >= 1 and chunk_size >= 1):
        raise ValueError("invalid feature timing or chunk configuration")
    allowed = normalize_segments(n_frames, segments)

    out = np.zeros((n_frames, len(FEATURE_NAMES)), dtype=np.float32)
    player_observed = np.isfinite(players).all(axis=2)
    ball_observed = np.isfinite(ball).all(axis=1)
    diagonal = math.hypot(length, width)

    for start, stop in allowed:
        if start == stop:
            continue
        seen_index: int | None = None
        previous_ball_index: int | None = None
        for frame in range(start, stop):
            out[frame, _INDEX["ball_observed"]] = float(ball_observed[frame])
            tracker_speed = ball_speeds[frame]
            if math.isfinite(float(tracker_speed)) and tracker_speed >= 0:
                out[frame, _INDEX["ball_tracker_speed_mps"]] = tracker_speed
                out[frame, _INDEX["ball_tracker_speed_valid"]] = 1.0
            if ball_observed[frame]:
                if (previous_ball_index is not None and
                        frame - previous_ball_index <= max_motion_gap_frames):
                    elapsed = (frame - previous_ball_index) / fps
                    delta = ball[frame] - ball[previous_ball_index]
                    out[frame, _INDEX["ball_motion_speed_mps"]] = float(np.linalg.norm(delta) / elapsed)
                    out[frame, _INDEX["ball_motion_valid"]] = 1.0
                previous_ball_index = frame
                seen_index = frame
                out[frame, _INDEX["ball_age_seconds"]] = 0.0
            else:
                age = max_ball_age_seconds if seen_index is None else (frame - seen_index) / fps
                out[frame, _INDEX["ball_age_seconds"]] = min(max_ball_age_seconds, age)

        for chunk_start in range(start, stop, chunk_size):
            chunk_stop = min(stop, chunk_start + chunk_size)
            positions = players[chunk_start:chunk_stop]
            coords = ball[chunk_start:chunk_stop]
            valid_player = player_observed[chunk_start:chunk_stop]
            valid_ball = ball_observed[chunk_start:chunk_stop]
            delta = positions - coords[:, None, :]
            distance = np.sqrt(np.sum(delta * delta, axis=2, dtype=np.float32))

            for side, prefix in ((0, "home"), (1, "away")):
                indices = np.flatnonzero(sides == side)
                side_valid = valid_player[:, indices] & valid_ball[:, None]
                side_dist = np.where(side_valid, distance[:, indices], np.inf)
                valid_count = np.sum(valid_player[:, indices], axis=1, dtype=np.int16)
                best_slot_index = np.argmin(side_dist, axis=1)
                best_distance = np.min(side_dist, axis=1)
                best_distance = np.where(np.isfinite(best_distance), best_distance, diagonal)
                out[chunk_start:chunk_stop, _INDEX[f"{prefix}_nearest_distance_m"]] = best_distance
                out[chunk_start:chunk_stop, _INDEX[f"{prefix}_tracks_observed"]] = valid_count

                for radius in (1, 2, 5):
                    count = np.sum(side_valid & (side_dist <= radius), axis=1, dtype=np.int16)
                    out[chunk_start:chunk_stop, _INDEX[f"{prefix}_players_within_{radius}m"]] = count

                nearest_speeds = speeds[chunk_start:chunk_stop, indices][
                    np.arange(chunk_stop - chunk_start), best_slot_index
                ]
                valid_nearest_speed = (np.isfinite(nearest_speeds) & (valid_count > 0) & valid_ball)
                speed_index = _INDEX[f"{prefix}_nearest_player_speed_mps"]
                valid_index = _INDEX[f"{prefix}_nearest_speed_valid"]
                out[chunk_start:chunk_stop, speed_index] = np.where(
                    valid_nearest_speed, nearest_speeds, 0.0
                )
                out[chunk_start:chunk_stop, valid_index] = valid_nearest_speed.astype(np.float32)

        out[start:stop, _INDEX["home_minus_away_distance_m"]] = (
            out[start:stop, _INDEX["home_nearest_distance_m"]] -
            out[start:stop, _INDEX["away_nearest_distance_m"]]
        )
    return out


def swap_home_away_features(features: object) -> np.ndarray:
    """Return the same evidence with team sides exchanged; useful for symmetry augmentation."""
    matrix = np.asarray(features, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != len(FEATURE_NAMES):
        raise ValueError("features must have shape [N, feature_count]")
    if not np.isfinite(matrix).all():
        raise ValueError("feature matrix must be finite")
    swapped = matrix.copy()
    for home_name, away_name in _SWAP_PAIRS:
        home_index, away_index = _INDEX[home_name], _INDEX[away_name]
        swapped[:, home_index] = matrix[:, away_index]
        swapped[:, away_index] = matrix[:, home_index]
    for name in _SIGNED_COLUMNS:
        swapped[:, _INDEX[name]] = -matrix[:, _INDEX[name]]
    return swapped
