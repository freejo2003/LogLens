#!/bin/sh
set -eu

python manage.py migrate --noinput

if [ "${LOGLENS_BOOTSTRAP_SUPERUSER:-false}" = "true" ]; then
    python manage.py bootstrap_superuser
fi

python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-10000}" \
    --workers 1 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
