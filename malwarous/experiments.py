"""Predeclared match-separated external candidate evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from time import monotonic
import zlib
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

from evaluation import possession_metrics as official_metrics

from .corruption import mask_ball_observations
from .external_pipeline import (
    FeaturePeriod,
    corrupt_period,
    load_feature_periods,
    nearest_smooth_predictions,
    score_match,
)
from .features import FEATURE_NAMES
from .models import fit_evidence_heads, predict_log_emissions
from .temporal import viterbi_decode


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "configs" / "experiment_protocol.json"
APPROVED_PROTOCOL_SHA256 = "7d04b40943e62d6870a1280bb06daf3e4215bba26fe3c5af75a5349e15ebe7d4"
APPROVED_DEVELOPMENT_MATCHES = ["J03WN1", "J03WPY", "J03WOH", "J03WQQ", "J03WOY", "J03WR9"]
APPROVED_TRAINING_MATCHES = ["J03WPY", "J03WOH", "J03WQQ", "J03WR9"]
APPROVED_SELECTION_MATCHES = ["J03WN1", "J03WOY"]
APPROVED_SEALED_MATCH = "J03WMX"
APPROVED_CANDIDATE_NAMES = {
    "geometry_mild", "full_mild", "full_control_persistence", "full_stoppage_sensitive"
}


def _protocol_digest(config: dict) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_approved_protocol(config: dict) -> str:
    digest = _protocol_digest(config)
    if digest != APPROVED_PROTOCOL_SHA256:
        raise ValueError("loaded experiment protocol differs from the reviewed frozen protocol")
    if (config.get("development_matches") != APPROVED_DEVELOPMENT_MATCHES or
            config.get("training_matches_for_selection") != APPROVED_TRAINING_MATCHES or
            config.get("selection_matches") != APPROVED_SELECTION_MATCHES or
            config.get("sealed_audit_match") != APPROVED_SEALED_MATCH or
            config.get("candidate_limit") != 4 or
            config.get("experiment_cap_hours") != 12 or
            config.get("latest_experiment_finish_pk_time") != "2026-11-16 08:00" or
            {item.get("name") for item in config.get("decoder_candidates", [])} != APPROVED_CANDIDATE_NAMES):
        raise ValueError("experiment settings exceed the independently approved bounds")
    return digest


def load_protocol(path: Path = PROTOCOL_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    _validate_approved_protocol(config)
    return config


def _match_seed(match_id: str, period_id: int, seed: int) -> int:
    data = f"{seed}:{match_id}:{period_id}".encode("ascii")
    return (seed + zlib.crc32(data)) & 0xFFFFFFFF


def _train_arrays(match_ids: list[str], seed: int,
                  budget_check=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features, statuses, owners = [], [], []
    for match_id in match_ids:
        if budget_check is not None:
            budget_check(f"before {match_id} training parse")
        periods = load_feature_periods(match_id)
        if budget_check is not None:
            budget_check(f"after {match_id} training parse")
        for period in periods:
            if budget_check is not None:
                budget_check(f"before {match_id} feature accumulation")
            features.append(period.features)
            statuses.append(period.status)
            owners.append(period.owner)
            moderate = corrupt_period(
                period, fraction=0.4,
                seed=_match_seed(match_id, period.period_id, seed),
                mean_block_frames=8,
            )
            features.append(moderate.features)
            statuses.append(period.status)
            owners.append(period.owner)
            if budget_check is not None:
                budget_check(f"after {match_id} feature accumulation")
    return np.concatenate(features), np.concatenate(statuses), np.concatenate(owners)


def _transition_matrix(candidate: dict) -> np.ndarray:
    turnover = float(candidate["turnover_penalty"])
    live_dead = float(candidate["live_dead_penalty"])
    dead_restart = float(candidate["dead_restart_penalty"])
    matrix = np.zeros((3, 3), dtype=np.float64)
    matrix[0, 1] = matrix[1, 0] = -turnover
    matrix[0, 2] = matrix[1, 2] = -live_dead
    matrix[2, 0] = matrix[2, 1] = -dead_restart
    return matrix


def _decode_emissions(periods: list[FeaturePeriod], emissions: list[np.ndarray],
                      transitions: np.ndarray) -> np.ndarray:
    parts = []
    for index, (period, log_evidence) in enumerate(zip(periods, emissions)):
        if log_evidence.shape != (len(period.frame_ids), 3):
            raise ValueError("emissions do not align with external period")
        parts.append(viterbi_decode(log_evidence, transitions))
        if index + 1 < len(periods):
            parts.append(np.asarray([official_metrics.X], dtype=np.int8))
    return np.concatenate(parts) if parts else np.empty(0, dtype=np.int8)


def _feature_names(protocol: dict, feature_set: str) -> tuple[str, ...]:
    if feature_set == "all_v1":
        return FEATURE_NAMES
    if feature_set == "ball_control_geometry":
        return tuple(protocol["feature_sets"][feature_set])
    raise ValueError("unknown feature set in locked protocol")


def _select_candidate(summary: list[dict], protocol: dict) -> dict:
    best_score = max(row["mean_spell_f1"] for row in summary)
    eligible = [row for row in summary if best_score - row["mean_spell_f1"] <= 0.02]
    candidates = {item["name"]: item for item in protocol["decoder_candidates"]}
    return min(
        eligible,
        key=lambda row: (
            len(_feature_names(protocol, candidates[row["candidate"]]["feature_set"])),
            candidates[row["candidate"]]["turnover_penalty"] +
            candidates[row["candidate"]]["live_dead_penalty"] +
            candidates[row["candidate"]]["dead_restart_penalty"],
            -row["mean_macro_f1"],
            row["candidate"],
        ),
    )


def _release_choice(selected: dict, reference_mean_spell_f1: float) -> tuple[str, str]:
    if selected["mean_spell_f1"] - reference_mean_spell_f1 < 0.02:
        return "nearest_smooth50_reference", "reference"
    return selected["candidate"], "learned"


def _check_experiment_budget(started: float, cap_hours: float, cutoff,
                             phase: str) -> None:
    """Enforce both preregistered wall-clock bounds at each expensive boundary."""
    if monotonic() - started > cap_hours * 3600:
        raise TimeoutError(f"external experiment exceeded its frozen time budget during {phase}")
    if datetime.now(ZoneInfo("Asia/Karachi")) >= cutoff:
        raise TimeoutError(f"external experiment passed its frozen cutoff during {phase}")


def run_selection(protocol: dict | None = None, *, budget_check=None) -> dict:
    """Fit on frozen training matches; select on two different matches under fixed corruptions."""
    config = protocol or load_protocol()
    protocol_hash = _validate_approved_protocol(config)
    started = monotonic()
    now_pk = datetime.now(ZoneInfo("Asia/Karachi"))
    cutoff = datetime.strptime(
        config["latest_experiment_finish_pk_time"], "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("Asia/Karachi"))
    if now_pk >= cutoff:
        raise ValueError("external candidate experiments are past the frozen cutoff")
    train_ids = list(config["training_matches_for_selection"])
    validation_ids = list(config["selection_matches"])
    development = set(config["development_matches"])
    sealed = config["sealed_audit_match"]
    if set(train_ids) & set(validation_ids) or not set(train_ids + validation_ids) <= development:
        raise ValueError("training and selection matches must be disjoint subsets of development")
    if sealed in train_ids or sealed in validation_ids:
        raise ValueError("sealed audit match cannot enter candidate selection")
    if len(config["decoder_candidates"]) > config["candidate_limit"]:
        raise ValueError("candidate count exceeds the locked limit")

    cap_hours = float(config["experiment_cap_hours"])

    def check(phase: str) -> None:
        _check_experiment_budget(started, cap_hours, cutoff, phase)
        if budget_check is not None:
            budget_check(phase)

    check("before training-data preparation")
    x_train, status_train, owner_train = _train_arrays(
        train_ids, int(config["random_seed"]), budget_check=check
    )
    check("after training-data preparation")
    feature_sets = sorted({candidate["feature_set"] for candidate in config["decoder_candidates"]})
    trained_models = {}
    for feature_set in feature_sets:
        trained_models[feature_set] = fit_evidence_heads(
            x_train,
            status_train,
            owner_train,
            feature_names=_feature_names(config, feature_set),
            max_iter=int(config["fixed_estimator"]["max_iter"]),
            max_leaf_nodes=int(config["fixed_estimator"]["max_leaf_nodes"]),
            min_samples_leaf=int(config["fixed_estimator"]["min_samples_leaf"]),
            max_bins=int(config["fixed_estimator"]["max_bins"]),
            l2_regularization=float(config["fixed_estimator"]["l2_regularization"]),
            random_state=int(config["fixed_estimator"]["random_state"]),
        )
        check(f"after {feature_set} model fitting")

    conditions = config["corruption"]["conditions"]
    results = []
    reference_results = []
    for match_id in validation_ids:
        check(f"before {match_id} selection parse")
        clean_periods = list(load_feature_periods(match_id))
        check(f"after {match_id} selection parse")
        for condition in conditions:
            check("candidate scoring")
            fraction = float(condition["masked_fraction"])
            if fraction == 0:
                views = clean_periods
            else:
                views = [
                    corrupt_period(
                        period,
                        fraction=fraction,
                        seed=_match_seed(match_id, period.period_id, int(config["random_seed"])),
                        mean_block_frames=8,
                    )
                    for period in clean_periods
                ]

            emissions_by_feature = {
                feature_set: [
                    predict_log_emissions(trained_models[feature_set], period.features)
                    for period in views
                ]
                for feature_set in feature_sets
            }
            reference_prediction = nearest_smooth_predictions(views, window=50)
            reference_score = score_match(views, reference_prediction)
            reference_results.append({
                "candidate": "nearest_smooth50_reference",
                "match": match_id,
                "corruption": condition["name"],
                "spell_f1": float(reference_score["spell_f1_mean"]),
                "macro_f1": float(reference_score["macro_f1"]),
                "graded_frames": int(reference_score["n_graded"]),
                "gt_spells": int(reference_score["n_gt_spells"]),
                "pred_spells": int(reference_score["n_pred_spells"]),
            })
            for candidate in config["decoder_candidates"]:
                log_emissions = emissions_by_feature[candidate["feature_set"]]
                transitions = _transition_matrix(candidate)
                prediction = _decode_emissions(views, log_emissions, transitions)
                score = score_match(views, prediction)
                results.append({
                    "candidate": candidate["name"],
                    "match": match_id,
                    "corruption": condition["name"],
                    "spell_f1": float(score["spell_f1_mean"]),
                    "macro_f1": float(score["macro_f1"]),
                    "graded_frames": int(score["n_graded"]),
                    "gt_spells": int(score["n_gt_spells"]),
                    "pred_spells": int(score["n_pred_spells"]),
                })

    check("final selection and report assembly")

    summary = []
    for candidate in config["decoder_candidates"]:
        rows = [result for result in results if result["candidate"] == candidate["name"]]
        summary.append({
            "candidate": candidate["name"],
            "mean_spell_f1": float(np.mean([row["spell_f1"] for row in rows])),
            "mean_macro_f1": float(np.mean([row["macro_f1"] for row in rows])),
            "evaluations": len(rows),
        })
    selected = _select_candidate(summary, config)
    reference_mean = float(np.mean([row["spell_f1"] for row in reference_results]))
    release_candidate, release_mode = _release_choice(selected, reference_mean)
    return {
        "protocol_id": config["protocol_id"],
        "protocol_sha256": protocol_hash,
        "status": "completed",
        "selected_candidate": selected["candidate"],
        "reference_mean_spell_f1": reference_mean,
        "release_candidate": release_candidate,
        "release_mode": release_mode,
        "selection_summary": sorted(summary, key=lambda row: row["candidate"]),
        "validation_rows": results,
        "reference_rows": reference_results,
        "training_matches": train_ids,
        "selection_matches": validation_ids,
        "sealed_match_accessed": False,
    }
