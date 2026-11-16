"""Serve only the public website on loopback, including seekable video ranges."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1] / 'website'


def byte_range(value: str, size: int) -> tuple[int, int]:
    """Parse one inclusive HTTP byte range; reject unsatisfiable ranges."""
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', value.strip())
    if not match or not any(match.groups()) or size <= 0:
        raise ValueError('invalid byte range')
    first, last = match.groups()
    if not first:
        count = int(last)
        if count <= 0:
            raise ValueError('empty suffix range')
        return max(0, size - count), size - 1
    start = int(first)
    end = min(size - 1, int(last)) if last else size - 1
    if start >= size or end < start:
        raise ValueError('unsatisfiable byte range')
    return start, end


class PublicSiteHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining = None
        relative = unquote(urlsplit(self.path).path).lstrip('/') or 'index.html'
        candidate = ROOT / relative
        if (any(part.startswith('.') for part in Path(relative).parts)
                or not candidate.resolve().is_relative_to(ROOT.resolve())
                or any(part.is_symlink() for part in [candidate, *candidate.parents] if part != ROOT.parent)
                or not candidate.is_file()):
            self.send_error(404)
            return None
        stream = candidate.open('rb')
        size = candidate.stat().st_size
        start, end, status = 0, size - 1, 200
        requested = self.headers.get('Range')
        if requested:
            try:
                start, end = byte_range(requested, size)
                status = 206
            except ValueError:
                stream.close()
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return None
        stream.seek(start)
        self.remaining = end - start + 1
        self.send_response(status)
        self.send_header('Content-Type', self.guess_type(str(candidate)))
        self.send_header('Content-Length', str(self.remaining))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if status == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        return stream

    def copyfile(self, source, outputfile):
        remaining = self.remaining
        while remaining:
            block = source.read(min(64 * 1024, remaining))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8788)
    args = parser.parse_args()
    handler = partial(PublicSiteHandler, directory=str(ROOT))
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'Public website: http://127.0.0.1:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
