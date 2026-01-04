#!/bin/bash
set -e

echo "Starting THE_BOT Backend..."

# Wait for database to be ready using Python
echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
python << 'PYEOF'
import socket
import time
import os

db_host = os.environ.get('DB_HOST', 'postgres')
db_port = int(os.environ.get('DB_PORT', '5432'))
max_attempts = 30

for i in range(1, max_attempts + 1):
    try:
        sock = socket.create_connection((db_host, db_port), timeout=2)
        sock.close()
        print("PostgreSQL is ready!")
        break
    except (socket.error, socket.timeout):
        print(f"Attempt {i}/{max_attempts}: Waiting for PostgreSQL...")
        time.sleep(2)
PYEOF


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
