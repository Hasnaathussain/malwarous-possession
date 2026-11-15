"""Verify the committed source inventory and every frozen inference dependency.

Git metadata and ignored local working files are not submission source. Every
tracked file must be declared, and every declared file must have the stated bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prepare_review_source as review


def verify(root: Path) -> dict:
    root = root.resolve(strict=True)
    manifest = json.loads(review.checked_file(root, review.MANIFEST).read_bytes())
    names = [entry['path'] for entry in manifest['files']]
    if len(set(names)) != len(names) or review.MANIFEST in names or manifest['excluded_self'] != review.MANIFEST:
        raise ValueError('invalid source inventory')
    expected = set(names) | {review.MANIFEST}
    indexed = None
    if (root / '.git').exists():
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '--stage', '-z'],
                                check=True, capture_output=True)
        indexed = {}
        for record in result.stdout.split(b'\x00'):
            if not record:
                continue
            metadata, name = record.split(b'\t', 1)
            mode, object_id, stage = metadata.split()
            if mode not in (b'100644', b'100755') or stage != b'0':
                raise ValueError('linked, nested or conflicted entries are not submission source')
            indexed[name.decode('utf-8')] = object_id
        actual = set(indexed)
        if not actual:
            raise ValueError('stage the reviewed inventory before verifying a new Git repository')
    else:
        actual = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
    if actual != expected:
        raise ValueError('tracked/source inventory differs from SOURCE_MANIFEST.json')
    for entry in manifest['files']:
        content = review.source_bytes(root, entry['path'])
        if hashlib.sha256(content).hexdigest() != entry['sha256'] or len(content) != entry['bytes']:
            raise ValueError('source checksum differs: '+entry['path'])
    if indexed is not None:
        # Check actual staged blobs too: names alone cannot catch a stale index
        # after the working tree and manifest have been edited.
        ordered = sorted(indexed)
        objects = subprocess.run(['git', '-C', str(root), 'cat-file', '--batch'],
            input=b''.join(indexed[name]+b'\n' for name in ordered),
            check=True, capture_output=True).stdout
        stream = io.BytesIO(objects)
        for name in ordered:
            header = stream.readline().split()
            if len(header) != 3 or header[1] != b'blob':
                raise ValueError('staged object is missing or not a file')
            content = stream.read(int(header[2]))
            if stream.read(1) != b'\n' or content != review.source_bytes(root, name):
                raise ValueError('staged bytes differ from reviewed source: '+name)
    review.verify_frozen_v2(root, set(names))
    return {'status': 'verified', 'source_files': len(expected),
            'frozen_source_report_model': 'pass'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(verify(args.root), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
