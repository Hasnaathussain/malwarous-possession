# Malwarous: contextual possession engine

Muhammad Hasnaat Hussain | Kabir Niazi | Younus Rehmatullah

Selected method: **context_p10_r0**. The fitted artifact and inference pipeline are frozen. Earlier reference dependencies are retained for reproducibility.

## Method

The engine writes one algorithmic H/A/D/X label for each of the 199,319 tactical-video frames. Missing ball observations do not automatically mean dead ball. Possession is inferred as a persistent team state; anonymous tracking slots are not treated as player identities.

One continuous half at a time is converted into 65 observable features: nearest-team geometry, nearby-player counts, ball motion and its validity, observation age/support, pitch-edge evidence, and valid-support context over 0.4, 2 and 4 seconds. Bounded previous/next geometric control observations preserve evidence through short outages. Unsupported distances never enter contextual means as physical measurements. Features receive no possession labels, match identity or absolute match time.

Two histogram gradient boosting heads estimate alive/dead and live H/A evidence without class-reweighting, using 100 iterations, at most 15 leaves, leaf support 100 and L2 regularization 5. Team-swap augmentation balances owner H/A counts; symmetric prediction enforces H/A equivariance. Their uncalibrated evidence is combined into three log scores. Viterbi decoding uses a fixed 10 log-score switching penalty and resets between the official halves; frames outside those blocks are X. Centered context, next observations and sequence decoding make the method offline.

## Possession rules and transfer

External supervision maps provider BallStatus 0 to D regardless of owner; active status 1 with BallPossession 1/2 supplies H/A. Unknown supervision is excluded from the corresponding head. Provider semantics are inherited, not independently established as equivalent to the challenge.

The challenge retains the last controlled side through loose balls and challenges, excludes mere touches/deflections as turnovers, and treats stoppages as ownerless D. Our learned evidence plus penalty-10 decoder only approximates those rules: there is no hard last-owner hold, contact/duel classifier, referee or restart detector. Restart sides are learned rather than imposed from tags. Missing ball coordinates alone do not force D; graded halves are decoded into H/A/D and outside-half blocks are X. No hard minimum spell length is imposed. [Full operational comparison](POSSESSION_RULES.md).

## External evidence

Six licensed DFL/Sportec matches were already consumed during earlier development. Provider BallStatus and BallPossession fields supply the external H/A/D supervision; no target-match human labels are used. Three fixed whole-match folds trained on four matches and predicted the other two. Candidate selection used pooled development results. The final artifact was then fitted on all six; cross-validation scores belong to the excluded-match predictors, not training-set evaluations of that final artifact.

Each method used identical observations, masks and graded support with the unmodified official scorer. The fixed scenarios were original observations, 40% block ball dropout with mean block 8 frames, and 70% dropout with mean block 25 frames. Primary spellF1 averages the official temporal-IoU thresholds; macroF1 is reported alongside it.

| Observation scenario | v1 spellF1 | v2 spellF1 |
|---|---:|---:|
| Original | 0.3083 | 0.5492 |
| Drop40 | 0.2728 | 0.5309 |
| Drop70 | 0.1854 | 0.3628 |
| Mean of 18 matched rows | 0.2555 | 0.4810 |

Mean macroF1 increased from 0.3981 to 0.8687. All 18 paired scenario differences were positive. These are three correlated views of each of six reused matches, not 18 independent matches. A descriptive six-match bootstrap interval for the mean spellF1 difference was [+0.2143,+0.2368], after candidate selection; it is not an independent confirmation interval. Subsequent registered boundary, contact-specialist and spell-balanced training studies failed their replacement gates, so this candidate remained unchanged.

A final fixed artifact check on J03WMX, excluded from v2 fitting/selection but previously consumed in the v1 audit, scored **0.5240 spellF1 and 0.9185 macroF1**, versus v1's 0.3072 and 0.4150 on identical clean inputs. This descriptive check did not select, tune or retrain the model. It is not a fresh blind test or a target-match score.

## Reproduction and workbench

Use the included checksum-verified external-only fitted weights with 64-bit Python 3.11.9 and the pinned dependencies. No training/finalizer step is required for the frozen source distribution. Source, report and model hashes are checked before target inputs are opened. From a separate working copy:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
$env:MTAH_DATA_DIR='D:\path\to\authorized\mtah2027-bundle'
.\.venv\Scripts\python.exe -m malwarous.v2.safe_runner v2_target_infer
.\.venv\Scripts\python.exe -m malwarous.v2.safe_runner v2_target_reproduce
```

Check each command's exit status before proceeding. The output is `artifacts_private/v2/Malwarous-v2.csv`. Local inference passed the official CSV/frame contract and exact byte reproduction. All 18 selected external fold predictions also reproduced exactly. Child diagnostics and restricted outputs stay local; terminal responses contain fixed status checks only. No target truth was used for fitting, tuning or selection; no human target annotation was created. A separately registered one-time public-window pipeline check was later run locally on the frozen CSV with the unmodified official evaluator. Its result did not affect the candidate or output.

The local workbench synchronizes optional video, pitch observations and H/A/D/X intervals. It provides frame seeking/stepping, timeline/evidence zoom, observation-quality indicators, supplied decision evidence, labelled-match error/boundary inspection and per-match benchmarks with split/runtime provenance. Playback samples are thinned with visible timestamp/age; labels remain full-rate. The interface imports official measurements and does not invent confidence or scores. Restricted-match inspection contains predictions only, with no reference labels or benchmarks.

## Limits and provenance

Short possessions remain difficult. In the previously consumed J03WMX descriptive check, the frozen artifact's IoU 0.5 recall was 10.3% over 165 spells longer than 0.5 and at most 2 seconds, versus 79.7% over 182 spells longer than 5 seconds. This is the auditable duration cohort in `experiments/final-external-results.json`, not a new holdout or the earlier pooled development cohort. Provider label semantics, synthetic dropout and transfer from professional tracking to automatic video tracking limit generalization. Block dropout is not conditioned on crowded duels or camera exits, unlike real invisibility. No new independent dense possession source qualified. No full-match competition-target accuracy is claimed.

External data: Manuel Bassek, Robert Rein, Hendrik Weber and Daniel Memmert, *An integrated dataset of spatiotemporal and event data in elite soccer*, [Figshare version 1](https://doi.org/10.6084/m9.figshare.28196177.v1), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Our changes include feature/coordinate transformations, dropout, fitted predictions and benchmark measurements. Authors do not endorse this model.

Official code: [Metrica Sports challenge](https://github.com/metrica-sports/more-than-a-hack-2027), commit `f8f2629ff1e0985f81d7e59d8413678514ee1530`, MIT. Full candidate tables, source/model hashes, failures and runtime scopes accompany the source. The synthetic video demonstration is generated software test material, clearly separated from measured accuracy. Competition assets and private viewer material are excluded. The team-published final CSV/PDF packet is the named exception for submission outputs.

## Asset decisions and final external check

The selected runner consumes tactical ATD and its team/pitch metadata plus official half/frame constants. Smart Tagging, homography and broadcast video/tracking are not integrated; this does not claim they were fully benchmarked. The public Smart Tagging loader describes approximate restart windows, not exact stoppage boundaries. No independently qualified analogous external tag channel supported a fusion experiment. Homography is unnecessary for the already projected coordinates used here; broadcast has a separate timeline with no validated automatic alignment.

The registered V6 cache-only diagnostic compared the already consumed p10/p25/p50 decoders on all 18 external rows. p25 and p50 failed the conjunctive spellF1/macroF1/transition gate; p10 is unchanged. No target-labelled boundary analysis or score was used for selection. Windows and Linux/WSL CPython 3.11.9 with requirements.lock reproduced the published CSV byte for byte; Linux independently repeated it. No macOS or arbitrary-platform identity is claimed.

Future work: a genuinely fresh match-level test, condition-aware missingness, qualified bounded restart priors, and short-spell/transition timing evaluation. These are opportunities, not demonstrated improvements. Inference source anchor: `b616105457a77cc4ad74324ce333e8657ad66f41`. Final packet tag: `malwarous-initial-2026-11-17`; see [release identity and form checklist](FINAL_REVIEW.md).
