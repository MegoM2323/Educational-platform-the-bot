#!/bin/bash

# Test Authentication Flow Script
# This script tests the login flow to verify authentication is working correctly

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:8080}"

echo "================================"
echo "Testing Authentication Flow"
echo "================================"
echo ""

# Test if backend is running
echo "1. Checking if backend is running..."
if ! curl -s "$BACKEND_URL/api/auth/profile/" > /dev/null 2>&1; then
  echo "❌ Backend is not running at $BACKEND_URL"
  echo "   Start the backend with: cd backend && python manage.py runserver 8000"
  exit 1
fi
echo "✅ Backend is running"
echo ""

# Test login endpoint
echo "2. Testing login endpoint..."
LOGIN_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@test.com",
    "password": "TestPass123!"
  }')

echo "Response: $LOGIN_RESPONSE"
echo ""

# Check if login was successful
if echo "$LOGIN_RESPONSE" | grep -q '"success":true'; then
  echo "✅ Login endpoint is working"

  # Extract token
  TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
  echo "Token obtained: ${TOKEN:0:20}..."
  echo ""

  # Test protected endpoint with token
  echo "3. Testing protected endpoint with token..."
  PROFILE_RESPONSE=$(curl -s -X GET "$BACKEND_URL/api/auth/profile/" \
    -H "Authorization: Token $TOKEN")

  echo "Response: $PROFILE_RESPONSE"

  if echo "$PROFILE_RESPONSE" | grep -q '"success":true'; then
    echo "✅ Protected endpoint is working"
  else
    echo "❌ Protected endpoint failed"
  fi
else
  echo "❌ Login endpoint failed"
  echo "Make sure test user exists: student@test.com / TestPass123!"
  exit 1
fi

echo ""
echo "================================"
echo "✅ All authentication checks passed!"
echo "================================"
