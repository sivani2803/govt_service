from __future__ import annotations

import json
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    APP_DATA_DIR,
    LIVE_COMPLAINTS_PATH,
    LIVE_COMPLAINT_COLUMNS,
    NOTIFICATION_COLUMNS,
    NOTIFICATION_HISTORY_PATH,
    UPLOADS_DIR,
)


def _read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=columns).to_csv(path, index=False)
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"CSV storage has no header row: {path}") from exc
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame


def _write_csv_atomic(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    try:
        frame.to_csv(temporary_path, index=False)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _read_complaints() -> pd.DataFrame:
    return _read_csv(LIVE_COMPLAINTS_PATH, LIVE_COMPLAINT_COLUMNS)


def _read_notifications() -> pd.DataFrame:
    return _read_csv(NOTIFICATION_HISTORY_PATH, NOTIFICATION_COLUMNS)


def append_csv_record(columns: list[str], record: dict[str, Any]) -> None:
    if columns == NOTIFICATION_COLUMNS:
        path = NOTIFICATION_HISTORY_PATH
    elif columns == LIVE_COMPLAINT_COLUMNS:
        path = LIVE_COMPLAINTS_PATH
    else:
        raise ValueError("No local CSV storage path is configured for the requested record type.")
    frame = _read_csv(path, columns)
    for column in record:
        if column not in frame.columns:
            frame[column] = ""
    frame = pd.concat([frame, pd.DataFrame([{**{column: "" for column in frame.columns}, **record}])], ignore_index=True)
    _write_csv_atomic(path, frame)


def list_complaints() -> pd.DataFrame:
    return _read_complaints()


def get_complaint(request_id: str) -> dict[str, str] | None:
    frame = _read_complaints()
    matches = frame[frame["SERVICEREQUESTID"].astype(str) == str(request_id)]
    if matches.empty:
        return None
    return {key: str(value) for key, value in matches.iloc[-1].to_dict().items()}


def list_notifications() -> pd.DataFrame:
    return _read_notifications()


def _new_request_id(submitted_at: datetime, existing: set[str]) -> str:
    while True:
        candidate = f"GSR-{submitted_at:%Y%m%d}-{secrets.token_hex(3).upper()}"
        if candidate not in existing:
            return candidate


def add_complaint(
    complaint: dict[str, Any],
    submitted_at: datetime,
    image_files: list[tuple[str, bytes]] | None = None,
) -> dict[str, str]:
    frame = _read_complaints()
    existing = set(frame["SERVICEREQUESTID"].astype(str))
    request_id = _new_request_id(submitted_at, existing)
    timestamp = submitted_at.isoformat(timespec="seconds")
    history = [
        {"event": "Submitted", "timestamp": timestamp},
        {"event": "Department Assigned", "timestamp": timestamp},
        {"event": "Agency Notified", "timestamp": timestamp},
    ]
    image_directory = UPLOADS_DIR / request_id
    image_directory_created = False
    image_paths: list[str] = []
    row: dict[str, Any] = {
        **complaint,
        "SERVICEREQUESTID": request_id,
        "ADDDATE": timestamp,
        "CLOSED_DATE": "",
        "IMAGE_PATHS": "[]",
        "STATUS_HISTORY": json.dumps(history, separators=(",", ":")),
    }
    columns = list(frame.columns)
    for column in row:
        if column not in columns:
            columns.append(column)
    frame = frame.reindex(columns=columns)
    frame = pd.concat([frame, pd.DataFrame([{column: row.get(column, "") for column in columns}])], ignore_index=True)

    try:
        if image_files:
            image_directory.mkdir(parents=True, exist_ok=False)
            image_directory_created = True
            for extension, image_data in image_files:
                normalized_extension = extension.lower().lstrip(".")
                if normalized_extension not in {"jpg", "jpeg", "png"}:
                    raise ValueError(f"Unsupported uploaded image extension: {extension}")
                filename = f"{secrets.token_hex(8)}.{normalized_extension}"
                image_path = image_directory / filename
                with image_path.open("xb") as image_file:
                    image_file.write(image_data)
                image_paths.append(image_path.relative_to(APP_DATA_DIR).as_posix())

        row["IMAGE_PATHS"] = json.dumps(image_paths, separators=(",", ":"))
        frame.at[frame.index[-1], "IMAGE_PATHS"] = row["IMAGE_PATHS"]
        _write_csv_atomic(LIVE_COMPLAINTS_PATH, frame)
    except (OSError, ValueError, RuntimeError, pd.errors.ParserError):
        if image_directory_created and image_directory.exists():
            shutil.rmtree(image_directory)
        raise
    return {key: str(value) for key, value in row.items()}


def get_complaint_image_paths(complaint: dict[str, str]) -> list[Path]:
    raw_paths = complaint.get("IMAGE_PATHS", "")
    if not raw_paths:
        return []
    try:
        stored_paths = json.loads(raw_paths)
    except json.JSONDecodeError as exc:
        raise ValueError("The stored problem photo paths are malformed.") from exc
    if not isinstance(stored_paths, list) or not all(isinstance(path, str) for path in stored_paths):
        raise ValueError("The stored problem photo paths have an unexpected format.")

    uploads_root = UPLOADS_DIR.resolve()
    resolved_paths: list[Path] = []
    for stored_path in stored_paths:
        image_path = (APP_DATA_DIR / stored_path).resolve()
        if not image_path.is_relative_to(uploads_root):
            raise ValueError("A stored problem photo path points outside the uploads directory.")
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("A stored problem photo has an unsupported file type.")
        if not image_path.is_file():
            raise FileNotFoundError(f"A stored problem photo could not be found: {image_path}")
        resolved_paths.append(image_path)
    return resolved_paths


def update_complaint_status(request_id: str, status: str) -> dict[str, str] | None:
    allowed_statuses = {"Open", "In Progress", "Resolved", "Closed"}
    if status not in allowed_statuses:
        raise ValueError(f"Unsupported complaint status: {status}")
    frame = _read_complaints()
    matches = frame.index[frame["SERVICEREQUESTID"].astype(str) == str(request_id)].tolist()
    if not matches:
        return None
    index = matches[-1]
    current_status = frame.at[index, "STATUS"]
    if current_status != status:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            history = json.loads(frame.at[index, "STATUS_HISTORY"] or "[]")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Status history for request {request_id} is invalid JSON.") from exc
        history.append({"event": status, "timestamp": now})
        frame.at[index, "STATUS_HISTORY"] = json.dumps(history, separators=(",", ":"))
        frame.at[index, "STATUS"] = status
        if status == "Closed" and not frame.at[index, "CLOSED_DATE"]:
            frame.at[index, "CLOSED_DATE"] = now
        _write_csv_atomic(LIVE_COMPLAINTS_PATH, frame)
    return {key: str(value) for key, value in frame.loc[index].to_dict().items()}
