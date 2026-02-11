import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DATABASE = os.path.join(BASE_DIR, "classified.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

    CLASSIFICATION_LEVELS = {
        0: {"label": "Unclassified", "color": "success"},
        1: {"label": "Confidential", "color": "info"},
        2: {"label": "Secret", "color": "warning"},
        3: {"label": "Top Secret", "color": "danger"},
    }
