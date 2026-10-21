from flask import Flask, g, jsonify, request

from auth import (check_credentials, create_token_pair, decode_token,
                  get_bearer_token, revoke, token_required)
from config import (DEBUG, ENABLE_ERROR_DEMO_ROUTE, MAJORS, REPORT_REQUIRED_FIELDS,
                    REPORT_TYPES, STUDENT_REQUIRED_FIELDS)
from data import reports, students
from errors import ApiError, register_error_handlers
from validators import (check_choice, check_double_major_change, check_relationship_rule,
                        get_json_body, get_put_body, reject_unknown_fields, require_fields,
                        validate_report, validate_student)

app = Flask(__name__)
app.json.sort_keys = False  # keep fields in the order we define them
register_error_handlers(app)


# ---------------------------------------------------------------------------
# Privacy: the ONLY way a report leaves the API on public routes.
# Whitelist approach: we copy the safe fields, so student_id (or any new
# sensitive field added later) can never leak by accident.
# ---------------------------------------------------------------------------
PUBLIC_REPORT_FIELDS = [
    "report_id", "major", "title", "type",
    "key_feature_1", "key_feature_2", "key_feature_3", "date",
]


def public_report(report):
    safe = {field: report[field] for field in PUBLIC_REPORT_FIELDS}
    safe["major_name"] = MAJORS.get(report["major"], report["major"])
    return safe


def find_report(report_id):
    return next((r for r in reports if r["report_id"] == report_id), None)


def find_student(student_id):
    return next((s for s in students if s["student_id"] == student_id), None)


def student_with_reports(student):
    """Protected routes only: the student (incl. student_id) + his/her reports nested."""
    result = dict(student)
    result["reports"] = [public_report(r) for r in reports
                         if r["student_id"] == student["student_id"]]
    return result


@app.route("/")
def home():
    return jsonify({"message": "TBS PFE API is running!", "docs": "See README.md"})


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------
@app.route("/auth/login", methods=["POST"])
def login():
    body = get_json_body()
    require_fields(body, ["username", "password"])
    if not check_credentials(body["username"], body["password"]):
        # Same message for unknown user and wrong password (don't help attackers).
        raise ApiError(401, "Invalid Credentials", "Wrong username or password.")
    return jsonify(create_token_pair(body["username"]))


@app.route("/auth/refresh", methods=["POST"])
def refresh():
    """Send the REFRESH token as 'Authorization: Bearer <refresh_token>'.
    Rotation: the old refresh token is revoked and a brand-new pair is returned."""
    payload = decode_token(get_bearer_token(), "refresh")
    revoke(payload)
    return jsonify(create_token_pair(payload["sub"]))


@app.route("/auth/logout", methods=["POST"])
@token_required
def logout():
    """Revokes the access token in the header, and the refresh token if sent in the
    body as {"refresh_token": "..."}."""
    revoke(g.token)
    revoked = ["access_token"]

    body = request.get_json(silent=True) or {}
    refresh_token = body.get("refresh_token") if isinstance(body, dict) else None
    if refresh_token:
        refresh_payload = decode_token(refresh_token, "refresh")
        if refresh_payload["sub"] != g.current_user:
            raise ApiError(401, "Invalid Token", "This refresh token belongs to another user.")
        revoke(refresh_payload)
        revoked.append("refresh_token")

    return jsonify({"message": f"User '{g.current_user}' logged out.", "revoked": revoked})


# ---------------------------------------------------------------------------
# STUDENTS (all protected: student_id is personal data)
# ---------------------------------------------------------------------------
@app.route("/students", methods=["GET"])
@token_required
def list_students():
    result = [student_with_reports(s) for s in students]
    return jsonify({"count": len(result), "students": result})


@app.route("/students/<student_id>", methods=["GET"])
@token_required
def get_student(student_id):
    student = find_student(student_id)
    if student is None:
        raise ApiError(404, "Not Found", f"No student found with id '{student_id}'.")
    return jsonify(student_with_reports(student))


@app.route("/students", methods=["POST"])
@token_required
def create_student():
    body = get_json_body()                                  # 400 not JSON
    require_fields(body, STUDENT_REQUIRED_FIELDS)           # 400 missing fields
    reject_unknown_fields(body, STUDENT_REQUIRED_FIELDS)    # 400 extra fields
    new_student = validate_student(body)                    # 422 bad types/values

    if find_student(new_student["student_id"]) is not None:  # 409 duplicate
        raise ApiError(409, "Conflict", "A student with this student_id already exists.")

    students.append(new_student)
    return jsonify(student_with_reports(new_student)), 201


@app.route("/students/<student_id>", methods=["PUT"])
@token_required
def update_student(student_id):
    """Full update. student_id comes from the URL and cannot change."""
    student = find_student(student_id)                       # 404 unknown student
    if student is None:
        raise ApiError(404, "Not Found", f"No student found with id '{student_id}'.")
    body = get_put_body("student_id", student_id, STUDENT_REQUIRED_FIELDS)  # 400 / 422 id change
    clean = validate_student(body)                           # 422 bad types/values
    check_double_major_change(student, clean["double_major"], reports)  # 409 relationship rule

    student.update(clean)
    return jsonify(student_with_reports(student))


@app.route("/students/<student_id>", methods=["DELETE"])
@token_required
def delete_student(student_id):
    """A report must always belong to a student, so a student with reports cannot be deleted."""
    student = find_student(student_id)
    if student is None:
        raise ApiError(404, "Not Found", f"No student found with id '{student_id}'.")
    count = sum(1 for r in reports if r["student_id"] == student_id)
    if count:
        raise ApiError(409, "Conflict",
                       f"This student still has {count} report(s). Every report must belong to a "
                       f"student, so delete the report(s) first.")

    students.remove(student)
    return jsonify({"message": f"Student '{student_id}' deleted.", "deleted": student})


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------
@app.route("/reports", methods=["GET"])
def list_reports():
    """Public. Optional filters: ?keyword= &type= &major= &year= (no student_id filter)."""
    keyword = request.args.get("keyword", "").strip().lower()
    rtype = request.args.get("type", "").strip()
    major = request.args.get("major", "").strip()
    year = request.args.get("year", "").strip()

    # Unknown filter values -> 422 (instead of silently returning an empty list).
    errors = []
    if rtype:
        rtype, error = check_choice(rtype, "type", REPORT_TYPES)
        errors.append(error)
    if major:
        major, error = check_choice(major, "major", list(MAJORS))
        errors.append(error)
    if year and not (year.isdigit() and len(year) == 4):
        errors.append("'year' must be a 4-digit year, e.g. 2024.")
    errors = [e for e in errors if e]
    if errors:
        raise ApiError(422, "Unprocessable Entity", "Invalid filter: " + " | ".join(errors))

    result = []
    for r in reports:
        if keyword:
            searchable = " ".join([r["title"], r["key_feature_1"],
                                   r["key_feature_2"], r["key_feature_3"]]).lower()
            if keyword not in searchable:
                continue
        if rtype and r["type"] != rtype:
            continue
        if major and r["major"] != major:
            continue
        if year and not r["date"].startswith(year):
            continue
        result.append(public_report(r))

    result.sort(key=lambda r: r["date"], reverse=True)  # newest first
    return jsonify({"count": len(result), "reports": result})


@app.route("/reports/<report_id>", methods=["GET"])
def get_report(report_id):
    """Public. One report, without student data."""
    report = find_report(report_id.upper())
    if report is None:
        raise ApiError(404, "Not Found", f"No report found with id '{report_id}'.")
    return jsonify(public_report(report))


@app.route("/reports", methods=["POST"])
@token_required
def create_report():
    """Protected. Full validation + relationship rule. Error messages never echo student_id."""
    body = get_json_body()                                  # 400 not JSON
    require_fields(body, REPORT_REQUIRED_FIELDS)            # 400 missing fields
    reject_unknown_fields(body, REPORT_REQUIRED_FIELDS)     # 400 extra fields
    new_report = validate_report(body)                      # 422 bad types/values

    if find_report(new_report["report_id"]) is not None:    # 409 duplicate
        raise ApiError(409, "Conflict", f"A report with id '{new_report['report_id']}' already exists.")

    student = find_student(new_report["student_id"])        # 404 unknown student
    if student is None:
        raise ApiError(404, "Not Found", "The referenced student does not exist.")

    check_relationship_rule(student, new_report["major"], reports)  # 409 relationship rule

    # Same field order as the seed data.
    new_report = {field: new_report[field] for field in REPORT_REQUIRED_FIELDS}
    reports.append(new_report)
    return jsonify(public_report(new_report)), 201


@app.route("/reports/<report_id>", methods=["PUT"])
@token_required
def update_report(report_id):
    """Full update. report_id comes from the URL and cannot change, so the new major/date
    must still match the major code and year inside it."""
    report = find_report(report_id.upper())                 # 404 unknown report
    if report is None:
        raise ApiError(404, "Not Found", f"No report found with id '{report_id}'.")
    body = get_put_body("report_id", report["report_id"], REPORT_REQUIRED_FIELDS)
    clean = validate_report(body)                           # 422 bad types/values

    student = find_student(clean["student_id"])             # 404 unknown student
    if student is None:
        raise ApiError(404, "Not Found", "The referenced student does not exist.")

    # The report being edited does not count against the rule (it is replaced, not added).
    check_relationship_rule(student, clean["major"], reports,
                            ignore_report_id=report["report_id"])  # 409 relationship rule

    report.update({field: clean[field] for field in REPORT_REQUIRED_FIELDS})
    return jsonify(public_report(report))


@app.route("/reports/<report_id>", methods=["DELETE"])
@token_required
def delete_report(report_id):
    report = find_report(report_id.upper())
    if report is None:
        raise ApiError(404, "Not Found", f"No report found with id '{report_id}'.")

    reports.remove(report)
    return jsonify({"message": f"Report '{report['report_id']}' deleted.",
                    "deleted": public_report(report)})


# ---------------------------------------------------------------------------
# DEMO ONLY: proves the 500 handler returns clean JSON without a stack trace.
# Switch off with ENABLE_ERROR_DEMO_ROUTE = False in config.py.
# ---------------------------------------------------------------------------
if ENABLE_ERROR_DEMO_ROUTE:
    @app.route("/debug/error", methods=["GET"])
    def demo_server_error():
        return 1 / 0  # deliberate crash


if __name__ == "__main__":
    app.run(debug=DEBUG)
