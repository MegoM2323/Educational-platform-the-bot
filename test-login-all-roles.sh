#!/bin/bash

# Test login for all user roles
API_URL="http://127.0.0.1:8000"
SERVER="mg@5.129.249.206"

echo "╔════════════════════════════════════════════════════╗"
echo "║  TESTING LOGIN FOR ALL ROLES                      ║"
echo "║  API: $API_URL                      ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Test data - standard test users created during setup
declare -A TEST_USERS=(
  ["admin"]="admin:admin123"
  ["student"]="student1:student123"
  ["teacher"]="teacher1:teacher123"
  ["tutor"]="tutor1:tutor123"
  ["parent"]="parent1:parent123"
)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

# Function to test login
test_login() {
  local role=$1
  local username=$2
  local password=$3

  echo -n "Testing $role ($username): "

  # Try login
  response=$(ssh "$SERVER" "curl -s -X POST '$API_URL/api/auth/login/' \
    -H 'Content-Type: application/json' \
    -d '{\"username\":\"$username\",\"password\":\"$password\"}' 2>/dev/null")

  if echo "$response" | grep -q '"access"' || echo "$response" | grep -q '"token"'; then
    echo -e "${GREEN}✓ OK${NC}"
    ((passed++))

    # Extract token for profile check
    if echo "$response" | grep -q '"access"'; then
      token=$(echo "$response" | grep -o '"access":"[^"]*' | cut -d'"' -f4)

      # Test profile endpoint
      echo -n "  └─ Profile: "
      profile=$(ssh "$SERVER" "curl -s -H 'Authorization: Bearer $token' '$API_URL/api/auth/profile/' 2>/dev/null")
      if echo "$profile" | grep -q '"id"'; then
        echo -e "${GREEN}✓ Accessible${NC}"
      else
        echo -e "${YELLOW}⚠ Limited access${NC}"
      fi
    fi
  elif echo "$response" | grep -q '"detail"' || echo "$response" | grep -q '"error"'; then
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Response: $response" | head -c 100
    echo ""
    ((failed++))
  else
    echo -e "${YELLOW}⚠ UNKNOWN${NC}"
    echo "  Response: $response" | head -c 100
    echo ""
  fi
}

# Check if API is reachable
echo "Checking API connectivity..."
if ssh "$SERVER" "curl -s '$API_URL/api/system/health/live/' > /dev/null 2>&1"; then
  echo -e "${GREEN}✓ API is reachable${NC}"
  echo ""
else
  echo -e "${RED}✗ API not reachable${NC}"
  echo "Make sure backend is running: ssh $SERVER 'pgrep -f daphne'"
  exit 1
fi

# Test each role
for role in "${!TEST_USERS[@]}"; do
  creds="${TEST_USERS[$role]}"
  username="${creds%:*}"
  password="${creds#*:}"
  test_login "$role" "$username" "$password"
done

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║  RESULTS                                          ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "Passed: ${GREEN}$passed${NC}"
echo -e "Failed: ${RED}$failed${NC}"
echo ""

if [ $failed -eq 0 ]; then
  echo -e "${GREEN}✓ All logins working!${NC}"
  echo ""
  echo "You can now access THE_BOT with:"
  echo "  https://the-bot.ru (after adding to /etc/hosts)"
  echo ""
  echo "Test accounts:"
  for role in "${!TEST_USERS[@]}"; do
    creds="${TEST_USERS[$role]}"
    username="${creds%:*}"
    password="${creds#*:}"
    echo "  $role: $username / $password"
  done
  exit 0
else
  echo -e "${RED}✗ Some logins failed${NC}"
  exit 1
fi
