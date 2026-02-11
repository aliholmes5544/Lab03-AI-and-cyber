from models.database import get_db, query_db


class Comment:
    def __init__(self, id, document_id, user_id, content, created_at, updated_at,
                 username=None):
        self.id = id
        self.document_id = document_id
        self.user_id = user_id
        self.content = content
        self.created_at = created_at
        self.updated_at = updated_at
        self.username = username

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return Comment(
            id=row["id"],
            document_id=row["document_id"],
            user_id=row["user_id"],
            content=row["content"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            username=row["username"] if "username" in row.keys() else None,
        )

    @staticmethod
    def create(document_id, user_id, content):
        db = get_db()
        cursor = db.execute(
            "INSERT INTO document_comments (document_id, user_id, content) "
            "VALUES (?, ?, ?)",
            (document_id, user_id, content),
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_by_id(comment_id):
        row = query_db(
            "SELECT c.*, u.username FROM document_comments c "
            "LEFT JOIN users u ON c.user_id = u.id WHERE c.id = ?",
            (comment_id,), one=True
        )
        return Comment.from_row(row)

    @staticmethod
    def get_by_document(document_id):
        rows = query_db(
            "SELECT c.*, u.username FROM document_comments c "
            "LEFT JOIN users u ON c.user_id = u.id "
            "WHERE c.document_id = ? ORDER BY c.created_at DESC",
            (document_id,)
        )
        return [Comment.from_row(row) for row in rows]

    @staticmethod
    def update(comment_id, content):
        db = get_db()
        db.execute(
            "UPDATE document_comments SET content = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (content, comment_id),
        )
        db.commit()

    @staticmethod
    def delete(comment_id):
        db = get_db()
        db.execute("DELETE FROM document_comments WHERE id = ?", (comment_id,))
        db.commit()

    @staticmethod
    def count_by_document(document_id):
        row = query_db(
            "SELECT COUNT(*) as count FROM document_comments WHERE document_id = ?",
            (document_id,), one=True
        )
        return row["count"] if row else 0
