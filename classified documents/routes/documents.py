import logging
import os
import io
import uuid
import mimetypes
import zipfile
from datetime import datetime

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_from_directory, abort, session,
                   send_file, jsonify, Response)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

from forms.document_forms import (UploadForm, SearchForm, ClassificationForm,
                                  CommentForm, TagForm, AddTagForm, ReuploadForm,
                                  BulkActionForm, AdvancedSearchForm, ExpirationForm)
from models.document import Document
from models.user import User
from models.audit_log import AuditLog
from models.comment import Comment
from models.tag import Tag, DocumentTag
from models.favorite import Favorite
from models.version import DocumentVersion
from models.recently_viewed import RecentlyViewed
from translations import get_translator

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/")
@login_required
def dashboard():
    page = request.args.get("page", 1, type=int)
    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    readable_levels = current_user.get_readable_levels()
    rows, total = Document.get_accessible_by_levels_sorted(
        readable_levels, sort_by=sort_by, sort_order=sort_order,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
        page=page
    )
    total_pages = max(1, (total + 19) // 20)

    # Get user's favorites for highlighting
    favorite_ids = Favorite.get_user_favorite_ids(current_user.id)

    # Get tags for each document
    doc_tags = {}
    for doc in rows:
        doc_tags[doc["id"]] = DocumentTag.get_document_tags(doc["id"])

    return render_template("documents/dashboard.html",
                           documents=rows, page=page, total_pages=total_pages,
                           total=total, favorite_ids=favorite_ids, doc_tags=doc_tags,
                           sort_by=sort_by, sort_order=sort_order,
                           date_from=date_from, date_to=date_to)


@documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    t = get_translator(session.get("lang", "en"))
    form = UploadForm()
    if form.validate_on_submit():
        classification = int(form.classification.data)
        if not current_user.can_write(classification):
            flash(t("flash_no_write_permission"), "danger")
            return render_template("documents/upload.html", form=form)

        file = form.file.data
        original_filename = secure_filename(file.filename)
        if not original_filename:
            original_filename = "unnamed_file"

        ext = os.path.splitext(original_filename)[1]
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_filename)

        file.save(filepath)
        file_size = os.path.getsize(filepath)
        mime_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"

        doc_id = Document.create(
            title=form.title.data,
            description=form.description.data,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            mime_type=mime_type,
            classification=classification,
            uploaded_by=current_user.id,
        )

        AuditLog.log(current_user.id, "upload", "document", doc_id,
                     f"Uploaded: {form.title.data} [{classification}]",
                     request.remote_addr)

        flash(t("flash_upload_success"), "success")
        return redirect(url_for("documents.detail", doc_id=doc_id))
    return render_template("documents/upload.html", form=form)


@documents_bp.route("/document/<int:doc_id>")
@login_required
def detail(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    classify_form = ClassificationForm(data={"classification": str(doc.classification)})
    comment_form = CommentForm()
    expiration_form = ExpirationForm()
    if doc.expires_at:
        try:
            expiration_form.expires_at.data = datetime.fromisoformat(doc.expires_at).date()
        except (ValueError, TypeError):
            pass

    # Get related data
    comments = Comment.get_by_document(doc_id)
    tags = DocumentTag.get_document_tags(doc_id)
    is_favorite = Favorite.is_favorite(current_user.id, doc_id)
    versions = DocumentVersion.get_by_document(doc_id)
    version_count = len(versions)

    # Add tag form with available tags
    all_tags = Tag.get_all()
    add_tag_form = AddTagForm()
    add_tag_form.tag_id.choices = [(t.id, t.name) for t in all_tags]

    # Record recently viewed
    RecentlyViewed.record(current_user.id, doc_id)

    AuditLog.log(current_user.id, "view", "document", doc_id,
                 f"Viewed: {doc.title}", request.remote_addr)

    return render_template("documents/detail.html", doc=doc,
                           classify_form=classify_form, comment_form=comment_form,
                           comments=comments, tags=tags, is_favorite=is_favorite,
                           versions=versions, version_count=version_count,
                           add_tag_form=add_tag_form, expiration_form=expiration_form)


@documents_bp.route("/document/<int:doc_id>/download")
@login_required
def download(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    AuditLog.log(current_user.id, "download", "document", doc_id,
                 f"Downloaded: {doc.title}", request.remote_addr)

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        doc.stored_filename,
        as_attachment=True,
        download_name=doc.original_filename,
    )


@documents_bp.route("/document/<int:doc_id>/classify", methods=["POST"])
@login_required
def classify(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if current_user.role != "admin":
        abort(403)

    t = get_translator(session.get("lang", "en"))
    form = ClassificationForm()
    if form.validate_on_submit():
        new_classification = int(form.classification.data)
        old_classification = doc.classification
        Document.update_classification(doc_id, new_classification)

        AuditLog.log(current_user.id, "classify", "document", doc_id,
                     f"Changed classification: {old_classification} -> {new_classification}",
                     request.remote_addr)

        flash(t("flash_classification_updated"), "success")
    return redirect(url_for("documents.detail", doc_id=doc_id))


@documents_bp.route("/document/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if current_user.role != "admin":
        abort(403)

    t = get_translator(session.get("lang", "en"))

    AuditLog.log(current_user.id, "delete", "document", doc_id,
                 f"Deleted: {doc.title}", request.remote_addr)

    Document.delete(doc_id)

    # Delete file from disk after DB record is removed
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.stored_filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        logger.warning("Failed to delete file %s for document %d", filepath, doc_id)
    flash(t("flash_document_deleted"), "success")
    return redirect(url_for("documents.dashboard"))


@documents_bp.route("/search", methods=["GET", "POST"])
@login_required
def search():
    form = SearchForm()
    documents = []
    total = 0
    page = request.args.get("page", 1, type=int)
    total_pages = 1

    if request.method == "POST" and form.validate_on_submit():
        query = form.query.data
        classification = form.classification.data
        return redirect(url_for("documents.search", q=query, c=classification))

    # GET with query params
    q = request.args.get("q", "")
    c = request.args.get("c", "")
    if q or c:
        form.query.data = q
        form.classification.data = c
        readable_levels = current_user.get_readable_levels()
        documents, total = Document.search_by_levels(
            readable_levels, q, c if c else None, page=page
        )
        total_pages = max(1, (total + 19) // 20)

        AuditLog.log(current_user.id, "search", "document", None,
                     f"Search: q='{q}' c='{c}'", request.remote_addr)

    return render_template("documents/search.html", form=form,
                           documents=documents, total=total, page=page,
                           total_pages=total_pages, q=q, c=c)


@documents_bp.route("/analytics")
@login_required
def analytics():
    if current_user.role != "admin":
        abort(403)

    # User statistics
    total_users = User.count_all()
    active_users = User.count_active()
    users_by_role = User.count_by_role()
    users_by_clearance = User.count_by_clearance()

    # Document statistics
    total_documents = Document.count_all()
    total_storage = Document.total_storage()
    docs_by_classification = Document.count_by_classification()

    # Activity statistics
    logins_today = AuditLog.count_today("login")
    uploads_today = AuditLog.count_today("upload")
    recent_activity = AuditLog.get_recent(10)

    return render_template("documents/analytics.html",
                           total_users=total_users,
                           active_users=active_users,
                           users_by_role=users_by_role,
                           users_by_clearance=users_by_clearance,
                           total_documents=total_documents,
                           total_storage=total_storage,
                           docs_by_classification=docs_by_classification,
                           logins_today=logins_today,
                           uploads_today=uploads_today,
                           recent_activity=recent_activity)


# ===================== PREVIEW =====================

@documents_bp.route("/document/<int:doc_id>/preview")
@login_required
def preview(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    AuditLog.log(current_user.id, "preview", "document", doc_id,
                 f"Preview: {doc.title}", request.remote_addr)

    # Determine preview type based on mime type
    mime = doc.mime_type or ""
    preview_type = "unsupported"

    if mime.startswith("image/"):
        preview_type = "image"
    elif mime == "application/pdf":
        preview_type = "pdf"
    elif mime.startswith("text/") or mime in ["application/json", "application/xml",
                                               "application/javascript"]:
        preview_type = "text"
        # Read text content
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.stored_filename)
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                text_content = f.read(100000)  # Limit to 100KB
        except Exception:
            text_content = "Unable to read file content."
        return render_template("documents/preview.html", doc=doc, preview_type=preview_type,
                               text_content=text_content)
    elif mime.startswith("video/"):
        preview_type = "video"
    elif mime.startswith("audio/"):
        preview_type = "audio"

    return render_template("documents/preview.html", doc=doc, preview_type=preview_type)


@documents_bp.route("/document/<int:doc_id>/raw")
@login_required
def raw_file(doc_id):
    """Serve file for inline viewing (preview)."""
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        doc.stored_filename,
        mimetype=doc.mime_type,
    )


# ===================== COMMENTS =====================

@documents_bp.route("/document/<int:doc_id>/comments", methods=["POST"])
@login_required
def add_comment(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    t = get_translator(session.get("lang", "en"))
    form = CommentForm()
    if form.validate_on_submit():
        Comment.create(doc_id, current_user.id, form.content.data)
        AuditLog.log(current_user.id, "comment", "document", doc_id,
                     f"Added comment on: {doc.title}", request.remote_addr)
        flash(t("flash_comment_added"), "success")

    return redirect(url_for("documents.detail", doc_id=doc_id))


@documents_bp.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.get_by_id(comment_id)
    if comment is None:
        abort(404)

    # Only comment owner or admin can delete
    if comment.user_id != current_user.id and current_user.role != "admin":
        abort(403)

    doc_id = comment.document_id
    t = get_translator(session.get("lang", "en"))

    Comment.delete(comment_id)
    AuditLog.log(current_user.id, "delete_comment", "comment", comment_id,
                 f"Deleted comment", request.remote_addr)
    flash(t("flash_comment_deleted"), "success")

    return redirect(url_for("documents.detail", doc_id=doc_id))


# ===================== TAGS =====================

@documents_bp.route("/tags")
@login_required
def tags():
    all_tags = Tag.get_all()
    tag_counts = {row["id"]: row["doc_count"] for row in DocumentTag.get_tag_counts()}
    tag_form = TagForm()
    return render_template("documents/tags.html", tags=all_tags,
                           tag_counts=tag_counts, tag_form=tag_form)


@documents_bp.route("/tags/create", methods=["POST"])
@login_required
def create_tag():
    t = get_translator(session.get("lang", "en"))
    form = TagForm()
    if form.validate_on_submit():
        existing = Tag.get_by_name(form.name.data.strip())
        if existing:
            flash(t("flash_tag_exists"), "warning")
        else:
            Tag.create(form.name.data.strip(), form.color.data, current_user.id)
            AuditLog.log(current_user.id, "create_tag", "tag", None,
                         f"Created tag: {form.name.data}", request.remote_addr)
            flash(t("flash_tag_created"), "success")
    return redirect(url_for("documents.tags"))


@documents_bp.route("/tags/<int:tag_id>/delete", methods=["POST"])
@login_required
def delete_tag(tag_id):
    tag = Tag.get_by_id(tag_id)
    if tag is None:
        abort(404)

    # Only admins can delete tags
    if current_user.role != "admin":
        abort(403)

    t = get_translator(session.get("lang", "en"))
    Tag.delete(tag_id)
    AuditLog.log(current_user.id, "delete_tag", "tag", tag_id,
                 f"Deleted tag: {tag.name}", request.remote_addr)
    flash(t("flash_tag_deleted"), "success")
    return redirect(url_for("documents.tags"))


@documents_bp.route("/tags/<int:tag_id>")
@login_required
def tag_documents(tag_id):
    tag = Tag.get_by_id(tag_id)
    if tag is None:
        abort(404)

    readable_levels = current_user.get_readable_levels()
    # Get documents with this tag that user can access
    documents = DocumentTag.get_documents_by_tag_levels(tag_id, readable_levels)

    return render_template("documents/tag_documents.html", tag=tag, documents=documents)


@documents_bp.route("/document/<int:doc_id>/tags", methods=["POST"])
@login_required
def add_document_tag(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    t = get_translator(session.get("lang", "en"))
    form = AddTagForm()
    form.tag_id.choices = [(t.id, t.name) for t in Tag.get_all()]

    if form.validate_on_submit():
        DocumentTag.add_tag(doc_id, form.tag_id.data, current_user.id)
        AuditLog.log(current_user.id, "add_tag", "document", doc_id,
                     f"Added tag to: {doc.title}", request.remote_addr)
        flash(t("flash_tag_added"), "success")

    return redirect(url_for("documents.detail", doc_id=doc_id))


@documents_bp.route("/document/<int:doc_id>/tags/<int:tag_id>/remove", methods=["POST"])
@login_required
def remove_document_tag(doc_id, tag_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    t = get_translator(session.get("lang", "en"))
    DocumentTag.remove_tag(doc_id, tag_id)
    AuditLog.log(current_user.id, "remove_tag", "document", doc_id,
                 f"Removed tag from: {doc.title}", request.remote_addr)
    flash(t("flash_tag_removed"), "success")

    return redirect(url_for("documents.detail", doc_id=doc_id))


# ===================== FAVORITES =====================

@documents_bp.route("/document/<int:doc_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    t = get_translator(session.get("lang", "en"))
    is_now_favorite = Favorite.toggle(current_user.id, doc_id)

    if is_now_favorite:
        AuditLog.log(current_user.id, "favorite", "document", doc_id,
                     f"Favorited: {doc.title}", request.remote_addr)
        flash(t("flash_favorited"), "success")
    else:
        AuditLog.log(current_user.id, "unfavorite", "document", doc_id,
                     f"Unfavorited: {doc.title}", request.remote_addr)
        flash(t("flash_unfavorited"), "info")

    # Check if AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"is_favorite": is_now_favorite})

    return redirect(request.referrer or url_for("documents.detail", doc_id=doc_id))


@documents_bp.route("/favorites")
@login_required
def favorites():
    page = request.args.get("page", 1, type=int)
    readable_levels = current_user.get_readable_levels()

    rows, total = Favorite.get_user_favorites_by_levels(current_user.id, readable_levels, page=page)
    total_pages = max(1, (total + 19) // 20)

    return render_template("documents/favorites.html",
                           documents=rows, page=page, total_pages=total_pages,
                           total=total)


# ===================== VERSION HISTORY =====================

@documents_bp.route("/document/<int:doc_id>/versions")
@login_required
def versions(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    versions = DocumentVersion.get_by_document(doc_id)
    return render_template("documents/versions.html", doc=doc, versions=versions)


@documents_bp.route("/document/<int:doc_id>/reupload", methods=["GET", "POST"])
@login_required
def reupload(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if not current_user.can_write(doc.classification):
        abort(403)

    t = get_translator(session.get("lang", "en"))
    form = ReuploadForm()

    if form.validate_on_submit():
        file = form.file.data
        original_filename = secure_filename(file.filename)
        if not original_filename:
            original_filename = doc.original_filename

        # Save old version info
        DocumentVersion.create(
            doc_id, doc.stored_filename, doc.file_size,
            current_user.id, form.change_notes.data
        )

        # Save new file
        ext = os.path.splitext(original_filename)[1]
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_filename)
        file.save(filepath)
        file_size = os.path.getsize(filepath)
        mime_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"

        # Update document
        Document.update_file(doc_id, stored_filename, file_size, mime_type)

        AuditLog.log(current_user.id, "reupload", "document", doc_id,
                     f"New version uploaded: {doc.title}", request.remote_addr)

        flash(t("flash_version_uploaded"), "success")
        return redirect(url_for("documents.detail", doc_id=doc_id))

    return render_template("documents/reupload.html", doc=doc, form=form)


@documents_bp.route("/version/<int:version_id>/download")
@login_required
def download_version(version_id):
    version = DocumentVersion.get_by_id(version_id)
    if version is None:
        abort(404)

    doc = Document.get_by_id(version.document_id)
    if doc is None:
        abort(404)
    if not current_user.can_read(doc.classification):
        abort(403)

    AuditLog.log(current_user.id, "download_version", "version", version_id,
                 f"Downloaded version {version.version_number} of: {doc.title}",
                 request.remote_addr)

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        version.stored_filename,
        as_attachment=True,
        download_name=f"v{version.version_number}_{doc.original_filename}",
    )


# ===================== RECENTLY VIEWED =====================

@documents_bp.route("/recent")
@login_required
def recent():
    page = request.args.get("page", 1, type=int)
    readable_levels = current_user.get_readable_levels()

    rows, total = RecentlyViewed.get_recent_paginated_by_levels(
        current_user.id, readable_levels, page=page
    )
    total_pages = max(1, (total + 19) // 20)

    return render_template("documents/recent.html",
                           documents=rows, page=page, total_pages=total_pages,
                           total=total)


# ===================== EXPIRATION =====================

@documents_bp.route("/document/<int:doc_id>/expiration", methods=["POST"])
@login_required
def set_expiration(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)

    # Only admin can set expiration
    if current_user.role != "admin":
        abort(403)

    t = get_translator(session.get("lang", "en"))
    form = ExpirationForm()

    if form.validate_on_submit():
        expires_at = form.expires_at.data
        if expires_at:
            Document.set_expiration(doc_id, expires_at.isoformat())
            AuditLog.log(current_user.id, "set_expiration", "document", doc_id,
                         f"Set expiration to {expires_at}: {doc.title}", request.remote_addr)
            flash(t("flash_expiration_set"), "success")
        else:
            Document.set_expiration(doc_id, None)
            AuditLog.log(current_user.id, "clear_expiration", "document", doc_id,
                         f"Cleared expiration: {doc.title}", request.remote_addr)
            flash(t("flash_expiration_cleared"), "info")

    return redirect(url_for("documents.detail", doc_id=doc_id))


@documents_bp.route("/expiring")
@login_required
def expiring():
    page = request.args.get("page", 1, type=int)
    days = request.args.get("days", 7, type=int)
    readable_levels = current_user.get_readable_levels()

    rows, total = Document.get_expiring_by_levels(readable_levels, days=days, page=page)
    total_pages = max(1, (total + 19) // 20)

    return render_template("documents/expiring.html",
                           documents=rows, page=page, total_pages=total_pages,
                           total=total, days=days)


@documents_bp.route("/document/<int:doc_id>/archive", methods=["POST"])
@login_required
def archive_document(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if current_user.role != "admin":
        abort(403)

    t = get_translator(session.get("lang", "en"))
    Document.archive(doc_id)
    AuditLog.log(current_user.id, "archive", "document", doc_id,
                 f"Archived: {doc.title}", request.remote_addr)
    flash(t("flash_document_archived"), "success")
    return redirect(url_for("documents.dashboard"))


@documents_bp.route("/document/<int:doc_id>/unarchive", methods=["POST"])
@login_required
def unarchive_document(doc_id):
    doc = Document.get_by_id(doc_id)
    if doc is None:
        abort(404)
    if current_user.role != "admin":
        abort(403)

    t = get_translator(session.get("lang", "en"))
    Document.unarchive(doc_id)
    AuditLog.log(current_user.id, "unarchive", "document", doc_id,
                 f"Unarchived: {doc.title}", request.remote_addr)
    flash(t("flash_document_unarchived"), "success")
    return redirect(url_for("documents.archived"))


@documents_bp.route("/archived")
@login_required
def archived():
    if current_user.role != "admin":
        abort(403)

    page = request.args.get("page", 1, type=int)
    readable_levels = current_user.get_readable_levels()

    rows, total = Document.get_archived_by_levels(readable_levels, page=page)
    total_pages = max(1, (total + 19) // 20)

    return render_template("documents/archived.html",
                           documents=rows, page=page, total_pages=total_pages,
                           total=total)


# ===================== BULK ACTIONS =====================

@documents_bp.route("/bulk/download", methods=["POST"])
@login_required
def bulk_download():
    doc_ids = request.form.get("document_ids", "")
    if not doc_ids:
        return redirect(url_for("documents.dashboard"))

    doc_id_list = [int(x) for x in doc_ids.split(",") if x.strip().isdigit()]
    readable_levels = current_user.get_readable_levels()
    max_clearance = max(readable_levels) if readable_levels else -1

    documents = Document.get_by_ids(doc_id_list, max_clearance)
    if not documents:
        t = get_translator(session.get("lang", "en"))
        flash(t("flash_no_documents_selected"), "warning")
        return redirect(url_for("documents.dashboard"))

    # Create ZIP file in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for doc in documents:
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], doc["stored_filename"])
            if os.path.exists(filepath):
                zf.write(filepath, doc["original_filename"])

    memory_file.seek(0)

    AuditLog.log(current_user.id, "bulk_download", "document", None,
                 f"Bulk downloaded {len(documents)} documents", request.remote_addr)

    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name="documents.zip"
    )


@documents_bp.route("/bulk/delete", methods=["POST"])
@login_required
def bulk_delete():
    if current_user.role != "admin":
        abort(403)

    t = get_translator(session.get("lang", "en"))
    doc_ids = request.form.get("document_ids", "")
    if not doc_ids:
        flash(t("flash_no_documents_selected"), "warning")
        return redirect(url_for("documents.dashboard"))

    doc_id_list = [int(x) for x in doc_ids.split(",") if x.strip().isdigit()]
    readable_levels = current_user.get_readable_levels()
    max_clearance = max(readable_levels) if readable_levels else -1

    documents = Document.get_by_ids(doc_id_list, max_clearance)

    # Delete from database first
    deleted_count = Document.bulk_delete(doc_id_list)

    # Then delete files from disk
    for doc in documents:
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], doc["stored_filename"])
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            logger.warning("Failed to delete file %s", filepath)

    AuditLog.log(current_user.id, "bulk_delete", "document", None,
                 f"Bulk deleted {deleted_count} documents", request.remote_addr)

    flash(t("flash_bulk_deleted").format(count=deleted_count), "success")
    return redirect(url_for("documents.dashboard"))


# ===================== ADVANCED SEARCH =====================

@documents_bp.route("/advanced-search", methods=["GET", "POST"])
@login_required
def advanced_search():
    all_tags = Tag.get_all()
    form = AdvancedSearchForm()
    form.tag_id.choices = [("", "All Tags")] + [(t.id, t.name) for t in all_tags]

    documents = []
    total = 0
    page = request.args.get("page", 1, type=int)
    total_pages = 1

    # Get filter params from URL or form
    q = request.args.get("q", "")
    c = request.args.get("c", "")
    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    tag_id = request.args.get("tag_id", "", type=int) or None

    if request.method == "POST" and form.validate_on_submit():
        return redirect(url_for("documents.advanced_search",
                                q=form.query.data or "",
                                c=form.classification.data or "",
                                sort_by=form.sort_by.data,
                                sort_order=form.sort_order.data,
                                date_from=form.date_from.data.isoformat() if form.date_from.data else "",
                                date_to=form.date_to.data.isoformat() if form.date_to.data else "",
                                tag_id=form.tag_id.data or ""))

    # Populate form with URL params
    form.query.data = q
    form.classification.data = c
    form.sort_by.data = sort_by
    form.sort_order.data = sort_order
    if date_from:
        try:
            form.date_from.data = datetime.fromisoformat(date_from).date()
        except ValueError:
            pass
    if date_to:
        try:
            form.date_to.data = datetime.fromisoformat(date_to).date()
        except ValueError:
            pass
    form.tag_id.data = tag_id

    # Perform search if any filter is active
    if q or c or date_from or date_to or tag_id:
        readable_levels = current_user.get_readable_levels()
        max_clearance = max(readable_levels) if readable_levels else -1

        documents, total = Document.search_advanced(
            max_clearance, query=q if q else None,
            classification=c if c else None,
            sort_by=sort_by, sort_order=sort_order,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
            tag_id=tag_id,
            page=page
        )
        total_pages = max(1, (total + 19) // 20)

        AuditLog.log(current_user.id, "advanced_search", "document", None,
                     f"Advanced search: q='{q}' c='{c}' sort={sort_by}",
                     request.remote_addr)

    return render_template("documents/advanced_search.html", form=form,
                           documents=documents, total=total, page=page,
                           total_pages=total_pages, q=q, c=c,
                           sort_by=sort_by, sort_order=sort_order,
                           date_from=date_from, date_to=date_to, tag_id=tag_id)
