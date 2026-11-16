import json
from pathlib import Path

import pytest

from scripts.export_public_site import (
    EXPECTED_SEQUENCE_IDS,
    _external_sequence,
    _intervals_to_frames,
    _validate_external_bundle,
    export_public_data,
)


def test_private_external_bundle_is_rejected_before_output_creation(tmp_path: Path) -> None:
    source = tmp_path / "private-source.json"
    source.write_text(json.dumps({"schema_version": "1.0", "dataset": {"kind": "private"}, "matches": []}), encoding="utf-8")
    output = tmp_path / "site-output"

    with pytest.raises(ValueError, match="public_external"):
        export_public_data(
            source,
            tmp_path / "intentionally-unavailable-synthetic-input",
            tmp_path / "intentionally-unavailable-benchmarks.json",
            output,
        )

    assert not output.exists()


def test_public_kind_with_unapproved_sequence_is_rejected(tmp_path: Path) -> None:
    bundle = {
        "schema_version": "1.0",
        "dataset": {"kind": "public_external", "license": "https://creativecommons.org/licenses/by/4.0/"},
        "matches": [{"id": "target-match-half1"}],
    }

    with pytest.raises(ValueError, match="exactly 12|unapproved or missing"):
        _validate_external_bundle(bundle)


def test_external_sequence_preserves_full_rate_interval_frames_and_centimeters() -> None:
    match = {
        "duration_s": 2.0,
        "sample_hz": 2.0,
        "pitch": {"length_m": 105.0, "width_m": 68.0},
        "samples": [
            {
                "t": 0.0,
                "ball": [52.501, 34.006],
                "players": [{"id": "slot-a", "team": "H", "x": 10.236, "y": 20.349}],
                "quality": {"ball_observed": True, "player_coverage": 1.0},
                "evidence": {"margin": 1.23456},
            },
            {
                "t": 0.48,
                "ball": None,
                "players": [{"id": "slot-a", "team": "H", "x": 10.246, "y": 20.359}],
                "quality": {"ball_observed": False, "player_coverage": 1.0},
                "evidence": {"margin": None},
            },
            {
                "t": 0.96,
                "ball": [53.0, 35.0],
                "players": [{"id": "slot-a", "team": "H", "x": 10.256, "y": 20.369}],
                "quality": {"ball_observed": True, "player_coverage": 1.0},
                "evidence": {"margin": 2.0},
            },
        ],
        "truth": [{"start_s": 0.0, "end_s": 1.0, "state": "H"}, {"start_s": 1.0, "end_s": 2.0, "state": "D"}],
        "predictions": {
            "v1": {"provenance": {"fps": 25}, "spells": [{"start_s": 0.0, "end_s": 2.0, "state": "H"}]},
            "v2": {"provenance": {"fps": 25}, "spells": [{"start_s": 0.0, "end_s": 1.0, "state": "H"}, {"start_s": 1.0, "end_s": 2.0, "state": "D"}]},
        },
        "evidence_series": [{"key": "margin", "label": "Margin", "unit": "m", "description": "Source evidence."}],
    }

    exported, display_count = _external_sequence("J03WN1-original-half1", match)

    assert display_count == 2  # deterministic thinning keeps source rows 0 and 2
    assert exported["samples"][0] == {
        "f": 0,
        "b": [5250, 3401],
        "p": [[0, 1024, 2035]],
        "q": {"ball_observed": True, "player_coverage": 1.0},
        "e": {"margin": 1.235},
    }
    assert exported["samples"][1]["f"] == 24
    assert exported["samples"][1]["b"] == [5300, 3500]
    assert exported["truth"] == [[0, 25, "H"], [25, 50, "D"]]
    assert exported["predictions"]["v2"] == [[0, 25, "H"], [25, 50, "D"]]
    assert exported["source_sample_hz"] == 2.0
    assert exported["sample_hz"] == 1.0
    assert exported["roster"] == [{"id": "H1", "team": "H", "number": 1}]


def test_interval_conversion_rejects_non_frame_aligned_label() -> None:
    with pytest.raises(ValueError, match="integer 25 Hz frame"):
        _intervals_to_frames([{"start_s": 0.0, "end_s": 0.041, "state": "H"}], 25, 100, "fixture")


def test_expected_external_allowlist_has_all_twelve_halves() -> None:
    assert len(EXPECTED_SEQUENCE_IDS) == 12
    assert EXPECTED_SEQUENCE_IDS[0] == "J03WN1-original-half1"
    assert EXPECTED_SEQUENCE_IDS[-1] == "J03WR9-original-half2"


def _write_external_bundle_stub(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "dataset": {"kind": "public_external", "license": "https://creativecommons.org/licenses/by/4.0/"},
                "matches": [{"id": sequence_id} for sequence_id in EXPECTED_SEQUENCE_IDS],
            }
        ),
        encoding="utf-8",
    )


def test_synthetic_private_kind_is_rejected_before_output_creation(tmp_path: Path) -> None:
    external = tmp_path / "external.json"
    _write_external_bundle_stub(external)
    synthetic = tmp_path / "synthetic"
    synthetic.mkdir()
    (synthetic / "demo.json").write_text(
        json.dumps({"schema_version": "1.0", "dataset": {"kind": "private"}, "matches": []}), encoding="utf-8"
    )
    (synthetic / "media-map.json").write_text("{}", encoding="utf-8")
    output = tmp_path / "site-output"

    with pytest.raises(ValueError, match="synthetic_demo"):
        export_public_data(external, synthetic, tmp_path / "unused-benchmarks.json", output)

    assert not output.exists()


def test_synthetic_video_hash_is_checked_before_output_creation(tmp_path: Path) -> None:
    external = tmp_path / "external.json"
    _write_external_bundle_stub(external)
    synthetic = tmp_path / "synthetic"
    synthetic.mkdir()
    (synthetic / "demo.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "dataset": {"kind": "synthetic_demo"},
                "matches": [
                    {
                        "id": "demo-01",
                        "media": {"id": "synthetic-demo", "offset_s": 0, "fps": 10},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (synthetic / "media-map.json").write_text(json.dumps({"synthetic-demo": "synthetic-demo.mp4"}), encoding="utf-8")
    (synthetic / "synthetic-demo.mp4").write_bytes(b"not the approved fixture")
    output = tmp_path / "site-output"

    with pytest.raises(ValueError, match="hash does not match"):
        export_public_data(external, synthetic, tmp_path / "unused-benchmarks.json", output)

    assert not output.exists()
