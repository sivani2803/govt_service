from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT_DIR / "government_service_request_model"
APP_DATA_DIR = ROOT_DIR / "government_service_request_app"
UPLOADS_DIR = APP_DATA_DIR / "uploads"

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
    "STATUS_HISTORY",
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
