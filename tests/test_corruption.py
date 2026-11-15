"""Synthetic checks that external observation corruption is deterministic and label-blind."""

import numpy as np
import pytest

from malwarous.corruption import block_mask, mask_ball_observations
from malwarous.external_sportec import ExternalFeatures


def _features(n=100):
    return ExternalFeatures(
        period_id=1,
        frame_ids=np.arange(n, dtype=np.int32),
        player_ids=("p1", "p2"),
        team_by_player=np.array([0, 1], dtype=np.int8),
        player_xy=np.ones((n, 2, 2), dtype=np.float32),
        ball_xy=np.ones((n, 2), dtype=np.float32),
    )


def test_exact_mask_fraction_and_deterministic_seed():
    first = block_mask(1000, 0.4, 20271113, mean_block_frames=8)
    second = block_mask(1000, 0.4, 20271113, mean_block_frames=8)
    assert np.array_equal(first, second)
    assert np.count_nonzero(first) == 400
    assert np.any(first[:-1] & first[1:])


def test_mask_copies_only_ball_positions_and_keeps_frame_keys():
    source = _features(100)
    corrupted = mask_ball_observations(source, fraction=0.4, seed=7)
    assert np.array_equal(corrupted.frame_ids, source.frame_ids)
    assert np.array_equal(corrupted.player_xy, source.player_xy)
    assert np.count_nonzero(~np.isfinite(corrupted.ball_xy[:, 0])) == 40
    assert np.count_nonzero(np.isfinite(source.ball_xy[:, 0])) == 100


@pytest.mark.parametrize("n,fraction,mean", [(-1, 0.2, 8), (10, -0.1, 8), (10, 1.1, 8), (10, 0.5, 0)])
def test_invalid_corruption_settings_fail_closed(n, fraction, mean):
    with pytest.raises(ValueError):
        block_mask(n, fraction, seed=1, mean_block_frames=mean)


def test_no_corruption_and_full_corruption_are_exact():
    assert not block_mask(10, 0, 1).any()
    assert block_mask(10, 1, 1).all()
