import os
import uuid
import mimetypes

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_from_directory, abort, session)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from forms.document_forms import UploadForm, SearchForm, ClassificationForm
from models.document import Document
from models.user import User
from models.audit_log import AuditLog
from translations import get_translator

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/")
@login_required
def dashboard():
    page = request.args.get("page", 1, type=int)
    readable_levels = current_user.get_readable_levels()
    rows, total = Document.get_accessible_by_levels(readable_levels, page=page)
    total_pages = max(1, (total + 19) // 20)
    return render_template("documents/dashboard.html",
                           documents=rows, page=page, total_pages=total_pages,
                           total=total)


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

    AuditLog.log(current_user.id, "view", "document", doc_id,
                 f"Viewed: {doc.title}", request.remote_addr)

    return render_template("documents/detail.html", doc=doc,
                           classify_form=classify_form)


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

    # Delete file from disk
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.stored_filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    AuditLog.log(current_user.id, "delete", "document", doc_id,
                 f"Deleted: {doc.title}", request.remote_addr)

    Document.delete(doc_id)
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
