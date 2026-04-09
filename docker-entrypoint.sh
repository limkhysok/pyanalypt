#!/bin/bash

set -e

# Extract DB host and port from DATABASE_URL
DB_HOST=$(echo $DATABASE_URL | sed -e 's/.*@//' -e 's/:.*//' -e 's/\/.*//')
DB_PORT=$(echo $DATABASE_URL | sed -e 's/.*:[^:]*@[^:]*://' -e 's/\/.*//')

if [ -z "$DB_PORT" ]; then
  DB_PORT=5432
fi

# Wait for PostgreSQL
echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "PostgreSQL is ready."

# Run migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files (safe to run in both dev and prod)
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

exec "$@"
