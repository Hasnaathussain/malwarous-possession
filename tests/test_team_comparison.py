"""Synthetic fixtures for the external-only team comparison harness."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from evaluation import possession_metrics as pm
from scripts.compare_team_models import ComparisonError, _score_block, compare


def _write_labels(path, ids, labels):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["frame", "label"])
        writer.writerows(zip(ids, labels))
    return path


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_fixture(root, cross_validation=True):
    root.mkdir(parents=True, exist_ok=True)
    manifest_dir = root / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    ids = [101, 102, 103, 104, 120, 121, 122, 123]
    truth_labels = ["H", "A", "D", "H", "H", "A", "D", "H"]
    blocks = []
    candidate_rows = {name: [] for name in ("alpha", "beta", "gamma")}
    for match_index, match_id in enumerate(("external-one", "external-two")):
        truth_path = _write_labels(root / "truth" / (match_id + ".csv"), ids, truth_labels)
        blocks.append({
            "match_id": match_id,
            "scenario": "standard",
            "evaluation_use": "reused_development" if cross_validation else "untouched_audit",
            "previous_research": ("synthetic test only; each match is used to train the other fold"
                                  if cross_validation else "synthetic test only; no prior reuse"),
            "truth_csv": str(truth_path.resolve()),
            "truth_sha256": _sha(truth_path),
            "halves": [
                {"half_id": "1", "start_row": 0, "stop_row": 4},
                {"half_id": "2", "start_row": 4, "stop_row": 8},
            ],
        })
        alternatives = {
            "alpha": truth_labels,
            "beta": truth_labels if match_index == 0 else ["H", "H", "D", "H", "H", "A", "D", "H"],
            "gamma": ["D", "A", "D", "H", "H", "A", "D", "H"],
        }
        for name, labels in alternatives.items():
            pred_path = _write_labels(root / "predictions" / name /
                                      (match_id + ".csv"), ids, labels)
            fold_model_path = root / "artifacts" / "folds" / (name + "-" + match_id + ".bin")
            fold_model_path.parent.mkdir(parents=True, exist_ok=True)
            fold_model_path.write_bytes((name + " model for " + match_id).encode("utf-8"))
            candidate_rows[name].append({
                "match_id": match_id,
                "scenario": "standard",
                "training_match_ids": (["external-two" if match_id == "external-one" else "external-one"]
                                       if cross_validation else
                                       ["training-two" if match_id == "external-one" else "training-one"]),
                "tuning_match_ids": [],
                "fit_exclusion_confirmed": True,
                "fold_id": "heldout-" + match_id,
                "fold_model_path": str(fold_model_path.resolve()),
                "model_sha256": _sha(fold_model_path),
                "csv": str(pred_path.resolve()),
                "sha256": _sha(pred_path),
            })

    candidates = []
    for name in ("alpha", "beta", "gamma"):
        artifact = root / "artifacts" / (name + ".zip")
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes((name + " frozen source archive").encode("utf-8"))
        candidates.append({
            "candidate_id": name,
            "description": name + " labeler frozen for comparison",
            "training_match_ids": (["external-one", "external-two"] if cross_validation else
                                    ["training-one", "training-two"]),
            "tuning_match_ids": [],
            "artifact_path": str(artifact.resolve()),
            "artifact_sha256": _sha(artifact),
            "cost": {
                "fit_seconds": 1.0,
                "inference_seconds": 0.5,
                "peak_memory_mb": 10.0,
                "hardware": "synthetic fixture CPU",
                "run_scope": "total across the two fold predictions",
            },
            "predictions": candidate_rows[name],
        })

    manifest = {
        "schema_version": 1,
        "data_role": "external_other_matches",
        "source": {
            "name": "synthetic unit-test fixture",
            "url_or_catalog_id": "synthetic-only",
            "license": "test data; not a benchmark",
            "label_provenance": "constructed in the test from fixed toy labels",
        },
        "externality_attestation": (
            "This test fixture is synthetic and contains no competition frames or labels."
        ),
        "selection_protocol": {
            "candidate_list_frozen_before_scoring": True,
            "whole_match_heldout_predictions": True,
            "target_match_data_used": False,
            "target_human_labels_used": False,
            "public_5min_used_for_selection": False,
            "primary_metric": "equal_match_scenario_spell_f1",
            "secondary_metric": "equal_match_scenario_macro_f1",
            "tie_break": "If intervals overlap, team vote on simplicity before target labels.",
        },
        "blocks": blocks,
        "candidates": candidates,
    }
    manifest_path = manifest_dir / "comparison.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path, manifest


def test_scores_frozen_candidates_with_official_metrics_and_no_cross_half_spells(tmp_path):
    manifest_path, _ = _make_fixture(tmp_path / "external-fixture")
    out = tmp_path / "result"
    report = compare(manifest_path, out, bootstrap_runs=200, bootstrap_seed=7)

    assert report["n_match_clusters"] == 2
    assert report["n_scenarios_per_match"] == 1
    assert report["selection_conditioned_by_prior_reuse"] is True
    assert report["ranked_candidates"][0]["candidate_id"] == "alpha"
    alpha = report["ranked_candidates"][0]
    assert alpha["mean_spell_f1"] == 1.0
    assert alpha["mean_macro_f1"] == 1.0
    # H at the end of half 1 and beginning of half 2 remains two spells.
    block_rows = list(csv.DictReader((out / "block_scores.csv").open(encoding="utf-8")))
    alpha_rows = [row for row in block_rows if row["candidate_id"] == "alpha"]
    assert all(int(row["n_gt_spells"]) == 6 for row in alpha_rows)
    assert (out / "summary.csv").is_file()
    assert (out / "pairwise_deltas.csv").is_file()
    report_text = (out / "report.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in report_text
    assert "H,A,D,H" not in report_text
    assert "Fewer than five independent match clusters" in report["bootstrap"]["warning"]


def test_halfwise_pooling_matches_official_evaluator_with_x_gap_and_abstentions():
    gt = pm.label_codes(["H", "A", "D", "H", "H", "A", "D", "H"])
    pred = pm.label_codes(["H", "X", "D", "H", "X", "A", "D", "H"])
    block = {
        "match_id": "external-one",
        "scenario": "standard",
        "truth_codes": gt,
        "halves": [
            {"half_id": "1", "start_row": 0, "stop_row": 4},
            {"half_id": "2", "start_row": 4, "stop_row": 8},
        ],
    }
    halfwise = _score_block(block, pred)
    joined = pm.evaluate(np.concatenate((gt[:4], [pm.X], gt[4:])),
                         np.concatenate((pred[:4], [pm.X], pred[4:])))

    assert halfwise["macro_f1"] == joined["macro_f1"]
    assert halfwise["spell_f1_mean"] == joined["spell_f1_mean"]
    assert halfwise["n_gt_spells"] == joined["n_gt_spells"]
    assert halfwise["n_pred_spells"] == joined["n_pred_spells"]


def test_rejects_duplicate_frame_ids_even_when_hash_is_updated(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    pred = Path(manifest["candidates"][0]["predictions"][0]["csv"])
    _write_labels(pred, [101, 103, 103, 108, 120, 123, 124, 130],
                  ["H", "A", "D", "H", "H", "A", "D", "H"])
    manifest["candidates"][0]["predictions"][0]["sha256"] = _sha(pred)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="unique and strictly increasing"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_half_ranges_that_skip_rows(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    manifest["blocks"][0]["halves"][1]["start_row"] = 5
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="ordered, contiguous"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_frame_id_mismatch_between_truth_and_prediction(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    pred = Path(manifest["candidates"][1]["predictions"][1]["csv"])
    _write_labels(pred, [101, 102, 103, 104, 120, 121, 122, 124],
                  ["H", "A", "D", "H", "H", "A", "D", "H"])
    manifest["candidates"][1]["predictions"][1]["sha256"] = _sha(pred)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="frame IDs differ from its truth"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_frame_gaps_inside_a_half(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    truth = Path(manifest["blocks"][0]["truth_csv"])
    _write_labels(truth, [101, 102, 104, 105, 120, 121, 122, 123],
                  ["H", "A", "D", "H", "H", "A", "D", "H"])
    manifest["blocks"][0]["truth_sha256"] = _sha(truth)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="continuous within each half"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_evaluation_match_in_its_prediction_training_ids(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    prediction = manifest["candidates"][0]["predictions"][0]
    prediction["training_match_ids"] = ["external-one", "external-two"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="evaluation match appears in training_match_ids"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_untouched_audit_rejects_match_in_candidate_tuning_union(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture", cross_validation=False)
    manifest["candidates"][0]["tuning_match_ids"] = ["external-one"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="marked untouched_audit"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_reused_development_is_allowed_and_reported_as_selection_conditioned(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture", cross_validation=False)
    manifest["blocks"][0]["evaluation_use"] = "reused_development"
    manifest["candidates"][0]["tuning_match_ids"] = ["external-one"]
    manifest["candidates"][0]["predictions"][1]["tuning_match_ids"] = ["external-one"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = compare(manifest_path, tmp_path / "result", bootstrap_runs=200)
    assert report["selection_conditioned_by_prior_reuse"] is True
    assert report["evaluation_use"] == "reused_development"
    assert "selection-conditioned" in report["interpretation"]


def test_untouched_audit_rejects_candidate_training_union_reuse(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture", cross_validation=False)
    manifest["candidates"][0]["training_match_ids"].append("external-one")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="marked untouched_audit.*training_match_ids union"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_relative_paths_that_escape_the_manifest_directory(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    truth = Path(manifest["blocks"][0]["truth_csv"])
    manifest["blocks"][0]["truth_csv"] = str(Path("../../") / truth.name)
    # Ensure the intended condition, rather than an absent-file error, is reached.
    (manifest_path.parent.parent.parent / truth.name).write_text("frame,label\n0,H\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="escapes the manifest directory"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_obvious_target_match_identifier(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    manifest["blocks"][0]["match_id"] = "competition199319"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="reserved competition/target identifier"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_public_ground_truth_filename(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    public_gt = _write_labels(tmp_path / "other" / "external_possession_gt_public.csv",
                              [1, 2], ["H", "A"])
    manifest["blocks"][0]["truth_csv"] = str(public_gt.resolve())
    manifest["blocks"][0]["truth_sha256"] = _sha(public_gt)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="shipped public ground-truth"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_known_competition_full_match_frame_count(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    target_like = _write_labels(tmp_path / "other" / "rows.csv", range(199319),
                                ["X"] * 199319)
    manifest["blocks"][0]["truth_csv"] = str(target_like.resolve())
    manifest["blocks"][0]["truth_sha256"] = _sha(target_like)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="known 199319-frame competition match length"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_known_public_five_minute_frame_range(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    public_range = range(11185, 18685)
    target_like = _write_labels(tmp_path / "other" / "rows.csv", public_range,
                                ["X"] * len(public_range))
    manifest["blocks"][0]["truth_csv"] = str(target_like.resolve())
    manifest["blocks"][0]["truth_sha256"] = _sha(target_like)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="known public five-minute competition frame range"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


def test_rejects_tampered_frozen_artifact_hash(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / "external-fixture")
    manifest["candidates"][0]["artifact_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ComparisonError, match="checksum mismatch"):
        compare(manifest_path, tmp_path / "result", bootstrap_runs=200)


@pytest.mark.parametrize('field', ['fit_seconds', 'inference_seconds', 'peak_memory_mb'])
def test_missing_cost_is_a_validation_error_not_an_uncaught_key_error(tmp_path, field):
    manifest_path, manifest = _make_fixture(tmp_path / 'external-fixture')
    del manifest['candidates'][0]['cost'][field]
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ComparisonError, match='is required'):
        compare(manifest_path, tmp_path / 'result', bootstrap_runs=200)


def test_evaluation_match_cannot_train_its_own_prediction(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / 'external-fixture')
    prediction = manifest['candidates'][0]['predictions'][0]
    prediction['training_match_ids'].append(prediction['match_id'])
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ComparisonError, match='evaluation match appears in training_match_ids'):
        compare(manifest_path, tmp_path / 'result', bootstrap_runs=200)


def test_grouped_cross_validation_cannot_be_declared_an_untouched_audit(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / 'external-fixture')
    for block in manifest['blocks']:
        block['evaluation_use'] = 'untouched_audit'
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ComparisonError, match='training_match_ids union'):
        compare(manifest_path, tmp_path / 'result', bootstrap_runs=200)


def test_prior_tuning_by_any_candidate_invalidates_untouched_status(tmp_path):
    manifest_path, manifest = _make_fixture(tmp_path / 'external-fixture', cross_validation=False)
    manifest['candidates'][2]['tuning_match_ids'] = ['external-one']
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ComparisonError, match='untouched_audit.*tuning_match_ids'):
        compare(manifest_path, tmp_path / 'result', bootstrap_runs=200)


def test_changed_fold_weights_are_rejected_before_scoring(tmp_path, monkeypatch):
    manifest_path, manifest = _make_fixture(tmp_path / 'external-fixture')
    model = Path(manifest['candidates'][1]['predictions'][0]['fold_model_path'])
    model.write_bytes(b'changed after candidate freeze')
    monkeypatch.setattr(pm, 'evaluate', lambda *a, **k: pytest.fail('scorer ran before provenance checks'))
    with pytest.raises(ComparisonError, match='model_sha256 checksum mismatch'):
        compare(manifest_path, tmp_path / 'result', bootstrap_runs=200)


def test_actual_untouched_external_set_is_identified_without_a_blindness_guarantee(tmp_path):
    manifest_path, _ = _make_fixture(tmp_path / 'external-fixture', cross_validation=False)
    report = compare(manifest_path, tmp_path / 'result', bootstrap_runs=200)
    assert report['selection_conditioned_by_prior_reuse'] is False
    assert report['evaluation_use'] == 'untouched_audit'
    assert report['evaluator_sha256'] == _sha(Path(pm.__file__))

