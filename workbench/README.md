# Local possession workbench

A Python standard-library HTTP server and vanilla HTML/CSS/JavaScript analyst interface. No package installation, remote requests, CDN, uploads, telemetry, or GPU is required. It does not run a model or inspect any existing private data automatically.

From the repository directory:

```powershell
python -m workbench.server
# Open http://127.0.0.1:8765
```

The default is a deterministic **software demonstration, not accuracy evidence**. All player/ball positions are generated; labels are authored to exercise boundary/error inspection. Scores and runtime are deliberately null. A demo animation is optional and uses an existing local `ffmpeg` executable:

```powershell
python -m workbench.make_demo_video
python -m workbench.server --data artifacts_private/v2/demo/demo.json --media-map artifacts_private/v2/demo/media-map.json
```

The optional generator writes only synthetic MP4, JSON and allowlist files under `artifacts_private/v2/demo/`. It refuses to overwrite an existing video. It renders the exact demo tracking samples at 10 fps for 72 seconds; this provides a real synchronized video/pitch playback test. Existing target media is never an input.

Load a permitted export:

```powershell
python -m workbench.server --data PATH_TO_PERMITTED_BUNDLE.json --media-map PATH_TO_LOCAL_ALLOWLIST.json --port 8765
```

The server reads only the explicitly selected bundle and optional media allowlist; it never scans asset directories. Stop with Ctrl+C. The server binds `127.0.0.1` only, accepts that Host only, serves three explicitly named static files, one JSON endpoint, and explicitly allowlisted media IDs. Encoded traversal, arbitrary filesystem routes and query-string paths are rejected. Media supports GET/HEAD and single byte Range requests. Cross-origin access is restricted by browser CSP/CORP and no CORS grants. This is a single-user local tool, not an authenticated public hosting service.

## Interaction

- Match selection, shared scrubber, play/pause, ±1 second, 0.25–4× playback. Space toggles playback and ←/→ seek one second outside controls and links; a held Space key does not repeatedly toggle. The pitch and evidence canvases include screen-reader descriptions. Reduced-motion preferences suppress interface transitions.
- Synchronized pitch and optional local video; all H/A/D/X spell timelines remain aligned to the same match clock. Version comparison is a shared-time overlay through stacked tracks and current-state readouts. Clicking a spell or evidence chart seeks the shared clock. Frame stepping follows the displayed frame index using the supplied frame rate and stays within the match interval.
- Observation quality reports only supplied coverage/ball-observed flags. Position readout shows the latest supplied sample and its age; there is no fabricated interpolation or ball marker during missing observations. Missing samples and unavailable local video have explicit descriptions, and an initial bundle-load failure offers retry.
- Measured evidence charts display only declared supplied numeric series, with nulls as gaps. These measurements are not confidence scores.
- Filterable reference boundaries, contiguous label disagreements, and missing-ball intervals. Jump buttons visit previous/next filtered events. Reference X/gaps do not create errors. Prediction gaps on labelled intervals count as visible disagreements. Boundary Δ is the nearest *same from→to transition* in the selected prediction minus reference time; this descriptive inspection aid is **not** the official evaluator's boundary matching.
- Per-match v1/v2 benchmark ledger includes metric source, spellF1, macroF1, runtime and model/split/evaluator provenance. Multiple matches can share one bundle; select “All matches” to compare the ledger. No unreported score is calculated by the UI.

## Version 1.0 JSON contract

See `schema.json` for the machine-readable contract and `demo.py` for a complete deterministic producer. Runtime validation is in `server.validate_bundle`; external JSON-schema libraries are optional and unnecessary. A minimal real export can contain no samples/evidence/media while still showing labels and benchmarks:

```json
{
  "schema_version": "1.0",
  "dataset": {
    "id": "permitted-public-evaluation",
    "title": "Public external holdout",
    "kind": "public_external",
    "split": "held-out-match",
    "provenance": "Dataset, licence/source, export command and revision"
  },
  "matches": [{
    "id": "match-01", "title": "Match 01", "duration_s": 30,
    "pitch": {"length_m": 105, "width_m": 68},
    "samples": [], "evidence_series": [],
    "truth": [{"start_s": 0, "end_s": 30, "state": "H"}],
    "predictions": {
      "v1": {"spells": [{"start_s": 0, "end_s": 30, "state": "H"}],
             "provenance": {"model_version": "revision-1", "split": "held-out-match"}}
    },
    "benchmarks": [{
      "version": "v1", "metric_source": "official",
      "spellF1": null, "macroF1": null, "runtime_s": null,
      "provenance": {"model_version": "revision-1", "split": "held-out-match",
                     "evaluator": "evaluation.possession_metrics.evaluate / repository revision"}
    }]
  }]
}
```

### Time and coordinates

`duration_s` is positive finite match-clock seconds. Samples have strictly increasing `t` in `[0,duration_s]`. Each spell is `{start_s,end_s,state}` with `0 <= start_s < end_s <= duration_s`; spells must be sorted and nonoverlapping, and gaps are permitted. Intervals are half-open `[start,end)`. H=home possession, A=away possession, D=dead ball, X=unknown reference/abstention prediction. At the exact duration endpoint the interface reads the final instant before the end.

Pitch coordinates are metres with origin at the rendered lower-left: x increases rightward from 0 to `length_m`, y upward from 0 to `width_m`. The screen/video mapping inverts y. Exporters must transform centred or normalized sources (for a centred 105×68 metre source: x += 52.5, y += 34). Numeric coordinates are never silently clamped. Out-of-pitch measurements may be supplied, and the drawing clips them near the pitch. `ball` is `[x,y]` or `[x,y,z]` or null. `players` entries are `{id,team:"H"|"A",x,y}`. `quality` may contain `player_coverage` (0–1), `ball_observed` (boolean), and additional documented fields. Missing keys mean not supplied, rather than zero. The interface currently exposes those two standardized quality fields.

Each evidence declaration is `{key,label,unit,description}`. `sample.evidence` maps a declared key to a finite number or null. Export actual available geometric/motion values, e.g. nearest home/away player distance, ball speed or observation age. Record derivation and validity rules in `description`. Null means missing/invalid. Do not turn a class label, distance margin, or display smoothness into invented probability/confidence.

### Metrics and provenance

`metric_source` is one of:

- `official`: imported output of the repository's official evaluator, on the stated permitted data/split. This means **official metric implementation**, not official target results or a leaderboard score. Use `spellF1` for evaluator `spell_f1_mean`, and `macroF1` for `macro_f1` (H/A/D; reference X excluded). Record exact evaluator revision/settings and test/training split. No source metric gets silently remapped by this interface.
- `proxy`: a diagnostic or alternative metric. State its definition and evaluator explicitly; never compare it as equivalent to official scores.
- `synthetic_demo`: illustrative software fixture. Synthetic bundles cannot claim `official` metrics.

Scores are finite 0–1 or null; runtime is nonnegative seconds or null. Always retain null for unavailable results. Every benchmark requires `version`, `metric_source`, and `provenance.model_version`, `.split`, `.evaluator`. Add e.g. commit, training_match_ids, test_match_id, evaluator_settings, hardware, runtime_scope, sample_count, seed, feature_version, calibration and processing_fps as extension provenance fields; they appear in the ledger. v1 and v2 can share a bundle without claiming the same training/evaluation procedure. Prediction provenance is separate from benchmark provenance. Model-facing confidence is not a required field.

### Optional locally configured media / private adapter

Match media config: `"media":{"id":"clip-01","offset_s":1.25,"fps":25}`. Mapping is **video time = match time + offset_s**; the video may begin before match time zero. Outside its available interval the match clock can still play. `fps` is source metadata/readout; the synchronization itself uses browser video seconds, so conversion from original frame numbers belongs in the adapter. Browser codec support determines whether an MP4/WebM plays; unavailable media produces an explicit fallback.

Local allowlist JSON: `{"clip-01":"relative/path/to/clip.mp4"}`. Relative paths resolve beside the allowlist file; absolute local paths also work. Only `.mp4`, `.webm`, `.ogv`, `.ogg`, `.mov`, `.m4v` files are accepted. Path strings are never included in the API response. Keep this operator config and private exports local. Do not attach paths or asset URLs to the match bundle as alternative media sources.

A private local target adapter can run separately under the user's local authorization and write the same schema with `dataset.kind:"private_local"`. Configure the resulting bundle and media explicitly. This workbench provides no target ingestion, frame extraction, target scoring, automatic discovery or remote processing. A person can inspect permitted local assets in their browser without sending frames to a model. Automated visual QA must continue using **synthetic/public permitted fixtures only**, never restricted target video frames or outputs.

## Validation

```powershell
python -m unittest discover -s tests -p test_workbench.py -v
node --check workbench/static/app.js
```

Tests use only generated data and temporary bytes, exercise contract rejection, missing observations, deterministic rendering, explicit allowlists, loopback binding, traversal/Host rejection and actual HTTP GET/HEAD/Range responses. They start an ephemeral loopback server and shut it down before returning.
