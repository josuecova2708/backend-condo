#!/bin/bash

echo "=== RAILWAY DEPLOYMENT DEBUG ==="
echo "PORT variable: $PORT"
echo "All environment variables:"
env | grep PORT
echo "================================"

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start gunicorn with Railway's PORT or default to 8000
ACTUAL_PORT=${PORT:-8000}
echo "Starting gunicorn on port: $ACTUAL_PORT"

exec gunicorn smart_condo_project.wsgi:application \
    --config gunicorn.conf.py