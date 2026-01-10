# T10: Manual Testing Checklist for Chat System Fixes

## Overview
This checklist covers manual verification tests for chat system optimizations:
- Query optimization (no N+1)
- WebSocket performance
- Memory leaks
- Rate limiting

---

## Test Setup

### Prerequisites
- Production environment: https://the-bot.ru
- Test accounts ready:
  - Student: test_student@test.local / password
  - Teacher: test_teacher@test.local / password
- Browser DevTools: Network tab open
- Chrome DevTools: Lighthouse performance available

### Environment Variables
```
ENVIRONMENT=production
DEBUG=False
```

---

## Test Group 1: Query Performance (N+1 Queries)

### T10.1: Load 100 chats - verify API latency < 100ms

**Procedure:**
1. Login as student with 100+ active chats
2. Open DevTools Network tab
3. Navigate to Forum/Chat page
4. Monitor GET `/api/chat/` request

**Expected Results:**
- Response time: **< 100ms** (target: 50ms)
- Query count: **2-3** (with prefetch_related optimization)
- No timeout errors
- All chat data loaded correctly

**Pass/Fail Criteria:**
- [ ] Response time < 100ms
- [ ] Chat list displays all chats
- [ ] No 500 errors in console
- [ ] Network tab shows single prefetch query

**Notes:**
- If >100ms, check database indexes on ChatParticipant and Message
- Verify prefetch_related is being used in ChatRoomViewSet.list()

---

### T10.2: Load notifications endpoint - verify latency < 50ms

**Procedure:**
1. Open DevTools Console
2. Execute: `fetch('/api/chat/notifications/').then(r => r.json()).then(console.log)`
3. Monitor response time

**Expected Results:**
- Response time: **< 50ms** (target: 20ms)
- Response format:
  ```json
  {
    "unread_messages": 5,
    "unread_threads": 2,
    "has_new_messages": true
  }
  ```
- Query count: **2** (filter participants + subquery aggregation)

**Pass/Fail Criteria:**
- [ ] Response < 50ms
- [ ] Correct unread counts returned
- [ ] No database queries per chat
- [ ] Cache is being used (verified in logs)

**Notes:**
- Check /api/chat/notifications/ is using Subquery with Coalesce
- Verify no N+1 query pattern

---

### T10.3: Load chat with 10k messages - verify sorting performance

**Procedure:**
1. Select a chat with many messages
2. Scroll to bottom (load all messages)
3. Measure load time in DevTools

**Expected Results:**
- Initial page load: **< 200ms**
- Pagination response: **< 100ms**
- No memory leaks during scrolling

**Pass/Fail Criteria:**
- [ ] Load time < 200ms
- [ ] Pagination works smoothly
- [ ] Messages sort correctly by date
- [ ] No lag when scrolling

---

## Test Group 2: WebSocket Performance

### T10.4: Rapid chat switching - verify no connection leaks (5 switches/sec for 30 seconds)

**Procedure:**
1. Login as student
2. Open DevTools Network tab with WebSocket filter
3. Open chat list
4. Rapidly switch between chats (click 5 chats per second)
5. Monitor WebSocket connections in DevTools for 30 seconds
6. Observe memory usage in Task Manager

**Expected Results:**
- WebSocket connections: **1 active** (properly cleanup old connections)
- Memory growth: **< 10MB** during 30-second test
- No connection errors in console
- All connections properly closed

**Pass/Fail Criteria:**
- [ ] Only 1 active WebSocket at end of test
- [ ] No "Connection reset" errors
- [ ] Memory stable (no continuous growth)
- [ ] No warnings about unhandled connections

**Detailed Checks:**
- Open DevTools Sources > Pause on exceptions
- Look for any unclosed WebSocket connections
- Verify previousChatIdRef is being cleared properly

**Notes:**
- If > 1 active WebSocket: check cleanup in handleSelectChat callback
- If memory grows: check for timeout leaks (switchTimeoutRef)
- Issue: Fixed in T5/T6 (cleanup handlers and previousChatIdRef)

---

### T10.5: Permission change during active WebSocket - verify disconnect in < 5 minutes

**Procedure:**
1. Student connects to chat as WebSocket
2. Admin (in separate browser) removes student's enrollment from course
3. Monitor WebSocket in DevTools
4. Wait up to 5 minutes, verify disconnection

**Expected Results:**
- WebSocket closes with code **4003** (Forbidden)
- Disconnect occurs within **5 minutes** (300 seconds)
- User sees notification/redirect to chat list
- No error messages in console

**Pass/Fail Criteria:**
- [ ] WebSocket closes within 5 minutes
- [ ] Close code is 4003
- [ ] No error messages displayed
- [ ] User redirected to appropriate page

**Implementation Check:**
- Heartbeat loop in consumers.py checks permissions every 300 seconds
- _check_current_permissions is called in heartbeat
- If permission fails, connection closes with code 4003

**Notes:**
- Test requires admin access to change enrollments
- May need to create separate test/staging environment
- Fixed in T7 (periodic permission recheck in heartbeat)

---

## Test Group 3: Database Indexes

### T10.6: Message sender index verification

**Procedure:**
1. Run Django shell: `python manage.py shell`
2. Execute:
   ```python
   from django.db import connection
   from django.test.utils import CaptureQueriesContext
   from chat.models import Message
   from accounts.models import User

   user = User.objects.first()

   with CaptureQueriesContext(connection) as ctx:
       messages = list(Message.objects.filter(sender=user))

   print(f"Queries: {len(ctx)}")
   print(f"SQL: {ctx[0]['sql']}")  # Should use index scan
   ```

**Expected Results:**
- Query count: **1** (single indexed query)
- SQL plan uses **Index Scan** on idx_message_sender
- Execution time: **< 50ms** even with 10k+ messages

**Pass/Fail Criteria:**
- [ ] Only 1 query executed
- [ ] Index scan used (check EXPLAIN ANALYZE)
- [ ] No sequential scan
- [ ] Time < 50ms

**Notes:**
- Migration 0020_add_message_sender_index.py creates the index
- PostgreSQL EXPLAIN ANALYZE shows index usage
- Run: `EXPLAIN ANALYZE SELECT * FROM chat_message WHERE sender_id = X;`

---

### T10.7: Participant-user index verification

**Procedure:**
1. Django shell:
   ```python
   from django.db import connection
   from django.test.utils import CaptureQueriesContext
   from chat.models import ChatParticipant
   from accounts.models import User

   user = User.objects.first()

   with CaptureQueriesContext(connection) as ctx:
       participants = list(ChatParticipant.objects.filter(user=user))

   print(f"Queries: {len(ctx)}")
   print(f"SQL: {ctx[0]['sql']}")
   ```

**Expected Results:**
- Query count: **1**
- Index used: idx_chat_participant_user_room
- Execution time: **< 20ms**

**Pass/Fail Criteria:**
- [ ] Single indexed query
- [ ] Index scan confirmed
- [ ] Time < 20ms

---

## Test Group 4: Cache Performance

### T10.8: Redis cache for can_initiate_chat

**Procedure:**
1. Django shell:
   ```python
   from django.core.cache import cache
   from chat.permissions import can_initiate_chat
   from accounts.models import User

   cache.clear()

   user1 = User.objects.first()
   user2 = User.objects.all()[1]

   # First call - hits database
   result1 = can_initiate_chat(user1, user2)

   # Check cache key
   key = f'chat_permission:{min(user1.id, user2.id)}:{max(user1.id, user2.id)}'
   cached = cache.get(key)
   print(f"Cache hit: {cached == result1}")

   # Second call - should be faster (from cache)
   result2 = can_initiate_chat(user1, user2)
   print(f"Results match: {result1 == result2}")
   ```

**Expected Results:**
- First call: hits database
- Cache key format: `chat_permission:{min_id}:{max_id}`
- Second call: uses cache (< 5ms)
- Timeout: 300 seconds (5 minutes)

**Pass/Fail Criteria:**
- [ ] Cache key created correctly
- [ ] Value stored in cache
- [ ] Reverse order (user2, user1) hits same cache
- [ ] Cache expires after 5 minutes

**Notes:**
- Uses deterministic key with min/max for consistency
- Fixed in T4 (Redis caching for permissions)

---

## Test Group 5: Rate Limiting

### T10.9: Message rate limiting under load

**Procedure:**
1. Write script to send 50 messages in 10 seconds
2. Monitor responses for 429 (Too Many Requests) errors
3. Check rate limit headers

**Expected Results:**
- First N messages: **200 OK**
- After limit: **429 Too Many Requests**
- Headers include:
  - `RateLimit-Limit: 10`
  - `RateLimit-Remaining: X`
  - `RateLimit-Reset: timestamp`

**Pass/Fail Criteria:**
- [ ] Rate limiting enforced
- [ ] Correct HTTP status codes
- [ ] Rate limit headers present
- [ ] Limit resets after cooldown

**Test Script:**
```python
import requests
import time

for i in range(50):
    response = requests.post(
        'https://the-bot.ru/api/chat/1/messages/',
        json={'content': f'Message {i}'},
        headers={'Authorization': f'Bearer {token}'}
    )
    print(f"{i}: {response.status_code}")
    if response.status_code == 429:
        print(f"Rate limited after {i} messages")
        break
    time.sleep(0.2)
```

---

## Test Group 6: WebSocket Authentication

### T10.10: Invalid token handling

**Procedure:**
1. Open WebSocket to chat without Authorization header
2. Send invalid token
3. Monitor WebSocket connection

**Expected Results:**
- WebSocket accepts initially (for message delivery)
- Auth timeout: **20 seconds**
- Close code: **4001** (Unauthorized)
- Error message logged

**Pass/Fail Criteria:**
- [ ] WebSocket closes after timeout
- [ ] Close code is 4001
- [ ] Error logged in console
- [ ] User cannot send messages

---

## Test Group 7: Performance Benchmarks

### T10.11: Load test - 100 concurrent users in same chat

**Procedure:**
1. Use load testing tool (Apache Bench, JMeter, or custom script)
2. Simulate 100 users connecting to same chat
3. Each user sends 1 message per second
4. Duration: 60 seconds

**Expected Results:**
- Success rate: **> 99%**
- Response time p95: **< 500ms**
- No database connection pool exhaustion
- No out-of-memory errors

**Commands:**
```bash
# Using Apache Bench
ab -n 100 -c 10 https://the-bot.ru/api/chat/1/messages/

# Using hey
hey -n 1000 -c 100 https://the-bot.ru/api/chat/1/messages/
```

---

## Test Group 8: Regression Tests

### T10.12: Auth token persistence after login

**Procedure:**
1. Login at /auth/signin
2. Open DevTools Application tab
3. Check localStorage for `auth_token`

**Expected Results:**
- Token present in localStorage
- Token format: JWT (3 parts separated by dots)
- Token used in Authorization header

**Pass/Fail Criteria:**
- [ ] Token saved in localStorage
- [ ] Token valid (can decode)
- [ ] API requests use token
- [ ] No 401 errors after login

**Notes:**
- Fixed in T20 (500ms delay + token verification)

---

## Test Group 9: Error Scenarios

### T10.13: Deleted message handling

**Procedure:**
1. Send message
2. Delete it using DELETE endpoint
3. Reload chat
4. Check if message appears

**Expected Results:**
- Message not displayed
- Message marked as is_deleted=True in database
- No error messages

**Pass/Fail Criteria:**
- [ ] Deleted message not shown
- [ ] Delete completes successfully
- [ ] No broken UI elements

---

### T10.14: Edited message update

**Procedure:**
1. Send message "Hello"
2. Edit to "Hello World"
3. Verify in real-time and after reload

**Expected Results:**
- Message updated immediately via WebSocket
- "Edited" indicator appears
- Edit history available (if implemented)

**Pass/Fail Criteria:**
- [ ] Message text updated
- [ ] Edited flag set
- [ ] WebSocket broadcast works
- [ ] Data persistent after reload

---

## Summary Checklist

### Critical Tests (Must Pass)
- [ ] T10.1: Chat list < 100ms response time
- [ ] T10.2: Notifications < 50ms response time
- [ ] T10.4: No WebSocket leaks during rapid switching
- [ ] T10.5: Permission check closes WebSocket in < 5 min
- [ ] T10.12: Auth token persists after login

### Important Tests (Should Pass)
- [ ] T10.3: Large chat message pagination
- [ ] T10.6: Message sender index used
- [ ] T10.8: Cache working for permissions
- [ ] T10.9: Rate limiting enforced
- [ ] T10.13-14: Message edit/delete works

### Performance Benchmarks
- [ ] API response time: < 100ms (most endpoints)
- [ ] WebSocket latency: < 200ms
- [ ] Memory growth: < 10MB during rapid switching
- [ ] Database queries: 2-3 max per endpoint

---

## Failure Remediation

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| > 100ms response | N+1 queries | Add prefetch_related, Subquery |
| WebSocket leak | No cleanup | Clear previousChatIdRef, timeout |
| Permission not checked | Heartbeat disabled | Enable _check_current_permissions |
| Memory growth | Unclosed connections | Ensure disconnectFromRoom() called |
| Auth token lost | Race condition | Increase delay in Auth.tsx |
| Index not used | Wrong column | Verify migration 0020 applied |

---

## Files to Check During Testing

```
backend/chat/views.py                       # ChatNotificationsView optimization
backend/chat/consumers.py                   # WebSocket heartbeat loop
backend/chat/permissions.py                 # can_initiate_chat cache
backend/chat/migrations/0020_*.py          # Message sender index
frontend/src/pages/dashboard/Forum.tsx     # Token delay, cleanup handlers
```

---

## Performance Targets

| Metric | Target | Pass | Fail |
|--------|--------|------|------|
| Chat list API | 50ms | <100ms | >100ms |
| Notifications API | 20ms | <50ms | >50ms |
| Message load (10k) | 200ms | <300ms | >300ms |
| WebSocket disconnect | 300s | <5min | >5min |
| Memory growth (30s) | 0MB | <10MB | >10MB |
| Query count | 2 | 2-3 | >5 |

---

## Sign-off

| Test | Tester | Date | Status |
|------|--------|------|--------|
| T10.1 | | | PASS/FAIL |
| T10.2 | | | PASS/FAIL |
| T10.3 | | | PASS/FAIL |
| T10.4 | | | PASS/FAIL |
| T10.5 | | | PASS/FAIL |
| T10.6 | | | PASS/FAIL |
| T10.7 | | | PASS/FAIL |
| T10.8 | | | PASS/FAIL |
| T10.9 | | | PASS/FAIL |
| T10.10 | | | PASS/FAIL |
| T10.11 | | | PASS/FAIL |
| T10.12 | | | PASS/FAIL |
| T10.13 | | | PASS/FAIL |
| T10.14 | | | PASS/FAIL |
