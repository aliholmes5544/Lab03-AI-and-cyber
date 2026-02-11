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

-- Comments on documents
CREATE TABLE IF NOT EXISTS document_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tags for organizing documents
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT 'secondary',
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Document-tag relationship
CREATE TABLE IF NOT EXISTS document_tags (
    document_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    added_by INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, tag_id),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- User favorites
CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, document_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Document version history
CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    stored_filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    uploaded_by INTEGER NOT NULL,
    change_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

-- Recently viewed documents
CREATE TABLE IF NOT EXISTS recently_viewed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, document_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
"""


def init_db():
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    db = sqlite3.connect(Config.DATABASE)
    db.executescript(SCHEMA)

    # Seed admin user if not exists
    cursor = db.execute("SELECT id FROM users WHERE username = 'admin'")
    if cursor.fetchone() is None:
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
        db.execute(
            "INSERT INTO users (username, email, password_hash, role, clearance) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "admin",
                admin_email,
                generate_password_hash(admin_password),
                "admin",
                3,
            ),
        )
        db.commit()
        if admin_password == "admin":
            print("WARNING: Admin created with default password. "
                  "Set ADMIN_PASSWORD env var for production.")
        print("Admin user created (username: admin)")
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

    # Migration: Add expiration columns to documents table if not exists
    cursor = db.execute("PRAGMA table_info(documents)")
    columns = [row[1] for row in cursor.fetchall()]
    if "expires_at" not in columns:
        db.execute("ALTER TABLE documents ADD COLUMN expires_at TIMESTAMP DEFAULT NULL")
        db.commit()
        print("Added expires_at column to documents table")
    if "is_archived" not in columns:
        db.execute("ALTER TABLE documents ADD COLUMN is_archived INTEGER DEFAULT 0")
        db.commit()
        print("Added is_archived column to documents table")

    db.close()
    print(f"Database initialized at {Config.DATABASE}")


if __name__ == "__main__":
    init_db()
