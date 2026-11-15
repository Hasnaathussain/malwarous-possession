"""Deterministic three-state Viterbi decoder for framewise log evidence.

State columns are fixed as H=0, A=1, D=2. Transition scores are indexed
``[previous_state, next_state]``. Explicit segments are decoded independently; frames outside
them remain -1 in the returned array.
"""

from __future__ import annotations

from operator import index
from typing import Iterable, Sequence

import numpy as np


N_STATES = 3
UNDECODED = -1


def _score_matrix(value: object, name: str, expected_shape: tuple[int, int]) -> np.ndarray:
    try:
        matrix = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a numeric matrix") from exc
    if matrix.shape != expected_shape:
        raise ValueError(f"{name} must have shape {expected_shape}")
    if np.isnan(matrix).any() or np.isposinf(matrix).any():
        raise ValueError(f"{name} cannot contain NaN or positive infinity")
    return matrix


def _normalize_segments(
    segments: Iterable[tuple[int, int]] | None,
    n_frames: int,
) -> list[tuple[int, int]]:
    if segments is None:
        return [(0, n_frames)] if n_frames else []

    normalized: list[tuple[int, int]] = []
    try:
        for item in segments:
            if isinstance(item, (str, bytes)):
                raise ValueError("each segment must be a (start, stop) pair")
            pair = tuple(item)
            if len(pair) != 2:
                raise ValueError("each segment must be a (start, stop) pair")
            if isinstance(pair[0], (bool, np.bool_)) or isinstance(pair[1], (bool, np.bool_)):
                raise ValueError("segment bounds must be integers")
            start, stop = index(pair[0]), index(pair[1])
            if start < 0 or stop < start or stop > n_frames:
                raise ValueError("segment must satisfy 0 <= start <= stop <= n_frames")
            normalized.append((start, stop))
    except TypeError as exc:
        raise ValueError("segments must be an iterable of integer pairs") from exc

    nonempty = sorted((start, stop) for start, stop in normalized if start < stop)
    for (_, prior_stop), (start, _) in zip(nonempty, nonempty[1:]):
        if start < prior_stop:
            raise ValueError("nonempty segments must be disjoint")
    return sorted(normalized)


def _decode_one(
    emissions: np.ndarray,
    transition_scores: np.ndarray,
) -> np.ndarray:
    """Decode a nonempty segment. Ties resolve to the lower state index."""
    n_frames = emissions.shape[0]
    backpointers = np.empty((n_frames, N_STATES), dtype=np.int8)
    previous = emissions[0].copy()  # equal start-state prior for H, A and D
    if np.all(np.isneginf(previous)):
        raise ValueError("frame has no admissible state")

    for frame in range(1, n_frames):
        with np.errstate(over="ignore", invalid="ignore"):
            candidates = previous[:, None] + transition_scores
        best_previous = np.argmax(candidates, axis=0)
        best_score = candidates[best_previous, np.arange(N_STATES)]
        with np.errstate(over="ignore", invalid="ignore"):
            current = best_score + emissions[frame]
        if np.isnan(current).any() or np.isposinf(current).any():
            raise ValueError("decoder score overflow")
        if np.all(np.isneginf(current)):
            raise ValueError("no admissible state path through segment")
        backpointers[frame] = best_previous.astype(np.int8)
        previous = current

    state = int(np.argmax(previous))
    path = np.empty(n_frames, dtype=np.int8)
    path[-1] = state
    for frame in range(n_frames - 1, 0, -1):
        state = int(backpointers[frame, state])
        path[frame - 1] = state
    return path


def viterbi_decode(
    log_emissions: object,
    transition_log_scores: object,
    segments: Sequence[tuple[int, int]] | None = None,
) -> np.ndarray:
    """Return the best H/A/D state sequence for each independent segment.

    Args:
        log_emissions: ``[N, 3]`` frame/state scores, with columns H, A, D. ``-inf`` forbids
            a state at a frame. Every decoded frame must retain at least one admissible state.
        transition_log_scores: ``[3, 3]`` scores indexed ``[previous, next]``. ``-inf`` forbids
            that transition. The same matrix is used independently within every segment.
        segments: optional half-open ``(start, stop)`` frame intervals. Intervals may be supplied
            in any order but nonempty intervals cannot overlap. Each interval starts with an equal
            prior over its three states. Frames outside intervals are returned as ``-1``.

    Ties deterministically choose the lowest state index. Empty intervals are accepted and have
    no effect. If ``segments`` is omitted, the full sequence is one segment. The decoder applies
    no minimum-duration or target-specific filtering.
    """
    emissions = np.asarray(log_emissions, dtype=np.float64)
    if emissions.ndim != 2 or emissions.shape[1] != N_STATES:
        raise ValueError("log_emissions must have shape [N, 3] for H, A, D")
    if np.isnan(emissions).any() or np.isposinf(emissions).any():
        raise ValueError("log_emissions cannot contain NaN or positive infinity")
    transitions = _score_matrix(transition_log_scores, "transition_log_scores", (N_STATES, N_STATES))
    normalized = _normalize_segments(segments, emissions.shape[0])

    result = np.full(emissions.shape[0], UNDECODED, dtype=np.int8)
    for start, stop in normalized:
        if start == stop:
            continue
        result[start:stop] = _decode_one(emissions[start:stop], transitions)
    return result
