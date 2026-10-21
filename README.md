# TBS PFE API

A small Flask REST API that gives Tunis Business School students access to previous
PFE (Projet de Fin d'Études) reports and lets them explore topics.

- **No database**: data lives in in-memory Python lists of dictionaries (reset on restart).
- **JWT auth** with access + refresh tokens, refresh **rotation** and **logout** (in-memory blocklist).
- **Privacy**: a student's ID (CIN-inspired) is never returned by a public route.
- **Every response is JSON**, including all errors.

## Project structure

| File | Role |
|---|---|
| `app.py` | Flask app and all routes; `public_report()` privacy serializer |
| `auth.py` | Users (hashed passwords), JWT create/check, blocklist, `@token_required` |
| `validators.py` | Body checks (400), value checks (422), relationship rule (409) |
| `errors.py` | `ApiError` + JSON error handlers (404, 405, 500, ...) |
| `config.py` | Settings: token lifetimes, majors, report types, levels |
| `data.py` | Seed data: 8 students, 9 reports |
| `postman/` | Postman collection + environment |
| `insomnia/` | Insomnia collection (with environment) |

## Setup and run (Windows PowerShell)

```powershell
python -m venv .venv                 # only the first time
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The API runs on `http://127.0.0.1:5000`.

### Short token for the demo (30 seconds)

Either edit `ACCESS_TOKEN_EXPIRES_SECONDS` in `config.py`, or without touching code:

```powershell
$env:ACCESS_TOKEN_EXPIRES_SECONDS=30; python app.py
```

Access tokens default to 5 minutes, refresh tokens to 1 day. Close the terminal (or run
`Remove-Item Env:ACCESS_TOKEN_EXPIRES_SECONDS`) to go back to 5 minutes.

### Demo users

| Username | Password |
|---|---|
| `admin` | `Admin@TBS2026` |
| `tbs_student` | `Pfe@2026` |

Only scrypt hashes (`werkzeug.security`) are stored in `auth.py`.

## Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | – | Body `{"username","password"}` → `access_token` + `refresh_token` |
| POST | `/auth/refresh` | Bearer **refresh** token | New access + refresh token; old refresh token revoked |
| POST | `/auth/logout` | Bearer access token | Revokes the access token (+ `{"refresh_token": "..."}` if sent in body) |
| GET | `/reports` | Public | List reports. Filters: `keyword`, `type`, `major`, `year` |
| GET | `/reports/<report_id>` | Public | One report |
| POST | `/reports` | Bearer access token | Create a report (full validation + relationship rule) |
| PUT | `/reports/<report_id>` | Bearer access token | Full update (all fields except `report_id`; same validation + rule) |
| DELETE | `/reports/<report_id>` | Bearer access token | Delete a report |
| GET | `/students` | Bearer access token | All students with their reports nested |
| GET | `/students/<student_id>` | Bearer access token | One student with their reports |
| POST | `/students` | Bearer access token | Create a student |
| PUT | `/students/<student_id>` | Bearer access token | Full update (all fields except `student_id`) |
| DELETE | `/students/<student_id>` | Bearer access token | Delete a student (only if they have no reports) |

Header format: `Authorization: Bearer <token>`. Each JWT has a `type` claim (`access` /
`refresh`), so one cannot be used in place of the other.

Example: `GET /reports?keyword=power bi&major=BA&year=2023`

## Data model

**Student**: `student_id` (string, exactly 8 digits, unique), `first_name`, `last_name`,
`double_major` (0 or 1), `level` (`freshman` / `sophomore` / `junior` / `senior`).
Level never blocks a report.

**Report**: `report_id` (`TBS-PFE-YYYY-MAJOR-NNN`, e.g. `TBS-PFE-2024-BA-017`, unique),
`student_id` (internal, never public), `major` (`BA`, `FIN`, `MKT`, `ACC`, `IT`, `IBE`),
`title`, `type` (`Internship report` / `Research thesis` / `Entrepreneurial project`),
`key_feature_1..3`, `date` (`YYYY-MM-DD`, real date, not in the future).
The major code and year inside `report_id` must match `major` and `date`.

### Relationship rule

A report belongs to exactly 1 student. A student has 1..2 reports:

- `double_major = 0` → at most **1** report
- `double_major = 1` → at most **2** reports, in **different** majors

Violations return **409 Conflict**. The rule is also enforced on updates and deletes:

- `PUT /reports/<id>` re-checks the rule (the report being edited doesn't count against itself),
  e.g. moving a report to a single-major student who already has one → 409.
- `PUT /students/<id>` refuses `double_major: 0` while the student holds 2 reports → 409.
- `DELETE /students/<id>` refuses a student who still has reports (a report must always
  belong to a student) → 409.
- IDs come from the URL and cannot be changed by PUT → 422.

### Privacy rule

Every report that leaves the API goes through `public_report()`, which **copies only
whitelisted fields**, so `student_id` can never leak, even if new fields are added later.
Error messages on report routes never echo a student ID. Student IDs are visible only on
the token-protected `/students` routes. Request **D01** in the collections proves it.

## Errors

Every error has the same shape:

```json
{"error": "Unprocessable Entity", "message": "'double_major' must be 0 (single major) or 1 (double major), got 3.", "status": 422}
```

| Code | When |
|---|---|
| 400 | Body missing / not JSON / not an object, missing fields, unknown fields |
| 401 | Missing token, malformed header, invalid token, **expired token** ("use /auth/refresh"), revoked token, wrong token type, bad credentials |
| 404 | Unknown report, unknown student, unknown route |
| 405 | Wrong HTTP method (e.g. `DELETE /reports`, `PATCH /students/<id>`) |
| 409 | Duplicate `student_id` / `report_id`, relationship rule (on POST, PUT and DELETE) |
| 422 | Wrong types or values (e.g. `double_major: 3`, `level: "master"`, bad date, bad ID format, unknown major/type, invalid filters); all problems listed at once |
| 500 | Unexpected crash → generic JSON, never a stack trace (demo: `GET /debug/error`, disable with `ENABLE_ERROR_DEMO_ROUTE = False`) |

## Testing with Postman and Insomnia

Both collections use the variables `base_url`, `access_token`, `refresh_token`
(+ `old_refresh_token` for the rotation demo). Tokens are **saved automatically** after
login and refresh.

**Folders** (80 requests):

1. **Demo script** (D01–D14): auth flow (token, expiry, refresh rotation, logout). Video part 1.
2. **CRUD tour** (C00–C18): POST, GET All, GET By Id, PUT, DELETE for both lists. Video part 2.
3. **Error cases** (E00–E44): every 400 / 401 / 404 / 405 / 409 / 422 / 500.

**Restart the server before each folder**: data is in memory and some requests
create or delete data. Folder 1 needs the 30-second token, folders 2 and 3 the normal one.

### Postman

1. **Import** → select both files in `postman/`.
2. Top-right environment dropdown → **TBS PFE Local**.
3. Each request has tests (status code, error format, privacy, token saving).
   Run one by one, or right-click the collection → **Run collection**.
4. D07 waits `wait_seconds` (default 35) before sending, to let a 30-second token expire.
   Set it to `0` if you prefer to wait yourself.

Command line (optional): `npx newman run postman/TBS_PFE_API.postman_collection.json -e postman/TBS_PFE_Local.postman_environment.json`

### Insomnia

1. **Import** → `insomnia/TBS_PFE_API.insomnia.json`.
2. Environment dropdown → **TBS PFE Local**.
3. After-response scripts save the tokens and run the checks (Insomnia 9+). On older
   versions, copy `access_token` / `refresh_token` from the login response into the
   environment by hand.
4. Before D07, wait ~30 seconds yourself.

## Demo script (video)

The full screen-by-screen script with narration is in [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md).

**Part 1: auth flow** (`$env:ACCESS_TOKEN_EXPIRES_SECONDS=30; python app.py`, folder 1)

| # | Request | Expected |
|---|---|---|
| D01 | GET `/reports` | 200, no `student_id` anywhere |
| D02 | GET `/reports?keyword=machine learning&major=BA` | 200, 1 result |
| D03 | GET `/reports/TBS-PFE-2024-BA-017` | 200 |
| D04 | GET `/students` (no token) | 401 |
| D05 | POST `/auth/login` | 200, tokens saved |
| D06 | GET `/students` | 200 |
| D07 | wait 30 s → GET `/students` | 401 "Access token expired, use /auth/refresh." |
| D08 | POST `/auth/refresh` | 200, new pair, old refresh revoked |
| D09 | GET `/students` | 200 |
| D10 | POST `/reports` for Yasmine (single major, has 1) | 409 relationship rule |
| D11 | POST `/reports` with bad data | 422, all problems listed |
| D12 | POST `/auth/refresh` with the OLD refresh token | 401 revoked |
| D13 | POST `/auth/logout` | 200 |
| D14 | GET `/students` with the same token | 401 revoked |

**Part 2: CRUD tour** (restart with `python app.py`, folder 2)

| # | Request | Expected |
|---|---|---|
| C00 | POST `/auth/login` | 200 |
| C01–C02 | GET `/students`, GET `/students/09876543` | 200 (Aziz: 2 reports nested) |
| C03 | POST `/students` (Rania) | 201 |
| C04 | PUT `/students/10203040` | 200 (level → senior, double_major → 1) |
| C05–C06 | DELETE `/students/10203040`, then GET it | 200, then 404 |
| C07–C08 | GET `/reports`, GET `/reports/TBS-PFE-2024-BA-017` | 200 (public) |
| C09 | POST `/reports` (Ranim, 1st report) | 201 |
| C10 | PUT `/reports/TBS-PFE-2025-IT-030` | 200 (title + features updated) |
| C11–C12 | POST `/reports` for Nour in MKT, GET Nour | 201, then 2 reports |
| C13–C14 | DELETE `/reports/TBS-PFE-2025-IT-030`, then GET it | 200, then 404 |
| C15–C18 | filters, `/`, logout | 200 |

**Part 3 (highlights from folder 3)**: E42 / E43 / E44 (relationship rule on PUT and DELETE),
E34 (500 with no stack trace).
