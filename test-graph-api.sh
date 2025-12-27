#!/bin/bash

# T120: Test Knowledge Graph API manually
# Usage: ./test-graph-api.sh TOKEN STUDENT_ID SUBJECT_ID

TOKEN=${1:-""}
STUDENT_ID=${2:-1}
SUBJECT_ID=${3:-1}

if [ -z "$TOKEN" ]; then
  echo "❌ Usage: ./test-graph-api.sh TOKEN [STUDENT_ID] [SUBJECT_ID]"
  echo ""
  echo "To get TOKEN:"
  echo "1. Open browser DevTools"
  echo "2. Go to Application > Local Storage"
  echo "3. Find 'auth_token' key"
  echo "4. Copy value"
  exit 1
fi

BASE_URL="http://localhost:8003/api"

echo "🔍 Testing Knowledge Graph API"
echo "================================"
echo ""

# Test 1: Get teacher students
echo "1️⃣  Testing GET /materials/teacher/students/"
echo "   Expected: List of students"
curl -s -X GET "$BASE_URL/materials/teacher/students/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq .
echo ""

# Test 2: Get or create graph
echo "2️⃣  Testing GET /knowledge-graph/students/$STUDENT_ID/subject/$SUBJECT_ID/"
echo "   Expected: { success: true, data: {...}, created: true/false }"
GRAPH_RESPONSE=$(curl -s -X GET "$BASE_URL/knowledge-graph/students/$STUDENT_ID/subject/$SUBJECT_ID/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")
echo "$GRAPH_RESPONSE" | jq .
GRAPH_ID=$(echo "$GRAPH_RESPONSE" | jq -r '.data.id // empty')
echo ""

if [ -z "$GRAPH_ID" ]; then
  echo "❌ Failed to get graph ID. Check if student/subject exists."
  exit 1
fi

echo "✅ Graph ID: $GRAPH_ID"
echo ""

# Test 3: Get lessons (lesson bank)
echo "3️⃣  Testing GET /knowledge-graph/lessons/?subject=$SUBJECT_ID&created_by=me"
echo "   Expected: { success: true, data: [...] }"
curl -s -X GET "$BASE_URL/knowledge-graph/lessons/?subject=$SUBJECT_ID&created_by=me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq .
echo ""

# Test 4: Get graph lessons
echo "4️⃣  Testing GET /knowledge-graph/$GRAPH_ID/lessons/"
echo "   Expected: { success: true, data: [...] }"
curl -s -X GET "$BASE_URL/knowledge-graph/$GRAPH_ID/lessons/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq .
echo ""

echo "✅ API tests complete!"
echo ""
echo "If all endpoints returned data correctly, the issue is in frontend."
echo "Check browser Console logs for transformation errors."
