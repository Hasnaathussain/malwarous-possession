"""Synthetic contracts for Metrica metadata and raw tracking ingestion."""

import numpy as np
import pytest

from malwarous.metrica_ingest import load_metrica_tracking, team_slots_from_metadata


def _write_meta(path, body):
    path.write_text(f"<Root>{body}</Root>", encoding="utf-8")
    return path


def _write_raw(path, rows):
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_metadata_maps_ordered_slots_to_sides_without_using_names(tmp_path):
    meta = _write_meta(tmp_path / "metadata.xml", """
      <Team id="H"><Name>Home</Name></Team><Team id="A"><Name>Away</Name></Team>
      <Player teamId="A"/><Player teamId="H"/><Player teamId="A"/>
    """)
    assert team_slots_from_metadata(meta).tolist() == [1, 0, 1]


def test_streaming_parser_aligns_frames_and_scales_coordinates(tmp_path):
    meta = _write_meta(tmp_path / "metadata.xml", """
      <Team id="H"/><Team id="A"/><Player teamId="H"/><Player teamId="A"/>
    """)
    teams = team_slots_from_metadata(meta)
    raw = _write_raw(tmp_path / "tracking.txt", [
        "1:0.5,0.25,2.0;0.25,0.5,3.0:0.2,0.4,9.0",
        "2:NaN,NaN,NaN;0.3,0.6,4.0:NaN,NaN,NaN",
    ])
    result = load_metrica_tracking(raw, teams, n_frames=2, pitch=(100.0, 50.0))

    assert result.frame.tolist() == [0, 1]
    assert result.team_by_slot.tolist() == [0, 1]
    assert result.player_xy[0].tolist() == [[50.0, 12.5], [25.0, 25.0]]
    assert result.player_speed[0].tolist() == [2.0, 3.0]
    assert result.ball_xy[0].tolist() == [20.0, 20.0]
    assert np.isnan(result.player_xy[1, 0]).all()
    assert np.isnan(result.ball_xy[1]).all()


@pytest.mark.parametrize("rows,n_frames", [
    (["1:0,0,0:0,0,0", "3:0,0,0:0,0,0"], 2),
    (["2:0,0,0:0,0,0"], 1),
    (["1:0,0,0:0,0,0"], 2),
    (["1:0,0,0:0,0,0", "2:0,0,0:0,0,0"], 1),
])
def test_rejects_frame_id_and_row_count_mismatches(tmp_path, rows, n_frames):
    raw = _write_raw(tmp_path / "tracking.txt", rows)
    with pytest.raises(ValueError):
        load_metrica_tracking(raw, np.array([0], dtype=np.int8), n_frames=n_frames, pitch=(100, 50))


def test_rejects_track_slot_mismatch_and_malformed_group(tmp_path):
    raw = _write_raw(tmp_path / "tracking.txt", ["1:0,0,0;0,0,0:0,0,0"])
    with pytest.raises(ValueError, match="slot count"):
        load_metrica_tracking(raw, np.array([0], dtype=np.int8), n_frames=1, pitch=(100, 50))

    bad = _write_raw(tmp_path / "bad.txt", ["1:0,0;0,0,0:0,0,0"])
    with pytest.raises(ValueError, match="x, y and speed"):
        load_metrica_tracking(bad, np.array([0, 1], dtype=np.int8), n_frames=1, pitch=(100, 50))


def test_nonfinite_values_become_missing_and_nonfinite_speed_stays_missing(tmp_path):
    raw = _write_raw(tmp_path / "tracking.txt", ["1:Infinity,0.1,NaN:0.5,0.5,Infinity"])
    result = load_metrica_tracking(raw, np.array([0], dtype=np.int8), n_frames=1, pitch=(100, 50))
    assert np.isnan(result.player_xy[0, 0]).all()
    assert np.isnan(result.player_speed[0, 0])
    assert result.ball_xy[0].tolist() == [50.0, 25.0]
    assert np.isnan(result.ball_speed[0])


def test_utf8_bom_and_out_of_range_team_values_are_handled_safely(tmp_path):
    meta = tmp_path / "metadata.xml"
    meta.write_text("\ufeff<Root><Team id='H'/><Team id='A'/><Player teamId='H'/></Root>", encoding="utf-8")
    assert team_slots_from_metadata(meta).tolist() == [0]

    raw = _write_raw(tmp_path / "tracking.txt", ["1:0,0,0:0,0,0"])
    with pytest.raises(ValueError, match="team vector"):
        load_metrica_tracking(raw, np.array([256]), n_frames=1, pitch=(100, 50))


def test_negative_speed_is_marked_missing_not_as_physical_motion(tmp_path):
    raw = _write_raw(tmp_path / "tracking.txt", ["1:0,0,-1:0,0,-2"])
    result = load_metrica_tracking(raw, np.array([0]), n_frames=1, pitch=(100, 50))
    assert np.isnan(result.player_speed[0, 0])
    assert np.isnan(result.ball_speed[0])


def test_metadata_rejects_unknown_team_id(tmp_path):
    meta = _write_meta(tmp_path / "bad.xml", """
      <Team id="H"/><Team id="A"/><Player teamId="X"/>
    """)
    with pytest.raises(ValueError, match="team mapping"):
        team_slots_from_metadata(meta)
