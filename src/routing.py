from __future__ import annotations

import pickle

import streamlit as st

from src.config import ROUTING_MAP_PATH


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


def route_department(service_code: str) -> str:
    mapping = load_routing_map()
    if service_code in mapping:
        return mapping[service_code]
    raise ValueError(f"No saved department route exists for service code {service_code!r}.")
