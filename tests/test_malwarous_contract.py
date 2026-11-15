"""Synthetic-only contracts for the official possession scorer and CSV validator."""

import numpy as np

from evaluation import possession_metrics as pm


def _codes(text):
    """Encode whitespace-separated synthetic labels using the official mapper."""
    return pm.label_codes(text.split())


def _canonical_csv(labels):
    lines = ["frame,label"]
    lines.extend(f"{frame},{label}" for frame, label in enumerate(labels))
    return ("\n".join(lines) + "\n").encode("ascii")


def _read_and_validate(path, n_expected):
    table = pm.read_label_csv(path)
    return table, pm.validate_submission(table, n_expected)


def test_perfect_synthetic_spells_score_perfectly():
    gt = _codes("H H D D A A")
    result = pm.evaluate(gt, gt.copy(), bootstrap_n=0)

    assert result["macro_f1"] == 1.0
    assert result["spell_f1_mean"] == 1.0
    assert result["n_gt_spells"] == result["n_pred_spells"] == 2
    assert result["n_gt_segments"] == result["n_pred_segments"] == 3
    assert result["n_graded"] == len(gt)


def test_fragmented_prediction_counts_each_synthetic_segment():
    gt = _codes("H H H H H H H H")
    pred = _codes("H A H A H A H A")

    assert pm.fragmentation(gt, pred, pm.valid_runs(gt)) == (1, 8, 8.0)


def test_one_prediction_cannot_cover_two_d_separated_spells():
    gt = _codes("H H D D H H")
    merged = _codes("H H H H H H")

    assert pm.possession_spells(gt, pm.valid_runs(gt)) == [
        (0, 2, pm.H),
        (4, 6, pm.H),
    ]
    score = pm.spell_scores(gt, merged, pm.valid_runs(gt), ious=(0.3,))
    assert (score["n_gt"], score["n_pred"]) == (2, 1)
    assert score["per_iou"][0.3]["n_matched"] == 1
    assert score["per_iou"][0.3]["n_missed"] == 1


def test_wrong_team_spell_does_not_match():
    gt = _codes("H H H D")
    pred = _codes("A A A D")

    score = pm.spell_scores(gt, pred, pm.valid_runs(gt), ious=(0.3,))
    assert score["per_iou"][0.3]["n_matched"] == 0
    assert score["per_iou"][0.3]["n_spurious"] == 1
    assert score["per_iou"][0.3]["n_missed"] == 1


def test_same_team_spells_separated_by_dead_ball_remain_two_spells():
    codes = _codes("H H D D H H")

    assert pm.possession_spells(codes, pm.valid_runs(codes)) == [
        (0, 2, pm.H),
        (4, 6, pm.H),
    ]


def test_one_frame_possessions_are_not_filtered_out():
    codes = _codes("H A D")

    assert pm.possession_spells(codes, pm.valid_runs(codes)) == [
        (0, 1, pm.H),
        (1, 2, pm.A),
    ]
    score = pm.spell_scores(codes, codes, pm.valid_runs(codes), ious=(0.5,))
    assert score["per_iou"][0.5]["f1"] == 1.0


def test_abstention_fill_is_local_to_each_valid_run_and_keeps_all_x_run():
    gt = _codes("H A D X H A D")
    pred = _codes("X H X A X X X")
    runs = pm.valid_runs(gt)

    assert runs == [(0, 3), (4, 7)]
    assert pm.fill_abstentions(pred, runs).tolist() == [
        pm.H, pm.H, pm.H, pm.A, pm.X, pm.X, pm.X,
    ]


def test_all_x_ground_truth_has_no_runs_and_does_not_fill_predictions():
    gt = _codes("X X X X")
    pred = _codes("A X H D")

    assert pm.valid_runs(gt) == []
    assert pm.fill_abstentions(pred, pm.valid_runs(gt)).tolist() == pred.tolist()


def test_abstention_on_live_ground_truth_is_scored_as_x_not_dead_ball():
    gt = _codes("H H H D A A")
    pred = _codes("H X H D A A")
    result = pm.evaluate(gt, pred, bootstrap_n=0)

    assert result["n_graded"] == 6
    assert result["n_abstain_on_graded"] == 1
    assert result["confusion"][pm.H][pm.X] == 1
    assert result["confusion"][pm.D][pm.X] == 0
    assert result["n_gt_spells"] == result["n_pred_spells"] == 2


def test_halftime_hole_splits_equal_labels_and_prevents_cross_half_transition():
    gt = _codes("D H X X D H")
    runs = pm.valid_runs(gt)

    assert runs == [(0, 2), (4, 6)]
    assert pm.segments(gt, runs) == [
        (0, 1, pm.D),
        (1, 2, pm.H),
        (4, 5, pm.D),
        (5, 6, pm.H),
    ]
    assert pm.transitions(gt, runs) == [
        (1, pm.D, pm.H),
        (5, pm.D, pm.H),
    ]
    assert pm.possession_spells(gt, runs) == [
        (1, 2, pm.H),
        (5, 6, pm.H),
    ]


def test_iou_threshold_includes_exact_edge_and_rejects_just_above():
    gt = np.array([pm.H] * 10 + [pm.D] * 5, dtype=np.int8)
    pred = np.array([pm.H] * 5 + [pm.D] * 10, dtype=np.int8)
    thresholds = (0.4999999, 0.5, 0.5000001)

    score = pm.spell_scores(gt, pred, pm.valid_runs(gt), ious=thresholds)
    assert [score["per_iou"][t]["f1"] for t in thresholds] == [1.0, 1.0, 0.0]


def test_equal_iou_greedy_matching_uses_stable_gt_then_prediction_order():
    overlaps = [(0.5, 0, 0), (0.5, 0, 1), (0.5, 1, 0)]

    assert pm.match_spells(overlaps, n_gt=2, n_pred=2, threshold=0.5) == (1, 1, 1)
    assert pm.match_spells(overlaps, n_gt=2, n_pred=2, threshold=0.5) == (1, 1, 1)


def test_full_evaluation_and_seeded_bootstrap_are_deterministic():
    gt = _codes("H H D A A X H D")
    pred = _codes("H X D A H X X D")

    first = pm.evaluate(gt, pred, bootstrap_n=32)
    second = pm.evaluate(gt, pred, bootstrap_n=32)

    assert first == second


def test_external_game_masks_are_derived_independently_from_synthetic_labels():
    external_a = _codes("H H X X A A D")
    external_b = _codes("D X H A A X H")

    assert pm.valid_runs(external_a) == [(0, 2), (4, 7)]
    assert pm.valid_runs(external_b) == [(0, 1), (2, 5), (6, 7)]

    score_a = pm.evaluate(external_a, external_a, bootstrap_n=0)
    score_b = pm.evaluate(external_b, external_b, bootstrap_n=0)
    assert (score_a["n_frames"], score_a["n_graded"], score_a["n_gt_spells"]) == (7, 5, 2)
    assert (score_b["n_frames"], score_b["n_graded"], score_b["n_gt_spells"]) == (7, 5, 3)


def test_canonical_synthetic_csv_has_stable_lf_bytes_and_validates(tmp_path):
    path = tmp_path / "synthetic.csv"
    payload = _canonical_csv(["H", "A", "D", "X"])

    assert payload == b"frame,label\n0,H\n1,A\n2,D\n3,X\n"
    assert b"\r" not in payload
    path.write_bytes(payload)

    table, reason = _read_and_validate(path, n_expected=4)
    assert reason is None
    assert table.columns.tolist() == ["frame", "label"]
    assert pm.label_codes(table).tolist() == [pm.H, pm.A, pm.D, pm.X]


def test_validator_normalizes_header_and_label_whitespace(tmp_path):
    path = tmp_path / "whitespace.csv"
    path.write_bytes(b" FRAME , LABEL \n0, h \n1,a \n")
    frame = pm.read_label_csv(path)

    assert pm.validate_submission(frame, n_expected=2) is None
    assert pm.label_codes(frame).tolist() == [pm.H, pm.A]


def test_validator_rejects_wrong_row_count_and_off_by_one_or_reordered_ids(tmp_path):
    too_short = tmp_path / "too_short.csv"
    too_short.write_bytes(_canonical_csv(["H", "A"])[:-len(b"1,A\n")])
    table = pm.read_label_csv(too_short)
    assert pm.validate_submission(table, n_expected=2).startswith("row count")

    for name, frame_ids in (
        ("one_based.csv", [1, 2, 3]),
        ("reordered.csv", [0, 2, 1]),
    ):
        path = tmp_path / name
        path.write_bytes(
            ("frame,label\n" + "".join(f"{frame_id},H\n" for frame_id in frame_ids))
            .encode("ascii")
        )
        table = pm.read_label_csv(path)
        assert pm.validate_submission(table, n_expected=3).startswith("'frame' column")


def test_validator_rejects_blank_and_illegal_labels(tmp_path):
    blank = tmp_path / "blank.csv"
    blank.write_bytes(b"frame,label\n0,H\n1,\n")
    table = pm.read_label_csv(blank)
    assert pm.validate_submission(table, n_expected=2).startswith("empty label")

    illegal = tmp_path / "illegal.csv"
    illegal.write_bytes(b"frame,label\n0,H\n1,Q\n")
    table = pm.read_label_csv(illegal)
    assert pm.validate_submission(table, n_expected=2).startswith("labels outside")


def test_csv_reader_requires_frame_and_label_but_validator_currently_allows_extras(tmp_path):
    missing = tmp_path / "missing.csv"
    missing.write_bytes(b"label\nH\n")
    try:
        pm.read_label_csv(missing)
    except ValueError as error:
        assert "frame" in str(error) and "label" in str(error)
    else:
        raise AssertionError("missing frame column should be rejected")

    extra = tmp_path / "extra.csv"
    extra.write_bytes(b"frame,label,note\n0,H,synthetic\n1,A,synthetic\n")
    table = pm.read_label_csv(extra)
    assert pm.validate_submission(table, n_expected=2) is None
