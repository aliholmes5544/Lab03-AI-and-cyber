"""Comprehensive test suite for the Classified Documents Management System."""
import re
import io
import os

# Remove stale DB from prior test runs so we start fresh
DB_PATH = os.path.join(os.path.dirname(__file__), "classified.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

from init_db import init_db
init_db()

from app import create_app

app = create_app()


def get_csrf(html):
    match = re.search(r'name="csrf_token".*?value="(.+?)"', html)
    return match.group(1) if match else ""


def login(client, username, password):
    r = client.get("/login")
    token = get_csrf(r.data.decode())
    return client.post("/login", data={
        "username": username,
        "password": password,
        "csrf_token": token,
    }, follow_redirects=True)


passed = 0
failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")


with app.test_client() as c:
    # ── Phase 1: Auth ────────────────────────────────────
    print("\n=== Authentication ===")

    r = c.get("/login")
    check("Login page loads", r.status_code == 200)

    r = login(c, "admin", "admin")
    check("Admin login succeeds", r.status_code == 200 and b"Documents" in r.data)

    r = c.get("/")
    check("Dashboard loads after login", r.status_code == 200)

    r = c.get("/logout", follow_redirects=True)
    check("Logout works", r.status_code == 200)

    r = c.get("/register")
    token = get_csrf(r.data.decode())
    r = c.post("/register", data={
        "username": "analyst",
        "email": "analyst@example.com",
        "password": "password123",
        "confirm_password": "password123",
        "csrf_token": token,
    }, follow_redirects=True)
    check("User registration works", r.status_code == 200 and b"Registration successful" in r.data)

    r = login(c, "analyst", "password123")
    check("New user login works", r.status_code == 200)
    c.get("/logout")

    # ── Phase 2: Document Upload & View (as admin) ──────
    print("\n=== Document Management (admin) ===")

    login(c, "admin", "admin")

    r = c.get("/upload")
    check("Upload page loads", r.status_code == 200)

    # Upload Secret document
    token = get_csrf(r.data.decode())
    r = c.post("/upload", data={
        "title": "Secret Intel Report",
        "description": "Eyes only intelligence briefing",
        "classification": "2",
        "csrf_token": token,
        "file": (io.BytesIO(b"CLASSIFIED INTEL DATA"), "intel_report.pdf"),
    }, content_type="multipart/form-data", follow_redirects=True)
    check("Upload Secret document", r.status_code == 200 and b"Secret Intel Report" in r.data)

    # Upload Unclassified document
    r = c.get("/upload")
    token = get_csrf(r.data.decode())
    r = c.post("/upload", data={
        "title": "Public Memo",
        "description": "Nothing sensitive",
        "classification": "0",
        "csrf_token": token,
        "file": (io.BytesIO(b"Public info here"), "memo.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    check("Upload Unclassified document", r.status_code == 200 and b"Public Memo" in r.data)

    # Upload Top Secret document
    r = c.get("/upload")
    token = get_csrf(r.data.decode())
    r = c.post("/upload", data={
        "title": "Top Secret Plan",
        "description": "Nuclear launch codes",
        "classification": "3",
        "csrf_token": token,
        "file": (io.BytesIO(b"LAUNCH CODE: 0000"), "topsecret.dat"),
    }, content_type="multipart/form-data", follow_redirects=True)
    check("Upload Top Secret document", r.status_code == 200 and b"Top Secret Plan" in r.data)

    # Get doc IDs from API
    r = c.get("/api/documents")
    docs_data = r.get_json()
    check("API lists 3 documents", docs_data["total"] == 3)

    secret_id = None
    unclass_id = None
    topsecret_id = None
    for d in docs_data["documents"]:
        if d["classification"] == 2:
            secret_id = d["id"]
        elif d["classification"] == 0:
            unclass_id = d["id"]
        elif d["classification"] == 3:
            topsecret_id = d["id"]

    # View document detail
    r = c.get(f"/document/{secret_id}")
    check("Document detail page loads", r.status_code == 200 and b"Secret Intel Report" in r.data)

    # Download document
    r = c.get(f"/document/{secret_id}/download")
    check("Document download works", r.status_code == 200 and b"CLASSIFIED INTEL DATA" in r.data)

    # ── Phase 3: Search ─────────────────────────────────
    print("\n=== Search ===")

    r = c.get("/search")
    check("Search page loads", r.status_code == 200)

    r = c.get("/search?q=Intel&c=")
    check("Search by keyword", r.status_code == 200 and b"Secret Intel Report" in r.data)

    r = c.get("/search?q=&c=0")
    check("Search by classification", r.status_code == 200 and b"Public Memo" in r.data)

    r = c.get("/search?q=nonexistent&c=")
    check("Search with no results", r.status_code == 200 and b"No documents match" in r.data)

    # ── Phase 4: Classification Change (admin) ──────────
    print("\n=== Classification Management ===")

    r = c.get(f"/document/{unclass_id}")
    token = get_csrf(r.data.decode())
    r = c.post(f"/document/{unclass_id}/classify", data={
        "classification": "1",
        "csrf_token": token,
    }, follow_redirects=True)
    check("Admin can change classification", r.status_code == 200)

    # Verify via API
    r = c.get(f"/api/documents/{unclass_id}")
    check("Classification updated to Confidential", r.get_json()["classification"] == 1)

    # Change it back for later tests
    r = c.get(f"/document/{unclass_id}")
    token = get_csrf(r.data.decode())
    c.post(f"/document/{unclass_id}/classify", data={
        "classification": "0",
        "csrf_token": token,
    }, follow_redirects=True)

    # ── Phase 5: Admin Panel ────────────────────────────
    print("\n=== Admin Panel ===")

    r = c.get("/admin/users")
    check("Admin users page loads", r.status_code == 200 and b"admin" in r.data and b"analyst" in r.data)

    # Find analyst user ID
    from models.user import User
    with app.app_context():
        analyst = User.get_by_username("analyst")
        analyst_id = analyst.id

    r = c.get(f"/admin/users/{analyst_id}/edit")
    check("User edit page loads", r.status_code == 200)

    # Upgrade analyst clearance to Secret (2)
    token = get_csrf(r.data.decode())
    r = c.post(f"/admin/users/{analyst_id}/edit", data={
        "role": "user",
        "clearance": "2",
        "is_active": "y",
        "csrf_token": token,
    }, follow_redirects=True)
    check("Update user clearance", r.status_code == 200 and b"updated" in r.data.lower())

    r = c.get("/admin/audit-log")
    check("Audit log page loads", r.status_code == 200)

    r = c.get("/admin/audit-log?action=upload")
    check("Audit log filtering by action", r.status_code == 200)

    r = c.get(f"/admin/audit-log?user_id={analyst_id}")
    check("Audit log filtering by user", r.status_code == 200)

    # ── Phase 6: Clearance Enforcement ──────────────────
    print("\n=== Clearance Enforcement ===")

    c.get("/logout")
    login(c, "analyst", "password123")

    # Analyst now has clearance 2 (Secret)
    r = c.get("/")
    check("Analyst sees Unclassified docs", b"Public Memo" in r.data)
    check("Analyst sees Secret docs", b"Secret Intel Report" in r.data)
    check("Analyst cannot see Top Secret docs", b"Top Secret Plan" not in r.data)

    r = c.get(f"/document/{secret_id}")
    check("Analyst can access Secret doc detail", r.status_code == 200)

    r = c.get(f"/document/{topsecret_id}")
    check("Analyst blocked from Top Secret doc (403)", r.status_code == 403)

    r = c.get(f"/document/{topsecret_id}/download")
    check("Analyst blocked from Top Secret download (403)", r.status_code == 403)

    # API clearance enforcement
    r = c.get("/api/documents")
    api_docs = r.get_json()["documents"]
    max_class = max(d["classification"] for d in api_docs) if api_docs else -1
    check("API respects clearance filter", max_class <= 2)

    r = c.get(f"/api/documents/{topsecret_id}")
    check("API blocks Top Secret doc (403)", r.status_code == 403)

    # ── Phase 7: Authorization ──────────────────────────
    print("\n=== Authorization ===")

    r = c.get("/admin/users")
    check("Non-admin blocked from admin pages (403)", r.status_code == 403)

    r = c.get("/admin/audit-log")
    check("Non-admin blocked from audit log (403)", r.status_code == 403)

    # Non-admin cannot classify documents
    # Get CSRF token from upload page (always has a form for authenticated users)
    r = c.get("/upload")
    token = get_csrf(r.data.decode())
    r = c.post(f"/document/{secret_id}/classify", data={
        "classification": "0",
        "csrf_token": token,
    }, follow_redirects=True)
    check("Non-admin blocked from classifying (403)", r.status_code == 403)

    # Non-admin cannot delete documents
    r = c.post(f"/document/{secret_id}/delete", data={
        "csrf_token": token,
    }, follow_redirects=True)
    check("Non-admin blocked from deleting (403)", r.status_code == 403)

    # ── Phase 8: REST API ───────────────────────────────
    print("\n=== REST API ===")

    r = c.get("/api/me")
    me = r.get_json()
    check("API /me returns current user", me["username"] == "analyst" and me["clearance"] == 2)

    r = c.get("/api/documents?per_page=1")
    data = r.get_json()
    check("API pagination works", len(data["documents"]) == 1 and data["total"] >= 2)

    r = c.get("/api/documents/search?q=Intel")
    data = r.get_json()
    check("API search works", data["total"] >= 1)

    r = c.get("/api/documents/search?classification=0")
    data = r.get_json()
    check("API search with classification filter", all(d["classification"] == 0 for d in data["documents"]))

    r = c.get("/api/documents/99999")
    check("API returns 404 for missing doc", r.status_code == 404)

    # ── Phase 9: Error Pages ────────────────────────────
    print("\n=== Error Pages ===")

    r = c.get("/this-does-not-exist")
    check("404 error page", r.status_code == 404)

    # ── Phase 10: Document Deletion (as admin) ──────────
    print("\n=== Document Deletion ===")

    c.get("/logout")
    login(c, "admin", "admin")

    # Delete the unclassified doc
    r = c.get(f"/document/{unclass_id}")
    token = get_csrf(r.data.decode())
    r = c.post(f"/document/{unclass_id}/delete", data={
        "csrf_token": token,
    }, follow_redirects=True)
    check("Admin can delete document", r.status_code == 200)

    r = c.get(f"/document/{unclass_id}")
    check("Deleted doc returns 404", r.status_code == 404)

    # ── Phase 11: Unauthenticated Access ────────────────
    print("\n=== Unauthenticated Access ===")

    c.get("/logout")

    r = c.get("/", follow_redirects=True)
    check("Unauthenticated redirected to login", r.status_code == 200 and b"Login" in r.data)

    r = c.get("/upload", follow_redirects=True)
    check("Unauthenticated cannot upload", b"Login" in r.data)

    r = c.get("/api/documents")
    check("Unauthenticated API returns 401", r.status_code == 401)

    # ── Summary ─────────────────────────────────────────
    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    if failed == 0:
        print("ALL TESTS PASSED")
    print(f"{'=' * 50}")

    exit(0 if failed == 0 else 1)
