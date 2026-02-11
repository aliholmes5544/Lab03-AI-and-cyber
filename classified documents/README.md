# Classified Documents Management System

A secure web application for managing classified documents with role-based access control, granular permissions, and full audit logging. Built with Flask and SQLite.

## Features

- **Classification Levels** — Unclassified, Confidential, Secret, Top Secret
- **Granular Permissions** — Per-level read/write access control beyond clearance ceiling
- **Document Management** — Upload, download, preview (PDF, images, text, video, audio), and version history
- **Search** — Basic and advanced search with filters (classification, date range, tags, sorting)
- **Tags & Favorites** — Organize documents with color-coded tags and personal favorites
- **Comments** — Discuss documents with threaded comments
- **Expiration & Archiving** — Set document expiration dates with auto-archive support
- **Bulk Operations** — Bulk download (ZIP) and bulk delete
- **Admin Panel** — User management, permission control, audit log, and analytics dashboard
- **Audit Logging** — Tracks all user actions (uploads, downloads, views, deletions, etc.)
- **Bilingual** — English and Arabic with RTL support
- **Dark Mode** — Toggle between light and dark themes
- **REST API** — JSON API for programmatic access with permission enforcement

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/aliholmes5544/Lab03-AI-and-cyber.git
   cd "Lab03-AI-and-cyber/classified documents"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   ```bash
   python init_db.py
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

## Default Admin Account

| Field    | Value   |
|----------|---------|
| Username | `admin` |
| Password | `admin` |

> **Note:** For production, set the `ADMIN_PASSWORD` and `ADMIN_EMAIL` environment variables before initializing the database.

## Environment Variables

| Variable         | Description                        | Default                          |
|------------------|------------------------------------|----------------------------------|
| `SECRET_KEY`     | Flask secret key for sessions      | `dev-secret-key-change-in-production` |
| `ADMIN_PASSWORD` | Initial admin password             | `admin`                          |
| `ADMIN_EMAIL`    | Initial admin email                | `admin@example.com`              |

## Project Structure

```
classified documents/
├── app.py                  # Application factory
├── config.py               # Configuration
├── init_db.py              # Database initialization & migrations
├── translations.py         # English/Arabic translations
├── requirements.txt        # Python dependencies
├── models/                 # Database models
│   ├── user.py             # User model with permission checks
│   ├── document.py         # Document model with search/filter
│   ├── permission.py       # Granular permission system
│   ├── comment.py          # Document comments
│   ├── tag.py              # Tags and document-tag relations
│   ├── favorite.py         # User favorites
│   ├── version.py          # Document version history
│   ├── recently_viewed.py  # Recently viewed tracking
│   ├── audit_log.py        # Audit logging
│   └── database.py         # Database connection helpers
├── routes/                 # Route blueprints
│   ├── auth.py             # Login, register, logout
│   ├── documents.py        # Document CRUD, search, tags, etc.
│   ├── admin.py            # Admin panel (users, audit log)
│   └── api.py              # REST API endpoints
├── forms/                  # WTForms form classes
│   ├── auth_forms.py       # Login & registration forms
│   ├── document_forms.py   # Upload, search, tag forms
│   └── admin_forms.py      # User management forms
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base layout with navbar
│   ├── auth/               # Login & register pages
│   ├── documents/          # Document views (dashboard, detail, etc.)
│   ├── admin/              # Admin pages (users, audit log, analytics)
│   └── errors/             # Error pages (403, 404, 413)
├── static/                 # Static assets (CSS, images)
└── uploads/                # Uploaded document storage (git-ignored)
```

## API Endpoints

All API endpoints require authentication.

| Method | Endpoint                  | Description              |
|--------|---------------------------|--------------------------|
| GET    | `/api/documents`          | List accessible documents |
| GET    | `/api/documents/<id>`     | Get document details      |
| GET    | `/api/documents/search`   | Search documents          |
| GET    | `/api/me`                 | Current user info         |

## Classification Levels

| Level | Label          | Color   |
|-------|----------------|---------|
| 0     | Unclassified   | Green   |
| 1     | Confidential   | Blue    |
| 2     | Secret         | Yellow  |
| 3     | Top Secret     | Red     |

## License

This project is for educational purposes.
