from __future__ import annotations

from datetime import datetime
from secrets import token_hex
from typing import Any

from src.config import NOTIFICATION_COLUMNS
from src.storage import append_csv_record


def create_agency_notification(
    complaint: dict[str, Any],
    message: str = "New service request submitted and routed for agency review.",
) -> dict[str, str]:
    notification_time = datetime.now().astimezone().isoformat(timespec="seconds")
    notification = {
        "NOTIFICATION_ID": f"NTF-{token_hex(5).upper()}",
        "SERVICEREQUESTID": str(complaint["SERVICEREQUESTID"]),
        "AGENCY": str(complaint["PREDICTED_DEPARTMENT"]),
        "PRIORITY": str(complaint["PREDICTED_PRIORITY"]),
        "SERVICE_CODE": str(complaint["SERVICECODE"]),
        "SERVICE_DESCRIPTION": str(complaint["SERVICECODEDESCRIPTION"]),
        "MESSAGE": str(message),
        "NOTIFICATION_TIME": notification_time,
        "NOTIFICATION_STATUS": "New",
    }
    append_csv_record(NOTIFICATION_COLUMNS, notification)
    return notification
