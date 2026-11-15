# V2 development study — 2026-11-14

## Authorization and scope

The user objective at `C:\Users\Hasnaat\.codex\attachments\946aeb24-0680-439c-9824-14a13f937635\goal-objective.md` authorizes local v2 implementation, permitted downloads, training, testing, evaluation and an interactive workbench. No commits, publication, organizer submission or new third-party contact are authorized. The previous wait-for-publication action is superseded for local development.

V1 remains unchanged: release snapshot commit `42f487187dbd9f8cd1ee75cc201e3e2952b7103f`, original configs, official scorer and status-only runner. V2 lives in new namespaces and files. Do not alter v1 locks to conceal a change. The prior development, selection and audit labels have all been consumed; no existing Sportec match is newly blind.

## Registered design, before new v2 scores

This is a bounded **development comparison**, not independent confirmation. Use six previously consumed DFL development matches, grouped into three fixed pairs:

1. J03WN1 / J03WOY
2. J03WPY / J03WOH
3. J03WQQ / J03WR9

For each outer fold, train on the other four matches; predict each excluded match without fitting on its labels. All candidates use the identical observations, masks, frame support and unmodified official scorer as v1. Hyperparameter selection on the pooled out-of-fit scores makes the resulting selected summary development evidence. Report every candidate and every match/scenario, including losses. The consumed J03WMX audit is not a fresh holdout and is initially excluded. New generalization claims require a genuinely independent licensed match source, identified before label inspection.

Three deterministic observation scenarios: original, 40% block ball dropout (mean block 8 frames), 70% dropout (mean block 25 frames). Seeds derive only from registered seed 20261114, match ID and period. Corrupt observations only, never labels. Compare v1 smooth50 on exactly the same corrupted inputs.

One new model family: shallow histogram gradient boosting with team-swap augmentation, natural class priors rather than balanced class weights, instantaneous geometric evidence plus observation-weighted centered context at 0.4, 2 and 4 seconds. Explicit support/age and inherited nearby-control evidence distinguish missing observations from dead ball. Features must consume observables only, reset at halves, avoid slot identity and absolute match/frame time, and remain team-equivariant. This is offline inference with future context, not real time. Sampling every fifth training frame limits CPU/memory; clean and moderate-dropout training views are fixed in advance.

At most six decoder candidates: turnover/live-dead switch penalties (10/10), (25/25), (50/50), each with emission averaging radius 0 or 12 frames. Penalties operate on accumulated log evidence, not a hard minimum spell length. Decode halves independently. The ablation is the same new emissions with the old weak penalty (1/1), reported diagnostically and ineligible for selection. No post-score additions without a separately recorded study amendment; no target-derived choices.

Selection: highest mean spellF1 across all 18 match/scenario rows; within 0.005 choose higher mean macroF1 then lower penalty then shorter averaging. Report clean and dropout groups separately, paired differences, number of matches helped/hurt, spell-count ratio, per-class F1 and error boundaries. Replacement recommendation requires mean gain >=0.02, clean mean gain >0, and no single match's scenario-average loss below -0.05; otherwise preserve v1 recommendation. These are development decision rules, not proof of target improvement.

Budget: three fold pipelines (six classifier-head fits), six eligible decoders plus one diagnostic, six matches x three scenarios. Maximum eight hours cumulative wall clock including resumed attempts, checkpoint each fold, no parallel heavy training. Context widths above are total widths; integer radii are 5, 25 and 50 at 25 Hz. Stop cleanly and record failures. Do not train/download a video model absent a plausible possession-specific contribution and acceptable CPU cost.

## Work ownership

- Root: protocol, v2 model/features/runner, paired benchmarks, integration and durable state.
- Sol High `v2_fragmentation`: code/report diagnosis; owns V2_DIAGNOSIS.md only.
- Sol High `v2_data_review`: primary-source data/license/independent-validation assessment; owns V2_DATA_REVIEW.md only.
- Sol High `v2_workbench`: local stdlib server + browser application in workbench/, synthetic integration tests.

## Data and release boundary

External CC BY Sportec results may be reported with attribution. Restricted target assets/predictions/plots/metrics remain local; hosted tool returns fixed statuses only. No public-target-label training, scoring iterations, selection or human annotation. The two competition videos can be locally served to the human through an explicit media allowlist; they must not appear in model-visible screenshots or outputs. Public-safe demo uses synthetic or specifically permitted external material, with provenance and evidence type visible. No invented confidence. No Git commit or push during this study.

## Acceptance evidence still needed

Meaningful synthetic invariants; successful complete paired campaign and exact config/source fingerprints; actual per-match errors and uncertainty; functioning viewer with pitch/video time mapping, timelines, evidence and benchmark tables; local-only security checks; public-safe synthetic demonstration; a reviewed v2 target runner preserving the existing status-only boundary if v2 clears its external gate. A working viewer alone does not demonstrate accuracy.
