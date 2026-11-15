"""Synthetic-only contract, file-serving and media-range integration tests."""
import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from workbench.demo import make_demo
from workbench.make_demo_video import render_frame
from workbench.server import byte_range, load_bundle, load_media_map, make_server, validate_bundle


class ContractTests(unittest.TestCase):
    def test_demo_is_deterministic_and_honest(self):
        first, second = make_demo(), make_demo()
        self.assertEqual(first, second)
        self.assertIs(validate_bundle(first), first)
        self.assertEqual(first["dataset"]["kind"], "synthetic_demo")
        match = first["matches"][0]
        self.assertEqual(len(match["samples"]), 721)
        self.assertTrue(any(sample["ball"] is None for sample in match["samples"]))
        for row in match["benchmarks"]:
            self.assertEqual(row["metric_source"], "synthetic_demo")
            self.assertIsNone(row["spellF1"])
            self.assertIsNone(row["macroF1"])

    def test_invalid_data_rejected(self):
        mutations = [
            lambda d: d.update(schema_version="9"),
            lambda d: d["matches"][0]["truth"][0].update(state="B"),
            lambda d: d["matches"][0]["truth"][1].update(start_s=0),
            lambda d: d["matches"][0]["samples"][1].update(t=0),
            lambda d: d["matches"][0]["samples"][0]["evidence"].update(home_nearest_m=float("nan")),
            lambda d: d["matches"][0]["samples"][0]["quality"].update(player_coverage=1.1),
            lambda d: d["matches"][0]["benchmarks"][0].update(metric_source="official"),
            lambda d: d["matches"][0].update(media={"id":"../../private", "offset_s":0}),
            lambda d: d["matches"][0].update(samples=[None]),
            lambda d: d.update(dataset=[]),
            lambda d: d["matches"][0].update(predictions=[]),
        ]
        base = make_demo()
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                bundle = copy.deepcopy(base); mutate(bundle)
                with self.assertRaises(ValueError):
                    validate_bundle(bundle)

    def test_optional_observations_and_gapped_labels(self):
        bundle = make_demo(); match = bundle["matches"][0]
        match["samples"] = []; match["truth"] = []
        match["predictions"] = {}; match["evidence_series"] = []
        self.assertIs(validate_bundle(bundle), bundle)

    def test_media_map_is_explicit_and_local(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "clip.mp4").write_bytes(b"fixture")
            config = root / "map.json"
            config.write_text(json.dumps({"clip":"clip.mp4"}), encoding="utf-8")
            self.assertEqual(load_media_map(config), {"clip":(root / "clip.mp4").resolve()})
            config.write_text(json.dumps({"clip":"https://example.com/video.mp4"}), encoding="utf-8")
            with self.assertRaises(ValueError): load_media_map(config)
            config.write_text(json.dumps({"clip":"\\\\example.invalid\\share\\clip.mp4"}), encoding="utf-8")
            with self.assertRaises(ValueError): load_media_map(config)
            config.write_text(json.dumps({"../clip":"clip.mp4"}), encoding="utf-8")
            with self.assertRaises(ValueError): load_media_map(config)

    def test_video_frame_is_exact_repeatable_rgb(self):
        sample = make_demo()["matches"][0]["samples"][0]
        frame = render_frame(sample)
        self.assertEqual(len(frame), 840*544*3)
        self.assertEqual(frame, render_frame(sample))

    def test_single_ranges(self):
        self.assertEqual(byte_range("bytes=2-4", 10), (2,4,True))
        self.assertEqual(byte_range("bytes=8-100", 10), (8,9,True))
        self.assertEqual(byte_range("bytes=-3", 10), (7,9,True))
        self.assertEqual(byte_range("bytes=3-", 10), (3,9,True))
        for header in ["bytes=10-", "bytes=-0", "bytes=5-2", "bytes=0-1,3-4", "bytes=-", "garbage"]:
            with self.subTest(header=header), self.assertRaises(ValueError): byte_range(header,10)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.media = Path(cls.temp.name) / "allowed.mp4"
        cls.media.write_bytes(b"0123456789")
        cls.server = make_server(make_demo(), {"allowed":cls.media}, port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=5); cls.temp.cleanup()

    def request(self, path, headers=None, method="GET"):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        conn.request(method,path,headers=headers or {})
        response = conn.getresponse(); data = response.read()
        result = (response.status,dict(response.getheaders()),data)
        conn.close()
        return result

    def test_page_and_data_round_trip(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, body = self.request("/")
        self.assertEqual(status,200); self.assertIn(b"Possession workbench",body)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Cross-Origin-Resource-Policy"],"same-origin")
        status, _, body = self.request("/api/bundle")
        self.assertEqual(status,200); self.assertEqual(validate_bundle(json.loads(body))["schema_version"],"1.0")
        self.assertNotIn(str(self.media).encode(),body)
        for route in ["/app.js","/style.css"]:
            self.assertEqual(self.request(route)[0],200)

    def test_arbitrary_files_and_traversal_are_rejected(self):
        for path in ["/server.py", "/workbench/server.py", "/../README.md", "/%2e%2e/README.md",
                     "/%252e%252e/README.md", "/media/../server.py", "/media/missing", "/api/bundle?path=secret", "/static/", "/media/allowed/extra"]:
            with self.subTest(path=path): self.assertEqual(self.request(path)[0],404)
        self.assertEqual(self.request("/api/bundle", {"Host":"attacker.example"})[0],403)

    def test_actual_http_range_and_head(self):
        status,headers,body = self.request("/media/allowed",{"Range":"bytes=2-4"})
        self.assertEqual((status,body),(206,b"234"))
        self.assertEqual(headers["Content-Range"],"bytes 2-4/10")
        status,_,body = self.request("/media/allowed",{"Range":"bytes=-2"})
        self.assertEqual((status,body),(206,b"89"))
        status,headers,body = self.request("/media/allowed",{"Range":"bytes=100-"})
        self.assertEqual((status,body),(416,b"")); self.assertEqual(headers["Content-Range"],"bytes */10")
        status,headers,body = self.request("/media/allowed",method="HEAD")
        self.assertEqual((status,body),(200,b"")); self.assertEqual(headers["Content-Length"],"10")


if __name__ == "__main__":
    unittest.main()
