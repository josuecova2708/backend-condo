#!/bin/bash

# Run migrations before starting the server
echo "=== Running database migrations ==="
python manage.py migrate --noinput

# Collect static files
echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

# Start gunicorn — Coolify uses a fixed port (default 8000)
ACTUAL_PORT=${PORT:-8000}
echo "=== Starting gunicorn on port: $ACTUAL_PORT ==="

exec gunicorn smart_condo_project.wsgi:application \
    --config gunicorn.conf.py