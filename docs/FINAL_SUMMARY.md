# Final method and evidence

The selected pipeline remains **V2 `context_p10_r0`**. It uses 65 observable
features, natural-prior alive/owner gradient-boosted heads, team symmetry and an
offline half-wise persistence decoder. Missing observations are explicit support
information. Track slots are not treated as player identities.

| Matched six-match development | Mean spellF1 | Mean macroF1 |
|---|---:|---:|
| smooth50 reference | 0.25548 | 0.39809 |
| selected V2 | 0.48095 | 0.86868 |

These measurements use three whole-match excluded folds and original/drop40/drop70
views on six previously consumed DFL/Sportec matches. Evaluation matches are
excluded from their model fits; pooled selection is still adaptive development,
not independent confirmation. The official scorer is unchanged. Full V2 evidence
and source pins remain in [the protocol](experiments/V2_STUDY.md),
[results](experiments/V2_RESULTS.md) and accompanying JSON.

The actual all-six fitted artifact additionally reached spellF1 **0.5240** and
macroF1 **0.9185** on J03WMX, excluded from V2 fitting/selection but already used
in a V1 audit. That is a descriptive artifact check, not a fresh test or a target
score. See [the fixed check](experiments/FINAL_EXTERNAL_RESULTS.md).

## Why later experiments were not shipped

| Experiment | Mean spellF1 | Replacement verdict |
|---|---:|---|
| Directed turnover contrast, V3 | 0.48716 | Failed registered meaningful-gain gate |
| Contact specialist, V4 | 0.48658 | Failed replacement and added-value gates |
| Spell-balanced ownership, V5 selected mixture | 0.48475 | Failed replacement and added-value gates |

V5 was the final bounded attempt: one owner head per excluded fold, using clipped
square-root inverse spell-length training weights derived at full rate before
sampling; the existing V2 alive/dead evidence was preserved. Its two fixed mixture
variants and baseline completed all 54 rows. The registered selection rule allowed
a .005 spellF1 tie range then used macroF1; it selected the half-strength mixture.
The full-strength mixture reached 0.48575, still below the meaningful replacement
gate. No additional candidates were introduced after scores.

The selected V5 gain was +0.00380, below the predeclared +0.02 minimum and the required
added value over the best earlier alternative. Clean performance and macroF1
improved slightly; five match-average differences were positive and one was
negative. No all-six V5 fit or target inference was performed. The internal
research workspace retains the complete protocols, reports and unsuccessful code;
inactive experimental versions are omitted from this concise source edition.

Short spells, provider-label semantics, synthetic dropout realism and transfer to
automatic competition tracking remain limitations. No target score, rank,
calibrated confidence or real-time inference claim is established.

## Source and reproduction

The included model was fitted only on J03WN1, J03WOY, J03WPY, J03WOH, J03WQQ and
J03WR9, original/drop40 views, stride 5 after full-rate context. The frozen config
and source/report/model hashes are verified before target processing. Model SHA256:
`c6deb427e42dca2b2d35ffa47576f4fbb94509729c0216b46312b1f367c2418d`.

Data credit: Manuel Bassek, Robert Rein, Hendrik Weber and Daniel Memmert,
*An integrated dataset of spatiotemporal and event data in elite soccer*,
[version 1](https://doi.org/10.6084/m9.figshare.28196177.v1), CC BY 4.0.
Derived features, masks, models and benchmark results are project modifications.

Use [the technical note](TECHNICAL_NOTE.md) and the top-level README for exact
inference/reproduction commands. Use [the team protocol](TEAM_COMPARISON.md) to
compare teammates on aligned external data. The short note and repository must
describe whichever complete pipeline the team ultimately chooses.

## Final registered decoder audit

V6 re-examined already consumed p10/p25/p50 predictions on all18 external rows. Mean spellF1: p10 0.4809519, p25 0.4721337, p50 0.4437200. Mean transition F1@25: 0.5154486, 0.5076051, 0.4928354. Both alternatives failed the preregistered conjunctive gate; the frozen candidate and final CSV are unchanged. This is reused development evidence, not a new holdout. Smart Tagging fusion was not qualified externally; approximate tag windows cannot safely become hard D intervals. Full rows/losses: [V6 results](experiments/V6_RESULTS.md).
