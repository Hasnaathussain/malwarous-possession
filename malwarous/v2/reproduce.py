"""Reproduce a completed external fold's predictions from its locally fitted model.

This command has no competition-input path. It checks exact array equality, not a
rounded metric, and verifies the campaign's registered source and prediction hashes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from .model import ContextFeatures, emissions, decode
from .study import ROOT, OUT, PAIRS, SCENARIOS, CANDIDATES, fingerprint, join_halves, cache_path


def reproduce_fold(fold):
    report = json.loads((ROOT / 'docs/experiments/v2-results.json').read_text('utf-8'))
    if fingerprint() != report['study']['source_sha256']:
        raise ValueError('study source fingerprint differs')
    candidate = next(c for c in CANDIDATES if c['name'] == report['summary']['selected'])
    # Only load a model produced locally by this study; never accept a caller's pickle path.
    model = joblib.load(OUT / 'models' / f'fold{fold}.joblib')
    checked = 0
    with threadpool_limits(limits=4):
        for match in PAIRS[fold]:
            for scenario, _, _ in SCENARIOS:
                halves = []
                for half in (1, 2):
                    with np.load(cache_path(match, scenario, half), allow_pickle=False) as d:
                        context = ContextFeatures(d['x'], d['sx'], tuple(d['names']), d['base'])
                        halves.append(decode(emissions(model, context), candidate['penalty'], candidate['radius']))
                prediction = join_halves(halves)
                path = OUT / 'predictions' / f"{match}-{scenario}-{candidate['name']}.npy"
                if hashlib.sha256(path.read_bytes()).hexdigest() != report['prediction_sha256'][path.name]:
                    raise ValueError('saved prediction hash differs')
                if not np.array_equal(prediction, np.load(path, allow_pickle=False)):
                    raise ValueError('reproduced external predictions differ')
                checked += 1
    return dict(status='pass', check='exact_external_prediction_reproduction', fold=fold, scenarios=checked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', type=int, choices=range(len(PAIRS)), default=0)
    args = parser.parse_args()
    print(json.dumps(reproduce_fold(args.fold)))


if __name__ == '__main__':
    main()
