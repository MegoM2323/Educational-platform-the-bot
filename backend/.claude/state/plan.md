# Critical Security: Fix is_active checks in get_contacts() methods

## Issue
The `get_contacts()` methods in ChatService don't validate `is_active` status of referenced users, creating security risk. This violates the permission model in permissions.py which strictly requires both users to be active.

## Parallel Group 1 - Fix all get_contacts role methods

### Task 1: Fix _get_contacts_for_student
- **File:** `backend/chat/services/chat_service.py` (lines 363-376)
- **Current problem:** Doesn't check `teacher__is_active=True`
- **Fix:** Add `teacher__is_active=True` to SubjectEnrollment filter
- **Agent:** coder

### Task 2: Fix _get_contacts_for_teacher
- **File:** `backend/chat/services/chat_service.py` (lines 379-401)
- **Current problems:**
  - Doesn't check `student__is_active=True` in SubjectEnrollment filter (line 383)
  - Parent filter checks `parent__is_active=True` but should check `user__is_active=True` (children active status)
  - Tutor filter checks `tutor__is_active=True` but should also check that children are active
- **Fixes:**
  - Line 383-385: Add `student__is_active=True` to SubjectEnrollment filter
  - Line 389-392: Change `parent__is_active=True` to `user__is_active=True`
  - Line 395-398: Add `user__is_active=True` to StudentProfile filter
- **Agent:** coder

### Task 3: Fix _get_contacts_for_tutor
- **File:** `backend/chat/services/chat_service.py` (lines 404-426)
- **Current problems:**
  - Line 408-411: Checks `tutor__is_active=True` (redundant - tutor is already known to be active), should check `user__is_active=True` (student active)
  - Line 414-417: Doesn't check `teacher__is_active=True` in SubjectEnrollment
  - Line 420-423: Doesn't check `user__is_active=True` for students
- **Fixes:**
  - Line 408-411: Change to `user__is_active=True`
  - Line 414-417: Add `teacher__is_active=True` to SubjectEnrollment filter
  - Line 420-423: Add `user__is_active=True` to StudentProfile filter
- **Agent:** coder

### Task 4: Fix _get_contacts_for_parent
- **File:** `backend/chat/services/chat_service.py` (lines 429-450)
- **Current problem:**
  - Line 433-436: Checks `parent__is_active=True` (redundant - parent is already active), should check `user__is_active=True` (children active)
  - Subsequent queries don't validate teacher/tutor active status
- **Fixes:**
  - Line 433-436: Change `parent__is_active=True` to `user__is_active=True`
  - Line 438-441: Add `teacher__is_active=True` to SubjectEnrollment filter
  - Line 444-447: Add `tutor__is_active=True` to StudentProfile filter
- **Agent:** coder

## Sequential (Testing)

### Task 5: Verify with permissions.py alignment
- Run test suite to ensure no regressions
- Verify all get_contacts() methods match permission model in permissions.py

---

## Implementation Status
- [ ] Task 1: Fix _get_contacts_for_student
- [ ] Task 2: Fix _get_contacts_for_teacher
- [ ] Task 3: Fix _get_contacts_for_tutor
- [ ] Task 4: Fix _get_contacts_for_parent
- [ ] Task 5: Run verification tests
