# Forum UI Bug Diagnosis

## Issue
Forum messages don't display in UI when clicking a chat, even though API returns data correctly.

## Enhanced Debugging Applied

Added comprehensive console logging to:
1. `/frontend/src/hooks/useForumMessages.ts` - Track hook execution and query state
2. `/frontend/src/pages/dashboard/Forum.tsx` - Track chat selection and render state

## Testing Steps

1. **Open Forum Page**
   - Login as student (e.g., Иван Соколов - ID 20)
   - Navigate to `/dashboard/student/forum`

2. **Open Browser DevTools**
   - Press F12
   - Go to Console tab
   - Clear console (Ctrl+L)

3. **Click on a Chat**
   - Click on any chat in the left panel
   - Watch console logs

4. **Expected Console Output**

```
[Forum] handleSelectChat called with chat: {id: 29, name: "...", ...}
[Forum] chat.id: 29 type: number
[Forum] selectedChat state updated

[Forum] ===== RENDER STATE =====
[Forum] Selected chat: {id: 29, ...}
[Forum] Selected chat ID: 29 type: number
[Forum] Messages response: {success: true, chat_id: "29", count: 1, results: [...]}
[Forum] Messages response structure: ["success", "chat_id", "limit", "offset", "count", "results"]
[Forum] Messages array: [{id: 110, content: "...", ...}]
[Forum] Messages array length: 1
[Forum] Is loading messages: false
[Forum] ===== END RENDER STATE =====

[useForumMessages] Hook called with chatId: 29 type: number enabled: true
[useForumMessages] queryFn executing for chatId: 29
[useForumMessages] Fetching messages for chat: 29
[forumAPI] Fetching messages from: /chat/forum/29/messages/?limit=50&offset=0
[forumAPI] Raw response: {data: {...}, error: null}
[forumAPI] Returning result: {success: true, ...}
[useForumMessages] Messages result: {success: true, ...}
[useForumMessages] Query state: {status: "success", isLoading: false, data: {...}, ...}
```

5. **Check Network Tab**
   - Go to Network tab in DevTools
   - Filter by "messages"
   - Should see: `GET /api/chat/forum/29/messages/?limit=50&offset=0`
   - Status: 200 OK
   - Response should contain messages array

## Potential Issues to Look For

### Issue 1: Query Not Enabled
**Symptom:**
```
[useForumMessages] Hook called with chatId: null type: object enabled: false
```
**Cause:** `selectedChat?.id` is null/undefined
**Fix:** Check why chat object doesn't have id property

### Issue 2: Query Runs But No Data
**Symptom:**
```
[useForumMessages] Query state: {status: "success", data: {results: []}, ...}
```
**Cause:** API returns empty results (permissions issue or no messages)
**Fix:** Check backend permissions and database

### Issue 3: Type Mismatch
**Symptom:**
```
[Forum] Selected chat ID: "29" type: string
```
**Cause:** Chat ID is string instead of number
**Fix:** Parse ID to number in hook call

### Issue 4: Response Structure Mismatch
**Symptom:**
```
[Forum] Messages response: undefined
[Forum] Messages array length: 0
```
**But Network tab shows 200 OK with data**
**Cause:** Response not being returned from queryFn
**Fix:** Check forumAPI.getForumMessages return value

## Manual API Test

```bash
cd backend
source ../.venv/bin/activate
python manage.py shell

# Test as student ID 20
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
client = Client()
student = User.objects.get(id=20)
client.force_login(student)

# Test forum chats
response = client.get('/api/chat/forum/')
print(response.json())

# Test messages for chat 29
response = client.get('/api/chat/forum/29/messages/')
print(response.json())
```

## Fix Checklist

- [ ] Verify `selectedChat.id` is number (not string, not undefined)
- [ ] Verify `useForumMessages` hook receives valid chatId
- [ ] Verify `enabled: !!chatId` evaluates to true when chat selected
- [ ] Verify `queryFn` executes (console log appears)
- [ ] Verify API request appears in Network tab
- [ ] Verify API returns 200 OK with data
- [ ] Verify `forumAPI.getForumMessages` returns correct structure
- [ ] Verify `messagesResponse` contains results array
- [ ] Verify `messages` array has items
- [ ] Verify render logic displays messages (not stuck in loading/empty state)

## Next Steps

Based on console logs, we can identify the exact point of failure and apply targeted fix.
