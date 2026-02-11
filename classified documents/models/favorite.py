from models.database import get_db, query_db


class Favorite:
    @staticmethod
    def toggle(user_id, document_id):
        """Toggle favorite status. Returns True if favorited, False if unfavorited."""
        db = get_db()
        existing = query_db(
            "SELECT 1 FROM favorites WHERE user_id = ? AND document_id = ?",
            (user_id, document_id), one=True
        )
        if existing:
            db.execute(
                "DELETE FROM favorites WHERE user_id = ? AND document_id = ?",
                (user_id, document_id)
            )
            db.commit()
            return False
        else:
            db.execute(
                "INSERT INTO favorites (user_id, document_id) VALUES (?, ?)",
                (user_id, document_id)
            )
            db.commit()
            return True

    @staticmethod
    def is_favorite(user_id, document_id):
        row = query_db(
            "SELECT 1 FROM favorites WHERE user_id = ? AND document_id = ?",
            (user_id, document_id), one=True
        )
        return row is not None

    @staticmethod
    def get_user_favorites(user_id, user_clearance, page=1, per_page=20):
        offset = (page - 1) * per_page
        rows = query_db(
            "SELECT d.* FROM documents d "
            "JOIN favorites f ON d.id = f.document_id "
            "WHERE f.user_id = ? AND d.classification <= ? AND d.is_archived = 0 "
            "ORDER BY f.created_at DESC LIMIT ? OFFSET ?",
            (user_id, user_clearance, per_page, offset)
        )
        count_row = query_db(
            "SELECT COUNT(*) as cnt FROM documents d "
            "JOIN favorites f ON d.id = f.document_id "
            "WHERE f.user_id = ? AND d.classification <= ? AND d.is_archived = 0",
            (user_id, user_clearance), one=True
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def get_user_favorites_by_levels(user_id, levels, page=1, per_page=20):
        """Get user favorites filtered by specific permission levels."""
        if not levels:
            return [], 0
        offset = (page - 1) * per_page
        placeholders = ",".join("?" * len(levels))
        params = [user_id] + list(levels)
        rows = query_db(
            f"SELECT d.* FROM documents d "
            f"JOIN favorites f ON d.id = f.document_id "
            f"WHERE f.user_id = ? AND d.classification IN ({placeholders}) AND d.is_archived = 0 "
            f"ORDER BY f.created_at DESC LIMIT ? OFFSET ?",
            params + [per_page, offset]
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents d "
            f"JOIN favorites f ON d.id = f.document_id "
            f"WHERE f.user_id = ? AND d.classification IN ({placeholders}) AND d.is_archived = 0",
            params, one=True
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def get_user_favorite_ids(user_id):
        rows = query_db(
            "SELECT document_id FROM favorites WHERE user_id = ?",
            (user_id,)
        )
        return {row["document_id"] for row in rows}

    @staticmethod
    def remove(user_id, document_id):
        db = get_db()
        db.execute(
            "DELETE FROM favorites WHERE user_id = ? AND document_id = ?",
            (user_id, document_id)
        )
        db.commit()
