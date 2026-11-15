"""Export licensed external study evidence into the local workbench contract.

No target input argument exists. Frame labels and predictions remain at 25 Hz;
only pitch samples are thinned for browser rendering. Benchmark scope is the full
two-half match/scenario even when the selected playback item is one half.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from malwarous.external_pipeline import load_feature_periods, corrupt_period
from .study import ROOT, OUT, PAIRS, SCENARIOS, seed, atomic_json

LABELS = ('H', 'A', 'D', 'X')


def spells(codes, fps=25.):
    codes = np.asarray(codes)
    starts = np.r_[0, np.flatnonzero(codes[1:] != codes[:-1]) + 1]
    stops = np.r_[starts[1:], len(codes)]
    return [dict(start_s=float(a / fps), end_s=float(b / fps), state=LABELS[int(codes[a])])
            for a, b in zip(starts, stops) if b > a]


def export(matches, scenario, destination):
    report = json.loads((ROOT / 'docs/experiments/v2-results.json').read_text('utf-8'))
    chosen = report['summary']['selected']
    allowed = {m for pair in PAIRS for m in pair}
    if not set(matches) <= allowed:
        raise ValueError('only registered public external matches may be exported')
    fraction, block = next((f, b) for s, f, b in SCENARIOS if s == scenario)
    bundle = dict(schema_version='1.0', dataset=dict(
        id='sportec-v2-development', title='Possession Lab · DFL external development',
        kind='public_external', license='CC BY 4.0',
        provenance='DFL/Sportec open release https://doi.org/10.6084/m9.figshare.28196177; '
                   'positions and provider BallStatus/BallPossession. No competition data.',
        split='Three fixed whole-match grouped folds; all sources consumed previously; '
              'development comparison after candidate selection, not independent validation.'), matches=[])
    for match in matches:
        clean = load_feature_periods(match)
        views = [corrupt_period(p, fraction=fraction, seed=seed(match, p.period_id),
                                mean_block_frames=block) if fraction else p for p in clean]
        prediction = np.load(OUT / 'predictions' / f'{match}-{scenario}-{chosen}.npy', allow_pickle=False)
        reference = np.load(OUT / 'predictions' / f'{match}-{scenario}-v1.npy', allow_pickle=False)
        offset = 0
        for period in views:
            n = len(period.frame_ids)
            source = period.source_features
            half = period.period_id
            with np.load(OUT / 'cache' / f'{match}-{scenario}-half{half}.npz', allow_pickle=False) as d:
                truth = d['truth']
                base = d['base']
                names = list(d['names'])
                support = d['x'][:, names.index('ball_support_4s')]
                margin = d['x'][:, names.index('control_margin_m')]
                previous = d['x'][:, names.index('previous_control')]
                previous_age = d['x'][:, names.index('previous_control_age_s')]
            evidence = np.load(OUT / 'predictions' / f'{match}-{scenario}-half{half}-emissions.npy', allow_pickle=False)
            samples = []
            for i in range(0, n, 12):
                ball = source.ball_xy[i]
                observed = bool(np.isfinite(ball).all())
                players = [dict(id=f'slot{j}', team='H' if side == 0 else 'A',
                                x=float(xy[0]) + 52.5, y=float(xy[1]) + 34.)
                           for j, (xy, side) in enumerate(zip(source.player_xy[i], source.team_by_player))
                           if np.isfinite(xy).all()]
                samples.append(dict(t=i / 25., ball=(ball + np.array([52.5, 34.])).astype(float).tolist() if observed else None,
                                    players=players, quality=dict(ball_observed=observed,
                                        player_coverage=min(1., len(players) / 22.),
                                        ball_age_s=float(base[i, 5])),
                                    evidence=dict(control_margin=float(margin[i]) if observed else None,
                                        ball_support_4s=float(support[i]),
                                        previous_control=float(previous[i]),
                                        previous_control_age_s=float(previous_age[i]),
                                        team_log_evidence=float(evidence[i, 0] - evidence[i, 1]),
                                        dead_log_evidence=float(evidence[i, 2]))))
            benchmarks = []
            for version, candidate in (('v1', 'v1_smooth50'), ('v2', chosen)):
                row = next(r for r in report['rows'] if r['match'] == match and
                           r['scenario'] == scenario and r['candidate'] == candidate)
                benchmarks.append(dict(version=version, metric_source='official',
                    spellF1=row['spell_f1_mean'], macroF1=row['macro_f1'],
                    runtime_s=row['inference_seconds'],
                    provenance=dict(model_version=candidate, split=row['split'],
                        evaluator='Unmodified official evaluation/possession_metrics.py; bootstrap_n=0',
                        scope=f'{match} {scenario}, both regulation halves; not just this playback half',
                        source_manifest_sha256=hashlib.sha256(json.dumps(report['study']['source_sha256'],
                            sort_keys=True).encode()).hexdigest(),
                        n_gt_spells=row['n_gt_spells'], n_pred_spells=row['n_pred_spells'],
                        per_class=row['per_class'],
                        transitions={tau: {key: value for key, value in scores.items()
                                           if key not in ('pairs', 'missed', 'spurious')}
                                     for tau, scores in row['transitions'].items()},
                        uncertainty=report['summary']['uncertainty'])))
            provenance = dict(split='grouped_out_of_fit_development', fps=25,
                              scenario=scenario, label_semantics='Provider active/inactive and team ownership',
                              inference_mode='offline; centered future context',
                              benchmark_scope='full match, both halves',
                              observation_sample_hz=25 / 12,
                              prediction_hz=25,
                              match=match, half=half)
            bundle['matches'].append(dict(id=f'{match}-{scenario}-half{half}',
                title=f'{match} · half {half} · {scenario}', duration_s=n / 25.,
                pitch=dict(length_m=105., width_m=68.), sample_hz=25 / 12,
                provenance=provenance, samples=samples, truth=spells(truth),
                predictions=dict(v1=dict(spells=spells(reference[offset:offset+n]),
                                          provenance=dict(provenance, model_version='nearest smooth50')),
                                 v2=dict(spells=spells(prediction[offset:offset+n]),
                                          provenance=dict(provenance, model_version=chosen))),
                evidence_series=[dict(key=k, label=label, unit=unit, description=description)
                    for k, label, unit, description in (
                        ('control_margin', 'Away minus home distance', 'm', 'Observable geometric margin; positive favors home. Null when ball absent.'),
                        ('ball_support_4s', 'Ball observation support', 'fraction', 'Observed ball fraction in centered four-second window.'),
                        ('previous_control', 'Previous nearby control', 'signed', 'Geometric control observation: +1 home, -1 away, 0 unsupported; not a label.'),
                        ('previous_control_age_s', 'Previous control age', 's', 'Time since observable nearby control; capped at five seconds.'),
                        ('team_log_evidence', 'Home vs away model evidence', 'log ratio', 'Raw learned H/A log-evidence difference; uncalibrated, not confidence.'),
                        ('dead_log_evidence', 'Dead model evidence', 'log score', 'Raw learned D log evidence before temporal decoding; uncalibrated.'))],
                benchmarks=benchmarks))
            offset += n + 1
    from workbench.server import validate_bundle
    validate_bundle(bundle)
    atomic_json(destination, bundle)
    return dict(status='exported', matches=len(bundle['matches']), scenario=scenario,
                source='licensed external development only', destination=str(destination))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--matches', nargs='+', default=['J03WN1'])
    p.add_argument('--scenario', choices=[s for s, _, _ in SCENARIOS], default='original')
    p.add_argument('--output', type=Path, default=OUT / 'workbench-external.json')
    a = p.parse_args()
    print(json.dumps(export(a.matches, a.scenario, a.output)))


if __name__ == '__main__':
    main()
