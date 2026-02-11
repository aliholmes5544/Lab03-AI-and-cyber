import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask import Flask, render_template, session, redirect, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import Config
from models.database import init_app as init_db_app
from models.user import User
from translations import get_translator


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Extensions
    csrf = CSRFProtect(app)
    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(int(user_id))

    # Database teardown
    init_db_app(app)

    # Template context - make classification levels and translations available everywhere
    @app.context_processor
    def inject_globals():
        lang = session.get("lang", "en")
        t = get_translator(lang)
        return {
            "classification_levels": app.config["CLASSIFICATION_LEVELS"],
            "t": t,
            "lang": lang,
        }

    @app.route("/set-language/<lang>")
    def set_language(lang):
        if lang in ("en", "ar"):
            session["lang"] = lang
        return redirect(request.referrer or "/")

    # Blueprints
    from routes.auth import auth_bp
    from routes.documents import documents_bp
    from routes.admin import admin_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Exempt API from CSRF
    csrf.exempt(api_bp)

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html"), 413

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False)
