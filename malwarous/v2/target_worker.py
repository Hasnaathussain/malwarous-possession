"""Restricted local v2 computation. Never invoke directly or print data.

Only the safe runner launches this module, with stdout/stderr retained locally.
No ground-truth path is used, and no target score or agreement statistic is computed.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
TARGET_INPUTS = ('malwarous/v2/target_worker.py', 'malwarous/v2/safe_runner.py',
                 'malwarous/v2/finalize.py', 'malwarous/v2/export.py',
                 'workbench/server.py', 'workbench/demo.py',
                 'malwarous/metrica_ingest.py', 'malwarous/inference.py', 'games.py')
PRIVATE = ROOT / 'artifacts_private' / 'v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_guard():
    if os.environ.get('MALWAROUS_V2_SAFE_RUNNER') != '1':
        raise RuntimeError('use the status-only runner')
    try:
        connection = socket.socket()
    except OSError:
        return
    connection.close()
    raise RuntimeError('offline boundary is absent')


def locked_model():
    require_guard()
    # Verify the original fallback/official constants too; never modify its locks.
    from malwarous.private_worker import _locked_window
    _locked_window()
    manifest = json.loads((ROOT / 'configs/v2_candidate.json').read_text('utf-8'))
    if manifest['id'] != 'malwarous-v2-external-development':
        raise ValueError('invalid v2 candidate manifest')
    if set(manifest['target_source_sha256']) != set(TARGET_INPUTS):
        raise ValueError('target source manifest is incomplete')
    for name, digest in (manifest['study_source_sha256'] | manifest['target_source_sha256']).items():
        source = (ROOT / name).resolve()
        if ROOT.resolve() not in source.parents or source.suffix not in ('.py', '.lock'):
            raise ValueError('invalid source manifest path')
        if sha(source) != digest:
            raise ValueError('locked source differs')
    if sha(ROOT / 'docs/experiments/v2-results.json') != manifest['report_sha256']:
        raise ValueError('development report changed')
    report = json.loads((ROOT / 'docs/experiments/v2-results.json').read_text('utf-8'))
    if not report['summary']['development_gate_passed'] or report['summary']['selected'] != manifest['candidate']['name']:
        raise ValueError('external development gate not satisfied')
    expected_candidate = next(c for c in report['study']['protocol']['candidates']
                              if c['name'] == report['summary']['selected'])
    if manifest['candidate'] != expected_candidate:
        raise ValueError('decoder differs from selected definition')
    if manifest['model_relative_path'] != 'models_private/v2-possession.joblib':
        raise ValueError('unexpected local model path')
    model_path = ROOT / manifest['model_relative_path']
    if sha(model_path) != manifest['model_sha256']:
        raise ValueError('local model checksum differs')
    import joblib
    return manifest, joblib.load(model_path)


def generate():
    require_guard()
    import numpy as np
    from threadpoolctl import threadpool_limits
    from games import GAME, GAMES, asset_paths, source_frames, half_video_blocks, require
    from malwarous.metrica_ingest import team_slots_from_metadata, load_metrica_tracking
    manifest, model = locked_model()  # All gates precede target access.
    from .model import build_context, emissions, decode
    require(['atd_meta', 'atd_raw'], game=GAME)
    paths = asset_paths()
    count = source_frames('tactical')
    if count != 199319:
        raise ValueError('frame contract changed')
    pitch = GAMES[GAME]['pitch']
    tracking = load_metrica_tracking(paths['atd_raw'], team_slots_from_metadata(paths['atd_meta']),
                                    n_frames=count, pitch=pitch)
    labels = np.full(count, 3, dtype=np.int8)
    evidence = np.full((count, 3), np.nan, dtype=np.float32)
    feature_views = []
    candidate = manifest['candidate']
    with threadpool_limits(limits=1):
        for half, start, last in half_video_blocks(GAME):
            stop = last + 1
            centre = np.array(pitch, dtype=np.float32) / 2
            context = build_context(tracking.player_xy[start:stop] - centre,
                                    tracking.team_by_slot, tracking.ball_xy[start:stop] - centre,
                                    pitch=pitch, fps=25.)
            scores = emissions(model, context)
            if not np.isfinite(scores).all():
                raise ValueError('nonfinite evidence')
            labels[start:stop] = decode(scores, candidate['penalty'], candidate['radius'])
            evidence[start:stop] = scores
            feature_views.append((start, stop, context))
    return labels, evidence, tracking, feature_views, manifest


def export_local(labels, evidence, tracking, views, manifest):
    require_guard()
    import numpy as np
    from games import asset_paths, GAME, GAMES
    from malwarous.inference import official_csv_valid
    from evaluation.possession_metrics import read_label_csv, label_codes
    from workbench.server import validate_bundle
    from .export import spells
    destination = PRIVATE / 'local-viewer'
    destination.mkdir(parents=True, exist_ok=True)
    old_path = ROOT / 'artifacts_private/Malwarous.csv'
    predictions = dict(v2=dict(spells=spells(labels), provenance=dict(
        model_version=manifest['candidate']['name'], split='unlabelled_competition_inference',
        inference_mode='offline centered future context; no target score')))
    if old_path.exists() and official_csv_valid(old_path, n_expected=199319):
        predictions['v1'] = dict(spells=spells(label_codes(read_label_csv(old_path))),
                                 provenance=dict(model_version='locked smooth50 fallback',
                                                 split='unlabelled_competition_inference'))
    samples = []
    for start, stop, context in views:
        for frame in range(start, stop, 12):
            local = frame - start
            ball = tracking.ball_xy[frame]
            valid_ball = bool(np.isfinite(ball).all())
            players = [dict(id=f'slot{slot}', team='H' if side == 0 else 'A',
                            x=float(xy[0]), y=float(xy[1]))
                       for slot, (side, xy) in enumerate(zip(tracking.team_by_slot, tracking.player_xy[frame]))
                       if np.isfinite(xy).all()]
            samples.append(dict(t=frame / 25., players=players,
                ball=ball.astype(float).tolist() if valid_ball else None,
                quality=dict(ball_observed=valid_ball, player_coverage=min(1., len(players) / 22.)),
                evidence=dict(team_log_evidence=float(evidence[frame, 0] - evidence[frame, 1]),
                              dead_log_evidence=float(evidence[frame, 2]),
                              ball_support_4s=float(context.original[local, context.names.index('ball_support_4s')]))))
    pitch = GAMES[GAME]['pitch']
    match = dict(id='competition-local', title='Restricted local match', duration_s=199319 / 25.,
        pitch=dict(length_m=pitch[0], width_m=pitch[1]), samples=samples,
        media=dict(id='tactical-local', offset_s=0, fps=25),
        predictions=predictions, truth=[], benchmarks=[],
        provenance=dict(split='unlabelled_competition_inference', restricted=True,
                        evidence_type='predictions only; no measured accuracy; no invented confidence'),
        evidence_series=[dict(key=k, label=title, unit=unit, description=description)
            for k, title, unit, description in (
                ('team_log_evidence', 'Home vs away evidence', 'log ratio', 'Uncalibrated learned log-evidence difference before decoder.'),
                ('dead_log_evidence', 'Dead evidence', 'log score', 'Uncalibrated learned D score before decoder.'),
                ('ball_support_4s', 'Ball observation support', 'fraction', 'Observed ball fraction in centered four-second context.'))])
    bundle = dict(schema_version='1.0', dataset=dict(id='restricted-local',
        title='Restricted competition match · local only', kind='private_local',
        provenance='Restricted competition assets. Never upload, publish or capture through hosted tools.',
        split='Unlabelled local inference; no target metric or manual labels'), matches=[match])
    validate_bundle(bundle)
    (destination / 'bundle.json').write_text(json.dumps(bundle, allow_nan=False), encoding='utf-8')
    (destination / 'media-map.json').write_text(json.dumps({'tactical-local': asset_paths()['video']}), encoding='utf-8')
    # The broadcast recording has a different timeline. Do not invent an offset or
    # imply it is synchronized; it requires a separately validated automatic mapping.


def main():
    if os.environ.get('MALWAROUS_V2_SAFE_RUNNER') != '1':
        return 2
    try:
        socket.socket()
    except OSError:
        pass
    else:
        return 2
    job, status_path = sys.argv[1:]
    status = Path(status_path).resolve()
    expected_status_root = (ROOT / 'artifacts_private/runs').resolve()
    if status.parent != expected_status_root or not status.name.startswith('v2-') or status.suffix != '.json':
        return 2
    checks = dict(offline_guard='pass')
    state, failure = 'failed', 'INTERNAL_ERROR'
    try:
        from .safe_runner import JOBS
        if job not in JOBS:
            raise ValueError('unsupported job')
        from malwarous.inference import write_submission, official_csv_valid
        labels, evidence, tracking, views, manifest = generate()
        checks.update(frame_contract='pass', finite_evidence='pass')
        output = PRIVATE / 'Malwarous-v2.csv'
        if job == 'v2_target_infer':
            write_submission(output, labels, n_expected=199319)
            if not official_csv_valid(output, n_expected=199319):
                raise ValueError('invalid output CSV')
            checks['csv_contract'] = 'pass'
        elif job == 'v2_target_reproduce':
            reproduction = PRIVATE / '.v2-reproduction.csv'
            write_submission(reproduction, labels, n_expected=199319)
            if not output.exists() or sha(output) != sha(reproduction):
                raise ValueError('byte reproduction mismatch')
            checks['byte_reproduction'] = 'pass'
        else:
            export_local(labels, evidence, tracking, views, manifest)
        state, failure = 'completed', None
    except Exception:
        traceback.print_exc()  # Safe-runner log only, never returned to hosted tools.
    result = dict(job=job, status=state, checks=checks)
    if failure:
        result['failure_code'] = failure
    Path(status_path).write_text(json.dumps(result), encoding='utf-8')
    return 0 if state == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
