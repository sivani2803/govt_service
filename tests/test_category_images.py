from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from PIL import Image

from src import category_images


def image_result(provider: str = "Google Programmable Search") -> category_images.ImageResult:
    return category_images.ImageResult(
        url=None,
        image_bytes=b"test image bytes",
        alt_text="Contextual road works photo; not evidence.",
        credit=f"Photo credit · {provider}",
        source_page_url="https://public.example.org/source",
        provider_name=provider,
    )


class CategoryImageProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.temp_dir.name) / "category_cache.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def resolve(self, *, google_key: str = "google-key", cse_id: str = "engine-id", unsplash_key: str = "unsplash-key", budget: int = 20, category: str = "Potholes") -> category_images.ImageResult:
        return category_images._resolve_category_image(
            category,
            category_images._category_query(category),
            "card",
            ("google", "unsplash", "local"),
            google_key,
            cse_id,
            unsplash_key,
            budget,
            4.0,
            "2026-10-06",
            str(self.cache_path),
        )

    def test_provider_precedence_and_missing_credential_fallback(self) -> None:
        google_image = image_result()
        with patch.object(category_images, "_search_google", return_value=google_image) as google, patch.object(
            category_images, "_search_unsplash", side_effect=AssertionError("second provider should not be queried")
        ):
            result = self.resolve()
        self.assertEqual(result.provider_name, "Google Programmable Search")
        google.assert_called_once()

        self.cache_path.unlink()
        Path(f"{self.cache_path}.lock").unlink(missing_ok=True)
        with patch.object(category_images, "_search_google", side_effect=AssertionError("missing key must skip Google")), patch.object(
            category_images, "_search_unsplash", return_value=image_result("Unsplash")
        ) as unsplash:
            result = self.resolve(google_key="", cse_id="")
        self.assertEqual(result.provider_name, "Unsplash")
        unsplash.assert_called_once()

    def test_missing_all_keys_uses_local_art_without_network(self) -> None:
        with patch.object(category_images, "_secret", return_value=""), patch(
            "src.media._unsplash_key", return_value=""
        ), patch.object(category_images, "_provider_order", return_value=("google", "unsplash", "local")), patch.object(
            category_images, "_cache_path", return_value=self.cache_path
        ), patch.object(category_images, "_search_google", side_effect=AssertionError("must remain offline")), patch.object(
            category_images, "_search_unsplash", side_effect=AssertionError("must remain offline")
        ):
            category_images._cached_category_image.clear()
            result = category_images.get_category_image("Street lighting")
        self.assertEqual(result.provider_name, "Local illustration")
        self.assertTrue(result.image_bytes)

    def test_category_cache_prevents_second_search_same_day(self) -> None:
        search_result = image_result()
        with patch.object(category_images, "_search_google", return_value=search_result) as search:
            first = self.resolve()
        with patch.object(category_images, "_search_google", side_effect=AssertionError("cache miss")):
            second = self.resolve()
        self.assertEqual(first.image_bytes, second.image_bytes)
        self.assertEqual(first.provider_name, second.provider_name)
        search.assert_called_once()
        saved = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["calls"], 1)
        self.assertEqual(len(saved["items"]), 1)

    def test_keyword_aliases_share_one_daily_category_search(self) -> None:
        with patch.object(category_images, "_search_google", return_value=image_result()) as search:
            first = self.resolve(category="Potholes")
            second = self.resolve(category="Road damage")
        self.assertEqual(first.provider_name, second.provider_name)
        self.assertIn("Road damage", second.alt_text)
        search.assert_called_once()

    def test_search_timeout_falls_back_and_is_cached_for_the_day(self) -> None:
        with patch.object(category_images, "_search_google", side_effect=TimeoutError):
            first = self.resolve()
        with patch.object(category_images, "_search_google", side_effect=AssertionError("timed-out category must not retry")):
            second = self.resolve()
        self.assertEqual(first.provider_name, "Local illustration")
        self.assertEqual(second.provider_name, "Local illustration")

    def test_url_validation_rejects_http_and_private_hosts_before_fetch(self) -> None:
        with patch.object(category_images, "_http_open", side_effect=AssertionError("invalid URL was fetched")):
            self.assertIsNone(category_images._download_image(
                "http://images.example.org/photo.jpg", "Roads", "test", "credit", None, "card", 4.0
            ))
            self.assertIsNone(category_images._download_image(
                "https://127.0.0.1/photo.jpg", "Roads", "test", "credit", None, "card", 4.0
            ))

    def test_download_rejects_non_image_content_type_and_oversize_header(self) -> None:
        class Response:
            def __init__(self, content_type: str, content_length: str):
                self.headers = {"Content-Type": content_type, "Content-Length": content_length}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def geturl(self):
                return "https://images.example.org/photo.jpg"

            def read(self, _limit=-1):
                return b"not an image"

        with patch.object(category_images, "_http_open", return_value=Response("text/html", "12")):
            self.assertIsNone(category_images._download_image(
                "https://images.example.org/photo.jpg", "Roads", "test", "credit", None, "card", 4.0
            ))
        with patch.object(
            category_images,
            "_http_open",
            return_value=Response("image/jpeg", str(category_images._MAX_IMAGE_DOWNLOAD_BYTES + 1)),
        ):
            self.assertIsNone(category_images._download_image(
                "https://images.example.org/photo.jpg", "Roads", "test", "credit", None, "card", 4.0
            ))

    def test_valid_image_is_reencoded_and_served_as_bytes(self) -> None:
        buffer = BytesIO()
        Image.new("RGB", (1600, 900), "teal").save(buffer, format="PNG")
        image_payload = buffer.getvalue()

        class Response:
            headers = {"Content-Type": "image/png", "Content-Length": str(len(image_payload))}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def geturl(self):
                return "https://images.example.org/photo.jpg"

            def read(self, _limit=-1):
                return image_payload

        with patch.object(category_images, "_http_open", return_value=Response()):
            result = category_images._download_image(
                "https://images.example.org/photo.jpg", "Roads", "Google", "Credit", "https://source.example.org/page", "thumbnail", 4.0
            )
        self.assertIsNotNone(result)
        self.assertIsNone(result.url)
        self.assertEqual(result.provider_name, "Google")
        self.assertTrue(result.alt_text.endswith("not evidence for a specific report."))
        with Image.open(BytesIO(result.image_bytes)) as processed:
            self.assertEqual(processed.format, "WEBP")
            self.assertLessEqual(processed.width, 480)

    def test_daily_budget_hit_returns_local_art_without_search(self) -> None:
        with patch.object(category_images, "_search_google", side_effect=AssertionError("budget must block search")):
            result = self.resolve(budget=0)
        self.assertEqual(result.provider_name, "Local illustration")

    def test_google_search_uses_safe_photo_public_domain_filter(self) -> None:
        response_body = json.dumps({
            "items": [{
                "link": "https://images.example.org/road.jpg",
                "image": {"width": 1600, "height": 900, "contextLink": "https://public.example.org/roads"},
            }]
        }).encode("utf-8")

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit=-1):
                return response_body

        with patch.object(category_images, "_http_open", return_value=Response()) as open_request, patch.object(
            category_images, "_download_image", return_value=image_result()
        ) as download:
            result = category_images._search_google("Roads", "road pothole repair city", "secret", "engine", "hero", 4.0)
        self.assertEqual(result.provider_name, "Google Programmable Search")
        query = parse_qs(urlsplit(open_request.call_args.args[0].full_url).query)
        self.assertEqual(query["safe"], ["active"])
        self.assertEqual(query["imgType"], ["photo"])
        self.assertEqual(query["rights"], ["cc_publicdomain"])
        self.assertEqual(query["searchType"], ["image"])
        download.assert_called_once()


if __name__ == "__main__":
    unittest.main()
