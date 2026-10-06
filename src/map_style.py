"""Map tile selection with a working dark local fallback."""
from __future__ import annotations

import os
from urllib.parse import urlencode

import folium
import streamlit as st
from branca.element import Element


_CARTO_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors '
    '&copy; <a href="https://carto.com/attributions">CARTO</a>'
)


def _carto_key() -> str:
    key = os.environ.get("CARTO_BASEMAP_API_KEY", "").strip()
    if key and not key.casefold().startswith("replace-"):
        return key
    try:
        configured_key = str(st.secrets.get("maps", {}).get("carto_basemap_key", "")).strip()
        return "" if configured_key.casefold().startswith("replace-") else configured_key
    except (FileNotFoundError, KeyError, TypeError, AttributeError):
        return ""


def make_civic_map(*, location: tuple[float, float] | list[float], zoom_start: int, **options: object) -> folium.Map:
    """Create a map using keyed CARTO Dark Matter or a darkened OSM fallback."""
    key = _carto_key()
    if key:
        tile_url = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png?" + urlencode({"key": key})
        map_object = folium.Map(
            location=location,
            zoom_start=zoom_start,
            tiles=tile_url,
            attr=_CARTO_ATTRIBUTION,
            subdomains="abcd",
            max_zoom=20,
            control_scale=True,
            **options,
        )
        return map_object

    map_object = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
        control_scale=True,
        **options,
    )
    # Keep the familiar street map readable on the dark CivicPulse canvas.
    # Only the tile pane is transformed; markers, controls, and attribution stay crisp.
    map_object.get_root().script.add_child(
        Element(
            f"{map_object.get_name()}.whenReady(function(){{"
            f"var pane={map_object.get_name()}.getPane('tilePane');"
            "if(pane){pane.style.filter='invert(.9) hue-rotate(180deg) brightness(.82) contrast(.92) saturate(.72)';}"
            "});"
        )
    )
    return map_object
