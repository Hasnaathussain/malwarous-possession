# Possession Atlas

An original, dependency-free public companion to Malwarous. It replays saved
external-development model outputs, explains the frozen method and exposes an
illustrative sequence-decoder lab. It runs entirely in the browser.

**[Live website](https://malwarous-atlas.vercel.app)**

## Preview

From the repository root, with Python 3.11 or later:

```sh
python -B scripts/serve_public_site.py --port 8788
```

Open http://127.0.0.1:8788. This loopback-only server serves the `website/`
directory and supports byte ranges for cold-cache video seeking. There is no
Python or Node dependency installation for the website. The Python model and
local analysis workbench have their own pinned environment in the main README.

## Explore

- Choose one of six licensed matches and either half, or the synthetic camera demo.
- Play, change speed, step frames, seek by time/frame, or jump between sides.
- Compare the V1 and selected V2 timelines; optionally show provider annotations.
- Inspect observation age and declared evidence values. Missing observations stay missing.
- Customize team colors, numbers, grid, trails and a geometric region diagram.
- Share a replay position or export an attributed field PNG.
- Inspect all 18 development rows and adjust synthetic evidence in the decoder lab.

Keyboard: Space plays/pauses, left/right steps frames when focus is outside form
controls. The interface supports reduced motion and responsive narrow layouts.

The replay is not a live feed or in-browser model inference. The frozen model uses
future context. Display positions are thinned; full-rate state intervals and
canonical benchmark values are preserved. Synthetic labels are authored fixtures,
not accuracy measurements. The lab does not change the fitted model. See
[public data provenance](PUBLIC_DATA.md) for licensing and transformations.

## Host on Vercel

Connect the repository with Root Directory `website`, Framework Preset **Other**,
empty build/install commands, and Output Directory `.`. `vercel.json` provides
static hosting and security headers. No secrets, environment variables, API,
database, uploads, analytics or external browser assets are needed. Deploy only
this directory; the model and research workspace are not web assets.

## Verify

```sh
node --test scripts/test_decoder_lab.mjs
node scripts/check_public_site.mjs http://127.0.0.1:8788
```

Run those commands from the repository root. The browser check requires a recent
Node runtime with built-in WebSocket support and Brave on Windows by default;
set `ATLAS_QA_BROWSER` to another Chromium executable when needed. It uses its own
headless profile, checks public-only data, and writes ignored QA screenshots.
The production URL can replace the local URL. Python tests cover the public
export gate, interval preservation and preview server boundaries.
