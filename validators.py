"""Validation helpers.

Order of checks used by the routes:
  400  body is not JSON / not an object / missing fields / unknown fields
  422  a field has the wrong type or an invalid value (all problems listed at once)
  409  duplicate id, relationship rule (checked in app.py / check_relationship_rule)
"""
import re
from datetime import date

from flask import request

from config import LEVELS, MAJORS, REPORT_TYPES
from errors import ApiError

STUDENT_ID_RE = re.compile(r"^\d{8}$")
# TBS-PFE-<4-digit year>-<major code>-<3-digit sequence>, e.g. TBS-PFE-2024-BA-017
REPORT_ID_RE = re.compile(r"^TBS-PFE-(\d{4})-([A-Z]{2,3})-(\d{3})$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# 400 helpers: shape of the body
# ---------------------------------------------------------------------------
def get_json_body():
    """Return the request body as a dict, or raise 400 if it is missing/invalid JSON."""
    body = request.get_json(silent=True)
    if body is None:
        raise ApiError(400, "Bad Request",
                       "Request body must be valid JSON with header Content-Type: application/json.")
    if not isinstance(body, dict):
        raise ApiError(400, "Bad Request", "Request body must be a JSON object { ... }.")
    return body


def require_fields(body, fields):
    """Raise 400 listing every required field that is missing or empty."""
    missing = [f for f in fields if f not in body or body[f] in (None, "")]
    if missing:
        raise ApiError(400, "Bad Request", "Missing required field(s): " + ", ".join(missing))


def reject_unknown_fields(body, allowed):
    unknown = [f for f in body if f not in allowed]
    if unknown:
        raise ApiError(400, "Bad Request",
                       "Unknown field(s): " + ", ".join(unknown) + ". Allowed: " + ", ".join(allowed))


def get_put_body(id_field, url_id, all_fields):
    """PUT = full replacement. The id comes from the URL and cannot be changed;
    every other field is required. Returns the body with the URL id filled in."""
    body = get_json_body()
    if id_field in body and body[id_field] != url_id:
        raise ApiError(422, "Unprocessable Entity",
                       f"'{id_field}' cannot be changed. It is taken from the URL; "
                       f"remove it from the body or send the same value.")
    require_fields(body, [f for f in all_fields if f != id_field])
    reject_unknown_fields(body, all_fields)
    return dict(body, **{id_field: url_id})


def _raise_if_errors(errors):
    if errors:
        raise ApiError(422, "Unprocessable Entity", " | ".join(errors))


# ---------------------------------------------------------------------------
# 422 helpers: small reusable checks (each returns an error string or None)
# ---------------------------------------------------------------------------
def _check_text(body, field, min_len, max_len):
    value = body[field]
    if not isinstance(value, str):
        return f"'{field}' must be a string."
    if not (min_len <= len(value.strip()) <= max_len):
        return f"'{field}' must be between {min_len} and {max_len} characters."
    return None


def _check_name(body, field):
    error = _check_text(body, field, 2, 50)
    if error:
        return error
    if not all(ch.isalpha() or ch in " '-" for ch in body[field].strip()):
        return f"'{field}' may only contain letters, spaces, hyphens and apostrophes."
    return None


def check_choice(value, field, allowed):
    """Case-insensitive match against a list. Returns (canonical_value, error)."""
    if not isinstance(value, str):
        return None, f"'{field}' must be a string."
    for option in allowed:
        if value.strip().lower() == option.lower():
            return option, None
    return None, f"'{field}' must be one of: " + ", ".join(allowed) + "."


def parse_date(value):
    """Returns (date_object, error)."""
    if not isinstance(value, str) or not DATE_RE.match(value):
        return None, "'date' must be a string in format YYYY-MM-DD."
    try:
        d = date.fromisoformat(value)
    except ValueError:
        return None, f"'date' {value} is not a real calendar date."
    if d > date.today():
        return None, "'date' cannot be in the future."
    return d, None


# ---------------------------------------------------------------------------
# STUDENT
# ---------------------------------------------------------------------------
def validate_student(body):
    """Return a clean student dict or raise 422 listing every problem."""
    errors = []
    clean = {}

    sid = body["student_id"]
    if not isinstance(sid, str):
        errors.append("'student_id' must be a string (keeps leading zeros, e.g. \"09876543\").")
    elif not STUDENT_ID_RE.match(sid):
        errors.append("'student_id' must be exactly 8 digits.")
    else:
        clean["student_id"] = sid

    for field in ("first_name", "last_name"):
        error = _check_name(body, field)
        if error:
            errors.append(error)
        else:
            clean[field] = " ".join(body[field].split())  # trim + collapse spaces

    dm = body["double_major"]
    # bool is a subclass of int in Python, so True/False must be rejected explicitly.
    if type(dm) is not int:
        errors.append("'double_major' must be an integer: 0 or 1.")
    elif dm not in (0, 1):
        errors.append(f"'double_major' must be 0 (single major) or 1 (double major), got {dm}.")
    else:
        clean["double_major"] = dm

    level, error = check_choice(body["level"], "level", LEVELS)
    if error:
        errors.append(error)
    else:
        clean["level"] = level

    _raise_if_errors(errors)
    return clean


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------
def validate_report(body):
    """Return a clean report dict or raise 422 listing every problem.
    Never echoes the student_id value (privacy rule)."""
    errors = []
    clean = {}

    # student_id: format only here; existence is checked in the route (404).
    sid = body["student_id"]
    if not isinstance(sid, str) or not STUDENT_ID_RE.match(sid):
        errors.append("'student_id' must be a string of exactly 8 digits.")
    else:
        clean["student_id"] = sid

    major, error = check_choice(body["major"], "major", list(MAJORS))
    if error:
        errors.append(error)
    else:
        clean["major"] = major

    rtype, error = check_choice(body["type"], "type", REPORT_TYPES)
    if error:
        errors.append(error)
    else:
        clean["type"] = rtype

    error = _check_text(body, "title", 10, 200)
    if error:
        errors.append(error)
    else:
        clean["title"] = body["title"].strip()

    for field in ("key_feature_1", "key_feature_2", "key_feature_3"):
        error = _check_text(body, field, 2, 60)
        if error:
            errors.append(error)
        else:
            clean[field] = body[field].strip()

    report_date, error = parse_date(body["date"])
    if error:
        errors.append(error)
    else:
        clean["date"] = body["date"]

    # report_id: format, then consistency with major and date.
    rid = body["report_id"]
    match = REPORT_ID_RE.match(rid.strip().upper()) if isinstance(rid, str) else None
    if match is None:
        errors.append("'report_id' must follow the format TBS-PFE-YYYY-MAJOR-NNN, "
                      "e.g. TBS-PFE-2024-BA-017.")
    else:
        id_year, id_major, _ = match.groups()
        if id_major not in MAJORS:
            errors.append(f"'report_id' contains unknown major code '{id_major}'.")
        elif major and id_major != major:
            errors.append(f"Major code in 'report_id' ({id_major}) does not match 'major' ({major}).")
        if report_date and int(id_year) != report_date.year:
            errors.append(f"Year in 'report_id' ({id_year}) does not match the year of 'date' "
                          f"({report_date.year}).")
        clean["report_id"] = match.group(0)

    _raise_if_errors(errors)
    return clean


# ---------------------------------------------------------------------------
# RELATIONSHIP RULE (graded)
# A report belongs to exactly 1 student. A student has 1..2 reports:
#   double_major = 0 -> max 1 report
#   double_major = 1 -> max 2 reports, in DIFFERENT majors
# ---------------------------------------------------------------------------
def check_relationship_rule(student, new_major, all_reports, ignore_report_id=None):
    """ignore_report_id: on PUT, the report being updated does not count against itself."""
    existing = [r for r in all_reports if r["student_id"] == student["student_id"]
                and r["report_id"] != ignore_report_id]

    if student["double_major"] == 0 and len(existing) >= 1:
        raise ApiError(409, "Conflict",
                       "Relationship rule: this student has a single major (double_major = 0) "
                       "and already has 1 report. Maximum is 1 report.")

    if student["double_major"] == 1:
        if len(existing) >= 2:
            raise ApiError(409, "Conflict",
                           "Relationship rule: this student is a double major and already has "
                           "2 reports. Maximum is 2 reports.")
        if any(r["major"] == new_major for r in existing):
            raise ApiError(409, "Conflict",
                           f"Relationship rule: this double-major student already has a report in "
                           f"{new_major} ({MAJORS[new_major]}). The 2 reports must be in different majors.")


def check_double_major_change(student, new_double_major, all_reports):
    """PUT /students: switching to single major is impossible while holding 2 reports."""
    count = sum(1 for r in all_reports if r["student_id"] == student["student_id"])
    if new_double_major == 0 and count > 1:
        raise ApiError(409, "Conflict",
                       f"Relationship rule: this student has {count} reports, so double_major "
                       f"cannot be set to 0 (a single-major student has at most 1 report). "
                       f"Delete a report first.")
