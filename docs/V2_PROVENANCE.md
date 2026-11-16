# V2 provenance and disclosure boundaries

V1 remains preserved in the internal reviewed snapshot at commit `42f487187dbd9f8cd1ee75cc201e3e2952b7103f`. V2 is the separately frozen selected candidate. This submission repository starts with the filtered source, not the internal research history; historical commit identifiers in locks record development lineage. The checked source fingerprints and included external-only weights permit reproduction without those historical Git objects. Repository publication does not authorize redistribution of competition assets or organizer-form submission.

## Data and labels

**Manuel Bassek, Robert Rein, Hendrik Weber and Daniel Memmert, “An integrated dataset of spatiotemporal and event data in elite soccer.”** Figshare https://doi.org/10.6084/m9.figshare.28196177.v1, described in Scientific Data https://doi.org/10.1038/s41597-025-04505-y, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The publisher's article API reverified the title, authors and licence on 2026-11-14. We use six previously consumed development matches, verify published file sizes/MD5, parse regulation halves, convert provider BallStatus/BallPossession into H/A/D/X, and derive observation features. Label semantics and source-to-target limitations remain explicit. The viewer transforms centred coordinates to corner-origin metres, thins pitch samples and displays full-rate prediction/label intervals. Synthetic ball-dropout masks and derived benchmark results are our modifications; they are not original provider labels.

The three whole-match folds contain predictions excluded from fitting on each particular match. Candidate selection uses those pooled development results. None of these matches is newly blind. J03WMX is a previously consumed v1 confidence audit, not a new v2 test. No fresh independent dense possession source qualified; see `experiments/V2_DATA_REVIEW.md`.

Competition tactical/broadcast recordings and tracking stay local under their separate restricted terms. V2 training never reads them. Frozen target inference uses only the tactical observables, documented game constants and external-only fitted artifact. It does not read target truth/public labels, compute a target score, create human annotations or use target predictions to select a model. The tactical video is available only through a local explicit media allowlist for human inspection. Broadcast has a different timeline; no synchronization is asserted without a validated mapping.

## Method, code and reproducibility

The official scorer and validator are unchanged at organizer commit `f8f2629ff1e0985f81d7e59d8413678514ee1530`, under the repository's MIT code licence. Our new contextual geometry, natural-prior heads, bounded inherited observation evidence and decoding study are independently implemented. GTT implementation, target outputs and competitor annotations are not reused. Generic temporal possession inference is prior art, not claimed as our invention.

`configs/v2_candidate.json` records the selected decoder, local artifact checksum, training matches, feature schema, report checksum, source hashes and inference mode. `docs/experiments/v2-benchmarks.json` contains the complete candidate/match/scenario comparison in compact form; `V2_RESULTS.md` is its human-readable table. The full audit retains original official transition details. Exact saved-fold prediction reproduction passed on all18 match/scenario rows. The final artifact is trained on all six external development matches after selection; the cross-validation metrics belong to the excluded-match fold models, not an evaluation of the final all-data model on its training matches.

The runtime environment is Python3.11.9, NumPy2.4.4, scikit-learn1.9.1 with pinned existing dependencies. Study training/prediction used four CPU threads. Reported v2 inference time includes context construction, cache reads, head prediction and decoding, excluding XML ingestion/scoring. A centered future-looking method is offline; no real-time or calibrated-confidence claim is made.

## Public-safe demonstration

`workbench/demo.py` and its optional MP4 generator create deterministic synthetic positions and authored labels solely to test the application. Benchmark values are null and explicitly marked software demonstration. The animation uses the exact generated pitch samples. It does not depict the competition match or establish accuracy.

The external viewer uses only licensed DFL/Sportec positions, provider labels and externally derived predictions/results with attribution. It contains no competition material. Other generated target outputs, logs, private viewer JSON/media maps, target-derived evidence and screenshots stay local and must not be sent to hosted models. The expressly team-published final CSV/PDF packet is the named public exception. The browser QA script rejects private bundles before capture. Local file serving is loopback-only with explicit routes/media IDs; it has no uploads, telemetry or external dependencies.

## Final release clarification

The selected candidate remains `context_p10_r0`; V6 transition diagnostics did not promote p25 or p50. See `experiments/V6_RESULTS.md` for all18 matched rows per candidate and losses. Smart Tagging/homography/broadcast are not integrated in this selected pipeline. Linux/WSL CPython3.11.9 with the pinned environment reproduced the published CSV exactly. The final CSV/PDF in `submission/` are explicitly team-published outputs; raw assets and private viewers remain excluded.
