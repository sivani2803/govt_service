from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from src import config, storage
from src.vision import analyze_civic_image


def png_bytes(color: str = "navy") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (24, 16), color).save(buffer, format="PNG")
    return buffer.getvalue()


class VisionServiceTests(unittest.TestCase):
    def test_default_provider_is_honest_metadata_only_demo(self) -> None:
        result = analyze_civic_image(png_bytes(), service_name="Road damage")
        self.assertIn("Demo Vision Analysis", result["engine"])
        self.assertEqual(result["status"], "demo_metadata_only")
        self.assertEqual(result["findings"], ())
        self.assertIsNone(result["confidence_pct"])
        self.assertIsNone(result["severity"])
        self.assertEqual(result["image_metadata"]["width"], 24)

    def test_rejects_unreadable_image(self) -> None:
        with self.assertRaises(ValueError):
            analyze_civic_image(b"not an image")


class StorageWorkflowTests(unittest.TestCase):
    def test_report_assignment_resolution_and_notification_read_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_data = root / "data"
            uploads = app_data / "uploads"
            complaints_path = app_data / "live_complaints.csv"
            notices_path = app_data / "agency_notifications.csv"
            with patch.multiple(
                storage,
                APP_DATA_DIR=app_data,
                UPLOADS_DIR=uploads,
                LIVE_COMPLAINTS_PATH=complaints_path,
                NOTIFICATION_HISTORY_PATH=notices_path,
            ):
                submitted = datetime.now(timezone.utc)
                complaint = storage.add_complaint(
                    {
                        "SERVICECODE": "ROAD",
                        "SERVICECODEDESCRIPTION": "Road damage",
                        "PREDICTED_PRIORITY": "High",
                        "PREDICTED_DEPARTMENT": "Roads",
                        "STATUS": "Open",
                    },
                    submitted,
                    [("png", png_bytes())],
                )
                request_id = complaint["SERVICEREQUESTID"]
                self.assertEqual(len(storage.get_complaint_image_paths(complaint)), 1)
                self.assertIn("Priority estimate generated", complaint["STATUS_HISTORY"])

                updated = storage.update_complaint_status(
                    request_id,
                    "In Progress",
                    event_label="Inspection Started",
                    officer_name="Field Officer",
                    officer_notes="Inspection underway",
                    inspection_image_files=[("png", png_bytes("orange"))],
                )
                self.assertIsNotNone(updated)
                self.assertEqual(updated["ASSIGNED_OFFICER"], "Field Officer")
                self.assertEqual(len(storage.get_complaint_image_paths(updated, "INSPECTION_IMAGE_PATHS")), 1)

                resolved = storage.update_complaint_status(
                    request_id,
                    "Resolved",
                    event_label="Resolution Submitted",
                    resolution_notes="Surface repaired",
                    resolution_image_files=[("png", png_bytes("green"))],
                )
                self.assertEqual(resolved["STATUS"], "Resolved")
                self.assertEqual(len(storage.get_complaint_image_paths(resolved, "RESOLUTION_IMAGE_PATHS")), 1)

                with self.assertRaises(ValueError):
                    storage.update_complaint_status(request_id, "Closed")

                storage.append_csv_record(
                    config.NOTIFICATION_COLUMNS,
                    {
                        "NOTIFICATION_ID": "NTF-TEST",
                        "SERVICEREQUESTID": request_id,
                        "NOTIFICATION_STATUS": "New",
                    },
                )
                self.assertTrue(storage.mark_notification_read("NTF-TEST"))
                self.assertEqual(storage.list_notifications().iloc[0]["NOTIFICATION_STATUS"], "Read")
                self.assertFalse(storage.mark_notification_read("NTF-MISSING"))

    def test_rejects_image_extension_content_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            storage._validate_image_data("jpg", png_bytes())


if __name__ == "__main__":
    unittest.main()
