#!/bin/bash
################################################################################
# THE_BOT Platform - API Testing Commands
# Команды для тестирования всех endpoints платформы
# Использование: source TESTING_COMMANDS.sh
################################################################################

set -e

# Configuration
API_URL="http://localhost:8000/api"
BACKEND_DIR="/home/mego/Python\ Projects/THE_BOT_platform/backend"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# 1. LOGIN AND GET TOKENS
################################################################################

echo -e "${BLUE}=== 1. AUTH - Login for all roles ===${NC}"

echo -e "${YELLOW}[*] Logging in as student...${NC}"
STUDENT_RESPONSE=$(curl -s -X POST "$API_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student1@test.com",
    "password": "student123"
  }')
echo "$STUDENT_RESPONSE" | jq '.'
STUDENT_TOKEN=$(echo "$STUDENT_RESPONSE" | jq -r '.data.token // .access // empty')
echo "Token: ${STUDENT_TOKEN:0:20}..."

echo -e "${YELLOW}[*] Logging in as teacher...${NC}"
TEACHER_RESPONSE=$(curl -s -X POST "$API_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher1@test.com",
    "password": "teacher123"
  }')
TEACHER_TOKEN=$(echo "$TEACHER_RESPONSE" | jq -r '.data.token // .access // empty')
echo "Token: ${TEACHER_TOKEN:0:20}..."

echo -e "${YELLOW}[*] Logging in as admin...${NC}"
ADMIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "admin123"
  }')
ADMIN_TOKEN=$(echo "$ADMIN_RESPONSE" | jq -r '.data.token // .access // empty')
echo "Token: ${ADMIN_TOKEN:0:20}..."

echo -e "${YELLOW}[*] Logging in as tutor...${NC}"
TUTOR_RESPONSE=$(curl -s -X POST "$API_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "tutor1@test.com",
    "password": "tutor123"
  }')
TUTOR_TOKEN=$(echo "$TUTOR_RESPONSE" | jq -r '.data.token // .access // empty')
echo "Token: ${TUTOR_TOKEN:0:20}..."

echo -e "${YELLOW}[*] Logging in as parent...${NC}"
PARENT_RESPONSE=$(curl -s -X POST "$API_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "parent1@test.com",
    "password": "parent123"
  }')
PARENT_TOKEN=$(echo "$PARENT_RESPONSE" | jq -r '.data.token // .access // empty')
echo "Token: ${PARENT_TOKEN:0:20}..."

################################################################################
# 2. TEST AUTHENTICATION ENDPOINTS
################################################################################

echo -e "\n${BLUE}=== 2. AUTH ENDPOINTS ===${NC}"

echo -e "${YELLOW}[*] GET /api/auth/me/ (current user)${NC}"
curl -s -X GET "$API_URL/auth/me/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data.email'

echo -e "${YELLOW}[*] POST /api/auth/change-password/${NC}"
# Don't actually change password, just test the endpoint
curl -s -X POST "$API_URL/auth/change-password/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "student123",
    "new_password": "student123"
  }' | jq '.success'

echo -e "${YELLOW}[*] POST /api/auth/refresh/${NC}"
curl -s -X POST "$API_URL/auth/refresh/" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\":\"$STUDENT_TOKEN\"}" | jq '.' || echo "Token format issue"

################################################################################
# 3. TEST PROFILE ENDPOINTS
################################################################################

echo -e "\n${BLUE}=== 3. PROFILE ENDPOINTS ===${NC}"

echo -e "${YELLOW}[*] GET /api/profile/ (current user profile)${NC}"
curl -s -X GET "$API_URL/profile/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data.email'

echo -e "${YELLOW}[*] PATCH /api/profile/ (update profile)${NC}"
curl -s -X PATCH "$API_URL/profile/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Updated Name"}' | jq '.data.full_name'

echo -e "${YELLOW}[*] GET /api/profile/teachers/ (list all teachers)${NC}"
curl -s -X GET "$API_URL/profile/teachers/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data[0].email'

echo -e "${YELLOW}[*] GET /api/profile/teachers/1/ (specific teacher)${NC}"
curl -s -X GET "$API_URL/profile/teachers/1/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data.email'

################################################################################
# 4. TEST SCHEDULING ENDPOINTS
################################################################################

echo -e "\n${BLUE}=== 4. SCHEDULING ENDPOINTS ===${NC}"

echo -e "${YELLOW}[*] GET /api/scheduling/lessons/ (list lessons)${NC}"
curl -s -X GET "$API_URL/scheduling/lessons/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data | length'

echo -e "${YELLOW}[*] GET /api/scheduling/lessons/ (as teacher)${NC}"
curl -s -X GET "$API_URL/scheduling/lessons/" \
  -H "Authorization: Bearer $TEACHER_TOKEN" | jq '.data | length'

echo -e "${YELLOW}[*] POST /api/scheduling/lessons/ (create lesson)${NC}"
LESSON_RESPONSE=$(curl -s -X POST "$API_URL/scheduling/lessons/" \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": 1,
    "start_time": "2026-01-06T10:00:00Z",
    "end_time": "2026-01-06T11:00:00Z"
  }')
echo "$LESSON_RESPONSE" | jq '.data.id // .error // .message'
LESSON_ID=$(echo "$LESSON_RESPONSE" | jq -r '.data.id // empty')

if [ -n "$LESSON_ID" ]; then
  echo -e "${YELLOW}[*] GET /api/scheduling/lessons/$LESSON_ID/ (get lesson)${NC}"
  curl -s -X GET "$API_URL/scheduling/lessons/$LESSON_ID/" \
    -H "Authorization: Bearer $TEACHER_TOKEN" | jq '.data.id'

  echo -e "${YELLOW}[*] PATCH /api/scheduling/lessons/$LESSON_ID/ (update lesson)${NC}"
  curl -s -X PATCH "$API_URL/scheduling/lessons/$LESSON_ID/" \
    -H "Authorization: Bearer $TEACHER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "end_time": "2026-01-06T12:00:00Z"
    }' | jq '.data.id'

  echo -e "${YELLOW}[*] DELETE /api/scheduling/lessons/$LESSON_ID/ (delete lesson)${NC}"
  curl -s -X DELETE "$API_URL/scheduling/lessons/$LESSON_ID/" \
    -H "Authorization: Bearer $TEACHER_TOKEN" | jq '.success'
fi

################################################################################
# 5. TEST MATERIALS ENDPOINTS
################################################################################

echo -e "\n${BLUE}=== 5. MATERIALS ENDPOINTS ===${NC}"

echo -e "${YELLOW}[*] GET /api/materials/ (list materials)${NC}"
curl -s -X GET "$API_URL/materials/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data | length'

echo -e "${YELLOW}[*] GET /api/materials/?subject=1 (filter by subject)${NC}"
curl -s -X GET "$API_URL/materials/?subject=1" \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data | length'

echo -e "${YELLOW}[*] POST /api/materials/ (create material - as teacher)${NC}"
MATERIAL_RESPONSE=$(curl -s -X POST "$API_URL/materials/" \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Material",
    "description": "Test description",
    "subject": 1,
    "content_type": "pdf"
  }')
echo "$MATERIAL_RESPONSE" | jq '.data.id // .error // .message'
MATERIAL_ID=$(echo "$MATERIAL_RESPONSE" | jq -r '.data.id // empty')

if [ -n "$MATERIAL_ID" ]; then
  echo -e "${YELLOW}[*] GET /api/materials/$MATERIAL_ID/ (get material)${NC}"
  curl -s -X GET "$API_URL/materials/$MATERIAL_ID/" \
    -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data.title'
fi

################################################################################
# 6. TEST PERMISSION ISSUES
################################################################################

echo -e "\n${BLUE}=== 6. SECURITY - PERMISSION TESTS ===${NC}"

echo -e "${YELLOW}[!] TEST: Student tries to access admin endpoints (should be 403)${NC}"
ADMIN_TEST=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/admin/users/" \
  -H "Authorization: Bearer $STUDENT_TOKEN")
HTTP_CODE=$(echo "$ADMIN_TEST" | tail -n1)
if [ "$HTTP_CODE" = "403" ]; then
  echo -e "${GREEN}✓ PASS: Got 403 Forbidden${NC}"
else
  echo -e "${RED}✗ FAIL: Got $HTTP_CODE (expected 403)${NC}"
fi

echo -e "${YELLOW}[!] TEST: No token access (should be 401)${NC}"
NO_TOKEN=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/profile/")
HTTP_CODE=$(echo "$NO_TOKEN" | tail -n1)
if [ "$HTTP_CODE" = "401" ]; then
  echo -e "${GREEN}✓ PASS: Got 401 Unauthorized${NC}"
else
  echo -e "${RED}✗ FAIL: Got $HTTP_CODE (expected 401)${NC}"
fi

################################################################################
# 7. TEST RATE LIMITING
################################################################################

echo -e "\n${BLUE}=== 7. RATE LIMITING ===${NC}"

echo -e "${YELLOW}[*] Attempting 6 logins in succession (limit is 5/minute)...${NC}"
for i in {1..6}; do
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/auth/login/" \
    -H "Content-Type: application/json" \
    -d '{
      "email": "student1@test.com",
      "password": "wrong_password"
    }')
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

  if [ "$HTTP_CODE" = "429" ]; then
    echo "Attempt $i: ✓ Rate limited (429)"
    break
  else
    echo "Attempt $i: HTTP $HTTP_CODE"
  fi
done

################################################################################
# 8. TEST CHAT ENDPOINTS
################################################################################

echo -e "\n${BLUE}=== 8. CHAT ENDPOINTS ===${NC}"

echo -e "${YELLOW}[*] GET /api/chat/conversations/ (list conversations)${NC}"
curl -s -X GET "$API_URL/chat/conversations/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data | length'

echo -e "${YELLOW}[*] POST /api/chat/messages/ (send message)${NC}"
MESSAGE_RESPONSE=$(curl -s -X POST "$API_URL/chat/messages/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "room": 1,
    "text": "Test message"
  }')
echo "$MESSAGE_RESPONSE" | jq '.data.id // .error // .message'

################################################################################
# 9. TEST ASSIGNMENTS ENDPOINTS
################################################################################

echo -e "\n${BLUE}=== 9. ASSIGNMENTS ENDPOINTS ===${NC}"

echo -e "${YELLOW}[*] GET /api/assignments/ (list assignments)${NC}"
curl -s -X GET "$API_URL/assignments/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq '.data | length'

echo -e "${YELLOW}[*] POST /api/assignments/1/submit/ (submit solution)${NC}"
SUBMIT_RESPONSE=$(curl -s -X POST "$API_URL/assignments/1/submit/" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "My solution text"
  }')
echo "$SUBMIT_RESPONSE" | jq '.data.id // .error // .message'

################################################################################
# 10. TEST API DOCUMENTATION
################################################################################

echo -e "\n${BLUE}=== 10. API DOCUMENTATION ===${NC}"

echo -e "${YELLOW}[*] GET /api/schema/ (OpenAPI schema)${NC}"
curl -s -X GET "$API_URL/schema/" | jq '.openapi'

echo -e "${YELLOW}[*] GET /api/schema/swagger/ (Swagger UI)${NC}"
curl -s -I "$API_URL/schema/swagger/" | head -3

################################################################################
# 11. PRINT SUMMARY
################################################################################

echo -e "\n${BLUE}=== SUMMARY ===${NC}"
echo -e "${GREEN}Tokens obtained:${NC}"
echo "  STUDENT:  ${STUDENT_TOKEN:0:30}..."
echo "  TEACHER:  ${TEACHER_TOKEN:0:30}..."
echo "  ADMIN:    ${ADMIN_TOKEN:0:30}..."
echo "  TUTOR:    ${TUTOR_TOKEN:0:30}..."
echo "  PARENT:   ${PARENT_TOKEN:0:30}..."

echo -e "\n${GREEN}To test WebSocket:${NC}"
echo "  wscat -c ws://localhost:8000/ws/chat/1/"

echo -e "\n${GREEN}To run Django management commands:${NC}"
echo "  cd $BACKEND_DIR"
echo "  python manage.py init_test_users"
echo "  python manage.py migrate"
echo "  python manage.py test"

echo -e "\n${GREEN}Testing complete!${NC}"
