"""Acquire one development match from the public Figshare DFL/Sportec record.

The sealed audit match is intentionally not an accepted argument. All downloaded files are kept
under the ignored external_data_cache directory; this command must never be pointed at target data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.request import Request, urlopen


ARTICLE_API = "https://api.figshare.com/v2/articles/28196177"
DEV_MATCHES = {"J03WN1", "J03WPY", "J03WOH", "J03WQQ", "J03WOY", "J03WR9"}
FILE_KINDS = {
    "metadata": "DFL_02_01_matchinformation",
    "events": "DFL_03_02_events_raw",
    "tracking": "DFL_04_03_positions_raw_observed",
}


def default_destination(match_id: str) -> Path:
    if match_id not in DEV_MATCHES:
        raise ValueError("match is not in the predeclared development set")
    root = Path(__file__).resolve().parents[1]
    return root / "external_data_cache" / "sportec" / match_id


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def _safe_files(article: dict, match_id: str) -> list[dict]:
    selected = []
    for entry in article.get("files", []):
        name = entry.get("name", "")
        if match_id not in name:
            continue
        if not name.endswith(".xml") or Path(name).name != name:
            raise ValueError("unsafe public source file metadata")
        if not re.fullmatch(r"DFL_[0-9]{2}_[0-9]{2}_[A-Za-z0-9_]+_DFL-COM-[0-9]{6}_DFL-MAT-" + match_id + r"\.xml", name):
            raise ValueError("unexpected public source file name")
        url = entry.get("download_url", "")
        if not url.startswith("https://ndownloader.figshare.com/files/"):
            raise ValueError("unexpected public source URL")
        size = entry.get("size")
        checksum = entry.get("computed_md5")
        if not isinstance(size, int) or size <= 0 or not re.fullmatch(r"[0-9a-f]{32}", str(checksum)):
            raise ValueError("invalid public source checksum metadata")
        kind = next((key for key, prefix in FILE_KINDS.items() if name.startswith(prefix + "_")), None)
        if kind is None:
            raise ValueError("unexpected public source file kind")
        selected.append({"kind": kind, "name": name, "size": size, "md5": checksum, "url": url})

    if {entry["kind"] for entry in selected} != set(FILE_KINDS):
        raise ValueError("the public source did not provide the expected three-file set")
    if len(selected) != len(FILE_KINDS):
        raise ValueError("the public source file set contains duplicates")
    return sorted(selected, key=lambda entry: list(FILE_KINDS).index(entry["kind"]))


def _download(entry: dict, destination: Path) -> bool:
    target = destination / entry["name"]
    if target.exists():
        size, checksum = _hash_file(target)
        if size == entry["size"] and checksum == entry["md5"]:
            return False
        raise ValueError("an existing cached file does not match the public checksum")

    request = Request(entry["url"], headers={"User-Agent": "Malwarous-MTAH2027/1.0"})
    with urlopen(request, timeout=60) as response:
        if getattr(response, "status", 200) != 200:
            raise OSError("public source download failed")
        digest = hashlib.md5(usedforsecurity=False)
        size = 0
        with tempfile.NamedTemporaryFile(dir=destination, prefix=".partial-", delete=False) as tmp:
            temp_path = Path(tmp.name)
            try:
                while block := response.read(1024 * 1024):
                    size += len(block)
                    digest.update(block)
                    tmp.write(block)
                tmp.flush()
                os.fsync(tmp.fileno())
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise

    if size != entry["size"] or digest.hexdigest() != entry["md5"]:
        temp_path.unlink(missing_ok=True)
        raise ValueError("downloaded source file failed the published size or checksum check")
    temp_path.replace(target)
    return True


def fetch(match_id: str, destination: Path) -> dict[str, object]:
    if match_id not in DEV_MATCHES:
        raise ValueError("match is not in the predeclared development set")
    root = Path(__file__).resolve().parents[1]
    cache_root = (root / "external_data_cache").resolve()
    destination = destination.resolve()
    if cache_root != destination and cache_root not in destination.parents:
        raise ValueError("destination must stay under the ignored external cache")
    destination.mkdir(parents=True, exist_ok=True)

    request = Request(ARTICLE_API, headers={"User-Agent": "Malwarous-MTAH2027/1.0"})
    with urlopen(request, timeout=30) as response:
        article = json.load(response)
    entries = _safe_files(article, match_id)
    reused = 0
    downloaded = 0
    for entry in entries:
        if _download(entry, destination):
            downloaded += 1
        else:
            reused += 1
    manifest = {
        "source": ARTICLE_API,
        "license": "CC BY 4.0",
        "match_id": match_id,
        "files": [{k: entry[k] for k in ("kind", "name", "size", "md5")} for entry in entries],
    }
    (destination / "acquisition-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return {"match": match_id, "status": "completed", "files_downloaded": downloaded,
            "files_reused": reused}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("match_id", choices=sorted(DEV_MATCHES), default="J03WPY", nargs="?")
    parser.add_argument("--destination", type=Path, default=None)
    args = parser.parse_args()
    try:
        destination = args.destination or default_destination(args.match_id)
        result = fetch(args.match_id, destination)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        # This command handles public data only, but still uses a generic return to keep logs tidy.
        print(json.dumps({"match": args.match_id, "status": "failed",
                          "failure_type": type(exc).__name__}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
