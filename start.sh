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

# Ensure PORT is set - Railway must provide this
if [ -z "$PORT" ]; then
    echo "ERROR: PORT variable not set by Railway!"
    echo "Setting default PORT=8080"
    export PORT=8080
fi

ACTUAL_PORT=${PORT:-8080}
echo "Starting gunicorn on port: $ACTUAL_PORT"

exec gunicorn smart_condo_project.wsgi:application \
    --config gunicorn.conf.py