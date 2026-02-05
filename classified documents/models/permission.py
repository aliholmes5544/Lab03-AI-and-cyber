from models.database import get_db, query_db

# Valid permission keys
PERMISSION_LEVELS = [0, 1, 2, 3]
PERMISSION_ACTIONS = ["read", "write"]
ALL_PERMISSIONS = [f"{action}_{level}" for level in PERMISSION_LEVELS for action in PERMISSION_ACTIONS]


class Permission:
    @staticmethod
    def get_user_permissions(user_id):
        """Get all permissions for a user."""
        rows = query_db(
            "SELECT permission FROM user_permissions WHERE user_id = ?",
            (user_id,)
        )
        return [row["permission"] for row in rows]

    @staticmethod
    def has_permission(user_id, action, level):
        """Check if user has a specific permission."""
        permission = f"{action}_{level}"
        row = query_db(
            "SELECT id FROM user_permissions WHERE user_id = ? AND permission = ?",
            (user_id, permission),
            one=True
        )
        return row is not None

    @staticmethod
    def can_read(user_id, classification):
        """Check if user can read documents at the given classification level."""
        return Permission.has_permission(user_id, "read", classification)

    @staticmethod
    def can_write(user_id, classification):
        """Check if user can write documents at the given classification level."""
        return Permission.has_permission(user_id, "write", classification)

    @staticmethod
    def grant(user_id, permission, granted_by):
        """Grant a permission to a user."""
        if permission not in ALL_PERMISSIONS:
            raise ValueError(f"Invalid permission: {permission}")
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO user_permissions (user_id, permission, granted_by) "
            "VALUES (?, ?, ?)",
            (user_id, permission, granted_by)
        )
        db.commit()

    @staticmethod
    def revoke(user_id, permission):
        """Revoke a permission from a user."""
        db = get_db()
        db.execute(
            "DELETE FROM user_permissions WHERE user_id = ? AND permission = ?",
            (user_id, permission)
        )
        db.commit()

    @staticmethod
    def revoke_all(user_id):
        """Revoke all permissions from a user."""
        db = get_db()
        db.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
        db.commit()

    @staticmethod
    def set_permissions(user_id, permissions, granted_by):
        """Replace all permissions for a user with the given set."""
        db = get_db()
        # Remove all existing permissions
        db.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
        # Grant new permissions
        for permission in permissions:
            if permission in ALL_PERMISSIONS:
                db.execute(
                    "INSERT INTO user_permissions (user_id, permission, granted_by) "
                    "VALUES (?, ?, ?)",
                    (user_id, permission, granted_by)
                )
        db.commit()

    @staticmethod
    def grant_all_at_clearance(user_id, clearance, granted_by):
        """Grant all read and write permissions up to the given clearance level."""
        permissions = []
        for level in range(clearance + 1):
            permissions.append(f"read_{level}")
            permissions.append(f"write_{level}")
        Permission.set_permissions(user_id, permissions, granted_by)

    @staticmethod
    def get_readable_levels(user_id):
        """Get list of classification levels the user can read."""
        permissions = Permission.get_user_permissions(user_id)
        levels = []
        for perm in permissions:
            if perm.startswith("read_"):
                level = int(perm.split("_")[1])
                levels.append(level)
        return sorted(levels)

    @staticmethod
    def get_writable_levels(user_id):
        """Get list of classification levels the user can write."""
        permissions = Permission.get_user_permissions(user_id)
        levels = []
        for perm in permissions:
            if perm.startswith("write_"):
                level = int(perm.split("_")[1])
                levels.append(level)
        return sorted(levels)
