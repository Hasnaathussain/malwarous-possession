"""Synthetic inference/CSV contracts; no target data is involved."""

from pathlib import Path

import numpy as np
import pytest

from evaluation import possession_metrics as pm
from malwarous.inference import infer_labels, official_csv_valid, write_submission
from malwarous.metrica_ingest import MetricaTracking
from malwarous.models import fit_evidence_heads
from malwarous.features import FEATURE_NAMES


def _synthetic_model():
    rng = np.random.default_rng(4)
    x = rng.normal(size=(180, len(FEATURE_NAMES))).astype(np.float32)
    x[:, FEATURE_NAMES.index("home_minus_away_distance_m")] = np.linspace(-5, 5, len(x))
    status = np.where(np.arange(len(x)) % 4 == 0, 0, 1)
    owner = np.where(x[:, FEATURE_NAMES.index("home_minus_away_distance_m")] < 0, 0, 1)
    return fit_evidence_heads(x, status, owner, max_iter=4, max_leaf_nodes=5,
                              min_samples_leaf=5, max_bins=16)


def test_inference_leaves_ungraded_and_halftime_frames_as_x():
    n = 8
    tracking = MetricaTracking(
        frame=np.arange(n),
        team_by_slot=np.array([0, 1], dtype=np.int8),
        player_xy=np.array([[[2, 2], [8, 8]]] * n, dtype=np.float32),
        player_speed=np.ones((n, 2), dtype=np.float32),
        ball_xy=np.array([[2, 2]] * n, dtype=np.float32),
        ball_speed=np.ones(n, dtype=np.float32),
    )
    model = _synthetic_model()
    labels = infer_labels(tracking, model, np.zeros((3, 3)), segments=[(1, 3), (5, 7)],
                          pitch=(10, 10), fps=25)
    assert labels[[0, 3, 4, 7]].tolist() == [pm.X] * 4
    assert np.isin(labels[[1, 2, 5, 6]], [pm.H, pm.A, pm.D]).all()


def test_submission_writer_is_exact_ascii_lf_and_validates(tmp_path):
    path = write_submission(tmp_path / "Malwarous.csv", [pm.H, pm.A, pm.D, pm.X], n_expected=4)
    assert path.read_bytes() == b"frame,label\n0,H\n1,A\n2,D\n3,X\n"
    assert official_csv_valid(path, n_expected=4)


@pytest.mark.parametrize("labels,n", [([0, 1], 3), ([0, 1, 4], 3), ([0, 1, -1], 3)])
def test_writer_rejects_wrong_length_or_illegal_label(tmp_path, labels, n):
    with pytest.raises(ValueError):
        write_submission(tmp_path / "bad.csv", labels, n_expected=n)


def test_official_validator_rejects_wrong_frame_contract(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("frame,label\n1,H\n0,A\n", encoding="ascii")
    assert not official_csv_valid(path, n_expected=2)
