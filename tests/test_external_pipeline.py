"""Synthetic checks for external labels, corruption and decoder boundaries."""

import numpy as np
import pytest

from evaluation import possession_metrics as pm
from malwarous.experiments import _decode_emissions, _release_choice, _select_candidate, load_protocol
from malwarous.external_pipeline import (
    FeaturePeriod,
    labels_for_official_metrics,
    source_files,
    transition_scores,
    corrupt_period,
)
from malwarous.external_sportec import ExternalFeatures
from malwarous.features import build_features


def test_external_truth_keeps_unknown_live_owners_as_x_and_dead_without_owner_as_d():
    got = labels_for_official_metrics([0, 1, 1, -1], [-1, 0, -1, 1])
    assert got.tolist() == [pm.D, pm.H, pm.X, pm.X]


def test_transition_penalties_have_explicit_control_and_stoppage_semantics():
    scores = transition_scores(0.7, 0.8, 0.2)
    assert scores[pm.H, pm.A] == scores[pm.A, pm.H] == -0.7
    assert scores[pm.H, pm.D] == scores[pm.A, pm.D] == -0.8
    assert scores[pm.D, pm.H] == scores[pm.D, pm.A] == -0.2
    assert np.diag(scores).tolist() == [0.0, 0.0, 0.0]


def test_periods_decode_independently_with_a_metric_gap_between_them():
    first = FeaturePeriod("J03WPY", 1, np.arange(2), np.zeros((2, 1)), np.array([1, 1]), np.array([0, 0]), None)
    second = FeaturePeriod("J03WPY", 2, np.arange(2), np.zeros((2, 1)), np.array([1, 1]), np.array([1, 1]), None)
    emissions = [np.array([[5, 0, -5], [5, 0, -5]]), np.array([[0, 5, -5], [0, 5, -5]])]
    transitions = np.zeros((3, 3))
    transitions[0, 1] = -np.inf
    prediction = _decode_emissions([first, second], emissions, transitions)
    assert prediction.tolist() == [pm.H, pm.H, pm.X, pm.A, pm.A]


def test_external_corruption_rebuilds_features_without_changing_labels():
    player_xy = np.array([[[1, 1], [3, 1]]] * 20, dtype=np.float32)
    ball_xy = np.array([[2, 1]] * 20, dtype=np.float32)
    source = ExternalFeatures(1, np.arange(20), ("h", "a"), np.array([0, 1]), player_xy, ball_xy)
    features = build_features(player_xy, [0, 1], ball_xy, pitch=(10, 5))
    period = FeaturePeriod("J03WPY", 1, np.arange(20), features,
                           np.array([1] * 20), np.array([0] * 20), source)
    corrupted = corrupt_period(period, fraction=0.4, seed=13)

    assert np.count_nonzero(corrupted.features[:, 0] == 0) == 8
    assert corrupted.status is period.status
    assert corrupted.owner is period.owner
    assert np.count_nonzero(corrupted.features[:, 6] != period.features[:, 6]) == 8


def test_sealed_audit_id_is_not_accepted_by_development_loader():
    with pytest.raises(ValueError, match="development set"):
        source_files("J03WMX")


def test_locked_candidate_tiebreak_prefers_fewer_features_when_within_two_points():
    config = load_protocol()
    summary = [
        {"candidate": "geometry_mild", "mean_spell_f1": 0.62, "mean_macro_f1": 0.55},
        {"candidate": "full_mild", "mean_spell_f1": 0.61, "mean_macro_f1": 0.60},
        {"candidate": "full_control_persistence", "mean_spell_f1": 0.63, "mean_macro_f1": 0.58},
        {"candidate": "full_stoppage_sensitive", "mean_spell_f1": 0.59, "mean_macro_f1": 0.54},
    ]
    assert _select_candidate(summary, config)["candidate"] == "geometry_mild"


def test_release_falls_back_to_nearest_reference_without_two_point_external_gain():
    selected = {"candidate": "full_control_persistence", "mean_spell_f1": 0.61}
    assert _release_choice(selected, 0.60) == ("nearest_smooth50_reference", "reference")
    assert _release_choice(selected, 0.59) == ("full_control_persistence", "learned")
