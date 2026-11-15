"""Attach all registered external scenarios and credit to a public-data viewer bundle.

Run after malwarous.v2.export. Never accepts a private_local/target bundle.
The playback observations stay original; each benchmark's own scenario and whole-
match scope are explicit. The interface imports scores without recomputing them.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from workbench.server import validate_bundle

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'artifacts_private/v2/workbench-all-external.json'
MATCHES = {'J03WN1', 'J03WOY', 'J03WPY', 'J03WOH', 'J03WQQ', 'J03WR9'}


def main():
    bundle = json.loads(DESTINATION.read_text('utf-8'))
    if bundle['dataset']['kind'] != 'public_external' or bundle['dataset']['id'] != 'sportec-v2-development':
        raise ValueError('requires registered public external bundle')
    report_path = ROOT / 'docs/experiments/v2-benchmarks.json'
    report = json.loads(report_path.read_text('utf-8'))
    selected = report['summary']['selected']
    credit = ('Manuel Bassek, Robert Rein, Hendrik Weber and Daniel Memmert, '
              'An integrated dataset of spatiotemporal and event data in elite soccer. '
              'https://doi.org/10.6084/m9.figshare.28196177.v1 · CC BY 4.0. '
              'Our changes: coordinate conversion, thinned pitch samples, label mapping, '
              'synthetic dropout, learned predictions and benchmark measurements. '
              'Playback uses original observations; table rows name their own observation scenario.')
    bundle['dataset']['provenance'] = credit
    bundle['dataset']['license'] = 'https://creativecommons.org/licenses/by/4.0/'
    report_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
    for item in bundle['matches']:
        match = item['provenance']['match']
        if match not in MATCHES:
            raise ValueError('unregistered match')
        rows = [r for r in report['rows'] if r['match'] == match and r['candidate'] in ('v1_smooth50', selected)]
        if len(rows) != 6:
            raise ValueError('complete matched scenario rows required')
        benchmarks = []
        for row in rows:
            version = 'v1' if row['candidate'] == 'v1_smooth50' else 'v2'
            benchmarks.append(dict(version=f"{version} · {row['scenario']}", metric_source='official',
                spellF1=row['spell_f1_mean'], macroF1=row['macro_f1'], runtime_s=row['inference_seconds'],
                provenance=dict(model_version=row['candidate'], split=row['split'],
                    evaluator='Unmodified official evaluation/possession_metrics.py; bootstrap_n=0',
                    scope=f"{match}, both regulation halves; benchmark scenario {row['scenario']}; playback original half",
                    scenario=row['scenario'], n_gt_spells=row['n_gt_spells'], n_pred_spells=row['n_pred_spells'],
                    per_class=row['per_class'], report_sha256=report_hash,
                    runtime_scope=report['runtime_note'], uncertainty=report['summary']['uncertainty'])))
        item['benchmarks'] = benchmarks
    validate_bundle(bundle)
    temporary = DESTINATION.with_suffix('.pending.json')
    temporary.write_text(json.dumps(bundle, allow_nan=False, separators=(',', ':')), encoding='utf-8')
    temporary.replace(DESTINATION)
    print(json.dumps(dict(status='pass',source='licensed external only',
                          playback_halves=len(bundle['matches']), benchmark_rows_per_half=6)))


if __name__ == '__main__':
    main()
