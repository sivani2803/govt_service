"""Local account storage and password authentication for CivicPulse.

Self-registration always creates citizen accounts. Agency roles must be
provisioned by an operator or granted by the configured OIDC allowlists.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

from src.config import AUTH_DATABASE_PATH

_CURRENT_ITERATIONS = 600_000
_SALT_BYTES = 16
_KEY_BYTES = 32
_MAX_PASSWORD_BYTES = 1024
_MAX_FAILED_ATTEMPTS = 5
_ATTEMPT_WINDOW_SECONDS = 15 * 60
_LOCKOUT_SECONDS = 15 * 60
_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_GENERIC_LOGIN_ERROR = "Email or password is incorrect, or sign-in is temporarily limited."


def _connect() -> sqlite3.Connection:
    Path(AUTH_DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(AUTH_DATABASE_PATH), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('citizen', 'officer', 'administrator')),
            created_at INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS login_attempts (
            attempt_key TEXT PRIMARY KEY,
            attempts INTEGER NOT NULL,
            window_started INTEGER NOT NULL,
            blocked_until INTEGER NOT NULL DEFAULT 0
        )"""
    )
    connection.commit()
    try:
        os.chmod(AUTH_DATABASE_PATH, 0o600)
    except OSError:
        # Windows ACLs, rather than POSIX mode bits, control file access there.
        pass
    return connection


def normalize_email(email: str) -> str:
    """Validate and canonicalize an email used as a login identifier."""
    normalized = str(email).strip().casefold()
    if len(normalized) > 254 or not _EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid email address.")
    return normalized


def validate_password(password: str) -> None:
    """Apply a simple passphrase policy without composition rules."""
    if not isinstance(password, str):
        raise ValueError("Enter a password.")
    byte_length = len(password.encode("utf-8"))
    if len(password) < 12:
        raise ValueError("Use a passphrase with at least 12 characters.")
    if byte_length > _MAX_PASSWORD_BYTES:
        raise ValueError("Passwords must be no longer than 1024 UTF-8 bytes.")


def _hash_password(password: str, salt: bytes | None = None, iterations: int = _CURRENT_ITERATIONS) -> str:
    selected_salt = salt or secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), selected_salt, iterations, dklen=_KEY_BYTES
    )
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.b64encode(selected_salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def _verify_password(password: str, encoded_hash: str) -> tuple[bool, int]:
    try:
        algorithm, iteration_text, salt_text, digest_text = encoded_hash.split("$", 3)
        iterations = int(iteration_text)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            raise ValueError("Unsupported password hash.")
        salt = base64.b64decode(salt_text, validate=True)
        expected = base64.b64decode(digest_text, validate=True)
        if len(salt) < _SALT_BYTES or len(expected) != _KEY_BYTES:
            raise ValueError("Malformed password hash.")
    except (ValueError, TypeError, base64.binascii.Error):
        return False, 0
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected))
    return hmac.compare_digest(actual, expected), iterations


def _public_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": str(row["user_id"]),
        "email": str(row["email"]),
        "display_name": str(row["display_name"]),
        "role": str(row["role"]),
    }


def _create_user(email: str, display_name: str, password: str, role: str) -> dict[str, Any]:
    normalized_email = normalize_email(email)
    normalized_name = " ".join(str(display_name).split())
    if not normalized_name or len(normalized_name) > 80:
        raise ValueError("Enter a name between 1 and 80 characters.")
    validate_password(password)
    if role not in {"citizen", "officer", "administrator"}:
        raise ValueError("The requested account role is not supported.")
    user = {
        "user_id": secrets.token_urlsafe(24),
        "email": normalized_email,
        "display_name": normalized_name,
        "password_hash": _hash_password(password),
        "role": role,
        "created_at": int(time.time()),
    }
    connection = _connect()
    try:
        with connection:
            connection.execute(
                "INSERT INTO users (user_id, email, display_name, password_hash, role, created_at) "
                "VALUES (:user_id, :email, :display_name, :password_hash, :role, :created_at)",
                user,
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("An account for this email may already exist. Try signing in instead.") from exc
    finally:
        connection.close()
    return {key: value for key, value in user.items() if key != "password_hash"}


def register_citizen(email: str, display_name: str, password: str) -> dict[str, Any]:
    """Create a public self-service account, always with citizen privileges."""
    return _create_user(email, display_name, password, "citizen")


def provision_user(email: str, display_name: str, password: str, role: str) -> dict[str, Any]:
    """Create an account for an operator-provisioned agency role."""
    if role == "citizen":
        return register_citizen(email, display_name, password)
    return _create_user(email, display_name, password, role)


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT user_id, email, display_name, role FROM users WHERE user_id = ? AND is_active = 1",
            (str(user_id),),
        ).fetchone()
        return _public_user(row) if row else None
    finally:
        connection.close()


def has_registered_users() -> bool:
    """Return whether an account exists, for choosing the first-run auth tab."""
    connection = _connect()
    try:
        return connection.execute("SELECT EXISTS(SELECT 1 FROM users LIMIT 1)").fetchone()[0] == 1
    finally:
        connection.close()


def _limiter_key(email: str, client_ip: str) -> str:
    payload = f"{email}\0{client_ip[:128]}".encode("utf-8", "replace")
    return hashlib.sha256(payload).hexdigest()


def authenticate_user(email: str, password: str, *, client_ip: str = "unknown") -> tuple[dict[str, Any] | None, str]:
    """Authenticate with generic errors and a per-email/IP temporary throttle."""
    safe_email = str(email).strip().casefold()[:254]
    safe_password = password if isinstance(password, str) else ""
    if len(safe_password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        safe_password = ""
    attempt_key = _limiter_key(safe_email, client_ip)
    now = int(time.time())

    connection = _connect()
    try:
        limit = connection.execute(
            "SELECT attempts, window_started, blocked_until FROM login_attempts WHERE attempt_key = ?",
            (attempt_key,),
        ).fetchone()
        user_row = connection.execute(
            "SELECT user_id, email, display_name, password_hash, role FROM users "
            "WHERE email = ? COLLATE NOCASE AND is_active = 1",
            (safe_email,),
        ).fetchone()
    finally:
        connection.close()

    if limit and int(limit["blocked_until"]) > now:
        _hash_password("constant-time unknown account password", salt=b"civicpulse-lockout", iterations=_CURRENT_ITERATIONS)
        return None, _GENERIC_LOGIN_ERROR

    encoded_hash = str(user_row["password_hash"]) if user_row else _hash_password(
        "constant-time unknown account password", salt=b"civicpulse-dummy-salt", iterations=_CURRENT_ITERATIONS
    )
    password_ok, stored_iterations = _verify_password(safe_password, encoded_hash)
    if not user_row or not password_ok:
        connection = _connect()
        try:
            with connection:
                previous = connection.execute(
                    "SELECT attempts, window_started FROM login_attempts WHERE attempt_key = ?",
                    (attempt_key,),
                ).fetchone()
                if not previous or now - int(previous["window_started"]) >= _ATTEMPT_WINDOW_SECONDS:
                    attempts, window_started = 1, now
                else:
                    attempts, window_started = int(previous["attempts"]) + 1, int(previous["window_started"])
                blocked_until = now + _LOCKOUT_SECONDS if attempts >= _MAX_FAILED_ATTEMPTS else 0
                connection.execute(
                    "INSERT INTO login_attempts (attempt_key, attempts, window_started, blocked_until) "
                    "VALUES (?, ?, ?, ?) ON CONFLICT(attempt_key) DO UPDATE SET "
                    "attempts=excluded.attempts, window_started=excluded.window_started, blocked_until=excluded.blocked_until",
                    (attempt_key, attempts, window_started, blocked_until),
                )
        finally:
            connection.close()
        return None, _GENERIC_LOGIN_ERROR

    connection = _connect()
    try:
        with connection:
            connection.execute("DELETE FROM login_attempts WHERE attempt_key = ?", (attempt_key,))
            if stored_iterations < _CURRENT_ITERATIONS:
                connection.execute(
                    "UPDATE users SET password_hash = ? WHERE user_id = ?",
                    (_hash_password(safe_password), str(user_row["user_id"])),
                )
    finally:
        connection.close()
    return _public_user(user_row), ""
