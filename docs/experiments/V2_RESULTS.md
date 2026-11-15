# V2 paired external development results

These are official-scorer measurements on six previously consumed external matches, with whole-match out-of-fit predictions and candidate selection on the pooled results. **Development evidence; not a blind test or a target-match score.**

Selected candidate: `context_p10_r0`. Registered development promotion gate: **PASS**.

| Candidate | Mean spellF1 | Clean spellF1 | Mean macroF1 | Rows |
|---|---:|---:|---:|---:|
| v1_smooth50 | 0.2555 | 0.3083 | 0.3981 | 18 |
| context_p10_r0 | 0.4810 | 0.5492 | 0.8687 | 18 |
| context_p10_r12 | 0.4807 | 0.5396 | 0.8656 | 18 |
| context_p25_r0 | 0.4721 | 0.5218 | 0.8697 | 18 |
| context_p25_r12 | 0.4698 | 0.5186 | 0.8666 | 18 |
| context_p50_r0 | 0.4437 | 0.4820 | 0.8694 | 18 |
| context_p50_r12 | 0.4413 | 0.4764 | 0.8658 | 18 |
| diagnostic_weak_p1_r0 | 0.4195 | 0.5055 | 0.8654 | 18 |

## Paired per-match/scenario comparison

Both methods use exactly the same observed inputs, dropout masks, full-rate labels and unmodified official evaluator. Scores cover both regulation halves; halftime is separated by an ungraded X. Spell counts below count H/A possessions, excluding D.

| Match | Observation scenario | v1 spellF1 | v2 spellF1 | Δ | v1 macroF1 | v2 macroF1 | Truth / v1 / v2 spells | v1 / v2 seconds |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| J03WN1 | original | 0.2838 | 0.5060 | +0.2223 | 0.3488 | 0.8852 | 500 / 436 / 296 | 0.24 / 13.03 |
| J03WN1 | drop40 | 0.2590 | 0.4719 | +0.2128 | 0.3444 | 0.8747 | 500 / 496 / 307 | 0.24 / 12.75 |
| J03WN1 | drop70 | 0.1671 | 0.3364 | +0.1693 | 0.3586 | 0.7595 | 500 / 757 / 330 | 0.27 / 12.21 |
| J03WOY | original | 0.2715 | 0.5269 | +0.2554 | 0.3759 | 0.8970 | 456 / 372 / 294 | 0.25 / 12.77 |
| J03WOY | drop40 | 0.2503 | 0.5077 | +0.2573 | 0.3717 | 0.8865 | 456 / 458 / 302 | 0.25 / 12.55 |
| J03WOY | drop70 | 0.1857 | 0.3597 | +0.1741 | 0.4154 | 0.7888 | 456 / 759 / 339 | 0.25 / 12.50 |
| J03WPY | original | 0.3171 | 0.5493 | +0.2323 | 0.3954 | 0.9152 | 421 / 375 / 270 | 0.26 / 13.02 |
| J03WPY | drop40 | 0.2672 | 0.5255 | +0.2583 | 0.3877 | 0.9053 | 421 / 519 / 280 | 0.25 / 12.84 |
| J03WPY | drop70 | 0.1803 | 0.3443 | +0.1640 | 0.4317 | 0.8100 | 421 / 715 / 354 | 0.25 / 12.87 |
| J03WOH | original | 0.3011 | 0.5734 | +0.2723 | 0.3849 | 0.9105 | 402 / 383 / 283 | 0.26 / 12.47 |
| J03WOH | drop40 | 0.2685 | 0.5514 | +0.2828 | 0.3763 | 0.8987 | 402 / 453 / 293 | 0.26 / 12.48 |
| J03WOH | drop70 | 0.1932 | 0.3839 | +0.1907 | 0.4188 | 0.8102 | 402 / 749 / 367 | 0.26 / 12.05 |
| J03WQQ | original | 0.3608 | 0.5838 | +0.2229 | 0.4162 | 0.9173 | 401 / 406 / 289 | 0.25 / 12.70 |
| J03WQQ | drop40 | 0.3152 | 0.5831 | +0.2679 | 0.4131 | 0.9108 | 401 / 524 / 311 | 0.25 / 13.07 |
| J03WQQ | drop70 | 0.2005 | 0.3909 | +0.1903 | 0.4630 | 0.8163 | 401 / 744 / 344 | 0.25 / 12.40 |
| J03WR9 | original | 0.3152 | 0.5555 | +0.2403 | 0.4095 | 0.9165 | 370 / 314 / 250 | 0.26 / 13.23 |
| J03WR9 | drop40 | 0.2766 | 0.5458 | +0.2692 | 0.4055 | 0.9104 | 370 / 405 / 261 | 0.25 / 12.72 |
| J03WR9 | drop70 | 0.1853 | 0.3616 | +0.1763 | 0.4484 | 0.8234 | 370 / 681 / 318 | 0.25 / 12.63 |

## Uncertainty, failures and provenance

Scenario-averaged match deltas: 6 helped, 0 hurt. Descriptive match-cluster bootstrap 95% interval for mean paired spellF1 difference: [+0.2143, +0.2368]. Descriptive six-match cluster bootstrap after candidate selection; not independent confirmation, not a target score.

Each match is one uncertainty cluster; correlated scenarios do not count as independent matches. No new independent dense H/A/D source was established. Provider labels, synthetic ball dropout and domain shift limit transfer claims. Raw model scores are uncalibrated evidence, not confidence.

v2 includes context construction, cache read + heads + decoder; v1 includes nearest geometry + smooth50; excludes scorer and XML ingest.

Environment: `{"numpy": "2.4.4", "python": "3.11.9", "sklearn": "1.9.1", "threads": 4}`.

Protocol, exact source hashes, every candidate row and per-class diagnostics: [v2-benchmarks.json](v2-benchmarks.json). Full local audit SHA-256: `743702395ee6e95a6bb769608527af95423c8ab7b34903182783241d6ff9e8e8`.

Source: DFL/Sportec open release, CC BY 4.0, https://doi.org/10.6084/m9.figshare.28196177. No competition assets, target labels, target-derived measurements or competitor outputs were used in this comparison.
