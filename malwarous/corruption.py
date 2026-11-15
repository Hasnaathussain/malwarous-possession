"""Label-independent observation dropout for external robustness checks."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .external_sportec import ExternalFeatures


def block_mask(n_frames: int, fraction: float, seed: int, mean_block_frames: float = 8.0) -> np.ndarray:
    """Return an exact-size dropout mask made from random contiguous blocks.

    The generator uses only match/period seed and configuration. It does not accept or inspect any
    labels, events, model output, or target-match content.
    """
    if n_frames < 0:
        raise ValueError("n_frames cannot be negative")
    if not np.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("fraction must be in [0, 1]")
    if not np.isfinite(mean_block_frames) or mean_block_frames < 1:
        raise ValueError("mean_block_frames must be at least one")
    target = int(round(n_frames * fraction))
    mask = np.zeros(n_frames, dtype=np.bool_)
    if target == 0:
        return mask
    if target == n_frames:
        mask[:] = True
        return mask

    rng = np.random.default_rng(seed)
    probability = 1.0 / mean_block_frames
    selected = 0
    starts = rng.permutation(n_frames)
    cursor = 0
    while selected < target:
        if cursor < n_frames:
            start = int(starts[cursor])
            cursor += 1
        else:
            start = int(rng.integers(0, n_frames))
        length = int(rng.geometric(probability))
        stop = min(n_frames, start + length)
        for frame in range(start, stop):
            if not mask[frame]:
                mask[frame] = True
                selected += 1
                if selected == target:
                    break
    return mask


def mask_ball_observations(
    features: ExternalFeatures,
    *,
    fraction: float,
    seed: int,
    mean_block_frames: float = 8.0,
) -> ExternalFeatures:
    """Copy a feature record with only a label-independent fraction of ball XY hidden."""
    n_frames = len(features.frame_ids)
    if features.ball_xy.shape != (n_frames, 2):
        raise ValueError("ball coordinates must align to frame ids")
    if features.player_xy.shape[0] != n_frames:
        raise ValueError("player coordinates must align to frame ids")
    mask = block_mask(n_frames, fraction, seed, mean_block_frames)
    ball_xy = features.ball_xy.copy()
    ball_xy[mask] = np.nan
    return replace(features, player_xy=features.player_xy, ball_xy=ball_xy)
