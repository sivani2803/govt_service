"""CivicPulse Road Watch: Dashcam road damage visualizer and sample telemetry.

Provides high-impact illustrative dashcam imagery of road damage, potholes,
and pavement fractures for the civic operations center dashboard.
All visuals are strictly illustrative/AI-generated samples and clearly labeled
as non-evidence visuals to uphold public service transparency.
"""
from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.config import ROAD_WATCH_ASSETS_DIR

_ROAD_WATCH_SAMPLES: list[dict[str, Any]] = [
    {
        "id": "RW-01-URBAN-DAY",
        "filename": "dashcam_pothole_urban_day.jpg",
        "title": "Severe Urban Asphalt Cavity",
        "category": "Road Damage / Pothole",
        "defect_type": "Pavement Cavity Void",
        "severity": "Critical",
        "severity_color": "#EF4444",
        "condition": "4–6 in. pit depth · Fractured jagged perimeter & aggregate loss",
        "lighting": "Overcast Daylight",
        "weather": "Dry / Normal",
        "lane_position": "Center Drive Lane",
        "simulated_sector": "Sector 4 North Arterial · Cam 01",
        "hud_telemetry": "LAT 16.5097° N · LON 80.6480° E · ELEV +18m · CAM_FWD_1080P",
        "service_code": "S0301",
        "service_name": "Pothole",
        "department": "DDOT",
        "disclaimer": "AI-generated illustrative sample · Not resident evidence",
    },
    {
        "id": "RW-02-WET-DUSK",
        "filename": "dashcam_pothole_wet_dusk.jpg",
        "title": "Rain-Filled Road Crater",
        "category": "Road Damage / Standing Water Hazard",
        "defect_type": "Submerged Cavity & Traction Hazard",
        "severity": "High",
        "severity_color": "#F97316",
        "condition": "Water-concealed depth · Low night visibility · High hydroplane risk",
        "lighting": "Dusk / Rain & Wet Asphalt",
        "weather": "Precipitation / Wet Surface",
        "lane_position": "Outer Traffic Lane",
        "simulated_sector": "Route 11 Corridor · Cam 02",
        "hud_telemetry": "LAT 16.5142° N · LON 80.6321° E · ELEV +14m · CAM_FWD_NIGHT_ENH",
        "service_code": "S0301",
        "service_name": "Pothole",
        "department": "DDOT",
        "disclaimer": "AI-generated illustrative sample · Not resident evidence",
    },
    {
        "id": "RW-03-SHOULDER-CRACK",
        "filename": "dashcam_edge_damage_shoulder.jpg",
        "title": "Shoulder Fatigue Cracking & Curb Slump",
        "category": "Pavement Deterioration",
        "defect_type": "Alligator Fatigue & Edge Breakdown",
        "severity": "High",
        "severity_color": "#F97316",
        "condition": "Longitudinal fracture seam · Structural shoulder erosion",
        "lighting": "Overcast Morning",
        "weather": "Damp / Post-Rain",
        "lane_position": "Shoulder / Curb Boundary",
        "simulated_sector": "Outer Ring Sector W · Cam 03",
        "hud_telemetry": "LAT 16.4988° N · LON 80.6610° E · ELEV +22m · CAM_FWD_1080P",
        "service_code": "S0301",
        "service_name": "Pothole",
        "department": "DDOT",
        "disclaimer": "AI-generated illustrative sample · Not resident evidence",
    },
    {
        "id": "RW-04-TRENCH-PATCH",
        "filename": "dashcam_pavement_void_patch.jpg",
        "title": "Commercial Corridor Trench Patch Failure",
        "category": "Utility Trench Depression",
        "defect_type": "Transverse Utility Seam Void",
        "severity": "Medium",
        "severity_color": "#EAB308",
        "condition": "Sunken utility cut · Exposed base aggregate & tire impact lip",
        "lighting": "Clear Morning Sunlight",
        "weather": "Dry / High Visibility",
        "lane_position": "Primary Travel Lane",
        "simulated_sector": "Commercial Avenue C-8 · Cam 04",
        "hud_telemetry": "LAT 16.5210° N · LON 80.6155° E · ELEV +16m · CAM_FWD_1080P",
        "service_code": "S0301",
        "service_name": "Pothole",
        "department": "DDOT",
        "disclaimer": "AI-generated illustrative sample · Not resident evidence",
    },
]


def get_road_watch_samples() -> list[dict[str, Any]]:
    """Return all configured road watch illustrative sample items."""
    return list(_ROAD_WATCH_SAMPLES)


def get_road_watch_sample(sample_id: str) -> dict[str, Any] | None:
    """Find a specific sample by ID or filename."""
    norm = str(sample_id).strip().casefold()
    for sample in _ROAD_WATCH_SAMPLES:
        if sample["id"].casefold() == norm or sample["filename"].casefold() == norm:
            return sample
    return None


@lru_cache(maxsize=16)
def get_sample_image_base64(filename: str) -> str:
    """Return a base64 data URI for the specified road watch asset."""
    file_path = ROAD_WATCH_ASSETS_DIR / filename
    if not file_path.is_file():
        return ""
    try:
        content = file_path.read_bytes()
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except OSError:
        return ""


@lru_cache(maxsize=8)
def get_sample_image_bytes(index: int = 0) -> bytes | None:
    """Return raw bytes of a sample image for fallback usage."""
    if not _ROAD_WATCH_SAMPLES:
        return None
    sample = _ROAD_WATCH_SAMPLES[index % len(_ROAD_WATCH_SAMPLES)]
    file_path = ROAD_WATCH_ASSETS_DIR / sample["filename"]
    if file_path.is_file():
        try:
            return file_path.read_bytes()
        except OSError:
            pass
    return None


def render_road_watch_panel(
    services: pd.DataFrame | None = None,
    on_report_callback: Any = None,
    key_prefix: str = "rw",
) -> None:
    """Render the central Road Watch operations center feature panel."""
    st.html(
        """
        <div class="road-watch-header">
          <div class="rw-title-group">
            <span class="rw-badge">DASHCAM SAMPLE VISUALS</span>
            <h2 class="rw-title">Road Watch · Illustrative Dashcam Samples</h2>
            <div class="rw-sub">Illustrative dashcam examples for proactive damage reporting</div>
          </div>
          <div class="rw-header-status">
            <span class="rw-chip rw-chip-urgent">SAMPLE CAMERA · ILLUSTRATIVE ONLY</span>
            <span class="rw-chip rw-chip-meta">REPORT ROAD DAMAGE</span>
          </div>
        </div>
        """,
    )

    # Sample camera selector tabs
    samples = get_road_watch_samples()
    labels = [
        f"CAM 01 · Urban Crater",
        f"CAM 02 · Wet Rain Dusk",
        f"CAM 03 · Shoulder Crack",
        f"CAM 04 · Trench Seam",
    ]

    selected_label = st.radio(
        "Select Road Watch Camera View",
        labels,
        horizontal=True,
        label_visibility="collapsed",
        key=f"{key_prefix}_cam_select",
    )
    selected_index = labels.index(selected_label) if selected_label in labels else 0
    sample = samples[selected_index]

    img_data_uri = get_sample_image_base64(sample["filename"])

    safe_title = html.escape(sample["title"])
    safe_condition = html.escape(sample["condition"])
    safe_sector = html.escape(sample["simulated_sector"])
    safe_telemetry = html.escape(sample["hud_telemetry"])
    safe_lighting = html.escape(sample["lighting"])
    safe_defect = html.escape(sample["defect_type"])
    safe_disclaimer = html.escape(sample["disclaimer"])
    severity_color = sample.get("severity_color", "#F97316")
    severity = html.escape(sample["severity"])

    st.html(
        f"""
        <div class="road-watch-container">
          <div class="rw-viewport">
            <img class="rw-image" src="{img_data_uri}" alt="{safe_title}" loading="eager" />
            <div class="rw-overlay-scrim"></div>
            
            <!-- Top HUD Bar -->
            <div class="rw-hud-top">
              <div class="rw-hud-tag rw-hud-rec">
                <span class="rw-rec-dot"></span>REC · FORWARD DASHCAM
              </div>
              <div class="rw-hud-telemetry">{safe_telemetry}</div>
              <div class="rw-hud-tag" style="background:rgba(15,23,42,.85);border-color:{severity_color};color:{severity_color};font-weight:700">
                SAMPLE LEVEL: {severity.upper()}
              </div>
            </div>

            <!-- Optical Grid Target Marker -->
            <div class="rw-target-box" aria-hidden="true">
              <div class="rw-target-corner tl"></div>
              <div class="rw-target-corner tr"></div>
              <div class="rw-target-corner bl"></div>
              <div class="rw-target-corner br"></div>
              <div class="rw-target-label">SAMPLE HAZARD AREA</div>
            </div>

            <!-- Bottom Data Panel with Contrast Scrim -->
            <div class="rw-hud-bottom">
              <div class="rw-meta-row">
                <div class="rw-meta-item">
                  <span class="rw-meta-label">SECTOR / ANGLE</span>
                  <span class="rw-meta-val">{safe_sector}</span>
                </div>
                <div class="rw-meta-item">
                  <span class="rw-meta-label">SURFACE DEFECT</span>
                  <span class="rw-meta-val" style="color:#FFF">{safe_defect}</span>
                </div>
                <div class="rw-meta-item">
                  <span class="rw-meta-label">LIGHTING &amp; AMBIENT</span>
                  <span class="rw-meta-val">{safe_lighting}</span>
                </div>
                <div class="rw-meta-item">
                  <span class="rw-meta-label">ILLUSTRATIVE CONDITION</span>
                  <span class="rw-meta-val" style="color:{severity_color}">{safe_condition}</span>
                </div>
              </div>
              <div class="rw-disclaimer-bar">
                <span class="rw-shield-icon">🛡️</span>
                <strong>PUBLIC SERVICE DISCLOSURE:</strong> {safe_disclaimer} · Real reports use resident-submitted evidence.
              </div>
            </div>
          </div>
        </div>
        """,
    )

    # Road Watch action toolbar
    btn_col1, btn_col2, btn_col3 = st.columns([2.2, 1.4, 1.4], vertical_alignment="center")
    with btn_col1:
        st.markdown(
            '<div class="rw-quick-copy"><strong>Citizen quick action</strong><br>'
            'Notice similar road damage? Submit a report and let local staff confirm the responsible department.</div>',
            unsafe_allow_html=True,
        )
    with btn_col2:
        if st.button(
            "＋ Report this road hazard →",
            key=f"{key_prefix}_action_report",
            type="primary",
            width="stretch",
            help="Opens the complaint submission form with Pothole service preselected",
        ):
            st.session_state["complaint_service_code"] = "S0301"
            st.session_state["portal_page"] = "Report Complaint"
            st.session_state["navigation_target"] = "Report Complaint"
            st.rerun()
    with btn_col3:
        if st.button(
            "⌖ View road repairs on map",
            key=f"{key_prefix}_action_map",
            width="stretch",
            help="Open the interactive civic map filtered to road infrastructure",
        ):
            st.session_state["portal_page"] = "Live Map"
            st.session_state["navigation_target"] = "Live Map"
            st.session_state["map_categories"] = ["Pothole"]
            st.rerun()


def render_road_sample_feed() -> None:
    """Render a compact multi-card preview grid of the 4 dashcam sample views."""
    samples = get_road_watch_samples()
    cols = st.columns(4)
    for idx, sample in enumerate(samples):
        with cols[idx]:
            img_uri = get_sample_image_base64(sample["filename"])
            safe_title = html.escape(sample["title"])
            safe_cond = html.escape(sample["condition"])
            safe_lighting = html.escape(sample["lighting"])
            safe_severity = html.escape(sample["severity"])
            color = sample.get("severity_color", "#F97316")
            st.html(
                f"""
                <div class="rw-card">
                  <div class="rw-card-thumb-wrap">
                    <img class="rw-card-thumb" src="{img_uri}" alt="{safe_title}" loading="lazy" />
                    <div class="rw-card-overlay"></div>
                    <span class="rw-card-badge" style="border-color:{color};color:{color}">{safe_severity}</span>
                  </div>
                  <div class="rw-card-body">
                    <div class="rw-card-title">{safe_title}</div>
                    <div class="rw-card-desc">{safe_cond}</div>
                    <div class="rw-card-meta">◷ {safe_lighting}</div>
                    <div class="rw-card-tag">SAMPLE VISUAL · NOT EVIDENCE</div>
                  </div>
                </div>
                """,
            )
