import random
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from forms.auth_forms import LoginForm, RegistrationForm
from models.user import User
from models.audit_log import AuditLog
from translations import get_translator

auth_bp = Blueprint("auth", __name__)


def generate_captcha():
    """Generate a simple math captcha."""
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    session["captcha_answer"] = a + b
    return f"{a} + {b} = ?"


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("documents.dashboard"))

    t = get_translator(session.get("lang", "en"))
    form = LoginForm()
    captcha_question = None

    if request.method == "GET":
        captcha_question = generate_captcha()
    else:
        # Validate captcha first
        captcha_answer = request.form.get("captcha", "")
        expected_answer = session.get("captcha_answer")

        if not captcha_answer or not expected_answer:
            flash(t("captcha_invalid"), "danger")
            captcha_question = generate_captcha()
            return render_template("auth/login.html", form=form, captcha_question=captcha_question)

        try:
            if int(captcha_answer) != expected_answer:
                flash(t("captcha_invalid"), "danger")
                captcha_question = generate_captcha()
                return render_template("auth/login.html", form=form, captcha_question=captcha_question)
        except ValueError:
            flash(t("captcha_invalid"), "danger")
            captcha_question = generate_captcha()
            return render_template("auth/login.html", form=form, captcha_question=captcha_question)

        # Captcha valid, now check form
        if form.validate_on_submit():
            user = User.get_by_username(form.username.data)
            if user and check_password_hash(user.password_hash, form.password.data):
                if not user.is_active:
                    flash(t("flash_account_deactivated"), "danger")
                    captcha_question = generate_captcha()
                    return render_template("auth/login.html", form=form, captcha_question=captcha_question)
                login_user(user)
                AuditLog.log(user.id, "login", "user", user.id,
                             "User logged in", request.remote_addr)
                next_page = request.args.get("next")
                return redirect(next_page or url_for("documents.dashboard"))
            flash(t("flash_invalid_credentials"), "danger")

        captcha_question = generate_captcha()

    return render_template("auth/login.html", form=form, captcha_question=captcha_question)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("documents.dashboard"))

    t = get_translator(session.get("lang", "en"))
    form = RegistrationForm()
    if form.validate_on_submit():
        password_hash = generate_password_hash(form.password.data)
        user_id = User.create(
            username=form.username.data,
            email=form.email.data,
            password_hash=password_hash,
        )
        AuditLog.log(user_id, "register", "user", user_id,
                     f"User registered: {form.username.data}", request.remote_addr)
        flash(t("flash_register_success"), "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    t = get_translator(session.get("lang", "en"))
    AuditLog.log(current_user.id, "logout", "user", current_user.id,
                 "User logged out", request.remote_addr)
    logout_user()
    flash(t("flash_logged_out"), "info")
    return redirect(url_for("auth.login"))
