"""Loopback-only, allowlisted HTTP server. Run: python -m workbench.server."""
from __future__ import annotations

import argparse
import json
import math
import mimetypes
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .demo import make_demo

ROOT = Path(__file__).resolve().parent
STATES = {"H", "A", "D", "X"}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_bundle(bundle):
    """Fail closed on invalid time/label/metric data; retain documented extension fields."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(isinstance(bundle, dict) and bundle.get("schema_version") == "1.0", "schema_version must be '1.0'")
    dataset = bundle.get("dataset", {})
    require(isinstance(dataset, dict), "dataset must be an object")
    require(dataset.get("kind") in {"synthetic_demo", "public_external", "private_local"}, "invalid dataset.kind")
    for field in ("id", "title", "split"):
        require(isinstance(dataset.get(field), str) and bool(dataset[field]), "dataset." + field + " required")
    require(isinstance(dataset.get("provenance"), (str, dict)) and bool(dataset["provenance"]), "dataset.provenance required")
    matches = bundle.get("matches")
    require(isinstance(matches, list) and bool(matches), "matches must be a nonempty list")
    ids = set()
    for match in matches:
        require(isinstance(match, dict), "match must be an object")
        identity = match.get("id")
        require(isinstance(identity, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", identity), "invalid match id")
        require(identity not in ids, "duplicate match id")
        ids.add(identity)
        duration = match.get("duration_s")
        require(finite(duration) and duration > 0, "duration_s must be positive")
        require(isinstance(match.get("title"), str) and bool(match["title"]), "match title required")
        pitch = match.get("pitch", {})
        require(isinstance(pitch, dict), "pitch must be an object")
        require(all(finite(pitch.get(k)) and pitch[k] > 0 for k in ("length_m", "width_m")), "invalid pitch dimensions")
        def check_spells(rows):
            require(isinstance(rows, list), "spells must be a list")
            last = 0.0
            for spell in rows:
                require(isinstance(spell, dict), "spell must be an object")
                start, end = spell.get("start_s"), spell.get("end_s")
                require(finite(start) and finite(end) and 0 <= start < end <= duration and start >= last,
                        "spells must be sorted, nonoverlapping, within duration")
                require(spell.get("state") in STATES, "invalid H/A/D/X state")
                last = end
        check_spells(match.get("truth", []))
        predictions = match.get("predictions", {})
        require(isinstance(predictions, dict), "predictions must be an object")
        for prediction in predictions.values():
            require(isinstance(prediction, dict), "prediction must be an object")
            check_spells(prediction.get("spells", []))
            require(isinstance(prediction.get("provenance"), dict), "prediction provenance required")
        series = match.get("evidence_series", [])
        require(isinstance(series, list) and all(isinstance(item, dict) for item in series), "evidence_series must be a list of objects")
        keys = [item.get("key") for item in series]
        require(all(isinstance(k, str) and k for k in keys) and len(set(keys)) == len(keys), "invalid evidence series keys")
        require(all(isinstance(item.get("label"), str) and item["label"] and isinstance(item.get("unit"), str)
                    and isinstance(item.get("description"), str) and item["description"] for item in series), "evidence metadata required")
        previous = -1.0
        samples = match.get("samples", [])
        require(isinstance(samples, list), "samples must be a list")
        for sample in samples:
            require(isinstance(sample, dict), "sample must be an object")
            time = sample.get("t")
            require(finite(time) and previous < time <= duration and time >= 0, "sample times must increase within duration")
            previous = time
            ball = sample.get("ball")
            require(ball is None or isinstance(ball, list) and len(ball) in (2, 3) and all(finite(v) for v in ball), "invalid ball coordinates")
            players = sample.get("players", [])
            require(isinstance(players, list) and all(isinstance(player, dict) for player in players), "players must be a list of objects")
            for player in players:
                require(player.get("team") in {"H", "A"} and all(finite(player.get(k)) for k in ("x", "y")), "invalid player")
            quality = sample.get("quality", {})
            require(isinstance(quality, dict), "quality must be an object")
            if "player_coverage" in quality:
                require(finite(quality["player_coverage"]) and 0 <= quality["player_coverage"] <= 1, "invalid player coverage")
            if "ball_observed" in quality:
                require(isinstance(quality["ball_observed"], bool), "ball_observed must be boolean")
            evidence = sample.get("evidence", {})
            require(isinstance(evidence, dict), "evidence must be an object")
            for key, value in evidence.items():
                require(key in keys and (value is None or finite(value)), "evidence must be declared and finite or null")
        media = match.get("media")
        if media:
            require(isinstance(media, dict), "media must be an object")
            require(isinstance(media.get("id"), str) and re.fullmatch(r"[A-Za-z0-9_.-]+", media["id"]), "invalid media id")
            require(finite(media.get("offset_s", 0)), "invalid media offset")
            require("fps" not in media or finite(media["fps"]) and media["fps"] > 0, "invalid media fps")
        benchmarks = match.get("benchmarks", [])
        require(isinstance(benchmarks, list), "benchmarks must be a list")
        for row in benchmarks:
            require(isinstance(row, dict), "benchmark must be an object")
            require(row.get("metric_source") in {"official", "synthetic_demo", "proxy"}, "invalid metric source")
            require(isinstance(row.get("provenance"), dict) and all(isinstance(row["provenance"].get(k), str) and row["provenance"][k] for k in ("model_version", "split", "evaluator")), "benchmark model_version/split/evaluator required")
            require(isinstance(row.get("version"), str) and bool(row["version"]), "benchmark version required")
            for key in ("spellF1", "macroF1"):
                value = row.get(key)
                require(value is None or finite(value) and 0 <= value <= 1, "invalid " + key)
            runtime = row.get("runtime_s")
            require(runtime is None or finite(runtime) and runtime >= 0, "invalid runtime_s")
            require(not (dataset["kind"] == "synthetic_demo" and row["metric_source"] == "official"), "synthetic data cannot claim official metrics")
    return bundle


def load_bundle(path=None):
    if path is None:
        return validate_bundle(make_demo())
    with Path(path).open(encoding="utf-8-sig") as stream:
        return validate_bundle(json.load(stream))


def load_media_map(path=None):
    """Only explicit files listed by a local operator can be streamed."""
    if path is None:
        return {}
    config_path = Path(path).resolve()
    mapping = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if not isinstance(mapping, dict):
        raise ValueError("media map must be an object of id: local_path")
    result = {}
    for key, value in mapping.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", key) or not isinstance(value, str):
            raise ValueError("invalid media mapping")
        if value.startswith(("\\\\", "//")) or "://" in value:
            raise ValueError("media mapping must name a local file, not a network path or URL")
        candidate = Path(value)
        resolved = (config_path.parent / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
        if not resolved.is_file():
            raise ValueError("mapped media file does not exist for " + key)
        if resolved.suffix.lower() not in {".mp4", ".webm", ".ogv", ".ogg", ".mov", ".m4v"}:
            raise ValueError("unsupported media extension for " + key)
        result[key] = resolved
    return result


def byte_range(header, size):
    """A single RFC 9110 byte range; unsupported/malformed/empty -> ValueError."""
    if not header:
        return 0, size - 1, False
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
    if not match or not any(match.groups()) or size == 0:
        raise ValueError("invalid byte range")
    first, last = match.groups()
    if first:
        start, end = int(first), min(int(last), size - 1) if last else size - 1
    else:
        length = int(last)
        if length <= 0:
            raise ValueError("invalid suffix range")
        start, end = max(0, size - length), size - 1
    if start >= size or end < start:
        raise ValueError("unsatisfiable byte range")
    return start, end, True


def make_server(bundle, media_map=None, port=8765):
    validate_bundle(bundle)
    media_map = media_map or {}
    # Exact routes only: no caller-controlled path is ever resolved on disk.
    static = {"/": (ROOT / "static" / "index.html", "text/html; charset=utf-8"),
              "/app.js": (ROOT / "static" / "app.js", "text/javascript; charset=utf-8"),
              "/style.css": (ROOT / "static" / "style.css", "text/css; charset=utf-8")}
    payload = json.dumps(bundle, allow_nan=False).encode()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # No requests or local paths written to logs.

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            super().end_headers()

        def do_HEAD(self):
            self.do_GET(head=True)

        def do_GET(self, head=False):
            # DNS rebinding / cross-origin browser requests cannot retrieve local data.
            host = self.headers.get("Host", "").split(":")[0]
            if host != "127.0.0.1":
                self.send_error(403, "Use the loopback address")
                return
            parts = urlsplit(self.path)
            path = unquote(parts.path)
            if parts.query or parts.fragment or ".." in path or "\\" in path or "%" in path:
                self.send_error(404)
                return
            if path == "/api/bundle":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if not head:
                    self.wfile.write(payload)
                return
            if path in static:
                file, mime = static[path]
            elif path.startswith("/media/") and path[7:] in media_map:
                file = media_map[path[7:]]
                mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            else:
                self.send_error(404)
                return
            size = file.stat().st_size
            is_media = path.startswith("/media/")
            try:
                start, end, partial = byte_range(self.headers.get("Range") if is_media else None, size)
            except ValueError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(max(0, end - start + 1)))
            if is_media:
                self.send_header("Accept-Ranges", "bytes")
            if partial:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if not head:
                with file.open("rb") as stream:
                    stream.seek(start)
                    remaining = end - start + 1
                    try:
                        while remaining > 0:
                            block = stream.read(min(65536, remaining))
                            if not block:
                                break
                            self.wfile.write(block)
                            remaining -= len(block)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, help="Explicit permitted bundle JSON; omitted = synthetic software demo")
    parser.add_argument("--media-map", type=Path, help="Local id-to-file JSON allowlist (never included in bundle)")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        server = make_server(load_bundle(args.data), load_media_map(args.media_map), args.port)
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.exit(2, f"Workbench configuration error: {error}\n")
    print(f"Local workbench: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
