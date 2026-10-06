"""Contextual civic imagery with an explicitly illustrative local fallback.

Category images use the provider service in ``src.category_images``; Unsplash
metadata and Pillow's original illustration remain the existing providers.
Illustrations are never presented as report evidence.
"""
from __future__ import annotations

import base64
import html
import os
import re
from functools import lru_cache
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st
from PIL import Image, ImageDraw, ImageFont


def _unsplash_key() -> str:
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
    if key and not key.casefold().startswith("replace-"):
        return key
    try:
        configured_key = str(st.secrets.get("media", {}).get("unsplash_access_key", "")).strip()
        return "" if configured_key.casefold().startswith("replace-") else configured_key
    except (FileNotFoundError, KeyError, TypeError, AttributeError):
        return ""


@st.cache_data(ttl=3600, show_spinner=False)
def _search_unsplash(query: str, access_key: str, timeout: float = 4.0) -> dict[str, str] | None:
    params = urlencode({"query": query, "per_page": 1, "orientation": "landscape"})
    request = Request(
        f"https://api.unsplash.com/search/photos?{params}",
        headers={"Authorization": f"Client-ID {access_key}", "Accept-Version": "v1"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = __import__("json").loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return None
    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not results:
        return None
    photo = results[0]
    urls = photo.get("urls", {})
    links = photo.get("links", {})
    user = photo.get("user", {})
    image_url = urls.get("small") or urls.get("regular")
    page_url = links.get("html")
    author = user.get("name", "Unsplash photographer")
    author_url = user.get("links", {}).get("html", "https://unsplash.com")
    if (
        not image_url
        or not image_url.startswith("https://images.unsplash.com/")
        or not page_url
        or not page_url.startswith("https://unsplash.com/")
        or not author_url.startswith("https://unsplash.com/")
    ):
        return None
    source_suffix = "utm_source=civicpulse&utm_medium=referral"
    return {
        "image_url": image_url,
        "alt": photo.get("alt_description") or photo.get("description") or query,
        "author": author,
        "author_url": f"{author_url}?{source_suffix}",
        "photo_url": f"{page_url}?{source_suffix}",
        "provider": "Unsplash",
    }


def get_relevant_image(query: str, *, timeout: float = 4.0, access_key: str | None = None) -> dict[str, str] | None:
    """Find one attributed Unsplash image result, or return ``None`` for fallback."""
    cleaned_query = re.sub(r"\s+", " ", str(query)).strip()[:120]
    key = access_key.strip() if isinstance(access_key, str) else _unsplash_key()
    if not cleaned_query or not key:
        return None
    return _search_unsplash(cleaned_query, key, max(3.0, min(5.0, float(timeout))))


@lru_cache(maxsize=32)
def generate_category_banner(query: str) -> bytes:
    """Draw a local, non-photographic civic category illustration with Pillow."""
    width, height = 800, 360
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            blend = x / max(1, width - 1)
            pixels[x, y] = (
                int(10 + 8 * blend),
                int(39 + 18 * blend),
                int(36 + 28 * blend),
            )
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((560, -175, 910, 180), fill=(13, 148, 136, 45), outline=(94, 234, 212, 115), width=2)
    draw.ellipse((604, -135, 850, 105), outline=(94, 234, 212, 70), width=2)
    # Street, lane markings, and civic buildings create a reusable local illustration.
    draw.rectangle((0, 255, width, height), fill=(8, 22, 24, 255))
    draw.polygon([(0, 314), (250, 261), (800, 261), (800, 360), (0, 360)], fill=(30, 48, 50, 255))
    for x in (370, 495, 620, 745):
        draw.rounded_rectangle((x, 300, x + 52, 307), radius=3, fill=(190, 174, 111, 215))
    draw.rectangle((573, 154, 618, 263), fill=(25, 59, 57, 255), outline=(91, 180, 163, 160), width=2)
    draw.rectangle((633, 181, 694, 263), fill=(28, 67, 61, 255), outline=(91, 180, 163, 160), width=2)
    draw.rectangle((708, 126, 761, 263), fill=(24, 55, 57, 255), outline=(91, 180, 163, 160), width=2)
    for x, y in ((583, 168), (600, 168), (583, 191), (600, 191), (643, 195), (668, 195), (719, 141), (740, 141), (719, 164), (740, 164)):
        draw.rectangle((x, y, x + 7, y + 10), fill=(112, 223, 195, 175))
    label = (re.sub(r"\s+", " ", str(query)).strip()[:48] or "Civic service").encode("ascii", "replace").decode("ascii")
    try:
        font = ImageFont.truetype("arial.ttf", 29)
        small_font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font, small_font = ImageFont.load_default(), ImageFont.load_default()
    draw.rounded_rectangle((34, 35, 340, 68), radius=15, fill=(13, 148, 136, 70), outline=(94, 234, 212, 100), width=1)
    draw.text((49, 44), "CIVICPULSE  /  SERVICE AREA", font=small_font, fill=(153, 246, 228, 255))
    draw.text((34, 102), label, font=font, fill=(239, 255, 250, 255), stroke_width=0)
    draw.text((36, 149), "Illustrative category visual", font=small_font, fill=(179, 207, 200, 255))
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def show_relevant_image(query: str, *, use_external: bool = True, width: int | None = None) -> None:
    """Render a safe, attributed category image using the provider fallback chain."""
    from src.category_images import category_image_markup, get_category_image

    category = " ".join(str(query).split())[:120] or "Civic service"
    size = "thumbnail" if width and width <= 200 else "card"
    placeholder = st.empty()
    placeholder.markdown(
        '<div class="category-visual category-visual-thumbnail category-skeleton" role="status" '
        f'aria-label="Loading a contextual image for {html.escape(category, quote=True)}">'
        '<span class="skeleton-shimmer"></span><span>Loading contextual image…</span></div>',
        unsafe_allow_html=True,
    )
    result = get_category_image(category, size=size, use_external=use_external)
    placeholder.markdown(
        category_image_markup(category, result, variant="thumbnail" if size == "thumbnail" else "card"),
        unsafe_allow_html=True,
    )


def show_category_image_card(category: str, *, icon: str = "◇") -> None:
    """Render a category tile with a contextual image header and attribution."""
    from src.category_images import category_image_markup, get_category_image

    label = " ".join(str(category).split())[:120] or "Civic service"
    placeholder = st.empty()
    placeholder.markdown(
        '<div class="category-visual category-visual-card category-skeleton" role="status" '
        f'aria-label="Loading a contextual image for {html.escape(label, quote=True)}">'
        '<span class="skeleton-shimmer"></span><span>Loading category image…</span></div>',
        unsafe_allow_html=True,
    )
    result = get_category_image(label, size="card")
    placeholder.markdown(
        category_image_markup(label, result, variant="card", icon=icon),
        unsafe_allow_html=True,
    )


def show_citizen_hero() -> None:
    """Render a contextual, accessible dashboard hero with a report CTA."""
    from src.category_images import get_category_image

    category = "Civic infrastructure"
    placeholder = st.empty()
    placeholder.markdown(
        '<section class="citizen-hero" role="status" aria-label="Loading civic category image">'
        '<div class="citizen-hero-image category-skeleton"><span class="skeleton-shimmer"></span></div>'
        '<div class="citizen-hero-overlay"><div class="hero-kicker">CivicPulse · Turning civic signals into action</div>'
        '<h1>Let’s make your neighborhood work better.</h1>'
        '<p>Report a local issue, share its location, and follow the request through resolution.</p>'
        '<span class="hero-cta" aria-hidden="true">＋ Report an issue →</span></div></section>',
        unsafe_allow_html=True,
    )
    result = get_category_image(category, size="hero")
    image_source = ""
    if result.image_bytes:
        mime = "image/png" if result.provider_name == "Local illustration" else "image/webp"
        image_source = f"data:{mime};base64,{base64.b64encode(result.image_bytes).decode('ascii')}"
    elif result.url:
        image_source = result.url
    safe_alt = html.escape(result.alt_text, quote=True)
    safe_credit = html.escape(result.credit or result.provider_name)
    source_link = html.escape(result.source_page_url or "", quote=True)
    attribution_text = (
        f'<a href="{source_link}" target="_blank" rel="noopener noreferrer">{safe_credit}</a>'
        if source_link
        else safe_credit
    )
    attribution = f'<div class="media-attribution">{attribution_text} · contextual image, not report evidence</div>'
    image_markup = (
        f'<img class="citizen-hero-image" src="{image_source}" alt="{safe_alt}" loading="eager">'
        if image_source
        else f'<div class="citizen-hero-image category-skeleton" role="img" aria-label="{safe_alt}"></div>'
    )
    placeholder.markdown(
        '<section class="citizen-hero">' + image_markup
        + '<div class="citizen-hero-overlay"><div class="hero-kicker">CivicPulse · Turning civic signals into action</div>'
        + '<h1>Let’s make your neighborhood work better.</h1>'
        + '<p>Report a local issue, share its location, and follow the request through resolution.</p>'
        + '<a class="hero-cta" href="?nav=report" aria-label="Report an issue" title="Report an issue">'
        + '<span aria-hidden="true">＋</span> Report an issue <span aria-hidden="true">→</span></a></div></section>'
        + attribution,
        unsafe_allow_html=True,
    )
