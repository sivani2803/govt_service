"""Cached contextual image providers for decorative service-category visuals.

Google Programmable Search, when configured, is used for a single search per
category/day. If it is unavailable or fails, that category uses the existing
Unsplash integration on a later day/configuration or the local illustration;
the service never makes a second paid/provider search for a category that day.
Fetched images are validated, resized, metadata-stripped, and served as bytes.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import html
import ipaddress
import json
import os
import re
import time
from dataclasses import asdict, dataclass, replace
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import streamlit as st
from PIL import Image, ImageOps

from src.config import APP_DATA_DIR

_CACHE_TTL_SECONDS = 24 * 60 * 60
_MAX_SEARCH_RESPONSE_BYTES = 1_500_000
_MAX_IMAGE_DOWNLOAD_BYTES = 5 * 1024 * 1024
_MAX_STORED_IMAGE_BYTES = 300 * 1024
_MAX_CACHE_ENTRIES_PER_DAY = 32
_DAILY_CALL_BUDGET = 20
_DEFAULT_TIMEOUT_SECONDS = 4.0
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_IMAGE_SIZE_LIMITS = {"thumbnail": (480, 270), "card": (960, 540), "hero": (1280, 720)}
_CATEGORY_TERMS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("pothole", "road damage", "road repair", "street repair"), "road pothole repair city"),
    (("streetlight", "street light", "lighting", "lamp post"), "street light outage public infrastructure"),
    (("waste", "garbage", "trash", "rubbish", "sanitation", "litter"), "garbage collection city sanitation"),
    (("drain", "sewer", "flood", "stormwater"), "city storm drain maintenance"),
    (("water", "hydrant", "leak", "pipe"), "municipal water pipe repair"),
    (("sidewalk", "footpath", "pavement"), "city sidewalk repair accessibility"),
    (("park", "tree", "green space"), "city park public space maintenance"),
    (("traffic", "signal", "sign"), "city traffic signal street sign"),
)
_CANONICAL_LABELS = {
    "road pothole repair city": "Roads",
    "street light outage public infrastructure": "Streetlights",
    "garbage collection city sanitation": "Waste",
    "city storm drain maintenance": "Drainage",
    "municipal water pipe repair": "Water",
    "city sidewalk repair accessibility": "Sidewalks",
    "city park public space maintenance": "Parks",
    "city traffic signal street sign": "Traffic",
}


@dataclass(frozen=True)
class ImageResult:
    """Image and attribution data returned by a category image provider."""

    url: str | None
    image_bytes: bytes | None
    alt_text: str
    credit: str
    source_page_url: str | None
    provider_name: str


def _clean_label(category: str) -> str:
    return " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", str(category)).split())[:120] or "Civic service"


def _category_query(category: str) -> str:
    lowered = _clean_label(category).casefold()
    for terms, query in _CATEGORY_TERMS:
        if any(term in lowered for term in terms):
            return query
    return f"{lowered[:90]} city public infrastructure photo"


def _secret(name: str, media_name: str | None = None) -> str:
    value = os.environ.get(name, "").strip()
    if value and not value.casefold().startswith(("replace-", "your-", "<")):
        return value
    try:
        secrets = st.secrets
        value = str(secrets.get(name, "") or "").strip()
        if not value:
            media = secrets.get("media", {})
            if hasattr(media, "get"):
                value = str(media.get(media_name or name.casefold(), "") or "").strip()
    except (FileNotFoundError, KeyError, TypeError, AttributeError):
        return ""
    return "" if value.casefold().startswith(("replace-", "your-", "<")) else value


def _provider_order() -> tuple[str, ...]:
    configured = os.environ.get("CIVICPULSE_IMAGE_PROVIDERS", "google,unsplash,local")
    names = tuple(name.strip().casefold() for name in configured.split(","))
    return tuple(name for name in names if name in {"google", "unsplash", "local"}) or ("local",)


def _timeout_seconds() -> float:
    try:
        value = float(os.environ.get("CIVICPULSE_IMAGE_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT_SECONDS))
    except (TypeError, ValueError):
        value = _DEFAULT_TIMEOUT_SECONDS
    return max(3.0, min(5.0, value))


def _daily_budget() -> int:
    try:
        return max(0, min(1000, int(os.environ.get("CIVICPULSE_IMAGE_DAILY_BUDGET", _DAILY_CALL_BUDGET))))
    except (TypeError, ValueError):
        return _DAILY_CALL_BUDGET


def _cache_path() -> Path:
    configured = os.environ.get("CIVICPULSE_IMAGE_CACHE_PATH", "").strip()
    return Path(configured).expanduser() if configured else APP_DATA_DIR / "category_image_cache.json"


def _active_provider(order: tuple[str, ...], google_key: str, cse_id: str, unsplash_key: str) -> str:
    for provider in order:
        if provider == "google" and google_key and cse_id:
            return provider
        if provider == "unsplash" and unsplash_key:
            return provider
        if provider == "local":
            return provider
    return "local"


def _is_safe_https_url(url: object) -> bool:
    if not isinstance(url, str) or len(url) > 2048:
        return False
    try:
        parsed = urlsplit(url)
        if parsed.scheme.casefold() != "https" or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.rstrip(".").casefold()
        if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal", ".test")):
            return False
        if parsed.port not in (None, 443):
            return False
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return "." in host
        return address.is_global
    except ValueError:
        return False


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request: Request, file: Any, code: int, message: str, headers: Any, new_url: str) -> Request | None:
        destination = urljoin(request.full_url, new_url)
        if not _is_safe_https_url(destination):
            return None
        return super().redirect_request(request, file, code, message, headers, destination)


def _http_open(request: Request, timeout: float) -> Any:
    opener = build_opener(_SafeRedirectHandler())
    return opener.open(request, timeout=timeout)


def _normalize_image(payload: bytes, size: str) -> bytes | None:
    try:
        with Image.open(BytesIO(payload)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                return None
            if source.width * source.height > 30_000_000:
                return None
            source.verify()
        with Image.open(BytesIO(payload)) as source:
            if source.width * source.height > 30_000_000:
                return None
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail(_IMAGE_SIZE_LIMITS.get(size, _IMAGE_SIZE_LIMITS["card"]), Image.Resampling.LANCZOS)
            quality = 78
            while True:
                output = BytesIO()
                image.save(output, format="WEBP", quality=quality, method=4)
                normalized = output.getvalue()
                if len(normalized) <= _MAX_STORED_IMAGE_BYTES:
                    return normalized
                if quality > 46:
                    quality -= 8
                    continue
                if image.width <= 320 or image.height <= 180:
                    return None
                image.thumbnail((int(image.width * 0.8), int(image.height * 0.8)), Image.Resampling.LANCZOS)
                quality = 68
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return None


def _download_image(url: str, category: str, provider: str, credit: str, source_page: str | None, size: str, timeout: float) -> ImageResult | None:
    if not _is_safe_https_url(url):
        return None
    request = Request(url, headers={"User-Agent": "CivicPulse/1.0 (decorative civic category imagery)", "Accept": "image/jpeg,image/png,image/webp"})
    try:
        with _http_open(request, timeout=timeout) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else url
            if not _is_safe_https_url(final_url):
                return None
            headers = getattr(response, "headers", {})
            content_type = str(headers.get("Content-Type", "")).split(";", 1)[0].strip().casefold()
            content_length = headers.get("Content-Length")
            if content_type not in _ALLOWED_IMAGE_TYPES:
                return None
            if content_length and int(content_length) > _MAX_IMAGE_DOWNLOAD_BYTES:
                return None
            payload = response.read(_MAX_IMAGE_DOWNLOAD_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
        return None
    if not payload or len(payload) > _MAX_IMAGE_DOWNLOAD_BYTES:
        return None
    normalized = _normalize_image(payload, size)
    if normalized is None:
        return None
    return ImageResult(
        url=None,
        image_bytes=normalized,
        alt_text=f"Contextual civic image for {_clean_label(category)}; not evidence for a specific report.",
        credit=credit,
        source_page_url=source_page if _is_safe_https_url(source_page) else None,
        provider_name=provider,
    )


def _search_google(category: str, query: str, api_key: str, cse_id: str, size: str, timeout: float) -> ImageResult | None:
    deadline = time.monotonic() + timeout
    params = urlencode(
        {
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "searchType": "image",
            "safe": "active",
            "imgType": "photo",
            "imgSize": "large" if size == "thumbnail" else "xlarge",
            "rights": "cc_publicdomain",
            "num": 10,
        }
    )
    request = Request(
        f"https://www.googleapis.com/customsearch/v1?{params}",
        headers={"Accept": "application/json", "User-Agent": "CivicPulse/1.0"},
    )
    try:
        with _http_open(request, timeout=timeout) as response:
            body = response.read(_MAX_SEARCH_RESPONSE_BYTES + 1)
        if len(body) > _MAX_SEARCH_RESPONSE_BYTES:
            return None
        results = json.loads(body.decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeDecodeError, TypeError):
        return None
    items = results.get("items", []) if isinstance(results, dict) else []
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        image_meta = item.get("image") if isinstance(item.get("image"), dict) else {}
        try:
            width, height = int(image_meta.get("width", 0)), int(image_meta.get("height", 0))
        except (TypeError, ValueError):
            continue
        image_url = item.get("link")
        source_page = image_meta.get("contextLink")
        if width < height or not _is_safe_https_url(image_url) or not _is_safe_https_url(source_page):
            continue
        return _download_image(
            image_url,
            category,
            "Google Programmable Search",
            "Google image result · public-domain usage-rights filter applied; verify the source licence before reuse",
            source_page,
            size,
            max(0.1, deadline - time.monotonic()),
        )
    return None


def _search_unsplash(category: str, query: str, access_key: str, size: str, timeout: float) -> ImageResult | None:
    # Reuse the existing Unsplash search, preserving its official API endpoint
    # and attribution links while downloading/re-serving the selected image.
    from src.media import get_relevant_image

    deadline = time.monotonic() + timeout
    result = get_relevant_image(query, timeout=timeout, access_key=access_key)
    if not result:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    return _download_image(
        result.get("image_url", ""),
        category,
        "Unsplash",
        f"Photo by {result.get('author', 'Unsplash photographer')} · Unsplash",
        result.get("photo_url"),
        size,
        remaining,
    )


def _local_image(category: str, size: str) -> ImageResult:
    from src.media import generate_category_banner

    image_bytes = generate_category_banner(_clean_label(category))
    return ImageResult(
        url=None,
        image_bytes=image_bytes,
        alt_text=f"Illustration for {_clean_label(category)}; not evidence for a specific report.",
        credit="Illustration generated locally by CivicPulse",
        source_page_url=None,
        provider_name="Local illustration",
    )


def _serialize_result(result: ImageResult) -> dict[str, Any]:
    record = asdict(result)
    record["image_bytes"] = base64.b64encode(result.image_bytes).decode("ascii") if result.image_bytes else None
    return record


def _deserialize_result(record: object) -> ImageResult | None:
    if not isinstance(record, dict):
        return None
    try:
        image_bytes = base64.b64decode(record["image_bytes"], validate=True) if record.get("image_bytes") else None
        url = record.get("url")
        if not image_bytes and not _is_safe_https_url(url):
            return None
        return ImageResult(
            url=url if isinstance(url, str) else None,
            image_bytes=image_bytes,
            alt_text=str(record.get("alt_text", "Contextual civic category image")),
            credit=str(record.get("credit", "")),
            source_page_url=record.get("source_page_url") if _is_safe_https_url(record.get("source_page_url")) else None,
            provider_name=str(record.get("provider_name", "Unknown provider")),
        )
    except (ValueError, TypeError, KeyError):
        return None


@contextlib.contextmanager
def _cache_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path(f"{path}.lock")
    with lock_path.open("a+b") as lock_file:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _read_cache(path: Path, cache_day: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("date") == cache_day:
            if isinstance(payload.get("items"), dict):
                return payload
    except (OSError, ValueError, TypeError):
        pass
    return {"date": cache_day, "calls": 0, "items": {}}


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


def _resolve_category_image(
    category: str,
    query: str,
    size: str,
    order: tuple[str, ...],
    google_key: str,
    cse_id: str,
    unsplash_key: str,
    daily_budget: int,
    timeout: float,
    cache_day: str,
    cache_file: str,
) -> ImageResult:
    """Resolve one provider image, reserving one daily search call per category."""
    path = Path(cache_file)
    category_key = hashlib.sha256(" ".join(query.casefold().split()).encode("utf-8")).hexdigest()[:24]
    provider = _active_provider(order, google_key, cse_id, unsplash_key)
    visual_label = _CANONICAL_LABELS.get(query, _clean_label(category))
    fallback = _local_image(visual_label, size)

    with _cache_lock(path):
        cache = _read_cache(path, cache_day)
        existing = cache["items"].get(category_key)
        if isinstance(existing, dict):
            if existing.get("state") == "pending":
                return fallback
            stored = _deserialize_result(existing.get("result"))
            if stored is not None:
                return replace(
                    stored,
                    alt_text=f"Contextual civic image for {_clean_label(category)}; not evidence for a specific report.",
                )
        if provider == "local":
            return fallback
        if int(cache.get("calls", 0)) >= daily_budget:
            cache["items"][category_key] = {"state": "complete", "result": _serialize_result(fallback)}
            _write_cache(path, cache)
            return fallback
        if len(cache["items"]) >= _MAX_CACHE_ENTRIES_PER_DAY:
            return fallback
        # Reserve the category and budget before network I/O. If this process
        # exits mid-request, subsequent runs use the local visual today instead
        # of accidentally issuing a second billable search.
        cache["calls"] = int(cache.get("calls", 0)) + 1
        cache["items"][category_key] = {"state": "pending", "provider": provider}
        _write_cache(path, cache)

    deadline = time.monotonic() + timeout
    try:
        if provider == "google":
            result = _search_google(category, query, google_key, cse_id, size, max(0.1, deadline - time.monotonic()))
        else:
            result = _search_unsplash(category, query, unsplash_key, size, max(0.1, deadline - time.monotonic()))
    except Exception:
        # Provider failures (including optional SDK/secrets/network issues) are
        # intentionally silent; the generated category image remains available.
        result = None
    final_result = result or fallback

    with _cache_lock(path):
        cache = _read_cache(path, cache_day)
        cache["items"][category_key] = {"state": "complete", "result": _serialize_result(final_result)}
        _write_cache(path, cache)
    return final_result


@st.cache_data(ttl=_CACHE_TTL_SECONDS, max_entries=128, show_spinner=False)
def _cached_category_image(
    category: str,
    query: str,
    size: str,
    order: tuple[str, ...],
    google_key: str,
    cse_id: str,
    unsplash_key: str,
    daily_budget: int,
    timeout: float,
    cache_day: str,
    cache_file: str,
) -> ImageResult:
    try:
        return _resolve_category_image(
            category,
            query,
            size,
            order,
            google_key,
            cse_id,
            unsplash_key,
            daily_budget,
            timeout,
            cache_day,
            cache_file,
        )
    except OSError:
        return _local_image(category, size)


def get_category_image(category: str, size: str = "card", *, use_external: bool = True) -> ImageResult:
    """Return an attributed, sanitized image or the local offline illustration.

    The on-disk daily cache key is the category (not the requested display
    size), enforcing at most one remote provider/search call per category/day.
    """
    label = _clean_label(category)
    size_name = size.strip().casefold() if isinstance(size, str) else "card"
    if size_name not in _IMAGE_SIZE_LIMITS:
        size_name = "card"
    order = _provider_order() if use_external else ("local",)
    unsplash_key = ""
    if use_external:
        try:
            from src.media import _unsplash_key

            unsplash_key = _unsplash_key()
        except Exception:
            unsplash_key = ""
    return _cached_category_image(
        label,
        _category_query(label),
        size_name,
        order,
        _secret("GOOGLE_API_KEY", "google_api_key") if use_external else "",
        _secret("GOOGLE_CSE_ID", "google_cse_id") if use_external else "",
        unsplash_key if use_external else "",
        _daily_budget(),
        _timeout_seconds(),
        date.today().isoformat(),
        str(_cache_path()),
    )


def category_image_markup(category: str, result: ImageResult, *, variant: str = "card", icon: str = "◇") -> str:
    """Build accessible image-card markup; use only trusted provider data."""
    label = _clean_label(category)
    safe_alt = html.escape(result.alt_text, quote=True)
    safe_label = html.escape(label)
    image_source = ""
    if result.image_bytes:
        mime = "image/webp" if result.provider_name != "Local illustration" else "image/png"
        # The local renderer emits PNG; remote providers are normalized to WebP.
        image_source = f"data:{mime};base64,{base64.b64encode(result.image_bytes).decode('ascii')}"
    elif result.url and _is_safe_https_url(result.url):
        image_source = result.url
    source = html.escape(result.source_page_url or "", quote=True)
    credit = html.escape(result.credit or result.provider_name)
    attribution_text = (
        f'<a href="{source}" target="_blank" rel="noopener noreferrer">{credit}</a>'
        if source
        else credit
    )
    attribution = f'<div class="category-attribution">{attribution_text}<span>Context image · not report evidence</span></div>'
    if not image_source:
        return (
            f'<div class="category-visual category-visual-{variant}" role="img" aria-label="{safe_alt}">'
            f'<div class="category-skeleton"><span>{html.escape(icon)}</span><strong>{safe_label}</strong>'
            '<small>Context image unavailable</small></div></div>' + attribution
        )
    return (
        f'<div class="category-visual category-visual-{variant}">'
        f'<img src="{image_source}" alt="{safe_alt}" loading="lazy">'
        '<div class="category-image-overlay"></div>'
        f'<div class="category-visual-title"><span aria-hidden="true">{html.escape(icon)}</span>'
        f'<strong>{safe_label}</strong></div></div>{attribution}'
    )
