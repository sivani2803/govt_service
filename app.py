from __future__ import annotations

import json
import html
import re
import warnings
from io import BytesIO
from datetime import datetime
from urllib.parse import quote_plus

import pandas as pd
import folium
import plotly.express as px
import streamlit as st
from PIL import Image
from plotly.graph_objects import Figure
from streamlit_folium import st_folium

from src.config import (
    APP_DATA_DIR,
    DEPARTMENT_HISTORY_PATH,
    DEPARTMENT_PRIORITY_HISTORY_PATH,
    MODEL_INFO,
    PRIORITY_HISTORY_PATH,
    SERVICE_LOOKUP_PATH,
    TOP_SERVICES_PATH,
    YEAR_HISTORY_PATH,
)
from src.location import browser_location
from src.notifications import create_agency_notification
from src.predictor import load_predictor_assets, predict_priority
from src.routing import load_routing_map, route_department
from src.storage import (
    add_complaint,
    get_complaint,
    get_complaint_image_paths,
    list_complaints,
    list_notifications,
    update_complaint_status,
)

st.set_page_config(
    page_title="Government Service Request System",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
      --navy: #112f50; --blue: #1769aa; --blue-dark: #0e4d82; --ink: #172b40;
      --muted: #63768a; --line: #e3eaf1; --canvas: #f3f6fa; --white: #fff;
      --green: #18794e; --amber: #956000; --red: #a52a2a;
    }
    html, body, [class*="css"] { font-family: "Segoe UI", "Inter", Arial, sans-serif; color: var(--ink); }
    .stApp { background: var(--canvas); }
    [data-testid="stHeader"] { height: 2.1rem; background: transparent; }
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
    [data-testid="stToolbar"], #MainMenu, footer { visibility: hidden; }
    [data-testid="stMainBlockContainer"] { max-width: 1440px; padding: 1.25rem 2.3rem 4rem; }
    h1, h2, h3, h4 { color: var(--ink); letter-spacing: -.025em; }
    h1 { font-size: 1.9rem !important; font-weight: 720 !important; }
    h2 { font-size: 1.35rem !important; font-weight: 700 !important; }
    h3 { font-size: 1.07rem !important; font-weight: 680 !important; }
    p, [data-testid="stMarkdownContainer"] { color: #344b62; }
    [data-testid="stCaptionContainer"] { color: var(--muted); }
    .block-container { padding-top: 1rem; }
    .app-brand {
      display:flex; align-items:center; gap:15px; min-height:67px;
    }
    .brand-seal {
      width:52px; height:52px; border-radius:16px; display:flex; align-items:center;
      justify-content:center; background:#eaf2f9; color:#123f68; border:1px solid #d6e4f0;
      font-size:25px; box-shadow:0 2px 7px rgba(17,47,80,.07);
    }
    .brand-name { font-size:19px; line-height:1.2; font-weight:750; color:var(--navy); }
    .brand-subtitle { font-size:12px; color:#677c90; margin-top:5px; letter-spacing:.015em; }
    .brand-utility { text-align:right; color:#526a80; font-size:12px; line-height:1.65; }
    .brand-utility strong { color:var(--navy); }
    .brand-utility .live-dot { color:#188355; font-size:15px; vertical-align:-1px; }
    .top-rule { height:1px; background:var(--line); margin:.55rem 0 .35rem; }
    [data-testid="stRadio"] [role="radiogroup"] { gap:7px; flex-wrap:wrap; }
    [data-testid="stRadio"] label[data-testid="stRadioOption"] {
      border:1px solid transparent; border-radius:9px; background:transparent;
      padding:8px 13px; transition:all .15s ease; min-height:39px;
    }
    [data-testid="stRadio"] label[data-testid="stRadioOption"]:hover {
      background:#e9f1f8; border-color:#dce7f0;
    }
    [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div:first-child { display:none; }
    [data-testid="stRadio"] label[data-testid="stRadioOption"] > div { display:flex; align-items:center; }
    [data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) {
      color:#fff; background:var(--navy); border-color:var(--navy);
      box-shadow:0 3px 8px rgba(17,47,80,.14);
    }
    [data-testid="stRadio"] label[data-testid="stRadioOption"] p { margin:0; color:#39536c; font-size:13px; font-weight:650; white-space:nowrap; }
    [data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) p { color:#fff; }
    .portal-banner {
      position:relative; overflow:hidden;
      background:linear-gradient(112deg,#102f50 0%,#164b77 58%,#1d648f 100%);
      color:white; padding:1.55rem 1.85rem; border-radius:16px;
      margin:.3rem 0 1.4rem; box-shadow:0 10px 26px rgba(17,47,80,.14);
    }
    .portal-banner:after {
      content:""; position:absolute; width:270px; height:270px; border:1px solid rgba(255,255,255,.12);
      border-radius:50%; right:-70px; top:-145px; box-shadow:0 0 0 32px rgba(255,255,255,.035),0 0 0 66px rgba(255,255,255,.025);
    }
    .portal-banner {
      color:white;
    }
    .portal-banner h1 { color:white; font-size:1.72rem !important; margin:0 0 .38rem; font-weight:740 !important; }
    .portal-banner p { color:#d7e6f3; margin:0; font-size:.97rem; max-width:760px; }
    .eyebrow { color:#668099; font-size:.72rem; font-weight:750; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.45rem; }
    .hero-panel {
      position:relative; overflow:hidden; border-radius:20px; padding:2.05rem 2.2rem;
      background:linear-gradient(112deg,#102f50,#185782); color:white;
      box-shadow:0 13px 30px rgba(17,47,80,.16); margin:.3rem 0 1.45rem;
    }
    .hero-panel:after { content:""; position:absolute; width:330px; height:330px; right:-80px; top:-210px; border:1px solid rgba(255,255,255,.14); border-radius:50%; box-shadow:0 0 0 35px rgba(255,255,255,.035),0 0 0 72px rgba(255,255,255,.025); }
    .hero-kicker { color:#b9d6eb; text-transform:uppercase; letter-spacing:.14em; font-size:.72rem; font-weight:700; }
    .hero-title { color:white; font-size:2rem; line-height:1.18; font-weight:760; letter-spacing:-.035em; margin:.45rem 0 .55rem; }
    .hero-copy { color:#d5e5f1; font-size:.96rem; max-width:640px; line-height:1.6; }
    .section-heading { display:flex; align-items:center; gap:10px; margin:.35rem 0 .8rem; }
    .section-heading h2 { margin:0; }
    .section-kicker { font-size:.75rem; font-weight:700; color:#6e8397; text-transform:uppercase; letter-spacing:.1em; }
    [data-testid="stMetric"] {
      background:var(--white); border:1px solid var(--line); border-radius:13px;
      padding:15px 17px; min-height:90px; box-shadow:0 2px 8px rgba(24,49,73,.035);
    }
    [data-testid="stMetricLabel"] p { color:#64788c !important; font-weight:600 !important; font-size:.8rem !important; }
    [data-testid="stMetricValue"] { color:var(--navy) !important; font-weight:750; font-size:1.6rem !important; }
    [data-testid="stPlotlyChart"] { background:#fff; border:1px solid var(--line); border-radius:14px; padding:8px; box-shadow:0 3px 12px rgba(24,49,73,.04); margin:.15rem 0 .8rem; }
    [data-testid="stForm"] { background:#fff; border:1px solid var(--line); border-radius:15px; padding:1.15rem 1.3rem 1.25rem; box-shadow:0 4px 14px rgba(24,49,73,.045); }
    [data-testid="stTextInput"] input:not(:disabled),
    [data-testid="stTextArea"] textarea:not(:disabled),
    [data-testid="stDateInput"] input:not(:disabled),
    [data-testid="stTimeInput"] input:not(:disabled) {
      color:#172b40 !important; -webkit-text-fill-color:#172b40 !important;
      caret-color:#112f50 !important; background-color:#fff !important; opacity:1 !important;
    }
    [data-testid="stTextInput"] input:not(:disabled)::placeholder,
    [data-testid="stTextArea"] textarea:not(:disabled)::placeholder,
    [data-testid="stDateInput"] input:not(:disabled)::placeholder,
    [data-testid="stTimeInput"] input:not(:disabled)::placeholder {
      color:#68798a !important; -webkit-text-fill-color:#68798a !important; opacity:1 !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
      border-radius:9px !important; border-color:#d5dfe8 !important; background:#fff !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] div,
    [data-testid="stSelectbox"] [data-baseweb="select"] input {
      color:#172b40 !important; -webkit-text-fill-color:#172b40 !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] input::placeholder {
      color:#68798a !important; -webkit-text-fill-color:#68798a !important; opacity:1 !important;
    }
    [data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
    [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within,
    [data-testid="stDateInput"] [data-baseweb="input"]:focus-within,
    [data-testid="stTimeInput"] [data-baseweb="input"]:focus-within,
    [data-testid="stSelectbox"] [data-baseweb="select"]:focus-within {
      border-color:#2879ad !important; box-shadow:0 0 0 2px rgba(23,105,170,.18) !important;
    }
    [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button {
      border-radius:9px; min-height:42px; font-weight:670; transition:all .15s ease;
    }
    [data-testid="stButton"] button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
      background:var(--blue); border-color:var(--blue); box-shadow:0 3px 8px rgba(23,105,170,.16);
    }
    [data-testid="stButton"] button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover { background:var(--blue-dark); border-color:var(--blue-dark); }
    [data-testid="stLinkButton"] a { border-radius:9px; font-weight:650; }
    [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
    .priority-high,.priority-medium,.priority-low,.status-badge {
      display:inline-flex; align-items:center; border-radius:999px; padding:.3rem .7rem;
      font-size:.77rem; font-weight:750; line-height:1.2; white-space:nowrap;
    }
    .priority-high { background:#fce8e8; color:var(--red); }
    .priority-medium { background:#fff2d6; color:var(--amber); }
    .priority-low { background:#e5f4eb; color:var(--green); }
    .status-open { background:#e9f1f8; color:#285d86; }
    .status-progress { background:#fff2d6; color:#805800; }
    .status-resolved,.status-closed { background:#e5f4eb; color:#176642; }
    .location-callout { border:1px solid #cfe0ee; border-left:4px solid #2873a8; border-radius:12px; background:#f3f8fc; padding:1rem 1.1rem; margin:.65rem 0; }
    .location-callout strong { color:#173c5e; }
    .case-card { background:#fff; border:1px solid var(--line); border-radius:14px; padding:1rem 1.15rem; margin:.55rem 0; box-shadow:0 3px 10px rgba(24,49,73,.04); }
    .case-id { color:#1b5e90; font-weight:750; font-size:.88rem; }
    .case-title { color:var(--navy); font-weight:700; font-size:1rem; margin:.34rem 0; }
    .case-meta { color:#687d91; font-size:.81rem; line-height:1.6; }
    .empty-state { text-align:center; background:#fff; border:1px dashed #cbd8e4; border-radius:16px; padding:2.3rem 1.4rem; margin:.8rem 0; }
    .empty-icon { font-size:2rem; margin-bottom:.4rem; }
    .empty-title { color:var(--navy); font-weight:720; font-size:1.05rem; }
    .empty-copy { color:#6b7f91; max-width:470px; margin:.35rem auto 0; line-height:1.55; font-size:.9rem; }
    .timeline { display:flex; align-items:flex-start; width:100%; margin:1.35rem 0 1.6rem; }
    .timeline-step { position:relative; flex:1; text-align:center; padding:0 3px; color:#7a8b9c; font-size:.75rem; font-weight:620; }
    .timeline-step:not(:last-child):after { content:""; position:absolute; left:calc(50% + 15px); right:calc(-50% + 15px); top:13px; height:2px; background:#d9e2ea; }
    .timeline-step.complete:not(:last-child):after { background:#23835b; }
    .timeline-dot { position:relative; z-index:1; width:27px; height:27px; border:2px solid #d3dee7; border-radius:50%; background:#fff; margin:0 auto 8px; display:flex; align-items:center; justify-content:center; font-size:.69rem; }
    .timeline-step.complete { color:#286c4c; }
    .timeline-step.complete .timeline-dot { border-color:#23835b; background:#e8f5ee; color:#18794e; }
    .timeline-step.current { color:#174e79; font-weight:750; }
    .timeline-step.current .timeline-dot { border-color:#1769aa; background:#1769aa; color:#fff; box-shadow:0 0 0 4px #e4f0f8; }
    .success-panel { background:linear-gradient(135deg,#eef8f2,#fff); border:1px solid #cfe7d8; border-radius:17px; padding:1.4rem 1.5rem; margin:.8rem 0 1rem; }
    .success-title { color:#176642; font-size:1.35rem; font-weight:760; }
    .helper-panel { background:#edf5fb; border:1px solid #d8e8f4; border-radius:12px; padding:.9rem 1rem; color:#345873; font-size:.88rem; line-height:1.55; margin:.4rem 0 .9rem; }
    [data-testid="stAlert"] { border-radius:11px; }
    @media (max-width:900px) {
      [data-testid="stMainBlockContainer"] { padding:.6rem 1rem 3rem; }
      [data-testid="stRadio"] label[data-testid="stRadioOption"] { padding:7px 8px; }
      [data-testid="stRadio"] label[data-testid="stRadioOption"] p { font-size:11px; }
      .hero-title { font-size:1.65rem; }
    }
    @media (max-width:620px) {
      [data-testid="stMainBlockContainer"] { padding:.4rem .75rem 2.4rem; }
      .brand-name { font-size:16px; }
      .brand-seal { width:43px; height:43px; }
      .brand-utility { font-size:10px; }
      .portal-banner { padding:1.2rem 1.25rem; }
      .timeline-step { font-size:.62rem; }
      .timeline-dot { width:23px; height:23px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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
    if frame.empty:
        raise ValueError("No service categories have a saved department route.")
    return frame.drop_duplicates("SERVICECODE").sort_values("SERVICECODEDESCRIPTION", kind="stable")


def _header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="portal-banner"><div class="eyebrow" style="color:#b9d5ee">DISTRICT SERVICE REQUEST SYSTEM</div>'
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
        "Open": "status-open",
        "In Progress": "status-progress",
        "Resolved": "status-resolved",
        "Closed": "status-closed",
    }.get(status, "status-open")
    return f'<span class="status-badge {style}">{html.escape(status)}</span>'


def _case_card(request: pd.Series | dict[str, object]) -> None:
    request_id = html.escape(str(request.get("SERVICEREQUESTID", "")))
    service = html.escape(str(request.get("SERVICECODEDESCRIPTION", "Service request")))
    place = html.escape(
        ", ".join(
            str(request.get(key, "")).strip()
            for key in ("LOCATION_ADDRESS", "CITY", "STATE")
            if str(request.get(key, "")).strip()
        )
    )
    pincode = html.escape(str(request.get("ZIPCODE", "")).strip())
    department = html.escape(str(request.get("PREDICTED_DEPARTMENT", "Unassigned")))
    submitted = html.escape(str(request.get("ADDDATE", "")))
    st.markdown(
        f'<div class="case-card"><div class="case-id">{request_id}</div>'
        f'<div class="case-title">{service}</div>'
        f'<div class="case-meta">{_priority_badge(str(request.get("PREDICTED_PRIORITY", "")))}'
        f' &nbsp; {_status_badge(str(request.get("STATUS", "Open")))}</div>'
        f'<div class="case-meta" style="margin-top:9px">⌖ &nbsp;{place or "Location recorded"}'
        f'{f" · PIN {pincode}" if pincode else ""}'
        f'<br>▣ &nbsp;{department} &nbsp; · &nbsp; ◷ &nbsp;{submitted}</div></div>',
        unsafe_allow_html=True,
    )


def _read_summary(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def _render_chart(figure: Figure) -> None:
    figure.update_layout(
        template="plotly_white",
        height=340,
        margin={"l": 20, "r": 20, "t": 55, "b": 30},
        title={"x": 0.03, "xanchor": "left", "font": {"size": 15, "color": "#173b5b"}},
        font={"family": "Segoe UI, Arial, sans-serif", "color": "#526a80", "size": 11},
        xaxis={"tickfont": {"color": "#526a80"}, "title_font": {"color": "#526a80"}, "gridcolor": "#edf1f5"},
        yaxis={"tickfont": {"color": "#526a80"}, "title_font": {"color": "#526a80"}, "gridcolor": "#edf1f5"},
        legend={"font": {"color": "#526a80"}},
        coloraxis_colorbar={
            "title": {"font": {"color": "#526a80"}},
            "tickfont": {"color": "#526a80"},
        },
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config={"displayModeBar": False, "responsive": True},
    )


def _priority_badge(priority: str) -> str:
    normalized = str(priority).strip().lower()
    style = {
        "high": "priority-high",
        "medium": "priority-medium",
        "low": "priority-low",
    }.get(normalized, "priority-medium")
    return f'<span class="{style}">{priority}</span>'


def _location_map_url(latitude: object, longitude: object, address: str = "") -> str | None:
    if pd.notna(latitude) and pd.notna(longitude) and str(latitude) and str(longitude):
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(f'{latitude},{longitude}')}"
    if address.strip():
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}"
    return None


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

    photo_columns = st.columns(min(3, len(image_paths)))
    for index, image_path in enumerate(image_paths):
        column = photo_columns[index % len(photo_columns)]
        column.image(
            str(image_path),
            caption=f"Problem photo {index + 1}",
            width="stretch",
        )
        if column.button(
            "View larger",
            key=f"{key_prefix}_photo_{index}",
            width="stretch",
        ):
            _show_problem_photo(str(image_path), f"Problem photo {index + 1}")


def citizen_dashboard() -> None:
    st.markdown(
        '<div class="hero-panel"><div class="hero-kicker">A simpler way to reach your city</div>'
        '<div class="hero-title">Report. Track. Resolve.</div>'
        '<div class="hero-copy">Report government service issues, see which department is responsible, '
        'and follow every update from submission to resolution.</div></div>',
        unsafe_allow_html=True,
    )
    complaints = list_complaints()
    total = len(complaints)
    open_count = int((complaints["STATUS"] == "Open").sum()) if total else 0
    active_count = int((complaints["STATUS"] == "In Progress").sum()) if total else 0
    resolved_count = int((complaints["STATUS"] == "Resolved").sum()) if total else 0
    closed_count = int((complaints["STATUS"] == "Closed").sum()) if total else 0
    cols = st.columns(4)
    for col, label, value in zip(
        cols,
        ["Open requests", "In progress", "Resolved", "Closed"],
        [open_count, active_count, resolved_count, closed_count],
    ):
        col.metric(label, f"{value:,}")

    _section_title("Get started", "SERVICES")
    actions = st.columns(3)
    action_specs = [
        ("＋", "Report a complaint", "Tell us what needs attention and where it occurred.", "report"),
        ("◷", "Track my request", "See your assigned department, status, and location.", "track"),
        ("ⓘ", "Service information", "Learn how routing and priority estimates work.", "info"),
    ]
    for col, (icon, title, copy, action) in zip(actions, action_specs):
        with col:
            st.markdown(
                f'<div class="case-card" style="min-height:119px"><div style="font-size:1.35rem;color:#1769aa">{icon}</div>'
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

    _section_title("Recent requests", "YOUR ACTIVITY")
    if total:
        recent = complaints.sort_values("ADDDATE", ascending=False).head(5)
        for _, request in recent.iterrows():
            _case_card(request)
        if st.button("View request tracking", width="content"):
            _go_to_page("Track Complaint")
            st.rerun()
    else:
        _empty_state(
            "No service requests yet",
            "When you submit a complaint, it will appear here with its assigned department and current status.",
            "⌂",
        )


def report_complaint(services: pd.DataFrame) -> None:
    _header("Report a complaint", "Tell us what needs attention and where the service request occurred.")
    if st.session_state.get("last_submission"):
        result = st.session_state["last_submission"]
        st.markdown(
            '<div class="success-panel"><div class="success-title">✓ &nbsp;Your request is on its way</div>'
            '<div style="color:#456c56;margin-top:5px">Your complaint has been recorded and routed to the responsible department.</div></div>',
            unsafe_allow_html=True,
        )
        if result.get("notification_error"):
            st.warning(
                f"Your request is saved, but its agency inbox notification could not be recorded: "
                f"{result['notification_error']}"
            )
        else:
            st.success("Agency inbox notification created.")
        st.markdown(f"### Request **{html.escape(result['request_id'])}**")
        result_cols = st.columns(4)
        result_cols[0].metric("Request ID", result["request_id"])
        result_cols[1].metric("Assigned department", result["department"])
        result_cols[2].markdown(
            f"**Predicted priority**<br>{_priority_badge(result['priority'])}",
            unsafe_allow_html=True,
        )
        result_cols[3].markdown(
            f"**Current status**<br>{_status_badge('Open')}",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="location-callout"><strong>⌖ &nbsp;Reported location</strong><br>'
            f'{html.escape(result["address"])}, {html.escape(result["city"])}, '
            f'{html.escape(result["state"])} · PIN {html.escape(result["pincode"])}</div>',
            unsafe_allow_html=True,
        )
        if result.get("latitude") is not None and result.get("longitude") is not None:
            st.caption(f"Coordinates: {result['latitude']}, {result['longitude']}")
        if st.button("＋  Submit another complaint", type="primary"):
            st.session_state.pop("last_submission", None)
            st.rerun()
        return

    st.markdown(
        '<div class="helper-panel"><strong>⌖ &nbsp;Location is required</strong> because the responsible '
        'department depends on where the issue occurred. Your address is required even when GPS is available. '
        'Coordinates are optional; you can still submit manually if location services are unavailable.</div>',
        unsafe_allow_html=True,
    )
    service_codes = [""] + services["SERVICECODE"].tolist()
    coordinates: tuple[float, float] | None = st.session_state.get(
        "complaint_selected_coordinates"
    )
    coordinates_are_valid = True

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
            st.text_input(
                "Service description",
                value=str(service_preview["SERVICECODEDESCRIPTION"]),
                disabled=True,
                key="service_type_preview",
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
            f"Responsible department: {route_department(service_code)}"
        )
    details = st.text_area(
        "Complaint details *",
        placeholder="Describe what happened, when it occurred, and anything that may help the agency respond.",
        height=125,
        max_chars=3000,
        key="complaint_details",
    )
    _section_title("Photos of the Problem (Optional)", "OPTIONAL")
    st.caption("Upload clear photos showing the issue. These photos will be visible to the assigned agency.")
    st.caption("Upload up to 5 JPG, JPEG, or PNG images (maximum 5 MB each). Remove a file from the upload list before submitting.")
    uploaded_files = st.file_uploader(
        "Add problem photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        max_upload_size=5,
        key="complaint_problem_photos",
    )
    uploaded_images: list[tuple[str, bytes]] = []
    uploaded_image_names: list[str] = []
    image_validation_errors: list[str] = []
    selected_files = uploaded_files or []
    if len(selected_files) > 5:
        image_validation_errors.append("A maximum of 5 photos may be attached to one complaint.")
    for uploaded_file in selected_files:
        image_data = uploaded_file.getvalue()
        if uploaded_file.size > 5 * 1024 * 1024:
            image_validation_errors.append(f"{uploaded_file.name} exceeds the 5 MB per-image limit.")
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(image_data)) as image:
                    image_format = image.format
                    if image_format not in {"JPEG", "PNG"}:
                        raise ValueError("Only JPG, JPEG, and PNG image content is accepted.")
                    if image.width * image.height > 25_000_000:
                        raise ValueError("The image dimensions exceed the supported limit.")
                    image.verify()
        except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            image_validation_errors.append(f"{uploaded_file.name} is not a supported image: {exc}")
            continue
        extension = "png" if image_format == "PNG" else "jpg"
        uploaded_images.append((extension, image_data))
        uploaded_image_names.append(uploaded_file.name)

    for image_error in image_validation_errors:
        st.error(image_error)
    if uploaded_images:
        preview_columns = st.columns(min(3, len(uploaded_images)))
        for index, ((_, image_data), filename) in enumerate(zip(uploaded_images, uploaded_image_names)):
            preview_columns[index % len(preview_columns)].image(
                image_data,
                caption=filename,
                width="stretch",
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
    address_parts = [address.strip(), city.strip(), state.strip(), pincode.strip()]
    pincode_is_valid = bool(re.fullmatch(r"[1-9]\d{5}", pincode.strip()))
    address_is_complete = all(address_parts)

    _section_title("Pick Exact Location (Optional)", "OPTIONAL")
    st.caption(
        "Click anywhere on the map to place a pin. The required address remains sufficient "
        "to submit if you do not need exact coordinates."
    )
    gps = browser_location(key="complaint_browser_location")
    if isinstance(gps, dict) and gps.get("latitude") is not None and gps.get("longitude") is not None:
        browser_coordinates = (float(gps["latitude"]), float(gps["longitude"]))
        if browser_coordinates != st.session_state.get("_last_browser_location"):
            st.session_state["complaint_selected_coordinates"] = browser_coordinates
            st.session_state["complaint_location_method"] = "Browser GPS"
            st.session_state["_last_browser_location"] = browser_coordinates
            coordinates = browser_coordinates
    india_center = (20.5937, 78.9629)
    map_object = folium.Map(
        location=coordinates or india_center,
        zoom_start=14 if coordinates else 5,
        tiles="OpenStreetMap",
        control_scale=True,
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
        if not coordinates_are_valid:
            st.caption("Correct the coordinates or clear both optional coordinate fields.")
        elif not form_is_valid:
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
        "WARD": "",
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
        department = route_department(str(service["SERVICECODE"]))
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
        }
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
        "department": department,
        "priority": priority,
        "address": address.strip(),
        "city": city.strip(),
        "state": state.strip(),
        "pincode": pincode.strip(),
        "latitude": latitude,
        "longitude": longitude,
        "notification_error": str(notification_error) if notification_error is not None else "",
    }
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
    stage_for_status = {"Open": 2, "In Progress": 3, "Resolved": 4, "Closed": 5}
    current_stage = stage_for_status.get(status, 0)
    event_by_name = {event.get("event"): event.get("timestamp", "") for event in events}
    steps = [
        "Submitted",
        "Department Assigned",
        "Agency Notified",
        "In Progress",
        "Resolved",
        "Closed",
    ]
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
        if index <= 2 and current_stage >= 2 and not timestamp:
            timestamp = "Recorded"
        detail = html.escape(timestamp) if timestamp else ("Current stage" if current else "Pending")
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


def agency_portal() -> None:
    _header("Agency inbox", "Review newly routed complaints, inspect reported locations, and keep request status current.")
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
    ordered = complaints.sort_values("ADDDATE", ascending=False)
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

    _section_title("Update case status", "CASE MANAGEMENT")
    statuses = ["Open", "In Progress", "Resolved", "Closed"]
    current_status = complaint["STATUS"] if complaint["STATUS"] in statuses else "Open"
    with st.form("agency_status_form"):
        new_status = st.selectbox("Status", statuses, index=statuses.index(current_status))
        changed = st.form_submit_button("Save status update", type="primary")
    if changed:
        try:
            updated = update_complaint_status(selected_id, new_status)
            if updated is None:
                st.error("The request was not found; no status was changed.")
            else:
                st.success(
                    f"Status updated to {new_status}."
                    + (f" Closed date: {updated['CLOSED_DATE']}." if new_status == "Closed" else "")
                )
                st.rerun()
        except (OSError, ValueError, RuntimeError) as exc:
            st.error(f"Status update failed: {exc}")


def admin_dashboard() -> None:
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


def main() -> None:
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
        "Agency Portal": "▤  Agency inbox",
        "Admin Dashboard": "▥  Analytics",
        "Model Information": "ⓘ  Model insights",
    }
    label_pages = {label: page for page, label in page_labels.items()}
    current_page = st.session_state.get("portal_page", "Citizen Dashboard")
    navigation_target = st.session_state.pop("navigation_target", None)
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

    brand_col, utility_col = st.columns([3.3, 1.5], vertical_alignment="center")
    with brand_col:
        st.markdown(
            '<div class="app-brand"><div class="brand-seal">🏛</div><div>'
            '<div class="brand-name">Government Service Request System</div>'
            '<div class="brand-subtitle">CITIZEN SERVICES &nbsp;·&nbsp; LOCAL DEMO PORTAL</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
    with utility_col:
        st.markdown(
            f'<div class="brand-utility"><span class="live-dot">●</span> &nbsp;LOCAL DEMO PORTAL'
            f'<br><strong>Public access</strong> &nbsp;·&nbsp; 🔔 {new_count} new agency notices</div>',
            unsafe_allow_html=True,
        )
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

    try:
        if page == "Citizen Dashboard":
            citizen_dashboard()
        elif page == "Report Complaint":
            report_complaint(services)
        elif page == "Track Complaint":
            show_tracking(st.session_state.get("tracking_id", ""))
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
