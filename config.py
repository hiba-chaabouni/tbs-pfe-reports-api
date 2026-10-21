"""Central settings for the TBS PFE API. Change values here, not in the code."""
import os

# Auto-reload while coding. Even when True, errors stay clean JSON (no stack trace).
DEBUG = True

# Adds GET /debug/error, a route that crashes on purpose to demo the 500 handler.
ENABLE_ERROR_DEMO_ROUTE = True

# ---------------------------------------------------------------------------
# JWT settings
# ---------------------------------------------------------------------------
# Secret used to sign tokens. Can be overridden with an environment variable.
SECRET_KEY = os.environ.get("SECRET_KEY", "tbs-pfe-api-dev-secret-change-me-2026-web-services")
JWT_ALGORITHM = "HS256"

# >>> DEMO: set this to 30 to watch the access token expire during the video <<<
# (or without editing code, in PowerShell: $env:ACCESS_TOKEN_EXPIRES_SECONDS=30; python app.py)
ACCESS_TOKEN_EXPIRES_SECONDS = int(os.environ.get("ACCESS_TOKEN_EXPIRES_SECONDS", 300))  # 5 min
REFRESH_TOKEN_EXPIRES_SECONDS = 24 * 3600   # 1 day

# Fixed TBS-style majors: code -> full name.
# The code is what appears inside a report_id (e.g. TBS-PFE-2024-BA-017).
MAJORS = {
    "BA": "Business Analytics",
    "FIN": "Finance",
    "MKT": "Marketing",
    "ACC": "Accounting",
    "IT": "Information Technology",
    "IBE": "International Business Economics",
}

REPORT_TYPES = ["Internship report", "Research thesis", "Entrepreneurial project"]

LEVELS = ["freshman", "sophomore", "junior", "senior"]

# Fields a client must send when creating a report.
REPORT_REQUIRED_FIELDS = [
    "report_id", "student_id", "major", "title", "type",
    "key_feature_1", "key_feature_2", "key_feature_3", "date",
]

# Fields a client must send when creating a student.
STUDENT_REQUIRED_FIELDS = ["student_id", "first_name", "last_name", "double_major", "level"]
