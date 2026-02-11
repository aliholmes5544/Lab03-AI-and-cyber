from models.database import get_db, query_db


class Document:
    def __init__(self, id, title, description, original_filename, stored_filename,
                 file_size, mime_type, classification, uploaded_by, created_at,
                 updated_at, expires_at=None, is_archived=0):
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
        self.expires_at = expires_at
        self.is_archived = is_archived

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        keys = row.keys()
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
            expires_at=row["expires_at"] if "expires_at" in keys else None,
            is_archived=row["is_archived"] if "is_archived" in keys else 0,
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
            f"SELECT * FROM documents WHERE classification IN ({placeholders}) AND is_archived = 0 "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            levels + [per_page, offset],
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents WHERE classification IN ({placeholders}) AND is_archived = 0",
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
        conditions = [f"classification IN ({placeholders})", "is_archived = 0"]

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

    @staticmethod
    def get_accessible_sorted(user_clearance, sort_by="created_at", sort_order="desc",
                              date_from=None, date_to=None, page=1, per_page=20):
        """Get documents with sorting and date filtering."""
        offset = (page - 1) * per_page
        params = [user_clearance]
        conditions = ["classification <= ?", "is_archived = 0"]

        if date_from:
            conditions.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= ?")
            params.append(date_to + " 23:59:59")

        where = " AND ".join(conditions)

        # Validate sort_by to prevent SQL injection
        valid_sorts = {"created_at", "updated_at", "title", "file_size", "classification"}
        if sort_by not in valid_sorts:
            sort_by = "created_at"
        sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        rows = query_db(
            f"SELECT * FROM documents WHERE {where} "
            f"ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?",
            params + [per_page, offset],
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents WHERE {where}",
            params, one=True,
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def get_accessible_by_levels_sorted(levels, sort_by="created_at", sort_order="desc",
                                        date_from=None, date_to=None, page=1, per_page=20):
        """Get documents for specific permission levels with sorting and filtering."""
        if not levels:
            return [], 0
        offset = (page - 1) * per_page
        placeholders = ",".join("?" * len(levels))
        params = list(levels)
        conditions = [f"classification IN ({placeholders})", "is_archived = 0"]

        if date_from:
            conditions.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= ?")
            params.append(date_to + " 23:59:59")

        where = " AND ".join(conditions)

        valid_sorts = {"created_at", "updated_at", "title", "file_size", "classification"}
        if sort_by not in valid_sorts:
            sort_by = "created_at"
        sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        rows = query_db(
            f"SELECT * FROM documents WHERE {where} "
            f"ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?",
            params + [per_page, offset],
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents WHERE {where}",
            params, one=True,
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def search_advanced(user_clearance, query=None, classification=None, sort_by="created_at",
                       sort_order="desc", date_from=None, date_to=None, tag_id=None,
                       page=1, per_page=20):
        """Advanced search with all filters."""
        offset = (page - 1) * per_page
        params = []
        conditions = ["d.classification <= ?", "d.is_archived = 0"]
        params.append(user_clearance)

        if query:
            conditions.append("(d.title LIKE ? OR d.description LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like])

        if classification is not None and classification != "":
            conditions.append("d.classification = ?")
            params.append(int(classification))

        if date_from:
            conditions.append("d.created_at >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("d.created_at <= ?")
            params.append(date_to + " 23:59:59")

        join_clause = ""
        if tag_id:
            join_clause = "JOIN document_tags dt ON d.id = dt.document_id"
            conditions.append("dt.tag_id = ?")
            params.append(tag_id)

        where = " AND ".join(conditions)

        valid_sorts = {"created_at", "updated_at", "title", "file_size", "classification"}
        if sort_by not in valid_sorts:
            sort_by = "created_at"
        sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        rows = query_db(
            f"SELECT d.* FROM documents d {join_clause} WHERE {where} "
            f"ORDER BY d.{sort_by} {sort_dir} LIMIT ? OFFSET ?",
            params + [per_page, offset],
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents d {join_clause} WHERE {where}",
            params, one=True,
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def get_by_ids(doc_ids, user_clearance):
        """Get multiple documents by IDs."""
        if not doc_ids:
            return []
        placeholders = ",".join("?" * len(doc_ids))
        rows = query_db(
            f"SELECT * FROM documents WHERE id IN ({placeholders}) AND classification <= ?",
            list(doc_ids) + [user_clearance]
        )
        return rows

    @staticmethod
    def bulk_delete(doc_ids):
        """Delete multiple documents."""
        if not doc_ids:
            return 0
        db = get_db()
        placeholders = ",".join("?" * len(doc_ids))
        cursor = db.execute(
            f"DELETE FROM documents WHERE id IN ({placeholders})",
            list(doc_ids)
        )
        db.commit()
        return cursor.rowcount

    @staticmethod
    def set_expiration(doc_id, expires_at):
        """Set or clear document expiration date."""
        db = get_db()
        db.execute(
            "UPDATE documents SET expires_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (expires_at, doc_id),
        )
        db.commit()

    @staticmethod
    def archive(doc_id):
        """Archive a document."""
        db = get_db()
        db.execute(
            "UPDATE documents SET is_archived = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (doc_id,),
        )
        db.commit()

    @staticmethod
    def unarchive(doc_id):
        """Unarchive a document."""
        db = get_db()
        db.execute(
            "UPDATE documents SET is_archived = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (doc_id,),
        )
        db.commit()

    @staticmethod
    def get_expiring(user_clearance, days=7, page=1, per_page=20):
        """Get documents expiring within specified days."""
        offset = (page - 1) * per_page
        rows = query_db(
            "SELECT * FROM documents WHERE classification <= ? AND is_archived = 0 "
            "AND expires_at IS NOT NULL AND expires_at <= datetime('now', '+' || ? || ' days') "
            "AND expires_at > datetime('now') "
            "ORDER BY expires_at ASC LIMIT ? OFFSET ?",
            (user_clearance, days, per_page, offset)
        )
        count_row = query_db(
            "SELECT COUNT(*) as cnt FROM documents WHERE classification <= ? AND is_archived = 0 "
            "AND expires_at IS NOT NULL AND expires_at <= datetime('now', '+' || ? || ' days') "
            "AND expires_at > datetime('now')",
            (user_clearance, days), one=True
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def get_expiring_by_levels(levels, days=7, page=1, per_page=20):
        """Get expiring documents filtered by specific permission levels."""
        if not levels:
            return [], 0
        offset = (page - 1) * per_page
        placeholders = ",".join("?" * len(levels))
        params = list(levels)
        rows = query_db(
            f"SELECT * FROM documents WHERE classification IN ({placeholders}) AND is_archived = 0 "
            f"AND expires_at IS NOT NULL AND expires_at <= datetime('now', '+' || ? || ' days') "
            f"AND expires_at > datetime('now') "
            f"ORDER BY expires_at ASC LIMIT ? OFFSET ?",
            params + [days, per_page, offset]
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents WHERE classification IN ({placeholders}) AND is_archived = 0 "
            f"AND expires_at IS NOT NULL AND expires_at <= datetime('now', '+' || ? || ' days') "
            f"AND expires_at > datetime('now')",
            params + [days], one=True
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def get_expired(user_clearance, page=1, per_page=20):
        """Get documents that have expired."""
        offset = (page - 1) * per_page
        rows = query_db(
            "SELECT * FROM documents WHERE classification <= ? AND is_archived = 0 "
            "AND expires_at IS NOT NULL AND expires_at <= datetime('now') "
            "ORDER BY expires_at ASC LIMIT ? OFFSET ?",
            (user_clearance, per_page, offset)
        )
        count_row = query_db(
            "SELECT COUNT(*) as cnt FROM documents WHERE classification <= ? AND is_archived = 0 "
            "AND expires_at IS NOT NULL AND expires_at <= datetime('now')",
            (user_clearance,), one=True
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def auto_archive_expired():
        """Archive all expired documents. Returns count of archived."""
        db = get_db()
        cursor = db.execute(
            "UPDATE documents SET is_archived = 1, updated_at = CURRENT_TIMESTAMP "
            "WHERE is_archived = 0 AND expires_at IS NOT NULL AND expires_at <= datetime('now')"
        )
        db.commit()
        return cursor.rowcount

    @staticmethod
    def update_file(doc_id, stored_filename, file_size, mime_type):
        """Update document file info (for reupload)."""
        db = get_db()
        db.execute(
            "UPDATE documents SET stored_filename = ?, file_size = ?, mime_type = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (stored_filename, file_size, mime_type, doc_id),
        )
        db.commit()

    @staticmethod
    def get_archived(user_clearance, page=1, per_page=20):
        """Get archived documents."""
        offset = (page - 1) * per_page
        rows = query_db(
            "SELECT * FROM documents WHERE classification <= ? AND is_archived = 1 "
            "ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (user_clearance, per_page, offset)
        )
        count_row = query_db(
            "SELECT COUNT(*) as cnt FROM documents WHERE classification <= ? AND is_archived = 1",
            (user_clearance,), one=True
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total

    @staticmethod
    def get_archived_by_levels(levels, page=1, per_page=20):
        """Get archived documents filtered by specific permission levels."""
        if not levels:
            return [], 0
        offset = (page - 1) * per_page
        placeholders = ",".join("?" * len(levels))
        params = list(levels)
        rows = query_db(
            f"SELECT * FROM documents WHERE classification IN ({placeholders}) AND is_archived = 1 "
            f"ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [per_page, offset]
        )
        count_row = query_db(
            f"SELECT COUNT(*) as cnt FROM documents WHERE classification IN ({placeholders}) AND is_archived = 1",
            params, one=True
        )
        total = count_row["cnt"] if count_row else 0
        return rows, total
