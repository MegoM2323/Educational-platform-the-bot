#!/bin/bash
set -e

echo "Starting THE_BOT Backend..."

# Wait for database to be ready
echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
for i in {1..30}; do
    if pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER 2>/dev/null; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "Attempt $i/30: Waiting for PostgreSQL..."
    sleep 2
done

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput || true

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Create cache table if using django-cachetable
python manage.py createcachetable 2>/dev/null || true

echo "Backend initialization complete!"

# Start Daphne ASGI server
exec daphne \
    -b 0.0.0.0 \
    -p 8000 \
    --access-log - \
    --verbosity 1 \
    config.asgi:application
