from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from forms.admin_forms import UserEditForm, UserAddForm
from models.user import User
from models.audit_log import AuditLog
from models.permission import Permission
from translations import get_translator

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
@login_required
def require_admin():
    if current_user.role != "admin":
        abort(403)


@admin_bp.route("/users")
def users():
    all_users = User.get_all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/add", methods=["GET", "POST"])
def user_add():
    t = get_translator(session.get("lang", "en"))
    form = UserAddForm()
    if form.validate_on_submit():
        password_hash = generate_password_hash(form.password.data)
        clearance = int(form.clearance.data)
        user_id = User.create(
            username=form.username.data,
            email=form.email.data,
            password_hash=password_hash,
            role=form.role.data,
            clearance=clearance,
        )

        # Handle permissions
        if form.grant_all_at_clearance.data:
            Permission.grant_all_at_clearance(user_id, clearance, current_user.id)
            perm_details = f"granted all permissions at clearance {clearance}"
        else:
            # Filter permissions to not exceed clearance level
            permissions = []
            for perm in form.permissions.data:
                level = int(perm.split("_")[1])
                if level <= clearance:
                    permissions.append(perm)
            Permission.set_permissions(user_id, permissions, current_user.id)
            perm_details = f"granted permissions: {permissions}"

        AuditLog.log(current_user.id, "add_user", "user", user_id,
                     f"Admin created user {form.username.data}: role={form.role.data}, "
                     f"clearance={form.clearance.data}, {perm_details}",
                     request.remote_addr)
        flash(t("flash_user_created", username=form.username.data), "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_add.html", form=form)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id):
    user = User.get_by_id(user_id)
    if user is None:
        abort(404)

    # Get current permissions
    current_permissions = user.get_permissions()

    form = UserEditForm(original_email=user.email, data={
        "email": user.email,
        "role": user.role,
        "clearance": str(user.clearance),
        "is_active": user.is_active,
        "permissions": current_permissions,
    })

    if form.validate_on_submit():
        t = get_translator(session.get("lang", "en"))
        clearance = int(form.clearance.data)
        update_data = {
            "email": form.email.data,
            "role": form.role.data,
            "clearance": clearance,
            "is_active": 1 if form.is_active.data else 0,
        }
        # Only update password if provided
        if form.password.data:
            update_data["password_hash"] = generate_password_hash(form.password.data)

        User.update(user_id, **update_data)

        # Handle permissions
        if form.grant_all_at_clearance.data:
            Permission.grant_all_at_clearance(user_id, clearance, current_user.id)
            perm_details = f"granted all permissions at clearance {clearance}"
        else:
            # Filter permissions to not exceed clearance level
            permissions = []
            for perm in form.permissions.data:
                level = int(perm.split("_")[1])
                if level <= clearance:
                    permissions.append(perm)
            Permission.set_permissions(user_id, permissions, current_user.id)
            perm_details = f"set permissions: {permissions}"

        details = f"Updated user {user.username}: email={form.email.data}, role={form.role.data}, clearance={form.clearance.data}, active={form.is_active.data}, {perm_details}"
        if form.password.data:
            details += ", password changed"

        AuditLog.log(current_user.id, "edit_user", "user", user_id,
                     details, request.remote_addr)
        flash(t("flash_user_updated", username=user.username), "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_edit.html", form=form, user=user)


@admin_bp.route("/audit-log")
def audit_log():
    page = request.args.get("page", 1, type=int)
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action", "")

    logs, total = AuditLog.get_logs(page=page, user_id=user_id,
                                    action=action if action else None)
    total_pages = max(1, (total + 49) // 50)

    return render_template("admin/audit_log.html", logs=logs, page=page,
                           total_pages=total_pages, total=total,
                           filter_user_id=user_id, filter_action=action)
