#!/bin/bash

# Exit immediately if a command fails
set -e

# Extract host and port from DATABASE_URL
# This is a simple parser, might need adjustment for complex URLs
DB_HOST=$(echo $DATABASE_URL | sed -e 's/.*@//' -e 's/:.*//' -e 's/\/.*//')
DB_PORT=$(echo $DATABASE_URL | sed -e 's/.*://' -e 's/\/.*//')

# Default to 5432 if port wasn't found
if [ -z "$DB_PORT" ]; then
  DB_PORT=5432
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "PostgreSQL is up and running!"

# Run migrations if database is available
echo "Applying database migrations..."
python manage.py migrate

# Execute the main command (from CMD in Dockerfile)
exec "$@"
