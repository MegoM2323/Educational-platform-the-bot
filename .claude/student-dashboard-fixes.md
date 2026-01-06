# Student Dashboard Testing & Fixes Plan
**Session ID:** student-dashboard-2026-01-07
**Status:** Active Testing Phase
**Target:** 100% dashboard functionality across all user roles

---

## Phase 1: E2E Testing (IN PROGRESS)

### Infrastructure Setup
- [ ] Backend server running on http://localhost:8000
- [ ] Frontend server running on http://localhost:8080
- [ ] PostgreSQL database ready
- [ ] Redis for cache/channels ready

### Test Execution
- [ ] Playwright tests: `frontend/e2e/student-dashboard.spec.ts` (15 tests)
- [ ] Playwright tests: `frontend/e2e/messaging.spec.ts` (existing)
- [ ] Generate test report with all failures
- [ ] Document all issues found

### Issues Found During Testing
*To be filled during execution*

---

## Phase 2: Bug Analysis & Planning - FINDINGS

### CRITICAL ISSUES FOUND ✓

#### Issue 1: E2E Test Login Failure (CRITICAL)
**File:** `frontend/e2e/student-dashboard.spec.ts` line 29
**Problem:** Wrong tab selected on login page
- Function tries to fill "Имя пользователя" field
- But "Логин" tab is inactive (Email tab is active by default)
- Field is hidden, causing 30-second timeout on all 15 tests
**Fix:** Click "Логин" tab before filling username field

#### Issue 2: No Real-Time Dashboard Updates (HIGH)
**File:** `frontend/src/pages/dashboard/StudentDashboard.tsx`
**Problem:** StudentDashboard doesn't use WebSocket
- Only HTTP polling via TanStack Query (60s stale time)
- No real-time updates when teacher posts grades, assignments change
- Other role data not pushed to student in real-time
**Fix:** Integrate WebSocket consumer for dashboard updates

#### Issue 3: Incomplete Offline Functionality (MEDIUM)
**File:** `frontend/src/pages/dashboard/StudentDashboard.tsx` line 184-192
**Problem:** Offline mode has basic cache but incomplete
- Doesn't show all necessary cached data
- Offline UI may not match online UI
**Fix:** Enhance offline state with full cached data display

#### Issue 4: Missing Network Retry Configuration (MEDIUM)
**File:** `frontend/src/hooks/useStudent.ts` line 15
**Problem:** No explicit retry logic for network failures
- Only uses default TanStack Query retry (3 attempts)
- No exponential backoff
- No retry config visible in hook
**Fix:** Add explicit retry options with exponential backoff

#### Issue 5: Student Permissions Not Fully Enforced (LOW)
**File:** `backend/materials/student_dashboard_views.py` line 34-38
**Problem:** Backend checks role but some edge cases may slip
- Role check is at view level, not middleware
- Service layer checks but could be bypassed
**Fix:** Add explicit role validation in service layer

### Cross-Role Interactions Status
✓ Student → Teacher feedback visible
✓ Student → Tutor assignments working
✓ Student → Parent notifications working
✓ Data isolation working correctly

### UI/UX Status
✓ Responsive design works
✓ Error handling present
✓ Loading states implemented
✓ Accessibility components exist but need validation

---

## Phase 3: Parallel Implementation Groups

### Group 1: E2E Test Fixes (CRITICAL)
**Task 1: Fix E2E Test Login Function**
- File: `frontend/e2e/student-dashboard.spec.ts` line 29-40
- Issue: #1 - E2E Test Login Failure
- Type: Bug fix
- Status: NOT STARTED

### Group 2: Frontend Hooks & API (Independent - Can run in parallel)
**Task 2.1: Add Network Retry to useStudent Hook**
- File: `frontend/src/hooks/useStudent.ts`
- Issue: #4 - Missing Network Retry Configuration
- Type: Enhancement
- Status: NOT STARTED

**Task 2.2: Add WebSocket Real-Time Dashboard Updates**
- File: `frontend/src/hooks/useStudent.ts` (add new hook useStudentDashboardRealTime)
- Related: `frontend/src/services/websocketService.ts`
- Issue: #2 - No Real-Time Dashboard Updates
- Type: Enhancement
- Status: NOT STARTED

**Task 2.3: Enhance StudentDashboard Offline Functionality**
- File: `frontend/src/pages/dashboard/StudentDashboard.tsx` line 184-192
- Issue: #3 - Incomplete Offline Functionality
- Type: Enhancement
- Status: NOT STARTED

### Group 3: Backend Permissions (Independent)
**Task 3: Strengthen Student Permissions Validation**
- File: `backend/materials/student_dashboard_service.py` line 28-29
- File: `backend/materials/student_dashboard_views.py` line 34-38
- Issue: #5 - Student Permissions Not Fully Enforced
- Type: Enhancement
- Status: NOT STARTED

### Group 3: Sequential Testing & Verification
**Task 3.1: Unit Tests**
- Create/update unit tests for fixed components
- Ensure 100% test pass rate
- Coverage: >90% for critical paths

**Task 3.2: Integration Tests**
- Test cross-module interactions
- Validate API contracts
- Test WebSocket connections

**Task 3.3: E2E Tests Re-run**
- Execute full Playwright test suite
- Verify all 15+ tests pass
- Performance metrics acceptable

---

## Phase 4: Specific Fixes by Category

### Data Flow Issues
- [ ] Verify API response caching
- [ ] Check data consistency across components
- [ ] Validate real-time updates via WebSocket

### UI/UX Issues
- [ ] Fix responsive layout bugs
- [ ] Improve loading states
- [ ] Add proper error boundaries
- [ ] Accessibility fixes (alt text, ARIA labels, keyboard navigation)

### Performance Issues
- [ ] Optimize API queries (select_related, prefetch_related)
- [ ] Implement lazy loading for materials
- [ ] Cache optimization
- [ ] Code splitting for frontend

### Cross-Role Interaction Issues
- [ ] Student can see teacher feedback
- [ ] Student receives tutor messages
- [ ] Parent notifications working
- [ ] Teacher can grade student submissions
- [ ] Tutor can assign work to student

---

## Review & Commit Strategy

### Code Review Checklist
- [ ] No console errors or warnings
- [ ] Accessibility compliance (WCAG 2.1 AA)
- [ ] Performance metrics met
- [ ] No security vulnerabilities
- [ ] Code style consistent
- [ ] All tests passing

### Commit Messages (Russian, no Claude mentions)
```
[STUDENT_DASHBOARD] Исправлено: [описание изменения]
[STUDENT_DASHBOARD] Улучшено: [описание улучшения]
[STUDENT_DASHBOARD] Добавлено: [описание новой функции]
```

---

## Test Report Template

### Summary
- Total Tests: X
- Passed: X
- Failed: X
- Skipped: X
- Success Rate: X%

### Failed Tests
```
Test: [Name]
File: [Path]
Error: [Full error message]
Stack Trace: [Stack]
Fix Applied: [What was fixed]
Re-test Status: [Pass/Fail]
```

---

## Status Tracking

| Phase | Task | Status | Issues | Fixes |
|-------|------|--------|--------|-------|
| 1 | E2E Setup | [TBD] | [TBD] | [TBD] |
| 2 | Analysis | [TBD] | [TBD] | [TBD] |
| 3.1 | Backend | [TBD] | [TBD] | [TBD] |
| 3.2 | Frontend | [TBD] | [TBD] | [TBD] |
| 3.3 | Hooks/API | [TBD] | [TBD] | [TBD] |
| 3.4 | Tests | [TBD] | [TBD] | [TBD] |
| 4 | Review | [TBD] | [TBD] | [TBD] |

---

## Execution Order

### Sequential (Phase 1-2)
1. Set up test infrastructure
2. Run E2E tests and collect all failures
3. Analyze and categorize issues
4. Create detailed fix list

### Parallel (Phase 3)
- Group 1: Backend API fixes (tasks 1.1, 1.2, 1.3 in parallel)
- Group 2: Frontend components fixes (tasks 2.1-2.5 in parallel)

### Sequential (Phase 4)
- Code review for each module
- Fix reviewer issues
- Re-test and verify

### Final (Phase 5)
- Comprehensive E2E test run
- Performance validation
- Single commit with all changes
