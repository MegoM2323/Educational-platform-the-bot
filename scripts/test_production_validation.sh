#!/bin/bash
# Test script for production validation
# Tests various invalid production configurations

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Testing Production Configuration Validation ==="
echo ""

# Backup original .env
if [ -f .env ]; then
    cp .env .env.backup
    echo "✓ Backed up .env to .env.backup"
fi

# Test function
test_config() {
    local test_name="$1"
    local env_content="$2"
    local should_fail="$3"

    echo ""
    echo "Test: $test_name"
    echo "---"

    # Create test .env
    echo "$env_content" > .env

    # Run check script
    if python scripts/check_production_config.py > /dev/null 2>&1; then
        if [ "$should_fail" = "true" ]; then
            echo "❌ FAILED - Should have caught configuration error"
            return 1
        else
            echo "✓ PASSED - Configuration valid"
            return 0
        fi
    else
        if [ "$should_fail" = "true" ]; then
            echo "✓ PASSED - Correctly caught configuration error"
            return 0
        else
            echo "❌ FAILED - Valid configuration rejected"
            return 1
        fi
    fi
}

# Test 1: DEBUG=True in production mode
test_config "DEBUG=True in production" \
"ENVIRONMENT=production
DEBUG=True
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DATABASE_URL=postgresql://user:pass@db.example.com:5432/prod
FRONTEND_URL=https://the-bot.ru
VITE_DJANGO_API_URL=https://the-bot.ru/api
VITE_WEBSOCKET_URL=wss://the-bot.ru/ws" \
"true"

# Test 2: Weak SECRET_KEY
test_config "Weak SECRET_KEY" \
"ENVIRONMENT=production
DEBUG=False
SECRET_KEY=short-key
DATABASE_URL=postgresql://user:pass@db.example.com:5432/prod
FRONTEND_URL=https://the-bot.ru
VITE_DJANGO_API_URL=https://the-bot.ru/api
VITE_WEBSOCKET_URL=wss://the-bot.ru/ws" \
"true"

# Test 3: SQLite database in production
test_config "SQLite in production" \
"ENVIRONMENT=production
DEBUG=False
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DATABASE_URL=sqlite:///db.sqlite3
FRONTEND_URL=https://the-bot.ru
VITE_DJANGO_API_URL=https://the-bot.ru/api
VITE_WEBSOCKET_URL=wss://the-bot.ru/ws" \
"true"

# Test 4: localhost FRONTEND_URL in production
test_config "localhost FRONTEND_URL" \
"ENVIRONMENT=production
DEBUG=False
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DATABASE_URL=postgresql://user:pass@db.example.com:5432/prod
FRONTEND_URL=http://localhost:8080
VITE_DJANGO_API_URL=https://the-bot.ru/api
VITE_WEBSOCKET_URL=wss://the-bot.ru/ws" \
"true"

# Test 5: localhost in VITE_DJANGO_API_URL
test_config "localhost in VITE_DJANGO_API_URL" \
"ENVIRONMENT=production
DEBUG=False
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DATABASE_URL=postgresql://user:pass@db.example.com:5432/prod
FRONTEND_URL=https://the-bot.ru
VITE_DJANGO_API_URL=http://localhost:8000/api
VITE_WEBSOCKET_URL=wss://the-bot.ru/ws" \
"true"

# Test 6: Valid production configuration (should pass)
test_config "Valid production config" \
"ENVIRONMENT=production
DEBUG=False
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DATABASE_URL=postgresql://user:pass@db.example.com:5432/prod
FRONTEND_URL=https://the-bot.ru
VITE_DJANGO_API_URL=https://the-bot.ru/api
VITE_WEBSOCKET_URL=wss://the-bot.ru/ws
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=live_ABCDEFGHIJKLMNOPabcdefghijklmnop" \
"false"

# Restore original .env
echo ""
if [ -f .env.backup ]; then
    mv .env.backup .env
    echo "✓ Restored original .env"
else
    rm -f .env
    echo "✓ Cleaned up test .env"
fi

echo ""
echo "=== All Tests Passed ==="
echo ""
echo "Production validation is working correctly!"
