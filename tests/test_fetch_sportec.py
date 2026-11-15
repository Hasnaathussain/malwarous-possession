"""Network-free synthetic contracts for the public-source fetcher."""

import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.fetch_sportec import _download, _safe_files, default_destination, fetch


class FakeResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def synthetic_file_entries(match_id="J03WPY"):
    component = "DFL-COM-000002"
    filenames = [
        f"DFL_02_01_matchinformation_{component}_DFL-MAT-{match_id}.xml",
        f"DFL_03_02_events_raw_{component}_DFL-MAT-{match_id}.xml",
        f"DFL_04_03_positions_raw_observed_{component}_DFL-MAT-{match_id}.xml",
    ]
    return [
        {"name": name, "size": 3, "computed_md5": hashlib.md5(b"xml", usedforsecurity=False).hexdigest(),
         "download_url": f"https://ndownloader.figshare.com/files/{i}"}
        for i, name in enumerate(filenames)
    ]


class FetchSportecTests(unittest.TestCase):
    def test_default_cache_path_follows_the_selected_development_match(self):
        self.assertEqual(default_destination("J03WN1").parts[-2:], ("sportec", "J03WN1"))
        self.assertEqual(default_destination("J03WR9").parts[-2:], ("sportec", "J03WR9"))
        with self.assertRaises(ValueError):
            default_destination("J03WMX")

    def test_file_set_requires_one_safe_file_of_each_kind(self):
        entries = _safe_files({"files": synthetic_file_entries()}, "J03WPY")
        self.assertEqual([e["kind"] for e in entries], ["metadata", "events", "tracking"])
        self.assertEqual(sum(e["size"] for e in entries), 9)

    def test_rejects_missing_duplicate_unsafe_and_non_figshare_files(self):
        cases = []
        cases.append(synthetic_file_entries()[:2])
        cases.append(synthetic_file_entries() + [synthetic_file_entries()[0]])
        bad_name = synthetic_file_entries()
        bad_name[0]["name"] = "../DFL_02_01_matchinformation_DFL-COM-000002_DFL-MAT-J03WPY.xml"
        cases.append(bad_name)
        bad_url = synthetic_file_entries()
        bad_url[0]["download_url"] = "https://example.invalid/file"
        cases.append(bad_url)
        for files in cases:
            with self.subTest(files=len(files)):
                with self.assertRaises(ValueError):
                    _safe_files({"files": files}, "J03WPY")

    def test_streamed_file_must_match_public_size_and_checksum(self):
        entry = {
            "name": "synthetic.xml", "size": 3,
            "md5": hashlib.md5(b"xml", usedforsecurity=False).hexdigest(),
            "url": "https://ndownloader.figshare.com/files/0",
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            with patch("scripts.fetch_sportec.urlopen", side_effect=lambda request, timeout: FakeResponse(b"xml")):
                self.assertTrue(_download(entry, path))
                self.assertEqual((path / "synthetic.xml").read_bytes(), b"xml")
                self.assertFalse(_download(entry, path))

    def test_bad_download_checksum_leaves_no_partial_file(self):
        entry = {
            "name": "synthetic.xml", "size": 99, "md5": "0" * 32,
            "url": "https://ndownloader.figshare.com/files/0",
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            with patch("scripts.fetch_sportec.urlopen", side_effect=lambda request, timeout: FakeResponse(b"xml")):
                with self.assertRaises(ValueError):
                    _download(entry, path)
            self.assertEqual(list(path.iterdir()), [])

    def test_rejects_sealed_audit_before_any_network_access(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                fetch("J03WMX", Path(folder))


if __name__ == "__main__":
    unittest.main()
