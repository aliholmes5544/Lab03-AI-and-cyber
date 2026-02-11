from models.database import get_db, query_db


class DocumentVersion:
    def __init__(self, id, document_id, version_number, stored_filename, file_size,
                 uploaded_by, change_notes, created_at, username=None):
        self.id = id
        self.document_id = document_id
        self.version_number = version_number
        self.stored_filename = stored_filename
        self.file_size = file_size
        self.uploaded_by = uploaded_by
        self.change_notes = change_notes
        self.created_at = created_at
        self.username = username

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return DocumentVersion(
            id=row["id"],
            document_id=row["document_id"],
            version_number=row["version_number"],
            stored_filename=row["stored_filename"],
            file_size=row["file_size"],
            uploaded_by=row["uploaded_by"],
            change_notes=row["change_notes"],
            created_at=row["created_at"],
            username=row["username"] if "username" in row.keys() else None,
        )

    @staticmethod
    def create(document_id, stored_filename, file_size, uploaded_by, change_notes=None):
        db = get_db()
        # Get next version number
        row = query_db(
            "SELECT MAX(version_number) as max_ver FROM document_versions WHERE document_id = ?",
            (document_id,), one=True
        )
        next_version = (row["max_ver"] or 0) + 1

        cursor = db.execute(
            "INSERT INTO document_versions (document_id, version_number, stored_filename, "
            "file_size, uploaded_by, change_notes) VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, next_version, stored_filename, file_size, uploaded_by, change_notes),
        )
        db.commit()
        return cursor.lastrowid, next_version

    @staticmethod
    def get_by_id(version_id):
        row = query_db(
            "SELECT v.*, u.username FROM document_versions v "
            "LEFT JOIN users u ON v.uploaded_by = u.id WHERE v.id = ?",
            (version_id,), one=True
        )
        return DocumentVersion.from_row(row)

    @staticmethod
    def get_by_document(document_id):
        rows = query_db(
            "SELECT v.*, u.username FROM document_versions v "
            "LEFT JOIN users u ON v.uploaded_by = u.id "
            "WHERE v.document_id = ? ORDER BY v.version_number DESC",
            (document_id,)
        )
        return [DocumentVersion.from_row(row) for row in rows]

    @staticmethod
    def get_latest_version_number(document_id):
        row = query_db(
            "SELECT MAX(version_number) as max_ver FROM document_versions WHERE document_id = ?",
            (document_id,), one=True
        )
        return row["max_ver"] or 0

    @staticmethod
    def delete(version_id):
        db = get_db()
        db.execute("DELETE FROM document_versions WHERE id = ?", (version_id,))
        db.commit()

    @staticmethod
    def count_by_document(document_id):
        row = query_db(
            "SELECT COUNT(*) as count FROM document_versions WHERE document_id = ?",
            (document_id,), one=True
        )
        return row["count"] if row else 0
