# Final continuation ledger - 16 November 2026

## Outcome and evidence boundary

Final candidate remains **context_p10_r0**, penalty10/radius0,65 observable features. No accuracy improvement was demonstrated by this continuation. No target score, rank, top-three claim or full-match score range is justified.

The user supplied public-window scores and frame-offset diagnoses. They were received but not reproduced or used for fitting, boundary shifts, thresholds or promotion. The organizer rules reserve public labels for pipeline correctness, not training/tuning/validation. Accordingly the requested public-GT diagnostic table was not regenerated. The unchanged CSV was format-validated without ground truth, and exactly regenerated on Linux. No target assets, labels, viewer images or prediction contents were returned to hosted tools.

## Registered experiments

Protocol committed before new diagnostics at `653df81d882432455d63f0edb6ba3371486401ef`, SHA256 `8c15af3fb2c633afd3efa4db7f2bdbdf7c0086ed8b18203b8fb9c038f99b0fce`.

| Route | Result | Decision |
|---|---|---|
| P0 Smart Tagging | Approximate restart windows; an analogous external channel lacked sufficient independence/timing qualification | No fusion candidate trained/scored/shipped |
| P1 p10 reference | spellF1 .4809519; macroF1 .8686798; T12 .4133264; T25 .5154486 | Retained |
| P1 p25 | spellF1 .4721337; macroF1 .8697351; T12 .4131947; T25 .5076051 | Rejected: primary gain, clean gain and transition gate fail;5/6 match means worse |
| P1 p50 | spellF1 .4437200; macroF1 .8694242; T12 .4083025; T25 .4928354 | Rejected: same gates plus worst-match loss;6/6 match means worse |
| P2/P3 new heads / P4 camera fusion | Not executed in this bounded final campaign | No unvalidated change shipped |

Gate versus p10 required all: spellF1 gain>=.02, macroF1 no drop, T25 improvement, positive clean spell gain and no match-average loss below−.05. Penalties and headline metrics were previously consumed; V6 adds registered transition/duration diagnostics, not fresh validation. All54 rows, negative rows, per-match deltas, scenario groups, short-spell recall and criterion booleans are in `experiments/v6-results.json` and `V6_RESULTS.md`. P0 evidence and primary links are in `V6_RESTART_FEASIBILITY.md`. V3/V4/V5 remain rejected.

## Reproduction and validation

Linux/WSL Ubuntu: downloaded CPython3.11.9 through uv, installed all31 exact requirements.lock pins, executed the frozen status-only inference command and an independent reproduction. Both completed with frame/finite/offline checks; reproduction returned byte_reproduction=pass. Linux output SHA256 equals the published CSV:

`2fa5c020221e49eb793cd6d59baa39e7f59e3e6a9bb0ed5a329d5331c8067824`

Model SHA256 is unchanged:

`c6deb427e42dca2b2d35ffa47576f4fbb94509729c0216b46312b1f367c2418d`

The unmodified official validator exited0 on the exact published CSV. Its complete native output is retained locally at `artifacts_private/runs/final-validator.txt`, rather than sending prediction distributions through a hosted tool. This is format validation, not target accuracy evaluation. Source/PDF/figure hashes and file sizes are recorded in SOURCE_MANIFEST.json; use `python -B scripts/verify_repository.py` after staging/release.

## Cleanup

No tracked frozen legacy file was removed, renamed, formatted or re-locked. `FROZEN_DEPENDENCIES.md` maps19 retained legacy files plus the current V2 configuration to the hash/import chain. `REPOSITORY_MAP.md` identifies the one selected pipeline and the cache-only V6 audit. No competition inputs, private viewer bundles, environment, caches, log or planning folder is tracked. User-authorized final CSV/PDF packet is retained. Only canonical ignored bytecode/test caches are cleanup candidates; historical research/worktrees outside the submission repo are not silently erased.

## Presentation and website

README: restrained hero/status badges, linked public replay/evidence/lab screenshots, GitHub-native Mermaid and details, exact reproduction commands, assets used/not integrated and attribution. Images carry public provenance. The four-page PDF is generated from `docs/Malwarous.html` with `node scripts/build_technical_pdf.mjs`; set ATLAS_QA_BROWSER to a Chromium executable if Brave is absent. No inference dependencies are changed. Chromium/font versions can affect PDF bytes; the committed PDF is pinned by the source manifest. The PDF contains selectable text, original method/state schematics, a licensed external timeline/evidence example and matched results. No target-derived imagery.

Atlas adds a football crest/formation/jersey metaphor; synthetic hero video with pause/reduced-motion handling; scroll reveals/nav; timeline zoom/pan/minimap, spell inspection/state highlights; V1/V2 difference lane and same-geometry state badge; evidence traces/tooltips; fullscreen with explicit browser fallback; keyboard/help; retry/loading/error states; match/half/frame and legacy replay links; four-control synthetic decoder including emission radius. It preserves observed sample positions instead of inventing interpolated coordinates through gaps. Day/night toggle and additional animated explainer are not shipped.

Team roles/links were verified on16November at malwarous.dev/team and homepage. Original SVG jerseys replace borrowed portraits. Public Younas spelling and user registration Younus spelling are explicitly recorded in TEAM_SOURCES.md. The community invitation is not a fourth competition member. No accounts, forms, API keys or uploads were added. Optional deployment analytics from a concurrent team-merged PR is isolated and described below.

## Submission checklist

| Item | Status |
|---|---|
| Malwarous, three enrolled technical members | User confirmed |
| Candidate and technical document agree | context_p10_r0 retained |
| Exact CSV valid and reproduces | Pass; Windows release and Linux/WSL verification |
| Final PDF source + selectable/rendered output | Included; four pages |
| Public repository + Atlas | Existing URLs; final release/deployment checked separately |
| CSV/PDF match final manifest | Required final verifier check |
| Google Form URL from registration email | Not supplied in this chat |
| Organizer form response | **Not submitted**; prior user instruction to wait remains in effect |
| Deadline | User-confirmed17November2026,23:59CET =18November03:59PKT |

Before submitting, use the exact committed submission/Malwarous.csv and submission/Malwarous.pdf, verify their hashes, enter the public repository URL, and check the form receipt. One final response per team; GitHub/Vercel publication is not submission.

## Final local verification

209 Python tests and34 subtests pass; six Node decoder/smoothing tests pass. The153-file staged manifest verifies, including all21 frozen source/report/model pins. New staged source scanned with Gitleaks v8.30.1 without custom suppressions: no leaks found. Browser QA passes public replay controls, timeline zoom/pan/state filtering/differences, evidence tooltips, help/fullscreen-or-explicit-fallback, synthetic seek/play sync, share/PNG export, and320/390/768/1366px layouts, with no runtime exceptions or unexpected external application requests. PDF text extraction confirms four unencrypted pages and selectable required claims. All final pages were rendered and visually reviewed.

## Concurrent Analytics repair

Remote main acquired Vercel PR1 during this work. Its bare @vercel/analytics import cannot resolve in a buildless browser module and prevented the deployed replay from starting. The merge retains the intended optional Web Analytics using the official plain-HTML endpoint in a separate script; removes the unused npm dependency/lock; and keeps replay startup independent. No source/model lock was changed. Local/automated browsers do not send analytics; deep-link parameters are redacted. This explains the reported stuck loading without attributing it to model behavior.

## Independent documentation review

A final read-only review corrected historical V1 recommendation wording, qualified V5 as the last training attempt before cache-only V6, and expanded the dependency table with direct test references. The selected config pins19 source files plus the report and fitted artifact (21 total), not21 source files. No model, CSV, PDF or website behavior changed in this documentation pass. Recursive ignored-cache cleanup was rejected by automatic approval review as blocked by policy; no bypass was attempted, and ignored local caches remain outside Git/deployment.
