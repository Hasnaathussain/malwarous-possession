"""Cache-only preregistered V6 study. No target or fit entry point exists."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from evaluation import possession_metrics as pm

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = Path('D:/more_than_a_hack/malwarous/artifacts_private/v2')
PROTOCOL = ROOT / 'docs/experiments/V6_PROTOCOL.md'
PROTOCOL_SHA = '8c15af3fb2c633afd3efa4db7f2bdbdf7c0086ed8b18203b8fb9c038f99b0fce'
PAIRS = (('J03WN1', 'J03WOY'), ('J03WPY', 'J03WOH'), ('J03WQQ', 'J03WR9'))
SCENARIOS = ('original', 'drop40', 'drop70')
CANDIDATES = ('context_p10_r0', 'context_p25_r0', 'context_p50_r0')
BINS = (('1-25', 1, 25), ('26-50', 26, 50), ('51-125', 51, 125), ('126+', 126, np.inf))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def transitions_by_run(gt, pred, runs, tolerance):
    counts = dict(n_gt=0, n_pred=0, n_matched=0, n_missed=0, n_spurious=0, n_ambiguous=0)
    latencies = []
    for run in runs:
        g = pm.transitions(gt, [run])
        p = pm.transitions(pred, [run])
        score = pm.transition_scores(g, p, tolerance, typed='to')
        for key in counts:
            counts[key] += score[key]
        latencies.extend(b[0] - a[0] for a, b in score['pairs'])
    precision = counts['n_matched'] / counts['n_pred'] if counts['n_pred'] else 0.
    recall = counts['n_matched'] / counts['n_gt'] if counts['n_gt'] else 0.
    return dict(counts, precision=precision, recall=recall,
                f1=2 * precision * recall / (precision + recall) if precision + recall else 0.,
                count_ratio=counts['n_pred'] / counts['n_gt'] if counts['n_gt'] else None,
                mean_latency=float(np.mean(latencies)) if latencies else None,
                mean_abs_latency=float(np.mean(np.abs(latencies))) if latencies else None)


def short_spells(gt, pred, runs):
    g, p = pm.possession_spells(gt, runs), pm.possession_spells(pred, runs)
    overlaps = pm.spell_overlaps(g, p)
    flags = [pm.matched_gt_flags(overlaps, len(g), threshold) for threshold in pm.SPELL_IOUS]
    result = {}
    for label, low, high in BINS:
        ix = [i for i, (a, b, _) in enumerate(g) if low <= b - a <= high]
        n_pred = sum(low <= b - a <= high for a, b, _ in p)
        recalls = [float(f[ix].mean()) if ix else None for f in flags]
        result[label] = dict(n_gt=len(ix), n_pred=int(n_pred),
                             count_ratio=n_pred / len(ix) if ix else None,
                             recall_mean_iou=float(np.mean(recalls)) if ix else None,
                             recall_by_iou=dict(zip(map(str, pm.SPELL_IOUS), recalls)))
    return result


def metrics(gt, pred):
    if gt.shape != pred.shape or not np.isin(pred, range(4)).all():
        raise ValueError('prediction alignment/label failure')
    score = pm.evaluate(gt, pred, bootstrap_n=0)
    runs = pm.valid_runs(gt)
    filled = pm.fill_abstentions(pred, runs)
    keys = ('spell_f1_mean', 'macro_f1', 'n_gt_spells', 'n_pred_spells',
            'spell_count_error', 'fragmentation', 'n_graded', 'per_class', 'alive_dead_f1')
    out = {key: score[key] for key in keys}
    out['spell_count_ratio'] = score['n_pred_spells'] / score['n_gt_spells'] if score['n_gt_spells'] else None
    out['transitions'] = {str(t): transitions_by_run(gt, filled, runs, t) for t in (12, 25)}
    out['short_spells'] = short_spells(gt, filled, runs)
    return out


def synthetic_checks():
    # Two short graded runs separated by X: matching must never cross the gap.
    gt = np.array([0, 1, 1, 3, 0, 0, 0], dtype=np.int8)
    pred = np.array([0, 0, 0, 3, 0, 1, 1], dtype=np.int8)
    got = transitions_by_run(gt, pred, pm.valid_runs(gt), 25)
    assert got['n_matched'] == 0 and got['n_missed'] == got['n_spurious'] == 1
    perfect = np.repeat([0, 1, 0, 1], [25, 26, 51, 126]).astype(np.int8)
    binned = short_spells(perfect, perfect, pm.valid_runs(perfect))
    assert all(v['n_gt'] == v['n_pred'] == 1 and v['recall_mean_iou'] == 1. for v in binned.values())
    assert transitions_by_run(perfect, perfect, pm.valid_runs(perfect), 12)['f1'] == 1.


def means(rows):
    return dict(n_rows=len(rows), spell_f1=float(np.mean([r['spell_f1_mean'] for r in rows])),
                macro_f1=float(np.mean([r['macro_f1'] for r in rows])),
                transition12=float(np.mean([r['transitions']['12']['f1'] for r in rows])),
                transition25=float(np.mean([r['transitions']['25']['f1'] for r in rows])),
                spell_count_ratio=float(np.mean([r['spell_count_ratio'] for r in rows])))


def summarize(rows):
    reference = {(r['match'], r['scenario']): r for r in rows if r['candidate'] == CANDIDATES[0]}
    summaries = []
    for name in CANDIDATES:
        group = [r for r in rows if r['candidate'] == name]
        for r in group:
            ref = reference[r['match'], r['scenario']]
            r['deltas_vs_p10'] = dict(spell_f1=r['spell_f1_mean'] - ref['spell_f1_mean'],
                                      macro_f1=r['macro_f1'] - ref['macro_f1'],
                                      transition25=r['transitions']['25']['f1'] - ref['transitions']['25']['f1'])
        delta = {key: float(np.mean([r['deltas_vs_p10'][key] for r in group]))
                 for key in ('spell_f1', 'macro_f1', 'transition25')}
        clean = float(np.mean([r['deltas_vs_p10']['spell_f1'] for r in group if r['scenario'] == 'original']))
        match_delta = {m: float(np.mean([r['deltas_vs_p10']['spell_f1'] for r in group if r['match'] == m]))
                       for pair in PAIRS for m in pair}
        checks = dict(spell_gain_ge_02=delta['spell_f1'] >= .02, macro_no_drop=delta['macro_f1'] >= 0.,
                      transition25_improves=delta['transition25'] > 0., clean_gain_positive=clean > 0.,
                      worst_match_ge_minus_05=min(match_delta.values()) >= -.05)
        summaries.append(dict(candidate=name, means=means(group),
                              by_scenario={s: means([r for r in group if r['scenario'] == s]) for s in SCENARIOS},
                              deltas_vs_p10=delta, clean_spell_delta=clean, match_spell_deltas=match_delta,
                              improved_matches=sum(v > 0 for v in match_delta.values()),
                              equal_matches=sum(v == 0 for v in match_delta.values()),
                              worse_matches=sum(v < 0 for v in match_delta.values()),
                              worst_row=min(group, key=lambda r: r['deltas_vs_p10']['spell_f1'])['match:scenario'],
                              negative_rows=[r['match:scenario'] for r in group if r['deltas_vs_p10']['spell_f1'] < 0],
                              gate_criteria=checks, gate_passed=all(checks.values()) if name != CANDIDATES[0] else False))
    passing = [s for s in summaries[1:] if s['gate_passed']]
    recommendation = CANDIDATES[0]
    if passing:
        best = max(s['means']['spell_f1'] for s in passing)
        recommendation = min((s for s in passing if best - s['means']['spell_f1'] <= .005),
                             key=lambda s: (-s['means']['macro_f1'], CANDIDATES.index(s['candidate'])))['candidate']
    return dict(candidates=summaries, recommendation=recommendation)


def write_report(result):
    lines = ['# V6 external transition diagnostic results', '',
             'These three decoder penalties and their headline scores were already evaluated in V2. '
             'New duration/transition diagnostics reuse six consumed matches and fixed out-of-fit predictions; '
             'all results are selection-conditioned development evidence. No target data or score was read. '
             'No fit, corruption, model, decoder, or release change was made.', '',
             f"Protocol commit: `{result['protocol_commit']}`; protocol SHA-256: `{PROTOCOL_SHA}`.", '',
             f"Recommendation: **retain {result['summary']['recommendation']}**.", '',
             '| Candidate | spellF1 | macroF1 | transition@12 | transition@25 | spell delta | macro delta | trans25 delta | gate |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for s in result['summary']['candidates']:
        m, d = s['means'], s['deltas_vs_p10']
        lines.append(f"| {s['candidate']} | {m['spell_f1']:.7f} | {m['macro_f1']:.7f} | {m['transition12']:.7f} | {m['transition25']:.7f} | {d['spell_f1']:+.7f} | {d['macro_f1']:+.7f} | {d['transition25']:+.7f} | {s['gate_passed']} |")
    for s in result['summary']['candidates']:
        lines += ['', f"## {s['candidate']}", '',
                  f"Gate criteria: `{json.dumps(s['gate_criteria'], sort_keys=True)}`. Clean spell delta {s['clean_spell_delta']:+.7f}.",
                  f"Match mean spell deltas: `{json.dumps(s['match_spell_deltas'], sort_keys=True)}`.",
                  f"Improved/equal/worse matches: {s['improved_matches']}/{s['equal_matches']}/{s['worse_matches']}. Worst row: {s['worst_row']}.", '',
                  '| Match | Scenario | spellF1 | macroF1 | T12 P/R/F1 | T25 P/R/F1 | spell count ratio | trans count ratio | spell delta |',
                  '|---|---|---:|---:|---|---|---:|---:|---:|']
        for r in result['rows']:
            if r['candidate'] != s['candidate']:
                continue
            ts = r['transitions']
            ttext = lambda t: '/'.join(f"{ts[t][k]:.4f}" for k in ('precision', 'recall', 'f1'))
            lines.append(f"| {r['match']} | {r['scenario']} | {r['spell_f1_mean']:.6f} | {r['macro_f1']:.6f} | {ttext('12')} | {ttext('25')} | {r['spell_count_ratio']:.4f} | {ts['25']['count_ratio']:.4f} | {r['deltas_vs_p10']['spell_f1']:+.6f} |")
        lines += ['', 'Duration bins below: GT/predicted counts and mean recall across official IoUs; counts are summed across 18 rows (each match appears in three corruption scenarios).', '',
                  '| Duration frames | GT count | Predicted count | mean row recall |', '|---|---:|---:|---:|']
        for b, _, _ in BINS:
            bs = [r['short_spells'][b] for r in result['rows'] if r['candidate'] == s['candidate']]
            rs = [v['recall_mean_iou'] for v in bs if v['recall_mean_iou'] is not None]
            lines.append(f"| {b} | {sum(v['n_gt'] for v in bs)} | {sum(v['n_pred'] for v in bs)} | {np.mean(rs):.6f} |")
    lines += ['', 'Machine-readable `v6-results.json` contains all 54 rows, per-class F1, per-row duration-bin counts/recalls, transition counts/latencies, scenario summaries, all paired deltas and input/source fingerprints. '
              'New transition matching is explicitly restricted within each GT-valid run; headline metrics use the unchanged official scorer. '
              'No hidden-score, independent-validation or target-improvement claim follows.']
    (ROOT / 'docs/experiments/V6_RESULTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def run(protocol_commit):
    if digest(PROTOCOL) != PROTOCOL_SHA:
        raise ValueError('protocol changed; root must freeze a new protocol before scoring')
    subprocess.run(['git', 'cat-file', '-e', protocol_commit + '^{commit}'], cwd=ROOT, check=True)
    committed = subprocess.check_output(['git', 'show', protocol_commit + ':docs/experiments/V6_PROTOCOL.md'], cwd=ROOT)
    if hashlib.sha256(committed).hexdigest() != PROTOCOL_SHA:
        raise ValueError('provided commit does not contain exact preregistration')
    synthetic_checks()
    inputs, rows, layouts = {}, [], []
    source_paths = ['evaluation/possession_metrics.py', 'malwarous/v6/study.py', 'configs/v2_candidate.json',
                    'malwarous/v2/model.py', 'models_private/v2-possession.joblib']
    frozen_before = {p: digest(ROOT / p) for p in source_paths if p != 'malwarous/v6/study.py'}
    for fold, pair in enumerate(PAIRS):
        for match in pair:
            for scenario in SCENARIOS:
                truths = []
                for half in (1, 2):
                    path = EXTERNAL / 'cache' / f'{match}-{scenario}-half{half}.npz'
                    inputs[str(path)] = digest(path)
                    with np.load(path, allow_pickle=False) as data:
                        truth = data['truth'].copy()
                        frames = data['frame_ids']
                        if truth.ndim != 1 or frames.shape != truth.shape or not np.isin(truth, range(4)).all():
                            raise ValueError('invalid external truth/frame alignment')
                        layouts.append(dict(path=str(path), keys=data.files, truth_shape=list(truth.shape),
                                            frame_ids_shape=list(frames.shape)))
                        truths.append(truth)
                truth = np.concatenate((truths[0], np.array([pm.X], dtype=np.int8), truths[1]))
                for candidate in CANDIDATES:
                    path = EXTERNAL / 'predictions' / f'{match}-{scenario}-{candidate}.npy'
                    # Missing prediction is a concrete stop; this runner never refits.
                    inputs[str(path)] = digest(path)
                    pred = np.load(path, allow_pickle=False)
                    if pred.shape != truth.shape or pred[len(truths[0])] != pm.X:
                        raise ValueError('cached prediction half boundary mismatch')
                    rows.append(dict(match=match, scenario=scenario, candidate=candidate, fold=fold,
                                     **{'match:scenario': match + ':' + scenario}, **metrics(truth, pred)))
                print(f'scored external {match} {scenario}', flush=True)
    summary = summarize(rows)
    assert len(rows) == 54
    if frozen_before != {p: digest(ROOT / p) for p in frozen_before}:
        raise ValueError('frozen file changed during study')
    result = dict(study='v6-reused-external-decoder-diagnostics', created_at=datetime.now(timezone.utc).isoformat(),
                  protocol_commit=protocol_commit, protocol_sha256=PROTOCOL_SHA,
                  evidence='selection-conditioned six-match development; candidates previously scored in V2',
                  source_sha256={p: digest(ROOT / p) for p in source_paths}, input_sha256=inputs,
                  cache_layouts=layouts, synthetic_checks='passed', frozen_files_unchanged=True,
                  rows=rows, summary=summary)
    for base in (ROOT / 'artifacts_private/v6', ROOT / 'docs/experiments'):
        base.mkdir(parents=True, exist_ok=True)
        (base / 'v6-results.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    write_report(result)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol-commit')
    parser.add_argument('--synthetic-only', action='store_true')
    args = parser.parse_args()
    if args.synthetic_only:
        synthetic_checks()
        print('Synthetic checks passed; no external labels/predictions read.')
    elif args.protocol_commit:
        run(args.protocol_commit)
    else:
        parser.error('--protocol-commit required before external scoring')
