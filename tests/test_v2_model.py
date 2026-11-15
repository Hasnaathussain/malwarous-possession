"""Small synthetic contracts for the v2 observation-only model and study."""

from __future__ import annotations

import inspect

import numpy as np

from malwarous.features import FEATURE_NAMES
from malwarous.v2 import study
from malwarous.v2.model import (
    BASE_INDEX,
    ContextFeatures,
    build_context,
    decode,
    emissions,
    fit_heads,
    window_mean,
)


def _tracking_fixture(n=12):
    """Return observations with both ball and player missingness and unambiguous geometry."""
    ball = np.column_stack((np.arange(n, dtype=float), np.zeros(n)))
    players = np.empty((n, 4, 2), dtype=float)
    offsets = np.array([[-0.5, 0.0], [-1.5, 0.0], [0.5, 0.0], [1.5, 0.0]])
    players[:] = ball[:, None, :] + offsets[None, :, :]
    ball[[3, 8]] = np.nan
    players[5, 0] = np.nan
    players[7, 2:] = np.nan
    # At frame 6 one team has no tracked players; the other still has support.
    players[6, :2] = np.nan
    return players, np.array([0, 0, 1, 1]), ball


def test_context_is_equivariant_to_home_away_swap_even_with_missing_geometry():
    players, teams, ball = _tracking_fixture()
    context = build_context(players, teams, ball)
    exchanged = build_context(players, 1 - teams, ball)

    np.testing.assert_allclose(context.swapped, exchanged.original, rtol=0, atol=1e-6)
    np.testing.assert_allclose(context.original, exchanged.swapped, rtol=0, atol=1e-6)
    assert np.isfinite(context.original).all()
    support_i = context.names.index("geometry_supported")
    assert context.original[[3, 8], support_i].tolist() == [0.0, 0.0]
    assert context.original[6, support_i] == 0.0


def test_context_is_invariant_to_anonymous_player_slot_order():
    players, teams, ball = _tracking_fixture()
    expected = build_context(players, teams, ball)
    order = np.array([3, 0, 2, 1])
    permuted = build_context(players[:, order], teams[order], ball)

    np.testing.assert_allclose(expected.base, permuted.base, rtol=0, atol=1e-6)
    np.testing.assert_allclose(expected.original, permuted.original, rtol=0, atol=1e-6)
    np.testing.assert_allclose(expected.swapped, permuted.swapped, rtol=0, atol=1e-6)


def test_context_inputs_and_schema_expose_observations_not_targets_or_identifiers():
    parameters = set(inspect.signature(build_context).parameters)
    assert not parameters.intersection({"status", "owner", "labels", "frame_ids", "match_id"})

    players, teams, ball = _tracking_fixture()
    names = build_context(players, teams, ball).names
    forbidden = ("status", "owner", "label", "target", "match_id", "frame_id", "timestamp")
    assert not any(token in name.lower() for name in names for token in forbidden)
    assert names[: len(FEATURE_NAMES)] == FEATURE_NAMES


def test_control_propagation_stops_after_five_seconds_of_unobserved_geometry():
    n = 302
    ball = np.full((n, 2), np.nan)
    players = np.full((n, 4, 2), np.nan)
    # Positive signed control means home is closer; the distant endpoints bracket a long outage.
    for frame, home_distance, away_distance in ((0, 0.5, 1.5), (300, 1.5, 0.5)):
        ball[frame] = (0.0, 0.0)
        players[frame, 0] = (home_distance, 0.0)
        players[frame, 1] = (home_distance + 0.5, 0.0)
        players[frame, 2] = (away_distance, 0.0)
        players[frame, 3] = (away_distance + 0.5, 0.0)
    context = build_context(players, np.array([0, 0, 1, 1]), ball)
    col = {name: i for i, name in enumerate(context.names)}
    x = context.original

    assert x[125, col["previous_control_supported"]] == 1.0  # exactly five seconds old
    assert x[125, col["previous_control"]] == 1.0
    assert x[126, col["previous_control_supported"]] == 0.0
    assert x[126, col["next_control_supported"]] == 0.0
    assert x[174, col["next_control_supported"]] == 0.0
    assert x[175, col["next_control_supported"]] == 1.0  # exactly five seconds ahead
    assert x[175, col["next_control"]] == -1.0


def test_weighted_window_mean_uses_observed_support_and_truncated_edges():
    values = np.array([10.0, 999.0, 30.0, 40.0, 88.0])
    observed = np.array([1.0, 0.0, 1.0, 1.0, 0.0])

    result = window_mean(values, radius=1, weights=observed)
    np.testing.assert_allclose(result, [10.0, 20.0, 35.0, 35.0, 40.0])
    np.testing.assert_array_equal(window_mean(values, 2, np.zeros(5)), np.zeros(5))


def test_decoder_keeps_a_short_strong_spell_and_rejects_a_weak_flicker():
    evidence = np.full((10, 3), -20.0)
    evidence[:, 0] = 0.0
    evidence[:, 1] = -3.0
    evidence[:, 2] = -10.0
    evidence[2, 1] = 2.0  # one-frame local preference is weaker than two switch costs
    evidence[6:9, 1] = 6.0  # three-frame spell has enough total evidence to pay both costs

    predicted = decode(evidence, penalty=3, radius=0)
    assert predicted[2] == 0
    assert predicted[6:9].tolist() == [1, 1, 1]
    assert predicted[[0, 1, 3, 4, 5, 9]].tolist() == [0, 0, 0, 0, 0, 0]


def test_decoder_calls_start_halves_with_independent_state_priors():
    first_half = np.tile(np.array([-10.0, 0.0, -20.0]), (5, 1))
    second_half = np.array(
        [
            [0.0, -3.0, -20.0],
            [0.0, -3.0, -20.0],
            [0.0, 10.0, -20.0],
            [0.0, 10.0, -20.0],
            [0.0, 10.0, -20.0],
        ]
    )

    second_prediction = decode(second_half, penalty=4, radius=0)
    joined_prediction = decode(np.concatenate((first_half, second_half)), penalty=4, radius=0)
    assert second_prediction[:2].tolist() == [0, 0]
    assert joined_prediction[len(first_half)] == 1


def test_building_a_half_starts_ball_motion_and_age_without_prior_half_context():
    teams = np.array([0, 0, 1, 1])
    first_ball = np.array([[0.0, 0.0], [1.0, 0.0]])
    first_players = np.tile(np.array([[-1.0, 0.0], [-2.0, 0.0], [1.0, 0.0], [2.0, 0.0]]), (2, 1, 1))
    second_ball = np.array([[np.nan, np.nan], [100.0, 0.0], [101.0, 0.0]])
    second_players = np.tile(np.array([[99.0, 0.0], [98.0, 0.0], [101.0, 0.0], [102.0, 0.0]]), (3, 1, 1))

    first = build_context(first_players, teams, first_ball)
    second = build_context(second_players, teams, second_ball)
    motion_i = BASE_INDEX["ball_motion_valid"]
    age_i = BASE_INDEX["ball_age_seconds"]
    assert first.base[-1, motion_i] == 1.0
    assert second.base[0, age_i] == 5.0
    assert second.base[1, motion_i] == 0.0


def test_fit_and_emissions_keep_the_natural_alive_prior_and_normalize_states():
    n = 120
    x = np.zeros((n, 2), dtype=np.float32)
    status = np.array([1] * 24 + [0] * 96, dtype=np.int8)
    owner = np.full(n, -1, dtype=np.int8)
    owner[:24] = [0] * 21 + [1] * 3
    names = ("observation_a", "observation_b")

    model = fit_heads(x, x.copy(), status, owner, names)
    context = ContextFeatures(x[:4], x[:4].copy(), names, np.zeros((4, 1)))
    probabilities = np.exp(emissions(model, context))

    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0, atol=1e-7)
    np.testing.assert_allclose(probabilities[:, :2].sum(axis=1), 0.2, atol=0.02)
    np.testing.assert_allclose(probabilities[:, 0], probabilities[:, 1], atol=1e-7)


def test_study_folds_hold_out_complete_match_pairs():
    groups = [set(pair) for pair in study.PAIRS]
    all_matches = set().union(*groups)
    assert len(all_matches) == sum(map(len, groups))

    for test_group in groups:
        test_matches = set(test_group)
        train_matches = all_matches - test_matches
        assert not train_matches.intersection(test_matches)
        assert all(group == test_group or group.issubset(train_matches) for group in groups)


def _summary_rows(per_match_delta, *, close_candidate_delta=None):
    rows = []
    matches = [match for pair in study.PAIRS for match in pair]
    scenarios = [scenario for scenario, _, _ in study.SCENARIOS]
    candidates = [candidate["name"] for candidate in study.CANDIDATES]
    for match_i, match in enumerate(matches):
        baseline = 0.5
        for scenario in scenarios:
            rows.append(dict(candidate="v1_smooth50", match=match, scenario=scenario,
                             spell_f1_mean=baseline, macro_f1=0.6))
            for candidate in candidates:
                delta = per_match_delta[match_i]
                macro = 0.7
                if candidate == "context_p25_r0":
                    delta += 0.002
                    macro = 0.8
                elif candidate == "context_p10_r12" and close_candidate_delta is not None:
                    delta = close_candidate_delta[match_i]
                    macro = 0.9
                rows.append(dict(candidate=candidate, match=match, scenario=scenario,
                                 spell_f1_mean=baseline + delta, macro_f1=macro))
            rows.append(dict(candidate=study.DIAGNOSTIC["name"], match=match, scenario=scenario,
                             spell_f1_mean=baseline, macro_f1=0.6))
    return rows


def test_summary_selects_by_macro_within_tolerance_and_applies_replacement_gate():
    # The p10/r12 candidate is 0.002 below the best spell score, within the 0.005 tie band.
    deltas = [0.02] * 6
    close = [0.021] * 6
    result = study.summary(_summary_rows(deltas, close_candidate_delta=close))

    assert result["selected"] == "context_p10_r12"
    assert result["development_gate_passed"] is True
    assert all(row["mean_paired_spell_delta"] > 0 for row in result["paired_match_deltas"])


def test_summary_gate_rejects_an_aggregate_gain_with_a_bad_match():
    # Five +0.05 matches and one -0.06 match still clear +0.02 overall, but fail the
    # required worst-match floor of -0.05.
    deltas = [0.05] * 5 + [-0.06]
    result = study.summary(_summary_rows(deltas))

    selected = next(row for row in result["candidates"] if row["candidate"] == result["selected"])
    baseline = next(row for row in result["candidates"] if row["candidate"] == "v1_smooth50")
    assert selected["mean_spell_f1"] - baseline["mean_spell_f1"] > 0.02
    assert result["paired_match_deltas"][-1]["mean_paired_spell_delta"] < -0.05
    assert result["development_gate_passed"] is False
