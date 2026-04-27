#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Wait for database
if [ "$DB_HOST" = "db" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
fi

# Apply database migrations
echo "Generating database migrations..."
python manage.py makemigrations user_auth dashboard frontend

echo "Applying database migrations..."
python manage.py migrate --noinput

# Create default superuser
echo "Creating default superuser..."
python manage.py init_admin

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create cache table if needed (optional)
# python manage.py createcachetable

# Start server
if [ "$APP_ENV" = "production" ]; then
    echo "Starting Daphne in production mode..."
    exec daphne -b 0.0.0.0 -p 8000 core.asgi:application
else
    echo "Starting Daphne in development mode..."
    # We use daphne even in dev as requested, but we could also use manage.py runserver
    # For dev, we might want auto-reload. Daphne doesn't have it built-in like runserver.
    # But django-admin runserver uses daphne if installed and ASGI_APPLICATION is set.
    exec python manage.py runserver 0.0.0.0:8000
fi
