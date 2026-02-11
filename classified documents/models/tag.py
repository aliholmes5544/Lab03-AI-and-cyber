from models.database import get_db, query_db


class Tag:
    def __init__(self, id, name, color, created_by, created_at):
        self.id = id
        self.name = name
        self.color = color
        self.created_by = created_by
        self.created_at = created_at

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return Tag(
            id=row["id"],
            name=row["name"],
            color=row["color"],
            created_by=row["created_by"],
            created_at=row["created_at"],
        )

    @staticmethod
    def create(name, color, created_by):
        db = get_db()
        cursor = db.execute(
            "INSERT INTO tags (name, color, created_by) VALUES (?, ?, ?)",
            (name, color, created_by),
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_by_id(tag_id):
        row = query_db("SELECT * FROM tags WHERE id = ?", (tag_id,), one=True)
        return Tag.from_row(row)

    @staticmethod
    def get_by_name(name):
        row = query_db("SELECT * FROM tags WHERE name = ?", (name,), one=True)
        return Tag.from_row(row)

    @staticmethod
    def get_all():
        rows = query_db("SELECT * FROM tags ORDER BY name")
        return [Tag.from_row(row) for row in rows]

    @staticmethod
    def delete(tag_id):
        db = get_db()
        db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        db.commit()

    @staticmethod
    def update(tag_id, name, color):
        db = get_db()
        db.execute(
            "UPDATE tags SET name = ?, color = ? WHERE id = ?",
            (name, color, tag_id),
        )
        db.commit()


class DocumentTag:
    @staticmethod
    def add_tag(document_id, tag_id, added_by):
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO document_tags (document_id, tag_id, added_by) "
            "VALUES (?, ?, ?)",
            (document_id, tag_id, added_by),
        )
        db.commit()

    @staticmethod
    def remove_tag(document_id, tag_id):
        db = get_db()
        db.execute(
            "DELETE FROM document_tags WHERE document_id = ? AND tag_id = ?",
            (document_id, tag_id),
        )
        db.commit()

    @staticmethod
    def get_document_tags(document_id):
        rows = query_db(
            "SELECT t.* FROM tags t "
            "JOIN document_tags dt ON t.id = dt.tag_id "
            "WHERE dt.document_id = ? ORDER BY t.name",
            (document_id,)
        )
        return [Tag.from_row(row) for row in rows]

    @staticmethod
    def get_documents_by_tag(tag_id, user_clearance):
        rows = query_db(
            "SELECT d.* FROM documents d "
            "JOIN document_tags dt ON d.id = dt.document_id "
            "WHERE dt.tag_id = ? AND d.classification <= ? "
            "ORDER BY d.created_at DESC",
            (tag_id, user_clearance)
        )
        return rows

    @staticmethod
    def get_documents_by_tag_levels(tag_id, levels):
        """Get documents with a tag filtered by specific permission levels."""
        if not levels:
            return []
        placeholders = ",".join("?" * len(levels))
        rows = query_db(
            f"SELECT d.* FROM documents d "
            f"JOIN document_tags dt ON d.id = dt.document_id "
            f"WHERE dt.tag_id = ? AND d.classification IN ({placeholders}) "
            f"ORDER BY d.created_at DESC",
            [tag_id] + list(levels)
        )
        return rows

    @staticmethod
    def get_tag_counts():
        rows = query_db(
            "SELECT t.id, t.name, t.color, COUNT(dt.document_id) as doc_count "
            "FROM tags t LEFT JOIN document_tags dt ON t.id = dt.tag_id "
            "GROUP BY t.id ORDER BY t.name"
        )
        return rows
