"""Synthetic parser contracts for the public Sportec adapter."""

from dataclasses import fields

import numpy as np
import pytest

from malwarous.external_sportec import (
    AWAY,
    HOME,
    UNKNOWN,
    ExternalFeatures,
    load_sportec_match,
    read_sportec_team_map,
)


TEAM_MAP = {"H1": HOME, "A1": AWAY}


def _write_xml(path, body):
    path.write_text(f"<PutDataRequest>{body}</PutDataRequest>", encoding="utf-8")
    return path


def _frameset(section, object_id, frames, ball=False):
    attr = f'GameSection="{section}" ' + (f'TeamId="BALL"' if ball else f'PersonId="{object_id}"')
    return f"<FrameSet {attr}>{frames}</FrameSet>"


def test_period_and_frame_order_is_canonical_and_gaps_stay_unknown(tmp_path):
    # File order deliberately starts in period 2 and then reverses frame ids in period 1.
    body = "".join([
        _frameset("secondHalf", "", '<Frame N="100001" X="3" Y="4" BallStatus="1" BallPossession="2"/>', ball=True),
        _frameset("secondHalf", "A1", '<Frame N="100000" X="7" Y="8"/>'),
        _frameset("firstHalf", "", '<Frame N="100002" X="9" Y="9" BallStatus="0"/> <Frame N="100000" X="1" Y="2" BallStatus="1" BallPossession="1"/>', ball=True),
        _frameset("firstHalf", "H1", '<Frame N="100002" X="6" Y="7"/> <Frame N="100000" X="2" Y="3"/>'),
        _frameset("firstHalf", "A1", '<Frame N="100000" X="4" Y="5"/>'),
    ])
    match = load_sportec_match(_write_xml(tmp_path / "tracking.xml", body), TEAM_MAP)

    assert match.period_bounds == ((1, 100000, 100003), (2, 100000, 100002))
    first, second = match.features
    assert first.frame_ids.tolist() == [100000, 100001, 100002]
    assert first.player_ids == ("H1", "A1")
    assert first.player_xy[0, 0].tolist() == [2.0, 3.0]
    assert first.player_xy[0, 1].tolist() == [4.0, 5.0]
    assert np.isnan(first.player_xy[1]).all()
    assert np.isnan(first.ball_xy[1]).all()
    assert second.frame_ids.tolist() == [100000, 100001]
    assert np.isnan(second.ball_xy[0]).all()
    assert second.ball_xy[1].tolist() == [3.0, 4.0]
    assert match.labels[1].ball_owner.tolist() == [UNKNOWN, 1]


def test_missing_status_owner_and_coordinates_remain_missing(tmp_path):
    body = "".join([
        _frameset("firstHalf", "", '<Frame N="100010" BallStatus="1"/>', ball=True),
        _frameset("firstHalf", "H1", '<Frame N="100010" X="2"/>'),
    ])
    match = load_sportec_match(_write_xml(tmp_path / "missing.xml", body), TEAM_MAP)

    labels = match.labels[0]
    features = match.features[0]
    assert labels.ball_status.tolist() == [1]
    assert labels.ball_owner.tolist() == [UNKNOWN]
    assert labels.possession_targets().tolist() == [UNKNOWN]
    assert np.isnan(features.player_xy[0, 0]).all()
    assert np.isnan(features.ball_xy[0]).all()


@pytest.mark.parametrize(
    "attribute,value",
    [("BallPossession", "3"), ("BallPossession", "0"), ("BallStatus", "2")],
)
def test_unsupported_label_codes_fail_closed(tmp_path, attribute, value):
    body = _frameset("firstHalf", "", f'<Frame N="1" {attribute}="{value}"/>', ball=True)
    with pytest.raises(ValueError, match="unsupported"):
        load_sportec_match(_write_xml(tmp_path / "bad-label.xml", body), TEAM_MAP)


def test_feature_contract_has_no_label_columns_or_attributes(tmp_path):
    body = _frameset("firstHalf", "", '<Frame N="42" X="1" Y="2" BallStatus="1" BallPossession="1"/>', ball=True)
    match = load_sportec_match(_write_xml(tmp_path / "separation.xml", body), TEAM_MAP)
    features = match.features[0]
    feature_names = {field.name for field in fields(ExternalFeatures)}

    assert feature_names == {"period_id", "frame_ids", "player_ids", "team_by_player", "player_xy", "ball_xy"}
    assert not hasattr(features, "ball_status")
    assert not hasattr(features, "ball_owner")
    assert match.labels[0].possession_targets().tolist() == [0]


def test_metadata_roster_maps_home_and_guest_players(tmp_path):
    metadata = """<PutDataRequest><MatchInformation><Teams>
      <Team Role="guest"><Players><Player PersonId="A1"/></Players></Team>
      <Team Role="home"><Players><Player PersonId="H1"/></Players></Team>
    </Teams></MatchInformation></PutDataRequest>"""
    path = tmp_path / "metadata.xml"
    path.write_text(metadata, encoding="utf-8")

    assert read_sportec_team_map(path) == {"A1": AWAY, "H1": HOME}


def test_duplicate_player_frame_is_rejected(tmp_path):
    body = "".join([
        _frameset("firstHalf", "H1", '<Frame N="7" X="1" Y="1"/>'),
        _frameset("firstHalf", "H1", '<Frame N="7" X="2" Y="2"/>'),
    ])
    with pytest.raises(ValueError, match="duplicate"):
        load_sportec_match(_write_xml(tmp_path / "duplicate.xml", body), TEAM_MAP)
