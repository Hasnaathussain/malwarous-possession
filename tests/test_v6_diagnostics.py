"""External diagnostic matching and promotion criteria, with synthetic inputs only."""
import copy

import numpy as np
import pytest

from malwarous.v6.study import CANDIDATES, PAIRS, SCENARIOS, metrics, summarize, synthetic_checks


def test_run_boundaries_and_duration_bins():
    synthetic_checks()


def test_diagnostic_rejects_misaligned_or_invalid_predictions():
    with pytest.raises(ValueError):
        metrics(np.array([0, 1]), np.array([0]))
    with pytest.raises(ValueError):
        metrics(np.array([0, 1]), np.array([0, 5]))


def test_promotion_requires_all_registered_conditions():
    rows = []
    for candidate, gain, macro in zip(CANDIDATES, [0, .019, .021], [.7, .71, .69]):
        for pair in PAIRS:
            for match in pair:
                for scenario in SCENARIOS:
                    rows.append(dict(candidate=candidate, match=match, scenario=scenario,
                        **{'match:scenario': f'{match}:{scenario}'}, spell_f1_mean=.5+gain,
                        macro_f1=macro, spell_count_ratio=1., transitions={
                            '12': {'f1': .5+gain}, '25': {'f1': .5+gain}}))
    result = summarize(copy.deepcopy(rows))
    assert result['recommendation'] == CANDIDATES[0]
    assert not any(c['gate_passed'] for c in result['candidates'])
    # Sufficient primary gain cannot compensate for a macroF1 loss.
    assert result['candidates'][2]['gate_criteria']['spell_gain_ge_02']
    assert not result['candidates'][2]['gate_criteria']['macro_no_drop']
    for row in rows:
        if row['candidate'] == CANDIDATES[2]:
            row['macro_f1'] = .71
    assert summarize(rows)['recommendation'] == CANDIDATES[2]
