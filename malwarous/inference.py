"""Deterministic full-match inference and exact two-column CSV writing."""

from __future__ import annotations

import csv
import os
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING, Sequence

import numpy as np

from evaluation import possession_metrics as official_metrics

if TYPE_CHECKING:
    from .metrica_ingest import MetricaTracking
    from .models import EvidenceHeads


CODE_TO_LABEL = np.asarray(("H", "A", "D", "X"), dtype="<U1")


def infer_labels(
    tracking: MetricaTracking,
    model: EvidenceHeads,
    transitions: object,
    *,
    segments: Sequence[tuple[int, int]],
    pitch: tuple[float, float],
    fps: float,
) -> np.ndarray:
    """Produce labels algorithmically, leaving every frame outside official half ranges as X."""
    from .features import build_features
    from .models import predict_log_emissions
    from .temporal import viterbi_decode

    features = build_features(
        tracking.player_xy,
        tracking.team_by_slot,
        tracking.ball_xy,
        player_speed=tracking.player_speed,
        ball_speed=tracking.ball_speed,
        pitch=pitch,
        fps=fps,
        segments=segments,
    )
    emissions = predict_log_emissions(model, features)
    decoded = viterbi_decode(emissions, transitions, segments=segments)
    labels = np.full(len(tracking.frame), official_metrics.X, dtype=np.int8)
    valid = decoded >= 0
    labels[valid] = decoded[valid]
    return labels


def write_submission(path: str | Path, labels: object, *, n_expected: int) -> Path:
    """Atomically write canonical ASCII CSV with LF newlines and exactly frame,label columns."""
    output = Path(path)
    codes = np.asarray(labels)
    if codes.shape != (n_expected,) or not np.isin(codes, (0, 1, 2, 3)).all():
        raise ValueError("label vector violates the competition frame/label contract")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="ascii", newline="", dir=output.parent,
            prefix=".submission-", suffix=".tmp", delete=False,
        ) as temporary:
            temp_path = Path(temporary.name)
            writer = csv.writer(temporary, lineterminator="\n")
            writer.writerow(("frame", "label"))
            writer.writerows((index, CODE_TO_LABEL[int(code)]) for index, code in enumerate(codes))
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temp_path, output)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
    return output


def official_csv_valid(path: str | Path, *, n_expected: int) -> bool:
    """Run the organizer's own parser/validator without returning its data-bearing reason string."""
    table = official_metrics.read_label_csv(path)
    return official_metrics.validate_submission(table, n_expected) is None
