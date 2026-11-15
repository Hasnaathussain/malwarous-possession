# Final all-six V2 external artifact check — preregistration

Registered before any J03WMX V2/V3 label inspection or scoring in this check.
This is a single descriptive artifact check, not fresh, blind, or independent confirmation.
J03WMX was previously consumed for the V1 audit. Its V1 aggregate results are already
known (spellF1 approximately 0.3072, macroF1 approximately 0.4150). They will not be
used for tuning, model selection, matching adjustments, or acceptance thresholds.
J03WMX was excluded from V2 fitting and selection; this check measures the actual final
V2 model fit on all six development matches, not any cross-validation fold predictor.

The fixed comparison is original clean J03WMX observations, full-rate at 25 Hz, both
regulation halves, V1 nearest-player smooth50 versus frozen final V2 context_p10_r0.
If and only if the completed frozen V3 development campaign recommends a replacement
under its existing summarize rule, also run that one decoder on the same final V2
emissions. No V3 fitting is permitted. Fix the decoder from the V3 report before
loading J03WMX labels; never use this check to select among decoders or versions.
No dropout scenarios, alternative windows, new matches, retries with altered settings,
training, threshold tuning, or follow-up search are part of this check.

Inputs are only the existing CC BY 4.0 Figshare 28196177 J03WMX metadata and tracking
XML under external_data_cache/sportec/J03WMX. Verify the exact cached manifest,
license, metadata/tracking MD5 and byte sizes, frozen V2 config/model/report SHA-256,
and frozen source code hashes before unpickling the model or parsing labels.
The V3 report must be completed, explicitly SHA-256 pinned, consistent with its
completed ledger, have verified decoder/study/diagnostic source hashes, and reproduce
its stored summary using its fixed rule. Incomplete/unpinned/mutated provenance stops
the job. No download, source contact, competition assets, target paths, viewer ports,
viewer logs, target labels, or target-derived values are inputs.

Write the full verified source/artifact ledger, chosen methods and registration hash
before parsing external labels. Keep labels out of feature inputs. Apply each method
to the exact same source observations, resetting each half and inserting one official
ungraded X between halves. Preserve the existing parser, baseline tie handling,
feature builder and official evaluator unchanged. V2 reads only
models_private/v2-possession.joblib; V3 reuses those same emissions.

Primary output: official spellF1 mean and paired difference versus V1. Also report
macroF1, per-class H/A/D precision/recall/F1, confusion/counts, possession spell counts,
IoU scores, official transition measures, both separate-half and two-half totals,
and descriptive truth-spell duration diagnostics (<=0.5 s, >0.5–2 s, >2–5 s, >5 s),
with rescued/lost short spells versus V1 and unmatched overlap patterns. H/A spells
exclude D as in the official evaluator. No independent-match confidence interval or
claim of fresh generalization is justified by a single previously consumed match.
No outcome of this check can trigger retraining, model choice, or artifact promotion.

Run only with `python -m malwarous.final_external_check --execute` after review.
Default/help invocation must not access inputs or run the check. No CLI paths, match
IDs or parameter overrides are allowed. A parent watchdog enforces a cumulative
15-minute wall-clock budget from the first execution attempt, including provenance,
XML ingest, feature construction, inference, scoring and writing. Four CPU threads.
A durable clock, exclusive lock, source ledger, failure records and result live only
under artifacts_private/final_external_check. A completed result is immutable; failed
attempts retain the original clock and pins and can only retry unchanged inputs
within that same budget. Record partial failures, never substitute partial results.

Runtime reporting separates provenance, source XML ingest, model load, V1 inference,
V2 context + heads + decoder, optional V3 decoder-only work, diagnostics/scoring,
and total worker time. Any shared work and exclusions must be explicit; an optional
V3 decoder-only runtime is not comparable to full V1/V2 inference time. XML and
scorer are excluded only from per-method inference, and included in total time.

Implementation scope: this document, malwarous/final_external_check.py, and synthetic
tests/test_final_external_check.py. Preserve every V1/V2/V3 artifact/source lock.
Preparation must not execute the real-data check. The V3 report hash is an explicit
pre-execution pin; if the campaign is still live, the unpinned implementation fails
closed until its completed report hash is inserted and this preparation is reviewed.

Preparation pin recorded after the V3 campaign completed, still before any J03WMX
parse/scoring: V3 full report SHA-256
`39e063bbb58a88f7bb07d82b75219efe403c983cb7b601e54035ba1fcc8aa177`.
Its fixed recommendation is `frozen_v2_p10`; the selected candidate failed the
registered replacement gain gate. Accordingly this prepared check compares V1 and
final V2 only. Any later development study or replacement candidate requires a
protocol amendment, new explicit source/report pins, and review before J03WMX labels
or scores are loaded; it cannot be added based on this check's outcome.

Pre-label amendment after final V4 development selection, still before any J03WMX
parse/scoring: the complete 144-row V4 full report SHA-256 is
`a2581b84db4324513c63b334da9579a21253b1cf258ce95dadc73f9056d13b69`.
V4 selected `contact_a75_p10`, mean spellF1 0.48658186 versus frozen V2 0.48095186.
It failed the registered >=0.02 replacement improvement and the specialist value
versus frozen V3 gate; its fixed recommendation is `frozen_v2_p10`.
No final V4 fitting or V4 target run will be created or consumed by this check.

Both completed V3 and V4 reports, matching completed ledgers, and all their current
Python source files must verify before importing their exact `summarize` rules.
Recompute and exactly compare both stored summaries before unpickling the final V2
model or parsing J03WMX labels. The V4 decision must reproduce both failed gates and
retention of V2; changed recommendations require a new pre-score amendment.
Normalize historical Windows backslashes to slash-separated repository paths on
every platform, reject colliding pin keys and absolute, drive-relative, or escaping
source paths, and preserve every recorded digest and protocol field.

The final registered methods are now fixed: V1 nearest-player smooth50 and actual
final all-six V2 `context_p10_r0`, on identical original observations for both halves.
No V3 decoder or V4 specialist output is included. `VERSION_REVIEW_COMPLETE` may be
set true only after this amendment and synthetic boundary tests pass. This prepares
the one final external check for root review; it does not execute or authorize a
new run by itself. All durable ledger, runtime and cumulative watchdog rules above
continue unchanged. No external-check score can change the chosen version.

Amendment validation completed: 30 synthetic boundary tests passed. Completed V3/V4
report hashes, current source hashes, completed ledgers and exact stored summaries
were also checked without loading any J03WMX input. `VERSION_REVIEW_COMPLETE = True`
now records the final development decision. The actual external check remains
unexecuted pending root review.
