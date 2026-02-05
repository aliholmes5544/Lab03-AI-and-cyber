from flask_login import UserMixin

from models.database import get_db, query_db
from models.permission import Permission


class User(UserMixin):
    def __init__(self, id, username, email, password_hash, role, clearance,
                 is_active, created_at):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.clearance = clearance
        self._is_active = is_active
        self.created_at = created_at

    @property
    def is_active(self):
        return bool(self._is_active)

    def can_read(self, classification):
        """Check if user can read documents at the given classification level."""
        # Clearance still acts as a ceiling
        if classification > self.clearance:
            return False
        return Permission.can_read(self.id, classification)

    def can_write(self, classification):
        """Check if user can write documents at the given classification level."""
        # Clearance still acts as a ceiling
        if classification > self.clearance:
            return False
        return Permission.can_write(self.id, classification)

    def get_readable_levels(self):
        """Get list of classification levels this user can read."""
        all_readable = Permission.get_readable_levels(self.id)
        # Filter by clearance ceiling
        return [level for level in all_readable if level <= self.clearance]

    def get_writable_levels(self):
        """Get list of classification levels this user can write."""
        all_writable = Permission.get_writable_levels(self.id)
        # Filter by clearance ceiling
        return [level for level in all_writable if level <= self.clearance]

    def get_permissions(self):
        """Get all permissions for this user."""
        return Permission.get_user_permissions(self.id)

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=row["role"],
            clearance=row["clearance"],
            is_active=row["is_active"],
            created_at=row["created_at"],
        )

    @staticmethod
    def get_by_id(user_id):
        row = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
        return User.from_row(row)

    @staticmethod
    def get_by_username(username):
        row = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        return User.from_row(row)

    @staticmethod
    def get_by_email(email):
        row = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        return User.from_row(row)

    @staticmethod
    def create(username, email, password_hash, role="user", clearance=0):
        db = get_db()
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash, role, clearance) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, role, clearance),
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_all():
        return query_db("SELECT * FROM users ORDER BY created_at DESC")

    @staticmethod
    def update(user_id, **kwargs):
        allowed = {"role", "clearance", "is_active", "email", "password_hash"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [user_id]
        db = get_db()
        db.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        db.commit()

    @staticmethod
    def count_all():
        row = query_db("SELECT COUNT(*) as count FROM users", one=True)
        return row["count"] if row else 0

    @staticmethod
    def count_active():
        row = query_db("SELECT COUNT(*) as count FROM users WHERE is_active = 1", one=True)
        return row["count"] if row else 0

    @staticmethod
    def count_by_role():
        rows = query_db("SELECT role, COUNT(*) as count FROM users GROUP BY role")
        return {row["role"]: row["count"] for row in rows}

    @staticmethod
    def count_by_clearance():
        rows = query_db("SELECT clearance, COUNT(*) as count FROM users GROUP BY clearance ORDER BY clearance")
        return {row["clearance"]: row["count"] for row in rows}
