# Image for the TBS PFE API. Build and run with: docker compose up --build
FROM python:3.14-slim

# Print logs straight away (no buffering) and don't write .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_DEBUG=0

WORKDIR /app

# Dependencies first, so Docker reuses this layer when only the code changes.
# gunicorn is only needed inside the container (it does not run on Windows).
COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn==23.0.0

COPY . .

# Run as a normal user, not root.
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# 0.0.0.0 = reachable from outside the container (Postman on Windows).
# ONE worker on purpose: data and the token blocklist live in memory, so several
# workers would each have their own copy. Threads still handle parallel requests.
# "--access-logfile -" prints every request to the logs (docker compose logs -f).
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", \
     "--access-logfile", "-", "app:app"]
