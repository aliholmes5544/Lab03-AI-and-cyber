import sqlite3
import os

from werkzeug.security import generate_password_hash

from config import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    clearance INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT,
    classification INTEGER NOT NULL DEFAULT 0,
    uploaded_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    details TEXT,
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    permission TEXT NOT NULL,
    granted_by INTEGER NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, permission)
);
"""


def init_db():
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    db = sqlite3.connect(Config.DATABASE)
    db.executescript(SCHEMA)

    # Seed admin user if not exists
    cursor = db.execute("SELECT id FROM users WHERE username = 'admin'")
    if cursor.fetchone() is None:
        db.execute(
            "INSERT INTO users (username, email, password_hash, role, clearance) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "admin",
                "admin@example.com",
                generate_password_hash("admin"),
                "admin",
                3,
            ),
        )
        db.commit()
        print("Admin user created (username: admin, password: admin)")
    else:
        print("Admin user already exists")

    # Migration: Grant existing users permissions at their clearance level
    cursor = db.execute("SELECT id, clearance FROM users")
    users = cursor.fetchall()
    for user_id, clearance in users:
        # Check if user already has permissions
        perm_cursor = db.execute(
            "SELECT id FROM user_permissions WHERE user_id = ? LIMIT 1",
            (user_id,)
        )
        if perm_cursor.fetchone() is None:
            # Grant read and write permissions up to clearance level
            for level in range(clearance + 1):
                for action in ["read", "write"]:
                    permission = f"{action}_{level}"
                    db.execute(
                        "INSERT OR IGNORE INTO user_permissions (user_id, permission, granted_by) "
                        "VALUES (?, ?, ?)",
                        (user_id, permission, user_id),
                    )
            db.commit()
            print(f"Granted permissions to user (id={user_id})")

    db.close()
    print(f"Database initialized at {Config.DATABASE}")


if __name__ == "__main__":
    init_db()
