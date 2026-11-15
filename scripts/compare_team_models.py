"""Compare three frozen labelers on the same held-out external matches.

The harness reads only CSV predictions/truth and hashes. It never imports or executes a
candidate, opens a model artifact, accesses network resources, or reads competition outputs.
See docs/TEAM_COMPARISON.md for the manifest contract and selection protocol.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation import possession_metrics as pm  # noqa: E402


SCHEMA_VERSION = 1
REQUIRED_CANDIDATES = 3
FORBIDDEN_IDENTIFIERS = re.compile(
    r"competition[-_ ]?199319|199319|bar[-_]ath|\btarget(?:[-_ ]?match)?\b", re.IGNORECASE
)
PUBLIC_GT_BASENAME = re.compile(r".*_possession_gt_public\.csv$", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FRAME_RE = re.compile(r"^[+-]?\d+$")
BLOCK_ID_SEPARATOR = "::"
COMPETITION_FRAME_COUNT = 199319
PUBLIC_WINDOW_FIRST_FRAME = 11185
PUBLIC_WINDOW_LAST_FRAME = 18684


class ComparisonError(ValueError):
    """Invalid manifest, provenance, CSV, or candidate comparison."""


def _fail(message: str) -> None:
    raise ComparisonError(message)


def _required_text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("{} must be a non-empty string".format(where))
    return value.strip()


def _match_id_list(value: Any, where: str) -> List[str]:
    if not isinstance(value, list):
        _fail("{} must be a list of match IDs".format(where))
    match_ids = [_required_text(item, "{}[]".format(where)) for item in value]
    if len(set(match_ids)) != len(match_ids):
        _fail("{} must not contain duplicate match IDs".format(where))
    for match_id in match_ids:
        if FORBIDDEN_IDENTIFIERS.search(match_id):
            _fail("{} contains a reserved competition/target identifier".format(where))
    return match_ids


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checked_hash(value: Any, actual: str, where: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        _fail("{} must be a lowercase SHA-256 hex digest".format(where))
    if value != actual:
        _fail("{} checksum mismatch".format(where))
    return actual


def _is_within(path: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath([str(path), str(parent)]) == str(parent)
    except ValueError:
        return False


def _resolve_input_path(raw: Any, base: Path, where: str) -> Path:
    value = _required_text(raw, where)
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve(strict=True)
    else:
        resolved = (base / candidate).resolve(strict=True)
        if not _is_within(resolved, base.resolve()):
            _fail("{} escapes the manifest directory; use an absolute external path if needed".format(where))
    if not resolved.is_file():
        _fail("{} must name a regular file".format(where))

    # Catch obvious paths to the competition match or its shipped/private answer-key locations.
    normalized = str(resolved).replace("\\", "/")
    if FORBIDDEN_IDENTIFIERS.search(normalized):
        _fail("{} points at a reserved competition/target identifier".format(where))
    if PUBLIC_GT_BASENAME.fullmatch(resolved.name):
        _fail("{} points at the shipped public ground-truth file".format(where))
    repo_gt = (ROOT / "evaluation" / "gt").resolve()
    legacy_gt = (ROOT / "gt").resolve()
    if _is_within(resolved, repo_gt) or _is_within(resolved, legacy_gt):
        _fail("{} points inside the competition ground-truth directory".format(where))
    return resolved


def _read_csv(path: Path, where: str) -> Tuple[np.ndarray, np.ndarray]:
    try:
        frame = pd.read_csv(path, dtype="string")
    except Exception as exc:
        _fail("could not read {}: {}".format(where, exc))
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    if list(frame.columns).count("frame") != 1 or list(frame.columns).count("label") != 1:
        _fail("{} must contain one 'frame' and one 'label' column".format(where))
    if set(frame.columns) != {"frame", "label"}:
        _fail("{} must contain exactly the 'frame' and 'label' columns".format(where))
    frame_text = frame["frame"].astype("string").str.strip()
    if frame_text.isna().any() or not frame_text.map(lambda x: bool(FRAME_RE.fullmatch(x))).all():
        _fail("{} has missing or non-integer frame IDs".format(where))
    try:
        frame_ids = frame_text.astype("int64").to_numpy()
    except (ValueError, OverflowError):
        _fail("{} has frame IDs outside signed 64-bit range".format(where))
    if len(frame_ids) == 0:
        _fail("{} contains no rows".format(where))
    if len(frame_ids) == COMPETITION_FRAME_COUNT:
        _fail("{} has the known 199319-frame competition match length".format(where))
    if (len(frame_ids) == PUBLIC_WINDOW_LAST_FRAME - PUBLIC_WINDOW_FIRST_FRAME + 1 and
            np.array_equal(frame_ids, np.arange(PUBLIC_WINDOW_FIRST_FRAME,
                                                PUBLIC_WINDOW_LAST_FRAME + 1))):
        _fail("{} has the known public five-minute competition frame range".format(where))
    if np.any(frame_ids[1:] <= frame_ids[:-1]):
        _fail("{} frame IDs must be unique and strictly increasing".format(where))

    labels = frame["label"].astype("string").str.strip().str.upper()
    if labels.isna().any() or (labels == "").any():
        _fail("{} contains an empty label; write X for an abstention".format(where))
    allowed = set(pm.LABELS)
    invalid = sorted(set(labels.tolist()) - allowed)
    if invalid:
        _fail("{} labels must be in {}; found {}".format(where, list(pm.LABELS), invalid[:5]))
    return frame_ids, pm.label_codes(labels.to_numpy(dtype=object))


def _block_key(match_id: str, scenario: str) -> Tuple[str, str]:
    return match_id, scenario


def _block_key_text(key: Tuple[str, str]) -> str:
    return key[0] + BLOCK_ID_SEPARATOR + key[1]


def _parse_manifest(path: Path) -> Dict[str, Any]:
    try:
        raw_bytes = path.read_bytes()
        manifest = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        _fail("could not read manifest JSON: {}".format(exc))
    if not isinstance(manifest, dict):
        _fail("manifest root must be a JSON object")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        _fail("schema_version must be {}".format(SCHEMA_VERSION))
    if manifest.get("data_role") != "external_other_matches":
        _fail("data_role must be exactly 'external_other_matches'")
    source = manifest.get("source")
    if not isinstance(source, dict):
        _fail("source must record external dataset provenance")
    for field in ("name", "url_or_catalog_id", "license", "label_provenance"):
        _required_text(source.get(field), "source.{}".format(field))
    attestation = _required_text(manifest.get("externality_attestation"),
                                 "externality_attestation")
    if len(attestation) < 20:
        _fail("externality_attestation must explicitly record the human externality audit")

    protocol = manifest.get("selection_protocol")
    if not isinstance(protocol, dict):
        _fail("selection_protocol must record the predeclared comparison protocol")
    required_false = ("target_match_data_used", "target_human_labels_used",
                      "public_5min_used_for_selection")
    for field in required_false:
        if protocol.get(field) is not False:
            _fail("selection_protocol.{} must be false".format(field))
    required_true = ("candidate_list_frozen_before_scoring",
                     "whole_match_heldout_predictions")
    for field in required_true:
        if protocol.get(field) is not True:
            _fail("selection_protocol.{} must be true".format(field))
    _required_text(protocol.get("tie_break"), "selection_protocol.tie_break")
    if protocol.get("primary_metric") != "equal_match_scenario_spell_f1":
        _fail("primary_metric must be equal_match_scenario_spell_f1")
    if protocol.get("secondary_metric") != "equal_match_scenario_macro_f1":
        _fail("secondary_metric must be equal_match_scenario_macro_f1")

    blocks = manifest.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        _fail("blocks must be a non-empty list of held-out match/scenario rows")
    base = path.resolve().parent
    parsed_blocks: Dict[Tuple[str, str], Dict[str, Any]] = {}
    scenarios_by_match: Dict[str, set] = defaultdict(set)
    evaluation_use_by_match: Dict[str, set] = defaultdict(set)
    for i, block in enumerate(blocks):
        where = "blocks[{}]".format(i)
        if not isinstance(block, dict):
            _fail("{} must be an object".format(where))
        match_id = _required_text(block.get("match_id"), where + ".match_id")
        scenario = _required_text(block.get("scenario"), where + ".scenario")
        if FORBIDDEN_IDENTIFIERS.search(match_id):
            _fail("{} contains a reserved competition/target identifier".format(where))
        key = _block_key(match_id, scenario)
        if key in parsed_blocks:
            _fail("duplicate match/scenario block {}".format(_block_key_text(key)))
        evaluation_use = block.get("evaluation_use")
        if evaluation_use not in ("reused_development", "untouched_audit"):
            _fail("{}.evaluation_use must be reused_development or untouched_audit".format(where))
        previous_research = _required_text(block.get("previous_research"),
                                           where + ".previous_research")
        evaluation_use_by_match[match_id].add(evaluation_use)
        gt_path = _resolve_input_path(block.get("truth_csv"), base, where + ".truth_csv")
        gt_ids, gt_codes = _read_csv(gt_path, where + ".truth_csv")
        gt_sha = _checked_hash(block.get("truth_sha256"), _sha256_file(gt_path),
                               where + ".truth_sha256")

        halves = block.get("halves")
        if not isinstance(halves, list) or len(halves) < 2:
            _fail("{} must define at least two non-empty half row ranges".format(where))
        parsed_halves: List[Dict[str, Any]] = []
        next_row = 0
        half_ids = set()
        for j, half in enumerate(halves):
            half_where = "{}.halves[{}]".format(where, j)
            if not isinstance(half, dict):
                _fail("{} must be an object".format(half_where))
            half_id = _required_text(half.get("half_id"), half_where + ".half_id")
            if half_id in half_ids:
                _fail("{} repeats half_id {}".format(where, half_id))
            half_ids.add(half_id)
            start = half.get("start_row")
            stop = half.get("stop_row")
            if (isinstance(start, bool) or not isinstance(start, int) or
                    isinstance(stop, bool) or not isinstance(stop, int)):
                _fail("{} start_row/stop_row must be integer row offsets".format(half_where))
            if start != next_row or stop <= start or stop > len(gt_ids):
                _fail("{} ranges must be non-empty, ordered, contiguous, and cover every row".format(
                    half_where))
            if stop - start > 1 and np.any(np.diff(gt_ids[start:stop]) != 1):
                _fail("{} frame IDs must be continuous within each half; resample missing frames first".format(
                    half_where))
            parsed_halves.append({"half_id": half_id, "start_row": start, "stop_row": stop})
            next_row = stop
        if next_row != len(gt_ids):
            _fail("{} half ranges must cover all truth rows".format(where))

        parsed_blocks[key] = {
            "match_id": match_id,
            "scenario": scenario,
            "truth_path": gt_path,
            "truth_sha256": gt_sha,
            "frame_ids": gt_ids,
            "truth_codes": gt_codes,
            "halves": parsed_halves,
            "evaluation_use": evaluation_use,
            "previous_research": previous_research,
        }
        scenarios_by_match[match_id].add(scenario)

    if len(scenarios_by_match) < 2:
        _fail("at least two distinct external match clusters are required")
    if any(len(uses) != 1 for uses in evaluation_use_by_match.values()):
        _fail("all scenarios for a match must share one evaluation_use status")
    scenario_sets = {tuple(sorted(scenarios)) for scenarios in scenarios_by_match.values()}
    if len(scenario_sets) != 1:
        _fail("every external match must use the same predeclared scenario set")

    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != REQUIRED_CANDIDATES:
        _fail("exactly three predeclared frozen candidates are required")
    parsed_candidates = []
    seen_candidates = set()
    expected_keys = set(parsed_blocks)
    for i, candidate in enumerate(candidates):
        where = "candidates[{}]".format(i)
        if not isinstance(candidate, dict):
            _fail("{} must be an object".format(where))
        candidate_id = _required_text(candidate.get("candidate_id"), where + ".candidate_id")
        if FORBIDDEN_IDENTIFIERS.search(candidate_id):
            _fail("{} contains a reserved competition/target identifier".format(where))
        if candidate_id in seen_candidates:
            _fail("candidate_id values must be unique")
        seen_candidates.add(candidate_id)
        description = _required_text(candidate.get("description"), where + ".description")
        training_match_ids = _match_id_list(candidate.get("training_match_ids"),
                                            where + ".training_match_ids")
        tuning_match_ids = _match_id_list(candidate.get("tuning_match_ids"),
                                          where + ".tuning_match_ids")
        artifact_path = _resolve_input_path(candidate.get("artifact_path"), base,
                                             where + ".artifact_path")
        artifact_sha = _checked_hash(candidate.get("artifact_sha256"), _sha256_file(artifact_path),
                                     where + ".artifact_sha256")
        cost = candidate.get("cost")
        if not isinstance(cost, dict):
            _fail("{}.cost must report runtime and hardware".format(where))
        _required_text(cost.get("hardware"), where + ".cost.hardware")
        run_scope = _required_text(cost.get("run_scope"), where + ".cost.run_scope")
        for field in ("fit_seconds", "inference_seconds", "peak_memory_mb"):
            if field not in cost:
                _fail("{}.cost.{} is required (use null if not measured)".format(where, field))
            value = cost.get(field)
            if value is not None and (isinstance(value, bool) or
                                      not isinstance(value, (int, float)) or
                                      not math.isfinite(float(value)) or value < 0):
                _fail("{}.cost.{} must be non-negative or null".format(where, field))

        predictions = candidate.get("predictions")
        if not isinstance(predictions, list):
            _fail("{}.predictions must include one CSV for every match/scenario block".format(where))
        prediction_map = {}
        for j, prediction in enumerate(predictions):
            prediction_where = "{}.predictions[{}]".format(where, j)
            if not isinstance(prediction, dict):
                _fail("{} must be an object".format(prediction_where))
            match_id = _required_text(prediction.get("match_id"), prediction_where + ".match_id")
            scenario = _required_text(prediction.get("scenario"), prediction_where + ".scenario")
            key = _block_key(match_id, scenario)
            if key not in expected_keys:
                _fail("{} references an unknown match/scenario".format(prediction_where))
            if key in prediction_map:
                _fail("{} repeats a match/scenario".format(prediction_where))
            prediction_training_ids = _match_id_list(
                prediction.get("training_match_ids"), prediction_where + ".training_match_ids")
            prediction_tuning_ids = _match_id_list(
                prediction.get("tuning_match_ids"), prediction_where + ".tuning_match_ids")
            if not set(prediction_training_ids).issubset(training_match_ids):
                _fail("{}.training_match_ids must be a subset of its candidate declaration".format(
                    prediction_where))
            if not set(prediction_tuning_ids).issubset(tuning_match_ids):
                _fail("{}.tuning_match_ids must be a subset of its candidate declaration".format(
                    prediction_where))
            if prediction.get("fit_exclusion_confirmed") is not True:
                _fail("{}.fit_exclusion_confirmed must be true".format(prediction_where))
            if match_id in prediction_training_ids:
                _fail("{} evaluation match appears in training_match_ids".format(prediction_where))
            fold_id = _required_text(prediction.get("fold_id"), prediction_where + ".fold_id")
            fold_model_path = _resolve_input_path(
                prediction.get("fold_model_path"), base, prediction_where + ".fold_model_path")
            model_sha = _checked_hash(prediction.get("model_sha256"),
                                      _sha256_file(fold_model_path),
                                      prediction_where + ".model_sha256")
            pred_path = _resolve_input_path(prediction.get("csv"), base,
                                            prediction_where + ".csv")
            pred_ids, pred_codes = _read_csv(pred_path, prediction_where + ".csv")
            pred_sha = _checked_hash(prediction.get("sha256"), _sha256_file(pred_path),
                                     prediction_where + ".sha256")
            gt_ids = parsed_blocks[key]["frame_ids"]
            if not np.array_equal(pred_ids, gt_ids):
                _fail("{} frame IDs differ from its truth CSV; align exact IDs first".format(
                    prediction_where))
            prediction_map[key] = {"path": pred_path, "sha256": pred_sha,
                                   "frame_ids": pred_ids, "codes": pred_codes,
                                   "training_match_ids": prediction_training_ids,
                                   "tuning_match_ids": prediction_tuning_ids,
                                   "fit_exclusion_confirmed": True,
                                   "fold_id": fold_id,
                                   "model_sha256": model_sha,
                                   "fold_model_path": fold_model_path}
        if set(prediction_map) != expected_keys:
            missing = sorted(_block_key_text(k) for k in expected_keys - set(prediction_map))
            _fail("{} is missing predictions for {}".format(where, missing[:5]))
        parsed_candidates.append({
            "candidate_id": candidate_id,
            "description": description,
            "artifact_sha256": artifact_sha,
            "cost": {key: cost[key] for key in
                     ("fit_seconds", "inference_seconds", "peak_memory_mb", "hardware",
                      "run_scope")},
            "training_match_ids": training_match_ids,
            "tuning_match_ids": tuning_match_ids,
            "predictions": prediction_map,
        })

    # A match is an untouched audit only if no candidate used it for model selection/tuning in
    # any fold. Candidate-level tuning IDs are the declared union of the per-prediction lists.
    any_prior_reuse = any(block["evaluation_use"] == "reused_development"
                          for block in parsed_blocks.values())
    for key, block in parsed_blocks.items():
        for candidate in parsed_candidates:
            if (block["evaluation_use"] == "untouched_audit" and
                    block["match_id"] in candidate["training_match_ids"]):
                _fail("match {} is marked untouched_audit but appears in candidate {} training_match_ids union".format(
                    block["match_id"], candidate["candidate_id"]))
            if block["match_id"] in candidate["tuning_match_ids"]:
                if block["evaluation_use"] == "untouched_audit":
                    _fail("match {} is marked untouched_audit but appears in candidate {} tuning_match_ids".format(
                        block["match_id"], candidate["candidate_id"]))
                any_prior_reuse = True
            for prediction in candidate["predictions"].values():
                if block["match_id"] in prediction["tuning_match_ids"]:
                    if block["evaluation_use"] == "untouched_audit":
                        _fail("match {} is marked untouched_audit but appears in a prediction tuning_match_ids".format(
                            block["match_id"]))
                    any_prior_reuse = True

    return {
        "manifest_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "source": source,
        "attestation": attestation,
        "protocol": protocol,
        "blocks": parsed_blocks,
        "candidates": parsed_candidates,
        "n_matches": len(scenarios_by_match),
        "n_scenarios": len(next(iter(scenario_sets))),
        "selection_conditioned_by_prior_reuse": any_prior_reuse,
    }


def _score_block(block: Mapping[str, Any], pred_codes: np.ndarray) -> Dict[str, Any]:
    """Apply official metrics per half and pool official sufficient counts within the match."""
    truth = block["truth_codes"]
    confusion = np.zeros((pm.N_LABELS, pm.N_LABELS), dtype=np.int64)
    tp_by_iou = {iou: 0 for iou in pm.SPELL_IOUS}
    fp_by_iou = {iou: 0 for iou in pm.SPELL_IOUS}
    fn_by_iou = {iou: 0 for iou in pm.SPELL_IOUS}
    n_gt_spells = n_pred_spells = 0
    n_frames = 0
    for half in block["halves"]:
        start, stop = half["start_row"], half["stop_row"]
        half_truth = truth[start:stop]
        half_pred = pred_codes[start:stop]
        # Calling the official evaluator on each half makes the break explicit; counts pool
        # exactly as they would for two disconnected valid runs in a full-match evaluation.
        scored = pm.evaluate(half_truth, half_pred, bootstrap_n=0)
        confusion += np.asarray(scored["confusion"], dtype=np.int64)
        n_gt_spells += int(scored["n_gt_spells"])
        n_pred_spells += int(scored["n_pred_spells"])
        n_frames += int(scored["n_frames"])
        for iou in pm.SPELL_IOUS:
            detail = scored["spell_f1"][iou]
            tp_by_iou[iou] += int(detail["n_matched"])
            fp_by_iou[iou] += int(detail["n_spurious"])
            fn_by_iou[iou] += int(detail["n_missed"])

    cm3 = pm.scored_confusion(confusion)
    macro_f1 = pm.macro_f1(cm3)
    per_iou = {}
    for iou in pm.SPELL_IOUS:
        tp, fp, fn = tp_by_iou[iou], fp_by_iou[iou], fn_by_iou[iou]
        denominator = 2 * tp + fp + fn
        per_iou[float(iou)] = {
            "f1": 2.0 * tp / denominator if denominator else 0.0,
            "matched": tp,
            "spurious": fp,
            "missed": fn,
        }
    return {
        "match_id": block["match_id"],
        "scenario": block["scenario"],
        "n_frames": n_frames,
        "n_graded": int(cm3.sum()),
        "macro_f1": macro_f1,
        "spell_f1_mean": float(np.mean([per_iou[iou]["f1"] for iou in per_iou])),
        "n_gt_spells": n_gt_spells,
        "n_pred_spells": n_pred_spells,
        "spell_f1_by_iou": per_iou,
    }


def _mean_by_match(rows: Sequence[Mapping[str, Any]], field: str) -> Dict[str, float]:
    grouped: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        grouped[row["match_id"]].append(float(row[field]))
    return {match: float(np.mean(values)) for match, values in grouped.items()}


def _cluster_bootstrap(values_by_match: Mapping[str, float], runs: int, seed: int,
                       low: float = 2.5, high: float = 97.5) -> Tuple[float, float]:
    values = np.asarray([values_by_match[key] for key in sorted(values_by_match)], dtype=np.float64)
    rng = np.random.RandomState(seed)
    draws = np.empty(runs, dtype=np.float64)
    for i in range(runs):
        picks = rng.randint(0, len(values), len(values))
        draws[i] = float(np.mean(values[picks]))
    return float(np.percentile(draws, low)), float(np.percentile(draws, high))


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compare(manifest_path: Path, output_dir: Path, bootstrap_runs: int = 5000,
            bootstrap_seed: int = 20261114) -> Dict[str, Any]:
    if bootstrap_runs < 100:
        _fail("bootstrap_runs must be at least 100")
    parsed = _parse_manifest(manifest_path)
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        _fail("output directory must be new or empty: {}".format(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    block_rows: List[Dict[str, Any]] = []
    candidate_rows: Dict[str, List[Dict[str, Any]]] = {}
    candidate_metadata: Dict[str, Dict[str, Any]] = {}
    for candidate in parsed["candidates"]:
        candidate_id = candidate["candidate_id"]
        candidate_metadata[candidate_id] = candidate
        rows = []
        for key in sorted(parsed["blocks"]):
            scored = _score_block(parsed["blocks"][key], candidate["predictions"][key]["codes"])
            row = {
                "candidate_id": candidate_id,
                "match_id": scored["match_id"],
                "scenario": scored["scenario"],
                "evaluation_use": parsed["blocks"][key]["evaluation_use"],
                "n_frames": scored["n_frames"],
                "n_graded": scored["n_graded"],
                "spell_f1_mean": scored["spell_f1_mean"],
                "macro_f1": scored["macro_f1"],
                "n_gt_spells": scored["n_gt_spells"],
                "n_pred_spells": scored["n_pred_spells"],
            }
            for iou, detail in scored["spell_f1_by_iou"].items():
                suffix = str(iou).replace(".", "_")
                row["spell_f1_at_{}".format(suffix)] = detail["f1"]
            rows.append(row)
            block_rows.append(row)
        candidate_rows[candidate_id] = rows

    interval_by_candidate: Dict[str, Dict[str, Any]] = {}
    summaries = []
    for candidate_id, rows in candidate_rows.items():
        spell_by_match = _mean_by_match(rows, "spell_f1_mean")
        macro_by_match = _mean_by_match(rows, "macro_f1")
        spell_interval = _cluster_bootstrap(spell_by_match, bootstrap_runs, bootstrap_seed)
        macro_interval = _cluster_bootstrap(macro_by_match, bootstrap_runs,
                                            bootstrap_seed + 1)
        interval_by_candidate[candidate_id] = {"spell": spell_interval, "macro": macro_interval}
        meta = candidate_metadata[candidate_id]
        summaries.append({
            "candidate_id": candidate_id,
            "mean_spell_f1": float(np.mean(list(spell_by_match.values()))),
            "mean_macro_f1": float(np.mean(list(macro_by_match.values()))),
            "spell_f1_cluster_bootstrap_95_low": spell_interval[0],
            "spell_f1_cluster_bootstrap_95_high": spell_interval[1],
            "macro_f1_cluster_bootstrap_95_low": macro_interval[0],
            "macro_f1_cluster_bootstrap_95_high": macro_interval[1],
            "match_clusters": parsed["n_matches"],
            "match_scenarios": len(rows),
            "artifact_sha256": meta["artifact_sha256"],
            "cost": meta["cost"],
        })
    summaries.sort(key=lambda row: (-row["mean_spell_f1"], -row["mean_macro_f1"],
                                    row["candidate_id"]))
    for rank, row in enumerate(summaries, start=1):
        row["score_rank"] = rank

    pairwise = []
    for left, right in itertools.combinations(parsed["candidates"], 2):
        left_id, right_id = left["candidate_id"], right["candidate_id"]
        left_rows = {(r["match_id"], r["scenario"]): r for r in candidate_rows[left_id]}
        right_rows = {(r["match_id"], r["scenario"]): r for r in candidate_rows[right_id]}
        if set(left_rows) != set(right_rows):
            _fail("internal error: candidates do not have paired block rows")
        delta_rows = []
        for key in sorted(left_rows):
            delta_rows.append({
                "match_id": key[0],
                "scenario": key[1],
                "spell_f1_delta": right_rows[key]["spell_f1_mean"] - left_rows[key]["spell_f1_mean"],
                "macro_f1_delta": right_rows[key]["macro_f1"] - left_rows[key]["macro_f1"],
            })
        spell_deltas = _mean_by_match(delta_rows, "spell_f1_delta")
        macro_deltas = _mean_by_match(delta_rows, "macro_f1_delta")
        spell_ci = _cluster_bootstrap(spell_deltas, bootstrap_runs, bootstrap_seed + 2)
        macro_ci = _cluster_bootstrap(macro_deltas, bootstrap_runs, bootstrap_seed + 3)
        pairwise.append({
            "candidate_a": left_id,
            "candidate_b": right_id,
            "delta_direction": "candidate_b minus candidate_a",
            "mean_spell_f1_delta": float(np.mean(list(spell_deltas.values()))),
            "spell_f1_delta_cluster_bootstrap_95_low": spell_ci[0],
            "spell_f1_delta_cluster_bootstrap_95_high": spell_ci[1],
            "mean_macro_f1_delta": float(np.mean(list(macro_deltas.values()))),
            "macro_f1_delta_cluster_bootstrap_95_low": macro_ci[0],
            "macro_f1_delta_cluster_bootstrap_95_high": macro_ci[1],
            "match_clusters": parsed["n_matches"],
        })

    low_cluster_warning = parsed["n_matches"] < 5
    report = {
        "schema_version": 1,
        "method": "official possession_metrics.py; per-half metric scoring; pooled match/scenario counts",
        "evaluator_sha256": _sha256_file(ROOT / "evaluation" / "possession_metrics.py"),
        "primary_metric": "equal_match_scenario_spell_f1",
        "secondary_metric": "equal_match_scenario_macro_f1",
        "spell_iou_thresholds": list(pm.SPELL_IOUS),
        "manifest_sha256": parsed["manifest_sha256"],
        "source": parsed["source"],
        "externality_attestation": parsed["attestation"],
        "selection_protocol": parsed["protocol"],
        "match_usage": [
            {
                "match_id": match_id,
                "evaluation_use": next(block["evaluation_use"] for block in parsed["blocks"].values()
                                       if block["match_id"] == match_id),
                "previous_research": next(block["previous_research"]
                                           for block in parsed["blocks"].values()
                                           if block["match_id"] == match_id),
            }
            for match_id in sorted({block["match_id"] for block in parsed["blocks"].values()})
        ],
        "candidate_lineage": [
            {
                "candidate_id": candidate["candidate_id"],
                "artifact_sha256": candidate["artifact_sha256"],
                "training_match_ids_union_across_folds": candidate["training_match_ids"],
                "tuning_match_ids_union_across_folds": candidate["tuning_match_ids"],
                "cost": candidate["cost"],
                "fold_models": [
                    {
                        "match_id": key[0],
                        "scenario": key[1],
                        "fold_id": prediction["fold_id"],
                        "model_sha256": prediction["model_sha256"],
                        "training_match_ids": prediction["training_match_ids"],
                        "tuning_match_ids": prediction["tuning_match_ids"],
                        "fit_exclusion_confirmed": prediction["fit_exclusion_confirmed"],
                    }
                    for key, prediction in sorted(candidate["predictions"].items())
                ],
            }
            for candidate in parsed["candidates"]
        ],
        "n_match_clusters": parsed["n_matches"],
        "n_scenarios_per_match": parsed["n_scenarios"],
        "selection_conditioned_by_prior_reuse": parsed["selection_conditioned_by_prior_reuse"],
        "evaluation_use": "reused_development" if parsed["selection_conditioned_by_prior_reuse"]
                         else "untouched_audit",
        "bootstrap": {
            "method": "paired percentile bootstrap over whole match clusters; all scenarios stay inside their match",
            "replicates": bootstrap_runs,
            "seed": bootstrap_seed,
            "interval": "95%",
            "warning": ("Fewer than five independent match clusters; intervals are descriptive and too weak "
                        "for a reliable winner claim." if low_cluster_warning else
                        "Match-cluster counts, not frame or scenario counts, determine uncertainty."),
        },
        "ranked_candidates": summaries,
        "pairwise_deltas": pairwise,
        "interpretation": (
            "Prior match reuse makes this a selection-conditioned development comparison. "
            if parsed["selection_conditioned_by_prior_reuse"] else
            "Matches were declared untouched before scoring; selecting among these candidates "
            "still makes this a development comparison, not a final independent test. "
        ) + ("If top candidates are not clearly separated, follow the predeclared simplicity "
             "tie-break and team vote before looking at target labels."),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "block_scores.csv", block_rows,
               ("candidate_id", "match_id", "scenario", "evaluation_use", "n_frames", "n_graded",
                "spell_f1_mean", "macro_f1", "n_gt_spells", "n_pred_spells",
                "spell_f1_at_0_3", "spell_f1_at_0_4", "spell_f1_at_0_5",
                "spell_f1_at_0_6", "spell_f1_at_0_7"))
    _write_csv(output_dir / "summary.csv", summaries,
               ("score_rank", "candidate_id", "mean_spell_f1", "mean_macro_f1",
                "spell_f1_cluster_bootstrap_95_low", "spell_f1_cluster_bootstrap_95_high",
                "macro_f1_cluster_bootstrap_95_low", "macro_f1_cluster_bootstrap_95_high",
                "match_clusters", "match_scenarios", "artifact_sha256"))
    _write_csv(output_dir / "pairwise_deltas.csv", pairwise,
               ("candidate_a", "candidate_b", "delta_direction", "mean_spell_f1_delta",
                "spell_f1_delta_cluster_bootstrap_95_low",
                "spell_f1_delta_cluster_bootstrap_95_high", "mean_macro_f1_delta",
                "macro_f1_delta_cluster_bootstrap_95_low",
                "macro_f1_delta_cluster_bootstrap_95_high", "match_clusters"))
    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="predeclared external comparison manifest JSON")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts_private" / "team-comparison",
                        help="new or empty output directory (default: ignored artifacts_private path)")
    parser.add_argument("--bootstrap", type=int, default=5000,
                        help="whole-match cluster bootstrap replicates (default: 5000)")
    parser.add_argument("--seed", type=int, default=20261114,
                        help="fixed bootstrap seed (default: 20261114)")
    args = parser.parse_args(argv)
    try:
        report = compare(args.manifest, args.out, args.bootstrap, args.seed)
    except (ComparisonError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "status": "complete",
        "output_dir": str(args.out.expanduser().resolve()),
        "match_clusters": report["n_match_clusters"],
        "scenarios_per_match": report["n_scenarios_per_match"],
        "ranking": [{"rank": row["score_rank"], "candidate": row["candidate_id"],
                     "mean_spell_f1": round(row["mean_spell_f1"], 4),
                     "mean_macro_f1": round(row["mean_macro_f1"], 4)}
                    for row in report["ranked_candidates"]],
        "uncertainty_note": report["bootstrap"]["warning"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
