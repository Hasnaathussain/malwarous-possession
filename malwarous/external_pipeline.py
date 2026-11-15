"""Development-only loaders and metric adapters for DFL/Sportec match experiments."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

import numpy as np

from evaluation import possession_metrics as official_metrics
from scripts.fetch_sportec import DEV_MATCHES

from .corruption import mask_ball_observations
from .external_sportec import ALIVE, DEAD, HOME, AWAY, ExternalFeatures, ExternalLabels
from .external_sportec import load_sportec_match, read_sportec_team_map
from .features import build_features
from .models import EvidenceHeads, predict_log_emissions
from .temporal import viterbi_decode
from starter.baseline import smooth as official_baseline_smooth


@dataclass(frozen=True)
class FeaturePeriod:
    match_id: str
    period_id: int
    frame_ids: np.ndarray
    features: np.ndarray
    status: np.ndarray
    owner: np.ndarray
    source_features: ExternalFeatures


def source_files(match_id: str, cache_root: Path | None = None) -> tuple[Path, Path]:
    if match_id not in DEV_MATCHES:
        raise ValueError("match is not in the predeclared development set")
    root = Path(__file__).resolve().parents[1]
    base = ((cache_root or root / "external_data_cache").resolve() / "sportec" / match_id).resolve()
    allowed_root = (root / "external_data_cache").resolve()
    if allowed_root not in base.parents:
        raise ValueError("source path must stay under the external data cache")
    metadata = tuple(base.glob("DFL_02_01_matchinformation_*_DFL-MAT-*.xml"))
    tracking = tuple(base.glob("DFL_04_03_positions_raw_observed_*_DFL-MAT-*.xml"))
    if len(metadata) != 1 or len(tracking) != 1:
        raise FileNotFoundError("development source files are missing or ambiguous")
    return metadata[0], tracking[0]


def load_feature_periods(match_id: str) -> tuple[FeaturePeriod, ...]:
    """Parse one permitted development match and derive observables separate from targets."""
    metadata_path, tracking_path = source_files(match_id)
    team_map = read_sportec_team_map(metadata_path)
    match = load_sportec_match(tracking_path, team_map)
    periods = []
    for features, labels in zip(match.features, match.labels):
        if not np.array_equal(features.frame_ids, labels.frame_ids):
            raise ValueError("external frame keys disagree")
        matrix = build_features(
            features.player_xy,
            features.team_by_player,
            features.ball_xy,
            pitch=(105.0, 68.0),
            fps=25.0,
            segments=((0, len(features.frame_ids)),),
        )
        periods.append(FeaturePeriod(
            match_id=match_id,
            period_id=features.period_id,
            frame_ids=features.frame_ids,
            features=matrix,
            status=labels.ball_status,
            owner=labels.ball_owner,
            source_features=features,
        ))
    return tuple(periods)


def corrupt_period(period: FeaturePeriod, *, fraction: float, seed: int,
                   mean_block_frames: float = 8.0) -> FeaturePeriod:
    corrupted = mask_ball_observations(
        period.source_features,
        fraction=fraction,
        seed=seed,
        mean_block_frames=mean_block_frames,
    )
    features = build_features(
        corrupted.player_xy,
        corrupted.team_by_player,
        corrupted.ball_xy,
        pitch=(105.0, 68.0),
        fps=25.0,
        segments=((0, len(corrupted.frame_ids)),),
    )
    return replace(period, features=features, source_features=corrupted)


def labels_for_official_metrics(status: object, owner: object) -> np.ndarray:
    """Map source labels to official H/A/D/X codes; unknown active owners remain X."""
    state = np.asarray(status)
    side = np.asarray(owner)
    if state.ndim != 1 or side.shape != state.shape:
        raise ValueError("external status and owner labels must be parallel vectors")
    if not np.isin(state, (-1, 0, 1)).all() or not np.isin(side, (-1, 0, 1)).all():
        raise ValueError("external labels contain an unsupported code")
    target = np.full(len(state), official_metrics.X, dtype=np.int8)
    target[state == DEAD] = official_metrics.D
    target[(state == ALIVE) & (side == HOME)] = official_metrics.H
    target[(state == ALIVE) & (side == AWAY)] = official_metrics.A
    return target


def transition_scores(turnover_penalty: float, live_dead_penalty: float,
                      dead_restart_penalty: float) -> np.ndarray:
    if any(not np.isfinite(value) or value < 0
           for value in (turnover_penalty, live_dead_penalty, dead_restart_penalty)):
        raise ValueError("transition penalties must be finite and nonnegative")
    scores = np.zeros((3, 3), dtype=np.float64)
    scores[official_metrics.H, official_metrics.A] = -turnover_penalty
    scores[official_metrics.A, official_metrics.H] = -turnover_penalty
    scores[official_metrics.H, official_metrics.D] = -live_dead_penalty
    scores[official_metrics.A, official_metrics.D] = -live_dead_penalty
    scores[official_metrics.D, official_metrics.H] = -dead_restart_penalty
    scores[official_metrics.D, official_metrics.A] = -dead_restart_penalty
    return scores


def decode_periods(model: EvidenceHeads, periods: Sequence[FeaturePeriod],
                   transitions: np.ndarray) -> np.ndarray:
    """Run model+decoder independently per period, separated by official X gaps."""
    chunks = []
    for period in periods:
        emissions = predict_log_emissions(model, period.features)
        chunks.append(viterbi_decode(emissions, transitions))
        chunks.append(np.asarray([official_metrics.X], dtype=np.int8))
    if not chunks:
        return np.empty(0, dtype=np.int8)
    chunks.pop()
    return np.concatenate(chunks)


def truth_for_metric(periods: Sequence[FeaturePeriod]) -> np.ndarray:
    chunks = []
    for period in periods:
        chunks.append(labels_for_official_metrics(period.status, period.owner))
        chunks.append(np.asarray([official_metrics.X], dtype=np.int8))
    if not chunks:
        return np.empty(0, dtype=np.int8)
    chunks.pop()
    return np.concatenate(chunks)


def score_match(periods: Sequence[FeaturePeriod], prediction: object) -> dict:
    pred = np.asarray(prediction, dtype=np.int8)
    truth = truth_for_metric(periods)
    if pred.shape != truth.shape:
        raise ValueError("external prediction and truth shapes disagree")
    return official_metrics.evaluate(truth, pred, bootstrap_n=0)


def nearest_smooth_predictions(periods: Sequence[FeaturePeriod], window: int = 50) -> np.ndarray:
    """Apply the nearest-player smooth-window reference; source track order breaks exact ties."""
    if window < 0:
        raise ValueError("window cannot be negative")
    chunks = []
    mapping = {"H": official_metrics.H, "A": official_metrics.A,
               "D": official_metrics.D, "X": official_metrics.X}
    for index, period in enumerate(periods):
        raw = np.full(len(period.features), -1, dtype=np.int8)
        source = period.source_features
        if (len(source.frame_ids) != len(raw) or
                source.player_xy.shape[0] != len(raw) or
                source.ball_xy.shape != (len(raw), 2)):
            raise ValueError("reference source coordinates do not align with the feature period")
        sides = np.asarray(source.team_by_player)
        for start in range(0, len(raw), 2048):
            stop = min(len(raw), start + 2048)
            players = source.player_xy[start:stop]
            ball = source.ball_xy[start:stop]
            valid_player = np.isfinite(players).all(axis=2)
            valid_ball = np.isfinite(ball).all(axis=1)
            delta = players - ball[:, None, :]
            distance_squared = np.sum(delta * delta, axis=2, dtype=np.float64)
            eligible = valid_player & valid_ball[:, None]
            nearest_distance = np.min(np.where(eligible, distance_squared, np.inf), axis=1)
            valid = valid_ball & np.isfinite(nearest_distance)
            nearest_slot = np.argmin(np.where(eligible, distance_squared, np.inf), axis=1)
            raw[start:stop][valid] = sides[nearest_slot[valid]]
        labels = official_baseline_smooth(raw, window)
        chunks.append(np.asarray([mapping[str(label)] for label in labels], dtype=np.int8))
        if index + 1 < len(periods):
            chunks.append(np.asarray([official_metrics.X], dtype=np.int8))
    return np.concatenate(chunks) if chunks else np.empty(0, dtype=np.int8)
