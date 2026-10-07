from __future__ import annotations

import pickle

import streamlit as st

from src.config import ROUTING_MAP_PATH


_US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire",
    "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio", "oklahoma",
    "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee",
    "texas", "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming",
    "dc", "district of columbia",
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", "il", "in",
    "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv",
    "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn",
    "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
}


def _is_indian_location(city: str, state: str) -> bool:
    normalized_state = str(state).strip().casefold()
    normalized_city = str(city).strip().casefold()
    return bool(normalized_state and normalized_state not in _US_STATES) or normalized_city == "vijayawada"


def _local_department(service_code: str, service_name: str) -> str:
    text = f"{service_code} {service_name}".casefold()
    if service_code == "S05SL" or any(word in text for word in ("streetlight", "street light", "lighting")):
        return "Local street lighting service · jurisdiction to confirm"
    if service_code == "DCWFQ" or any(word in text for word in ("water", "leak", "pipe", "flood", "hydrant")):
        return "Local water service · jurisdiction to confirm"
    if any(word in text for word in ("waste", "trash", "garbage", "litter", "sanitation", "recycl")):
        return "Local waste and sanitation service · jurisdiction to confirm"
    if any(word in text for word in ("pothole", "road", "roadway", "sidewalk", "pavement")):
        return "Local roads service · jurisdiction to confirm"
    return "Local civic service · jurisdiction to confirm"


@st.cache_resource(show_spinner=False)
def load_routing_map() -> dict[str, str]:
    if not ROUTING_MAP_PATH.is_file():
        raise FileNotFoundError(f"Department routing map does not exist: {ROUTING_MAP_PATH}")
    try:
        with ROUTING_MAP_PATH.open("rb") as mapping_file:
            mapping = pickle.load(mapping_file)
    except (pickle.PickleError, EOFError) as exc:
        raise RuntimeError(f"The saved department routing map could not be read: {exc}") from exc
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("The saved deployment routing map must be a non-empty SERVICECODE mapping.")
    invalid = [code for code, department in mapping.items() if not isinstance(department, str)]
    if invalid:
        raise ValueError(f"The saved routing map contains invalid department values for: {invalid[:5]}")
    return {str(code): department for code, department in mapping.items()}


def route_department(
    service_code: str,
    *,
    city: str = "",
    state: str = "",
    service_name: str = "",
) -> str:
    """Use neutral local routing labels for Indian locations; retain saved routes elsewhere."""
    if _is_indian_location(city, state):
        return _local_department(str(service_code), service_name)
    mapping = load_routing_map()
    if service_code in mapping:
        return mapping[service_code]
    raise ValueError(f"No saved department route exists for service code {service_code!r}.")
