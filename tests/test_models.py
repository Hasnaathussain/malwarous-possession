"""Synthetic tests for the separately labelled and team-symmetric evidence heads."""

import numpy as np
import pytest

from malwarous.features import FEATURE_NAMES, swap_home_away_features
from malwarous.models import ALIVE, AWAY, DEAD, HOME, fit_evidence_heads, predict_log_emissions


def _training_data(n=160):
    rng = np.random.default_rng(11)
    x = rng.normal(size=(n, len(FEATURE_NAMES))).astype(np.float32)
    margin = FEATURE_NAMES.index("home_minus_away_distance_m")
    x[:, margin] = np.linspace(-8, 8, n)
    status = np.where(np.arange(n) % 3 == 0, DEAD, ALIVE).astype(np.int8)
    owner = np.where(x[:, margin] < 0, HOME, AWAY).astype(np.int8)
    owner[np.arange(n) % 7 == 0] = -1
    return x, status, owner


def _fit():
    x, status, owner = _training_data()
    return x, fit_evidence_heads(
        x, status, owner,
        feature_names=("ball_observed", "home_minus_away_distance_m"),
        max_iter=6, max_leaf_nodes=5, min_samples_leaf=5, max_bins=16,
    )


def test_fit_uses_only_the_named_features_and_owner_labels_only_during_training():
    x, model = _fit()
    assert model.feature_names == ("ball_observed", "home_minus_away_distance_m")
    emissions = predict_log_emissions(model, x)
    assert emissions.shape == (len(x), 3)
    assert np.isfinite(emissions).all()
    assert np.allclose(np.exp(emissions).sum(axis=1), 1.0)


def test_predictions_are_exactly_equivariant_to_home_away_exchange():
    x, model = _fit()
    original = np.exp(predict_log_emissions(model, x))
    swapped = np.exp(predict_log_emissions(model, swap_home_away_features(x)))
    assert np.allclose(original[:, 0], swapped[:, 1], atol=1e-7)
    assert np.allclose(original[:, 1], swapped[:, 0], atol=1e-7)
    assert np.allclose(original[:, 2], swapped[:, 2], atol=1e-7)


def test_unknown_live_owner_is_ignored_for_owner_head_but_status_remains_valid():
    x, status, owner = _training_data()
    owner[(status == ALIVE)] = -1
    with pytest.raises(ValueError, match="owner head"):
        fit_evidence_heads(x, status, owner, max_iter=2, max_leaf_nodes=3,
                           min_samples_leaf=2, max_bins=8)


def test_unsupported_labels_and_unknown_feature_names_are_rejected():
    x, status, owner = _training_data()
    status[0] = 7
    with pytest.raises(ValueError, match="label code"):
        fit_evidence_heads(x, status, owner)
    x, status, owner = _training_data()
    with pytest.raises(ValueError, match="outside the approved schema"):
        fit_evidence_heads(x, status, owner, feature_names=("target_frame_label",))
