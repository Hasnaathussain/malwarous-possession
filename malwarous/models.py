"""Small external-only classifier heads for live/dead evidence and live team control."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from .features import FEATURE_NAMES, swap_home_away_features


DEAD = 0
ALIVE = 1
HOME = 0
AWAY = 1


@dataclass(frozen=True)
class EvidenceHeads:
    """Two separately supervised estimators and their fixed observable feature subset."""

    alive_model: HistGradientBoostingClassifier
    owner_model: HistGradientBoostingClassifier
    feature_names: tuple[str, ...]
    random_state: int


def _feature_indices(feature_names: Sequence[str]) -> np.ndarray:
    requested = tuple(feature_names)
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("feature names must be a nonempty unique sequence")
    unknown = set(requested) - set(FEATURE_NAMES)
    if unknown:
        raise ValueError("feature names are outside the approved schema")
    return np.asarray([FEATURE_NAMES.index(name) for name in requested], dtype=np.int32)


def _new_model(*, max_iter: int, max_leaf_nodes: int, min_samples_leaf: int,
               max_bins: int, l2_regularization: float, random_state: int):
    if min(max_iter, max_leaf_nodes, min_samples_leaf) < 1:
        raise ValueError("estimator iteration/tree settings must be positive")
    if not 2 <= max_bins <= 255 or l2_regularization < 0 or not np.isfinite(l2_regularization):
        raise ValueError("invalid estimator regularization settings")
    return HistGradientBoostingClassifier(
        loss="log_loss",
        max_iter=max_iter,
        max_leaf_nodes=max_leaf_nodes,
        min_samples_leaf=min_samples_leaf,
        max_bins=max_bins,
        l2_regularization=l2_regularization,
        class_weight="balanced",
        early_stopping=False,
        random_state=random_state,
    )


def fit_evidence_heads(
    features: object,
    ball_status: object,
    ball_owner: object,
    *,
    feature_names: Sequence[str] = FEATURE_NAMES,
    max_iter: int = 100,
    max_leaf_nodes: int = 15,
    min_samples_leaf: int = 50,
    max_bins: int = 63,
    l2_regularization: float = 2.0,
    random_state: int = 20271113,
) -> EvidenceHeads:
    """Fit separate heads; label values are arguments only to this training function.

    `ball_status`: -1 unknown, 0 inactive/dead, 1 active/live.
    `ball_owner`: -1 unknown, 0 home, 1 away. Ownership loss uses only active rows with a known owner.
    Every training row is augmented by a home/away feature swap; only owner targets swap too.
    """
    x = np.asarray(features, dtype=np.float32)
    status = np.asarray(ball_status)
    owner = np.asarray(ball_owner)
    if x.ndim != 2 or x.shape[1] != len(FEATURE_NAMES) or not np.isfinite(x).all():
        raise ValueError("features must be finite and match the approved feature schema")
    if status.shape != (len(x),) or owner.shape != (len(x),):
        raise ValueError("label arrays must align one-to-one with features")
    if not np.isin(status, (-1, DEAD, ALIVE)).all() or not np.isin(owner, (-1, HOME, AWAY)).all():
        raise ValueError("unsupported external label code")
    status = status.astype(np.int8, copy=False)
    owner = owner.astype(np.int8, copy=False)
    selected_features = tuple(feature_names)
    indices = _feature_indices(selected_features)
    x = x[:, indices]
    swapped = swap_home_away_features(np.asarray(features, dtype=np.float32))[:, indices]

    status_valid = status >= 0
    y_alive = (status[status_valid] == ALIVE).astype(np.int8)
    if set(np.unique(y_alive)) != {0, 1}:
        raise ValueError("alive head requires both known dead and live examples")
    alive_x = np.concatenate((x[status_valid], swapped[status_valid]), axis=0)
    alive_y = np.concatenate((y_alive, y_alive), axis=0)

    owner_valid = (status == ALIVE) & (owner >= 0)
    y_owner = owner[owner_valid]
    if set(np.unique(y_owner)) != {HOME, AWAY}:
        raise ValueError("owner head requires known live examples from both teams")
    owner_x = np.concatenate((x[owner_valid], swapped[owner_valid]), axis=0)
    owner_y = np.concatenate((y_owner, 1 - y_owner), axis=0)

    alive_model = _new_model(
        max_iter=max_iter, max_leaf_nodes=max_leaf_nodes, min_samples_leaf=min_samples_leaf,
        max_bins=max_bins, l2_regularization=l2_regularization, random_state=random_state,
    )
    owner_model = _new_model(
        max_iter=max_iter, max_leaf_nodes=max_leaf_nodes, min_samples_leaf=min_samples_leaf,
        max_bins=max_bins, l2_regularization=l2_regularization, random_state=random_state,
    )
    alive_model.fit(alive_x, alive_y)
    owner_model.fit(owner_x, owner_y)
    return EvidenceHeads(alive_model, owner_model, selected_features, random_state)


def predict_log_emissions(model: EvidenceHeads, features: object) -> np.ndarray:
    """Return normalized H/A/D log-emissions with exact home/away swap equivariance."""
    x_all = np.asarray(features, dtype=np.float32)
    if x_all.ndim != 2 or x_all.shape[1] != len(FEATURE_NAMES) or not np.isfinite(x_all).all():
        raise ValueError("features must be finite and match the approved feature schema")
    indices = _feature_indices(model.feature_names)
    x = x_all[:, indices]
    sx = swap_home_away_features(x_all)[:, indices]

    def class_probability(estimator, values: np.ndarray, class_code: int) -> np.ndarray:
        positions = np.flatnonzero(estimator.classes_ == class_code)
        if len(positions) != 1:
            raise ValueError("trained estimator is missing an expected class")
        return estimator.predict_proba(values)[:, int(positions[0])]

    # Alive head classes are 0=dead, 1=live. Team swapping leaves them unchanged.
    p_dead = 0.5 * (
        class_probability(model.alive_model, x, DEAD) +
        class_probability(model.alive_model, sx, DEAD)
    )
    p_live = 0.5 * (
        class_probability(model.alive_model, x, ALIVE) +
        class_probability(model.alive_model, sx, ALIVE)
    )
    # The swapped input reverses ownership classes; average in the original orientation.
    p_home = 0.5 * (
        class_probability(model.owner_model, x, HOME) +
        class_probability(model.owner_model, sx, AWAY)
    )
    p_away = 0.5 * (
        class_probability(model.owner_model, x, AWAY) +
        class_probability(model.owner_model, sx, HOME)
    )
    probabilities = np.column_stack((p_live * p_home, p_live * p_away, p_dead))
    probabilities = np.maximum(probabilities, 1e-12)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    return np.log(probabilities)
