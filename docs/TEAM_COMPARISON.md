# Fair comparison of the three team algorithms

Use this procedure to choose among three frozen possession labelers. The comparison is for
development on **whole, held-out external matches**. It does not score the competition match, the
published five-minute window, or any competition ground truth.

## Protocol to agree on before scoring

1. Pick the external match set and scenario set together. Use the same matches and scenarios for
   every candidate, with labels from an identified source whose license permits the work. Record
   each candidate's training and tuning match IDs, plus the sets used for each prediction/fold.
   The per-prediction training set must exclude its evaluated match. Candidate-level lists are the
   union across folds, so a match may appear there because it trained a different fold. Mark that
   case `reused_development`, even though each prediction is out of fold. Use `untouched_audit` only
   when no candidate trained or tuned on the match in any fold. Record prior research use and how
   the labels were made.
2. Freeze the three candidate list and the selection rule before anyone reveals their scores. Use
   the same input data and preprocessing scenario for each algorithm. Do not add a fourth variant or
   tune after seeing results.
3. Have each teammate produce one `frame,label` CSV for every predeclared match/scenario. Include
   every frame in the same order for each candidate. Frame IDs may be match-specific and need not
   start at zero; within a half they must be integer, consecutive, and unique. They must exactly
   match across truth and all three predictions for that block. A frame-number gap is allowed at
   halftime because halves are scored separately.
4. Mark each half as a contiguous row range in the manifest. Do not rely on a frame-number gap to
   represent halftime. The harness scores each half separately, then pools the official scorer's
   counts inside that match/scenario. This prevents spells crossing the half boundary and does not
   treat neighboring frames as independent observations.
5. Package each candidate's source/model artifact as a file, record its SHA-256, and include measured
   fit/inference cost, measurement scope, and hardware. For every prediction, identify its fold and
   the fold-model file; the harness verifies that file's SHA-256. Hashes make accidental changes
   visible; they are not proof of authorship or a security check. The harness reads prediction CSVs,
   model bytes for hashing, and metadata only. It never loads a pickle or executes candidate code.
6. Create a manifest using [the example](../configs/team_comparison.example.json), then run:

   ```powershell
   python scripts/compare_team_models.py path\to\comparison.json --out artifacts_private\team-comparison
   ```

   The default output directory is `artifacts_private/team-comparison`, which this repository
   ignores. A non-empty output directory is left untouched and causes a clear error.

## How to read the result

The primary metric is the official `spell_f1_mean`: H/A possessions are matched one-to-one by
temporal IoU at 0.3 through 0.7, and their F1 values are averaged. The secondary metric is the
official H/A/D `macro_f1`. Halves are scored independently with
`evaluation/possession_metrics.py`; official confusion and spell counts are then pooled to get the
whole match/scenario score. Each match/scenario contributes equally to the reported means. Every
candidate is evaluated on the same rows.

`pairwise_deltas.csv` reports paired `candidate_b - candidate_a` differences. Its 95% intervals
resample whole match IDs and keep every scenario for a sampled match together. The number of
independent matches, not the number of scenarios or frames, sets the uncertainty. Fewer than five
match clusters is explicitly marked as too little evidence for a reliable winner claim; two or
three matches can give a bootstrap interval, but it is only descriptive.

`report.json` records the SHA-256 of the official evaluator and says whether any match was
previously reused for training or development. A `reused_development` block makes the result
selection-conditioned; it is not a blind or independent audit. Even if all blocks were declared
`untouched_audit` before scoring, using them now to select a candidate makes this a development
comparison rather than a final independent test.

Treat a small score gap or overlapping paired interval as unresolved. Use the pre-agreed
simplicity/reproducibility tie-break and have the team vote before anyone inspects competition
labels. The script reports a score order for convenience; it does not establish a universal
winner or authorize target-set tuning.

## Provenance and limits

The manifest requires source and label provenance, a predeclared candidate list, per-candidate
training/tuning match ID unions repeated as per-prediction fold sets, an explicit fit-exclusion
attestation, fold IDs and fold-model hashes, fit/inference cost and its measurement scope, exact CSV
hashes, and explicit attestations that competition
match data, competition human labels, and the public five-minute window were not used for
selection. The harness also rejects recognizable competition identifiers, the shipped public
ground-truth filename, competition ground-truth folders, the known competition frame count and
published five-minute frame range, duplicate or misaligned frame IDs, missing candidate/block
pairs, inconsistent half ranges, and relative paths that escape the manifest folder. Absolute
paths to external data are allowed so large licensed files can remain outside the repository.

These checks catch mistakes and obvious leakage. A manifest flag or SHA-256 cannot prove that a
dataset is external, that a held-out match was excluded from training, or that the stated label
source is genuine. A teammate must verify and sign the externality attestation. Review the source
license before use, keep raw licensed data local, and share only aggregate comparison results if
the license permits it. This harness must never be pointed at the competition's public or private
labels.

## CSV format

Truth and prediction files contain exactly `frame,label` columns. Labels are `H`, `A`, `D`, or `X`
(abstain). Within each half, frame IDs must increase by exactly one; missing frames must be
resampled to the common frame grid before scoring, because otherwise temporal IoU would compress
time. Half boundaries can have any frame-number gap. Each block is one match and one predeclared
scenario. `halves` is an ordered, gap-free partition of CSV row offsets using an inclusive start
and exclusive stop. For example, for a two-half file with 240 rows, use `0..120` and `120..240`.
Each match must include the same set of scenarios and one `evaluation_use` status for all scenarios.

The example config uses placeholder paths and hash text and cannot run until replaced with actual
external files and their computed SHA-256 digests. It contains no labels or benchmark scores.
