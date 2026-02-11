from models.database import get_db, query_db


class AuditLog:
    @staticmethod
    def log(user_id, action, target_type, target_id, details, ip_address):
        db = get_db()
        db.execute(
            "INSERT INTO audit_logs (user_id, action, target_type, target_id, "
            "details, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, action, target_type, target_id, details, ip_address),
        )
        db.commit()

    @staticmethod
    def get_logs(page=1, per_page=50, user_id=None, action=None):
        offset = (page - 1) * per_page
        conditions = []
        params = []

        if user_id:
            conditions.append("audit_logs.user_id = ?")
            params.append(user_id)
        if action:
            conditions.append("audit_logs.action = ?")
            params.append(action)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        rows = query_db(
            f"SELECT audit_logs.*, users.username FROM audit_logs "
            f"LEFT JOIN users ON audit_logs.user_id = users.id "
            f"{where} ORDER BY audit_logs.timestamp DESC LIMIT ? OFFSET ?",
            params + [per_page, offset],
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM audit_logs {where}",
            params, one=True,
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def count_today(action=None):
        if action:
            row = query_db(
                "SELECT COUNT(*) as count FROM audit_logs "
                "WHERE action = ? AND DATE(timestamp) = DATE('now')",
                (action,), one=True
            )
        else:
            row = query_db(
                "SELECT COUNT(*) as count FROM audit_logs "
                "WHERE DATE(timestamp) = DATE('now')",
                one=True
            )
        return row["count"] if row else 0

    @staticmethod
    def get_recent(limit=10):
        return query_db(
            "SELECT audit_logs.*, users.username FROM audit_logs "
            "LEFT JOIN users ON audit_logs.user_id = users.id "
            "ORDER BY audit_logs.timestamp DESC LIMIT ?",
            (limit,)
        )
