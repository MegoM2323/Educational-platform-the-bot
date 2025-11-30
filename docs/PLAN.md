# Forum API Endpoints Fix Plan

## Overview

Critical bug discovered during browser testing: Forum frontend calls incorrect API paths causing all requests to return HTTP 404. Backend endpoints exist at `/api/chat/forum/` but frontend calls `/api/forum/chats/`. This breaks ALL forum functionality.

**Root Cause**: API path mismatch between frontend (`forumAPI.ts`) and backend URL routing (`chat/urls.py` + `config/urls.py`).

**Impact**:
- Users CANNOT use forum at all
- Chat list returns 404
- Messages cannot be sent
- WebSocket connection fails
- ALL 8 browser test scenarios blocked

**Goals**:
- Fix API endpoint paths in frontend
- Verify all 3 forum endpoints work (list chats, get messages, send message)
- Confirm WebSocket integration functional
- Pass all 8 browser test scenarios

## Active Tasks | Blocked Tasks | Pending | Escalations | Completed

### Active Tasks
None

### Blocked Tasks
None

### Pending
- T502 (@py-backend-dev): Verify forum backend endpoints respond correctly (waiting for dispatch)
- T503 (@qa-code-tester): Integration tests for forum API endpoints (blocked by T502)
- T504 (@qa-user-tester): Re-run 8 forum browser test scenarios (blocked by T503)

### Escalations
None

### Completed
- T501 (@react-frontend-dev): Fix forum API endpoint paths ✅

---

## Execution Order

### Wave 1: Fix Frontend API Paths (IMMEDIATE - 10 minutes)
- T501 (@react-frontend-dev): Fix forum API endpoint paths in forumAPI.ts

### Wave 2: Verify Backend Endpoints (SEQUENTIAL after T501)
- T502 (@py-backend-dev): Verify forum backend endpoints respond correctly

### Wave 3: Test Integration (SEQUENTIAL after T502)
- T503 (@qa-code-tester): Integration tests for forum API endpoints
- T504 (@qa-user-tester): Re-run 8 forum browser test scenarios

---

## Task Specifications

### T501: Fix forum API endpoint paths in forumAPI.ts
- **Agent**: react-frontend-dev
- **Priority**: CRITICAL
- **Parallel**: no
- **Status**: completed ✅
**Acceptance Criteria**:
  - [x] `getForumChats()` calls `/chat/forum/` instead of `/forum/chats/`
  - [x] `getForumMessages()` calls `/chat/forum/{id}/messages/` instead of `/forum/chats/{id}/messages/`
  - [x] `sendForumMessage()` calls `/chat/forum/{id}/send_message/` instead of `/forum/chats/{id}/send_message/`
  - [x] TypeScript types unchanged (no breaking changes)
  - [x] Response parsing unchanged
**Implementation Steps**:
1. Open `frontend/src/integrations/api/forumAPI.ts`
2. Change line 70: `'/forum/chats/'` → `'/chat/forum/'`
3. Change line 88: `'/forum/chats/${chatId}/messages/'` → `'/chat/forum/${chatId}/messages/'`
4. Change line 109: `'/forum/chats/${chatId}/send_message/'` → `'/chat/forum/${chatId}/send_message/'`
5. Save file
6. Verify no TypeScript errors: `npm run type-check` (from frontend/)
**Test Scenarios**:
  - TypeScript compilation succeeds
  - No runtime errors on forum page load
  - Browser network tab shows correct paths: `/api/chat/forum/`, `/api/chat/forum/{id}/messages/`, `/api/chat/forum/{id}/send_message/`
**References**:
  - `frontend/src/integrations/api/forumAPI.ts` (MODIFY lines 70, 88, 109)

**Results**:
- Changed 3 API endpoint paths
- TypeScript compilation successful (npx tsc --noEmit)
- No breaking changes to interfaces or response parsing
- Frontend now calls correct backend paths

### T502: Verify forum backend endpoints respond correctly
- **Agent**: py-backend-dev
- **Priority**: HIGH
- **Blocked by**: [T501]
**Acceptance Criteria**:
  - [ ] GET `/api/chat/forum/` returns 200 with chat list
  - [ ] GET `/api/chat/forum/{id}/messages/` returns 200 with messages
  - [ ] POST `/api/chat/forum/{id}/send_message/` returns 201 with created message
  - [ ] Permissions enforced (participant check)
  - [ ] Response format matches frontend TypeScript interfaces
**Implementation Steps**:
1. Start Django dev server: `cd backend && python manage.py runserver`
2. Create test SubjectEnrollment (or use existing from database)
3. Verify forum chats exist: `ChatRoom.objects.filter(type__in=['forum_subject', 'forum_tutor'])`
4. Test GET /api/chat/forum/ with student token:
   ```bash
   curl -H "Authorization: Token {student_token}" http://localhost:8000/api/chat/forum/
   ```
5. Verify response: `{"success": true, "count": N, "results": [...]}`
6. Get chat ID from response
7. Test GET /api/chat/forum/{id}/messages/:
   ```bash
   curl -H "Authorization: Token {student_token}" http://localhost:8000/api/chat/forum/{id}/messages/
   ```
8. Test POST /api/chat/forum/{id}/send_message/:
   ```bash
   curl -X POST -H "Authorization: Token {student_token}" -H "Content-Type: application/json" \
     -d '{"content": "Test message"}' \
     http://localhost:8000/api/chat/forum/{id}/send_message/
   ```
9. Verify message appears in database
10. Verify Pachca notification sent (if configured)
**Test Scenarios**:
  - Student GET /api/chat/forum/ → 200, returns student's chats
  - Teacher GET /api/chat/forum/ → 200, returns teacher's chats
  - Tutor GET /api/chat/forum/ → 200, returns tutor's chats
  - GET /api/chat/forum/{id}/messages/ → 200, returns messages
  - POST /api/chat/forum/{id}/send_message/ → 201, message created
  - Non-participant GET → 403
  - Invalid chat ID → 404
**References**:
  - `backend/chat/forum_views.py` (verify logic)
  - `backend/chat/urls.py` (verify routing)
  - `backend/config/urls.py` (verify `/api/chat/` inclusion)

### T503: Integration tests for forum API endpoints
- **Agent**: qa-code-tester
- **Priority**: HIGH
- **Blocked by**: [T502]
**Acceptance Criteria**:
  - [ ] Test: Student fetches chats → returns FORUM_SUBJECT + FORUM_TUTOR
  - [ ] Test: Teacher fetches chats → returns only FORUM_SUBJECT
  - [ ] Test: Student sends message → 201, message saved, signal triggered
  - [ ] Test: Non-participant access → 403
  - [ ] Test: Pagination works (limit/offset)
  - [ ] All tests pass
**Implementation Steps**:
1. Create `backend/tests/integration/chat/test_forum_api_endpoints.py`
2. Use pytest fixtures for student, teacher, tutor, subject, enrollment
3. Write test cases:
   - `test_student_list_chats()` - verify student sees both chat types
   - `test_teacher_list_chats()` - verify teacher sees only FORUM_SUBJECT
   - `test_tutor_list_chats()` - verify tutor sees only FORUM_TUTOR
   - `test_get_messages()` - verify pagination and response format
   - `test_send_message()` - verify message creation and signal
   - `test_permissions()` - verify non-participant blocked
4. Run tests: `pytest backend/tests/integration/chat/test_forum_api_endpoints.py -v`
5. Verify all pass
6. Check coverage: include forum_views.py
**Test Scenarios**:
  - All integration tests pass (6+ test cases)
  - No N+1 queries (use pytest-django's `django_assert_num_queries`)
  - Permissions correctly enforced
  - Response format matches frontend expectations
**References**:
  - `backend/tests/integration/chat/test_forum_api_endpoints.py` (CREATE)
  - `backend/tests/conftest.py` (use existing fixtures)

### T504: Re-run 8 forum browser test scenarios
- **Agent**: qa-user-tester
- **Priority**: HIGH
- **Blocked by**: [T503]
**Acceptance Criteria**:
  - [ ] Test 1: Student login → forum page → chat list loads (HTTP 200)
  - [ ] Test 2: Student selects teacher chat → messages load
  - [ ] Test 3: Student sends message → appears in chat
  - [ ] Test 4: Teacher login → forum page → student chats load
  - [ ] Test 5: Teacher sends reply → student receives (real-time or polling)
  - [ ] Test 6: Tutor login → forum page → assigned student chats load
  - [ ] Test 7: WebSocket connection established (ws://localhost:8000/ws/chat/{room_id}/)
  - [ ] Test 8: Real-time message delivery works
  - [ ] All 8 scenarios pass
**Implementation Steps**:
1. Start Django dev server (Daphne for WebSocket): `cd backend && daphne config.asgi:application`
2. Start frontend dev server: `cd frontend && npm run dev`
3. Use Playwright MCP to run browser tests
4. Scenario 1: Student login → navigate to `/dashboard/student/forum`
   - Wait for chat list to load
   - Verify HTTP GET /api/chat/forum/ returns 200
   - Verify chat list populated (≥1 chat)
5. Scenario 2: Click first chat in list
   - Verify HTTP GET /api/chat/forum/{id}/messages/ returns 200
   - Verify message window displays messages
6. Scenario 3: Type message "Hello teacher" and send
   - Verify HTTP POST /api/chat/forum/{id}/send_message/ returns 201
   - Verify message appears in chat window
7. Scenario 4: Logout student, login as teacher
   - Navigate to `/dashboard/teacher/forum`
   - Verify chat list loads with student chats
8. Scenario 5: Teacher sends reply "Hello student"
   - Verify message sent successfully
9. Scenario 6: Logout teacher, login as tutor
   - Navigate to `/dashboard/tutor/forum`
   - Verify chat list loads with assigned student chats
10. Scenario 7: Open browser DevTools → Network tab → WS filter
    - Verify WebSocket connection to `ws://localhost:8000/ws/chat/{room_id}/`
11. Scenario 8: Send message → verify appears immediately in other user's browser
    - Use two browser windows (student + teacher)
    - Send message from one → verify appears in other
12. Document any failures
13. Create fix tasks if needed
**Test Scenarios**:
  - All 8 browser test scenarios pass
  - HTTP requests return 200/201 (not 404)
  - WebSocket connection successful
  - Real-time updates work
  - No console errors in browser
  - No network errors
**References**:
  - Playwright MCP
  - `frontend/src/pages/dashboard/Forum.tsx` (component under test)
  - `frontend/src/integrations/api/forumAPI.ts` (API client)

---

## Timeline

- T501: 10 minutes (simple path changes)
- T502: 20 minutes (manual API testing)
- T503: 30 minutes (write integration tests)
- T504: 40 minutes (run 8 browser scenarios)

**Total**: ~1.5 hours to fully functional forum

---

## Notes

### Why This Happened

1. **Documentation mismatch**: FORUM_SYSTEM.md documented endpoints as `/api/forum/chats/` but actual backend routing is `/api/chat/forum/`
2. **Missing integration testing**: Unit tests passed (backend logic works) but integration tests didn't verify full URL paths
3. **Browser testing caught it**: qa-user-tester's E2E tests revealed HTTP 404 errors

### Prevention

1. Update FORUM_SYSTEM.md with correct paths after fix
2. Add integration tests verifying full URL paths (T503)
3. Add E2E tests to CI/CD pipeline

### Related Issues

- T003 (forum backend analysis) reported NO blocking issues → analysis was incomplete (didn't verify URL routing)
- T004 (forum frontend analysis) reported "API endpoint mismatch" → correct finding, but not escalated as blocker
