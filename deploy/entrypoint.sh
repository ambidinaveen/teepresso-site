#!/usr/bin/env bash
# ==========================================================================
# Teepresso container entrypoint.
# Waits for the DB, applies migrations, collects static, seeds on first boot,
# then hands off to the CMD (Gunicorn by default).
# ==========================================================================
set -euo pipefail

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"

# 1) Wait for PostgreSQL (only when POSTGRES_HOST is set; SQLite needs no wait)
if [ -n "${POSTGRES_HOST:-}" ]; then
  echo "⏳ Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432} …"
  until python - <<'PY' 2>/dev/null
import os, socket
s = socket.socket(); s.settimeout(2)
s.connect((os.environ["POSTGRES_HOST"], int(os.environ.get("POSTGRES_PORT", "5432"))))
s.close()
PY
  do sleep 1; done
  echo "✓ Database is reachable."
fi

# 2) Schema + static
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 3) Seed demo data only on a fresh DB (no products yet)
if ! python - <<'PY' 2>/dev/null
import django; django.setup()
from products.models import Product
import sys; sys.exit(0 if Product.objects.exists() else 1)
PY
then
  echo "🌱 Empty catalog detected — seeding demo data…"
  python manage.py seed || true
fi

# 4) Run the container's main process (Gunicorn / Celery / etc.)
exec "$@"
