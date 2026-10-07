from __future__ import annotations

import unittest
from pathlib import Path

from src import road_watch
from src.config import ROAD_WATCH_ASSETS_DIR


class RoadWatchAssetTests(unittest.TestCase):
    def test_samples_catalog_loaded(self) -> None:
        samples = road_watch.get_road_watch_samples()
        self.assertEqual(len(samples), 4)
        for sample in samples:
            self.assertIn("id", sample)
            self.assertIn("filename", sample)
            self.assertIn("title", sample)
            self.assertIn("condition", sample)
            self.assertIn("severity", sample)
            self.assertIn("lighting", sample)
            self.assertIn("hud_telemetry", sample)
            self.assertIn("disclaimer", sample)
            self.assertIn("not resident evidence", sample["disclaimer"].casefold())

    def test_sample_files_exist_on_disk(self) -> None:
        samples = road_watch.get_road_watch_samples()
        for sample in samples:
            file_path = ROAD_WATCH_ASSETS_DIR / sample["filename"]
            self.assertTrue(file_path.is_file(), f"Asset {sample['filename']} must exist")
            self.assertGreater(file_path.stat().st_size, 10_000, "Asset size must be substantial")

    def test_get_sample_by_id(self) -> None:
        sample = road_watch.get_road_watch_sample("RW-01-URBAN-DAY")
        self.assertIsNotNone(sample)
        self.assertEqual(sample["severity"], "Critical")
        self.assertIn("Urban", sample["title"])

        missing = road_watch.get_road_watch_sample("NON_EXISTENT")
        self.assertIsNone(missing)

    def test_sample_image_base64_generation(self) -> None:
        uri = road_watch.get_sample_image_base64("dashcam_pothole_urban_day.jpg")
        self.assertTrue(uri.startswith("data:image/jpeg;base64,"))
        self.assertGreater(len(uri), 1000)

    def test_sample_image_bytes(self) -> None:
        image_bytes = road_watch.get_sample_image_bytes(0)
        self.assertIsNotNone(image_bytes)
        self.assertTrue(image_bytes.startswith(b"\xff\xd8"))


if __name__ == "__main__":
    unittest.main()
