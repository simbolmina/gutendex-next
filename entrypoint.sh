#!/bin/sh
# Patched entrypoint for gutendex-next behind a reverse proxy (Coolify/Traefik).
# Replaces the upstream file at the repo root.
#
# Two additions vs upstream:
#   --proxy-headers --forwarded-allow-ips=* : uvicorn then honors the
#       X-Forwarded-Proto / Host headers the proxy sets, so `request.base_url`
#       (used to build the `next`/`previous` page URLs) comes back as the
#       public https URL instead of http://<container>:8000. Without this the
#       StoryCodex app refuses the returned `next` links (off-origin) and
#       pagination silently stops after page 1.
set -e

echo "Initializing database..."
python - <<'PY'
from app.database import engine, Base

# Create all tables
Base.metadata.create_all(bind=engine)
print("Database tables created successfully")
PY

if [ "${RUN_UPDATECATALOG_ON_STARTUP:-false}" = "true" ]; then
  echo "Updating Gutenberg catalog (this can take several minutes)..."
  python catalog/updatecatalog.py
fi

echo "Starting FastAPI server..."
UVICORN_WORKERS="${UVICORN_WORKERS:-2}"
UVICORN_LIMIT_MAX_REQUESTS="${UVICORN_LIMIT_MAX_REQUESTS:-2000}"

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "${UVICORN_WORKERS}" \
  --limit-max-requests "${UVICORN_LIMIT_MAX_REQUESTS}" \
  --proxy-headers \
  --forwarded-allow-ips="*"
