from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

_component_path = Path(__file__).resolve().parent / "browser_location_component"
_browser_location = components.declare_component(
    "government_request_browser_location",
    path=str(_component_path),
)


def browser_location(key: str) -> Any:
    return _browser_location(key=key, default=None)
