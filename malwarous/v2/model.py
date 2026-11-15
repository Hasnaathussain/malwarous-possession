"""Observation-weighted temporal evidence with identity-independent geometry.

All transforms consume observables only. Each call represents one continuous half;
centered context is deliberately offline and must never cross a half boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from malwarous.features import FEATURE_NAMES, build_features, swap_home_away_features
from malwarous.temporal import viterbi_decode


BASE_INDEX = {name: i for i, name in enumerate(FEATURE_NAMES)}
MODEL_SETTINGS = dict(max_iter=100, max_leaf_nodes=15, min_samples_leaf=100,
                      l2_regularization=5., max_bins=63, early_stopping=False,
                      random_state=20261114)


def window_mean(values, radius, weights=None):
    """Centered truncated mean, weighted by observation support, O(n * columns)."""
    x = np.asarray(values, dtype=np.float64)
    vector = x.ndim == 1
    if vector:
        x = x[:, None]
    if x.ndim != 2 or not np.isfinite(x).all() or radius < 0 or int(radius) != radius:
        raise ValueError('invalid window input')
    if weights is None:
        w = np.ones_like(x)
    else:
        w = np.broadcast_to(np.asarray(weights, dtype=float).reshape(len(x), -1), x.shape)
        if not np.isfinite(w).all() or (w < 0).any():
            raise ValueError('invalid window weights')
    lo = np.maximum(0, np.arange(len(x)) - radius)
    hi = np.minimum(len(x), np.arange(len(x)) + radius + 1)
    sx = np.vstack((np.zeros((1, x.shape[1])), np.cumsum(x * w, axis=0)))
    sw = np.vstack((np.zeros((1, x.shape[1])), np.cumsum(w, axis=0)))
    denom = sw[hi] - sw[lo]
    result = np.divide(sx[hi] - sx[lo], denom, out=np.zeros_like(denom), where=denom > 0)
    return result[:, 0] if vector else result


def _context(base, ball, fps, pitch):
    n = len(base)
    columns = [base.copy()]
    names = list(FEATURE_NAMES)
    observed = base[:, BASE_INDEX['ball_observed']]
    home = base[:, BASE_INDEX['home_nearest_distance_m']]
    away = base[:, BASE_INDEX['away_nearest_distance_m']]
    both = observed * (base[:, BASE_INDEX['home_tracks_observed']] > 0) * (
        base[:, BASE_INDEX['away_tracks_observed']] > 0)
    # Missing geometry has an explicit support bit; it is not a 125m physical observation.
    for name in ('home_nearest_distance_m', 'away_nearest_distance_m',
                 'home_minus_away_distance_m'):
        col = BASE_INDEX[name]
        columns[0][:, col] = np.where(both > 0, np.clip(base[:, col], -30, 30), 0)
    speed = np.minimum(base[:, BASE_INDEX['ball_motion_speed_mps']], 60)
    speed_valid = base[:, BASE_INDEX['ball_motion_valid']]
    near = np.minimum(home, away)
    margin = np.clip(away - home, -10, 10)
    control = np.sign(margin) * ((near <= 3) & (np.abs(margin) >= .4) & (both > 0))

    def add(name, value):
        names.append(name)
        columns.append(np.asarray(value, dtype=np.float32).reshape(n, 1))

    add('geometry_supported', both)
    add('nearby_control_signed', control)
    add('control_margin_m', np.where(both, margin, 0))
    add('nearest_any_m', np.where(both, np.minimum(near, 30), 0))
    # Pitch-relative boundary evidence transfers between grounds and is not match time/location.
    edge = np.minimum(pitch[0] / 2 - np.abs(ball[:, 0]), pitch[1] / 2 - np.abs(ball[:, 1]))
    edge = np.where(observed, np.nan_to_num(edge), 0)
    add('ball_inside_edge_m', np.clip(edge, -15, 30))
    for seconds in (.4, 2., 4.):
        radius = int(round(seconds * fps / 2))
        key = f'{seconds:g}s'
        add(f'ball_support_{key}', window_mean(observed, radius))
        add(f'geometry_support_{key}', window_mean(both, radius))
        add(f'motion_support_{key}', window_mean(speed_valid, radius))
        add(f'ball_speed_{key}', window_mean(speed, radius, speed_valid))
        add(f'ball_speed_square_{key}', window_mean(speed ** 2, radius, speed_valid))
        add(f'home_distance_{key}', window_mean(np.minimum(home, 30), radius, both))
        add(f'away_distance_{key}', window_mean(np.minimum(away, 30), radius, both))
        add(f'control_margin_{key}', window_mean(margin, radius, both))
        add(f'nearby_control_{key}', window_mean(control, radius, np.abs(control)))
        add(f'nearby_control_support_{key}', window_mean(np.abs(control), radius))
        add(f'edge_{key}', window_mean(edge, radius, observed))

    idx = np.arange(n)
    known = control != 0
    previous = np.maximum.accumulate(np.where(known, idx, -1))
    following = np.minimum.accumulate(np.where(known, idx, n)[::-1])[::-1]
    for direction, location in (('previous', previous), ('next', following)):
        age = np.abs(location - idx) / fps
        valid = (location >= 0) & (location < n) & (age <= 5.)
        safe = np.clip(location, 0, max(0, n - 1))
        add(f'{direction}_control', np.where(valid, control[safe], 0))
        add(f'{direction}_control_age_s', np.where(valid, age, 5.))
        add(f'{direction}_control_supported', valid)
    x = np.concatenate(columns, axis=1).astype(np.float32)
    if not np.isfinite(x).all():
        raise ValueError('nonfinite contextual features')
    return x, tuple(names)


@dataclass(frozen=True)
class ContextFeatures:
    original: np.ndarray
    swapped: np.ndarray
    names: tuple[str, ...]
    base: np.ndarray


def build_context(player_xy, team_by_slot, ball_xy, *, fps=25., pitch=(105., 68.)):
    """One half, positions in metres with origin at pitch centre.

    Corner-origin inputs must subtract half the pitch dimensions before this call.
    This explicit convention is necessary for transferable boundary evidence.
    """
    if len(ball_xy) == 0:
        raise ValueError('a context half must be nonempty')
    base = build_features(player_xy, team_by_slot, ball_xy, fps=fps, pitch=pitch)
    original, names = _context(base, np.asarray(ball_xy), fps, pitch)
    swapped, swap_names = _context(swap_home_away_features(base), np.asarray(ball_xy), fps, pitch)
    if swap_names != names:
        raise ValueError('feature schemas differ')
    return ContextFeatures(original, swapped, names, base)


@dataclass
class ContextHeads:
    alive: HistGradientBoostingClassifier
    owner: HistGradientBoostingClassifier
    feature_names: tuple[str, ...]


def fit_heads(x, swapped, status, owner, names):
    x, swapped = np.asarray(x), np.asarray(swapped)
    status, owner = np.asarray(status), np.asarray(owner)
    if x.shape != swapped.shape or x.shape != (len(status), len(names)) or owner.shape != status.shape:
        raise ValueError('training dimensions differ')
    if not np.isfinite(x).all() or not np.isfinite(swapped).all():
        raise ValueError('nonfinite training evidence')
    if not np.isin(status, [-1, 0, 1]).all() or not np.isin(owner, [-1, 0, 1]).all():
        raise ValueError('invalid training labels')
    alive_rows = status >= 0
    owner_rows = (status == 1) & (owner >= 0)
    if set(status[alive_rows]) != {0, 1} or set(owner[owner_rows]) != {0, 1}:
        raise ValueError('training needs both alive/dead and home/away')
    a = HistGradientBoostingClassifier(**MODEL_SETTINGS)
    o = HistGradientBoostingClassifier(**MODEL_SETTINGS)
    a.fit(np.concatenate((x[alive_rows], swapped[alive_rows])), np.tile(status[alive_rows], 2))
    o.fit(np.concatenate((x[owner_rows], swapped[owner_rows])),
          np.concatenate((owner[owner_rows], 1 - owner[owner_rows])))
    return ContextHeads(a, o, tuple(names))


def emissions(model, context):
    if context.names != model.feature_names:
        raise ValueError('model feature schema mismatch')
    # Class order is validated by the fit requirements: sklearn classes_ = [0, 1].
    a = .5 * (model.alive.predict_proba(context.original)[:, 1] +
              model.alive.predict_proba(context.swapped)[:, 1])
    h = .5 * (model.owner.predict_proba(context.original)[:, 0] +
              model.owner.predict_proba(context.swapped)[:, 1])
    p = np.column_stack((a * h, a * (1 - h), 1 - a))
    return np.log(np.maximum(p, 1e-9))


def decode(log_evidence, penalty, radius=0):
    if penalty < 0 or not np.isfinite(penalty):
        raise ValueError('invalid switch penalty')
    evidence = window_mean(log_evidence, radius)
    transitions = np.full((3, 3), -float(penalty))
    np.fill_diagonal(transitions, 0.)
    return viterbi_decode(evidence, transitions)
