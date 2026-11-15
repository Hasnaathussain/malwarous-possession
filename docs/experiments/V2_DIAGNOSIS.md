# V2 diagnosis and bounded proposal

2026-11-14. Scope: repository code, ops records, and the aggregate public external reports only. No competition assets/output, external cached frame labels, or cached frame predictions were opened. This is a design diagnosis, not a new accuracy result. V1 locks, protocol, runner, and release remain untouched.

## What failed in v1

The public report makes fragmentation, rather than lack of frame discrimination, the first issue to fix. Values below come from `selection-v1.json`; counts are **H/A possession spells**, excluding D, as implemented in `evaluation/possession_metrics.py`.

| Condition | V1 full-control spellF1, WN1 / WOY | Predicted spells, WN1 / WOY | Smooth50 spellF1, WN1 / WOY |
|---|---:|---:|---:|
| Clean | .2141 / .2229 | 1,342 / 1,283 | .2838 / .2715 |
| Moderate | .0219 / .0177 | 3,276 / 3,470 | .2608 / .2601 |
| Severe | .0098 / .0068 | 3,449 / 3,727 | .2401 / .2442 |

There are 500 / 456 ground-truth H/A spells. Clean full-control macroF1 is .8277 / .8521, yet spellF1 loses to smooth50. The severe WOY geometry model makes 3,871 spells for 456 true spells and scores .0058. The best learned mean is .0822 versus smooth50 .2601. The report's selected geometry model (.0658) follows the registered simplicity tie rule; it is not the numerical learned maximum. This distinction does not change the failed comparison.

1. **Temporal evidence has the wrong scale.** `experiments._transition_matrix` charges only .4 or 1.0 log-score units for an H/A switch and .2-.8 for D entry/exit, while `temporal._decode_one` adds an emission every 40 ms. An internal H-A-H island only needs accumulated A-versus-H log odds above twice the turnover cost to survive. With a .4 cost, even one frame above odds exp(.8) can justify two switches. A D island is even cheaper (.4+.2 in the mild case). Smooth50 instead pools 101 frames, about four seconds, of team evidence. The v1 decoder does not have comparable persistence or a duration mechanism. Increasing turnover cost to 1 reduces clean counts and helps, but leaves D islands and noisy dropout evidence largely intact.

2. **Dropout erases the entire local control cue.** `features.build_features` sets both team distances to pitch diagonal, their difference to zero, and all proximity counts to zero when ball XY is missing. Only backward observation age survives. There is no last/next reliable control, observation fraction, local distance average, or vote support. A head must guess from almost identical missing-frame inputs. Across geometric mean-eight-frame blocks, guesses can alternate repeatedly with newly observed evidence. Training includes a 40% masked view, so this is not simply absent augmentation: the representation cannot retain control through gaps. Exact per-frame state transitions responsible for the aggregate failure cannot be established without a new permitted diagnostic run.

3. **Dead-ball errors split valid live spells.** `models.predict_log_emissions` multiplies the live and owner probabilities and injects D on every frame. Alive and owner heads are independently trained; there is no reliability gate or local context before decoding. A brief high D score can cut one true H spell into two. The official scorer matches same-team H/A spells one-to-one at IoUs .3/.4/.5/.6/.7; several small correct fragments cannot collectively rescue a spell. D is excluded from the spell list but D boundaries still cause this damage.

4. **Balanced outputs are not calibrated emissions.** `_new_model` fixes `class_weight='balanced'`. This changes the live/dead prior, and normalized products of separately reweighted probabilities do not restore it. Owner augmentation already balances home/away. V1 explicitly documents the values as evidence, so this is an explanation and a redesign opportunity, not a hidden contractual error. Constant transition costs need tuning against the actual emitted log-score scale.

5. **Several nominal features are constant during training.** `external_pipeline.load_feature_periods` and `corrupt_period` never pass player or tracker speeds to `build_features`; the external feature type contains only XY. Both tracker-speed features and four nearest-player-speed/validity features therefore stay zero. 'Full' mainly adds observed-track counts over geometry, not richer speed evidence. Motion speed is derived from ball XY and remains useful, but its validity flickers after gaps. Do not rely on target-only tracker speed in v2.

6. **The validation views are stress conditions, not independent matches.** Each corruption uses a deterministic match/period seed. Clean/moderate/severe share the same labels; they cannot be counted as six independent validation samples. Random synthetic ball masking also leaves every player track unchanged. It cannot establish robustness to all target tracker failures, source annotation differences, or informative camera visibility. This limits the claims even if v2 wins.

## Registered v2 design assessment

The authoritative bounded design is `V2_STUDY.md`, registered by the root agent before any new v2 score. It uses three grouped folds of the six consumed development matches, natural-prior shallow HGB, explicit context at 0.4/2/4 seconds, nearby-control inheritance and full-rate decoder costs 10/25/50, each with emission averaging radius 0/12. The weak-cost 1/1 decoder is diagnostic and ineligible for selection. This is a suitable first experiment: one fixed model family with reused emissions isolates whether proper persistence repairs fragmentation. Stronger penalties are hypotheses, not validated optima. No new grid is recommended after seeing results.

Implementation details that matter:

- Define whether context seconds mean radius or total width. The existing smooth50 window is +/-50 frames, 101 total frames, about four seconds; ambiguous timing can make supposedly equivalent context half as large.
- Compute context at full 25 Hz before selecting every fifth training row. Infer and decode every original frame so training subsampling does not quantize boundaries. Use equal match/view weighting if intended; frame-length imbalance otherwise remains under natural class priors.
- Use cumulative weighted sums and explicit valid-support denominators. Exclude diagonal distance sentinels and missing-frame zeros from geometric means. Pool vote support and observation fraction separately. Reset every forward/backward carry, rolling window and decoder at each half.
- Last/next control must carry only true observed geometric evidence, with capped age and explicit no-support flags. Never forward-fill labels or create an unbounded synthetic ball trajectory. Missing observations are uncertainty, not proof of D.
- Derive motion from XY in both domains; external tracker speed features are constant and target-only speed must not become a learned dependency. Robust short-window displacement with a validity mask is safer than treating zero as a measured stationary ball.
- Preserve exact H/A swapping for signed margins, nearest-team votes, counts, inherited control and output probabilities. Unknown labels remain excluded from losses. A tie convention must be deterministic and documented.
- Head class probabilities under natural priors are still not established calibration. Bound extreme log scores numerically so an isolated overconfident sample does not beat every transition cost. Average emissions independently inside each half; exclude boundary padding from the denominator. Larger costs must not become an undocumented hard minimum duration.
- A learned D override can split a correct H spell into two even when frame D-F1 improves. Count H/A spells and report their duration distribution; do not interpret total H/A/D segment counts as the official possession count.
- Three fold pipelines mean six binary-head fits when using separate alive/owner heads. Constrain OpenMP/BLAS threads and release raw coordinate arrays between matches. Cache observable context once per match/scenario; reuse fitted heads and emissions across all decoders.

A small explicit-duration or semi-Markov model is a possible later campaign, but adds risk now: label-dependent duration priors must stay within training folds, and a hard duration floor erases valid quick possessions. First measure the registered context-plus-persistence correction.

## Validation interpretation and pitfalls

All seven DFL matches, including formerly sealed J03WMX, have influenced v1 development or confidence. None is a fresh blind holdout. The registered v2 study excludes J03WMX initially and uses grouped out-of-fit predictions on six consumed matches. These predictions avoid fitting on each held-out match's labels, but selecting a candidate on the pooled results still makes them adaptive development evidence. A later confidence-only run on J03WMX would not restore blindness.

Keep both halves, every corruption view and every training augmentation of a match in one fold. Freeze protocol/code hashes, masks, seeds, model and selection gate before running. No per-match penalty adjustment. Any later calibration, duration prior or support threshold fitted from labels must use training-fold labels only. The registered severe corruption is 70% dropout with mean 25-frame blocks; v1 severe was 60% with mean eight-frame blocks. Their raw scores cannot be compared directly. The new smooth50 run on exactly the same observations is the valid paired comparator.

The primary metric remains the unmodified official mean spellF1 over IoUs .3/.4/.5/.6/.7, with same-team one-to-one matching. MacroF1 is secondary. Compute paired deltas on the same six matches/scenarios, aggregate scenarios within each match before uncertainty estimation, and report losses as well as means. Eighteen rows are six match clusters, not eighteen independent examples. The registered acceptance gate (+.02 mean gain, positive clean mean gain, no match average worse than -.05) is a development decision rule, not statistical proof of target improvement. With six matches, even a match bootstrap is descriptive and unstable.

Spell-count ratio is a useful failure alarm, never an optimization target alone: constant predictions can suppress fragmentation while merging true spells and destroying temporal IoU. Report at least clean/severe results separately, per-match deltas, official per-class F1, H/A spell counts, short-spell fractions, and boundary errors where permitted. Context can shift restart/turnover times enough to lose high-IoU matches even after counts improve.

No target assets or scores should resolve any of these choices. If the bounded campaign fails its gate, preserve the locked v1 recommendation and record the failure. If it passes, fit final v2 weights once on all registered training-development matches and lock the new artifacts before any private target job. V2 needs a separate reviewed inference manifest/status-only boundary, not a weakened or repointed v1 lock. No commit, publication, or submission is authorized by this diagnostic task.
