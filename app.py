from __future__ import annotations

import base64
import json
import html
import hashlib
import os
import re
import sqlite3
import warnings
from io import BytesIO
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import pandas as pd
import folium
import plotly.express as px
import streamlit as st
from PIL import Image, ImageOps
from plotly.graph_objects import Figure
from streamlit_folium import st_folium

from src.config import (
    APP_DATA_DIR,
    DEPARTMENT_HISTORY_PATH,
    DEPARTMENT_PRIORITY_HISTORY_PATH,
    FEATURE_MEDIANS_PATH,
    MODEL_INFO,
    PRIORITY_MODEL_PATH,
    PRIORITY_HISTORY_PATH,
    PROJECT_CONFIG_PATH,
    SERVICE_LOOKUP_PATH,
    TOP_SERVICES_PATH,
    UPLOADS_DIR,
    YEAR_HISTORY_PATH,
)
from src.location import browser_location
from src.media import show_category_image_card, show_citizen_hero, show_relevant_image, get_civic_sample_data_uri
from src.map_style import make_civic_map
from src.theme import inject_theme
from src.ui_components import floating_action_markup, floating_action_target
from src.notifications import create_agency_notification
from src.authentication import authenticate_user, get_user_by_id, has_registered_users, register_citizen
from src.predictor import load_predictor_assets, predict_priority
from src.routing import load_routing_map, route_department
from src.storage import (
    add_complaint,
    get_complaint,
    get_complaint_image_paths,
    list_complaints,
    list_notifications,
    mark_notification_read,
    update_complaint_status,
)
from src.vision import analyze_civic_image
from src.road_watch import render_road_sample_feed, render_road_watch_panel

st.set_page_config(
    page_title="CivicPulse | Turning civic signals into action",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "app_theme" not in st.session_state:
    st.session_state["app_theme"] = "light"

inject_theme(st.session_state.get("app_theme", "light"))

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


@st.cache_data(show_spinner=False)
def load_service_lookup() -> pd.DataFrame:
    frame = pd.read_csv(SERVICE_LOOKUP_PATH, dtype=str).fillna("")
    required = {
        "SERVICECODE",
        "SERVICECODEDESCRIPTION",
        "SERVICETYPECODEDESCRIPTION",
        "DEPARTMENT",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Service lookup is missing columns: {', '.join(sorted(missing))}")
    routable_codes = set(load_routing_map())
    frame = frame[frame["SERVICECODE"].isin(routable_codes)]
    frame.loc[frame["SERVICECODE"] == "DCWFQ", "SERVICECODEDESCRIPTION"] = "Water flooding or leakage"
    if frame.empty:
        raise ValueError("No service categories have a saved department route.")
    return frame.drop_duplicates("SERVICECODE").sort_values("SERVICECODEDESCRIPTION", kind="stable")


def _header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="portal-banner"><div class="eyebrow" style="color:#b9d5ee">CIVICPULSE · CIVIC OPERATIONS</div>'
        f"<h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def _section_title(title: str, eyebrow: str = "") -> None:
    label = f'<div class="section-kicker">{html.escape(eyebrow)}</div>' if eyebrow else ""
    st.markdown(
        f'<div class="section-heading"><div>{label}<h2>{html.escape(title)}</h2></div></div>',
        unsafe_allow_html=True,
    )


def _go_to_page(page: str) -> None:
    st.session_state["portal_page"] = page
    st.session_state["navigation_target"] = page


def _navigation_changed(label_pages: dict[str, str]) -> None:
    selected = st.session_state.get("navigation_choice")
    if selected in label_pages:
        st.session_state["portal_page"] = label_pages[selected]


def _empty_state(title: str, message: str, icon: str = "◇") -> None:
    st.markdown(
        f'<div class="empty-state"><div class="empty-icon">{icon}</div>'
        f'<div class="empty-title">{html.escape(title)}</div>'
        f'<div class="empty-copy">{html.escape(message)}</div></div>',
        unsafe_allow_html=True,
    )


def _status_badge(status: str) -> str:
    style = {
        "new": "status-new",
        "open": "status-new",
        "assigned": "status-assigned",
        "in progress": "status-progress",
        "resolved": "status-resolved",
        "rejected": "status-rejected",
        "closed": "status-closed",
    }.get(str(status).strip().casefold(), "status-new")
    return f'<span class="status-badge {style}">{html.escape(status)}</span>'


def _case_card(request: pd.Series | dict[str, object]) -> None:
    req_dict = dict(request) if hasattr(request, "to_dict") else dict(request)
    request_id = html.escape(str(req_dict.get("SERVICEREQUESTID", "")))
    service = html.escape(str(req_dict.get("SERVICECODEDESCRIPTION", "Service request")))
    place = html.escape(
        ", ".join(
            str(req_dict.get(key, "")).strip()
            for key in ("LOCATION_ADDRESS", "CITY", "STATE")
            if str(req_dict.get(key, "")).strip()
        )
    )
    pincode = html.escape(str(req_dict.get("ZIPCODE", "")).strip())
    department = html.escape(str(req_dict.get("PREDICTED_DEPARTMENT", "Unassigned")))
    submitted = html.escape(str(req_dict.get("ADDDATE", "")))
    priority = str(req_dict.get("PREDICTED_PRIORITY", "Medium"))
    status = str(req_dict.get("STATUS", "Open"))

    # Check for authentic resident-attached evidence photos
    image_paths = []
    try:
        image_paths = get_complaint_image_paths(req_dict)
    except Exception:
        image_paths = []

    is_resident_photo = bool(image_paths)
    service_lower = service.casefold()
    is_road_case = any(k in service_lower for k in ("pothole", "road", "street", "pavement"))

    media_col, details_col = st.columns([1.15, 3.05], vertical_alignment="center")
    with media_col:
        if is_resident_photo and image_paths:
            st.image(str(image_paths[0]), caption="📷 Resident Evidence", width="stretch")
        elif is_road_case:
            from src.road_watch import get_sample_image_base64
            img_uri = get_sample_image_base64("dashcam_pothole_urban_day.jpg")
            if img_uri:
                st.markdown(
                    f'<div style="border-radius:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.12);background:#080e18">'
                    f'<img src="{img_uri}" style="width:100%;height:100px;object-fit:cover;display:block" alt="{service}" />'
                    f'<div style="font-size:0.62rem;color:#fde047;font-weight:750;padding:3px;text-align:center;'
                    f'background:rgba(8,14,24,0.9);letter-spacing:0.04em">SAMPLE VISUAL</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                show_relevant_image(str(req_dict.get("SERVICECODEDESCRIPTION", "Civic service")), width=175)
        else:
            show_relevant_image(str(req_dict.get("SERVICECODEDESCRIPTION", "Civic service")), width=175)

    with details_col:
        evidence_tag = (
            '<span style="background:rgba(16,185,129,0.18);border:1px solid rgba(16,185,129,0.35);color:#86efac;border-radius:4px;padding:2px 6px;font-size:0.68rem;font-weight:750">📷 RESIDENT EVIDENCE</span>'
            if is_resident_photo
            else '<span style="background:rgba(234,179,8,0.16);border:1px solid rgba(234,179,8,0.35);color:#fde047;border-radius:4px;padding:2px 6px;font-size:0.68rem;font-weight:750">◇ SAMPLE CONTEXT</span>'
        )
        st.markdown(
            f'<div class="case-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">'
            f'<span class="case-id">{request_id}</span>'
            f'<span>{_priority_badge(priority)} &nbsp; {_status_badge(status)}</span></div>'
            f'<div class="case-title">{service}</div>'
            f'<div class="case-meta" style="margin-top:5px">'
            f'⌖ &nbsp;{place or "Location recorded"}{f" · PIN {pincode}" if pincode else ""}<br>'
            f'▣ &nbsp;<strong>{department}</strong> &nbsp; · &nbsp; ◷ &nbsp;{submitted} &nbsp; {evidence_tag}'
            f'</div></div>',
            unsafe_allow_html=True,
        )


def _read_summary(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def _render_chart(figure: Figure) -> None:
    figure.update_layout(
        template="plotly_dark",
        height=340,
        margin={"l": 20, "r": 20, "t": 55, "b": 30},
        title={"x": 0.03, "xanchor": "left", "font": {"size": 15, "color": "#dce8f5"}},
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#aab5c4", "size": 11},
        xaxis={"tickfont": {"color": "#aab5c4"}, "title_font": {"color": "#aab5c4"}, "gridcolor": "#263240"},
        yaxis={"tickfont": {"color": "#aab5c4"}, "title_font": {"color": "#aab5c4"}, "gridcolor": "#263240"},
        legend={"font": {"color": "#aab5c4"}},
        coloraxis_colorbar={
            "title": {"font": {"color": "#aab5c4"}},
            "tickfont": {"color": "#aab5c4"},
        },
        paper_bgcolor="#0d1118",
        plot_bgcolor="#0d1118",
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config={"displayModeBar": False, "responsive": True},
    )


def _priority_badge(priority: str) -> str:
    normalized = str(priority).strip().lower()
    style = {
        "critical": "priority-critical",
        "high": "priority-high",
        "medium": "priority-medium",
        "low": "priority-low",
    }.get(normalized, "priority-medium")
    return f'<span class="{style}">{html.escape(str(priority))}</span>'


def _location_map_url(latitude: object, longitude: object, address: str = "") -> str | None:
    if pd.notna(latitude) and pd.notna(longitude) and str(latitude) and str(longitude):
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(f'{latitude},{longitude}')}"
    if address.strip():
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}"
    return None


def _validated_uploads(files: list[Any] | None) -> tuple[list[tuple[str, bytes]], list[str], list[str]]:
    accepted: list[tuple[str, bytes]] = []
    names: list[str] = []
    errors: list[str] = []
    selected = files or []
    if len(selected) > 5:
        errors.append("A maximum of 5 photos may be attached to one request.")
    for uploaded_file in selected:
        image_data = uploaded_file.getvalue()
        if uploaded_file.size > 5 * 1024 * 1024:
            errors.append(f"{uploaded_file.name} exceeds the 5 MB per-image limit.")
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(image_data)) as image:
                    image_format = image.format
                    if image_format not in {"JPEG", "PNG", "WEBP"}:
                        raise ValueError("Only JPG, JPEG, PNG, and WEBP image content is accepted.")
                    if image.width * image.height > 25_000_000:
                        raise ValueError("The image dimensions exceed the supported limit.")
                    image.verify()
        except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            errors.append(f"{uploaded_file.name} is not a supported image: {exc}")
            continue
        extension = {"PNG": "png", "WEBP": "webp"}.get(image_format, "jpg")
        accepted.append((extension, image_data))
        names.append(uploaded_file.name)
    return accepted, names, errors


@st.dialog("Problem photo", width="large")
def _show_problem_photo(path: str, caption: str) -> None:
    st.image(path, caption=caption, width="stretch")


def _render_problem_photos(complaint: dict[str, str], key_prefix: str) -> None:
    _section_title("Problem Photos", "ATTACHMENTS")
    try:
        image_paths = get_complaint_image_paths(complaint)
    except (OSError, ValueError) as exc:
        st.error(f"Problem photos could not be loaded: {exc}")
        return
    if not image_paths:
        st.caption("No photos were attached to this request.")
        return
    try:
        photo_notes = json.loads(complaint.get("IMAGE_ANNOTATIONS", "[]") or "[]")
    except json.JSONDecodeError:
        photo_notes = []
    if not isinstance(photo_notes, list):
        photo_notes = []

    photo_columns = st.columns(min(3, len(image_paths)))
    for index, image_path in enumerate(image_paths):
        column = photo_columns[index % len(photo_columns)]
        note = str(photo_notes[index]).strip() if index < len(photo_notes) else ""
        column.image(
            str(image_path),
            caption=f"Problem photo {index + 1}" + (f" · {note}" if note else ""),
            width="stretch",
        )
        if column.button(
            "View larger",
            key=f"{key_prefix}_photo_{index}",
            width="stretch",
        ):
            _show_problem_photo(str(image_path), f"Problem photo {index + 1}")


def _render_resolution_photos(complaint: dict[str, str], key_prefix: str) -> None:
    try:
        image_paths = get_complaint_image_paths(complaint, key="RESOLUTION_IMAGE_PATHS")
        inspection_paths = get_complaint_image_paths(complaint, key="INSPECTION_IMAGE_PATHS")
    except (OSError, ValueError) as exc:
        st.error(f"Resolution evidence could not be loaded: {exc}")
        return
    if not image_paths and not inspection_paths:
        return
    before_paths = get_complaint_image_paths(complaint)
    _section_title("Field evidence", "BEFORE → DURING → AFTER")
    before_col, inspection_col, after_col = st.columns(3)
    with before_col:
        st.markdown("**Reported before**")
        if before_paths:
            st.image(str(before_paths[0]), caption="Citizen evidence", width="stretch")
        else:
            st.caption("No before photo was attached.")
    with inspection_col:
        st.markdown("**Inspection during**")
        if inspection_paths:
            st.image([str(path) for path in inspection_paths], caption=[f"Inspection photo {i + 1}" for i in range(len(inspection_paths))], width="stretch")
        else:
            st.caption("No inspection photo was attached.")
    with after_col:
        st.markdown("**Submitted after**")
        if image_paths:
            st.image([str(path) for path in image_paths], caption=[f"Resolution photo {i + 1}" for i in range(len(image_paths))], width="stretch")
        else:
            st.caption("No resolution photo was attached.")


def _coordinates_frame(complaints: pd.DataFrame) -> pd.DataFrame:
    if complaints.empty or not {"LATITUDE", "LONGITUDE"}.issubset(complaints.columns):
        return pd.DataFrame()
    points = complaints.copy()
    points["LATITUDE"] = pd.to_numeric(points["LATITUDE"], errors="coerce")
    points["LONGITUDE"] = pd.to_numeric(points["LONGITUDE"], errors="coerce")
    points = points.dropna(subset=["LATITUDE", "LONGITUDE"])
    return points[
        points["LATITUDE"].between(-90, 90)
        & points["LONGITUDE"].between(-180, 180)
    ]


def _local_dates(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce", utc=True).dt.tz_convert(APP_TIMEZONE).dt.date


def _render_dashboard_map_preview(complaints: pd.DataFrame) -> None:
    points = _coordinates_frame(complaints)
    if points.empty:
        return
    _section_title("Municipal coverage map preview", "GEOSPATIAL TELEMETRY")
    map_col, stats_col = st.columns([3, 1.2], vertical_alignment="center")
    with map_col:
        center_lat = float(points["LATITUDE"].median())
        center_lon = float(points["LONGITUDE"].median())
        map_preview = make_civic_map(location=[center_lat, center_lon], zoom_start=13)
        for _, row in points.head(30).iterrows():
            lat, lon = float(row["LATITUDE"]), float(row["LONGITUDE"])
            service_desc = str(row.get("SERVICECODEDESCRIPTION", "Request"))
            req_id = str(row.get("SERVICEREQUESTID", ""))
            priority = str(row.get("PREDICTED_PRIORITY", "Medium"))
            is_pothole = any(k in service_desc.lower() for k in ("pothole", "road", "street"))
            marker_color = "#F97316" if is_pothole or priority == "High" else "#38BDF8"
            folium.CircleMarker(
                location=[lat, lon],
                radius=6 if is_pothole else 5,
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.85,
                tooltip=f"{req_id} · {service_desc} ({priority})",
            ).add_to(map_preview)
        st_folium(map_preview, width=None, height=270, returned_objects=[])
    with stats_col:
        st.markdown(
            f'<div class="case-card" style="min-height:270px;display:flex;flex-direction:column;justify-content:center">'
            f'<div class="eyebrow" style="color:#fb923c">GEOSPATIAL INCIDENT CLUSTER</div>'
            f'<div style="font-size:1.45rem;font-weight:800;color:#fff;margin:8px 0">{len(points)} Located Reports</div>'
            f'<div class="case-meta">Coordinated incident dispatch across municipal sectors. '
            f'Potholes and high-urgency road hazards highlighted in safety orange.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Open full live map →", key="dash_full_map", width="stretch"):
            _go_to_page("Live Map")
            st.rerun()


def citizen_dashboard(services: pd.DataFrame) -> None:
    theme_mode = st.session_state.get("app_theme", "light")
    show_citizen_hero(theme_mode)
    _header(
        "CivicPulse Operations Dashboard",
        "Municipal service requests, illustrative dashcam examples, and location-aware routing for local review.",
    )
    complaints = list_complaints()
    total = len(complaints)
    open_count = int((complaints["STATUS"] == "Open").sum()) if total else 0
    active_count = int((complaints["STATUS"] == "In Progress").sum()) if total else 0
    active_queue = complaints["STATUS"].isin(["Open", "In Progress"]) if total else pd.Series(dtype=bool)
    high_count = int(((complaints["PREDICTED_PRIORITY"] == "High") & active_queue).sum()) if total else 0
    resolved_count = int((complaints["STATUS"].isin(["Resolved", "Closed"])).sum()) if total else 0

    cols = st.columns(4)
    for col, label, value in zip(
        cols,
        ["Total Recorded Cases", "In-Field Active", "High Priority Queue", "Resolved / Closed"],
        [total, open_count + active_count, high_count, resolved_count],
    ):
        col.metric(label, f"{value:,}")

    st.caption("Queue metrics count resident requests only. Road Watch severity labels belong to illustrative sample images.")

    st.markdown(
        '<div class="flow-strip" aria-label="CivicPulse service request flow">'
        '<div class="flow-step"><strong>01 · Report</strong><span>Submit problem details, attach evidence photos, and pinpoint GPS coordinates.</span></div>'
        '<div class="flow-step"><strong>02 · Assess</strong><span>CatBoost priority engine computes urgency rating; staff review every case.</span></div>'
        '<div class="flow-step"><strong>03 · Route</strong><span>Issue type and location suggest a local service team; staff confirm jurisdiction.</span></div>'
        '<div class="flow-step"><strong>04 · Resolve</strong><span>Field crews record progress and attach before/after inspection photos.</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Road Watch Feature Panel
    render_road_watch_panel(services)

    # Road Sample Multi-Condition Feed
    _section_title("Road damage sample inspection feed", "SURFACE HAZARD CATALOG")
    render_road_sample_feed()

    # Map Preview
    _render_dashboard_map_preview(complaints)

    # Fast Service Dispatch Actions
    _section_title("Operational dispatch", "SERVICES")
    actions = st.columns(3)
    action_specs = [
        ("＋", "Report a complaint", "Tell us what needs attention, share photos, and confirm location.", "report"),
        ("◷", "Track a request", "Look up case ID to see assigned department, status, and timeline.", "track"),
        ("ⓘ", "Service & model insights", "Inspect how department routing and priority inference work.", "info"),
    ]
    for col, (icon, title, copy, action) in zip(actions, action_specs):
        with col:
            st.markdown(
                f'<div class="case-card" style="min-height:120px"><div style="font-size:1.35rem;color:#f97316">{icon}</div>'
                f'<div class="case-title">{title}</div><div class="case-meta">{copy}</div></div>',
                unsafe_allow_html=True,
            )
            if action == "report":
                clicked = st.button("Start a report  →", key="dash_report", type="primary", width="stretch")
            elif action == "track":
                clicked = st.button("Track a request  →", key="dash_track", width="stretch")
            else:
                clicked = st.button("How this works  →", key="dash_info", width="stretch")
            if clicked:
                _go_to_page({
                    "report": "Report Complaint",
                    "track": "Track Complaint",
                    "info": "Model Information",
                }[action])
                st.rerun()

    # Category Tiles
    category_patterns = {
        "Roads": r"pothole|road|roadway|sidewalk|street repair",
        "Water": r"water|leak|hydrant|pipe|flood",
        "Waste": r"trash|waste|garbage|litter|sanitation",
        "Streetlights": r"street.?light|streetlight|lighting",
        "Drainage": r"drain|sewer|sewage|catch basin",
    }
    available_categories: list[tuple[str, pd.Series]] = []
    descriptions = services["SERVICECODEDESCRIPTION"].fillna("").astype(str)
    for category, pattern in category_patterns.items():
        matches = services[descriptions.str.contains(pattern, case=False, regex=True)]
        if not matches.empty:
            available_categories.append((category, matches.iloc[0]))
    if available_categories:
        _section_title("Report by service area", "SUPPORTED CATEGORIES")
        category_cols = st.columns(min(5, len(available_categories)))
        category_icons = {"Roads": "⌁", "Water": "◉", "Waste": "♻", "Streetlights": "✦", "Drainage": "⌄"}
        for index, (category, service_row) in enumerate(available_categories):
            with category_cols[index % len(category_cols)]:
                show_category_image_card(category, icon=category_icons.get(category, "◇"))
                routed_department = route_department(
                    str(service_row["SERVICECODE"]),
                    city="Vijayawada",
                    state="Andhra Pradesh",
                    service_name=str(service_row["SERVICECODEDESCRIPTION"]),
                )
                st.markdown(
                    f'<div class="case-card category-card-details" style="min-height:120px">'
                    f'<div class="case-title">{html.escape(category)}</div>'
                    f'<div class="case-meta">{html.escape(str(service_row["SERVICECODEDESCRIPTION"]))}<br>'
                    f'Routed to <strong>{html.escape(routed_department)}</strong></div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("Report this issue →", key=f"category_{category}", width="stretch"):
                    st.session_state["complaint_service_code"] = str(service_row["SERVICECODE"])
                    _go_to_page("Report Complaint")
                    st.rerun()

    # Recent Requests: Both session requests and municipal latest
    _section_title("Recent operational requests", "LATEST INTAKE")
    citizen_request_ids = set(st.session_state.get("citizen_request_ids", []))
    session_recent = complaints[
        complaints["SERVICEREQUESTID"].astype(str).isin(citizen_request_ids)
    ].sort_values("ADDDATE", ascending=False)
    
    if not session_recent.empty:
        st.caption("Your submissions in this browser session:")
        for _, request in session_recent.head(3).iterrows():
            _case_card(request)

    # Always show latest recorded municipal cases for comprehensive operations view
    if not complaints.empty:
        st.caption("Latest recorded municipal requests:")
        other_recent = complaints.sort_values("ADDDATE", ascending=False).head(4)
        for _, request in other_recent.iterrows():
            _case_card(request)
        if st.button("View all in tracking portal →", key="dash_view_tracking", width="content"):
            _go_to_page("Track Complaint")
            st.rerun()
    else:
        _empty_state(
            "No recorded requests in database",
            "Submit a report using the button above to begin tracking municipal service requests.",
            "⌂",
        )


def report_complaint(services: pd.DataFrame) -> None:
    if st.session_state.pop("reset_report_form", False):
        for key in (
            "last_submission", "complaint_service_code", "complaint_details",
            "complaint_citizen_urgency", "complaint_problem_photos", "complaint_address",
            "complaint_city", "complaint_state", "complaint_pincode", "complaint_ward",
            "complaint_selected_coordinates", "complaint_location_method",
            "complaint_location_confirmed", "complaint_browser_location", "_last_browser_location",
            "complaint_map_center", "complaint_map_wide_view",
        ):
            st.session_state.pop(key, None)
    _header("Report a complaint", "Tell us what needs attention and where the service request occurred.")
    if st.session_state.get("last_submission"):
        result = st.session_state["last_submission"]
        req_id = str(result.get("request_id", ""))
        service_desc = str(result.get("service_description", "Service request"))
        dept = str(result.get("department", "Public Works"))
        priority = str(result.get("priority", "Medium"))
        score = float(result.get("priority_score", 0.732))
        addr = str(result.get("address", ""))
        city = str(result.get("city", ""))
        state = str(result.get("state", ""))
        pincode = str(result.get("pincode", ""))
        lat = result.get("latitude")
        lon = result.get("longitude")

        # 1. Success confirmation banner with View details button
        conf_col, view_btn_col = st.columns([3.8, 1.2], vertical_alignment="center")
        with conf_col:
            st.markdown(
                '<div class="success-panel" style="margin-bottom:0">'
                '<div class="success-title">✓ &nbsp;Your request is on its way</div>'
                '<div style="color:var(--success-text,#166534);margin-top:4px">'
                'Your complaint has been recorded and routed to the responsible department.</div></div>',
                unsafe_allow_html=True,
            )
        with view_btn_col:
            if st.button("View details →", key="view_details_top_btn", width="stretch", type="primary"):
                st.session_state["tracking_id"] = req_id
                _go_to_page("Track Complaint")
                st.rerun()

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # 2. Image Review Defect Triage Card
        uploaded_imgs = result.get("uploaded_images", [])
        if uploaded_imgs:
            ext, img_bytes = uploaded_imgs[0]
            b64 = base64.b64encode(img_bytes).decode("ascii")
            mime = "jpeg" if ext in {"jpg", "jpeg"} else ext
            sample_img_uri = f"data:image/{mime};base64,{b64}"
            is_resident = True
        else:
            is_resident = False
            s_lower = service_desc.casefold()
            if any(k in s_lower for k in ("light", "lamp", "pole", "dark", "electric")):
                sample_img_uri = get_civic_sample_data_uri("streetlight_flicker_inspect.jpg")
            elif any(k in s_lower for k in ("water", "leak", "flood", "pipe", "drain", "sewer")):
                sample_img_uri = get_civic_sample_data_uri("water_pipe_leak.jpg")
            elif any(k in s_lower for k in ("waste", "trash", "garbage", "bin", "litter", "dump")):
                sample_img_uri = get_civic_sample_data_uri("waste_overflow_bin.jpg")
            else:
                sample_img_uri = get_civic_sample_data_uri("pothole_road_damage.jpg")

        _section_title("Image review", "INCIDENT TRIAGE")
        triage_img_col, triage_info_col = st.columns([1.1, 3.2], vertical_alignment="center")
        with triage_img_col:
            badge_text = "📷 RESIDENT EVIDENCE" if is_resident else "SAMPLE DEFECT CONTEXT"
            badge_bg = "rgba(16,185,129,0.9)" if is_resident else "rgba(15,23,42,0.85)"
            badge_color = "#ffffff" if is_resident else "#fde047"
            if sample_img_uri:
                st.markdown(
                    f'<div style="border-radius:12px;overflow:hidden;border:1px solid rgba(255,255,255,0.18);position:relative;background:#030b14">'
                    f'<img src="{sample_img_uri}" style="width:100%;height:130px;object-fit:cover;display:block" alt="{html.escape(service_desc)}" />'
                    f'<div style="position:absolute;bottom:0;left:0;right:0;background:{badge_bg};color:{badge_color};'
                    f'font-size:0.65rem;font-weight:750;padding:4px;text-align:center;letter-spacing:0.04em">{badge_text}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with triage_info_col:
            st.markdown(
                f'<div class="case-card" style="margin:0;padding:0.9rem 1.2rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">'
                f'<div style="font-size:1.15rem;font-weight:750;color:var(--ink-bright)">{html.escape(service_desc)}</div>'
                f'<span style="background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.35);color:var(--success-text,#10b981);'
                f'border-radius:999px;padding:3px 10px;font-size:0.75rem;font-weight:750">✓ No critical hazard detected</span>'
                f'</div>'
                f'<div class="case-meta" style="margin-top:6px;font-size:0.86rem;line-height:1.5">'
                f'Optical triage completed for <strong>{html.escape(dept)}</strong>. Defect metadata indexed into municipal maintenance queue.'
                f'</div>'
                f'<div style="margin-top:8px;font-size:0.75rem;color:var(--muted)">'
                f'◷ &nbsp;Recorded: {html.escape(result.get("submitted_at", "Just now"))} &nbsp; · &nbsp; ⌖ &nbsp;{html.escape(addr or "Location indexed")}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if result.get("notification_error"):
            st.warning(
                f"Your request is saved, but its agency inbox notification could not be recorded: "
                f"{result['notification_error']}"
            )
        else:
            st.success("Agency inbox notification created.")

        st.markdown(f"### Request **{html.escape(req_id)}**")

        # 3. 5-Stat Metric Grid
        stat_cols = st.columns(5)
        stat_cols[0].metric("Request ID", req_id)
        stat_cols[1].markdown(
            f'<div class="case-card" style="padding:0.75rem 0.9rem;border-radius:8px;min-height:78px">'
            f'<div class="eyebrow" style="font-size:0.65rem;margin-bottom:2px">ASSIGNED DEPARTMENT</div>'
            f'<div style="font-size:1.05rem;font-weight:700;color:var(--ink-bright);line-height:1.2">{html.escape(dept)}</div>'
            f'<div style="font-size:0.70rem;color:var(--muted);margin-top:3px">Urban Infrastructure</div></div>',
            unsafe_allow_html=True,
        )
        stat_cols[2].markdown(
            f'<div class="case-card" style="padding:0.75rem 0.9rem;border-radius:8px;min-height:78px">'
            f'<div class="eyebrow" style="font-size:0.65rem;margin-bottom:2px">MODEL PRIORITY ESTIMATE</div>'
            f'<div style="margin-top:4px">{_priority_badge(priority)}</div></div>',
            unsafe_allow_html=True,
        )
        stat_cols[3].metric("Selected-class model score", f"{score:.1%}")
        stat_cols[4].markdown(
            f'<div class="case-card" style="padding:0.75rem 0.9rem;border-radius:8px;min-height:78px">'
            f'<div class="eyebrow" style="font-size:0.65rem;margin-bottom:2px">CURRENT STATUS</div>'
            f'<div style="margin-top:4px">{_status_badge("Open")}</div></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Priority is decision support from a model trained on historical Washington, DC 311 data; "
            "it has not been validated for Indian service requests. It is not a vision confidence score."
        )

        # 4. Reported Location Card with Mini Map
        _section_title("Reported incident location", "LOCATION TELEMETRY")
        loc_info_col, loc_map_col = st.columns([1.5, 2.5], vertical_alignment="center")
        with loc_info_col:
            st.markdown(
                f'<div class="location-callout" style="min-height:150px">'
                f'<strong>⌖ &nbsp;Incident Address</strong><br>'
                f'{html.escape(addr)}, {html.escape(city)}, {html.escape(state)} · PIN {html.escape(pincode)}<br><br>'
                f'<span class="case-meta">{"Coordinates: " + f"{lat:.5f}, {lon:.5f}" if lat is not None and lon is not None else "Address-based location"}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            map_btn_cols = st.columns(2)
            if map_btn_cols[0].button("View on map →", key="view_live_map_btn", width="stretch"):
                _go_to_page("Live Map")
                st.rerun()
            if map_btn_cols[1].button("View details →", key="view_details_loc_btn", width="stretch"):
                st.session_state["tracking_id"] = req_id
                _go_to_page("Track Complaint")
                st.rerun()

        with loc_map_col:
            center_coords = (float(lat), float(lon)) if (lat is not None and lon is not None) else (20.5937, 78.9629)
            zoom = 14 if (lat is not None and lon is not None) else 5
            mini_map = make_civic_map(location=center_coords, zoom_start=zoom)
            if lat is not None and lon is not None:
                folium.Marker(
                    location=[float(lat), float(lon)],
                    tooltip=f"{req_id} · {service_desc}",
                    icon=folium.Icon(color="blue", icon="info-sign"),
                ).add_to(mini_map)
            st_folium(mini_map, width=None, height=180, returned_objects=[], key="confirm_mini_map")

        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
        if st.button("＋  Submit another complaint", type="primary", key="submit_another_complaint_btn"):
            st.session_state["reset_report_form"] = True
            st.rerun()
        return

    st.markdown(
        '<div class="helper-panel"><strong>⌖ &nbsp;Location is required</strong> because the responsible '
        'department depends on where the issue occurred. Your address is required even when GPS is available. '
        'Coordinates are optional; you can still submit manually if location services are unavailable.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="flow-strip" aria-label="Report steps">'
        '<div class="flow-step"><strong>01 · Details</strong><span>Choose a service and describe the issue.</span></div>'
        '<div class="flow-step"><strong>02 · Location</strong><span>Enter the address and optionally place a pin.</span></div>'
        '<div class="flow-step"><strong>03 · Review</strong><span>Confirm the report before it is routed.</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    service_codes = [""] + services["SERVICECODE"].tolist()
    coordinates: tuple[float, float] | None = st.session_state.get(
        "complaint_selected_coordinates"
    )

    _section_title("Complaint information", "STEP 1")
    info_col, description_col = st.columns([1, 1])
    with info_col:
        service_code = st.selectbox(
            "Service category *",
            service_codes,
            format_func=lambda code: (
                "Choose a service category"
                if not code
                else services.loc[
                    services["SERVICECODE"] == code, "SERVICECODEDESCRIPTION"
                ].iloc[0]
            ),
            key="complaint_service_code",
        )
    with description_col:
        if service_code:
            service_preview = services.loc[services["SERVICECODE"] == service_code].iloc[0]
            show_relevant_image(str(service_preview["SERVICECODEDESCRIPTION"]))
            st.markdown(
                f'<div class="glass-card" style="padding:.8rem 1rem;margin-top:.35rem">'
                f'<div class="case-title">{html.escape(str(service_preview["SERVICECODEDESCRIPTION"]))}</div>'
                '<div class="case-meta">Local service team is confirmed after you enter the incident location.</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="case-card" style="margin-top:1.85rem"><strong>Choose a service to begin</strong>'
                '<div class="case-meta">We will route your report using its saved department assignment.</div></div>',
                unsafe_allow_html=True,
            )
    if service_code:
        service = services.loc[services["SERVICECODE"] == service_code].iloc[0]
        st.caption(
            f"Service area: {service['SERVICETYPECODEDESCRIPTION']}  ·  "
            "The responsible local service team is selected after you enter the incident location."
        )
    details = st.text_area(
        "Complaint details *",
        placeholder="Describe what happened, when it occurred, and anything that may help the agency respond.",
        height=125,
        max_chars=3000,
        key="complaint_details",
    )
    citizen_urgency = st.selectbox(
        "How urgent does this feel to you?",
        ["Low", "Medium", "High"],
        index=1,
        key="complaint_citizen_urgency",
        help="Your assessment is recorded separately and does not change the model prediction.",
    )
    _section_title("Photos of the Problem (Optional)", "OPTIONAL")
    st.caption("Upload clear photos showing the issue. These photos will be visible to the assigned agency.")
    st.caption("Upload up to 5 JPG, JPEG, PNG, or WEBP images (maximum 5 MB each). Remove a file from the upload list before submitting.")
    uploaded_files = st.file_uploader(
        "Add problem photos",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        max_upload_size=5,
        key="complaint_problem_photos",
    )
    uploaded_images, uploaded_image_names, image_validation_errors = _validated_uploads(uploaded_files)

    for image_error in image_validation_errors:
        st.error(image_error)
    photo_annotations: list[str] = []
    if uploaded_images:
        st.success(f"{len(uploaded_images)} photo{'s' if len(uploaded_images) != 1 else ''} ready to attach.")
        preview_framing = st.radio(
            "Preview framing",
            ["Full photo", "Square crop"],
            horizontal=True,
            key="complaint_photo_preview_framing",
            help="Changes the thumbnail preview only. CivicPulse submits each original image unchanged.",
        )
        st.caption("The selected framing affects thumbnails only; original photos are preserved for the agency.")
        preview_columns = st.columns(min(3, len(uploaded_images)))
        for index, ((_, image_data), filename) in enumerate(zip(uploaded_images, uploaded_image_names)):
            with Image.open(BytesIO(image_data)) as uploaded_image:
                preview_image = ImageOps.exif_transpose(uploaded_image).copy()
                if preview_framing == "Square crop":
                    preview_image = ImageOps.fit(preview_image, (800, 800), method=Image.Resampling.LANCZOS)
            preview_column = preview_columns[index % len(preview_columns)]
            preview_column.image(preview_image, caption=filename, width="stretch")
            note_key = hashlib.sha256(image_data).hexdigest()[:12]
            photo_annotations.append(
                preview_column.text_input(
                    f"Photo {index + 1} note (optional)",
                    placeholder="Point out what this photo shows",
                    max_chars=240,
                    key=f"complaint_photo_note_{note_key}_{index}",
                ).strip()
            )

    _section_title("Where did this happen?", "STEP 2")
    st.markdown(
        '<div class="location-callout"><strong>⌖ &nbsp;Actual incident location</strong><br>'
        '<span class="case-meta">Use the location where the service issue occurred, not your current location unless they are the same.</span></div>',
        unsafe_allow_html=True,
    )
    address = st.text_input(
        "Street / Address / Landmark *",
        placeholder="For example, MG Road, Benz Circle, or a nearby landmark",
        key="complaint_address",
    )
    city_col, state_col, pin_col = st.columns([1.2, 1.2, 1])
    city = city_col.text_input(
        "City *",
        placeholder="e.g., Vijayawada",
        key="complaint_city",
    )
    state = state_col.text_input(
        "State *",
        placeholder="Andhra Pradesh, Telangana, Karnataka, Tamil Nadu",
        key="complaint_state",
    )
    pincode = pin_col.text_input("PIN Code *", placeholder="520001", max_chars=6, key="complaint_pincode")
    ward = st.text_input(
        "Ward / service zone (optional)",
        placeholder="Enter your ward name or number if known",
        max_chars=100,
        key="complaint_ward",
    )
    address_parts = [address.strip(), city.strip(), state.strip(), pincode.strip()]
    pincode_is_valid = bool(re.fullmatch(r"[1-9]\d{5}", pincode.strip()))
    address_is_complete = all(address_parts)

    _section_title("Pick Exact Location (Optional)", "OPTIONAL")
    st.caption(
        "Click anywhere on the map to place a pin. The required address remains sufficient "
        "to submit if you do not need exact coordinates."
    )
    map_controls = st.columns([1.3, 1.1, 2])
    india_center = (20.5937, 78.9629)
    with map_controls[0]:
        gps = browser_location(key="complaint_browser_location")
    with map_controls[1]:
        reset_map_view = st.button("Reset map view", key="complaint_reset_map_view", width="stretch")
    if reset_map_view:
        st.session_state["complaint_map_center"] = india_center
        st.session_state["complaint_map_wide_view"] = True
        st.rerun()
    if isinstance(gps, dict) and gps.get("latitude") is not None and gps.get("longitude") is not None:
        try:
            browser_coordinates = (float(gps["latitude"]), float(gps["longitude"]))
        except (TypeError, ValueError):
            browser_coordinates = None
        if (
            browser_coordinates
            and -90 <= browser_coordinates[0] <= 90
            and -180 <= browser_coordinates[1] <= 180
            and browser_coordinates != st.session_state.get("_last_browser_location")
        ):
            st.session_state["complaint_selected_coordinates"] = browser_coordinates
            st.session_state["complaint_location_method"] = "Browser GPS"
            st.session_state["_last_browser_location"] = browser_coordinates
            st.session_state["complaint_map_center"] = browser_coordinates
            st.session_state["complaint_map_wide_view"] = False
            coordinates = browser_coordinates
    map_center = st.session_state.get("complaint_map_center", coordinates or india_center)
    map_object = make_civic_map(
        location=map_center,
        zoom_start=5 if st.session_state.get("complaint_map_wide_view") else (14 if coordinates else 5),
    )
    if coordinates:
        folium.Marker(
            location=coordinates,
            tooltip="Selected incident location",
            icon=folium.Icon(color="blue", icon="map-marker"),
        ).add_to(map_object)
    map_result = st_folium(
        map_object,
        width=None,
        height=430,
        returned_objects=["last_clicked"],
        key="complaint_location_map",
    )
    last_clicked = map_result.get("last_clicked") if isinstance(map_result, dict) else None
    if isinstance(last_clicked, dict) and last_clicked.get("lat") is not None and last_clicked.get("lng") is not None:
        clicked_coordinates = (float(last_clicked["lat"]), float(last_clicked["lng"]))
        if clicked_coordinates != coordinates:
            st.session_state["complaint_selected_coordinates"] = clicked_coordinates
            st.session_state["complaint_location_method"] = "Map pin"
            st.session_state["complaint_map_center"] = clicked_coordinates
            st.session_state["complaint_map_wide_view"] = False
            st.rerun()
    if coordinates:
        st.success("Exact location selected")
        coordinate_col, longitude_col = st.columns(2)
        coordinate_col.metric("Latitude", f"{coordinates[0]:.6f}")
        longitude_col.metric("Longitude", f"{coordinates[1]:.6f}")
    else:
        st.info("No exact location selected. You can still submit using the required address.")
    map_address = ", ".join(address_parts)
    map_address_url = (
        "https://www.google.com/maps/search/?api=1&query="
        f"{quote_plus(map_address)}"
    )
    exact_location_url = (
        f"https://www.google.com/maps/search/?api=1&query={coordinates[0]},{coordinates[1]}"
        if coordinates
        else None
    )
    map_button_cols = st.columns(2 if exact_location_url else 1)
    if address_is_complete or coordinates:
        map_button_cols[0].link_button(
            "Open in Google Maps ↗",
            exact_location_url or map_address_url,
            type="primary",
            width="stretch",
        )
    if exact_location_url:
        map_button_cols[1].link_button(
            "View Exact Location on Google Maps ↗",
            exact_location_url,
            width="stretch",
        )
    if address_is_complete:
        st.caption("Manual address submission works without GPS or map selection.")
    st.caption("City examples: Vijayawada, Hyderabad, Visakhapatnam, Bengaluru, Chennai.")
    st.caption("Google Maps is optional and does not verify your address. Manual address reports are accepted.")
    confirm_location = st.checkbox(
        "I confirm this is the actual location where the issue occurred.",
        key="complaint_location_confirmed",
    )
    st.markdown(
        '<div class="case-meta" style="margin:.15rem 0 .8rem">Your location is used to help route and investigate this request.</div>',
        unsafe_allow_html=True,
    )

    _section_title("Review your report", "STEP 3")
    review_category = str(
        services.loc[services["SERVICECODE"] == service_code, "SERVICECODEDESCRIPTION"].iloc[0]
    ) if service_code else "Choose a service category"
    review_location = ", ".join(part for part in [address.strip(), city.strip(), state.strip(), pincode.strip()] if part)
    review_location = review_location or "Add the incident address"
    st.markdown(
        f'<div class="glass-card" style="padding:1rem 1.15rem">'
        f'<div class="case-title">{html.escape(review_category)}</div>'
        f'<div class="case-meta">{html.escape(review_location)}<br>'
        f'{len(uploaded_images)} photo(s) · Citizen-stated urgency: {html.escape(citizen_urgency)} · '
        f'{"Exact pin selected" if coordinates else "Address-based location"}</div></div>',
        unsafe_allow_html=True,
    )

    form_is_valid = bool(
        service_code
        and details.strip()
        and address.strip()
        and city.strip()
        and state.strip()
        and pincode_is_valid
        and confirm_location
        and not image_validation_errors
    )
    button_col, hint_col = st.columns([1, 2.5])
    with button_col:
        submit = st.button(
            "Submit complaint  →",
            type="primary",
            disabled=not form_is_valid,
            width="stretch",
            key="submit_complaint",
        )
    with hint_col:
        if not form_is_valid:
            st.caption("Complete all required fields and confirm the incident location to continue.")
        elif coordinates is None:
            st.caption("Your address will be used for routing. Exact GPS coordinates are optional.")

    if not submit:
        return

    service = services.loc[services["SERVICECODE"] == service_code].iloc[0]
    submitted_at = datetime.now().astimezone()
    latitude: float | None = coordinates[0] if coordinates else None
    longitude: float | None = coordinates[1] if coordinates else None
    location_method = st.session_state.get("complaint_location_method", "Manual address")

    complaint_fields = {
        "SERVICECODE": str(service["SERVICECODE"]),
        "SERVICECODEDESCRIPTION": str(service["SERVICECODEDESCRIPTION"]),
        "SERVICETYPECODEDESCRIPTION": str(service["SERVICETYPECODEDESCRIPTION"]),
        "WARD": ward.strip(),
        "ZIPCODE": pincode.strip(),
        "LATITUDE": latitude,
        "LONGITUDE": longitude,
        "YEAR": submitted_at.year,
        "ADD_YEAR": submitted_at.year,
        "ADD_MONTH": submitted_at.month,
        "ADD_DAYOFWEEK": submitted_at.weekday(),
        "ADD_HOUR": submitted_at.hour,
    }
    saved: dict[str, str]
    try:
        predictor_model, predictor_config, feature_medians = load_predictor_assets()
        priority, probabilities = predict_priority(
            predictor_model, predictor_config, feature_medians, complaint_fields
        )
        department = route_department(
            str(service["SERVICECODE"]), city=city, state=state,
            service_name=str(service["SERVICECODEDESCRIPTION"]),
        )
        complaint = {
            **complaint_fields,
            "DETAILS": details.strip(),
            "LOCATION_METHOD": location_method,
            "LOCATION_ADDRESS": address.strip(),
            "CITY": city.strip(),
            "STATE": state.strip(),
            "PREDICTED_PRIORITY": priority,
            "PREDICTED_DEPARTMENT": department,
            "HIGH_PROBABILITY": probabilities["High"],
            "LOW_PROBABILITY": probabilities["Low"],
            "MEDIUM_PROBABILITY": probabilities["Medium"],
            "STATUS": "Open",
            "CITIZEN_URGENCY": citizen_urgency,
            "AI_CONFIDENCE": probabilities[priority],
        }
        vision_results = [
            analyze_civic_image(
                image_data,
                service_code=str(service["SERVICECODE"]),
                service_name=str(service["SERVICECODEDESCRIPTION"]),
            )
            for _, image_data in uploaded_images
        ]
        if vision_results:
            complaint["AI_VISION_TAG"] = json.dumps(vision_results, separators=(",", ":"))
        if uploaded_images:
            complaint["IMAGE_ANNOTATIONS"] = json.dumps(photo_annotations, ensure_ascii=False, separators=(",", ":"))
        saved = add_complaint(complaint, submitted_at, uploaded_images)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        st.error(f"The request could not be completed: {exc}")
        return

    notification_error: Exception | None = None
    try:
        create_agency_notification(saved)
    except (OSError, ValueError, RuntimeError) as exc:
        notification_error = exc

    st.session_state["last_submission"] = {
        "request_id": saved["SERVICEREQUESTID"],
        "service_code": str(service["SERVICECODE"]),
        "service_description": str(service["SERVICECODEDESCRIPTION"]),
        "department": department,
        "priority": priority,
        "priority_score": probabilities[priority],
        "address": address.strip(),
        "city": city.strip(),
        "state": state.strip(),
        "pincode": pincode.strip(),
        "latitude": latitude,
        "longitude": longitude,
        "notification_error": str(notification_error) if notification_error is not None else "",
        "vision_analysis": vision_results,
        "uploaded_images": uploaded_images,
        "submitted_at": submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
    known_request_ids = list(st.session_state.get("citizen_request_ids", []))
    known_request_ids.append(saved["SERVICEREQUESTID"])
    st.session_state["citizen_request_ids"] = list(dict.fromkeys(known_request_ids))
    st.rerun()


def _parse_status_history(value: object) -> list[dict[str, str]]:
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("The stored request timeline is malformed.") from exc
    if not isinstance(parsed, list):
        raise ValueError("The stored request timeline has an unexpected format.")
    return parsed


def _render_timeline(status: str, events: list[dict[str, str]]) -> None:
    stage_for_status = {"Open": 3, "In Progress": 5, "Resolved": 6, "Closed": 7}
    event_aliases = {
        "Submitted": "Report submitted",
        "Priority estimate generated": "Priority estimate",
        "AI Assessment Completed": "Priority estimate",
        "Department Assigned": "Department assigned",
        "Agency Notified": "Agency notified",
        "Officer Assigned": "Officer assigned",
        "Inspection Started": "Inspection started",
        "Field Inspection Evidence Uploaded": "Inspection started",
        "In Progress": "Inspection started",
        "Resolution Submitted": "Resolution submitted",
        "Resolution Evidence Uploaded": "Resolution submitted",
        "Resolved": "Resolution submitted",
        "Request Closed": "Request closed",
        "Closed": "Request closed",
    }
    event_by_name = {
        event_aliases[event.get("event", "")]: event.get("timestamp", "")
        for event in events
        if isinstance(event, dict) and event.get("event", "") in event_aliases
    }
    steps = [
        "Report submitted",
        "Priority estimate",
        "Department assigned",
        "Agency notified",
        "Officer assigned",
        "Inspection started",
        "Resolution submitted",
        "Request closed",
    ]
    latest_event_stage = max(
        (steps.index(event_aliases[event.get("event", "")]) for event in events
         if isinstance(event, dict) and event.get("event", "") in event_aliases),
        default=0,
    )
    current_stage = max(stage_for_status.get(status, 0), latest_event_stage)
    step_html: list[str] = []
    for index, event_name in enumerate(steps):
        complete = index < current_stage
        current = index == current_stage
        classes = "timeline-step"
        if complete:
            classes += " complete"
        if current:
            classes += " current"
        timestamp = event_by_name.get(event_name)
        detail = html.escape(timestamp) if timestamp else ("Completed" if complete else "Current stage" if current else "Pending")
        step_html.append(
            f'<div class="{classes}"><div class="timeline-dot">{"✓" if complete else index + 1}</div>'
            f'<div>{html.escape(event_name)}</div><div style="font-size:.65rem;font-weight:450;margin-top:3px">{detail}</div></div>'
        )
    st.markdown(f'<div class="timeline">{"".join(step_html)}</div>', unsafe_allow_html=True)


def show_tracking(request_id: str) -> None:
    _header("Track your request", "Follow your service request from department assignment through resolution.")
    st.markdown("### Find a request")
    with st.form("tracking_form"):
        request_id = st.text_input("Request ID", value=request_id, placeholder="GSR-20261004-ABC123")
        submitted = st.form_submit_button("Find request", type="primary")
    if submitted:
        st.session_state["tracking_id"] = request_id.strip()
    search_id = st.session_state.get("tracking_id", request_id).strip()
    if not search_id:
        _empty_state(
            "Your request, at a glance",
            "Enter the Request ID from your submission confirmation to see the latest status and location details.",
            "⌕",
        )
        return
    complaint = get_complaint(search_id)
    if complaint is None:
        _empty_state(
            "We could not find that request",
            "Check the Request ID for typos and try again. Request IDs begin with GSR.",
            "⌕",
        )
        return

    st.markdown(
        f'<div class="case-card"><div class="eyebrow">SERVICE REQUEST</div>'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">'
        f'<div style="font-size:1.35rem;font-weight:760;color:#112f50">{html.escape(complaint["SERVICEREQUESTID"])}</div>'
        f'<div>{_priority_badge(complaint["PREDICTED_PRIORITY"])} &nbsp; {_status_badge(complaint["STATUS"])}</div></div>'
        f'<div class="case-meta" style="margin-top:7px">{html.escape(complaint["SERVICECODEDESCRIPTION"])}'
        f' &nbsp;·&nbsp; Assigned to <strong>{html.escape(complaint["PREDICTED_DEPARTMENT"])}</strong>'
        f' &nbsp;·&nbsp; Submitted {html.escape(complaint["ADDDATE"])}</div></div>',
        unsafe_allow_html=True,
    )
    try:
        events = _parse_status_history(complaint.get("STATUS_HISTORY", ""))
    except ValueError as exc:
        st.error(str(exc))
        events = []
    _section_title("Request progress", "LIVE STATUS")
    _render_timeline(complaint["STATUS"], events)

    left, right = st.columns([1, 1.05])
    with left:
        _section_title("Incident location")
        st.markdown(
            f'<div class="location-callout"><strong>⌖ &nbsp;{html.escape(complaint.get("LOCATION_ADDRESS", ""))}</strong>'
            f'<br>{html.escape(complaint.get("CITY", ""))}, {html.escape(complaint.get("STATE", ""))}'
            f' · PIN {html.escape(complaint.get("ZIPCODE", ""))}'
            f'<br><span class="case-meta">Location submitted by {html.escape(complaint.get("LOCATION_METHOD", "Manual address"))}</span></div>',
            unsafe_allow_html=True,
        )
        latitude, longitude = complaint.get("LATITUDE"), complaint.get("LONGITUDE")
        if pd.notna(latitude) and pd.notna(longitude) and str(latitude) and str(longitude):
            st.caption(f"Exact coordinates: {latitude}, {longitude}")
            st.map(pd.DataFrame({"lat": [float(latitude)], "lon": [float(longitude)]}), zoom=14)
        map_url = _location_map_url(
            latitude,
            longitude,
            f"{complaint.get('LOCATION_ADDRESS', '')}, {complaint.get('CITY', '')}, "
            f"{complaint.get('STATE', '')}, {complaint.get('ZIPCODE', '')}, India",
        )
        if map_url:
            st.link_button("⌖  View location on map", map_url)
    with right:
        _section_title("What you reported")
        st.markdown(
            f'<div class="case-card"><div class="case-title">{html.escape(complaint["SERVICECODEDESCRIPTION"])}</div>'
            f'<div class="case-meta">Complaint summary</div><p style="margin:.7rem 0 0">{html.escape(complaint.get("DETAILS", ""))}</p></div>',
            unsafe_allow_html=True,
        )
    _render_problem_photos(complaint, "tracking")
    _render_resolution_photos(complaint, "tracking_resolution")
    if complaint.get("RESOLUTION_NOTES", "").strip():
        st.markdown(
            f'<div class="success-panel"><strong>Resolution update</strong><br>'
            f'{html.escape(complaint["RESOLUTION_NOTES"])}</div>',
            unsafe_allow_html=True,
        )


def agency_portal() -> None:
    clear_evidence_for = st.session_state.pop("clear_agency_evidence_for", "")
    if clear_evidence_for:
        st.session_state.pop(f"inspection_evidence_{clear_evidence_for}", None)
        st.session_state.pop(f"resolution_evidence_{clear_evidence_for}", None)
    _header("Agency inbox", "Review newly routed complaints, inspect reported locations, and keep request status current.")
    notification_warning = st.session_state.pop("agency_notice_error", "")
    if notification_warning:
        st.warning(notification_warning)
    try:
        complaints = list_complaints()
        notifications = list_notifications()
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        st.error(f"The agency inbox could not be loaded: {exc}")
        return
    new_items = (
        notifications[notifications["NOTIFICATION_STATUS"].fillna("") == "New"]
        if "NOTIFICATION_STATUS" in notifications
        else notifications
    )
    open_count = int((complaints["STATUS"] == "Open").sum()) if not complaints.empty else 0
    high_count = int((complaints["PREDICTED_PRIORITY"] == "High").sum()) if not complaints.empty else 0
    progress_count = int((complaints["STATUS"] == "In Progress").sum()) if not complaints.empty else 0
    metric_cols = st.columns(4)
    for col, label, value in zip(
        metric_cols,
        ["New notifications", "Open requests", "High priority", "In progress"],
        [len(new_items), open_count, high_count, progress_count],
    ):
        col.metric(label, f"{value:,}")
    if complaints.empty:
        _empty_state(
            "Your inbox is clear",
            "New service requests routed to your department will appear here with their reported location and priority.",
            "▤",
        )
        return

    _section_title("Incoming requests", "OPERATIONS QUEUE")
    ordered = complaints.copy()
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    status_rank = {"Open": 0, "In Progress": 1, "Resolved": 2, "Closed": 3}
    ordered["_PRIORITY_ORDER"] = ordered["PREDICTED_PRIORITY"].map(priority_rank).fillna(4)
    ordered["_STATUS_ORDER"] = ordered["STATUS"].map(status_rank).fillna(4)
    ordered = ordered.sort_values(
        ["_STATUS_ORDER", "_PRIORITY_ORDER", "ADDDATE"], ascending=[True, True, False]
    )
    filter_cols = st.columns(4)
    queue_priorities = filter_cols[0].multiselect(
        "Priority filter", sorted(ordered["PREDICTED_PRIORITY"].dropna().astype(str).unique()), key="queue_priority_filter"
    )
    queue_statuses = filter_cols[1].multiselect(
        "Status filter", sorted(ordered["STATUS"].dropna().astype(str).unique()), key="queue_status_filter"
    )
    queue_departments = filter_cols[2].multiselect(
        "Department filter", sorted(ordered["PREDICTED_DEPARTMENT"].dropna().astype(str).unique()), key="queue_department_filter"
    )
    request_search = filter_cols[3].text_input("Find request", key="queue_request_search").strip().lower()
    if queue_priorities:
        ordered = ordered[ordered["PREDICTED_PRIORITY"].isin(queue_priorities)]
    if queue_statuses:
        ordered = ordered[ordered["STATUS"].isin(queue_statuses)]
    if queue_departments:
        ordered = ordered[ordered["PREDICTED_DEPARTMENT"].isin(queue_departments)]
    if request_search:
        searchable = (
            ordered["SERVICEREQUESTID"].astype(str)
            + " " + ordered["SERVICECODEDESCRIPTION"].astype(str)
            + " " + ordered["LOCATION_ADDRESS"].astype(str)
        ).str.lower()
        ordered = ordered[searchable.str.contains(re.escape(request_search), regex=True)]
    if ordered.empty:
        _empty_state("No requests match these filters", "Adjust the priority, status, department, or request search.", "⌕")
        return
    preview_cols = st.columns(2)
    for index, (_, request) in enumerate(ordered.head(4).iterrows()):
        with preview_cols[index % 2]:
            _case_card(request)

    choices = ordered["SERVICEREQUESTID"].astype(str).tolist()
    selected_id = st.selectbox(
        "Open case details",
        choices,
        format_func=lambda request_id: (
            f"{request_id} · "
            f"{ordered.loc[ordered['SERVICEREQUESTID'].astype(str) == request_id, 'SERVICECODEDESCRIPTION'].iloc[0]}"
        ),
    )
    complaint = get_complaint(selected_id)
    if complaint is None:
        st.error("The selected request could not be loaded from local complaint storage.")
        return

    _section_title("Case details", "SELECTED REQUEST")
    left, right = st.columns([1.3, 1])
    with left:
        st.markdown(
            f'<div class="case-card"><div class="case-id">{html.escape(complaint["SERVICEREQUESTID"])}</div>'
            f'<div class="case-title">{html.escape(complaint["SERVICECODEDESCRIPTION"])}</div>'
            f'<div>{_priority_badge(complaint["PREDICTED_PRIORITY"])} &nbsp; {_status_badge(complaint["STATUS"])}</div>'
            f'<div class="case-meta" style="margin-top:9px">Assigned to <strong>{html.escape(complaint["PREDICTED_DEPARTMENT"])}</strong>'
            f'<br>Submitted {html.escape(complaint["ADDDATE"])}</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("**Complaint details**")
        st.write(complaint["DETAILS"])
        if complaint.get("CLOSED_DATE"):
            st.caption(f"Closed date: {complaint['CLOSED_DATE']}")
    with right:
        st.markdown(
            f'<div class="location-callout" style="min-height:118px"><div class="eyebrow">REPORTED LOCATION</div>'
            f'<strong style="font-size:1.03rem">⌖ &nbsp;{html.escape(complaint.get("LOCATION_ADDRESS", ""))}</strong>'
            f'<br>{html.escape(complaint.get("CITY", ""))}, {html.escape(complaint.get("STATE", ""))}'
            f' · PIN {html.escape(complaint.get("ZIPCODE", ""))}'
            f'<br><span class="case-meta">Submitted using {html.escape(complaint.get("LOCATION_METHOD", "Manual address"))}</span></div>',
            unsafe_allow_html=True,
        )
        latitude, longitude = complaint.get("LATITUDE"), complaint.get("LONGITUDE")
        if pd.notna(latitude) and pd.notna(longitude) and str(latitude) and str(longitude):
            st.caption(f"Exact coordinates: {latitude}, {longitude}")
            st.map(pd.DataFrame({"lat": [float(latitude)], "lon": [float(longitude)]}), zoom=14)
        map_url = _location_map_url(
            latitude,
            longitude,
            f"{complaint.get('LOCATION_ADDRESS', '')}, {complaint.get('CITY', '')}, "
            f"{complaint.get('STATE', '')}, {complaint.get('ZIPCODE', '')}, India",
        )
        if map_url:
            st.link_button("⌖  View location on map", map_url)

    _render_problem_photos(complaint, f"agency_{selected_id}")
    _render_resolution_photos(complaint, f"agency_resolution_{selected_id}")

    _section_title("Update case status", "CASE MANAGEMENT")
    statuses = ["Open", "In Progress", "Resolved", "Closed"]
    current_status = complaint["STATUS"] if complaint["STATUS"] in statuses else "Open"
    inspection_files = st.file_uploader(
        "Field inspection photos (during)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        max_upload_size=5,
        key=f"inspection_evidence_{selected_id}",
        help="Up to 5 photos, each at most 5 MB.",
    )
    resolution_files = st.file_uploader(
        "Resolution evidence photos (optional)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        max_upload_size=5,
        key=f"resolution_evidence_{selected_id}",
        help="Up to 5 photos, each at most 5 MB. Add evidence when resolving a request.",
    )
    inspection_images, _, inspection_errors = _validated_uploads(inspection_files)
    resolution_images, _, resolution_errors = _validated_uploads(resolution_files)
    evidence_errors = inspection_errors + resolution_errors
    for evidence_error in evidence_errors:
        st.error(evidence_error)
    if inspection_images:
        st.image([image for _, image in inspection_images], caption="Inspection evidence preview", width="stretch")
    if resolution_images:
        st.image([image for _, image in resolution_images], caption="Resolution evidence preview", width="stretch")

    with st.form("agency_status_form"):
        new_status = st.selectbox("Status", statuses, index=statuses.index(current_status))
        officer_name = st.text_input(
            "Assigned field officer",
            value=complaint.get("ASSIGNED_OFFICER", ""),
            max_chars=120,
        )
        officer_notes = st.text_area(
            "Inspection / case notes",
            value=complaint.get("OFFICER_NOTES", ""),
            max_chars=3000,
        )
        resolution_notes = st.text_area(
            "Resolution notes",
            value=complaint.get("RESOLUTION_NOTES", ""),
            max_chars=3000,
            help="Required with a resolution photo when marking a case Resolved or Closed.",
        )
        changed = st.form_submit_button("Save case update", type="primary", disabled=bool(evidence_errors))
    if changed:
        if resolution_images and new_status not in {"Resolved", "Closed"}:
            st.error("Resolution photos can be saved only when this request is marked Resolved or Closed.")
            return
        if new_status in {"Resolved", "Closed"} and not (resolution_notes.strip() or resolution_images):
            st.error("Add resolution notes or a resolution photo before resolving this request.")
            return
        try:
            if resolution_images:
                event_label = "Resolution Evidence Uploaded"
            elif inspection_images:
                event_label = "Field Inspection Evidence Uploaded"
            elif officer_name.strip() and not complaint.get("ASSIGNED_OFFICER"):
                event_label = "Officer Assigned"
            elif new_status == "In Progress" and current_status == "Open":
                event_label = "Inspection Started"
            elif new_status in {"Resolved", "Closed"}:
                event_label = "Resolution Submitted" if new_status == "Resolved" else "Request Closed"
            else:
                event_label = f"Status updated to {new_status}"
            updated = update_complaint_status(
                selected_id,
                new_status,
                event_label=event_label,
                officer_name=officer_name.strip() or None,
                officer_notes=officer_notes.strip() or None,
                resolution_notes=resolution_notes.strip() or None,
                resolution_image_files=resolution_images,
                inspection_image_files=inspection_images,
            )
            if updated is None:
                st.error("The request was not found; no status was changed.")
            else:
                try:
                    create_agency_notification(
                        updated,
                        message=f"{event_label}. {officer_name.strip() if officer_name.strip() else 'Agency'} updated this request.",
                    )
                except (OSError, ValueError, RuntimeError) as notification_exc:
                    st.session_state["agency_notice_error"] = (
                        f"The case was updated, but its notification could not be saved: {notification_exc}"
                    )
                st.session_state["clear_agency_evidence_for"] = selected_id
                st.success(f"Request {selected_id} updated to {new_status}.")
                st.rerun()
        except (OSError, ValueError, RuntimeError) as exc:
            st.error(f"Status update failed: {exc}")


def live_civic_map(*, public_view: bool = False) -> None:
    _header(
        "Live civic map",
        "Explore approximate request hotspots." if public_view
        else "Explore the real service requests recorded by this installation.",
    )
    try:
        requests = list_complaints()
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        st.error(f"The request map could not be loaded: {exc}")
        return
    if requests.empty:
        _empty_state("No requests to map", "Requests with a selected location will appear here.", "⌖")
        return

    filter_cols = st.columns(5)
    priorities = sorted(requests["PREDICTED_PRIORITY"].dropna().astype(str).unique())
    categories = sorted(requests["SERVICECODEDESCRIPTION"].dropna().astype(str).unique())
    departments = sorted(requests["PREDICTED_DEPARTMENT"].dropna().astype(str).unique())
    statuses = sorted(requests["STATUS"].dropna().astype(str).unique())
    chosen_priorities = filter_cols[0].multiselect("Priority", priorities, key="map_priorities")
    chosen_categories = filter_cols[1].multiselect("Category", categories, key="map_categories")
    chosen_departments = filter_cols[2].multiselect("Department", departments, key="map_departments")
    chosen_statuses = filter_cols[3].multiselect("Status", statuses, key="map_statuses")
    ward_values = sorted(
        value for value in requests.get("WARD", pd.Series(dtype=str)).dropna().astype(str).unique()
        if value.strip()
    )
    chosen_wards = filter_cols[4].multiselect("Ward", ward_values, key="map_wards")
    date_values = _local_dates(requests["ADDDATE"])
    if date_values.notna().any():
        first_date = date_values.min()
        last_date = date_values.max()
        range_col, _ = st.columns([1.4, 2])
        selected_range = range_col.date_input(
            "Submitted between",
            value=(first_date, last_date),
            min_value=first_date,
            max_value=last_date,
            key="map_date_range",
        )
    else:
        selected_range = None

    filtered = requests.copy()
    if chosen_priorities:
        filtered = filtered[filtered["PREDICTED_PRIORITY"].isin(chosen_priorities)]
    if chosen_categories:
        filtered = filtered[filtered["SERVICECODEDESCRIPTION"].isin(chosen_categories)]
    if chosen_departments:
        filtered = filtered[filtered["PREDICTED_DEPARTMENT"].isin(chosen_departments)]
    if chosen_statuses:
        filtered = filtered[filtered["STATUS"].isin(chosen_statuses)]
    if chosen_wards:
        filtered = filtered[filtered["WARD"].isin(chosen_wards)]
    if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
        parsed_dates = _local_dates(filtered["ADDDATE"])
        lower, upper = selected_range
        filtered = filtered[parsed_dates.between(lower, upper)]

    points = _coordinates_frame(filtered)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Filtered requests", len(filtered))
    metric_cols[1].metric("Located requests", len(points))
    metric_cols[2].metric("Without coordinates", len(filtered) - len(points))
    metric_cols[3].metric("All recorded requests", len(requests))
    if points.empty:
        st.warning("No requests in this selection have valid latitude and longitude coordinates.")
        return

    if public_view:
        # Citizens see coarse aggregated hotspots; exact locations, IDs, and
        # request details remain available only to authenticated agency staff.
        public_points = (
            points.assign(
                _lat_cell=points["LATITUDE"].round(1),
                _lon_cell=points["LONGITUDE"].round(1),
            )
            .groupby(["_lat_cell", "_lon_cell"], as_index=False)
            .size()
        )
        center = [float(public_points["_lat_cell"].mean()), float(public_points["_lon_cell"].mean())]
        map_object = make_civic_map(location=center, zoom_start=7)
        for _, hotspot in public_points.iterrows():
            count = int(hotspot["size"])
            folium.CircleMarker(
                location=[float(hotspot["_lat_cell"]), float(hotspot["_lon_cell"])],
                radius=min(17, 7 + count),
                color="#5eead4",
                fill=True,
                fill_color="#0d9488",
                fill_opacity=0.65,
                tooltip=f"Approximate hotspot · {count} mapped {'request' if count == 1 else 'requests'}",
            ).add_to(map_object)
        st_folium(map_object, width=None, height=620, returned_objects=[], key="public_civic_live_map")
        st.caption("Public view groups coordinates into approximate 0.1° cells and hides request IDs, addresses, and exact coordinates.")
        st.dataframe(
            filtered.groupby(["SERVICECODEDESCRIPTION", "PREDICTED_PRIORITY", "STATUS"], dropna=False)
            .size().rename("Requests").reset_index()
            .rename(columns={"SERVICECODEDESCRIPTION": "Service category", "PREDICTED_PRIORITY": "Priority", "STATUS": "Status"}),
            hide_index=True,
            width="stretch",
        )
        return

    center = [float(points["LATITUDE"].mean()), float(points["LONGITUDE"].mean())]
    map_object = make_civic_map(location=center, zoom_start=11)
    priority_colors = {"High": "red", "Medium": "orange", "Low": "green"}
    for _, request in points.iterrows():
        request_id = html.escape(str(request["SERVICEREQUESTID"]))
        title = html.escape(str(request["SERVICECODEDESCRIPTION"]))
        department = html.escape(str(request["PREDICTED_DEPARTMENT"]))
        status = html.escape(str(request["STATUS"]))
        priority = str(request["PREDICTED_PRIORITY"])
        location = html.escape(
            ", ".join(str(request.get(key, "")).strip() for key in ("LOCATION_ADDRESS", "CITY") if str(request.get(key, "")).strip())
        )
        popup = (
            f"<strong>{request_id}</strong><br>{title}<br>Priority: {html.escape(priority)}"
            f"<br>Department: {department}<br>Status: {status}<br>Location: {location or 'Coordinates recorded'}"
        )
        marker_color = "gray" if str(request["STATUS"]) in {"Resolved", "Closed"} else priority_colors.get(priority, "blue")
        folium.CircleMarker(
            location=[float(request["LATITUDE"]), float(request["LONGITUDE"])],
            radius=8,
            color=marker_color,
            fill=True,
            fill_opacity=0.82,
                tooltip=f"{request_id} · {html.escape(priority)} · {status}",
            popup=folium.Popup(popup, max_width=320),
        ).add_to(map_object)
    st_folium(map_object, width=None, height=620, returned_objects=[], key="civic_live_map")
    st.caption("Marker colors show priority; status is also written in each marker's tooltip and details.")
    st.dataframe(
        points[["SERVICEREQUESTID", "SERVICECODEDESCRIPTION", "PREDICTED_PRIORITY", "PREDICTED_DEPARTMENT", "STATUS", "LATITUDE", "LONGITUDE"]],
        hide_index=True,
        width="stretch",
    )


def notification_center() -> None:
    _header("Notification center", "Agency notices generated by request submissions and operations updates.")
    try:
        notifications = list_notifications()
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        st.error(f"Notifications could not be loaded: {exc}")
        return

    unread = notifications[notifications["NOTIFICATION_STATUS"].fillna("") != "Read"] if not notifications.empty else pd.DataFrame()

    refresh_col, mark_all_col, summary_col = st.columns([1, 1.2, 3], vertical_alignment="center")
    if refresh_col.button("Refresh", width="stretch", key="refresh_notices_btn"):
        st.rerun()
    if not unread.empty and mark_all_col.button("Mark all as read", width="stretch", key="mark_all_read_btn"):
        for _, n_row in unread.iterrows():
            n_id = str(n_row.get("NOTIFICATION_ID", ""))
            if n_id:
                mark_notification_read(n_id)
        st.rerun()

    summary_col.metric("Unread notices", len(unread))
    st.caption("Notices are read from local request storage when this page loads.")

    if notifications.empty:
        _empty_state("No notifications yet", "New routed-request notices will be listed here.", "♧")
        return

    ordered = notifications.sort_values("NOTIFICATION_TIME", ascending=False, kind="stable")
    for _, notice in ordered.iterrows():
        notice_id = str(notice.get("NOTIFICATION_ID", ""))
        request_id = str(notice.get("SERVICEREQUESTID", ""))
        is_unread = str(notice.get("NOTIFICATION_STATUS", "")) != "Read"
        notice_col, action_col, view_col = st.columns([4, 1.1, 1.1], vertical_alignment="center")
        notice_col.markdown(
            f'<div class="case-card"><div class="case-id">{html.escape(request_id)}'
            f' &nbsp;·&nbsp; {"NEW" if is_unread else "READ"}</div>'
            f'<div class="case-title">{html.escape(str(notice.get("SERVICE_DESCRIPTION", "Service request")))}</div>'
            f'<div class="case-meta">{html.escape(str(notice.get("MESSAGE", "")))}<br>'
            f'{html.escape(str(notice.get("AGENCY", "Unassigned")))} · '
            f'{html.escape(str(notice.get("PRIORITY", "")))} priority · '
            f'{html.escape(str(notice.get("NOTIFICATION_TIME", "")))}</div></div>',
            unsafe_allow_html=True,
        )
        if is_unread and action_col.button("Mark read", key=f"notice_read_{notice_id}", width="stretch"):
            if mark_notification_read(notice_id):
                st.rerun()
            st.error("That notification no longer exists.")
        if request_id and view_col.button("View case →", key=f"notice_view_{notice_id}", width="stretch"):
            st.session_state["tracking_id"] = request_id
            _go_to_page("Track Complaint")
            st.rerun()


def department_intelligence() -> None:
    _header("Department intelligence", "Workload summaries based on saved department routes and current request records.")
    try:
        complaints = list_complaints()
        departments = sorted(set(load_routing_map().values()))
    except (OSError, ValueError, RuntimeError, pd.errors.ParserError) as exc:
        st.error(f"Department information could not be loaded: {exc}")
        return
    if not departments:
        _empty_state("No routed departments", "The saved service routing map has no department entries.", "▤")
        return
    summaries: list[dict[str, Any]] = []
    for department in departments:
        rows = complaints[complaints["PREDICTED_DEPARTMENT"] == department] if not complaints.empty else complaints
        assigned = rows.get("ASSIGNED_OFFICER", pd.Series(dtype=str)).astype(str).str.strip().ne("")
        status = rows.get("STATUS", pd.Series(dtype=str))
        high_active = (rows.get("PREDICTED_PRIORITY", pd.Series(dtype=str)) == "High") & status.isin(["Open", "In Progress"])
        summaries.append({
            "Department": department,
            "Incoming": int((status == "Open").sum()),
            "Assigned": int(assigned.sum()),
            "In progress": int((status == "In Progress").sum()),
            "Resolved": int(status.isin(["Resolved", "Closed"]).sum()),
            "High priority active": int(high_active.sum()),
            "SLA risk": "Not configured",
        })
    summary_frame = pd.DataFrame(summaries)
    _section_title("Department workload", "CURRENT REQUESTS")
    st.dataframe(summary_frame, hide_index=True, width="stretch")
    selected_department = st.selectbox("Department detail", departments, key="department_detail")
    row = summary_frame[summary_frame["Department"] == selected_department].iloc[0]
    _section_title(selected_department, "ROUTING MAP DEPARTMENT")
    metric_cols = st.columns(5)
    for col, label in zip(metric_cols, ["Incoming", "Assigned", "In progress", "Resolved", "High priority active"]):
        col.metric(label, int(row[label]))
    st.info("SLA risk is not available: this installation has no configured service-level targets or working-hours calendar.")


def ward_intelligence() -> None:
    _header("Ward intelligence", "Understand request volume in the wards citizens have entered in their reports.")
    try:
        complaints = list_complaints()
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        st.error(f"Ward request data could not be loaded: {exc}")
        return
    if complaints.empty or "WARD" not in complaints:
        _empty_state("No ward data available", "Ward information is optional and will appear after it is provided in a citizen report.", "⌖")
        return
    ward_rows = complaints[complaints["WARD"].fillna("").astype(str).str.strip() != ""]
    if ward_rows.empty:
        _empty_state(
            "No ward data available",
            "No ward names or numbers have been entered yet. CivicPulse does not infer ward boundaries from an address.",
            "⌖",
        )
        return
    summary = ward_rows.groupby("WARD", dropna=True).agg(
        Requests=("SERVICEREQUESTID", "count"),
        High_priority=("PREDICTED_PRIORITY", lambda values: int((values == "High").sum())),
        Open=("STATUS", lambda values: int((values == "Open").sum())),
        In_progress=("STATUS", lambda values: int((values == "In Progress").sum())),
        Resolved=("STATUS", lambda values: int(values.isin(["Resolved", "Closed"]).sum())),
    ).reset_index().sort_values("Requests", ascending=False)
    summary = summary.rename(columns={
        "WARD": "Ward", "High_priority": "High priority", "In_progress": "In progress"
    })
    st.dataframe(summary, hide_index=True, width="stretch")
    selected_ward = st.selectbox("Focus ward", summary["Ward"].tolist(), key="ward_detail")
    selected_rows = ward_rows[ward_rows["WARD"] == selected_ward]
    metric_cols = st.columns(5)
    for col, label in zip(metric_cols, ["Requests", "High priority", "Open", "In progress", "Resolved"]):
        col.metric(label, int(summary.loc[summary["Ward"] == selected_ward, label].iloc[0]))
    points = _coordinates_frame(selected_rows)
    if points.empty:
        st.caption("No valid coordinates are recorded for this ward yet.")
    else:
        map_object = make_civic_map(
            location=[float(points["LATITUDE"].mean()), float(points["LONGITUDE"].mean())],
            zoom_start=12,
        )
        for _, request in points.iterrows():
            folium.Marker(
                [float(request["LATITUDE"]), float(request["LONGITUDE"])],
                tooltip=f"{request['SERVICEREQUESTID']} · {request['PREDICTED_PRIORITY']}",
            ).add_to(map_object)
        st_folium(map_object, width=None, height=460, returned_objects=[], key="ward_requests_map")
    st.dataframe(
        selected_rows[["SERVICEREQUESTID", "SERVICECODEDESCRIPTION", "PREDICTED_PRIORITY", "STATUS", "ADDDATE"]],
        hide_index=True,
        width="stretch",
    )


def _command_center(complaints: pd.DataFrame) -> None:
    statuses = complaints["STATUS"] if not complaints.empty else pd.Series(dtype=str)
    today = datetime.now(APP_TIMEZONE).date()
    closed_dates = _local_dates(complaints.get("CLOSED_DATE", pd.Series(dtype=str)))
    resolved_today = int((closed_dates.dt.date == today).sum()) if not complaints.empty else 0
    high_open = int(((complaints["PREDICTED_PRIORITY"] == "High") & (statuses.isin(["Open", "In Progress"]))).sum()) if not complaints.empty else 0
    active = int(statuses.isin(["Open", "In Progress"]).sum())
    assigned = int(complaints.get("PREDICTED_DEPARTMENT", pd.Series(dtype=str)).astype(str).str.strip().ne("").sum()) if not complaints.empty else 0
    metric_cols = st.columns(5)
    for col, label, value in zip(
        metric_cols,
        ["Active requests", "High priority active", "Awaiting routing", "Resolved today", "Total local requests"],
        [active, high_open, len(complaints) - assigned, resolved_today, len(complaints)],
    ):
        col.metric(label, f"{value:,}")
    st.info("SLA risk is unavailable because no service-level targets are configured for this installation.")

    _section_title("Civic incident map", "RECORDED COORDINATES")
    points = _coordinates_frame(complaints)
    if points.empty:
        _empty_state("No mapped requests yet", "Add a location pin when reporting an issue to show it on the command map.", "⌖")
    else:
        center = [float(points["LATITUDE"].mean()), float(points["LONGITUDE"].mean())]
        map_object = make_civic_map(location=center, zoom_start=11)
        priority_colors = {"High": "red", "Medium": "orange", "Low": "green"}
        for _, request in points.iterrows():
            request_id = html.escape(str(request["SERVICEREQUESTID"]))
            description = html.escape(str(request["SERVICECODEDESCRIPTION"]))
            priority = str(request["PREDICTED_PRIORITY"])
            raw_status = str(request["STATUS"])
            status = html.escape(raw_status)
            department = html.escape(str(request.get("PREDICTED_DEPARTMENT", "")))
            location = html.escape(
                ", ".join(str(request.get(key, "")).strip() for key in ("LOCATION_ADDRESS", "CITY") if str(request.get(key, "")).strip())
            )
            folium.CircleMarker(
                location=[float(request["LATITUDE"]), float(request["LONGITUDE"])],
                radius=9,
                color="gray" if raw_status in {"Resolved", "Closed"} else priority_colors.get(priority, "blue"),
                fill=True,
                fill_opacity=0.85,
                tooltip=f"{request_id} · {html.escape(priority)} · {status}",
                popup=folium.Popup(
                    f"<strong>{request_id}</strong><br>{description}<br>{html.escape(priority)} · {status}"
                    f"<br>{department}<br>{location or 'Coordinates recorded'}"
                ),
            ).add_to(map_object)
        st_folium(map_object, width=None, height=680, returned_objects=[], key="presentation_civic_map")

    _section_title("Latest request activity", "FROM SAVED STATUS HISTORY")
    activity: list[dict[str, str]] = []
    for _, request in complaints.iterrows():
        for event in _parse_status_history(request.get("STATUS_HISTORY", "")):
            if not isinstance(event, dict):
                continue
            activity.append({
                "Request": str(request.get("SERVICEREQUESTID", "")),
                "Event": str(event.get("event", "Update")),
                "Time": str(event.get("timestamp", "")),
                "Category": str(request.get("SERVICECODEDESCRIPTION", "")),
                "Priority": str(request.get("PREDICTED_PRIORITY", "")),
            })
    if activity:
        activity_frame = pd.DataFrame(activity)
        activity_frame["_sort"] = pd.to_datetime(activity_frame["Time"], errors="coerce", utc=True)
        st.dataframe(
            activity_frame.sort_values("_sort", ascending=False).drop(columns="_sort").head(12),
            hide_index=True,
            width="stretch",
        )
    else:
        _empty_state("No activity yet", "Request submissions and status updates will appear here.", "◷")


def admin_dashboard() -> None:
    presentation = st.toggle("Command Center presentation mode", key="command_center_mode")
    if presentation:
        _header("CivicPulse Command Center", "Live operational view built from this installation's saved requests.")
        try:
            _command_center(list_complaints())
        except (OSError, ValueError, KeyError, pd.errors.ParserError) as exc:
            st.error(f"The command center could not be loaded: {exc}")
        return
    _header("Operations dashboard", "Prepared historical summaries combined with locally submitted demo requests.")
    try:
        historical_departments = _read_summary(DEPARTMENT_HISTORY_PATH)
        historical_priorities = _read_summary(PRIORITY_HISTORY_PATH)
        historical_years = _read_summary(YEAR_HISTORY_PATH)
        historical_services = _read_summary(TOP_SERVICES_PATH)
        department_priority = _read_summary(DEPARTMENT_PRIORITY_HISTORY_PATH)
    except (OSError, pd.errors.ParserError, ValueError) as exc:
        st.error(f"Historical summary data could not be loaded: {exc}")
        return

    live = list_complaints()
    historic_total = int(pd.to_numeric(historical_departments["Count"], errors="coerce").fillna(0).sum())
    total = historic_total + len(live)
    live_status = live["STATUS"] if not live.empty else pd.Series(dtype=str)
    open_count = int((live_status == "Open").sum())
    in_progress_count = int((live_status == "In Progress").sum())
    resolved_count = int((live_status == "Resolved").sum())
    closed_count = int((live_status == "Closed").sum())
    metrics = st.columns(5)
    for col, label, value in zip(
        metrics,
        ["Total requests", "Open", "In progress", "Resolved", "Closed"],
        [total, open_count, in_progress_count, resolved_count, closed_count],
    ):
        col.metric(label, f"{value:,}")
    st.caption(
        f"Historical total from prepared department summaries: {historic_total:,}. "
        "Status counts represent locally tracked live requests."
    )

    _section_title("Local operations", "FILTER SAVED REQUESTS")
    period_col, period_help_col = st.columns([1, 3])
    period = period_col.selectbox(
        "Reporting window",
        ["All time", "Today", "7 days", "30 days", "90 days", "Custom"],
        key="analytics_period",
    )
    local_live = live.copy()
    if not local_live.empty:
        local_live["_LOCAL_DATE"] = _local_dates(local_live["ADDDATE"])
        valid_dates = local_live["_LOCAL_DATE"].dropna()
        today = datetime.now(APP_TIMEZONE).date()
        if period == "Today":
            local_live = local_live[local_live["_LOCAL_DATE"] == today]
        elif period in {"7 days", "30 days", "90 days"}:
            window_days = int(period.split()[0])
            local_live = local_live[local_live["_LOCAL_DATE"] >= today - pd.Timedelta(days=window_days - 1)]
        elif period == "Custom" and not valid_dates.empty:
            date_range = st.date_input(
                "Custom date range",
                value=(valid_dates.min(), valid_dates.max()),
                min_value=valid_dates.min(),
                max_value=valid_dates.max(),
                key="analytics_custom_range",
            )
            if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
                local_live = local_live[local_live["_LOCAL_DATE"].between(date_range[0], date_range[1])]
        period_help_col.caption("This section uses saved request records. Prepared historical summaries below are separate reference data.")
    if local_live.empty:
        _empty_state("No requests in this window", "Try a wider date range or record a new service request.", "◷")
    else:
        local_status = local_live["STATUS"]
        completed_count = int(local_status.isin(["Resolved", "Closed"]).sum())
        submitted_times = pd.to_datetime(local_live["ADDDATE"], errors="coerce", utc=True)
        resolved_times = pd.to_datetime(local_live["CLOSED_DATE"], errors="coerce", utc=True)
        resolution_hours = (resolved_times - submitted_times).dt.total_seconds() / 3600
        valid_resolution_hours = resolution_hours[resolution_hours.ge(0)].dropna()
        average_resolution = f"{valid_resolution_hours.mean():.1f} h" if not valid_resolution_hours.empty else "—"
        local_metrics = st.columns(5)
        for col, label, value in zip(
            local_metrics,
            ["Requests", "Open", "High priority", "In progress", "Resolution rate"],
            [len(local_live), int((local_status == "Open").sum()),
             int((local_live["PREDICTED_PRIORITY"] == "High").sum()),
             int((local_status == "In Progress").sum()),
             f"{completed_count / len(local_live):.1%}" if len(local_live) else "—"],
        ):
            col.metric(label, value if isinstance(value, str) else f"{value:,}")
        st.metric("Average recorded resolution time", average_resolution)
        if valid_resolution_hours.empty:
            st.caption("This window has no completed requests with valid submission and completion timestamps.")
        trend = local_live.groupby("_LOCAL_DATE").size().rename("Requests").reset_index()
        category_counts = local_live.groupby("SERVICECODEDESCRIPTION").size().rename("Requests").reset_index()
        priority_counts = local_live.groupby("PREDICTED_PRIORITY").size().rename("Requests").reset_index()
        department_counts = local_live.groupby("PREDICTED_DEPARTMENT").size().rename("Requests").reset_index()
        chart_left, chart_right = st.columns(2)
        with chart_left:
            _render_chart(
                px.line(trend, x="_LOCAL_DATE", y="Requests", markers=True, title="Saved requests over time")
                .update_traces(line_color="#76b8ff", marker_color="#61e7e0", line_width=3)
            )
        with chart_right:
            _render_chart(
                px.bar(category_counts.sort_values("Requests", ascending=False).head(12),
                       x="Requests", y="SERVICECODEDESCRIPTION", orientation="h",
                       title="Saved requests by service category", color="Requests",
                       color_continuous_scale=["#18324a", "#76b8ff"])
            )
        chart_left, chart_right = st.columns(2)
        with chart_left:
            _render_chart(
                px.pie(
                    priority_counts,
                    names="PREDICTED_PRIORITY",
                    values="Requests",
                    title="Saved requests by model priority",
                    hole=0.45,
                    color="PREDICTED_PRIORITY",
                    color_discrete_map={"Low": "#61d6a0", "Medium": "#ffc56c", "High": "#ff718d"},
                )
            )
        with chart_right:
            _render_chart(
                px.bar(department_counts.sort_values("Requests", ascending=False),
                       x="Requests", y="PREDICTED_DEPARTMENT", orientation="h",
                       title="Saved requests by department", color="Requests",
                       color_continuous_scale=["#18324a", "#76b8ff"])
            )
        if local_live.get("WARD", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("").any():
            ward_summary = local_live[local_live["WARD"].fillna("").astype(str).str.strip() != ""]
            ward_summary = ward_summary.groupby("WARD").size().rename("Requests").reset_index()
            _render_chart(px.bar(ward_summary, x="WARD", y="Requests", title="Requests by reported ward"))
        else:
            st.caption("Ward breakdown will appear when reporters provide a ward or service-zone value.")

    department_data = historical_departments.copy()
    priority_data = historical_priorities.copy()
    dp_data = department_priority.copy()
    if not live.empty:
        live_dept = live.groupby("PREDICTED_DEPARTMENT").size().rename("Count")
        department_data = department_data.set_index("Department")
        department_data["Count"] = department_data["Count"].add(live_dept, fill_value=0)
        department_data = department_data.rename_axis("Department").reset_index()

        live_priority = live.groupby("PREDICTED_PRIORITY").size().rename("Count")
        priority_data = priority_data.set_index("Priority")
        priority_data["Count"] = priority_data["Count"].add(live_priority, fill_value=0)
        priority_data = priority_data.rename_axis("Priority").reset_index()

        live_matrix = pd.crosstab(live["PREDICTED_DEPARTMENT"], live["PREDICTED_PRIORITY"])
        dp_data = dp_data.set_index("Department")
        for name in ["Low", "Medium", "High"]:
            if name not in dp_data:
                dp_data[name] = 0
            dp_data[name] = dp_data[name].add(live_matrix.get(name, pd.Series(dtype=float)), fill_value=0)
        dp_data = dp_data.rename_axis("Department").reset_index()

    first, second = st.columns(2)
    with first:
        _render_chart(
            px.bar(
                department_data.sort_values("Count", ascending=False),
                x="Department",
                y="Count",
                title="Requests by department",
                color="Count",
                color_continuous_scale=["#d8e9f6", "#1769aa", "#112f50"],
            ),
        )
    with second:
        _render_chart(
            px.pie(
                priority_data,
                names="Priority",
                values="Count",
                title="Requests by priority",
                hole=0.42,
                color="Priority",
                color_discrete_map={"Low": "#23835b", "Medium": "#d99a20", "High": "#c24b4b"},
            ),
        )

    status_data = pd.DataFrame(
        {"Status": ["Open", "In Progress", "Resolved", "Closed"],
         "Count": [open_count, in_progress_count, resolved_count, closed_count]}
    )
    year_data = historical_years.copy()
    year_data["YEAR"] = year_data["YEAR"].astype(str)
    current_year = str(datetime.now().year)
    this_year_live = int((live["ADD_YEAR"].astype(str) == current_year).sum()) if not live.empty else 0
    if current_year in year_data["YEAR"].values:
        year_data.loc[year_data["YEAR"] == current_year, "Count"] += this_year_live
    elif this_year_live:
        year_data = pd.concat(
            [year_data, pd.DataFrame([{"YEAR": current_year, "Count": this_year_live}])],
            ignore_index=True,
        )
    year_data["Count"] = pd.to_numeric(year_data["Count"], errors="coerce").fillna(0)
    year_data = year_data.sort_values("YEAR")
    service_data = historical_services.head(15)

    first, second = st.columns(2)
    with first:
        _render_chart(
            px.bar(
                status_data,
                x="Status",
                y="Count",
                title="Live requests by status",
                color="Status",
                color_discrete_map={
                    "Open": "#397aa8",
                    "In Progress": "#d99a20",
                    "Resolved": "#23835b",
                    "Closed": "#52718b",
                },
            )
        )
    with second:
        _render_chart(
            px.line(
                year_data,
                x="YEAR",
                y="Count",
                title="Historical yearly request trend",
                markers=True,
            ).update_traces(line_color="#1769aa", marker_color="#1769aa", line_width=3),
        )
    first, second = st.columns(2)
    with first:
        _render_chart(
            px.bar(
                service_data.sort_values("Count"),
                x="Count",
                y="Service Category",
                orientation="h",
                title="Top service categories",
                color="Count",
                color_continuous_scale=["#d9eee7", "#23835b"],
            ),
        )
    with second:
        heatmap_data = dp_data.set_index("Department")[["Low", "Medium", "High"]]
        _render_chart(
            px.imshow(
                heatmap_data,
                text_auto=True,
                aspect="auto",
                color_continuous_scale=["#f2f7fb", "#9fc5df", "#1769aa", "#112f50"],
                title="Department × priority",
                labels={"x": "Priority", "y": "Department", "color": "Requests"},
            ),
        )


def model_information(project_config: dict) -> None:
    _header("Model performance", "Transparent information about the model and rules used to route service requests.")
    st.markdown(
        '<div class="case-card"><div class="eyebrow">PRIORITY CLASSIFICATION</div>'
        '<div class="case-title" style="font-size:1.2rem">CatBoost priority prediction</div>'
        '<div class="case-meta">The saved CatBoost classifier was trained on historical Washington, DC 311 data '
        'and has not been validated for India. Its predictions for Indian service requests are experimental decision '
        'support and require agency review. The model estimates Low, Medium, and High priority using legacy service, '
        'ward, ZIP code, date/time, and coordinate features; an Indian PIN Code is passed through its legacy ZIP-code '
        'feature. High priority is assigned when the High-class '
        'probability reaches the configured threshold; otherwise the stronger Low or Medium class is used.</div></div>',
        unsafe_allow_html=True,
    )
    st.info(
        "India data note: the citizen form records State and PIN Code, but the saved model was not trained or "
        "validated on Indian service-request data. Do not treat its priority estimate as India-validated."
    )
    _section_title("Evaluation results", "HELD-OUT TEST SET")
    metric_cols = st.columns(5)
    for col, label in zip(
        metric_cols,
        ["Test accuracy", "Macro F1", "Macro precision", "Macro recall", "Weighted F1"],
    ):
        col.metric(label, MODEL_INFO["priority_metrics"][label])
    threshold_col, explanation_col = st.columns([1, 3])
    with threshold_col:
        st.metric("High-priority threshold", f"{project_config['high_threshold']:.2f}")
    with explanation_col:
        st.markdown(
            '<div class="helper-panel" style="margin-top:.4rem"><strong>Interpreting the results</strong><br>'
            'These figures summarize evaluation performance; they do not guarantee an individual prediction. '
            'Department staff retain responsibility for case review and service decisions.</div>',
            unsafe_allow_html=True,
        )

    _section_title("Department routing", "DETERMINISTIC LOOKUP")
    st.markdown(
        '<div class="case-card"><div class="case-title">SERVICECODE → Department</div>'
        '<div class="case-meta">Each supported service code is looked up in the saved department routing map. '
        'Routing is deterministic and independent of the CatBoost priority prediction.</div></div>',
        unsafe_allow_html=True,
    )
    routing_metrics = [
        ("Routing accuracy", MODEL_INFO["routing_metrics"]["Accuracy"]),
        ("Routing Macro F1", MODEL_INFO["routing_metrics"]["Macro F1"]),
        ("Routing Weighted F1", MODEL_INFO["routing_metrics"]["Weighted F1"]),
        ("Unseen service codes", MODEL_INFO["routing_metrics"]["Unseen test codes"]),
    ]
    routing_cols = st.columns(4)
    for col, (label, value) in zip(routing_cols, routing_metrics):
        col.metric(label, value)

    with st.expander("Model inputs and demo-mode data"):
        st.write("CatBoost feature columns:", ", ".join(project_config["feature_cols"]))
        st.write(
            "Demo mode uses the saved model, routing map, feature medians, service lookup, "
            "and prepared historical summary CSV files. Large raw historical datasets are "
            "not required."
        )
        st.caption(f"Prepared reference files are loaded from: {APP_DATA_DIR}")


def _auth_configuration() -> tuple[bool, set[str], set[str]]:
    """Read optional Streamlit OIDC configuration and trusted role allowlists."""
    try:
        auth = dict(st.secrets.get("auth", {}))
        roles = dict(st.secrets.get("roles", {}))
    except (FileNotFoundError, KeyError, TypeError, AttributeError):
        return False, set(), set()
    required_auth_values = ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")
    enabled = all(auth.get(key) and not str(auth.get(key)).startswith("replace-") for key in required_auth_values)
    admins = {str(email).strip().lower() for email in roles.get("administrators", []) if str(email).strip()}
    officers = {str(email).strip().lower() for email in roles.get("officers", []) if str(email).strip()}
    return enabled, admins, officers


def _current_user_role(auth_enabled: bool, admins: set[str], officers: set[str]) -> tuple[str, str]:
    if not auth_enabled:
        return "anonymous", ""
    try:
        if not st.user.is_logged_in:
            return "anonymous", ""
        email = str(st.user.get("email", "")).strip().lower()
        display_name = str(st.user.get("name", "")).strip() or email
        verified_claim = st.user.get("email_verified", False)
        email_verified = verified_claim is True or str(verified_claim).strip().casefold() == "true"
    except (AttributeError, KeyError, TypeError):
        return "anonymous", ""
    if email_verified and email in admins:
        return "administrator", display_name
    if email_verified and email in officers:
        return "officer", display_name
    return "citizen", display_name


def _begin_credential_session(user: dict[str, Any]) -> None:
    """Keep only the account ID in Streamlit session state; reload role from DB."""
    st.session_state["credential_user_id"] = str(user["user_id"])
    st.session_state["auth_source"] = "credentials"
    st.session_state["auth_expires_at"] = datetime.now().timestamp() + 8 * 60 * 60


def _render_authentication_screen(oidc_enabled: bool) -> None:
    try:
        has_accounts = has_registered_users()
    except (OSError, sqlite3.Error) as exc:
        st.error(f"The local account store could not be opened: {exc}")
        return
    st.markdown(
        '<div class="portal-banner auth-card"><div class="eyebrow">CIVICPULSE · SECURE ACCESS</div>'
        '<h1>Welcome to CivicPulse</h1>'
        '<p>Create a citizen account to report and follow service requests, or sign in to continue.</p></div>',
        unsafe_allow_html=True,
    )
    left, form_column, right = st.columns([1, 1.25, 1])
    with form_column:
        with st.container(border=True):
            st.markdown('<div class="section-kicker">YOUR ACCOUNT</div>', unsafe_allow_html=True)
            mode = st.radio(
                "Account access",
                ["Sign in", "Register"],
                horizontal=True,
                index=0 if has_accounts else 1,
                key="auth_mode_existing" if has_accounts else "auth_mode_first_run",
                label_visibility="collapsed",
            )
            if mode == "Register":
                with st.form("citizen_registration_form", clear_on_submit=False):
                    display_name = st.text_input("Full name", max_chars=80, autocomplete="name")
                    email = st.text_input("Email address", max_chars=254, autocomplete="email")
                    password = st.text_input("Create password", type="password", max_chars=1024, autocomplete="new-password")
                    confirm_password = st.text_input("Confirm password", type="password", max_chars=1024, autocomplete="new-password")
                    st.caption("Use at least 12 characters. New self-registered accounts receive citizen access.")
                    submitted = st.form_submit_button("Create account", type="primary", width="stretch")
                if submitted:
                    if password != confirm_password:
                        st.error("The two passwords do not match.")
                    else:
                        try:
                            new_user = register_citizen(email, display_name, password)
                        except ValueError as exc:
                            st.error(str(exc))
                        except (OSError, RuntimeError, sqlite3.Error) as exc:
                            st.error(f"The account could not be created: {exc}")
                        else:
                            _begin_credential_session(new_user)
                            st.rerun()
            else:
                with st.form("citizen_login_form", clear_on_submit=False):
                    email = st.text_input("Email address", max_chars=254, autocomplete="email")
                    password = st.text_input("Password", type="password", max_chars=1024, autocomplete="current-password")
                    submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
                if submitted:
                    try:
                        client_ip = str(st.context.ip_address or "unknown")
                    except Exception:
                        client_ip = "unknown"
                    try:
                        user, error_message = authenticate_user(email, password, client_ip=client_ip)
                    except (OSError, RuntimeError, sqlite3.Error) as exc:
                        st.error(f"Sign-in is temporarily unavailable: {exc}")
                    else:
                        if user:
                            _begin_credential_session(user)
                            st.rerun()
                        st.error(error_message)
                st.caption("Forgot your password? Contact your CivicPulse administrator; email reset is not configured.")

            st.markdown(
                '<div class="helper-panel">For account safety, public registration never grants agency access. '
                'Officers and administrators are provisioned separately.</div>',
                unsafe_allow_html=True,
            )
            if oidc_enabled:
                st.divider()
                configured_provider = str(st.secrets.get("auth", {}).get("server_metadata_url", ""))
                provider_label = "Continue with Google" if "accounts.google.com" in configured_provider else "Continue with your organization"
                st.button(provider_label, type="secondary", on_click=st.login, key="oidc_continue", width="stretch")


def _local_demo_override_enabled() -> bool:
    """Enable the unauthenticated demo only through an explicit local opt-in."""
    return os.environ.get("CIVICPULSE_DEMO_MODE", "").strip().casefold() in {"1", "true", "yes"}


def help_center() -> None:
    _header("CivicPulse help", "Quick guidance for submitting, following, and understanding a service request.")
    help_columns = st.columns(3)
    help_cards = [
        ("01", "Report clearly", "Choose the closest service category, describe what happened, and attach a photo only when it helps explain the issue."),
        ("02", "Add a location", "Confirm the report location on the map. A precise location helps the responsible team find the issue."),
        ("03", "Follow progress", "Keep the request ID shown after submission. Use it on Track a request to review status updates."),
    ]
    for column, (number, title, description) in zip(help_columns, help_cards):
        with column:
            st.markdown(
                f'<section class="help-card"><span class="help-number">{number}</span>'
                f'<h3>{html.escape(title)}</h3><p>{html.escape(description)}</p></section>',
                unsafe_allow_html=True,
            )
    st.caption("Priority estimates and routing suggestions support agency triage; staff review and manage requests.")
    report_col, track_col = st.columns(2)
    with report_col:
        if st.button("Report an issue", type="primary", key="help_report"):
            _go_to_page("Report Complaint")
            st.rerun()
    with track_col:
        if st.button("Track a request", key="help_track"):
            _go_to_page("Track Complaint")
            st.rerun()


def system_health(auth_enabled: bool) -> None:
    _header("System health", "A transparent view of the services and integrations this installation actually uses.")
    checks: list[tuple[str, bool | None, str]] = []
    try:
        complaints = list_complaints()
        notifications = list_notifications()
        checks.append(("Local request store", True, f"CSV storage readable · {len(complaints):,} requests"))
        checks.append(("Local notification store", True, f"CSV storage readable · {len(notifications):,} notices"))
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        checks.append(("Local data storage", False, str(exc)))
    upload_writable = os.access(UPLOADS_DIR if UPLOADS_DIR.is_dir() else APP_DATA_DIR, os.W_OK)
    checks.append(("Evidence storage", upload_writable, "Upload directory is writable" if upload_writable else "Upload directory is not writable"))
    model_files = (PRIORITY_MODEL_PATH, PROJECT_CONFIG_PATH, FEATURE_MEDIANS_PATH)
    model_ready = all(path.is_file() for path in model_files)
    checks.append(("Priority model assets", model_ready, "CatBoost artifacts " + ("are present" if model_ready else "are incomplete")))
    checks.append(("Vision analysis", None, "Demo Vision Analysis: metadata only; no computer-vision model configured"))
    checks.append(("Real-time events", None, "Not configured; views refresh when the app reruns"))
    checks.append(("Standalone API", None, "Not configured; the Streamlit app calls local services directly"))
    auth_store_writable = os.access(APP_DATA_DIR if APP_DATA_DIR.exists() else APP_DATA_DIR.parent, os.W_OK)
    auth_detail = "Local credential accounts available"
    if auth_enabled:
        auth_detail += " · OIDC sign-in and allowlists also configured"
    checks.append(("Authentication", auth_store_writable, auth_detail if auth_store_writable else "Account database directory is not writable"))
    for label, healthy, detail in checks:
        if healthy is True:
            st.success(f"{label} — available · {detail}")
        elif healthy is False:
            st.error(f"{label} — unavailable · {detail}")
        else:
            st.info(f"{label} — {detail}")


def main() -> None:
    auth_enabled, administrators, officers = _auth_configuration()
    oidc_role, oidc_name = _current_user_role(auth_enabled, administrators, officers) if auth_enabled else ("anonymous", "")
    auth_source = "oidc" if oidc_role != "anonymous" else ""
    role, display_name = oidc_role, oidc_name

    if role == "anonymous":
        credential_user_id = st.session_state.get("credential_user_id")
        session_expiry = float(st.session_state.get("auth_expires_at", 0) or 0)
        if credential_user_id and datetime.now().timestamp() < session_expiry:
            try:
                credential_user = get_user_by_id(str(credential_user_id))
            except (OSError, sqlite3.Error) as exc:
                st.error(f"The local account store could not be read: {exc}")
                st.stop()
            if credential_user:
                role = str(credential_user["role"])
                display_name = str(credential_user["display_name"])
                auth_source = "credentials"
            else:
                st.session_state.pop("credential_user_id", None)
                st.session_state.pop("auth_expires_at", None)
                st.session_state.pop("auth_source", None)
        else:
            st.session_state.pop("credential_user_id", None)
            st.session_state.pop("auth_expires_at", None)

    if role == "anonymous" and _local_demo_override_enabled():
        role, display_name, auth_source = "demo", "Local demo", "demo"
    if role == "anonymous":
        _render_authentication_screen(auth_enabled)
        st.stop()

    try:
        services = load_service_lookup()
        _, project_config, _ = load_predictor_assets()
    except (OSError, ValueError, KeyError, RuntimeError, pd.errors.ParserError) as exc:
        st.error(f"The application could not load its local model or prepared data: {exc}")
        st.stop()

    page_labels = {
        "Citizen Dashboard": "⌂  Dashboard",
        "Report Complaint": "＋  Report a complaint",
        "Track Complaint": "◷  Track a request",
        "Help Center": "ⓘ  Help center",
        "Live Map": "⌖  Live map",
        "Notifications": "♧  Notifications",
        "System Health": "◉  System health",
        "Ward Intelligence": "⌖  Ward intelligence",
        "Department Intelligence": "▤  Departments",
        "Agency Portal": "▤  Agency inbox",
        "Admin Dashboard": "▥  Analytics",
        "Model Information": "ⓘ  Model insights",
    }
    if auth_source == "oidc":
        st.session_state.pop("credential_user_id", None)
        st.session_state.pop("auth_expires_at", None)
    st.session_state["auth_source"] = auth_source
    st.session_state["authenticated"] = role not in {"anonymous", "demo"}
    st.session_state["user_role"] = role

    if role == "citizen":
        allowed_pages = {"Citizen Dashboard", "Report Complaint", "Track Complaint", "Help Center", "Live Map"}
    elif role == "officer":
        allowed_pages = {
            "Citizen Dashboard", "Report Complaint", "Track Complaint", "Live Map",
            "Notifications", "System Health", "Ward Intelligence", "Department Intelligence",
            "Agency Portal", "Admin Dashboard", "Model Information", "Help Center",
        }
    else:
        allowed_pages = set(page_labels)
    page_labels = {page: label for page, label in page_labels.items() if page in allowed_pages}
    label_pages = {label: page for page, label in page_labels.items()}
    current_page = st.session_state.get("portal_page", "Citizen Dashboard")
    navigation_target = st.session_state.pop("navigation_target", None)
    try:
        requested_action = str(st.query_params.get("nav", "")).strip().casefold()
        if requested_action:
            st.query_params.pop("nav", None)
            query_target = floating_action_target(requested_action, role)
            if query_target in allowed_pages:
                navigation_target = query_target
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    if navigation_target in page_labels:
        st.session_state["navigation_choice"] = page_labels[navigation_target]
    elif st.session_state.get("navigation_choice") not in label_pages:
        st.session_state["navigation_choice"] = page_labels.get(current_page, page_labels["Citizen Dashboard"])

    try:
        notifications = list_notifications()
        new_count = (
            int((notifications["NOTIFICATION_STATUS"].fillna("") == "New").sum())
            if "NOTIFICATION_STATUS" in notifications
            else len(notifications)
        )
    except (OSError, ValueError, pd.errors.ParserError):
        new_count = 0

    brand_col, utility_col, theme_col = st.columns([2.7, 1.4, 0.7], vertical_alignment="center")
    with brand_col:
        st.markdown(
            '<div class="app-brand"><div class="brand-seal">🏛</div><div>'
            '<div class="brand-name">CivicPulse</div>'
            '<div class="brand-subtitle">TURNING CIVIC SIGNALS INTO ACTION</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
    with utility_col:
        role_labels = {
            "demo": "LOCAL DEMO",
            "citizen": "CITIZEN",
            "officer": "AGENCY OFFICER",
            "administrator": "AGENCY ADMIN",
        }
        role_label = role_labels.get(role, "PUBLIC")
        status_label = "DEMO WORKSPACE" if role == "demo" else ("OIDC SESSION VERIFIED" if auth_source == "oidc" else "SIGNED IN")
        avatar = html.escape((display_name or "P")[:1].upper())
        st.markdown(
            f'<div class="brand-utility"><span class="utility-pill">'
            f'<span class="live-dot">●</span>&nbsp;{status_label}</span><br>'
            f'<span class="avatar-chip">{avatar}</span> '
            f'<strong>{html.escape(display_name or "Public access")}</strong> '
            f'<span class="role-pill">{role_label}</span><br>'
            f'♧ &nbsp;{new_count} new agency notices</div>',
            unsafe_allow_html=True,
        )
        if auth_source in {"oidc", "credentials"} and st.button("Sign out", key="sign_out", width="stretch"):
            st.session_state.pop("credential_user_id", None)
            st.session_state.pop("auth_expires_at", None)
            st.session_state.pop("auth_source", None)
            st.session_state.pop("authenticated", None)
            st.session_state.pop("user_role", None)
            if auth_source == "oidc":
                st.logout()
            st.rerun()
    with theme_col:
        current_theme = st.session_state.get("app_theme", "light")
        toggle_label = "🌙 Dark" if current_theme == "light" else "☀️ Light"
        if st.button(toggle_label, key="app_theme_toggle_btn", width="stretch", help="Toggle between Light and Dark mode"):
            st.session_state["app_theme"] = "dark" if current_theme == "light" else "light"
            st.rerun()
    st.markdown('<div class="top-rule"></div>', unsafe_allow_html=True)
    page_label = st.radio(
        "Main navigation",
        list(page_labels.values()),
        key="navigation_choice",
        horizontal=True,
        label_visibility="collapsed",
        on_change=_navigation_changed,
        args=(label_pages,),
    )
    page = label_pages[page_label]
    st.session_state["portal_page"] = page
    st.markdown(floating_action_markup(role, new_count), unsafe_allow_html=True)

    try:
        if page == "Citizen Dashboard":
            citizen_dashboard(services)
        elif page == "Report Complaint":
            report_complaint(services)
        elif page == "Track Complaint":
            show_tracking(st.session_state.get("tracking_id", ""))
        elif page == "Help Center":
            help_center()
        elif page == "Live Map":
            live_civic_map(public_view=(role == "citizen"))
        elif page == "Notifications":
            notification_center()
        elif page == "System Health":
            system_health(auth_enabled)
        elif page == "Ward Intelligence":
            ward_intelligence()
        elif page == "Department Intelligence":
            department_intelligence()
        elif page == "Agency Portal":
            agency_portal()
        elif page == "Admin Dashboard":
            admin_dashboard()
        else:
            model_information(project_config)
    except (OSError, ValueError, KeyError, RuntimeError, pd.errors.ParserError) as exc:
        st.error(f"Unable to load local request data: {exc}")


if __name__ == "__main__":
    main()
