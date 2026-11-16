"""Cold-cache video seeking and local public-root boundaries."""
from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from scripts import serve_public_site as site


@pytest.mark.parametrize(('value', 'expected'), [
    ('bytes=0-3', (0, 3)), ('bytes=7-', (7, 9)),
    ('bytes=-4', (6, 9)), ('bytes=8-100', (8, 9)),
])
def test_single_ranges(value, expected):
    assert site.byte_range(value, 10) == expected


@pytest.mark.parametrize('value', ['bytes=-0', 'bytes=10-', 'bytes=5-2',
                                      'bytes=0-1,4-5', 'bytes=-', 'items=0-1'])
def test_invalid_ranges(value):
    with pytest.raises(ValueError):
        site.byte_range(value, 10)


def test_public_root_and_seekable_bytes(tmp_path, monkeypatch):
    public = tmp_path / 'website'
    public.mkdir()
    (public / 'index.html').write_bytes(b'<p>public</p>')
    (public / 'clip.mp4').write_bytes(b'0123456789')
    (public / '.hidden').write_bytes(b'hidden')
    (tmp_path / 'private.txt').write_bytes(b'private')
    monkeypatch.setattr(site, 'ROOT', public)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(site.PublicSiteHandler, directory=str(public)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base + '/') as response:
            assert response.read() == b'<p>public</p>'
        with urlopen(Request(base + '/clip.mp4', headers={'Range': 'bytes=3-6'})) as response:
            assert response.status == 206
            assert response.headers['Content-Range'] == 'bytes 3-6/10'
            assert response.read() == b'3456'
        with urlopen(Request(base + '/clip.mp4', method='HEAD')) as response:
            assert response.headers['Accept-Ranges'] == 'bytes'
            assert response.headers['Content-Length'] == '10'
            assert response.read() == b''
        for path in ('/.hidden', '/%2e%2e/private.txt', '/missing'):
            with pytest.raises(HTTPError) as error:
                urlopen(base + path)
            assert error.value.code == 404
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + '/clip.mp4', headers={'Range': 'bytes=99-'}))
        assert error.value.code == 416
        assert error.value.headers['Content-Range'] == 'bytes */10'
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
