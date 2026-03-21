#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate

echo "Loading initial data (skips if already loaded)..."
python manage.py loaddata initial_data.json --ignorenonexistent 2>/dev/null || echo "Data already loaded, skipping."

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting gunicorn..."
exec gunicorn leave_system.wsgi --log-file -
