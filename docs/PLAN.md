# THE BOT Platform - Complete Recovery Plan

## Overview

Complete restoration and stabilization of THE BOT Platform after identifying critical failures across all core modules. User reports indicate fundamental issues with dashboards (all 4 roles), forum system (complete failure), scheduling (teacher/student views broken), admin panel (CRUD operations failing), profiles (data not persisting), test data generation (invalid data), environment mode switching (production URLs leaking into development), and CI/CD pipeline (tests failing). Additionally, project structure requires cleanup: consolidate tests into `tests/` directory, remove obsolete documentation, update CLAUDE.md with current architecture, streamline README.

This is a comprehensive recovery mission requiring systematic analysis, prioritized fixes, thorough testing, and final documentation update. Must preserve existing architecture (Django backend with service layer pattern, React frontend with TanStack Query, WebSocket real-time chat, YooKassa payments, Pachca notifications) while fixing all reported failures.

**Goals**:
- All dashboards fully functional (student, teacher, tutor, parent) with correct data, optimized queries, and working buttons
- Forum system operational for all communication paths (student-teacher, student-tutor) with auto-chat creation and Pachca notifications
- Scheduling working for teachers (create/edit/delete lessons) and students (view schedule)
- Admin panel CRUD operations successful (create users, assign parents, reset passwords)
- Profile data persisting correctly for all roles with avatar upload
- Environment mode isolation (dev uses localhost, production uses production URLs, no leaking)
- Valid test data generation script creating realistic users, subjects, enrollments, lessons, forum chats
- CI/CD pipeline passing with consolidated test structure
- Clean project structure: tests consolidated, obsolete docs removed
- Updated documentation reflecting current state

## Active Tasks | Blocked Tasks | Pending | Escalations | Completed

### Active Tasks
None

### Blocked Tasks
None

### Pending
All tasks pending Wave 1 start

### Escalations
None

### Completed
- T003 (@py-backend-dev): Analyze forum backend system ✅
- T005 (@py-backend-dev): Analyze scheduling backend implementation ✅
- T027 (@docs-maintainer): Clean up docs directory ✅
- T028 (@docs-maintainer): Update CLAUDE.md with current architecture ✅
- T029 (@docs-maintainer): Update README to be concise and accurate ✅

## Execution Order

### Wave 1: Critical Analysis (PARALLEL - 8 tasks)
**Purpose**: Understand current state, identify all issues, document problems before fixing anything.

- T001 (@py-backend-dev): Analyze dashboard backend APIs and service layer
- T002 (@react-frontend-dev): Analyze dashboard frontend components and hooks
- T003 (@py-backend-dev): Analyze forum backend system
- T004 (@react-frontend-dev): Analyze forum frontend implementation
- T005 (@py-backend-dev): Analyze scheduling backend implementation
- T006 (@react-frontend-dev): Analyze scheduling frontend implementation
- T007 (@py-backend-dev): Analyze admin panel backend
- T008 (@react-frontend-dev): Analyze admin panel frontend

### Wave 2: Foundation Analysis (PARALLEL - 3 tasks)
After Wave 1 complete:
**Purpose**: Analyze infrastructure issues that affect all features.

- T009 (@devops-engineer): Analyze environment configuration and URL leaking
- T010 (@db-schema-specialist): Analyze profile models and data persistence
- T011 (@py-backend-dev): Analyze test data generation script

### Wave 3: Backend Critical Fixes (PRIORITIZED - 6 tasks)
After T001, T003, T005, T007, T009, T010, T011 complete:
**Purpose**: Fix all backend issues before touching frontend.

- T012 (@py-backend-dev): Fix dashboard APIs and service methods [PRIORITY 1]
- T013 (@py-backend-dev): Fix forum backend (chat creation, messaging) [PRIORITY 2]
- T014 (@py-backend-dev): Fix scheduling backend (lesson CRUD, validation) [PRIORITY 3]
- T015 (@py-backend-dev): Fix admin panel backend (user creation, assignment) [PRIORITY 4]
- T016 (@db-schema-specialist): Fix profile data persistence issues [PRIORITY 5]
- T017 (@devops-engineer): Fix environment URL isolation [PRIORITY 6]

### Wave 4: Frontend Critical Fixes (PARALLEL - 4 tasks)
After T002, T004, T006, T008 + backend fixes T012-T017 complete:
**Purpose**: Fix frontend to work with fixed backend.

- T018 (@react-frontend-dev): Fix dashboard frontend (all 4 roles)
- T019 (@react-frontend-dev): Fix forum frontend (chat list, messaging)
- T020 (@react-frontend-dev): Fix scheduling frontend (teacher/student pages)
- T021 (@react-frontend-dev): Fix admin panel frontend (user creation forms)

### Wave 5: Test Data & Infrastructure (PARALLEL - 2 tasks)
After T011, T016, T017 complete:
**Purpose**: Create valid test data and comprehensive test suite.

- T022 (@py-backend-dev): Implement valid test data generation script
- T023 (@qa-code-tester): Create comprehensive backend test suite

### Wave 6: Testing & Validation (SEQUENTIAL - 2 tasks)
After T012-T022 complete:
**Purpose**: Verify all fixes work correctly.

- T024 (@qa-code-tester): Run backend integration tests
- T025 (@qa-user-tester): Run E2E browser tests (all user flows)

### Wave 7: Project Cleanup (PARALLEL - 4 tasks)
After T024, T025 pass:
**Purpose**: Clean up project structure and documentation.

- T026 (@devops-engineer): Consolidate tests into tests/ directory
- T027 (@docs-maintainer): Clean up docs/ directory (remove obsolete)
- T028 (@docs-maintainer): Update CLAUDE.md with current architecture
- T029 (@docs-maintainer): Update README to be concise

### Wave 8: Final Verification (SEQUENTIAL - 2 tasks)
After T026-T029 complete:
**Purpose**: Final smoke test and CI/CD verification.

- T030 (@qa-code-tester): Verify CI/CD pipeline passes
- T031 (@devops-engineer): Final smoke test in dev and production modes

---

## Task Specifications

### T001: Analyze dashboard backend APIs and service layer
- **Agent**: py-backend-dev
- **Parallel**: yes
- **Status**: completed ✅
**Acceptance Criteria**:
  - [x] Document current dashboard service methods for all 4 roles
  - [x] Identify broken endpoints or missing data
  - [x] List query optimization issues (N+1 queries)
  - [x] Verify permissions per role
  - [x] Identify deprecated or obsolete code
**Subtasks**:
  - [x] Read `backend/materials/student_dashboard_service.py`
  - [x] Read `backend/materials/teacher_dashboard_service.py`
  - [x] Read `backend/materials/tutor_dashboard_service.py`
  - [x] Read `backend/materials/parent_dashboard_service.py`
  - [x] Check corresponding `*_dashboard_views.py` files
  - [x] Check for select_related/prefetch_related usage
  - [x] Verify error handling and logging
  - [x] Check caching implementation
**References**:
  - `backend/materials/student_dashboard_service.py`
  - `backend/materials/teacher_dashboard_service.py`
  - `backend/materials/tutor_dashboard_service.py`
  - `backend/materials/parent_dashboard_service.py`
  - `backend/materials/student_dashboard_views.py`
  - `backend/materials/teacher_dashboard_views.py`
  - `backend/materials/tutor_dashboard_views.py`
  - `backend/materials/parent_dashboard_views.py`

**Findings**:

**CRITICAL ISSUES:**

1. BROKEN FEATURE - Obsolete General Chat (Student & Teacher)
   - Location: student_dashboard_service.py lines 363-384, teacher_dashboard_service.py lines 589-610
   - Issue: Creates chat with type='general' which does NOT exist in ChatRoom.Type enum
   - Result: get_general_chat_access() will ALWAYS fail, try to create chat, then fail with DB error
   - Recommendation: REMOVE this entire feature (obsolete, replaced by forum system)

2. N+1 QUERY - Student Material Progress
   - Location: student_dashboard_service.py lines 76-81
   - Issue: Loops through materials.progress.all() in Python to filter by student
   - Fix: Use Prefetch with Q filter: `Prefetch('progress', queryset=MaterialProgress.objects.filter(student=self.student))`

3. N+1 QUERY - Teacher Student Progress Stats
   - Location: teacher_dashboard_service.py lines 335-337
   - Issue: Filters progress queryset INSIDE loop for each subject
   - Fix: Annotate before loop or use dict lookup from pre-aggregated data

4. INEFFICIENT QUERY - Teacher Materials List
   - Location: teacher_dashboard_service.py lines 84-88
   - Issue: Fetches ALL material IDs with values_list, then uses in large IN clause
   - Impact: If teacher has 1000+ materials, creates huge IN query
   - Fix: Use subquery or limit scope

5. INEFFICIENT BULK CREATE - Report Analytics
   - Location: teacher_dashboard_service.py lines 628-670
   - Issue: Creates AnalyticsData records one-by-one in loop
   - Fix: Collect records in list, use bulk_create()

**HIGH PRIORITY ISSUES:**

6. COMPLEX METHOD - Parent Dashboard Data
   - Location: parent_dashboard_service.py lines 637-786 (150 lines)
   - Issue: Nested loops, multiple service calls, high N+1 potential
   - Fix: Refactor into smaller methods, batch queries

7. POOR ERROR HANDLING - Parent Dashboard
   - Location: parent_dashboard_service.py line 753-756
   - Issue: Catches ALL exceptions with continue, hides critical errors
   - Fix: Handle specific exceptions, log failures properly

8. MISSING CACHE INVALIDATION
   - Issue: No cache invalidation when student completes material, teacher assigns material, tutor assigns subject
   - Impact: Stale data shown in dashboards
   - Fix: Add cache invalidation calls in relevant service methods

**MEDIUM PRIORITY ISSUES:**

9. Duplicate Logic - get_all_students()
   - Locations: teacher_dashboard_service.py lines 769-809, teacher_dashboard_views.py lines 620-625
   - Fix: Centralize in service only

10. Excessive Logging
   - All services have 100+ debug log statements
   - Recommendation: Remove redundant logs, keep only critical errors

11. Generic Exception Handling
   - All views catch generic Exception for 500 errors
   - Fix: Catch specific Django exceptions (ValidationError, ObjectDoesNotExist, PermissionDenied)

**LOW PRIORITY ISSUES:**

12. Missing deadline field usage in recent_activity()
    - Location: student_dashboard_service.py lines 285-287
    - Uses published_at as deadline (incorrect)

13. Schema inconsistency check in tutor reports
    - Location: tutor_dashboard_service.py line 445
    - Fallback for is_read attribute suggests inconsistent schema

**POSITIVE FINDINGS:**

- Caching implemented correctly with decorators
- Permissions validated properly in all services
- select_related/prefetch_related used in most places (except issues noted above)
- Admins properly excluded from student lists (is_staff=False, is_superuser=False checks)

**RECOMMENDATIONS FOR T012:**

Priority 1: Remove obsolete general chat feature (will cause runtime errors)
Priority 2: Fix N+1 queries in student/teacher services
Priority 3: Refactor parent dashboard complexity
Priority 4: Add cache invalidation hooks
Priority 5: Improve error handling specificity

### T002: Analyze dashboard frontend components and hooks
- **Agent**: react-frontend-dev
- **Parallel**: yes
- **Status**: completed ✅
**Acceptance Criteria**:
  - [x] Document current dashboard components for all roles
  - [x] Identify broken buttons or navigation issues
  - [x] List data fetching hooks and API integration
  - [x] Verify error handling and loading states
  - [x] Identify obsolete functionality
**Subtasks**:
  - [x] Read `frontend/src/pages/dashboard/StudentDashboard.tsx`
  - [x] Read `frontend/src/pages/dashboard/TeacherDashboard.tsx`
  - [x] Read `frontend/src/pages/dashboard/TutorDashboard.tsx`
  - [x] Read `frontend/src/pages/dashboard/ParentDashboard.tsx`
  - [x] Check custom hooks in `frontend/src/hooks/` (useDashboard, useStudentDashboard, etc.)
  - [x] Check API clients in `frontend/src/integrations/api/`
  - [x] Identify obsolete buttons (e.g., "My Students" button in tutor dashboard)
  - [x] Test navigation (profile edit, forum, schedule links)
**References**:
  - `frontend/src/pages/dashboard/StudentDashboard.tsx`
  - `frontend/src/pages/dashboard/TeacherDashboard.tsx`
  - `frontend/src/pages/dashboard/TutorDashboard.tsx`
  - `frontend/src/pages/dashboard/ParentDashboard.tsx`
  - `frontend/src/hooks/useStudent.ts`
  - `frontend/src/hooks/useTeacher.ts`
  - `frontend/src/hooks/useTutor.ts`
  - `frontend/src/hooks/useParent.ts`
  - `frontend/src/integrations/api/dashboard.ts`

**Findings**:

## ARCHITECTURE (CORRECT)
✅ All dashboards use TanStack Query for data fetching
✅ Proper hook-based architecture: Components → Hooks → API Clients → Backend
✅ Error boundaries and loading states implemented throughout
✅ Type-safe with TypeScript interfaces
✅ Cache management with proper invalidation on mutations

## CRITICAL ISSUES

### 1. Teacher Dashboard - Broken Detail Navigation (HIGH PRIORITY)
**Location**: `TeacherDashboard.tsx` lines 85-103
**Problem**: All detail click handlers lose entity IDs and navigate to list pages:
- Material click → `/dashboard/teacher/materials` (should be `/materials/${materialId}`)
- Student click → `/dashboard/teacher/materials` (should be student detail or modal)
- Assignment click → `/dashboard/teacher/submissions/pending` (should be `/submissions/${assignmentId}`)
- Report click → `/dashboard/teacher/reports` (should be `/reports/${reportId}`)

**Impact**: Teachers CANNOT view any detail pages - critical UX failure
**Fix**: Either create detail pages OR implement detail modals

### 2. Teacher Dashboard - Wrong "All Students" Navigation (MEDIUM PRIORITY)
**Location**: `TeacherDashboard.tsx` line 458
**Problem**: Button text says "All Students" but navigates to `/dashboard/teacher/materials`
**Impact**: Confusing UX, displays wrong page
**Fix**: Navigate to `/dashboard/teacher/students` or change button text to "Materials"

### 3. Tutor Dashboard - Redundant "My Students" Button (LOW PRIORITY)
**Location**: `TutorDashboard.tsx` lines 109-112
**Problem**: "My Students" button appears in Quick Actions section (redundant with students list above)
**Impact**: Redundant UI element, confusing navigation
**Fix**: Remove Quick Action button OR rename to "Manage Students"

### 4. Tutor Dashboard - Aggressive Cache Invalidation (PERFORMANCE)
**Location**: `useTutor.ts` lines 25-26
**Problem**: `staleTime: 0, gcTime: 0` - data NEVER cached, always fetches fresh
**Impact**: Unnecessary API calls on every render/focus, poor performance
**Fix**: Set `staleTime: 30000` (30 seconds) for better UX

### 5. Parent Dashboard - Missing enrollment_id Validation (MEDIUM PRIORITY)
**Location**: `ParentDashboard.tsx` lines 369, 333
**Problem**: Payment button disabled if `!subject.enrollment_id` but no error message shown
**Impact**: Silent failure - user sees disabled button without explanation
**Fix**: Add error badge/tooltip when enrollment_id missing

### 6. Parent Dashboard - Complex Payment Logic in Component (MAINTAINABILITY)
**Location**: `ParentDashboard.tsx` lines 282-397 (115 lines of payment UI logic)
**Problem**: Payment button rendering logic hardcoded in component (nested ternaries, complex conditions)
**Impact**: Hard to test, hard to maintain, violates separation of concerns
**Fix**: Extract to `PaymentButton` component OR `usePaymentActions()` custom hook

## NAVIGATION ISSUES

### Student Dashboard ✅
- ✅ Edit Profile → `/profile/student` (WORKING)
- ✅ All materials → `/dashboard/student/materials` (WORKING)
- ✅ All assignments → `/dashboard/student/assignments` (WORKING)
- ✅ Quick Actions all working
- ⚠️ Material click navigates to list page (no detail page - may be intentional)

### Teacher Dashboard ❌
- ✅ Edit Profile → `/profile/teacher` (WORKING)
- ❌ Material click → loses materialId (navigates to list)
- ❌ Student click → navigates to `/materials` instead of student page
- ❌ Assignment click → loses assignmentId (navigates to list)
- ❌ Report click → loses reportId (navigates to list)
- ❌ "All Students" button → navigates to `/materials` (WRONG)
- ✅ Chat → `/dashboard/teacher/general-chat` (⚠️ inconsistent with student `/dashboard/chat`)

### Tutor Dashboard ✅ (Simple)
- ✅ Edit Profile → `/profile/tutor` (WORKING)
- ✅ Students → `/dashboard/tutor/students` (WORKING)
- ✅ Reports → `/dashboard/tutor/reports` (WORKING)
- ✅ Chat → `/dashboard/tutor/chat` (WORKING)
- ⚠️ Student card click → navigates to list page (loses student context)

### Parent Dashboard ✅
- ✅ All navigation working correctly
- ✅ Child detail → `/dashboard/parent/children/${childId}` (WORKING)
- ✅ Report detail → `/dashboard/parent/reports/${reportId}` (WORKING)
- ✅ All Quick Actions working

## HOOKS ANALYSIS

### `useStudent.ts` ✅
- ✅ `useStudentDashboard()` - Proper TanStack Query setup
- ✅ staleTime: 60s, refetchOnWindowFocus: true
- ✅ Material submission mutations with query invalidation
- ✅ No issues found

### `useTeacher.ts` ✅
- ✅ `useTeacherDashboard()` - Proper TanStack Query setup
- ✅ Data transformation for form compatibility (lines 17-28)
- ✅ Pending submissions hook
- ✅ Feedback mutations with proper invalidation
- ✅ No issues found

### `useTutor.ts` ⚠️
- ❌ **staleTime: 0, gcTime: 0** - Never caches data (PERFORMANCE ISSUE)
- ⚠️ Excessive console.log statements (debugging code left in production)
- ✅ Proper mutations with cache invalidation via `cacheService.delete()`
- **Fix**: Increase staleTime to 30000ms, remove debug logging

### `useParent.ts` ✅
- ✅ `useParentDashboard()` - Proper TanStack Query setup
- ✅ staleTime: 60s, window focus refetch with 1s debounce
- ✅ Payment mutations store `pending_payment_id` in sessionStorage
- ✅ Proper cache invalidation after payments
- ⚠️ Debug logging left in production (lines 9-14, 16-17, 25)
- **Fix**: Remove console.log statements

### `useProfile.ts` ✅
- ✅ Generic profile hook used by all dashboards
- ✅ Fixed in T405 - removed hard redirects, now throws errors
- ✅ Proper error handling for 401/404
- ✅ Cache clearing on auth errors
- ✅ staleTime: 5min, refetchOnWindowFocus: false
- ✅ No issues found

## API CLIENT ANALYSIS (`dashboard.ts`) ✅

✅ All endpoints properly typed with TypeScript interfaces
✅ Safe fallbacks for optional data (empty arrays/objects)
✅ Error throwing for critical data (dashboard responses)
✅ Cache invalidation via `cacheInvalidationManager.invalidateEndpoint()`
✅ Payment endpoints properly integrated with YooKassa
✅ No issues found

## RECOMMENDATIONS FOR T018 (Frontend Fixes)

### Must Fix (Blocking):
1. Create detail pages OR modals for Teacher dashboard entities (materials, students, assignments, reports)
2. Fix "All Students" button navigation in Teacher dashboard (line 458)
3. Add enrollment_id validation with user-facing error in Parent dashboard

### Should Fix (High Priority):
4. Increase tutor students cache staleTime from 0ms to 30000ms (`useTutor.ts` line 25)
5. Extract payment button logic from ParentDashboard to `PaymentButton` component
6. Remove student card click handler in Tutor dashboard (navigates to list, loses context)

### Nice to Have:
7. Remove debug console.log statements in `useTutor.ts` and `useParent.ts`
8. Standardize chat navigation across all roles (currently inconsistent)
9. Extract status badge logic to shared utility function
10. Consider student detail modal in Tutor dashboard for better UX

### T003: Analyze forum backend system
- **Agent**: py-backend-dev
- **Parallel**: yes
- **Status**: completed ✅
**Acceptance Criteria**:
  - [x] Document forum chat creation signals
  - [x] Verify SubjectEnrollment → ChatRoom signal works
  - [x] Check forum API endpoints (list chats, send message)
  - [x] Verify Pachca notification integration
  - [x] Test permissions per role (student, teacher, tutor)
  - [x] Identify chat creation issues
**Subtasks**:
  - [x] Read `backend/chat/signals.py` (forum chat creation signal)
  - [x] Read `backend/chat/views.py` (forum API endpoints)
  - [x] Read `backend/chat/services/pachca_service.py`
  - [x] Check ChatRoom model (forum types: FORUM_SUBJECT, FORUM_TUTOR)
  - [x] Verify signal creates chats on SubjectEnrollment save
  - [x] Test API endpoints (GET /api/forum/chats/, POST send_message)
  - [x] Check permissions (ForumChatPermission)
  - [x] Test with actual SubjectEnrollment creation
**References**:
  - `backend/chat/signals.py`
  - `backend/chat/views.py`
  - `backend/chat/models.py`
  - `backend/chat/services/pachca_service.py`
  - `backend/chat/permissions.py`

**Findings**:

**Signal Handler (Chat Creation) - SOLID ✅**
- File: `backend/chat/signals.py`
- Signal: `create_forum_chat_on_enrollment` triggered by `post_save` on SubjectEnrollment
- Logic:
  1. Only runs when `created=True` (new enrollment)
  2. Creates FORUM_SUBJECT chat: student-teacher per subject
  3. Creates FORUM_TUTOR chat: student-tutor (if student has tutor assigned)
  4. Idempotent: checks if chat already exists before creating (prevents duplicates)
  5. Proper error handling: logs errors but allows enrollment to succeed
- Query optimization: Uses `select_related('tutor')` when fetching StudentProfile
- Chat naming format: "{Subject} - {Student} ↔ {Teacher/Tutor}"
- Signal registered in `chat/apps.py` ready() method ✅

**Forum API Endpoints - SOLID ✅**
- File: `backend/chat/forum_views.py` (separate from general chat views)
- Endpoints:
  - `GET /api/chat/forum/` - List user's forum chats (role-filtered)
  - `GET /api/chat/forum/{id}/messages/` - Get messages from specific forum chat
  - `POST /api/chat/forum/{id}/send_message/` - Send message to forum chat
- Query optimization:
  - List: `select_related('created_by', 'enrollment__subject', 'enrollment__teacher', 'enrollment__student')`, `prefetch_related('participants')`
  - Messages: `select_related('sender', 'reply_to__sender')`, `prefetch_related('replies', 'read_by')`
- Role-based filtering:
  - Student: sees FORUM_SUBJECT + FORUM_TUTOR chats
  - Teacher: sees FORUM_SUBJECT chats (where they're teacher)
  - Tutor: sees FORUM_TUTOR chats (where they're tutor)
  - Parent: sees nothing (empty queryset)
- Permission checks: user must be participant of chat
- Pagination: limit (default 50, max 100), offset
- Response format: `{'success': True, 'count': X, 'results': [...]}`

**Pachca Integration - SOLID ✅**
- File: `backend/chat/services/pachca_service.py`
- Signal: `send_forum_notification` triggered by `post_save` on Message
- Only runs for forum chats (FORUM_SUBJECT, FORUM_TUTOR types)
- Message format: `[Forum] {Subject}: {Sender} → {Recipient}: {MessagePreview}`
- HTTP retry logic: exponential backoff (1s, 2s, 4s) for 3 attempts
- Graceful error handling: logs errors, doesn't block message creation
- Environment configuration:
  - PACHCA_FORUM_API_TOKEN
  - PACHCA_FORUM_CHANNEL_ID
  - PACHCA_FORUM_BASE_URL (optional)
- Method `is_configured()` checks if both token and channel_id are set

**ChatRoom Model - SOLID ✅**
- File: `backend/chat/models.py`
- Forum types: FORUM_SUBJECT, FORUM_TUTOR (added to Type.choices)
- New field: `enrollment` FK to SubjectEnrollment (nullable, for forum chats only)
- Indexes: `(type, enrollment)`, `(type, is_active)` for query optimization
- Related name: `forum_chats` on SubjectEnrollment

**SubjectEnrollment Model - SOLID ✅**
- File: `backend/materials/models.py`
- Fields: student (FK User), subject (FK Subject), teacher (FK User), assigned_by (FK User), custom_subject_name
- Method: `get_subject_name()` - returns custom name if set, otherwise standard subject name
- Reverse relation: `forum_chats` from ChatRoom

**NO BLOCKING ISSUES FOUND ❌**

**Overall Assessment**:
Forum backend is fully functional and production-ready:
- Signal creates chats automatically on enrollment (idempotent)
- API endpoints optimized with select_related/prefetch_related
- Role-based permissions correctly enforced
- Pachca notifications working with retry logic
- Proper error handling throughout
- All code follows service layer pattern and DRY principles

**Potential Improvements (non-blocking)**:
1. Add test coverage for signal handler (verify idempotency, error handling)
2. Add test coverage for Pachca notification (mock httpx.post)
3. Consider caching forum chat list per user (cache_key: f"forum_chats_{user.id}")
4. Add unread message count to chat list response (already in ChatRoomListSerializer)
5. WebSocket real-time updates (existing ChatConsumer should handle this)

### T004: Analyze forum frontend implementation
- **Agent**: react-frontend-dev
- **Parallel**: yes
- **Status**: completed ✅
**Acceptance Criteria**:
  - [x] Document forum page components
  - [x] Verify chat list rendering
  - [x] Check message sending/receiving logic
  - [x] Verify WebSocket integration
  - [x] Test forum navigation for all roles
  - [x] Identify loading/error state issues
**Subtasks**:
  - [x] Read `frontend/src/pages/dashboard/Forum.tsx`
  - [x] Check forum hooks (useForumChats, useForumMessages)
  - [x] Check `frontend/src/integrations/api/forumAPI.ts`
  - [x] Verify WebSocket connection in forum context
  - [x] Identify broken chat list or messaging issues
  - [x] Check chat filtering and search
  - [x] Verify unread message badges
**References**:
  - `frontend/src/pages/dashboard/Forum.tsx`
  - `frontend/src/hooks/useForumChats.ts`
  - `frontend/src/hooks/useForumMessages.ts`
  - `frontend/src/integrations/api/forumAPI.ts`
  - `frontend/src/services/chatWebSocketService.ts` (not used yet)

**Findings**:

**Component Architecture - GOOD ✅**
- Forum page: `frontend/src/pages/dashboard/Forum.tsx`
- Components defined inline: ChatList, ChatWindow, ChatListItem
- Proper TypeScript interfaces for all props
- Clean two-panel layout: chat list (left) + message window (right)
- Responsive grid system (md:grid-cols-3)

**Routing - GOOD ✅**
- Routes configured for all 4 roles in App.tsx:
  - `/dashboard/student/forum`
  - `/dashboard/teacher/forum`
  - `/dashboard/tutor/forum`
  - `/dashboard/parent/forum`
- Lazy-loaded for performance
- All wrapped in ProtectedRoute

**API Integration - GOOD ✅**
- File: `frontend/src/integrations/api/forumAPI.ts`
- Endpoints implemented:
  - `getForumChats()` → GET `/forum/chats/`
  - `getForumMessages(chatId, limit, offset)` → GET `/forum/chats/{id}/messages/`
  - `sendForumMessage(chatId, data)` → POST `/forum/chats/{id}/send_message/`
- Uses `unifiedAPI.request()` with error handling
- Proper TypeScript interfaces: ForumChat, ForumMessage, ForumUser, ForumSubject
- Pagination support (limit/offset parameters)
- **MISMATCH**: API calls `/forum/chats/` but backend might be at `/api/chat/forum/` (needs verification with T003)

**Custom Hooks - GOOD ✅**
- `useForumChats()`: Fetches chat list, 5min stale time, 2 retries
- `useForumChatsWithRefresh()`: Wrapper with manual refresh via invalidateQueries
- `useForumMessages(chatId, limit, offset)`: Fetches messages, 30s stale time, enabled only when chatId present
- `useSendForumMessage()`: Mutation hook, invalidates queries on success, toast notifications
- `usePaginatedForumMessages()`: **BROKEN** - state setters are placeholders `() => {}`

**WebSocket Integration - MISSING ❌ (CRITICAL)**
- **NO WebSocket integration in Forum.tsx**
- No imports of chatWebSocketService or websocketService
- Messages rely ONLY on TanStack Query polling (30s stale time)
- No real-time updates when other user sends message
- No typing indicators
- No online status
- WebSocket services exist but unused:
  - `chatWebSocketService.ts` - has connectToRoom(), sendRoomMessage() methods
  - `websocketService.ts` - base WebSocket implementation
- **Impact**: Users must refresh or wait 30s to see new messages

**Loading/Error States - GOOD ✅**
- Loading skeletons for chat list and messages
- Empty states with icons and helpful text
- Error handling via TanStack Query + sonner toasts
- Disabled send button during submission
- Loading spinner on send button

**UI/UX Features - GOOD ✅**
- Search/filter chats by name, subject, participant name
- Unread count badges on chats (from backend data)
- Avatar initials for participants
- Message timestamps (HH:MM format)
- Own messages right-aligned, others left-aligned
- Subject name displayed if available
- Empty states when no chats/messages
- Enter key to send message
- Prevents double-send (disabled during submission)

**Identified Issues**:

**CRITICAL**:
1. **No WebSocket integration** - Real-time updates completely missing
   - Forum relies on query polling (30s)
   - Recipients don't see new messages in real-time
   - No typing indicators, no online status
   - Solution: Integrate chatWebSocketService.connectToRoom()

**HIGH**:
2. **API endpoint mismatch** - Frontend calls `/forum/chats/`, backend may be at `/api/chat/forum/`
   - Needs verification with T003 backend analysis
   - May cause 404 errors if backend path differs

**MODERATE**:
3. **Pagination broken** - usePaginatedForumMessages has placeholder setters
   - Lines 36-37 in useForumMessages.ts: `const [limit, setLimit] = [50, () => {}];`
   - loadMore() and loadBefore() won't work
   - Users can't load older messages beyond initial 50

**MINOR**:
4. **User ID from localStorage** - Hardcoded in 6 places (lines 33, 39, 180, 192, 206, 228)
   - Should use AuthContext for current user
   - Fragile if localStorage key changes
   - Not reactive to user change

5. **No message read tracking** - Messages fetched but not marked as read
   - Backend has is_read field and unread_count
   - Frontend displays unread_count but doesn't mark messages read when viewing
   - Should call mark-as-read API when viewing chat

6. **No connection status indicator** - Users don't know if offline/online
   - Important for debugging WebSocket issues

**Missing Features (vs FORUM_SYSTEM.md spec)**:
1. Real-time WebSocket updates (CRITICAL)
2. Message read status tracking
3. Pagination for older messages (implemented but broken)
4. Typing indicators
5. Online status for participants
6. File/image attachments (if backend supports)

**Recommendations for T019 (Frontend Fix)**:
1. **PRIORITY 1**: Integrate WebSocket
   - Import chatWebSocketService
   - On chat selection: connectToRoom(selectedChat.id, handlers)
   - Add onMessage handler to append new messages to TanStack Query cache
   - Add typing indicators via onTyping/onTypingStop handlers
   - Disconnect on unmount or chat change
2. **PRIORITY 2**: Verify API endpoint paths match backend (coordinate with T013)
3. **PRIORITY 3**: Fix pagination - replace placeholder setters with useState
4. **PRIORITY 4**: Replace localStorage user ID with useAuth() hook
5. **PRIORITY 5**: Implement message read tracking (mark as read when viewing chat)

### T005: Analyze scheduling backend implementation
- **Agent**: py-backend-dev
- **Parallel**: yes
- **Status**: completed ✅
**Acceptance Criteria**:
  - [x] Document lesson CRUD API endpoints
  - [x] Verify validation logic (time, teacher-student relationship)
  - [x] Check permissions (teacher create, student view)
  - [x] Verify tutor view of student schedule
  - [x] Identify lesson creation issues
**Subtasks**:
  - [x] Read `backend/scheduling/` app (views, models, serializers)
  - [x] Check Lesson model and validation
  - [x] Verify lesson creation API (POST /api/scheduling/lessons/)
  - [x] Verify lesson update/delete API
  - [x] Verify student schedule API (GET /api/scheduling/lessons/)
  - [x] Verify tutor student schedule API (GET /api/scheduling/lessons/student_schedule/)
  - [x] Check permissions (IsTeacher, IsStudent, IsTutor)
  - [x] Verify SubjectEnrollment validation
**References**:
  - `backend/scheduling/views.py`
  - `backend/scheduling/models.py`
  - `backend/scheduling/serializers.py`
  - `backend/scheduling/permissions.py`

**Findings**:

**Architecture - SOLID**:
- Service layer pattern: LessonService in services/lesson_service.py (business logic)
- ViewSet pattern: LessonViewSet in views.py (API endpoints)
- Models: Lesson (main), LessonHistory (audit trail)
- URL routing: /api/scheduling/lessons/ via DefaultRouter

**API Endpoints (9 total)**:
1. POST /lessons/ - Create (teacher only)
2. GET /lessons/ - List (role-filtered)
3. GET /lessons/{id}/ - Detail
4. PATCH /lessons/{id}/ - Update (teacher only, before start)
5. DELETE /lessons/{id}/ - Cancel (teacher only, 2-hour rule)
6. GET /lessons/my-schedule/ - Current user's schedule
7. GET /lessons/student-schedule/?student_id=X - Tutor view
8. GET /lessons/upcoming/ - Next 10 upcoming
9. GET /lessons/{id}/history/ - Change history

**Validation Logic**:
- Time: start_time < end_time (serializer + service + model)
- Date: date >= today (serializer + service + model)
- SubjectEnrollment: teacher teaches subject to student (service + model)
- Role: only teachers create, only creator can edit/delete
- Cancellation: can_cancel checks 2-hour rule
- Past protection: cannot edit started lessons

**CRITICAL ISSUE - BREAKING EDIT/DELETE**:

**ISSUE 1: PATCH method not handled**
- Location: views.py line 134 (update method)
- Problem: ViewSet.update() handles PUT, not PATCH
- DRF behavior: PATCH → partial_update(), PUT → update()
- Current: custom update() overrides PUT only
- Impact: PATCH requests bypass custom validation, use default ModelViewSet.partial_update()
- Frontend: likely sends PATCH for partial updates
- **This is PRIMARY reason editing doesn't work**
- Fix: Rename update() to partial_update() OR override both

**ISSUE 2: 204 response with body**
- Location: views.py line 207-220 (destroy)
- Problem: Returns 204 with JSON body
- HTTP spec: 204 must have empty body
- Impact: May confuse HTTP clients
- Fix: Return 200 with message OR 204 without body

**ISSUE 3: Field type inconsistency**
- Location: serializers.py line 81 (LessonCreateSerializer)
- Problem: student/subject are CharField (expect UUIDs)
- Reality: User model uses integer PKs
- Workaround: View converts string to int
- Impact: May fail if frontend sends int
- Fix: Use IntegerField or PrimaryKeyRelatedField

**ISSUE 4: Missing role permissions at DRF level**
- Location: views.py line 36 (permission_classes)
- Problem: Only IsAuthenticated enforced
- Current: Role check in view methods (manual)
- Best practice: Use get_permissions() for action-based permissions
- Impact: Minor - works but not DRF pattern
- Fix: Add get_permissions() returning IsTeacher for create/update/destroy

**ISSUE 5: Duplicate validation**
- Locations: serializers.py, lesson_service.py, models.py
- Problem: Same validation in 3 layers
- Impact: Performance overhead, code duplication
- Fix: Keep in serializer + model, remove from service

**Query Optimization - EXCELLENT**:
- All querysets: select_related('teacher', 'student', 'subject')
- No N+1 queries detected
- Indexes on Lesson model (teacher+date, student+date, subject+date, status)

**Service Layer - EXCELLENT**:
- LessonService separates business logic
- Views are thin wrappers
- Transactions: @transaction.atomic on update/delete
- LessonHistory audit trail implemented

**Recommendations for T014**:

**Priority 1 (MUST FIX)**:
1. Rename update() → partial_update() to handle PATCH
2. Test PATCH /lessons/{id}/ with minimal payload

**Priority 2 (SHOULD FIX)**:
1. Fix destroy() response: 200 with body OR 204 without
2. Change student/subject to IntegerField in serializers
3. Add get_permissions() for action-based role enforcement

**Priority 3 (NICE TO HAVE)**:
1. Create IsLessonTeacher permission class (object-level)
2. Remove duplicate validation from service
3. Add pagination to lesson lists

### T006: Analyze scheduling frontend implementation
- **Agent**: react-frontend-dev
- **Parallel**: yes
- **Status**: completed ✅
**Acceptance Criteria**:
  - [x] Document teacher schedule page
  - [x] Verify student schedule page
  - [x] Check tutor student schedule component
  - [x] Verify lesson creation form
  - [x] Test edit/delete functionality
  - [x] Identify form validation issues
**Subtasks**:
  - [x] Read `frontend/src/pages/dashboard/TeacherSchedulePage.tsx`
  - [x] Read `frontend/src/pages/dashboard/StudentSchedulePage.tsx`
  - [x] Check tutor student schedule component (if exists in TutorDashboard)
  - [x] Check scheduling hooks (useTeacherLessons, useStudentSchedule)
  - [x] Check `frontend/src/integrations/api/schedulingAPI.ts`
  - [x] Identify broken lesson creation or schedule view issues
  - [x] Check date/time pickers and validation
**References**:
  - `frontend/src/pages/dashboard/TeacherSchedulePage.tsx`
  - `frontend/src/pages/dashboard/StudentSchedulePage.tsx`
  - `frontend/src/hooks/` (scheduling hooks)
  - `frontend/src/integrations/api/schedulingAPI.ts`
  - `frontend/src/components/` (BookingWidget, TeacherScheduleWidget)

**Findings**: See `docs/T006_FINDINGS.md` for complete analysis

**🔴 CRITICAL BLOCKER**: Student schedule not loading - API endpoint mismatch
- Frontend calls: GET `/scheduling/lessons/my-schedule/` (likely doesn't exist)
- Teacher calls: GET `/scheduling/lessons/` (works)
- **Impact**: Students cannot see any lessons
- **Fix**: Coordinate with T005 - either backend adds `my_schedule` action OR frontend uses standard endpoint
- **Missing**: Error display on StudentSchedulePage (shows empty state instead of error)

**🟡 Other Issues**:
- Edit lesson dialog not implemented (UI exists but not wired)
- Form validation gaps (time comparison, same-day past time)
- No delete confirmation dialog
- Loading state inconsistency (minor)

**Overall Quality**: ✅ Excellent frontend code (TypeScript, React patterns, UX). Main issue is backend API integration.

### T007: Analyze admin panel backend
- **Agent**: py-backend-dev
- **Parallel**: yes
- **Status**: completed ✅
**Acceptance Criteria**:
  - [x] Document user creation endpoints (student, parent, teacher, tutor)
  - [x] Verify parent assignment logic
  - [x] Check user update/delete endpoints
  - [x] Verify password reset functionality
  - [x] Check permissions (admin/staff only)
  - [x] Identify user creation issues
**Subtasks**:
  - [x] Read `backend/accounts/admin_views.py` or `backend/accounts/views.py`
  - [x] Check user creation serializers
  - [x] Verify POST /api/auth/students/create/
  - [x] Verify POST /api/auth/parents/create/
  - [x] Verify POST /api/auth/assign-parent/
  - [x] Verify PATCH /api/auth/users/{id}/
  - [x] Verify DELETE /api/auth/users/{id}/delete/
  - [x] Verify POST /api/auth/users/{id}/reset-password/
  - [x] Check permissions (IsAdminUser, IsStaff)
**References**:
  - `backend/accounts/admin_views.py`
  - `backend/accounts/views.py`
  - `backend/accounts/serializers.py`
  - `backend/accounts/permissions.py`

### T008: Analyze admin panel frontend
- **Agent**: react-frontend-dev
- **Parallel**: yes
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Document admin dashboard components
  - [ ] Verify user creation forms
  - [ ] Check parent assignment interface
  - [ ] Verify user edit/delete modals
  - [ ] Test navigation and tabs
  - [ ] Identify form submission issues
**Subtasks**:
  - [ ] Read `frontend/src/pages/admin/` (AdminDashboard, student/parent/staff tabs)
  - [ ] Check admin hooks (useAdminStudents, useAdminParents, etc.)
  - [ ] Check `frontend/src/integrations/api/adminAPI.ts`
  - [ ] Identify broken user creation forms
  - [ ] Identify broken parent assignment functionality
  - [ ] Identify broken user edit/delete flows
  - [ ] Check form validation
**References**:
  - `frontend/src/pages/admin/AdminDashboard.tsx`
  - `frontend/src/pages/admin/` (other admin pages if exist)
  - `frontend/src/hooks/` (admin hooks)
  - `frontend/src/integrations/api/adminAPI.ts`

### T009: Analyze environment configuration and URL leaking
- **Agent**: devops-engineer
- **Parallel**: yes (with Wave 2)
- **Status**: pending ⏸️
- **Blocked by**: Wave 1 completion
**Acceptance Criteria**:
  - [ ] Document current EnvConfig service
  - [ ] Identify production URLs appearing in dev mode
  - [ ] Verify .env vs .env.example vs .env.production
  - [ ] Check frontend VITE env variables
  - [ ] Verify backend URL generation
  - [ ] Reproduce URL leaking issue
**Subtasks**:
  - [ ] Read `backend/core/services/env_config.py`
  - [ ] Check `.env`, `.env.example`, `.env.production`
  - [ ] Check `frontend/.env` and Vite config
  - [ ] Test in dev mode: verify localhost URLs (ENVIRONMENT=development)
  - [ ] Test media file URLs (should be localhost in dev)
  - [ ] Reproduce URL leaking issue (set dev mode, check URLs in browser network tab)
  - [ ] Check VITE_DJANGO_API_URL and VITE_WEBSOCKET_URL
**References**:
  - `backend/core/services/env_config.py`
  - `.env`
  - `.env.example`
  - `.env.production`
  - `frontend/.env`
  - `frontend/vite.config.ts`

### T010: Analyze profile models and data persistence
- **Agent**: db-schema-specialist
- **Parallel**: yes (with Wave 2)
- **Status**: pending ⏸️
- **Blocked by**: Wave 1 completion
**Acceptance Criteria**:
  - [ ] Document User and Profile models for all roles
  - [ ] Verify profile creation signals
  - [ ] Check profile update serializers
  - [ ] Identify why data not persisting
  - [ ] Verify migrations applied
  - [ ] Test profile save in database
**Subtasks**:
  - [ ] Read `backend/accounts/models.py` (User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile)
  - [ ] Check `backend/accounts/signals.py` (profile creation signal)
  - [ ] Read `backend/accounts/profile_views.py` and serializers
  - [ ] Test profile update API manually (PATCH /api/profile/student/, etc.)
  - [ ] Check database for profile records (use Django shell or DB client)
  - [ ] Verify migrations with `python manage.py showmigrations accounts`
  - [ ] Check if profile save() method works
**References**:
  - `backend/accounts/models.py`
  - `backend/accounts/signals.py`
  - `backend/accounts/profile_views.py`
  - `backend/accounts/serializers.py`

### T011: Analyze test data generation script
- **Agent**: py-backend-dev
- **Parallel**: yes (with Wave 2)
- **Status**: pending ⏸️
- **Blocked by**: Wave 1 completion
**Acceptance Criteria**:
  - [ ] Document current test data script
  - [ ] Identify what invalid data is created
  - [ ] Design valid test dataset architecture
  - [ ] Plan relationships (student-teacher-tutor-parent, subjects, enrollments)
  - [ ] Plan expected data structure
**Subtasks**:
  - [ ] Find test data generation script (backend/management/commands/ or scripts/)
  - [ ] Read script and understand current logic
  - [ ] Test script execution and check generated data
  - [ ] Design valid dataset: users (5 students, 3 teachers, 2 tutors, 2 parents), profiles, subjects (Math, English, Science), enrollments, lessons, forum chats
  - [ ] Document expected data structure
  - [ ] Plan idempotency (script can run multiple times)
**References**:
  - Test data generation script (locate first)
  - `backend/accounts/models.py`
  - `backend/materials/models.py`
  - `backend/scheduling/models.py`
  - `backend/chat/models.py`

### T012: Fix dashboard backend APIs and service methods
- **Agent**: py-backend-dev
- **Blocked by**: [T001]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] All dashboard API endpoints return correct data
  - [ ] Service methods optimized (no N+1 queries)
  - [ ] Permissions correctly enforced
  - [ ] Error handling consistent
  - [ ] Deprecated code removed
**Implementation Steps**:
1. Apply T001 recommendations based on findings
2. Fix N+1 queries (add select_related/prefetch_related)
3. Refactor complex methods (e.g., ParentDashboardService.get_dashboard_data())
4. Standardize caching across all 4 role services
5. Remove deprecated code (e.g., _create_general_chat if obsolete)
6. Test each dashboard endpoint manually
7. Verify query optimization with django-debug-toolbar or logging
8. Add proper error handling
**Test Scenarios**:
  - Student: GET /api/dashboard/student/ → 200 with progress, tasks, materials
  - Teacher: GET /api/dashboard/teacher/ → 200 with students, subjects, schedule (no N+1)
  - Tutor: GET /api/dashboard/tutor/ → 200 with assigned students (valid data)
  - Parent: GET /api/dashboard/parent/ → 200 with child progress
  - Unauthorized: all endpoints → 403
  - Invalid role: endpoint → 403
**References**:
  - `backend/materials/student_dashboard_service.py` (MODIFY)
  - `backend/materials/teacher_dashboard_service.py` (MODIFY)
  - `backend/materials/tutor_dashboard_service.py` (MODIFY)
  - `backend/materials/parent_dashboard_service.py` (MODIFY)
  - `backend/materials/*_dashboard_views.py` (MODIFY)

### T013: Fix forum backend system
- **Agent**: py-backend-dev
- **Blocked by**: [T003]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Forum chats auto-created on SubjectEnrollment
  - [ ] Chat list API returns correct chats per role
  - [ ] Message sending API works
  - [ ] Pachca notifications sent (if configured)
  - [ ] Permissions correctly enforced
**Implementation Steps**:
1. Fix `create_forum_chat_on_enrollment` signal based on T003 findings
2. Fix forum chat list API (GET /api/forum/chats/)
3. Fix message sending API (POST /api/forum/chats/{id}/send_message/)
4. Fix Pachca notification trigger
5. Verify permissions (ForumChatPermission checks role and chat membership)
6. Test signal: create SubjectEnrollment → verify chats created
7. Test API endpoints
8. Add proper error handling
**Test Scenarios**:
  - Create SubjectEnrollment → FORUM_SUBJECT and FORUM_TUTOR chats created (2 chats)
  - Student GET /api/forum/chats/ → returns student-teacher and student-tutor chats
  - Teacher GET /api/forum/chats/ → returns chats for students they teach
  - Tutor GET /api/forum/chats/ → returns chats for assigned students
  - POST send_message → message saved, Pachca notification sent
  - Invalid permissions → 403
  - Re-save enrollment → no duplicate chats (idempotency)
**References**:
  - `backend/chat/signals.py` (MODIFY)
  - `backend/chat/views.py` (MODIFY)
  - `backend/chat/services/pachca_service.py` (MODIFY)
  - `backend/chat/permissions.py` (check)

### T014: Fix scheduling backend
- **Agent**: py-backend-dev
- **Blocked by**: [T005]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Teacher can create lessons
  - [ ] Teacher can edit/delete lessons
  - [ ] Student sees assigned lessons
  - [ ] Tutor sees student lessons
  - [ ] Validation works (time, permissions, SubjectEnrollment)
**Implementation Steps**:
1. Fix lesson creation validation based on T005 findings
2. Fix lesson update/delete permissions
3. Fix student schedule API
4. Fix tutor student schedule API
5. Add proper error messages
6. Test all CRUD operations
7. Verify SubjectEnrollment validation
8. Add proper error handling
**Test Scenarios**:
  - Teacher POST /api/scheduling/lessons/ → 201 with lesson created
  - Teacher PATCH /api/scheduling/lessons/{id}/ → 200 with updated lesson
  - Teacher DELETE /api/scheduling/lessons/{id}/ → 204 or 403 (2-hour rule)
  - Student GET /api/scheduling/lessons/ → 200 with student's lessons
  - Tutor GET /api/scheduling/lessons/student_schedule/?student_id=X → 200
  - Invalid data (start_time > end_time) → 400 with error message
  - Teacher not assigned to student → 400 with error message
**References**:
  - `backend/scheduling/views.py` (MODIFY)
  - `backend/scheduling/models.py` (check validation)
  - `backend/scheduling/serializers.py` (MODIFY)

### T015: Fix admin panel backend
- **Agent**: py-backend-dev
- **Blocked by**: [T007]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Student creation works with auto-generated credentials
  - [ ] Parent creation works
  - [ ] Parent assignment to multiple students works
  - [ ] User update works
  - [ ] User delete works
  - [ ] Password reset works
**Implementation Steps**:
1. Fix student creation endpoint based on T007 findings
2. Fix parent creation endpoint
3. Fix parent assignment endpoint (support multiple students)
4. Fix user update endpoint
5. Fix user delete endpoint (soft/hard delete)
6. Fix password reset endpoint
7. Test all admin operations
8. Add proper error handling
**Test Scenarios**:
  - POST /api/auth/students/create/ → 201 with student + credentials
  - POST /api/auth/parents/create/ → 201 with parent + credentials
  - POST /api/auth/assign-parent/ (multiple student_ids) → 200
  - PATCH /api/auth/users/{id}/ → 200 with updated user
  - DELETE /api/auth/users/{id}/delete/ → 204
  - POST /api/auth/users/{id}/reset-password/ → 200 with new password
  - Non-admin user → 403
**References**:
  - `backend/accounts/admin_views.py` (MODIFY)
  - `backend/accounts/views.py` (MODIFY)
  - `backend/accounts/serializers.py` (MODIFY)

### T016: Fix profile data persistence
- **Agent**: db-schema-specialist
- **Blocked by**: [T010]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Profile update API saves data to database
  - [ ] Avatar upload works
  - [ ] Role-specific fields saved correctly
  - [ ] Subsequent GET returns saved data
**Implementation Steps**:
1. Fix profile serializer save() method based on T010 findings
2. Fix profile view PATCH handler
3. Verify signal creates profiles on user creation
4. Add transaction handling if needed (atomic)
5. Test profile update for all roles
6. Verify data in database (Django shell or DB client)
7. Add proper error handling
**Test Scenarios**:
  - Student PATCH /api/profile/student/ → 200, data saved
  - GET /api/profile/student/ → returns saved data
  - Teacher PATCH /api/profile/teacher/ (with avatar) → 200, avatar saved
  - Tutor PATCH /api/profile/tutor/ (with bio) → 200, bio saved
  - Invalid field → 400 with error
**References**:
  - `backend/accounts/profile_views.py` (MODIFY)
  - `backend/accounts/serializers.py` (MODIFY)
  - `backend/accounts/signals.py` (check profile creation)
  - `backend/accounts/models.py` (check profile models)

### T017: Fix environment URL isolation
- **Agent**: devops-engineer
- **Blocked by**: [T009]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Development mode uses only localhost URLs
  - [ ] Production mode uses only production URLs
  - [ ] No URL leaking between modes
  - [ ] Media file URLs respect environment
  - [ ] Frontend API URLs respect environment
**Implementation Steps**:
1. Fix EnvConfig service based on T009 findings
2. Update .env.example with clear instructions
3. Fix any hardcoded URLs in backend
4. Fix any hardcoded URLs in frontend
5. Test in development mode (ENVIRONMENT=development)
6. Test in production mode (ENVIRONMENT=production)
7. Verify media file URLs
8. Add proper error handling
**Test Scenarios**:
  - Dev mode: all URLs use localhost:8000 and localhost:8080
  - Prod mode: all URLs use the-bot.ru
  - Open file in study plan (dev) → downloads from localhost
  - Switch ENVIRONMENT → URLs change accordingly
  - WebSocket URL correct per environment
**References**:
  - `backend/core/services/env_config.py` (MODIFY)
  - `.env.example` (MODIFY)
  - `frontend/.env` (MODIFY)
  - Frontend API client config (MODIFY)

### T018: Fix dashboard frontend for all roles
- **Agent**: react-frontend-dev
- **Blocked by**: [T002, T012]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] All dashboard buttons work
  - [ ] Navigation correct (profile, forum, schedule)
  - [ ] Data displays properly
  - [ ] Loading/error states handled
  - [ ] Tutor "My Students" section shows correct data
  - [ ] Obsolete buttons removed
**Implementation Steps**:
1. Fix StudentDashboard based on T002 findings and backend T012
2. Fix TeacherDashboard based on T002 findings and backend T012
3. Fix TutorDashboard based on T002 findings and backend T012
4. Fix ParentDashboard based on T002 findings and backend T012
5. Update hooks to use fixed APIs
6. Fix button click handlers
7. Remove obsolete buttons
8. Test in browser for all roles
**Test Scenarios**:
  - Student dashboard: displays progress, tasks, materials, buttons work
  - Teacher dashboard: displays students, subjects, schedule, buttons work
  - Tutor dashboard: "My Students" shows assigned students (no obsolete button)
  - Parent dashboard: shows child progress
  - Loading/error states display correctly
  - Navigation buttons work (profile, forum, schedule)
**References**:
  - `frontend/src/pages/dashboard/StudentDashboard.tsx` (MODIFY)
  - `frontend/src/pages/dashboard/TeacherDashboard.tsx` (MODIFY)
  - `frontend/src/pages/dashboard/TutorDashboard.tsx` (MODIFY)
  - `frontend/src/pages/dashboard/ParentDashboard.tsx` (MODIFY)
  - `frontend/src/hooks/` (MODIFY)

### T019: Fix forum frontend
- **Agent**: react-frontend-dev
- **Blocked by**: [T004, T013]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Forum page loads for all roles
  - [ ] Chat list displays correctly
  - [ ] Messages send and receive
  - [ ] WebSocket real-time updates work
  - [ ] Navigation works
**Implementation Steps**:
1. Fix Forum.tsx based on T004 findings and backend T013
2. Fix useForumChats hook
3. Fix useForumMessages hook
4. Fix WebSocket integration
5. Test chat list rendering
6. Test message sending
7. Test real-time message receiving
8. Add proper error handling
**Test Scenarios**:
  - Student forum: shows teacher and tutor chats
  - Teacher forum: shows student chats
  - Click chat → messages load
  - Send message → appears in chat
  - Other user sends message → real-time update
  - Loading/error states handled
**References**:
  - `frontend/src/pages/dashboard/Forum.tsx` (MODIFY)
  - `frontend/src/hooks/` (MODIFY)
  - `frontend/src/integrations/api/forumAPI.ts` (MODIFY)

### T020: Fix scheduling frontend
- **Agent**: react-frontend-dev
- **Blocked by**: [T006, T014]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Teacher can create lessons
  - [ ] Teacher can edit/delete lessons
  - [ ] Student sees lesson schedule
  - [ ] All fields validate
  - [ ] Forms submit correctly
**Implementation Steps**:
1. Fix TeacherSchedulePage based on T006 findings and backend T014
2. Fix StudentSchedulePage based on T006 findings and backend T014
3. Fix lesson creation form
4. Fix lesson edit/delete functionality
5. Update scheduling hooks
6. Test in browser
7. Add proper error handling
**Test Scenarios**:
  - Teacher: create lesson → submit → appears in list
  - Teacher: edit lesson → submit → updated
  - Student: schedule page → shows lessons
  - Invalid form data → validation errors
  - Loading/error states handled
**References**:
  - `frontend/src/pages/dashboard/TeacherSchedulePage.tsx` (MODIFY)
  - `frontend/src/pages/dashboard/StudentSchedulePage.tsx` (MODIFY)
  - `frontend/src/hooks/` (MODIFY)
  - `frontend/src/integrations/api/schedulingAPI.ts` (MODIFY)

### T021: Fix admin panel frontend
- **Agent**: react-frontend-dev
- **Blocked by**: [T008, T015]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Student creation form works
  - [ ] Parent creation form works
  - [ ] Parent assignment works (multiple students)
  - [ ] User edit works
  - [ ] User delete works
  - [ ] Forms validate correctly
**Implementation Steps**:
1. Fix admin dashboard components based on T008 findings and backend T015
2. Fix student creation form
3. Fix parent creation form
4. Fix parent assignment interface
5. Fix user edit modal
6. Fix user delete confirmation
7. Update admin hooks
8. Test in browser
9. Add proper error handling
**Test Scenarios**:
  - Create student → form submits → appears in list
  - Create parent → form submits → appears in list
  - Assign parent to students → submit → saved
  - Edit user → submit → updated
  - Delete user → confirm → removed
  - Invalid form → validation errors
**References**:
  - `frontend/src/pages/admin/AdminDashboard.tsx` (MODIFY)
  - `frontend/src/pages/admin/` (MODIFY)
  - `frontend/src/hooks/` (MODIFY)
  - `frontend/src/integrations/api/adminAPI.ts` (MODIFY)

### T022: Implement valid test data generation script
- **Agent**: py-backend-dev
- **Blocked by**: [T011, T016, T017]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Script creates valid users for all roles
  - [ ] Profiles populated with realistic data
  - [ ] Subjects and enrollments created
  - [ ] Forum chats auto-created via signals
  - [ ] Lessons created for students
  - [ ] Script idempotent (can run multiple times)
**Implementation Steps**:
1. Create Django management command: `backend/management/commands/generate_test_data.py`
2. Based on T011 design, create:
   - Users: 5 students, 3 teachers, 2 tutors, 2 parents
   - Profiles with valid data (names, emails, phone numbers, etc.)
   - Subjects: Math, English, Science
   - Assign teachers to subjects (TeacherSubject)
   - Enroll students in subjects (SubjectEnrollment) → triggers forum chat creation
   - Assign tutors to students (StudentProfile.tutor)
   - Assign parents to students (StudentProfile.parent)
   - Create lessons for students
3. Add cleanup command (delete all test data)
4. Make script idempotent (check if data exists before creating)
5. Test script execution
**Test Scenarios**:
  - Run script → users created with profiles
  - Check database: profiles have data
  - Check forum chats created automatically (via signal)
  - Check lessons exist
  - Run script again → idempotent (no duplicates)
  - Run cleanup → all test data deleted
**References**:
  - `backend/management/commands/generate_test_data.py` (CREATE)
  - `backend/accounts/models.py`
  - `backend/materials/models.py`
  - `backend/scheduling/models.py`
  - `backend/chat/models.py`

### T023: Create comprehensive backend test suite
- **Agent**: qa-code-tester
- **Blocked by**: [T012, T013, T014, T015, T016, T017, T022]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Unit tests for all fixed services
  - [ ] Integration tests for all fixed APIs
  - [ ] Test coverage > 80%
  - [ ] All tests pass
  - [ ] No N+1 query warnings
**Implementation Steps**:
1. Create test structure in `backend/tests/` (unit/, integration/)
2. Write unit tests for dashboard services
3. Write unit tests for forum signals and services
4. Write unit tests for scheduling logic
5. Write unit tests for admin user creation
6. Write integration tests for all API endpoints
7. Use fixtures from conftest.py
8. Mock external services (Pachca, YooKassa, Supabase)
9. Run tests with coverage: `pytest backend/tests/ --cov=backend --cov-report=html`
10. Fix any failures
**Test Scenarios**:
  - Dashboard services: return correct data, optimized queries
  - Forum: signal creates chats, API correct, permissions enforced
  - Scheduling: validation works, CRUD correct
  - Admin: user creation, parent assignment, password reset
  - Profiles: data persists, avatar upload
  - Environment: URLs correct per mode
**References**:
  - `backend/tests/unit/` (CREATE)
  - `backend/tests/integration/` (CREATE)
  - `backend/tests/conftest.py` (MODIFY)

### T024: Run backend integration tests
- **Agent**: qa-code-tester
- **Blocked by**: [T023]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] All backend tests pass
  - [ ] Coverage report generated (>80%)
  - [ ] No regressions found
  - [ ] No N+1 query warnings
**Implementation Steps**:
1. Run full test suite: `pytest backend/tests/ -v`
2. Generate coverage report: `pytest backend/tests/ --cov=backend --cov-report=html`
3. Review failures (if any)
4. Create fix tasks for failures
5. Repeat until all pass
6. Review coverage report (htmlcov/index.html)
**Test Scenarios**:
  - All dashboard tests pass
  - All forum tests pass
  - All scheduling tests pass
  - All admin tests pass
  - All profile tests pass
  - Coverage > 80%
  - No N+1 query warnings in logs
**References**:
  - `backend/tests/`

### T025: Run E2E browser tests for all user flows
- **Agent**: qa-user-tester
- **Blocked by**: [T024]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Dashboard flows work for all roles
  - [ ] Forum messaging works
  - [ ] Scheduling works (teacher/student)
  - [ ] Admin panel works
  - [ ] Profile editing works
  - [ ] All E2E tests pass
**Implementation Steps**:
1. Run existing E2E tests: `npx playwright test` (from frontend/)
2. Create new E2E tests for fixed features (if needed)
3. Test student dashboard flow (login → dashboard → forum → send message)
4. Test teacher dashboard flow (login → dashboard → create lesson → view students)
5. Test tutor dashboard flow (login → dashboard → see students → view schedule)
6. Test parent dashboard flow (login → dashboard → view child progress)
7. Test forum messaging flow (student → teacher chat)
8. Test scheduling flow (teacher create lesson → student view)
9. Test admin panel flow (create student → assign parent → reset password)
10. Review failures and create fix tasks
**Test Scenarios**:
  - Student: login → dashboard → forum → send message
  - Teacher: login → dashboard → create lesson → view students
  - Tutor: login → dashboard → see students → view schedule
  - Parent: login → dashboard → view child progress
  - Admin: create student → assign parent → reset password
  - All navigation works, no console errors
  - WebSocket real-time updates work
**References**:
  - Playwright MCP
  - `frontend/tests/e2e/` (if exists)

### T026: Consolidate tests and remove obsolete files
- **Agent**: devops-engineer
- **Blocked by**: [T024, T025]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] All tests moved to designated directories
  - [ ] Obsolete test files removed
  - [ ] Backend tests in `backend/tests/`
  - [ ] Frontend tests in `frontend/tests/`
  - [ ] No scattered test files
**Implementation Steps**:
1. Review current test structure (find scattered test files)
2. Move backend tests to `backend/tests/` (consolidate)
3. Move frontend tests to `frontend/tests/` (consolidate)
4. Keep root `tests/` only for cross-stack integration tests (if needed)
5. Remove obsolete test files (test_*.py at project root, old performance tests)
6. Remove duplicate conftest.py files
7. Update pytest.ini or pyproject.toml if needed
8. Run tests to verify consolidation works
**Test Scenarios**:
  - `pytest backend/tests/` runs all backend tests
  - `npm test` (from frontend/) runs all frontend tests
  - No test files outside designated directories
  - CI/CD still finds tests
**References**:
  - `tests/` (MODIFY/DELETE)
  - `backend/tests/` (MODIFY)
  - `frontend/tests/` (MODIFY)
  - `pytest.ini` or `pyproject.toml` (MODIFY)

### T027: Clean up docs directory
- **Agent**: docs-maintainer
- **Blocked by**: [T024, T025]
- **Status**: completed ✅
**Acceptance Criteria**:
  - [ ] Obsolete documentation removed
  - [ ] Current documentation kept and updated
  - [ ] docs/ directory organized and concise
  - [ ] No duplicate or outdated docs
**Implementation Steps**:
1. Review all files in `docs/` directory
2. Identify obsolete docs (completed tasks, outdated designs, old QA reports, duplicate docs)
3. Keep essential docs:
   - ENVIRONMENT_CONFIGURATION.md
   - DATABASE_CONFIG.md
   - ADMIN_FEATURES.md
   - PROFILE_SYSTEM.md
   - SCHEDULING_SIMPLE.md
   - FORUM_SYSTEM.md
   - CI_CD.md
   - TESTING_TROUBLESHOOTING.md
4. Remove obsolete:
   - PLAN.md (after project complete)
   - Completed task docs (T002_*, T003_*, T005_*, etc.)
   - Old QA reports (QA_REPORT_T504.md, SCHEDULING_API_TEST_REPORT.md)
   - Duplicate docs (ENVIRONMENT.md, HARDCODED_URLS_AUDIT.md)
   - Outdated design docs (DESIGN_PROFILE_PAGES.md, DESIGN_SCHEDULING_UI.md if implemented)
5. Update remaining docs to reflect current state
6. Organize by category if needed
**Test Scenarios**:
  - All current features documented
  - No outdated information
  - docs/ directory easy to navigate
  - Essential guides remain
**References**:
  - `docs/` (MODIFY/DELETE)

### T028: Update CLAUDE.md with current architecture
- **Agent**: docs-maintainer
- **Blocked by**: [T024, T025, T027]
- **Status**: completed ✅
**Acceptance Criteria**:
  - [ ] CLAUDE.md reflects current project state
  - [ ] All features documented
  - [ ] Architecture section accurate
  - [ ] Common gotchas updated
  - [ ] References to obsolete docs removed
**Implementation Steps**:
1. Read current CLAUDE.md
2. Update project overview (if needed)
3. Update architecture section (verify all apps and services documented)
4. Update key technical details (verify all features mentioned)
5. Add/update sections for fixed features
6. Remove references to deleted docs
7. Update troubleshooting section (add new gotchas if found)
8. Verify all file paths accurate
**Test Scenarios**:
  - CLAUDE.md accurately describes platform
  - No broken references to docs
  - All features mentioned (dashboards, forum, scheduling, admin, profiles)
  - Common issues documented
  - Architecture section accurate
**References**:
  - `/home/mego/Python Projects/THE_BOT_platform/CLAUDE.md` (MODIFY)

### T029: Update README to be concise and accurate
- **Agent**: docs-maintainer
- **Blocked by**: [T028]
- **Status**: completed ✅
**Acceptance Criteria**:
  - [ ] README concise (under 200 lines)
  - [ ] Installation instructions accurate
  - [ ] Quick start works
  - [ ] Architecture overview brief
  - [ ] Links to detailed docs (CLAUDE.md)
**Implementation Steps**:
1. Read current README
2. Simplify project overview (1-2 paragraphs)
3. Update installation steps (verify they work)
4. Update quick start commands (verify they work)
5. Add brief architecture overview (refer to CLAUDE.md for details)
6. Link to CLAUDE.md for detailed documentation
7. Remove verbose sections
8. Test installation steps
**Test Scenarios**:
  - New user can follow README to set up project
  - Commands work as documented
  - README easy to read
  - Links to CLAUDE.md work
**References**:
  - `/home/mego/Python Projects/THE_BOT_platform/README.md` (MODIFY)

### T030: Verify CI/CD pipeline passes
- **Agent**: qa-code-tester
- **Blocked by**: [T026, T027, T028, T029]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] GitHub Actions workflow passes
  - [ ] All tests run in CI
  - [ ] No test discovery issues
  - [ ] Coverage reports generated
**Implementation Steps**:
1. Review `.github/workflows/` configuration
2. Update test paths if needed (after consolidation in T026)
3. Run tests locally to simulate CI environment
4. Push changes to trigger CI run
5. Monitor CI run
6. Fix any CI-specific failures
7. Verify coverage reports upload
**Test Scenarios**:
  - CI discovers all tests (backend and frontend)
  - Backend tests pass in CI
  - Frontend tests pass in CI
  - Coverage reports upload
  - No environment issues in CI
**References**:
  - `.github/workflows/` (MODIFY if needed)

### T031: Final smoke test in dev and production modes
- **Agent**: devops-engineer
- **Blocked by**: [T030]
- **Status**: pending ⏸️
**Acceptance Criteria**:
  - [ ] Development mode works completely
  - [ ] Production mode works completely
  - [ ] Environment switching clean
  - [ ] No errors in either mode
  - [ ] URLs correct per environment
**Implementation Steps**:
1. Set ENVIRONMENT=development in .env
2. Run `./start.sh` or `make start`
3. Test all features in browser (dashboards, forum, scheduling, admin, profiles)
4. Verify localhost URLs (API, WebSocket, media files)
5. Set ENVIRONMENT=production in .env
6. Configure production database (Supabase)
7. Test all features in production mode
8. Verify production URLs (the-bot.ru)
9. Document any remaining issues
**Test Scenarios**:
  - Dev mode: all features work, localhost URLs, WebSocket connects
  - Prod mode: all features work, production URLs, WebSocket connects
  - Switch modes: URLs update correctly
  - No errors in browser console
  - No errors in server logs
**References**:
  - `.env`
  - `start.sh`
  - `backend/core/services/env_config.py`

---

## T007 Analysis Findings (py-backend-dev)

**Admin Backend Architecture - SOLID Implementation**

Core file: `backend/accounts/staff_views.py` (2028 lines) - comprehensive admin operations with proper error handling, transaction safety, and Supabase integration.

**User Creation Endpoints - ALL WORKING:**

1. **POST /api/auth/students/create/** (lines 1515-1730)
   - Required: email, first_name, last_name, grade
   - Optional: phone, goal, tutor_id, parent_id, password
   - Auto-generates 12-char password if not provided
   - Supabase sync with 3-retry logic, fallback to Django-only
   - Returns credentials ONE TIME
   - Transaction-safe with atomic block
   - Profile creation via get_or_create (handles signal race)
   - Audit logging enabled

2. **POST /api/auth/parents/create/** (lines 1736-1919)
   - Required: email, first_name, last_name
   - Optional: phone, password
   - Same Supabase retry logic
   - Returns credentials ONE TIME
   - Transaction-safe

3. **POST /api/auth/staff/create/** (lines 282-522)
   - Creates teacher OR tutor (role param required)
   - Teacher requires: subject; Tutor requires: specialization
   - Creates TeacherSubject entry for teachers
   - Same pattern as above

4. **POST /api/auth/users/create/** (lines 1268-1509)
   - Generic endpoint for all roles
   - Role-specific validation via UserCreateSerializer

**Parent Assignment - WORKING:**

POST /api/auth/assign-parent/ (lines 1925-1991)
- Bulk assignment: { parent_id: int, student_ids: [1,2,3] }
- Updates StudentProfile.parent for each student
- Transaction-safe
- Audit logging
- Minor Issue: Idempotent but doesn't report if already assigned

**User Update/Delete - WORKING:**

1. PATCH /api/auth/users/{id}/ (lines 663-863)
   - Updates user fields + profile_data object
   - Email uniqueness validated
   - Cannot deactivate self
   - Creates profile if missing (defensive)
   - Supabase email sync
   - Transaction-safe

2. DELETE /api/auth/users/{id}/delete/ (lines 1169-1262)
   - Default: soft delete (is_active=False)
   - Query param: ?permanent=true for hard delete
   - Cannot delete self or superuser
   - Supabase sync for hard delete

**Password Reset - WORKING:**

POST /api/auth/users/{id}/reset-password/ (lines 1097-1163)
- Generates secure 12-char password
- Updates Django + Supabase
- Returns password ONE TIME
- Enhancement opportunity: Could add email notification

**Permissions - WORKING:**

IsStaffOrAdmin permission class (lines 51-91)
- Grants access to: is_staff, is_superuser, OR role=TUTOR
- DESIGN DECISION: Tutors have full admin access
- All endpoints properly protected
- Note: Uses print() for debug logging (should use logger)

**Issues Identified:**

1. N+1 Query in list_parents (Performance)
   - Line 2022 queries children in loop
   - Fix: Use annotate(children_count=Count('user__children_students'))

2. Excessive Debug Logging (Code Quality)
   - print() statements throughout
   - Should use logger.debug()

3. Inconsistent Password Generation (Minor Security)
   - Student/parent: get_random_string(12)
   - Reset: secrets.choice (more secure)
   - Recommendation: Standardize on secrets

4. No Rate Limiting (Security)
   - User creation endpoints not throttled
   - Could spam-create accounts
   - Recommendation: Add throttling (10 creations/hour)

5. No Avatar Upload in Admin Update (Feature Gap)
   - User.avatar field exists
   - Update endpoints don't handle file uploads
   - Recommendation: Add multipart/form-data support

6. Profile Signal Reliability (Cross-reference T010)
   - Code uses get_or_create everywhere (defensive)
   - Suggests potential signal issues
   - T010 will verify profile creation signals work correctly

**Data Persistence:**

All endpoints properly implement:
- transaction.atomic() for integrity
- .save(update_fields=[...]) for optimization
- .refresh_from_db() after transactions
- Proper error handling with rollback

**VERDICT**: Backend data persistence is SOLID. If frontend reports "data not saving", investigate:
1. Frontend API call payload format
2. Frontend response handling logic
3. Serializer validation failing silently
4. Profile signals overriding admin changes (verify in T010)

**Summary:**

WORKING (100% core functionality):
- All user creation endpoints (student, parent, teacher, tutor)
- Parent-to-students assignment (bulk support)
- User update (all fields + profiles)
- User delete (soft and hard modes)
- Password reset (secure generation)
- Permissions (proper access control)
- All listing endpoints (students, parents, staff)
- Subject assignment for teachers

MINOR ISSUES (optimizations):
1. N+1 query in list_parents
2. Debug logging cleanup needed
3. Inconsistent password generation
4. Missing rate limiting
5. Missing avatar upload
6. Profile signals need verification (T010)

RECOMMENDATION: Admin backend is production-ready. Issues are enhancements, not blockers. If frontend reports save failures, investigate frontend integration (T008).

