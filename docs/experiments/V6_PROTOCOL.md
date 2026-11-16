# V6 protocol: external restart feasibility and frozen-decoder transition study

Status: proposed for root commit before any new scoring. Written 2026-11-16. This protocol creates no authorization to read target assets or to change the frozen release.

## Scope and evidence boundary

Use only official public upstream documentation/source (`DATA.md` and `starter/load_smart_tagging.py`), licensed EXTERNAL Sportec documentation/schema, and the already permitted six-match external V2 development caches. Never read target tracking, SmartTagging payloads, videos, labels, predictions, CSVs, private viewers, diagnostics or metrics. Public upstream source may be read through web/Git; target payloads must never be uploaded or returned through hosted tools. Keep frozen V2 source/config/model/submission bytes unchanged. No commit or push by the experiment owner.

All six matches and all decoder penalties below were previously consumed. This is a newly preregistered diagnostic over reused, selection-conditioned development data, not a fresh validation set or independent replication. V2 `context_p10_r0` remains the reference. V3/V4/V5 failed gates; no V5 resurrection.

## P0: restart-channel independence feasibility, before any fusion

Inspect official public source/documentation only. Record exact upstream Git revision and SHA-256 of the two allowed source documents. Identify SmartTagging event families, timing/alignment contract, and whether documented restart/stoppage annotations are separate from possession/live-dead labels. Do not inspect the target SmartTagging payload.

Inspect licensed EXTERNAL Sportec publication/schema and cached external acquisition manifests/file names only for an analogous event channel. A feature is eligible only if its provenance demonstrates that it is an independently supplied annotation/observable, not a direct copy, deterministic transformation, interval fill, target-derived proxy, or provider calculation from `BallStatus` / `BallPossession`. Schema presence alone does not establish annotation independence. Sparse restart events must not be expanded into dense truth. An event occurring at a dead/live boundary is not by itself evidence of circularity or independence.

Required go evidence: (1) lawful accessible external event payload for the same six matches, (2) documented time alignment to position frames, (3) documented annotation/provenance independence from the two scoring labels, (4) analogous semantics to allowed public upstream SmartTagging source, and (5) a separately frozen, bounded feature/experiment amendment before labels or new scores are examined. Absent any required item, report P0 NOT VALIDATED and perform no fusion, no event reconstruction from scoring labels, and no target reads. P0 is a feasibility audit; this protocol preregisters no fusion candidate.

## P1: transition-aware diagnostics on existing frozen V2 candidates

Scoring cannot start until root confirms this exact protocol was committed. Use existing external caches and saved out-of-fit predictions; reuse saved emissions and the unchanged V2 decoder only if a named prediction is missing. No training, new fit, source-data parse, new mask, changed support, or hyperparameter search. Abort rather than silently refit missing caches.

Paths (read-only inputs): `D:/more_than_a_hack/malwarous/artifacts_private/v2/cache/<match>-<scenario>-half<1|2>.npz` (read only `truth` and alignment metadata); `D:/more_than_a_hack/malwarous/artifacts_private/v2/predictions/<match>-<scenario>-context_p<10|25|50>_r0.npy`; optional corresponding `*-half<1|2>-emissions.npy`. Do not inspect adjacent private viewer/target folders. New code goes under `malwarous/v6/`; new results under `artifacts_private/v6/` and sanitized external summaries under `docs/experiments/`. Record SHA-256 input/source/protocol fingerprints and cache array keys/shapes. Half predictions must align with half truths and be joined with one X sentinel, exactly as V2. Respect every X-separated valid run; do not allow cross-run transition matches.

Fixed matches and three excluded pairs: J03WN1/J03WOY, J03WPY/J03WOH, J03WQQ/J03WR9. Fixed scenarios: original, drop40 (mean missing block 8), drop70 (mean missing block 25), existing V2 seed 20261114. Existing training uses other four matches, natural priors, symmetry augmentation, 65 features, 0.4/2/4 second centered context, stride five, original/drop40 training views. Preserve all of it.

Exactly three candidates: `context_p10_r0` (frozen reference), `context_p25_r0`, `context_p50_r0`. All three penalties and their official headline metrics have already been evaluated in V2; disclose this prominently. Radius 12 and weak p1 candidates are excluded. No newly tuned objective, decoder, duration threshold or candidate may be introduced from these diagnostics.

## Metrics frozen before new computation

For every candidate report all 18 match/scenario rows, not only means, using unchanged `evaluation/possession_metrics.py`, `bootstrap_n=0`: official spellF1 averaged over IoUs .3/.4/.5/.6/.7; macroF1 H/A/D; per-class F1; alive/dead F1; GT/predicted spell counts and their ratio; official fragmentation ratio.

Transition metrics: official destination-typed one-to-one matching at 12 and 25 frames, separately within each GT-valid run to avoid possible pairing across short X gaps. Sum TP/FP/FN across runs within a match/scenario and compute precision/recall/F1 from those summed counts; also report n_GT/n_pred/n_matched/n_missed/n_spurious, mean signed and absolute latency for matched transitions, and transition count ratio n_pred/n_GT (undefined as null if denominator zero). Report both tolerances separately; no averaged tolerance score.

Short-spell diagnostics: fix inclusive duration bins 1-25 frames (<=1 s), 26-50 (>1 to 2 s), 51-125 (>2 to 5 s), and >125 (>5 s) at 25 Hz. Report GT count, predicted count, and mean GT recall across the same five official IoU thresholds. Match full GT/predicted spells by the official matching routine first, then attribute matches/misses to the GT-duration bin; do not re-match each bin independently. Report count ratios by duration bin as diagnostics, with null for zero GT count. Short-spell metrics do not control candidate eligibility or enable post-score tuning.

## Summaries and replacement gate

Compute unweighted means over the 18 rows and over each scenario's six rows. Report all paired candidate-minus-p10 row deltas, each match's mean delta over its three scenarios, number of improved/equal/worse matches, worst match and scenario, and every negative row. Any uncertainty interval is optional; if included, resample six match clusters with seed 20261116 (5000 draws), never individual frames, and label it descriptive selection-conditioned uncertainty.

A p25 or p50 candidate is eligible for a replacement recommendation only when ALL hold versus frozen p10 on exactly these same rows: (a) mean official spellF1 gain >=0.02; (b) mean macroF1 gain >=0; (c) mean transition F1@25 strictly improves; (d) original-scenario mean spellF1 gain >0; (e) no match's three-scenario mean spellF1 loss is below -0.05. Report each criterion's measured delta and boolean. These are conjunctive development gates, not target-performance promises. If both pass, choose higher mean official spellF1; within .005 choose higher mean macroF1, then lower penalty. If neither passes, retain V2 p10. Do not rewrite the gate after observing results.

## Budget and stop rules

Metadata/source audit plus cache scoring only; no heavy fit, no new dataset payload download, no target inference. Validate scorer/diagnostic logic with small synthetic arrays before scoring external caches. Maximum two hours for this bounded V6 campaign, checkpoint results, stop on missing provenance/alignment or unavailable cached data and report the concrete limitation. A further objective needs independent external justification and a separate root-committed amendment before scoring; none is authorized by this document.
