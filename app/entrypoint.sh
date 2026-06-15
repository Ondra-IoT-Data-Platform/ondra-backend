#!/bin/sh
set -e

echo "Running migrations..."
/app/.venv/bin/python manage.py migrate --noinput

echo "Collecting static files..."
/app/.venv/bin/python manage.py collectstatic --noinput

echo "Starting server..."
exec /app/.venv/bin/python -m uvicorn config.asgi:application \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 2
