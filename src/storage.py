from __future__ import annotations

import json
import secrets
import shutil
import warnings
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image

from src.config import (
    APP_DATA_DIR,
    LIVE_COMPLAINTS_PATH,
    LIVE_COMPLAINT_COLUMNS,
    NOTIFICATION_COLUMNS,
    NOTIFICATION_HISTORY_PATH,
    UPLOADS_DIR,
)

_IMAGE_FORMATS = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_IMAGE_PIXELS = 25_000_000


def _validate_image_data(extension: str, image_data: bytes) -> str:
    normalized_extension = extension.lower().lstrip(".")
    expected_format = _IMAGE_FORMATS.get(normalized_extension)
    if expected_format is None:
        raise ValueError(f"Unsupported uploaded image extension: {extension}")
    if not isinstance(image_data, bytes) or not image_data:
        raise ValueError("Uploaded image data is empty.")
    if len(image_data) > _MAX_IMAGE_BYTES:
        raise ValueError("Uploaded image exceeds the 5 MB per-image limit.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_data)) as image:
                actual_format = image.format
                if actual_format != expected_format:
                    raise ValueError("Image content does not match its file extension.")
                if image.width * image.height > _MAX_IMAGE_PIXELS:
                    raise ValueError("The image dimensions exceed the supported limit.")
                image.verify()
    except (OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Uploaded file is not a supported, readable image.") from exc
    return normalized_extension


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


def mark_notification_read(notification_id: str) -> bool:
    """Mark one real inbox event as read. Return False when the ID is unknown."""
    frame = _read_notifications()
    matches = frame.index[frame["NOTIFICATION_ID"].astype(str) == str(notification_id)].tolist()
    if not matches:
        return False
    index = matches[-1]
    if frame.at[index, "NOTIFICATION_STATUS"] != "Read":
        frame.at[index, "NOTIFICATION_STATUS"] = "Read"
        _write_csv_atomic(NOTIFICATION_HISTORY_PATH, frame)
    return True


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
    if image_files and len(image_files) > 5:
        raise ValueError("A maximum of 5 images may be attached to one request.")
    normalized_images = [(_validate_image_data(ext, image_data), image_data) for ext, image_data in (image_files or [])]
    frame = _read_complaints()
    existing = set(frame["SERVICEREQUESTID"].astype(str))
    request_id = _new_request_id(submitted_at, existing)
    timestamp = submitted_at.isoformat(timespec="seconds")
    history = [
        {"event": "Submitted", "timestamp": timestamp},
        {"event": "Priority estimate generated", "timestamp": timestamp},
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
        if normalized_images:
            image_directory.mkdir(parents=True, exist_ok=False)
            image_directory_created = True
            for normalized_extension, image_data in normalized_images:
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


def get_complaint_image_paths(complaint: dict[str, str], key: str = "IMAGE_PATHS") -> list[Path]:
    raw_paths = complaint.get(key, "")
    if not raw_paths:
        return []
    try:
        stored_paths = json.loads(raw_paths)
    except json.JSONDecodeError as exc:
        raise ValueError(f"The stored photo paths for {key} are malformed.") from exc
    if not isinstance(stored_paths, list) or not all(isinstance(path, str) for path in stored_paths):
        raise ValueError(f"The stored photo paths for {key} have an unexpected format.")

    uploads_root = UPLOADS_DIR.resolve()
    resolved_paths: list[Path] = []
    for stored_path in stored_paths:
        image_path = (APP_DATA_DIR / stored_path).resolve()
        if not image_path.is_relative_to(uploads_root):
            raise ValueError("A stored photo path points outside the uploads directory.")
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ValueError("A stored photo has an unsupported file type.")
        if not image_path.is_file():
            continue  # gracefully handle missing sample photos
        resolved_paths.append(image_path)
    return resolved_paths


def update_complaint_status(
    request_id: str,
    status: str,
    event_label: str | None = None,
    officer_name: str | None = None,
    officer_notes: str | None = None,
    resolution_notes: str | None = None,
    resolution_image_files: list[tuple[str, bytes]] | None = None,
    inspection_image_files: list[tuple[str, bytes]] | None = None,
) -> dict[str, str] | None:
    allowed_statuses = {"Open", "In Progress", "Resolved", "Closed"}
    if status not in allowed_statuses:
        raise ValueError(f"Unsupported complaint status: {status}")
    if resolution_image_files and len(resolution_image_files) > 5:
        raise ValueError("A maximum of 5 resolution images may be attached to one request.")
    if inspection_image_files and len(inspection_image_files) > 5:
        raise ValueError("A maximum of 5 inspection images may be attached to one request.")
    normalized_resolution_images = [
        (_validate_image_data(ext, image_data), image_data)
        for ext, image_data in (resolution_image_files or [])
    ]
    normalized_inspection_images = [
        (_validate_image_data(ext, image_data), image_data)
        for ext, image_data in (inspection_image_files or [])
    ]
    if status in {"Resolved", "Closed"} and not (resolution_notes and resolution_notes.strip()) and not normalized_resolution_images:
        raise ValueError("Resolution notes or at least one valid resolution photo are required.")
    frame = _read_complaints()
    matches = frame.index[frame["SERVICEREQUESTID"].astype(str) == str(request_id)].tolist()
    if not matches:
        return None
    index = matches[-1]
    existing = frame.loc[index]
    no_status_change = str(existing.get("STATUS", "")) == status
    no_officer_change = not officer_name or str(existing.get("ASSIGNED_OFFICER", "")) == officer_name
    no_notes_change = not officer_notes or str(existing.get("OFFICER_NOTES", "")) == officer_notes
    no_resolution_change = not resolution_notes or str(existing.get("RESOLUTION_NOTES", "")) == resolution_notes
    if (no_status_change and no_officer_change and no_notes_change and no_resolution_change
            and not normalized_resolution_images and not normalized_inspection_images):
        raise ValueError("No changes were submitted for this request.")
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        history = json.loads(frame.at[index, "STATUS_HISTORY"] or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Status history for request {request_id} is invalid JSON.") from exc
    if not isinstance(history, list) or not all(isinstance(event, dict) for event in history):
        raise ValueError(f"Status history for request {request_id} has an unexpected format.")
    try:
        existing_res = json.loads(frame.at[index, "RESOLUTION_IMAGE_PATHS"] or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Resolution evidence paths for request {request_id} are invalid JSON.") from exc
    if not isinstance(existing_res, list) or not all(isinstance(path, str) for path in existing_res):
        raise ValueError(f"Resolution evidence paths for request {request_id} have an unexpected format.")
    try:
        existing_inspection = json.loads(frame.at[index, "INSPECTION_IMAGE_PATHS"] or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Inspection evidence paths for request {request_id} are invalid JSON.") from exc
    if not isinstance(existing_inspection, list) or not all(isinstance(path, str) for path in existing_inspection):
        raise ValueError(f"Inspection evidence paths for request {request_id} have an unexpected format.")

    event_name = event_label or status
    history.append({"event": event_name, "timestamp": now})
    frame.at[index, "STATUS_HISTORY"] = json.dumps(history, separators=(",", ":"))
    frame.at[index, "STATUS"] = status

    if officer_name:
        frame.at[index, "ASSIGNED_OFFICER"] = officer_name
    if officer_notes:
        frame.at[index, "OFFICER_NOTES"] = officer_notes
    if resolution_notes:
        frame.at[index, "RESOLUTION_NOTES"] = resolution_notes

    created_resolution_paths: list[Path] = []
    created_inspection_paths: list[Path] = []
    try:
        for folder, prefix, file_list, current_paths, column, created_paths in (
            ("inspection", "inspection", normalized_inspection_images, existing_inspection,
             "INSPECTION_IMAGE_PATHS", created_inspection_paths),
            ("resolution", "res", normalized_resolution_images, existing_res,
             "RESOLUTION_IMAGE_PATHS", created_resolution_paths),
        ):
            if not file_list:
                continue
            evidence_dir = (UPLOADS_DIR / str(request_id) / folder).resolve()
            if not evidence_dir.is_relative_to(UPLOADS_DIR.resolve()):
                raise ValueError("The request ID is not a safe evidence directory name.")
            evidence_dir.mkdir(parents=True, exist_ok=True)
            new_paths = []
            for norm_ext, image_data in file_list:
                target = evidence_dir / f"{prefix}_{secrets.token_hex(6)}.{norm_ext}"
                with target.open("xb") as evidence_file:
                    created_paths.append(target)
                    evidence_file.write(image_data)
                new_paths.append(target.relative_to(APP_DATA_DIR).as_posix())
            current_paths.extend(new_paths)
            frame.at[index, column] = json.dumps(current_paths, separators=(",", ":"))
    except (OSError, ValueError, RuntimeError):
        for created_path in [*created_inspection_paths, *created_resolution_paths]:
            created_path.unlink(missing_ok=True)
        raise

    if status in {"Resolved", "Closed"} and not frame.at[index, "CLOSED_DATE"]:
        frame.at[index, "CLOSED_DATE"] = now

    try:
        _write_csv_atomic(LIVE_COMPLAINTS_PATH, frame)
    except (OSError, ValueError, RuntimeError, pd.errors.ParserError):
        for created_path in [*created_inspection_paths, *created_resolution_paths]:
            created_path.unlink(missing_ok=True)
        raise
    return {key: str(value) for key, value in frame.loc[index].to_dict().items()}
