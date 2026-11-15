"""Synthetic tests for deterministic H/A/D Viterbi decoding."""

import numpy as np
import pytest

from malwarous.temporal import UNDECODED, viterbi_decode


def _emissions(states, margin=8.0):
    result = np.full((len(states), 3), -margin, dtype=np.float64)
    for frame, state in enumerate(states):
        result[frame, state] = 0.0
    return result


def test_exact_evidence_path_without_transition_cost():
    expected = np.array([0, 0, 1, 1, 2, 2], dtype=np.int8)
    assert np.array_equal(viterbi_decode(_emissions(expected), np.zeros((3, 3))), expected)


def test_transition_cost_suppresses_weak_one_frame_flicker():
    emissions = np.zeros((5, 3), dtype=np.float64)
    emissions[:, 2] = -20.0
    emissions[:, 0] = 0.5
    emissions[1, 1] = 0.8
    emissions[3, 1] = 0.8
    transitions = np.full((3, 3), -2.0)
    np.fill_diagonal(transitions, 0.0)

    assert np.array_equal(viterbi_decode(emissions, transitions), np.zeros(5, dtype=np.int8))


def test_strong_evidence_overrides_switch_cost():
    emissions = np.zeros((5, 3), dtype=np.float64)
    emissions[:, 2] = -20.0
    emissions[:, 0] = 4.0
    emissions[2, 1] = 10.0
    transitions = np.full((3, 3), -2.0)
    np.fill_diagonal(transitions, 0.0)

    assert viterbi_decode(emissions, transitions).tolist() == [0, 0, 1, 0, 0]


def test_one_frame_possession_is_preserved_when_supported():
    states = np.array([0, 0, 1, 0, 0], dtype=np.int8)
    emissions = _emissions(states, margin=5.0)
    transitions = np.full((3, 3), -2.0)
    np.fill_diagonal(transitions, 0.0)

    assert viterbi_decode(emissions, transitions).tolist() == states.tolist()


def test_segments_decode_independently_and_leave_other_frames_undecoded():
    emissions = _emissions([0, 0, 1, 1, 2, 2])
    # This transition matrix forbids H->A. The two separate segments can still start in H then A.
    transitions = np.zeros((3, 3), dtype=np.float64)
    transitions[0, 1] = -np.inf

    decoded = viterbi_decode(emissions, transitions, segments=[(3, 4), (0, 2), (5, 5)])
    assert decoded.tolist() == [0, 0, UNDECODED, 1, UNDECODED, UNDECODED]


def test_ties_are_deterministic_and_choose_lowest_state_index():
    emissions = np.zeros((8, 3), dtype=np.float64)
    transitions = np.zeros((3, 3), dtype=np.float64)

    first = viterbi_decode(emissions, transitions)
    second = viterbi_decode(emissions, transitions)
    assert np.array_equal(first, np.zeros(8, dtype=np.int8))
    assert np.array_equal(first, second)


def test_empty_sequences_and_empty_segments_are_valid():
    transitions = np.zeros((3, 3), dtype=np.float64)
    assert viterbi_decode(np.empty((0, 3)), transitions).shape == (0,)
    assert viterbi_decode(np.zeros((3, 3)), transitions, segments=[]).tolist() == [
        UNDECODED, UNDECODED, UNDECODED,
    ]
    assert viterbi_decode(np.zeros((3, 3)), transitions, segments=[(0, 0), (3, 3)]).tolist() == [
        UNDECODED, UNDECODED, UNDECODED,
    ]


@pytest.mark.parametrize("bad", [
    np.zeros(3),
    np.zeros((2, 4)),
    np.array([[0.0, np.nan, 0.0]]),
    np.array([[0.0, np.inf, 0.0]]),
])
def test_malformed_emissions_are_rejected(bad):
    with pytest.raises(ValueError):
        viterbi_decode(bad, np.zeros((3, 3)))


@pytest.mark.parametrize("bad_transition", [
    np.zeros((2, 2)),
    np.array([[0.0, np.nan, 0.0]] * 3),
    np.array([[0.0, np.inf, 0.0]] * 3),
])
def test_malformed_transition_scores_are_rejected(bad_transition):
    with pytest.raises(ValueError):
        viterbi_decode(np.zeros((2, 3)), bad_transition)


@pytest.mark.parametrize("segments", [
    [(0, 3), (2, 4)],  # overlap
    [(-1, 1)],
    [(0, 5)],
    [(2, 1)],
    [(0.0, 1)],
    [(True, 1)],
    [(0,)],
])
def test_malformed_segments_are_rejected(segments):
    with pytest.raises(ValueError):
        viterbi_decode(np.zeros((4, 3)), np.zeros((3, 3)), segments)


def test_forbidden_state_and_forbidden_transition_are_respected():
    emissions = np.array([[0.0, -np.inf, -np.inf], [0.0, 0.0, -np.inf]])
    transitions = np.zeros((3, 3))
    transitions[0, 1] = -np.inf

    assert viterbi_decode(emissions, transitions).tolist() == [0, 0]


def test_impossible_frame_or_path_fails_instead_of_inventing_a_state():
    transitions = np.full((3, 3), -np.inf)
    transitions[np.diag_indices(3)] = 0.0
    with pytest.raises(ValueError, match="admissible"):
        viterbi_decode(np.full((1, 3), -np.inf), transitions)
    impossible = np.full((2, 3), -np.inf)
    impossible[0, 0] = 0.0
    impossible[1, 1] = 0.0
    with pytest.raises(ValueError, match="admissible state path"):
        viterbi_decode(impossible, transitions)
