"""Synthetic feature tests for missingness, control geometry and side symmetry."""

import numpy as np
import pytest

from malwarous.features import FEATURE_NAMES, build_features, swap_home_away_features


IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}


def test_features_use_metric_geometry_and_never_turn_missing_into_origin():
    players = np.array([[[11.0, 10.0], [13.0, 10.0]]], dtype=np.float32)
    ball = np.array([[10.0, 10.0]], dtype=np.float32)
    features = build_features(players, [0, 1], ball, player_speed=[[3.0, 4.0]], pitch=(100, 50))

    assert features.shape == (1, len(FEATURE_NAMES))
    assert features[0, IDX["ball_observed"]] == 1
    assert features[0, IDX["home_nearest_distance_m"]] == 1
    assert features[0, IDX["away_nearest_distance_m"]] == 3
    assert features[0, IDX["home_minus_away_distance_m"]] == -2
    assert features[0, IDX["home_players_within_1m"]] == 1
    assert features[0, IDX["away_players_within_2m"]] == 0
    assert features[0, IDX["home_nearest_player_speed_mps"]] == 3


def test_ball_missingness_and_age_are_explicit_and_temporal_state_resets_per_segment():
    players = np.zeros((5, 2, 2), dtype=np.float32)
    ball = np.array([[1, 1], [np.nan, np.nan], [np.nan, np.nan], [3, 1], [np.nan, np.nan]], dtype=np.float32)
    features = build_features(players, [0, 1], ball, pitch=(10, 5), fps=1, segments=[(0, 3), (3, 5)])

    assert features[1, IDX["ball_observed"]] == 0
    assert features[1, IDX["ball_age_seconds"]] == 1
    assert features[2, IDX["ball_age_seconds"]] == 2
    assert features[3, IDX["ball_age_seconds"]] == 0
    assert features[4, IDX["ball_age_seconds"]] == 1
    assert features[3, IDX["ball_motion_valid"]] == 0
    assert np.all(np.isfinite(features))


def test_ball_motion_uses_only_short_observation_gaps():
    players = np.zeros((4, 2, 2), dtype=np.float32)
    ball = np.array([[0, 0], [1, 0], [np.nan, np.nan], [3, 0]], dtype=np.float32)
    features = build_features(players, [0, 1], ball, pitch=(10, 5), fps=1, max_motion_gap_frames=2)

    assert features[1, IDX["ball_motion_valid"]] == 1
    assert features[1, IDX["ball_motion_speed_mps"]] == 1
    assert features[3, IDX["ball_motion_valid"]] == 1
    assert features[3, IDX["ball_motion_speed_mps"]] == 1


def test_team_swap_is_exact_equivariance_for_all_feature_columns():
    players = np.array([[[4, 2], [8, 3], [7, 6], [1, 4]]], dtype=np.float32)
    speed = np.array([[3, 4, 2, 5]], dtype=np.float32)
    ball = np.array([[5, 3]], dtype=np.float32)
    original = build_features(players, [0, 0, 1, 1], ball, player_speed=speed, pitch=(10, 8))
    exchanged = build_features(players, [1, 1, 0, 0], ball, player_speed=speed, pitch=(10, 8))

    assert np.array_equal(swap_home_away_features(original), exchanged)


def test_features_exclude_ids_labels_and_absolute_coordinates():
    assert all("owner" not in name.lower() and "status" not in name.lower() for name in FEATURE_NAMES)
    assert not any(name in FEATURE_NAMES for name in ("frame_id", "player_id", "ball_x", "ball_y"))
    features = build_features(np.zeros((1, 2, 2)), [0, 1], np.zeros((1, 2)))
    assert np.isfinite(features).all()


def test_rejects_invalid_shapes_or_overlapping_segments():
    with pytest.raises(ValueError):
        build_features(np.zeros((2, 1, 2)), [0], np.zeros((1, 2)))
    with pytest.raises(ValueError, match="both teams"):
        build_features(np.zeros((1, 1, 2)), [0], np.zeros((1, 2)))
    with pytest.raises(ValueError, match="disjoint"):
        build_features(np.zeros((4, 2, 2)), [0, 1], np.zeros((4, 2)), segments=[(0, 3), (2, 4)])
    with pytest.raises(ValueError, match="integers"):
        build_features(np.zeros((1, 2, 2)), [0, 1], np.zeros((1, 2)), max_motion_gap_frames=1.5)
