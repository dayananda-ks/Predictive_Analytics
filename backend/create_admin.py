from __future__ import annotations

import os
import getpass
from werkzeug.security import generate_password_hash

from backend.config import get_config
from backend.database import create_user, get_user_by_email


def create_admin_interactive():
    config = get_config()
    db = config.DATABASE_PATH
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    name = os.getenv("ADMIN_NAME", "Administrator")

    if not email:
        email = input("Admin email: ").strip().lower()
    if not password:
        password = getpass.getpass("Admin password (will not echo): ")

    if get_user_by_email(db, email):
        print("An account with that email already exists.")
        return

    password_hash = generate_password_hash(password)
    user_id = create_user(db, name, email, password_hash, role="admin")
    print(f"Created admin user id={user_id} email={email}")


if __name__ == "__main__":
    create_admin_interactive()
