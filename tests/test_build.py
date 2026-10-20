import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("site_builder", ROOT / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ArchiveBuildTests(unittest.TestCase):
    def setUp(self):
        self.records = builder.load_records()

    def test_imported_records_and_fixed_addresses(self):
        builder.validate_records(self.records)
        works = [r for r in self.records if r.get("show_on_home") and not r.get("is_demo")]
        self.assertEqual(len(works), 17)
        self.assertEqual(sum(bool(r.get("video")) for r in works), 8)
        first = builder.prepare_record(next(r for r in works if r["id"] == "F001"))
        self.assertTrue(first["page_url"].endswith("/f/f001-jia/"))
        self.assertTrue(first["download_pdf_url"].endswith("/F001-card.pdf"))
        self.assertGreater(len(next(r for r in works if r["id"] == "F005")["story"]), 320)

    def test_media_paths_cannot_escape_media_directory(self):
        record = copy.deepcopy(self.records[0])
        record["photo"] = "README.md"
        with self.assertRaises(ValueError):
            builder.validate_records([record])

    def test_duplicate_slugs_rejected(self):
        records = copy.deepcopy(self.records[:2])
        records[1]["slug"] = records[0]["slug"]
        with self.assertRaisesRegex(ValueError, "slug"):
            builder.validate_records(records)

    def test_missing_gallery_image_rejected(self):
        record = copy.deepcopy(self.records[0])
        record["gallery"] = [{"path": "media/missing.jpg", "caption": "test"}]
        with self.assertRaises(FileNotFoundError):
            builder.validate_records([record])

    def test_private_record_not_rendered_or_copied(self):
        records = copy.deepcopy(self.records[:2])
        records[0]["visibility"] = "private"
        captured = []
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with patch.object(builder, "load_records", return_value=records), \
                 patch.object(builder, "OUTPUT_DIR", Path(directory) / "docs"), \
                 patch.object(builder, "ensure_inside_workspace"), \
                 patch.object(builder, "copy_public_assets", side_effect=lambda items: captured.extend(items)), \
                 patch.object(builder, "build_printable_exports"):
                builder.build_site()
                output = Path(directory) / "docs"
                self.assertFalse((output / "f" / records[0]["slug"]).exists())
                self.assertFalse((output / "qrcodes" / (records[0]["id"] + ".png")).exists())
                self.assertTrue((output / "f" / records[1]["slug"] / "index.html").is_file())
                self.assertEqual([r["id"] for r in captured], [records[1]["id"]])


if __name__ == "__main__":
    unittest.main()
