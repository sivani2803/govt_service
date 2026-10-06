from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import authentication


class LocalAccountTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "accounts.sqlite3"
        self.path_patch = patch.object(authentication, "AUTH_DATABASE_PATH", self.database_path)
        self.path_patch.start()

    def tearDown(self) -> None:
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_first_run_registration_and_existing_user_sign_in(self) -> None:
        self.assertFalse(authentication.has_registered_users())
        account = authentication.register_citizen(
            "  First.User@example.com ", "First User", "a long enough passphrase"
        )
        self.assertTrue(authentication.has_registered_users())
        self.assertEqual(account["role"], "citizen")
        self.assertNotIn("password_hash", account)

        connection = sqlite3.connect(self.database_path)
        try:
            stored_hash = connection.execute(
                "SELECT password_hash FROM users WHERE user_id = ?", (account["user_id"],)
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertNotEqual(stored_hash, "a long enough passphrase")
        self.assertTrue(stored_hash.startswith("pbkdf2_sha256$"))

        signed_in, error = authentication.authenticate_user(
            "FIRST.USER@example.com", "a long enough passphrase", client_ip="127.0.0.1"
        )
        self.assertEqual(error, "")
        self.assertEqual(signed_in["user_id"], account["user_id"])

    def test_public_registration_cannot_assign_agency_role(self) -> None:
        citizen = authentication.register_citizen("person@example.com", "Person", "another long passphrase")
        self.assertEqual(citizen["role"], "citizen")
        with self.assertRaises(ValueError):
            authentication.provision_user(
                "staff@example.com", "Staff", "another long passphrase", "superuser"
            )

    def test_registration_validates_password_and_duplicate_email(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 12"):
            authentication.register_citizen("person@example.com", "Person", "short")
        authentication.register_citizen("person@example.com", "Person", "another long passphrase")
        with self.assertRaisesRegex(ValueError, "already exist"):
            authentication.register_citizen("PERSON@example.com", "Person Two", "different long passphrase")


if __name__ == "__main__":
    unittest.main()
