"""Synthetic checks for pitch reflection symmetry and coordinate conventions."""

from __future__ import annotations

import numpy as np
import pytest

from malwarous.metrica_ingest import load_metrica_tracking
from malwarous.v2.model import build_context


def _centered_fixture():
    """Eight frames with asymmetric geometry and explicit missing observations."""
    ball = np.array(
        [
            [-18.0, -9.0],
            [-12.0, -6.0],
            [-6.0, -3.0],
            [0.0, 0.0],
            [6.0, 3.0],
            [12.0, 6.0],
            [18.0, 9.0],
            [24.0, 12.0],
        ],
        dtype=np.float32,
    )
    players = np.empty((8, 4, 2), dtype=np.float32)
    offsets = np.array(
        [[-1.0, 0.5], [-2.0, 1.0], [1.5, -0.5], [3.0, -1.0]],
        dtype=np.float32,
    )
    players[:] = ball[:, None, :] + offsets[None, :, :]
    ball[2] = np.nan
    players[5, 0] = np.nan
    players[6, 3] = np.nan
    return players, np.array([0, 0, 1, 1], dtype=np.int8), ball


@pytest.mark.parametrize("axis", [0, 1], ids=["longitudinal", "lateral"])
def test_context_is_invariant_to_reflecting_either_centered_pitch_axis(axis):
    players, teams, ball = _centered_fixture()
    reflected_players = players.copy()
    reflected_ball = ball.copy()
    reflected_players[:, :, axis] *= -1
    reflected_ball[:, axis] *= -1

    expected = build_context(players, teams, ball)
    reflected = build_context(reflected_players, teams, reflected_ball)

    np.testing.assert_allclose(reflected.base, expected.base, rtol=0, atol=1e-6)
    np.testing.assert_allclose(reflected.original, expected.original, rtol=0, atol=1e-6)
    np.testing.assert_allclose(reflected.swapped, expected.swapped, rtol=0, atol=1e-6)
    assert np.isfinite(reflected.original).all()
    assert np.isfinite(reflected.swapped).all()


def test_normalized_metrica_coordinates_match_centered_metre_coordinates(tmp_path):
    pitch = (105.0, 68.0)
    players_centered, teams, ball_centered = _centered_fixture()
    center = np.asarray(pitch, dtype=np.float32) / 2

    # The Metrica export stores normalized corner-origin coordinates. Convert the
    # synthetic centered metre fixture to that wire format, then ingest it through
    # the public parser before moving it back to pitch-centered metres.
    players_normalized = (players_centered + center) / np.asarray(pitch, dtype=np.float32)
    ball_normalized = (ball_centered + center) / np.asarray(pitch, dtype=np.float32)

    rows = []
    for frame in range(len(ball_centered)):
        encoded_players = []
        for slot in range(players_centered.shape[1]):
            x, y = players_normalized[frame, slot]
            encoded_players.append(f"{x},{y},NaN")
        x, y = ball_normalized[frame]
        rows.append(f"{frame + 1}:" + ";".join(encoded_players) + f":{x},{y},NaN")

    raw_path = tmp_path / "synthetic-normalized-tracking.txt"
    raw_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    metrica = load_metrica_tracking(
        raw_path,
        teams,
        n_frames=len(ball_centered),
        pitch=pitch,
    )

    metrica_centered_players = metrica.player_xy - center
    metrica_centered_ball = metrica.ball_xy - center
    parsed_context = build_context(metrica_centered_players, teams, metrica_centered_ball, pitch=pitch)
    direct_context = build_context(players_centered, teams, ball_centered, pitch=pitch)

    np.testing.assert_allclose(metrica_centered_players, players_centered, rtol=0, atol=1e-5, equal_nan=True)
    np.testing.assert_allclose(metrica_centered_ball, ball_centered, rtol=0, atol=1e-5, equal_nan=True)
    np.testing.assert_allclose(parsed_context.base, direct_context.base, rtol=0, atol=1e-5)
    np.testing.assert_allclose(parsed_context.original, direct_context.original, rtol=0, atol=1e-5)
    np.testing.assert_allclose(parsed_context.swapped, direct_context.swapped, rtol=0, atol=1e-5)
