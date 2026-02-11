from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from models.document import Document
from models.audit_log import AuditLog

api_bp = Blueprint("api", __name__)


@api_bp.before_request
def require_auth():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401


def classification_label(level):
    levels = current_app.config.get("CLASSIFICATION_LEVELS", {})
    entry = levels.get(level)
    if entry:
        return entry["label"]
    return "Unknown"


def _get(obj, key):
    try:
        return obj[key]
    except TypeError:
        return getattr(obj, key)


def doc_to_dict(row):
    return {
        "id": _get(row, "id"),
        "title": _get(row, "title"),
        "description": _get(row, "description"),
        "original_filename": _get(row, "original_filename"),
        "file_size": _get(row, "file_size"),
        "mime_type": _get(row, "mime_type"),
        "classification": _get(row, "classification"),
        "classification_label": classification_label(_get(row, "classification")),
        "created_at": _get(row, "created_at"),
        "updated_at": _get(row, "updated_at"),
    }


@api_bp.route("/documents")
def list_documents():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    readable_levels = current_user.get_readable_levels()
    rows, total = Document.get_accessible_by_levels(readable_levels, page=page,
                                                     per_page=per_page)

    return jsonify({
        "documents": [doc_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    })


@api_bp.route("/documents/<int:doc_id>")
def get_document(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        return jsonify({"error": "Document not found"}), 404
    if not current_user.can_read(doc.classification):
        return jsonify({"error": "Insufficient clearance"}), 403

    AuditLog.log(current_user.id, "api_view", "document", doc_id,
                 f"API view: {doc.title}", request.remote_addr)

    return jsonify(doc_to_dict(doc))


@api_bp.route("/documents/search")
def search_documents():
    q = request.args.get("q", "")
    c = request.args.get("classification", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    readable_levels = current_user.get_readable_levels()
    rows, total = Document.search_by_levels(
        readable_levels, q, c if c else None, page=page, per_page=per_page
    )

    return jsonify({
        "documents": [doc_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "query": q,
        "classification_filter": c,
    })


@api_bp.route("/me")
def me():
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "clearance": current_user.clearance,
        "clearance_label": classification_label(current_user.clearance),
    })
