"""Produce compact, licensed external benchmark artifacts from the complete study.

The complete audit remains available locally. This export retains every candidate
and matched row without copying the scorer's large per-transition pairing lists.
"""
from __future__ import annotations
import hashlib
import json
from .study import ROOT, atomic_json


def main():
    full_path = ROOT / 'docs/experiments/v2-results.json'
    full = json.loads(full_path.read_text('utf-8'))
    summary = full['summary']
    selected = summary['selected']
    keys = ('match', 'fold', 'scenario', 'candidate', 'spell_f1_mean', 'macro_f1',
            'n_gt_spells', 'n_pred_spells', 'fragmentation', 'n_graded', 'per_class',
            'inference_seconds', 'feature_seconds', 'fit_seconds', 'split', 'metric_source')
    compact = dict(source='DFL/Sportec CC BY 4.0; https://doi.org/10.6084/m9.figshare.28196177',
                   interpretation=full['study']['protocol']['interpretation'],
                   full_report_sha256=hashlib.sha256(full_path.read_bytes()).hexdigest(),
                   study=full['study'], environment=full['environment'],
                   runtime_note=full['runtime_note'], summary=summary,
                   finished_at=full['finished_at'],
                   rows=[{k: row[k] for k in keys} for row in full['rows']])
    atomic_json(ROOT / 'docs/experiments/v2-benchmarks.json', compact)
    lines = ['# V2 paired external development results', '',
             'These are official-scorer measurements on six previously consumed external matches, '
             'with whole-match out-of-fit predictions and candidate selection on the pooled results. '
             '**Development evidence; not a blind test or a target-match score.**', '',
             f"Selected candidate: `{selected}`. Registered development promotion gate: "
             f"**{'PASS' if summary['development_gate_passed'] else 'FAIL'}**.", '',
             '| Candidate | Mean spellF1 | Clean spellF1 | Mean macroF1 | Rows |',
             '|---|---:|---:|---:|---:|']
    for row in summary['candidates']:
        lines.append(f"| {row['candidate']} | {row['mean_spell_f1']:.4f} | "
                     f"{row['mean_clean_spell_f1']:.4f} | {row['mean_macro_f1']:.4f} | {row['n_rows']} |")
    lines += ['', '## Paired per-match/scenario comparison', '',
              'Both methods use exactly the same observed inputs, dropout masks, full-rate labels '
              'and unmodified official evaluator. Scores cover both regulation halves; halftime '
              'is separated by an ungraded X. Spell counts below count H/A possessions, excluding D.', '',
              '| Match | Observation scenario | v1 spellF1 | v2 spellF1 | Δ | v1 macroF1 | v2 macroF1 | Truth / v1 / v2 spells | v1 / v2 seconds |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for row in full['rows']:
        if row['candidate'] != selected:
            continue
        old = next(r for r in full['rows'] if r['candidate'] == 'v1_smooth50' and
                   (r['match'], r['scenario']) == (row['match'], row['scenario']))
        lines.append(f"| {row['match']} | {row['scenario']} | {old['spell_f1_mean']:.4f} | "
                     f"{row['spell_f1_mean']:.4f} | {row['spell_f1_mean']-old['spell_f1_mean']:+.4f} | "
                     f"{old['macro_f1']:.4f} | {row['macro_f1']:.4f} | "
                     f"{row['n_gt_spells']} / {old['n_pred_spells']} / {row['n_pred_spells']} | "
                     f"{old['inference_seconds']:.2f} / {row['inference_seconds']:.2f} |")
    lo, hi = summary['paired_match_bootstrap_95pct']
    lines += ['', '## Uncertainty, failures and provenance', '',
              f"Scenario-averaged match deltas: {summary['matches_helped']} helped, "
              f"{summary['matches_hurt']} hurt. Descriptive match-cluster bootstrap 95% interval "
              f"for mean paired spellF1 difference: [{lo:+.4f}, {hi:+.4f}]. " + summary['uncertainty'], '',
              'Each match is one uncertainty cluster; correlated scenarios do not count as independent '
              'matches. No new independent dense H/A/D source was established. Provider labels, '
              'synthetic ball dropout and domain shift limit transfer claims. Raw model scores are '
              'uncalibrated evidence, not confidence.', '',
              full['runtime_note'], '',
              'Environment: `' + json.dumps(full['environment'], sort_keys=True) + '`.', '',
              'Protocol, exact source hashes, every candidate row and per-class diagnostics: '
              '[v2-benchmarks.json](v2-benchmarks.json). Full local audit SHA-256: '
              '`' + compact['full_report_sha256'] + '`.', '',
              'Source: DFL/Sportec open release, CC BY 4.0, '
              'https://doi.org/10.6084/m9.figshare.28196177. No competition assets, target labels, '
              'target-derived measurements or competitor outputs were used in this comparison.', '']
    (ROOT / 'docs/experiments/V2_RESULTS.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(dict(status='reported', selected=selected,
                          development_gate_passed=summary['development_gate_passed'], rows=len(full['rows']))))


if __name__ == '__main__':
    main()
