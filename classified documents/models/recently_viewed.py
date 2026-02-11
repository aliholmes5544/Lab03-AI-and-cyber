from models.database import get_db, query_db


class RecentlyViewed:
    @staticmethod
    def record(user_id, document_id):
        """Record a document view. Uses UPSERT to update timestamp if exists."""
        db = get_db()
        # Delete and re-insert to update timestamp (SQLite UPSERT)
        db.execute(
            "DELETE FROM recently_viewed WHERE user_id = ? AND document_id = ?",
            (user_id, document_id)
        )
        db.execute(
            "INSERT INTO recently_viewed (user_id, document_id) VALUES (?, ?)",
            (user_id, document_id)
        )
        db.commit()

        # Keep only last 50 viewed documents per user
        db.execute(
            "DELETE FROM recently_viewed WHERE user_id = ? AND id NOT IN "
            "(SELECT id FROM recently_viewed WHERE user_id = ? ORDER BY viewed_at DESC LIMIT 50)",
            (user_id, user_id)
        )
        db.commit()

    @staticmethod
    def get_recent(user_id, user_clearance, limit=10):
        rows = query_db(
            "SELECT d.* FROM documents d "
            "JOIN recently_viewed rv ON d.id = rv.document_id "
            "WHERE rv.user_id = ? AND d.classification <= ? AND d.is_archived = 0 "
            "ORDER BY rv.viewed_at DESC LIMIT ?",
            (user_id, user_clearance, limit)
        )
        return rows

    @staticmethod
    def get_recent_paginated(user_id, user_clearance, page=1, per_page=20):
        offset = (page - 1) * per_page
        rows = query_db(
            "SELECT d.*, rv.viewed_at as last_viewed FROM documents d "
            "JOIN recently_viewed rv ON d.id = rv.document_id "
            "WHERE rv.user_id = ? AND d.classification <= ? AND d.is_archived = 0 "
            "ORDER BY rv.viewed_at DESC LIMIT ? OFFSET ?",
            (user_id, user_clearance, per_page, offset)
        )
        count_row = query_db(
            "SELECT COUNT(*) as cnt FROM documents d "
            "JOIN recently_viewed rv ON d.id = rv.document_id "
            "WHERE rv.user_id = ? AND d.classification <= ? AND d.is_archived = 0",
            (user_id, user_clearance), one=True
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def get_recent_paginated_by_levels(user_id, levels, page=1, per_page=20):
        """Get recently viewed documents filtered by specific permission levels."""
        if not levels:
            return [], 0
        offset = (page - 1) * per_page
        placeholders = ",".join("?" * len(levels))
        params = [user_id] + list(levels)
        rows = query_db(
            f"SELECT d.*, rv.viewed_at as last_viewed FROM documents d "
            f"JOIN recently_viewed rv ON d.id = rv.document_id "
            f"WHERE rv.user_id = ? AND d.classification IN ({placeholders}) AND d.is_archived = 0 "
            f"ORDER BY rv.viewed_at DESC LIMIT ? OFFSET ?",
            params + [per_page, offset]
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents d "
            f"JOIN recently_viewed rv ON d.id = rv.document_id "
            f"WHERE rv.user_id = ? AND d.classification IN ({placeholders}) AND d.is_archived = 0",
            params, one=True
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def clear_user_history(user_id):
        db = get_db()
        db.execute("DELETE FROM recently_viewed WHERE user_id = ?", (user_id,))
        db.commit()
