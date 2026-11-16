# Public replay data

The public data pack is static JSON plus one synthetic demonstration video. The
browser reads `replays/index.json`, then loads the selected sequence and the
benchmark table. There is no upload or live-data endpoint.

## External replay source

The twelve external half replays cover six DFL/Sportec matches: J03WN1, J03WOY,
J03WPY, J03WOH, J03WQQ and J03WR9. They are derived from the approved
DFL/Sportec external development bundle for the
[Bassek, Rein, Weber and Memmert dataset](https://doi.org/10.6084/m9.figshare.28196177.v1),
licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Attribution: Bassek, Rein, Weber and Memmert.

The data uses generic home (`H`) and away (`A`) side codes. It contains no team
or athlete names. Each sequence assigns stable, local diagram IDs in source
roster order. The displayed roster numbers are those local IDs, not shirt
numbers or real player identities.

Observations are thinned for display by retaining every second source row and,
when necessary, the final source row. `sample_hz` reports the resulting display
cadence (about 1.04 Hz); `source_sample_hz` records the source cadence (about
2.083 Hz). Each sample's `f` value is its original source frame at 25 fps.
Sampled ball and player positions are converted from meters to centimeters and
rounded to the nearest centimeter (`coordinate_scale: 100`). External ball
positions remain two dimensional because the source provides no elevation.
Synthetic ball positions retain their source third coordinate. Evidence values
are rounded to three decimal places for display. Quality values are retained
from the source. These display reductions do not change the truth or prediction
intervals: they remain full-rate, half-open 25 fps frame ranges. A missing ball
observation stays `null`; no gap is interpolated.

The replay labels are official source annotations and model outputs for the
approved external development matches. They are not competition data. The
sequence provenance identifies the grouped out-of-fit development split and
whole-match, both-half benchmark scope.

## Benchmarks

`replays/benchmarks.json` contains 18 whole-match rows: six matches across the
`original`, `drop40` and `drop70` scenarios. Each row pairs the `v1_smooth50`
baseline with selected `context_p10_r0` V2 values from the canonical benchmark
report. Its summary values are copied directly from that report without
rounding. The two half replays for a match share the same whole-match benchmark
row; the table does not present half-level metrics.

These are reused-source grouped development measurements after candidate
selection. They are not independent validation or target scores. Metrics use
the official evaluator implementation, and the benchmark source is limited to
the six external matches.

## Synthetic demo

`replays/synthetic-demo.json` and `media/synthetic-demo.mp4` are a software
fixture with a 10 fps, 72 second video and 720-frame timeline. Its positions and
authored labels are synthetic, not trained-model results. Its V1/V2 benchmark
placeholders remain `null`; no accuracy metrics were computed. The input media
is pinned by SHA-256 `61d04f220ac6aae121b930626ddeb46cd756e3c3f65a2e6e0bebf7b6f21c2f2c`.
The approved fixture does not specify a separate third-party dataset license.

## Rebuilding the pack

From the repository root, run the exporter with the approved inputs:

```text
python scripts/export_public_site.py --external-bundle <approved-public-external-bundle.json> --synthetic-dir <approved-synthetic-demo-directory>
```

The canonical benchmark report defaults to `docs/experiments/v2-benchmarks.json`.
Use `--benchmarks-report` to provide that report explicitly and `--output-dir`
to change the website output directory.
