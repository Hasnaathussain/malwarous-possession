#!/usr/bin/env python3
"""Export the explicitly approved, display-only Possession Atlas data pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any


EXPECTED_MATCH_IDS = ("J03WN1", "J03WOY", "J03WPY", "J03WOH", "J03WQQ", "J03WR9")
EXPECTED_SEQUENCE_IDS = tuple(
    f"{match_id}-original-half{half}"
    for match_id in EXPECTED_MATCH_IDS
    for half in (1, 2)
)
EXPECTED_SCENARIOS = ("original", "drop40", "drop70")
EXPECTED_VIDEO_SHA256 = "61d04f220ac6aae121b930626ddeb46cd756e3c3f65a2e6e0bebf7b6f21c2f2c"
EXTERNAL_SOURCE_URL = "https://doi.org/10.6084/m9.figshare.28196177.v1"
LICENSE = {
    "name": "CC BY 4.0",
    "url": "https://creativecommons.org/licenses/by/4.0/",
    "source": EXTERNAL_SOURCE_URL,
    "credit": "Bassek, Rein, Weber and Memmert",
}
V1_CANDIDATE = "v1_smooth50"
V2_CANDIDATE = "context_p10_r0"

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_REPORT = REPO_ROOT / "docs" / "experiments" / "v2-benchmarks.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "website"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read approved source file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in approved source file {path}: {exc}") from exc


def _finite_number(value: Any, description: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{description} must be numeric")
    result = float(value)
    _require(math.isfinite(result), f"{description} must be finite")
    return result


def _frame(seconds: Any, fps: int, description: str) -> int:
    value = _finite_number(seconds, description)
    frames = value * fps
    rounded = round(frames)
    _require(abs(frames - rounded) <= 1e-6, f"{description} does not align to an integer {fps} Hz frame")
    return int(rounded)


def _centimeters(meters: Any, description: str) -> int:
    return int(round(_finite_number(meters, description) * 100.0))


def _round_evidence(value: Any, description: str) -> int | float | None:
    if value is None:
        return None
    rounded = round(_finite_number(value, description), 3)
    return int(rounded) if rounded.is_integer() else rounded


def _validate_external_bundle(bundle: Any) -> dict[str, dict[str, Any]]:
    _require(isinstance(bundle, dict), "External bundle root must be an object")
    _require(bundle.get("schema_version") == "1.0", "External bundle schema_version must be 1.0")
    dataset = bundle.get("dataset")
    _require(isinstance(dataset, dict), "External bundle is missing dataset metadata")
    _require(dataset.get("kind") == "public_external", "External bundle kind must be public_external")
    _require(dataset.get("license") == LICENSE["url"], "External bundle license does not match the approved CC BY 4.0 source")
    matches = bundle.get("matches")
    _require(isinstance(matches, list), "External bundle matches must be a list")
    ids = [match.get("id") for match in matches if isinstance(match, dict)]
    _require(len(ids) == len(matches), "Every external match must be an object with an id")
    _require(len(ids) == len(EXPECTED_SEQUENCE_IDS), f"External bundle must contain exactly {len(EXPECTED_SEQUENCE_IDS)} approved halves")
    _require(set(ids) == set(EXPECTED_SEQUENCE_IDS), "External bundle contains unapproved or missing sequence IDs")
    _require(len(set(ids)) == len(ids), "External bundle contains duplicate sequence IDs")
    return {match["id"]: match for match in matches}


def _match_identity(sequence_id: str) -> tuple[str, int]:
    found = re.fullmatch(r"(J03WN1|J03WOY|J03WPY|J03WOH|J03WQQ|J03WR9)-original-half([12])", sequence_id)
    _require(found is not None, f"Unapproved external sequence id: {sequence_id}")
    assert found is not None
    return found.group(1), int(found.group(2))


def _intervals_to_frames(intervals: Any, fps: int, duration_frames: int, label: str) -> list[list[Any]]:
    _require(isinstance(intervals, list), f"{label} intervals must be a list")
    converted: list[list[Any]] = []
    previous_start = -1
    for index, interval in enumerate(intervals):
        _require(isinstance(interval, dict), f"{label} interval {index} must be an object")
        start = _frame(interval.get("start_s"), fps, f"{label} interval {index} start_s")
        end = _frame(interval.get("end_s"), fps, f"{label} interval {index} end_s")
        state = interval.get("state")
        _require(state in {"H", "A", "D", "X"}, f"{label} interval {index} has an unknown state")
        _require(0 <= start < end <= duration_frames, f"{label} interval {index} is outside the half")
        _require(start >= previous_start, f"{label} intervals are not ordered")
        converted.append([start, end, state])
        previous_start = start
    return converted


def _external_sequence(sequence_id: str, match: dict[str, Any]) -> tuple[dict[str, Any], int]:
    match_id, half = _match_identity(sequence_id)
    predictions_source = match.get("predictions")
    _require(isinstance(predictions_source, dict), f"{sequence_id} has no predictions object")
    _require(set(("v1", "v2")).issubset(predictions_source), f"{sequence_id} is missing V1 or V2 predictions")
    v2_meta = predictions_source["v2"].get("provenance", {})
    fps = v2_meta.get("fps") if isinstance(v2_meta, dict) else None
    _require(fps == 25, f"{sequence_id} must use the approved 25 Hz labels")
    fps = int(fps)
    duration_s = _finite_number(match.get("duration_s"), f"{sequence_id} duration_s")
    duration_frames = _frame(duration_s, fps, f"{sequence_id} duration_s")
    pitch_source = match.get("pitch")
    _require(isinstance(pitch_source, dict), f"{sequence_id} is missing pitch metadata")
    pitch = {
        "length_m": _finite_number(pitch_source.get("length_m"), f"{sequence_id} pitch length_m"),
        "width_m": _finite_number(pitch_source.get("width_m"), f"{sequence_id} pitch width_m"),
    }
    source_hz = _finite_number(match.get("sample_hz"), f"{sequence_id} sample_hz")
    _require(source_hz > 0, f"{sequence_id} sample_hz must be positive")
    source_samples = match.get("samples")
    _require(isinstance(source_samples, list) and source_samples, f"{sequence_id} must contain source observations")

    # Player IDs are replaced by stable, sequence-local diagram labels. The
    # numbers are local display indices, not shirt numbers or player identities.
    roster: list[dict[str, Any]] = []
    roster_index: dict[str, int] = {}
    source_team_by_id: dict[str, str] = {}
    team_count = {"H": 0, "A": 0}
    for sample in source_samples:
        _require(isinstance(sample, dict), f"{sequence_id} contains a malformed observation")
        players = sample.get("players")
        _require(isinstance(players, list), f"{sequence_id} observation players must be a list")
        for player in players:
            _require(isinstance(player, dict), f"{sequence_id} contains a malformed player record")
            source_id = player.get("id")
            team = player.get("team")
            _require(isinstance(source_id, str) and source_id, f"{sequence_id} player ID is missing")
            _require(team in {"H", "A"}, f"{sequence_id} player team must be H or A")
            if source_id in roster_index:
                _require(source_team_by_id[source_id] == team, f"{sequence_id} player team changed within the half")
                continue
            team_count[team] += 1
            number = team_count[team]
            roster_index[source_id] = len(roster)
            source_team_by_id[source_id] = team
            roster.append({"id": f"{team}{number}", "team": team, "number": number})
    _require(bool(roster), f"{sequence_id} contains no players")

    # Retain every second true source observation, plus the final source row if
    # it is an odd-indexed endpoint. This is display thinning only.
    selected_indices = list(range(0, len(source_samples), 2))
    if selected_indices[-1] != len(source_samples) - 1:
        selected_indices.append(len(source_samples) - 1)
    display_samples: list[dict[str, Any]] = []
    last_frame = -1
    for source_index in selected_indices:
        sample = source_samples[source_index]
        frame = _frame(sample.get("t"), fps, f"{sequence_id} observation {source_index} t")
        _require(0 <= frame < duration_frames, f"{sequence_id} observation frame is outside the half")
        _require(frame > last_frame, f"{sequence_id} observation frames must be strictly increasing")
        last_frame = frame
        quality = sample.get("quality")
        _require(isinstance(quality, dict), f"{sequence_id} observation quality must be an object")
        _require("ball_observed" in quality and "player_coverage" in quality, f"{sequence_id} observation quality is incomplete")
        ball = sample.get("ball")
        if ball is None or quality.get("ball_observed") is False:
            ball_cm = None
        else:
            _require(isinstance(ball, list) and len(ball) in {2, 3}, f"{sequence_id} ball must have x, y, optional z or be null")
            ball_cm = [_centimeters(value, f"{sequence_id} ball coordinate") for value in ball]
        players_out: list[list[int]] = []
        for player in sample["players"]:
            source_id = player["id"]
            players_out.append(
                [
                    roster_index[source_id],
                    _centimeters(player.get("x"), f"{sequence_id} player x"),
                    _centimeters(player.get("y"), f"{sequence_id} player y"),
                ]
            )
        evidence_source = sample.get("evidence")
        _require(isinstance(evidence_source, dict), f"{sequence_id} observation evidence must be an object")
        evidence = {key: _round_evidence(value, f"{sequence_id} evidence {key}") for key, value in evidence_source.items()}
        display_samples.append({"f": frame, "b": ball_cm, "p": players_out, "q": dict(quality), "e": evidence})

    truth = _intervals_to_frames(match.get("truth"), fps, duration_frames, f"{sequence_id} truth")
    output_predictions: dict[str, list[list[Any]]] = {}
    for version in ("v1", "v2"):
        prediction = predictions_source[version]
        _require(isinstance(prediction, dict), f"{sequence_id} {version} prediction must be an object")
        output_predictions[version] = _intervals_to_frames(
            prediction.get("spells"), fps, duration_frames, f"{sequence_id} {version} prediction"
        )
    evidence_series = match.get("evidence_series")
    _require(isinstance(evidence_series, list), f"{sequence_id} evidence_series must be a list")
    _require(all(isinstance(item, dict) for item in evidence_series), f"{sequence_id} evidence_series entries must be objects")
    _require(all("key" in item and "label" in item and "unit" in item and "description" in item for item in evidence_series), f"{sequence_id} evidence_series metadata is incomplete")

    display_hz = len(display_samples) / (duration_frames / fps)
    title_half = "first" if half == 1 else "second"
    result = {
        "id": sequence_id,
        "match_id": match_id,
        "half": half,
        "title": f"{match_id} / {title_half} half",
        "kind": "public_external",
        "fps": fps,
        "duration_frames": duration_frames,
        "pitch": pitch,
        "sample_hz": round(display_hz, 10),
        "source_sample_hz": source_hz,
        "coordinate_scale": 100,
        "roster": roster,
        "samples": display_samples,
        "truth": truth,
        "predictions": output_predictions,
        "evidence_series": evidence_series,
        "provenance": {
            "split": "grouped_out_of_fit_development",
            "benchmark_scope": "full match, both halves",
        },
        "license": dict(LICENSE),
    }
    return result, len(display_samples)


def _validate_synthetic_sources(synthetic_dir: Path) -> tuple[dict[str, Any], Path, str]:
    demo_path = synthetic_dir / "demo.json"
    media_map_path = synthetic_dir / "media-map.json"
    video_path = synthetic_dir / "synthetic-demo.mp4"
    demo = _read_json(demo_path)
    media_map = _read_json(media_map_path)
    _require(isinstance(demo, dict), "Synthetic demo root must be an object")
    _require(demo.get("schema_version") == "1.0", "Synthetic demo schema_version must be 1.0")
    dataset = demo.get("dataset")
    _require(isinstance(dataset, dict), "Synthetic demo is missing dataset metadata")
    _require(dataset.get("kind") == "synthetic_demo", "Synthetic fixture kind must be synthetic_demo")
    matches = demo.get("matches")
    _require(isinstance(matches, list) and len(matches) == 1, "Synthetic demo must contain exactly one approved fixture")
    fixture = matches[0]
    _require(isinstance(fixture, dict) and fixture.get("id") == "demo-01", "Synthetic fixture ID must be demo-01")
    media = fixture.get("media")
    _require(isinstance(media, dict), "Synthetic fixture is missing media metadata")
    _require(media.get("id") == "synthetic-demo" and media.get("offset_s") == 0, "Synthetic fixture media metadata is not approved")
    _require(media.get("fps") == 10, "Synthetic demo media must be 10 fps")
    _require(media_map == {"synthetic-demo": "synthetic-demo.mp4"}, "Synthetic media map does not match the approved fixture")
    _require(video_path.is_file(), "Approved synthetic demo video is missing")
    video_hash = _sha256_file(video_path)
    _require(video_hash == EXPECTED_VIDEO_SHA256, "Synthetic demo video hash does not match the approved media")
    _require(_finite_number(fixture.get("duration_s"), "Synthetic duration_s") == 72.0, "Synthetic fixture duration must be 72 seconds")
    _require(len(fixture.get("samples", [])) == 721, "Synthetic fixture must contain the approved 721 observations")
    _require(_frame(fixture["duration_s"], 10, "Synthetic duration_s") == 720, "Synthetic fixture must be 720 frames at 10 fps")
    return fixture, video_path, video_hash


def _synthetic_sequence(fixture: dict[str, Any]) -> dict[str, Any]:
    fps = 10
    duration_frames = _frame(fixture.get("duration_s"), fps, "Synthetic duration_s")
    pitch_source = fixture.get("pitch")
    _require(isinstance(pitch_source, dict), "Synthetic fixture is missing pitch metadata")
    pitch = {
        "length_m": _finite_number(pitch_source.get("length_m"), "Synthetic pitch length_m"),
        "width_m": _finite_number(pitch_source.get("width_m"), "Synthetic pitch width_m"),
    }
    source_samples = fixture.get("samples")
    _require(isinstance(source_samples, list) and len(source_samples) == 721, "Synthetic fixture observations are invalid")
    roster: list[dict[str, Any]] = []
    roster_index: dict[str, int] = {}
    team_by_id: dict[str, str] = {}
    team_count = {"H": 0, "A": 0}
    for sample in source_samples:
        _require(isinstance(sample, dict) and isinstance(sample.get("players"), list), "Synthetic fixture player observations are invalid")
        for player in sample["players"]:
            source_id = player.get("id")
            team = player.get("team")
            _require(isinstance(source_id, str) and source_id and team in {"H", "A"}, "Synthetic fixture roster is invalid")
            if source_id in roster_index:
                _require(team_by_id[source_id] == team, "Synthetic player team changed")
                continue
            team_count[team] += 1
            number = team_count[team]
            roster_index[source_id] = len(roster)
            team_by_id[source_id] = team
            roster.append({"id": f"{team}{number}", "team": team, "number": number})
    output_samples: list[dict[str, Any]] = []
    previous_frame = -1
    for index, sample in enumerate(source_samples):
        frame = _frame(sample.get("t"), fps, f"Synthetic observation {index} t")
        _require(0 <= frame <= duration_frames and frame > previous_frame, "Synthetic observation frames are invalid")
        previous_frame = frame
        quality = sample.get("quality")
        _require(isinstance(quality, dict) and "ball_observed" in quality and "player_coverage" in quality, "Synthetic observation quality is incomplete")
        ball = sample.get("ball")
        if ball is None or quality.get("ball_observed") is False:
            ball_cm = None
        else:
            _require(isinstance(ball, list) and len(ball) in {2, 3}, "Synthetic ball must have x, y, optional z or be null")
            ball_cm = [_centimeters(value, "Synthetic ball coordinate") for value in ball]
        players_out = [
            [roster_index[player["id"]], _centimeters(player.get("x"), "Synthetic player x"), _centimeters(player.get("y"), "Synthetic player y")]
            for player in sample["players"]
        ]
        evidence_source = sample.get("evidence")
        _require(isinstance(evidence_source, dict), "Synthetic observation evidence must be an object")
        evidence = {key: _round_evidence(value, f"Synthetic evidence {key}") for key, value in evidence_source.items()}
        output_samples.append({"f": frame, "b": ball_cm, "p": players_out, "q": dict(quality), "e": evidence})

    truth = _intervals_to_frames(fixture.get("truth"), fps, duration_frames, "Synthetic truth")
    predictions_source = fixture.get("predictions")
    _require(isinstance(predictions_source, dict) and {"v1", "v2"}.issubset(predictions_source), "Synthetic fixture requires V1 and V2 authored labels")
    predictions: dict[str, list[list[Any]]] = {}
    for version in ("v1", "v2"):
        prediction = predictions_source[version]
        _require(isinstance(prediction, dict), f"Synthetic {version} labels must be an object")
        predictions[version] = _intervals_to_frames(prediction.get("spells"), fps, duration_frames, f"Synthetic {version} labels")
    evidence_series = fixture.get("evidence_series")
    _require(isinstance(evidence_series, list) and all(isinstance(item, dict) for item in evidence_series), "Synthetic evidence_series is invalid")
    _require(all("key" in item and "label" in item and "unit" in item and "description" in item for item in evidence_series), "Synthetic evidence_series metadata is incomplete")
    synthetic_benchmarks = fixture.get("benchmarks")
    _require(isinstance(synthetic_benchmarks, list) and len(synthetic_benchmarks) == 2, "Synthetic fixture benchmark placeholders are missing")
    benchmark_placeholders: list[dict[str, Any]] = []
    for index, row in enumerate(synthetic_benchmarks):
        _require(isinstance(row, dict), "Synthetic benchmark placeholder must be an object")
        _require(row.get("version") in {"v1", "v2"}, "Synthetic benchmark placeholder has unknown version")
        _require(row.get("metric_source") == "synthetic_demo", "Synthetic benchmark source must remain synthetic_demo")
        _require(row.get("spellF1") is None and row.get("macroF1") is None and row.get("runtime_s") is None, "Synthetic benchmark metric cells must remain null")
        benchmark_placeholders.append({
            "version": row["version"],
            "metric_source": row["metric_source"],
            "spellF1": None,
            "macroF1": None,
            "runtime_s": None,
        })
    _require({row["version"] for row in benchmark_placeholders} == {"v1", "v2"}, "Synthetic benchmark placeholders must cover V1 and V2")
    return {
        "id": "synthetic-demo",
        "match_id": "synthetic-demo",
        "half": None,
        "title": "Synthetic demo / 72 seconds",
        "kind": "synthetic_demo",
        "fps": fps,
        "duration_frames": duration_frames,
        "pitch": pitch,
        "sample_hz": 10,
        "coordinate_scale": 100,
        "roster": roster,
        "samples": output_samples,
        "truth": truth,
        "predictions": predictions,
        "evidence_series": evidence_series,
        "provenance": {
            "split": "synthetic_fixture",
            "benchmark_scope": "not_evaluated",
            "description": "Deterministic generated positions and authored labels. Software demo only; not accuracy evidence.",
        },
        "benchmarks": benchmark_placeholders,
        "media": {"url": "./media/synthetic-demo.mp4", "offset_s": 0},
    }


def _benchmark_data(report: Any) -> dict[str, Any]:
    _require(isinstance(report, dict), "Benchmark report root must be an object")
    rows = report.get("rows")
    _require(isinstance(rows, list), "Benchmark report rows must be a list")
    required: dict[str, dict[tuple[str, str], dict[str, Any]]] = {
        V1_CANDIDATE: {},
        V2_CANDIDATE: {},
    }
    for row in rows:
        if not isinstance(row, dict) or row.get("candidate") not in required:
            continue
        match_id = row.get("match")
        scenario = row.get("scenario")
        if match_id not in EXPECTED_MATCH_IDS or scenario not in EXPECTED_SCENARIOS:
            continue
        _require(row.get("metric_source") == "official", "Selected benchmark rows must come from the official evaluator")
        _require(row.get("split") == "grouped_out_of_fit_development", "Selected benchmark rows must be grouped out-of-fit development")
        key = (match_id, scenario)
        _require(key not in required[row["candidate"]], f"Duplicate benchmark row for {row['candidate']} {key}")
        for metric in ("spell_f1_mean", "macro_f1", "inference_seconds"):
            _finite_number(row.get(metric), f"Benchmark {row['candidate']} {key} {metric}")
        required[row["candidate"]][key] = row
    expected_pairs = {(match_id, scenario) for match_id in EXPECTED_MATCH_IDS for scenario in EXPECTED_SCENARIOS}
    for candidate, candidate_rows in required.items():
        _require(set(candidate_rows) == expected_pairs, f"Benchmark report is missing one or more selected rows for {candidate}")

    output_rows = []
    for match_id in EXPECTED_MATCH_IDS:
        for scenario in EXPECTED_SCENARIOS:
            row: dict[str, Any] = {"match_id": match_id, "scenario": scenario}
            for label, candidate in (("v1", V1_CANDIDATE), ("v2", V2_CANDIDATE)):
                source = required[candidate][(match_id, scenario)]
                row[label] = {
                    "spellF1": source["spell_f1_mean"],
                    "macroF1": source["macro_f1"],
                    "inference_s": source["inference_seconds"],
                }
            output_rows.append(row)
    _require(len(output_rows) == 18, "Public benchmark table must contain exactly 18 match/scenario rows")

    summary_source = report.get("summary", {}).get("candidates", [])
    _require(isinstance(summary_source, list), "Benchmark report summary candidates must be a list")
    summary_by_candidate = {item.get("candidate"): item for item in summary_source if isinstance(item, dict)}
    summary: dict[str, dict[str, float]] = {}
    for label, candidate in (("v1", V1_CANDIDATE), ("v2", V2_CANDIDATE)):
        source_summary = summary_by_candidate.get(candidate)
        _require(isinstance(source_summary, dict), f"Benchmark summary is missing {candidate}")
        summary[label] = {
            "spellF1": _finite_number(source_summary.get("mean_spell_f1"), f"{candidate} summary spellF1"),
            "macroF1": _finite_number(source_summary.get("mean_macro_f1"), f"{candidate} summary macroF1"),
        }
    return {
        "interpretation": "reused-source grouped development, not independent or target",
        "rows": output_rows,
        "summary": summary,
        "license": dict(LICENSE),
        "metric_source": "official evaluator implementation; external matches only",
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def export_public_data(
    external_bundle_path: Path,
    synthetic_dir: Path,
    benchmark_report_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Validate all approved inputs, then emit the public JSON and one video."""
    external_bundle = _read_json(external_bundle_path)
    # Validate the public data kind and the complete allowlist before touching
    # synthetic inputs or creating any destination files.
    matches = _validate_external_bundle(external_bundle)
    fixture, video_source, video_hash = _validate_synthetic_sources(synthetic_dir)
    benchmark_report = _read_json(benchmark_report_path)
    benchmark_data = _benchmark_data(benchmark_report)

    external_sequences: list[dict[str, Any]] = []
    display_sample_count = 0
    for sequence_id in EXPECTED_SEQUENCE_IDS:
        sequence, sample_count = _external_sequence(sequence_id, matches[sequence_id])
        external_sequences.append(sequence)
        display_sample_count += sample_count
    synthetic_sequence = _synthetic_sequence(fixture)
    all_sequences = external_sequences + [synthetic_sequence]
    index = {
        "schema_version": "1.0",
        "sequences": [
            {
                "id": item["id"],
                "match_id": item["match_id"],
                "half": item["half"],
                "title": item["title"],
                "kind": item["kind"],
                "fps": item["fps"],
                "duration_frames": item["duration_frames"],
                "url": f"./replays/{item['id']}.json",
            }
            for item in all_sequences
        ],
        "benchmarks_url": "./replays/benchmarks.json",
        "default_sequence": "J03WN1-original-half1",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    replay_dir = output_dir / "replays"
    for sequence in all_sequences:
        _write_json(replay_dir / f"{sequence['id']}.json", sequence)
    _write_json(replay_dir / "benchmarks.json", benchmark_data)
    _write_json(replay_dir / "index.json", index)
    media_target = output_dir / "media" / "synthetic-demo.mp4"
    media_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(video_source, media_target)
    _require(_sha256_file(media_target) == video_hash, "Copied synthetic demo media did not preserve the approved hash")
    sizes = {
        path.name: path.stat().st_size
        for path in [*(replay_dir / f"{item['id']}.json" for item in all_sequences), replay_dir / "benchmarks.json", replay_dir / "index.json", media_target]
    }
    _require(max(size for name, size in sizes.items() if name not in {"synthetic-demo.mp4"}) <= 3 * 1024 * 1024, "An exported sequence or JSON manifest exceeds 3 MiB")
    return {
        "sequences": len(all_sequences),
        "external_sequences": len(external_sequences),
        "display_samples": display_sample_count,
        "benchmarks": len(benchmark_data["rows"]),
        "sizes": sizes,
        "video_sha256": video_hash,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-bundle", type=Path, required=True, help="Approved public_external workbench JSON bundle")
    parser.add_argument("--synthetic-dir", type=Path, required=True, help="Directory containing approved demo.json, media-map.json and synthetic-demo.mp4")
    parser.add_argument("--benchmarks-report", type=Path, default=DEFAULT_BENCHMARK_REPORT, help="Canonical v2-benchmarks.json report")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Public website output directory")
    args = parser.parse_args(argv)
    try:
        result = export_public_data(args.external_bundle, args.synthetic_dir, args.benchmarks_report, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    total_bytes = sum(result["sizes"].values())
    largest_name, largest_size = max(result["sizes"].items(), key=lambda item: item[1])
    print(
        f"Exported {result['sequences']} sequences ({result['external_sequences']} external), "
        f"{result['display_samples']} display observations, and {result['benchmarks']} benchmark rows."
    )
    print(f"Public data pack: {total_bytes / (1024 * 1024):.2f} MiB total; largest file {largest_name} {largest_size / (1024 * 1024):.2f} MiB.")
    print(f"Synthetic demo SHA-256: {result['video_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
