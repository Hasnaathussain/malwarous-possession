# Final fitted-artifact external check

The fixed, pre-label method list was v1 smooth50 versus final all-six-match v2 `context_p10_r0`. V3 and V4 had failed their registered replacement gates before this check. No result of this check changed model selection, fitting or promotion.

| Method | spellF1 | macroF1 | H/A predicted spells |
|---|---:|---:|---:|
| v1 smooth50 | 0.3072 | 0.4150 | 360 |
| Final all-six v2 | 0.5240 | 0.9185 | 289 |

Both methods received identical original J03WMX observations, two regulation halves, 25Hz frame support, and the unchanged official scorer; source truth contained511 H/A spells. The match was excluded from v2 fitting/selection but previously consumed in the v1 audit. This is a descriptive artifact check, **not a fresh, blind or independent test and not a competition-target score**.

The complete source/config/report/model checksums and pre-label method decision were recorded before XML parsing or model unpickling. The completed ledger verifies the result checksum. Runtime was103.21 seconds including provenance, ingest and diagnostics. Inference measured0.30 seconds for nearest geometry/smooth50 and14.04 seconds for v2 context, heads and decoding; source XML ingest took79.46 seconds. These CPU measurements do not imply real-time operation: the model uses future context and whole-half decoding.

The complete per-class/half/IoU/transition/duration diagnostics and explicit runtime scopes are in [final-external-results.json](final-external-results.json). The pre-score protocol and version amendments are in [FINAL_EXTERNAL_CHECK.md](FINAL_EXTERNAL_CHECK.md). No target inputs, target labels, private viewer feedback, downloads or external messages were involved.

Source: Manuel Bassek, Robert Rein, Hendrik Weber and Daniel Memmert, https://doi.org/10.6084/m9.figshare.28196177.v1, CC BY4.0. Coordinate/features, fitted predictions and derived evaluation are project modifications.
