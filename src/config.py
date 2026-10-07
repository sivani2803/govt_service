from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT_DIR / "government_service_request_model"
APP_DATA_DIR = ROOT_DIR / "government_service_request_app"
UPLOADS_DIR = APP_DATA_DIR / "uploads"
AUTH_DATABASE_PATH = APP_DATA_DIR / "civicpulse_accounts.sqlite3"
ASSETS_DIR = ROOT_DIR / "assets"
ROAD_WATCH_ASSETS_DIR = ASSETS_DIR / "road_watch"
CIVIC_SAMPLES_DIR = ASSETS_DIR / "civic_samples"

PRIORITY_MODEL_PATH = MODEL_DIR / "priority_catboost_model.cbm"
PROJECT_CONFIG_PATH = MODEL_DIR / "project_config.pkl"
ROUTING_MAP_PATH = APP_DATA_DIR / "deployment_department_map.pkl"
FEATURE_MEDIANS_PATH = APP_DATA_DIR / "feature_medians.pkl"

SERVICE_LOOKUP_PATH = APP_DATA_DIR / "service_lookup.csv"
LIVE_COMPLAINTS_PATH = APP_DATA_DIR / "live_complaints.csv"
NOTIFICATION_HISTORY_PATH = APP_DATA_DIR / "agency_notifications.csv"
YEAR_HISTORY_PATH = APP_DATA_DIR / "historical_year.csv"
DEPARTMENT_HISTORY_PATH = APP_DATA_DIR / "historical_department.csv"
PRIORITY_HISTORY_PATH = APP_DATA_DIR / "historical_priority.csv"
DEPARTMENT_PRIORITY_HISTORY_PATH = APP_DATA_DIR / "historical_department_priority.csv"
TOP_SERVICES_PATH = APP_DATA_DIR / "top_service_categories.csv"

LIVE_COMPLAINT_COLUMNS = [
    "SERVICEREQUESTID",
    "ADDDATE",
    "SERVICECODE",
    "SERVICECODEDESCRIPTION",
    "SERVICETYPECODEDESCRIPTION",
    "DETAILS",
    "WARD",
    "ZIPCODE",
    "LATITUDE",
    "LONGITUDE",
    "PREDICTED_DEPARTMENT",
    "PREDICTED_PRIORITY",
    "HIGH_PROBABILITY",
    "LOW_PROBABILITY",
    "MEDIUM_PROBABILITY",
    "STATUS",
    "CLOSED_DATE",
    "LOCATION_METHOD",
    "LOCATION_ADDRESS",
    "CITY",
    "STATE",
    "IMAGE_PATHS",
    "IMAGE_ANNOTATIONS",
    "STATUS_HISTORY",
    "ASSIGNED_OFFICER",
    "OFFICER_NOTES",
    "INSPECTION_IMAGE_PATHS",
    "RESOLUTION_IMAGE_PATHS",
    "RESOLUTION_NOTES",
    "AI_CONFIDENCE",
    "AI_REASONS",
    "AI_VISION_TAG",
    "CITIZEN_URGENCY",
    "SLA_HOURS",
]

NOTIFICATION_COLUMNS = [
    "NOTIFICATION_ID",
    "SERVICEREQUESTID",
    "AGENCY",
    "PRIORITY",
    "SERVICE_CODE",
    "SERVICE_DESCRIPTION",
    "MESSAGE",
    "NOTIFICATION_TIME",
    "NOTIFICATION_STATUS",
]

REQUEST_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]

CIVIC_COLORS = {
    "bg_primary": "#080E18",
    "panel_bg": "#0E1726",
    "panel_alt": "#142033",
    "border": "rgba(255,255,255,0.10)",
    "text_primary": "#F1F5F9",
    "text_muted": "#94A3B8",
    "safety_orange": "#F97316",
    "signal_yellow": "#EAB308",
    "ops_blue": "#38BDF8",
    "civic_emerald": "#0F766E",
    "civic_teal": "#0D9488",
    "success": "#10B981",
    "warning": "#F59E0B",
    "priority_high": "#EF4444",
    "info": "#38BDF8",
}

MODEL_INFO = {
    "priority_metrics": {
        "Test accuracy": "99.68%",
        "Macro precision": "76.22%",
        "Macro recall": "79.54%",
        "Macro F1": "77.70%",
        "Weighted F1": "99.70%",
    },
    "routing_metrics": {
        "Accuracy": "100%",
        "Macro F1": "1.00",
        "Weighted F1": "1.00",
        "Unseen test codes": "0",
    },
}
