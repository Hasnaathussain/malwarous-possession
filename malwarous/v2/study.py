"""Bounded external-only paired study; never accepts competition assets.

Run ``python -m malwarous.v2.study``. A source/protocol ledger prevents silent
continuation of a changed campaign. Outputs under artifacts_private/v2 are external
development artifacts, separated from the immutable v1 release.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path
from time import perf_counter
from datetime import datetime, timezone
import zlib

import numpy as np
import sklearn
import joblib
from threadpoolctl import threadpool_limits

from malwarous.external_pipeline import (load_feature_periods, corrupt_period, source_files,
                                         nearest_smooth_predictions, labels_for_official_metrics)
from evaluation import possession_metrics as pm
from .model import build_context, ContextFeatures, fit_heads, emissions, decode, MODEL_SETTINGS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts_private' / 'v2'
PAIRS = (('J03WN1', 'J03WOY'), ('J03WPY', 'J03WOH'), ('J03WQQ', 'J03WR9'))
SCENARIOS = (('original', 0., 8), ('drop40', .4, 8), ('drop70', .7, 25))
CANDIDATES = tuple({'name': f'context_p{p}_r{r}', 'penalty': p, 'radius': r}
                   for p in (10, 25, 50) for r in (0, 12))
DIAGNOSTIC = {'name': 'diagnostic_weak_p1_r0', 'penalty': 1, 'radius': 0}
PROTOCOL = dict(id='v2-development-20261114', folds=PAIRS, scenarios=SCENARIOS,
                candidates=CANDIDATES, diagnostic=DIAGNOSTIC, seed=20261114,
                training_stride=5, train_scenarios=['original', 'drop40'],
                feature_context_total_width_s=[.4, 2., 4.], model=MODEL_SETTINGS,
                interpretation='consumed-source grouped development; not independent validation',
                selection='mean spellF1; within .005 macroF1, then penalty, then radius',
                replacement_gate='mean gain >=.02; clean gain >0; worst match mean delta >=-.05')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n',
                         encoding='utf-8')
    os.replace(temporary, path)


def fingerprint():
    paths = ['malwarous/v2/model.py', 'malwarous/v2/study.py',
             'malwarous/features.py', 'malwarous/temporal.py', 'malwarous/corruption.py',
             'malwarous/external_pipeline.py', 'malwarous/external_sportec.py',
             'evaluation/possession_metrics.py', 'starter/baseline.py', 'requirements.lock']
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def seed(match, half):
    return zlib.crc32(f'20261114:{match}:{half}'.encode('ascii'))


def verify_source(match):
    metadata, tracking = source_files(match)
    manifest = json.loads((metadata.parent / 'acquisition-manifest.json').read_text('utf-8'))
    if manifest['match_id'] != match or manifest['license'] != 'CC BY 4.0':
        raise ValueError('unexpected external source manifest')
    for path in (metadata, tracking):
        entry = next(f for f in manifest['files'] if f['name'] == path.name)
        digest = hashlib.md5(usedforsecurity=False)
        with path.open('rb') as f:
            while block := f.read(1024 * 1024):
                digest.update(block)
        if path.stat().st_size != entry['size'] or digest.hexdigest() != entry['md5']:
            raise ValueError('external source checksum mismatch')
    return manifest


def cache_path(match, scenario, half):
    return OUT / 'cache' / f'{match}-{scenario}-half{half}.npz'


def prepare(match, check):
    check()
    manifest = verify_source(match)
    periods = load_feature_periods(match)
    for scenario, fraction, block in SCENARIOS:
        for period in periods:
            check()
            path = cache_path(match, scenario, period.period_id)
            if path.exists():
                continue
            view = corrupt_period(period, fraction=fraction, seed=seed(match, period.period_id),
                                  mean_block_frames=block) if fraction else period
            source = view.source_features
            started = perf_counter()
            context = build_context(source.player_xy, source.team_by_player, source.ball_xy)
            feature_seconds = perf_counter() - started
            started = perf_counter()
            reference = nearest_smooth_predictions([view])
            reference_seconds = perf_counter() - started
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.pending.npz')
            np.savez(temp, x=context.original, sx=context.swapped, names=context.names,
                     base=context.base, status=period.status, owner=period.owner,
                     truth=labels_for_official_metrics(period.status, period.owner),
                     reference=reference, frame_ids=period.frame_ids,
                     feature_seconds=feature_seconds, reference_seconds=reference_seconds)
            os.replace(temp, path)
    return manifest


def train(matches, check):
    xs, sxs, statuses, owners = [], [], [], []
    names = None
    for match in matches:
        for scenario in PROTOCOL['train_scenarios']:
            for half in (1, 2):
                check()
                with np.load(cache_path(match, scenario, half), allow_pickle=False) as data:
                    names = tuple(data['names'])
                    # Context was computed at full 25 Hz before the deterministic sampling.
                    xs.append(data['x'][::5].copy())
                    sxs.append(data['sx'][::5].copy())
                    statuses.append(data['status'][::5].copy())
                    owners.append(data['owner'][::5].copy())
    return fit_heads(np.concatenate(xs), np.concatenate(sxs), np.concatenate(statuses),
                     np.concatenate(owners), names)


def join_halves(parts):
    return np.concatenate((parts[0], np.array([pm.X], dtype=np.int8), parts[1]))


def summarize_metric(truth, prediction):
    score = pm.evaluate(truth, prediction, bootstrap_n=0)
    keys = ['spell_f1_mean', 'macro_f1', 'n_gt_spells', 'n_pred_spells',
            'spell_count_error', 'fragmentation', 'n_graded', 'per_class', 'transitions',
            'alive_dead_f1', 'team_acc_gt_alive', 'n_abstain_on_graded', 'spell_f1']
    return {key: score[key] for key in keys}


def evaluate_match(model, match, fold, fit_seconds, check):
    rows = []
    for scenario, _, _ in SCENARIOS:
        check()
        evidence, truth, reference = [], [], []
        feature_seconds = reference_seconds = 0.
        inference_started = perf_counter()
        for half in (1, 2):
            with np.load(cache_path(match, scenario, half), allow_pickle=False) as d:
                context = ContextFeatures(d['x'], d['sx'], tuple(d['names']), d['base'])
                evidence.append(emissions(model, context))
                np.save(OUT / 'predictions' / f'{match}-{scenario}-half{half}-emissions.npy', evidence[-1])
                truth.append(d['truth'])
                reference.append(d['reference'])
                feature_seconds += float(d['feature_seconds'])
                reference_seconds += float(d['reference_seconds'])
        # Includes cache loading: conservative and explicitly labelled in report.
        emission_seconds = perf_counter() - inference_started
        truth = join_halves(truth)
        ref_prediction = join_halves(reference)
        common = dict(match=match, fold=fold, scenario=scenario, fit_seconds=fit_seconds,
                      feature_seconds=feature_seconds, metric_source='official',
                      split='grouped_out_of_fit_development', input_support='two regulation halves',
                      fps=25, label_source='DFL BallStatus/BallPossession', license='CC BY 4.0')
        rows.append(dict(common, candidate='v1_smooth50', inference_seconds=reference_seconds,
                         **summarize_metric(truth, ref_prediction)))
        np.save(OUT / 'predictions' / f'{match}-{scenario}-v1.npy', ref_prediction)
        for candidate in (*CANDIDATES, DIAGNOSTIC):
            check()
            started = perf_counter()
            prediction = join_halves([decode(e, candidate['penalty'], candidate['radius'])
                                      for e in evidence])
            runtime = feature_seconds + emission_seconds + perf_counter() - started
            rows.append(dict(common, candidate=candidate['name'], inference_seconds=runtime,
                             **summarize_metric(truth, prediction)))
            np.save(OUT / 'predictions' / f"{match}-{scenario}-{candidate['name']}.npy", prediction)
        print(json.dumps(dict(status='scored', match=match, scenario=scenario,
                              candidates=len(CANDIDATES) + 2)), flush=True)
    return rows


def summary(rows):
    names = ['v1_smooth50'] + [c['name'] for c in CANDIDATES] + [DIAGNOSTIC['name']]
    summaries = []
    for name in names:
        group = [r for r in rows if r['candidate'] == name]
        summaries.append(dict(candidate=name, mean_spell_f1=float(np.mean([r['spell_f1_mean'] for r in group])),
                              mean_macro_f1=float(np.mean([r['macro_f1'] for r in group])),
                              mean_clean_spell_f1=float(np.mean([r['spell_f1_mean'] for r in group if r['scenario'] == 'original'])),
                              n_rows=len(group)))
    eligible = [s for s in summaries if s['candidate'].startswith('context_')]
    best = max(s['mean_spell_f1'] for s in eligible)
    lookup = {c['name']: c for c in CANDIDATES}
    selected = min((s for s in eligible if best - s['mean_spell_f1'] <= .005),
                   key=lambda s: (-s['mean_macro_f1'], lookup[s['candidate']]['penalty'],
                                  lookup[s['candidate']]['radius']))
    baseline = summaries[0]
    deltas = []
    for pair in PAIRS:
        for match in pair:
            candidate = [r for r in rows if r['match'] == match and r['candidate'] == selected['candidate']]
            reference = [r for r in rows if r['match'] == match and r['candidate'] == 'v1_smooth50']
            delta = float(np.mean([r['spell_f1_mean'] for r in candidate]) -
                          np.mean([r['spell_f1_mean'] for r in reference]))
            deltas.append(dict(match=match, mean_paired_spell_delta=delta))
    rng = np.random.default_rng(20261114)
    values = np.array([r['mean_paired_spell_delta'] for r in deltas])
    boot = rng.choice(values, size=(5000, len(values)), replace=True).mean(axis=1)
    gate = (selected['mean_spell_f1'] - baseline['mean_spell_f1'] >= .02 and
            selected['mean_clean_spell_f1'] > baseline['mean_clean_spell_f1'] and
            float(values.min()) >= -.05)
    return dict(candidates=summaries, selected=selected['candidate'], development_gate_passed=bool(gate),
                paired_match_deltas=deltas, matches_helped=int((values > 0).sum()),
                matches_hurt=int((values < 0).sum()),
                paired_match_bootstrap_95pct=np.quantile(boot, [.025, .975]).tolist(),
                uncertainty='Descriptive six-match cluster bootstrap after candidate selection; '
                            'not independent confirmation, not a target score.')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    stamp = dict(protocol=PROTOCOL, source_sha256=fingerprint())
    ledger = OUT / 'study-ledger.json'
    if ledger.exists():
        existing = json.loads(ledger.read_text('utf-8'))
        if canonical(existing['definition']) != canonical(stamp):
            raise RuntimeError('campaign sources/protocol changed; record a separate study amendment')
        if existing.get('status') == 'completed':
            print(json.dumps(dict(status='already_completed', report='docs/experiments/v2-results.json')))
            return 0
    else:
        atomic_json(ledger, dict(definition=stamp, status='started',
                                started_at=datetime.now(timezone.utc).isoformat()))
    initial_start = datetime.fromisoformat(json.loads(ledger.read_text('utf-8'))['started_at'])
    def check():
        if (datetime.now(timezone.utc) - initial_start).total_seconds() > 8 * 3600:
            raise TimeoutError('v2 cumulative campaign eight-hour budget exhausted')
    # A process-level exclusive lock prevents duplicate campaign jobs.
    lock = OUT / 'active.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, str(os.getpid()).encode('ascii'))
        (OUT / 'predictions').mkdir(exist_ok=True)
        with threadpool_limits(limits=4):
            manifests = {}
            for pair in PAIRS:
                for match in pair:
                    manifests[match] = prepare(match, check)
                    print(json.dumps(dict(status='prepared', match=match)), flush=True)
            rows = []
            for fold, pair in enumerate(PAIRS):
                checkpoint = OUT / f'fold{fold}.json'
                if checkpoint.exists():
                    rows.extend(json.loads(checkpoint.read_text('utf-8')))
                    continue
                matches = [m for other in PAIRS for m in other if m not in pair]
                fit_started = perf_counter()
                model = train(matches, check)
                fit_seconds = perf_counter() - fit_started
                (OUT / 'models').mkdir(exist_ok=True)
                joblib.dump(model, OUT / 'models' / f'fold{fold}.joblib')
                print(json.dumps(dict(status='fitted', fold=fold, fit_seconds=fit_seconds)), flush=True)
                fold_rows = []
                for match in pair:
                    fold_rows.extend(evaluate_match(model, match, fold, fit_seconds, check))
                atomic_json(checkpoint, fold_rows)
                rows.extend(fold_rows)
                del model
            report = dict(study=stamp, source_manifests=manifests, rows=rows, summary=summary(rows),
                          prediction_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in sorted((OUT / 'predictions').glob('*.npy'))},
                          environment=dict(python=platform.python_version(), numpy=np.__version__,
                                           sklearn=sklearn.__version__, threads=4),
                          finished_at=datetime.now(timezone.utc).isoformat(),
                          elapsed_seconds=perf_counter() - started,
                          runtime_note='v2 includes context construction, cache read + heads + decoder; '
                                       'v1 includes nearest geometry + smooth50; excludes scorer and XML ingest.')
            atomic_json(ROOT / 'docs' / 'experiments' / 'v2-results.json', report)
            state = json.loads(ledger.read_text('utf-8'))
            state.update(status='completed', finished_at=report['finished_at'])
            atomic_json(ledger, state)
            print(json.dumps(dict(status='completed', summary=report['summary'])), flush=True)
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
