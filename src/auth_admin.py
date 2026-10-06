"""Operator-only CLI for provisioning CivicPulse agency accounts.

Run this command on the host that owns CivicPulse's local account database.
Passwords are read through the terminal prompt and never accepted as flags.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from src.authentication import provision_user


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision a CivicPulse agency account.")
    parser.add_argument("--email", required=True, help="Agency account email address")
    parser.add_argument("--name", required=True, help="Account holder's display name")
    parser.add_argument("--role", required=True, choices=("officer", "administrator"))
    args = parser.parse_args()

    password = getpass.getpass("Choose a passphrase (12+ characters): ")
    confirmation = getpass.getpass("Confirm passphrase: ")
    if password != confirmation:
        print("Passphrases did not match.", file=sys.stderr)
        return 2
    try:
        user = provision_user(args.email, args.name, password, args.role)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Created {user['role']} account for {user['email']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
