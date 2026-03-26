#!/usr/bin/env python3
"""Create a new user for the visit-steven-desk5090 system."""

import sys
import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.auth_service import hash_password, load_users, save_users


def create_user(username: str, password: str, role: str = "user"):
    users = load_users()

    if username in users:
        print(f"User '{username}' already exists. Updating password...")

    users[username] = {
        "username": username,
        "password_hash": hash_password(password),
        "role": role
    }

    save_users(users)
    print(f"User '{username}' created/updated successfully.")


def main():
    print("=" * 50)
    print("Visit Steven Desk5090 - User Creation")
    print("=" * 50)

    username = input("Username: ").strip()
    if not username:
        print("Error: Username cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if not password:
        print("Error: Password cannot be empty.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: Passwords do not match.")
        sys.exit(1)

    role = input("Role [user/admin]: ").strip() or "user"

    create_user(username, password, role)


if __name__ == "__main__":
    main()
