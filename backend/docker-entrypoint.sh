#!/usr/bin/env sh
set -e

# Apply migrations, then start the API. Compose orders this after postgres is
# healthy (depends_on: condition: service_healthy).
alembic upgrade head
exec uvicorn vcm.main:app --host 0.0.0.0 --port 8000
