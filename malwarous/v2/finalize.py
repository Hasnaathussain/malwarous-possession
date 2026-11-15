"""Train the selected v2 candidate on licensed external development matches only.

Refuses to replace v1 or proceed without the registered paired development gate.
No target files or public target labels are read here.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from time import perf_counter
import joblib
from threadpoolctl import threadpool_limits
from .study import ROOT, OUT, PAIRS, CANDIDATES, train, fingerprint, atomic_json


def main():
    report_path = ROOT / 'docs/experiments/v2-results.json'
    report = json.loads(report_path.read_text('utf-8'))
    if report['study']['source_sha256'] != fingerprint():
        raise ValueError('study source changed')
    if not report['summary']['development_gate_passed']:
        print(json.dumps(dict(status='not_promoted', reason='registered_development_gate_failed')))
        return 0
    manifest_path = ROOT / 'configs/v2_candidate.json'
    model_path = ROOT / 'models_private/v2-possession.joblib'
    if manifest_path.exists() or model_path.exists():
        raise FileExistsError('v2 final artifact already exists; refusing silent replacement')
    started = perf_counter()
    def check():
        if perf_counter() - started > 3600:
            raise TimeoutError('final external fit exceeded one-hour budget')
    matches = [m for pair in PAIRS for m in pair]
    with threadpool_limits(limits=4):
        model = train(matches, check)
    check()
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    candidate = next(c for c in CANDIDATES if c['name'] == report['summary']['selected'])
    from .target_worker import TARGET_INPUTS
    manifest = dict(id='malwarous-v2-external-development', candidate=candidate,
        model_relative_path='models_private/v2-possession.joblib',
        model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
        report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
        study_source_sha256=report['study']['source_sha256'],
        target_source_sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in TARGET_INPUTS},
        feature_names=list(model.feature_names), training_matches=matches,
        training_views=['original', 'drop40'], training_stride=5,
        frozen_at=datetime.now(timezone.utc).isoformat(), fit_seconds=perf_counter() - started,
        evidence='Grouped out-of-fit development on previously consumed matches; '
                 'selection-conditioned; target improvement unmeasured; no independent test.',
        inference_mode='offline, centered future context; pitch-centred metric coordinates',
        v1_preserved=True)
    atomic_json(manifest_path, manifest)
    print(json.dumps(dict(status='frozen', candidate=candidate['name'], training_matches=len(matches),
                          fit_seconds=manifest['fit_seconds'], target_data_used=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
