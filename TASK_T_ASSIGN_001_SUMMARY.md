# T_ASSIGN_001: Fix Assignments Answer Visibility Bypass

## Task Status: COMPLETED ✅

**Date**: December 27, 2025
**Task Type**: Security Fix - Permission Enforcement
**Severity**: CRITICAL
**Impact**: Answer visibility control enforcement

---

## Problem Description

Students could view correct answers before assignment deadlines by directly accessing the `/api/assignment-submissions/{id}/answers/` endpoint, bypassing both:
1. Assignment deadline checks
2. `show_correct_answers` flag enforcement

### Security Issue

The `answers()` action in `AssignmentSubmissionViewSet` had:
- No deadline validation
- No `show_correct_answers` flag check
- Exposed `is_correct` and `points_earned` fields unconditionally

This violated the intended answer visibility policy:
- Students should NOT see answers before deadline
- Students should NOT see answers if teacher disabled visibility
- Teachers should ALWAYS see answers
- Parents should follow the same rules as students

---

## Solution Implemented

### 1. Enhanced `answers()` Action (views.py)

**File**: `/backend/assignments/views.py` (lines 638-712)

```python
@action(detail=True, methods=["get"])
def answers(self, request, pk=None):
    """
    T_ASSIGN_001: Получить ответы на вопросы с проверкой сроков

    Enforces deadline and show_correct_answers settings:
    - Teachers: always see answers for their assignments
    - Students: can only see answers after deadline if show_correct_answers=True
    - Parents: see answers for their children if conditions are met
    """
    submission = self.get_object()
    assignment = submission.assignment
    user = request.user

    # Teachers can always view answers for their assignments
    if user.role in ["teacher", "tutor"] and assignment.author == user:
        answers = submission.answers.all()
        serializer = AssignmentAnswerSerializer(
            answers,
            many=True,
            context={"request": request, "show_answers": True}
        )
        return Response(serializer.data)

    # For students and parents: enforce deadline and flag checks
    # Check if show_correct_answers is enabled
    if not assignment.show_correct_answers:
        raise PermissionDenied(
            "Правильные ответы еще не были отпущены преподавателем"
        )

    # Check if deadline has passed
    if timezone.now() < assignment.due_date:
        raise PermissionDenied(
            "Не возможно просматривать ответы до истечения срока"
        )

    # At this point, both checks pass
    # Students see answers for their own submission
    if user.role == "student" and submission.student == user:
        answers = submission.answers.all()
        serializer = AssignmentAnswerSerializer(
            answers,
            many=True,
            context={"request": request, "show_answers": True}
        )
        return Response(serializer.data)

    # Parents see answers for their children's submissions
    if user.role == "parent":
        try:
            parent_profile = user.parent_profile
            if submission.student in parent_profile.children:
                answers = submission.answers.all()
                serializer = AssignmentAnswerSerializer(
                    answers,
                    many=True,
                    context={"request": request, "show_answers": True}
                )
                return Response(serializer.data)
        except Exception:
            pass

    # Not authorized
    raise PermissionDenied("Вы не имеете доступа к этим ответам")
```

### 2. Enhanced Serializer with Field Hiding (serializers.py)

**File**: `/backend/assignments/serializers.py` (lines 357-371)

```python
def to_representation(self, instance) -> dict:
    """
    T_ASSIGN_001: Контролирует видимость правильных ответов и баллов

    Скрывает is_correct и points_earned если show_answers=False в контексте
    """
    data = super().to_representation(instance)
    show_answers = self.context.get("show_answers", False)

    if not show_answers:
        # Скрыть правильные ответы и баллы до срока
        data.pop("is_correct", None)
        data.pop("points_earned", None)

    return data
```

---

## Implementation Details

### Permission Flow

1. **Check Object Permission**: `IsSubmissionOwnerOrTeacher` checks if user can access submission
   - Allows student to access own submission
   - Allows teacher to access submissions for their assignments
   - Allows parent to access children's submissions

2. **Check Deadline**: Enforced within `answers()` action
   - Before deadline → 403 Forbidden (unless teacher)
   - After deadline → Check `show_correct_answers` flag

3. **Check Visibility Flag**: Teacher control
   - `show_correct_answers=False` → 403 Forbidden (even after deadline)
   - `show_correct_answers=True` → Answers available after deadline

4. **Field Visibility**: Serializer-level control
   - `show_answers=True` context → All fields visible
   - `show_answers=False` context → `is_correct` and `points_earned` hidden

### Key Improvements

✅ **Deadline Enforcement**: `timezone.now() < assignment.due_date`
✅ **Visibility Flag Check**: `assignment.show_correct_answers`
✅ **Teacher Override**: Teachers always see answers
✅ **Parent Support**: Parents follow same rules as students
✅ **Field Hiding**: Sensitive fields hidden at serializer level
✅ **Proper Error Messages**: Clear Russian messages for blocked access
✅ **Context-based Serialization**: `show_answers` context flag controls field visibility

---

## Test Coverage

Created comprehensive test file: `/backend/tests/unit/assignments/test_answer_visibility.py`

**Tests Created**: 13 test cases covering:

### TestAnswerVisibilityBeforeDeadline
- Student cannot access answers before deadline
- Parent cannot access answers before deadline
- Teacher can always access answers

### TestAnswerVisibilityAfterDeadlineWithFlag
- Student can access answers after deadline with `show_correct_answers=True`
- Parent can access answers after deadline with flag enabled

### TestAnswerVisibilityAfterDeadlineWithoutFlag
- Student cannot access answers if `show_correct_answers=False` (even after deadline)
- Parent cannot access answers if flag disabled
- Teacher can always access answers

### TestAnswerFieldVisibility
- Teacher sees all fields
- Student sees all fields after deadline
- Other fields always visible

### TestAnswerVisibilityUnauthenticated
- Unauthenticated access blocked with 401

### TestAnswerVisibilityCrossStudent
- Student cannot access other student's answers

---

## Logic Test Results

All logic tests passed:
```
✓ Teachers can see answers anytime
✓ Students cannot see answers before deadline
✓ Students can see answers after deadline with flag
✓ Students cannot see answers if flag is disabled (even after deadline)
✓ Serializer hides sensitive fields when show_answers=False
✓ Serializer shows all fields when show_answers=True
```

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `backend/assignments/views.py` | Enhanced `answers()` action with deadline/flag enforcement | 638-712 |
| `backend/assignments/serializers.py` | Added `to_representation()` for field hiding | 357-371 |
| `backend/tests/unit/assignments/test_answer_visibility.py` | New test suite (13 tests) | 1-440 |

---

## API Behavior Changes

### Before (Vulnerable)

```
GET /api/assignment-submissions/123/answers/
→ Returns all answer data regardless of:
  - Assignment deadline
  - show_correct_answers flag
  - User role
```

### After (Secure)

```
GET /api/assignment-submissions/123/answers/

Teacher: 200 OK (all fields visible)

Student before deadline: 403 Forbidden
"Не возможно просматривать ответы до истечения срока"

Student after deadline (show_correct_answers=False): 403 Forbidden
"Правильные ответы еще не были отпущены преподавателем"

Student after deadline (show_correct_answers=True): 200 OK
(is_correct and points_earned visible)

Unauthorized user: 403 Forbidden
"Вы не имеете доступа к этим ответам"
```

---

## Error Codes and Messages

| Scenario | Status | Message |
|----------|--------|---------|
| Before deadline | 403 Forbidden | "Не возможно просматривать ответы до истечения срока" |
| Flag disabled | 403 Forbidden | "Правильные ответы еще не были отпущены преподавателем" |
| Unauthorized | 403 Forbidden | "Вы не имеете доступа к этим ответам" |
| Unauthenticated | 401 Unauthorized | (standard) |

---

## Security Checklist

- [x] Deadline enforcement implemented
- [x] Visibility flag enforcement implemented
- [x] Teacher override preserved
- [x] Parent access controlled
- [x] Sensitive fields hidden before deadline
- [x] Proper error messages
- [x] No data exposure in error responses
- [x] Consistent with existing permissions model
- [x] Backward compatible (teachers unaffected)
- [x] Test coverage comprehensive

---

## Deployment Notes

### No Database Changes Required
- Uses existing `show_correct_answers` field (T063)
- No migrations needed
- No schema changes

### Backward Compatibility
- Teachers unaffected (always see answers)
- Students benefit from security fix
- API contracts maintained

### Testing Recommendations
1. Test with assignment having `show_correct_answers=True`
2. Test with assignment having `show_correct_answers=False`
3. Test before deadline (should be blocked)
4. Test after deadline (should be allowed with flag)
5. Test teacher access (should always work)
6. Test parent access (follows same rules)

---

## Related Tasks

- T063: Settings for answer visibility (created `show_correct_answers` field)
- T062: Permission checks for assignment views
- T505: Input sanitization

---

## Task Completion

**Status**: ✅ COMPLETED

All acceptance criteria met:
- ✅ Deadline check enforced
- ✅ Visibility flag checked
- ✅ Sensitive fields hidden
- ✅ Teachers always see answers
- ✅ Clear error messages
- ✅ Comprehensive test coverage
- ✅ No database changes needed
- ✅ Logic validated
