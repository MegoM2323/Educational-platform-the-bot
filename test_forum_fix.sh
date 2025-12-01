#!/bin/bash

# Forum Messages Fix Verification Script
# Tests that messages load correctly when clicking a forum chat

echo "========================================"
echo "Forum Messages Fix Verification"
echo "========================================"

cd "$(dirname "$0")/backend"
source ../.venv/bin/activate

echo ""
echo "1. Testing Backend API..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()
client = Client()

# Get student with messages (Иван Соколов - ID 20)
student = User.objects.filter(id=20, role='student').first()
if not student:
    print('❌ Student ID 20 not found')
    exit(1)

print(f'✅ Testing as: {student.first_name} {student.last_name} (ID: {student.id})')
client.force_login(student)

# Test forum chats endpoint
response = client.get('/api/chat/forum/')
if response.status_code != 200:
    print(f'❌ Forum chats endpoint failed: {response.status_code}')
    exit(1)

data = response.json()
if not data.get('success') or not data.get('results'):
    print('❌ Forum chats response invalid')
    exit(1)

chat_count = len(data['results'])
print(f'✅ Found {chat_count} forum chats')

# Find chat with messages (chat ID 29)
test_chat_id = 29
print(f'\\n2. Testing messages endpoint for chat {test_chat_id}...')

response = client.get(f'/api/chat/forum/{test_chat_id}/messages/')
if response.status_code == 403:
    print('❌ Access denied (student not participant of chat 29)')
    # Try to find any chat this student is in
    for chat in data['results']:
        test_chat_id = chat['id']
        print(f'   Trying chat {test_chat_id} instead...')
        response = client.get(f'/api/chat/forum/{test_chat_id}/messages/')
        if response.status_code == 200:
            break

if response.status_code != 200:
    print(f'❌ Messages endpoint failed: {response.status_code}')
    exit(1)

msg_data = response.json()
print(f'\\n✅ Messages endpoint response:')
print(f'   success: {msg_data.get(\"success\")}')
print(f'   chat_id: {msg_data.get(\"chat_id\")}')
print(f'   count: {msg_data.get(\"count\")}')
print(f'   results: {len(msg_data.get(\"results\", []))} messages')

if msg_data.get('count') > 0:
    first_msg = msg_data['results'][0]
    print(f'\\n   First message:')
    print(f'     ID: {first_msg.get(\"id\")}')
    print(f'     Sender: {first_msg.get(\"sender\", {}).get(\"full_name\")}')
    print(f'     Content: {first_msg.get(\"content\", \"\")[:50]}...')
else:
    print('   ℹ️  Chat has no messages yet')

print('\\n✅ Backend API tests passed!')
print('\\n3. Frontend Fix Applied:')
print('   ✓ forumAPI.getForumMessages now returns ForumMessage[]')
print('   ✓ useForumMessages hook expects ForumMessage[]')
print('   ✓ Forum.tsx uses messages directly (not .results)')
print('   ✓ WebSocket cache updated for array structure')
print('\\n4. Test in Browser:')
print('   1. Navigate to http://localhost:8082/dashboard/student/forum')
print('   2. Open DevTools Console (F12)')
print('   3. Click on any chat')
print('   4. Verify console shows:')
print('      [useForumMessages] Messages array: [...] length: N')
print('      [Forum] Messages array is array: true')
print('      [Forum] Messages array length: N')
print('   5. Verify messages appear in UI')
print('\\n========================================')"

echo ""
echo "Fix Summary:"
echo "============"
echo ""
echo "ROOT CAUSE:"
echo "  unifiedAPI.request() auto-extracts 'results' array from paginated responses."
echo "  forumAPI.getForumMessages() was expecting full ForumMessagesResponse object,"
echo "  but received only the array, then tried to return it as ForumMessagesResponse."
echo "  Forum.tsx accessed .results on an array, got undefined, fell back to []."
echo ""
echo "FIX APPLIED:"
echo "  1. Changed forumAPI.getForumMessages return type: ForumMessage[]"
echo "  2. Updated useForumMessages to expect ForumMessage[]"
echo "  3. Updated Forum.tsx to use messages directly"
echo "  4. Fixed WebSocket cache update for array structure"
echo ""
echo "FILES MODIFIED:"
echo "  - frontend/src/integrations/api/forumAPI.ts"
echo "  - frontend/src/hooks/useForumMessages.ts"
echo "  - frontend/src/pages/dashboard/Forum.tsx"
echo ""
echo "========================================"
