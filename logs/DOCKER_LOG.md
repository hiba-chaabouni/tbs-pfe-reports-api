# Docker log: TBS PFE API

A dated, step-by-step record of moving the API to Docker. New entries go at the bottom.

---

## 2026-10-25: Install check

**Goal:** confirm Docker Desktop (Windows, WSL 2 backend) works before touching the project.

Commands run (PowerShell, transcript in `logs/docker_setup_terminal.txt`):

```powershell
docker --version          # -> Docker version 29.9.2, build a82e528
docker run hello-world    # -> pulled and ran the test image: Docker works
docker compose version    # -> Docker Compose version v5.6.1
```

Result: Docker and Compose are installed and working.

---

## 2026-10-25: Reading the project before writing Docker files

What we checked, and what it means for Docker:

| Finding | Consequence |
|---|---|
| `config.py` already reads `SECRET_KEY` and `ACCESS_TOKEN_EXPIRES_SECONDS` from environment variables | Docker can pass them in with no code change, and `python app.py` keeps its defaults |
| `app.run(debug=DEBUG)` listens on `127.0.0.1` only | Fine for local runs. In a container we need `0.0.0.0`, so the container uses gunicorn with `--bind 0.0.0.0:5000` and `app.py` stays as it is |
| `DEBUG = True` was hard-coded | Changed to `DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"`: still on locally, off in Docker (`FLASK_DEBUG=0`) |
| Data and the logout blocklist are in-memory Python lists | gunicorn **must use 1 worker**. With several workers each process has its own lists, so a token revoked in one worker would still work in another, and a report created in one would be missing in another |
| Collections use `http://127.0.0.1:5000` | Mapping port `5000:5000` means Postman and Insomnia need no change |
| Local Python is 3.14 (from the `__pycache__` file names) | Image based on `python:3.14-slim` to match |

---

## 2026-10-25: Files created

### `Dockerfile`: the recipe for the image
- `python:3.14-slim`: a small official Python image.
- `PYTHONUNBUFFERED=1`: logs show up immediately in `docker compose logs`.
- Copies `requirements.txt` and installs it **before** copying the code, so Docker reuses the
  install step when only the code changes and rebuilds are faster.
- Installs `gunicorn==23.0.0` here only, not in `requirements.txt`, because gunicorn does not run on
  Windows and the local venv doesn't need it.
- Runs as a normal user (`appuser`), not root.
- `EXPOSE 5000`, and starts `gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --access-logfile - app:app`.
  `--access-logfile -` prints one line per request to the container logs.

### `.dockerignore`: what is NOT copied into the image
`.venv`, `__pycache__`, `.git`, `logs`, `postman/`, `.postman/`, `insomnia/`, `.env`, docs.
This keeps the image small and keeps the secret out of it, since the secret is passed at run time instead.

### `docker-compose.yml`: how to run the container
- Port `5000:5000`.
- `SECRET_KEY` comes from `.env`. If it is missing, Compose stops with a clear message (`:?` syntax).
- `ACCESS_TOKEN_EXPIRES_SECONDS` comes from `.env` or the shell, with 300 as the default.
- `FLASK_DEBUG: "0"`: debug off.
- `restart: unless-stopped`: comes back up if Docker Desktop restarts.

### `.env.example` (committed) and `.env` (not committed)
- `.env.example` is the template with placeholder values.
- `.env` was created locally with a random 64-character secret (`secrets.token_hex(32)`).
- `.gitignore` already contained `.env`. Confirmed with `git check-ignore -v .env` -> `.gitignore:4:.env`.

### `README.md`
Added a "Run with Docker" section (up/down, token expiry, logs, reset data) and the new
files to the project structure table.

---

## 2026-10-25: Checks run (before the first build)

```powershell
git check-ignore -v .env           # .env is ignored by git
docker compose config --quiet      # compose file is valid -> OK
docker compose config              # env resolved: ACCESS_TOKEN_EXPIRES_SECONDS "300", FLASK_DEBUG "0", SECRET_KEY set
python -c "import config; print(config.DEBUG)"                  # True  (local run unchanged)
$env:FLASK_DEBUG=0; python -c "import config; print(config.DEBUG)"  # False (Docker setting)
```

Problems met so far:
- **Several gunicorn workers would break the in-memory data.** Fixed by using `--workers 1`
  (plus `--threads 4`) before it could cause trouble.
- **The app would be unreachable from Postman** if it listened on `127.0.0.1` inside the container.
  Fixed by binding gunicorn to `0.0.0.0:5000`.

---

## 2026-10-25: First build, run and Postman test

```powershell
docker compose up --build -d     # image built, container "tbs-pfe-api" started
docker compose logs -f           # gunicorn running, requests visible
docker compose ps                # tbs-pfe-api  Up
```

Ran the whole Postman collection in one go: **277 passed, 3 failed**, all 3 in
**D07 "Wait for expiry, retry -> 401 expired"** (got `200` instead of `401`).

**Cause:** not a Docker bug. The container used the default 300-second access token
(confirmed: login returned `"access_expires_in": 300`). D07 waits 35 seconds, then expects
the token to be expired, which only happens with a 30-second token. The README already says
folder 1 needs the 30-second token and folders 2 and 3 need the normal one.

**Fix:** run folder 1 on its own with `ACCESS_TOKEN_EXPIRES_SECONDS=30`, then go back to
300 and restart before folders 2 and 3:

```powershell
$env:ACCESS_TOKEN_EXPIRES_SECONDS=30; docker compose up -d      # folder 1
Remove-Item Env:ACCESS_TOKEN_EXPIRES_SECONDS; docker compose up -d   # folder 2
docker compose restart                                           # folder 3
```

Problem met: `docker compose logs -f` keeps the terminal busy, so other commands need a
second terminal (VS Code terminal panel -> `+`).

## 2026-10-25: Re-run with the right token per folder

Ran each folder separately, as described above (30-second token for folder 1, then 300
seconds with a fresh container for folders 2 and 3).

**Result: all tests passed, 0 failures.** D07 now gets `401 expired` as expected.

The API runs fully in Docker: no venv needed, debug off, the JWT secret comes from `.env`,
the token lifetime can be changed without rebuilding, and logs are available with `docker compose logs -f`.
`python app.py` still works for local runs.

## 2026-10-25: Shutdown

```powershell
docker compose down     # container tbs-pfe-api and network ourapi2026_default removed
```

Problem met: `Stop-Transcript` failed with "l'hôte n'effectue pas de transcription"
(this host is not transcribing). The transcript (`logs/docker_build_terminal.txt`) was started in
the **first** terminal, the one running `docker compose logs -f`, but `Stop-Transcript` was typed
in the **second** terminal. Each PowerShell terminal has its own transcript.
**Fix:** in the first terminal, press Ctrl+C to stop following the logs, then run `Stop-Transcript` there.
To find the right one among several VS Code terminals, hover over each name in the terminal list until
the tooltip shows the PID from the transcript header (here `2040`).
Done at 17:24:50: the transcript now ends with "Fin de la transcription Windows PowerShell".
