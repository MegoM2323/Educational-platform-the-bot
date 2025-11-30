# Project Plan: Forum Chat Display Bug Fix

## Overview

Critical frontend bug prevents forum chats from displaying despite working backend API. API endpoint `/api/chat/forum/` returns HTTP 200 with 6 chats in correct format `{success: true, count: 6, results: [...]}`. Data arrives in browser (visible in Network tab), but React component shows "Нет активных чатов" (No active chats). Root cause likely in data extraction chain: unifiedClient → forumAPI → useForumChats → Forum component.

**Goals**:
- Forum page displays all 6 chats correctly
- Chat list is clickable and functional
- Unread badges display
- Enable browser testing (currently blocked)

## Active Tasks | Blocked Tasks | Pending | Escalations | Completed

### Active Tasks
None

### Blocked Tasks
- T603 (@qa-user-tester): Execute comprehensive forum browser tests (blocked by T604)

### Pending
- T604 (@react-frontend-dev): Fix forum chat display bug (ready to dispatch)

### Escalations
None

### Completed
- T601 (@py-backend-dev): Fixed SupabaseAuthService initialization ✅
- T602 (@qa-code-tester): Executed 23/23 forum API tests ✅

---

## Execution Order

### Wave 1: Fix Frontend Bug (CRITICAL)
**Immediate:**
- T604 (@react-frontend-dev): Debug and fix chat display → Enable browser testing

### Wave 2: Browser Testing
**After T604 completes:**
- T603 (@qa-user-tester): Execute 8 browser test scenarios → Verify end-to-end workflows

**Total Estimated Time**: 30-60 minutes for T604, then 1-2 hours for T603

---

## Task Specifications

### T604: Fix Forum Chat Display Bug
- **Agent**: react-frontend-dev
- **Parallel**: no
- **Priority**: CRITICAL - blocks browser testing

**Acceptance Criteria**:
  - [ ] Forum page at `/dashboard/student/forum` displays chat list
  - [ ] All 6 forum chats visible in UI
  - [ ] Chat names display correctly (format: "{Subject} - {Student} ↔ {Teacher/Tutor}")
  - [ ] Chat types show correctly (FORUM_SUBJECT and FORUM_TUTOR badges)
  - [ ] Unread count badges appear if > 0
  - [ ] Clicking chat loads messages
  - [ ] No console errors
  - [ ] Data flows through: API → unifiedClient → forumAPI → useForumChats → Forum component

**Investigation Steps**:
1. **Open browser DevTools**:
   - Network tab: Check `/api/chat/forum/` response structure
   - Console: Check for errors, warnings, or data structure logs
   - React DevTools: Inspect `useForumChats` hook return value
   - Application tab: Check localStorage cache

2. **Trace data flow**:
   - API returns: `{success: true, count: 6, results: [chat1, chat2, ...]}`
   - unifiedClient.request() line 680-685: Should extract `results` array
   - forumAPI.getForumChats() line 75: Should return `response.data?.results || []`
   - useForumChats() line 7: Should return React Query object with `data` field
   - Forum.tsx line 300: Should extract `chats` from `data` with fallback `[]`

3. **Add debug logging**:
   - forumAPI.getForumChats(): Log `response.data` before returning
   - useForumChats(): Log query result before return
   - Forum.tsx: Log `chats` variable after extraction
   - Identify where data becomes empty/undefined

4. **Check common issues**:
   - Response structure mismatch: API might return different format than expected
   - Type mismatch: TypeScript types might not match actual data
   - Async timing: Component might render before data arrives
   - Cache issue: React Query might cache old empty response
   - Conditional rendering: Component might hide chats due to wrong condition

5. **Fix implementation**:
   - If data extraction wrong: Fix forumAPI.getForumChats() or unifiedClient logic
   - If type mismatch: Update TypeScript interfaces
   - If async issue: Add proper loading/error states
   - If cache issue: Clear React Query cache or adjust cache config
   - Test fix: Verify all 6 chats appear in UI

**Test Scenarios**:
  - Valid login: Student user → Navigate to `/dashboard/student/forum` → See chat list
  - Chat count: Verify 6 chats appear (3 FORUM_SUBJECT + 3 FORUM_TUTOR if student has tutor)
  - Chat data: Each chat shows name, subject (if FORUM_SUBJECT), unread count, last message
  - Click chat: Select chat → Messages load → Can type and send
  - Search: Type in search → Chat list filters correctly
  - Empty state: If no chats (edge case), shows "Нет активных чатов"
  - Loading state: While loading, shows skeleton loaders

**Files to Examine**:
  - `frontend/src/integrations/api/forumAPI.ts` (CRITICAL - line 68-76)
  - `frontend/src/integrations/api/unifiedClient.ts` (REVIEW - line 680-685, response extraction)
  - `frontend/src/hooks/useForumChats.ts` (VERIFY - line 5-11, React Query usage)
  - `frontend/src/pages/dashboard/Forum.tsx` (CHECK - line 300, data extraction)
  - Browser DevTools Network/Console (DIAGNOSE)

**Expected Fix Location**:
Most likely one of these:
1. forumAPI.getForumChats() not extracting `results` correctly
2. unifiedClient not handling forum API response format
3. useForumChats() not returning data properly
4. Forum.tsx not accessing data correctly

**Debug Commands**:
```bash
# Open browser console and run:
localStorage.clear()  # Clear cache
# Reload page
# Check Network tab for /api/chat/forum/ response
# Check Console for any errors or warnings
```

---

### T603: Execute Comprehensive Forum Browser Tests
- **Agent**: qa-user-tester
- **Blocked by**: [T604]
- **Parallel**: no

**Acceptance Criteria**:
  - [ ] All 8 forum browser test scenarios pass
  - [ ] Student can send message to teacher and receive reply
  - [ ] Tutor can message student
  - [ ] Real-time message updates via WebSocket
  - [ ] Unread badges display correctly
  - [ ] Chat list filtering/search works
  - [ ] Responsive UI on mobile viewport

**Test Scenarios**:
  - Student login → navigate to `/dashboard/student/forum` → see chat list
  - Select teacher chat → messages load → type and send message → message appears
  - Teacher login → see new unread badge → open student chat → read message → reply
  - Student sees reply in real-time via WebSocket
  - Tutor login → navigate to forum → see assigned students → send message
  - Student receives tutor message → badge appears → opens chat → reads and replies
  - Multi-subject workflow: Student with 3 subjects → sees 3 separate chats → switches between them
  - Search/filter: Type teacher name → chat list filters → only matching chats visible

**References**:
  - `frontend/tests/e2e/forum/` (EXECUTE ALL .spec.ts FILES)
  - `frontend/src/pages/dashboard/forum/ForumPage.tsx` (VERIFY RENDERING)
  - `frontend/src/hooks/useForumChats.ts` (CHECK STATE MANAGEMENT)

---

## Technical Context

### Current Status
- ✅ **Backend API**: 23/23 tests passed, API returns HTTP 200 with correct data
- ✅ **Database**: Forum chats exist (6 chats created via signals)
- ✅ **Authentication**: Login works, tokens issued correctly
- ❌ **Frontend Display**: React component does not render chats despite receiving data
- ⏸️ **Browser Tests**: Blocked until UI displays chats

### API Response Format (Verified Working)
```json
{
  "success": true,
  "count": 6,
  "results": [
    {
      "id": 1,
      "name": "Math - Student1 ↔ Teacher1",
      "type": "forum_subject",
      "subject": {"id": 1, "name": "Math"},
      "participants": [...],
      "unread_count": 0,
      "last_message": {...},
      "created_at": "2025-12-01T10:00:00Z",
      "updated_at": "2025-12-01T10:00:00Z",
      "is_active": true
    },
    // ... 5 more chats
  ]
}
```

### Frontend Data Flow
```
1. API Response → unifiedClient.request<ForumChatsResponse>('/chat/forum/')
2. unifiedClient extracts response.data.results (line 680-685)
3. forumAPI.getForumChats() returns response.data?.results || [] (line 75)
4. useForumChats() wraps in React Query: queryFn: () => forumAPI.getForumChats()
5. Forum.tsx extracts: const { data: chats = [] } = useForumChats()
6. ChatList component receives chats prop
7. ChatList renders chat items or "Нет активных чатов" if empty
```

**Problem Point**: Data becomes empty somewhere in steps 3-7

### Expected Outcome
After T604: Forum page displays all 6 chats → T603 executes → Browser tests pass → User confirms "переписка полностью работает между студентами и преподователями и между тьюторами и студентами"
