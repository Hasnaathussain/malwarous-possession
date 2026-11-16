# Final critique review and submission freeze

Reviewed 16 November 2026. Candidate remains `context_p10_r0`; no fit, penalty,
radius, timing shift, target-specific rule or CSV change follows this review.

| Concern | Finding and action |
| --- | --- |
| No public-window pipeline check | Legitimate omission. The published evaluator explicitly supports a worked-example check. Protocol `1ed2888` fixed the file and prohibited any score-based decision before execution. One unmodified official run with bootstrap 1000 completed locally; detailed scores/counts stay in the ignored local report. |
| Must beat public smooth125 or match 17 spells | Not a legitimate acceptance gate. The organizer shows that public-window and full-match baseline rankings reverse. Neither threshold/count was used to tune, replace, veto or select the candidate. |
| Possession rules missing | The PDF already had a short paragraph; the Markdown note lacked one and the wording overstated semantic correspondence. Added an explicit provider-to-target comparison and distinguished learned persistence from a hard control rule. See [POSSESSION_RULES.md](POSSESSION_RULES.md). |
| Domain shift and selection bias | Real, unresolved limitations. Random block-dropout robustness is not evidence of robustness to visibility conditioned on duels, crowding or camera movement. Eighteen rows are three correlated views of six reused matches, not eighteen independent matches. J03WMX is not a fresh holdout. |
| Short possessions | A real measured weakness. To provide auditable denominators, the current note/PDF cite the already published J03WMX descriptive check: IoU-0.5 recall 10.3% over 165 spells of >0.5–2s versus 79.7% over 182 spells of >5s. This is a different cohort from the earlier pooled 11.3%/78.9% figures, not a new holdout. No evidence-backed replacement cleared its gate; reporting the weakness does not fix recall. |
| Unused assets | Valid opportunity, not a demonstrated gain. Smart Tagging fusion was not externally qualified or scored; homography and broadcast were not integrated. Future work is qualified restart fusion and automatic feed alignment. |
| Presentation versus initial-phase score | Correct: the Initial Challenge ranks the CSV, not the website. This final pass prioritizes packet correctness and reproducibility; no extra website features are introduced. |
| External data and future context | External other-match data is expressly allowed subject to access/disclosure. The task is full-match labelling with no online/causal restriction; the official centered-smoothing baseline also uses future observations. Source links below. |
| Public CSV copying | Real exposure, already published at the team's request. Removing it now would not retract clones/history. The packet remains public; no history rewrite or claim of restored secrecy. |
| Cross-platform contradiction | Outdated for current README/PDF. Both record exact Windows and Linux/WSL CPython 3.11.9 reproduction. Wording is harmonized; no macOS or arbitrary-platform identity is claimed. |
| Open PR | GitHub inspection found PR #2 closed and no open PRs at review time. Freeze the final packet with an annotated tag; do not merge or move that tag after upload. |

## Local check evidence

The official validator and public evaluator both exited 0; the CSV SHA256 before
and after was unchanged. Raw public labels, generated reports, distributions and
transition files are not added to Git or sent to hosted tools. The local report is
`artifacts_private/final-pipeline-check/scoreboard.txt`; exact validator output is
`artifacts_private/final-pipeline-check/validator.txt`. The check is diagnostic
only and does not establish full-match accuracy, a target forecast, or a rank.

Three synthetic tests additionally passed: longitudinal reflection, lateral
reflection, and normalized-Metrica ingestion/centering parity with direct centered
metre coordinates, including missing samples. Existing side-equivariance and
frame-index tests complement these checks. They test implemented conventions, not
the actual target annotations or every possible provider/schema error.

## Release identity

The frozen inference-source anchor cited in the PDF is
`b616105457a77cc4ad74324ce333e8657ad66f41`. This review changes documentation,
synthetic tests and PDF packaging only; its frozen inference sources and CSV are
unchanged. Final packet tag: **`malwarous-initial-2026-11-17`**.

The annotated tag identifies the final commit, manifest and PDF hash. A PDF cannot
contain the hash of the same commit that contains that PDF without a circular hash
dependency. It therefore cites the fixed inference anchor and final tag; resolve
the tag for the exact packet commit. Record `git rev-parse <tag>^{commit}` with the
upload receipt. Never force-move the tag.

## Form checklist

- [x] Team name confirmed by the user: **Malwarous**, three registered technical members.
- [x] Exact frozen CSV validated; before/after SHA256 unchanged.
- [x] Public repository and data provenance available; restricted inputs excluded.
- [x] Technical document explains implemented semantics, assets, limits and reproduction.
- [ ] Resolve final tag and compare uploaded files against its `SOURCE_MANIFEST.json`.
- [ ] Open the organizer's emailed form with the team's Google account; URL/login not verified here.
- [ ] Upload `Malwarous.csv`, `Malwarous.pdf`, public repository URL and exact team name.
- [ ] Save the confirmation/receipt and verify the last response is the intended one.

**Not submitted.** The standing instruction not to submit remains in effect.
User-confirmed deadline: 17 November 2026, 23:59 CET / 18 November, 03:59 PKT.

## Official sources

All at organizer revision `f8f2629ff1e0985f81d7e59d8413678514ee1530`:
[rules](https://github.com/metrica-sports/more-than-a-hack-2027/blob/f8f2629ff1e0985f81d7e59d8413678514ee1530/RULES.md),
[FAQ](https://github.com/metrica-sports/more-than-a-hack-2027/blob/f8f2629ff1e0985f81d7e59d8413678514ee1530/FAQ.md),
[evaluation guide](https://github.com/metrica-sports/more-than-a-hack-2027/blob/f8f2629ff1e0985f81d7e59d8413678514ee1530/EVALUATION.md),
[submission requirements](https://github.com/metrica-sports/more-than-a-hack-2027/blob/f8f2629ff1e0985f81d7e59d8413678514ee1530/SUBMISSION.md),
[centered baseline](https://github.com/metrica-sports/more-than-a-hack-2027/blob/f8f2629ff1e0985f81d7e59d8413678514ee1530/starter/baseline.py).
