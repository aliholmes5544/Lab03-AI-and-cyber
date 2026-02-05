from models.database import get_db, query_db


class Document:
    def __init__(self, id, title, description, original_filename, stored_filename,
                 file_size, mime_type, classification, uploaded_by, created_at,
                 updated_at):
        self.id = id
        self.title = title
        self.description = description
        self.original_filename = original_filename
        self.stored_filename = stored_filename
        self.file_size = file_size
        self.mime_type = mime_type
        self.classification = classification
        self.uploaded_by = uploaded_by
        self.created_at = created_at
        self.updated_at = updated_at

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return Document(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            original_filename=row["original_filename"],
            stored_filename=row["stored_filename"],
            file_size=row["file_size"],
            mime_type=row["mime_type"],
            classification=row["classification"],
            uploaded_by=row["uploaded_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def create(title, description, original_filename, stored_filename,
               file_size, mime_type, classification, uploaded_by):
        db = get_db()
        cursor = db.execute(
            "INSERT INTO documents (title, description, original_filename, "
            "stored_filename, file_size, mime_type, classification, uploaded_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, description, original_filename, stored_filename,
             file_size, mime_type, classification, uploaded_by),
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_by_id(doc_id):
        row = query_db("SELECT * FROM documents WHERE id = ?", (doc_id,), one=True)
        return Document.from_row(row)

    @staticmethod
    def get_accessible(user_clearance, page=1, per_page=20):
        offset = (page - 1) * per_page
        rows = query_db(
            "SELECT * FROM documents WHERE classification <= ? "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_clearance, per_page, offset),
        )
        count_row = query_db(
            "SELECT COUNT(*) as cnt FROM documents WHERE classification <= ?",
            (user_clearance,), one=True,
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def search(user_clearance, query, classification=None, page=1, per_page=20):
        offset = (page - 1) * per_page
        params = []
        conditions = ["classification <= ?"]
        params.append(user_clearance)

        if query:
            conditions.append("(title LIKE ? OR description LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like])

        if classification is not None and classification != "":
            conditions.append("classification = ?")
            params.append(int(classification))

        where = " AND ".join(conditions)

        rows = query_db(
            f"SELECT * FROM documents WHERE {where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [per_page, offset],
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents WHERE {where}",
            params, one=True,
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def update_classification(doc_id, classification):
        db = get_db()
        db.execute(
            "UPDATE documents SET classification = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (classification, doc_id),
        )
        db.commit()

    @staticmethod
    def delete(doc_id):
        db = get_db()
        db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        db.commit()

    @staticmethod
    def count_all():
        row = query_db("SELECT COUNT(*) as count FROM documents", one=True)
        return row["count"] if row else 0

    @staticmethod
    def total_storage():
        row = query_db("SELECT SUM(file_size) as total FROM documents", one=True)
        return row["total"] if row and row["total"] else 0

    @staticmethod
    def count_by_classification():
        rows = query_db("SELECT classification, COUNT(*) as count FROM documents GROUP BY classification ORDER BY classification")
        return {row["classification"]: row["count"] for row in rows}

    @staticmethod
    def get_accessible_by_levels(levels, page=1, per_page=20):
        """Get documents accessible at any of the given classification levels."""
        if not levels:
            return [], 0
        offset = (page - 1) * per_page
        placeholders = ",".join("?" * len(levels))
        rows = query_db(
            f"SELECT * FROM documents WHERE classification IN ({placeholders}) "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            levels + [per_page, offset],
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents WHERE classification IN ({placeholders})",
            levels, one=True,
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def search_by_levels(levels, query, classification=None, page=1, per_page=20):
        """Search documents within accessible classification levels."""
        if not levels:
            return [], 0
        offset = (page - 1) * per_page
        placeholders = ",".join("?" * len(levels))
        params = list(levels)
        conditions = [f"classification IN ({placeholders})"]

        if query:
            conditions.append("(title LIKE ? OR description LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like])

        if classification is not None and classification != "":
            classification_int = int(classification)
            if classification_int in levels:
                conditions.append("classification = ?")
                params.append(classification_int)
            else:
                # User doesn't have access to this classification
                return [], 0

        where = " AND ".join(conditions)

        rows = query_db(
            f"SELECT * FROM documents WHERE {where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [per_page, offset],
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents WHERE {where}",
            params, one=True,
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total
