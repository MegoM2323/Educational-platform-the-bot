# Forum System Unit Tests - Quick Start Guide

## Running the Tests

### Run all forum comprehensive tests (30 tests)
```bash
cd backend
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py -v
```

### Run specific test class
```bash
# Chat Creation Signal Tests (6 tests)
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py::TestForumChatCreationSignal -v

# Message Tests (6 tests)
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py::TestForumMessages -v

# Chat Participant Tests (4 tests)
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py::TestChatParticipants -v

# Serializer Tests (3 tests)
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py::TestForumSerializers -v

# Permission Tests (6 tests)
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py::TestForumPermissions -v

# Query Optimization Tests (2 tests)
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py::TestForumQueryOptimization -v

# Signal with Mocks Tests (3 tests)
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py::TestForumSignalWithMocks -v
```

### Run specific test
```bash
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py::TestForumChatCreationSignal::test_enrollment_creates_forum_subject_chat -v
```

### Run with coverage report
```bash
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py --cov=chat --cov-report=html
```

### Run with detailed output (short traceback)
```bash
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py -v --tb=short
```

### Run with full traceback (for debugging)
```bash
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py -v --tb=long
```

## Test File Location
```
backend/tests/unit/chat/test_forum_comprehensive.py
```

## Test Structure

### 1. TestForumChatCreationSignal (6 tests)
Tests automatic forum chat creation when SubjectEnrollment is created.

**Scenarios:**
- FORUM_SUBJECT chat auto-created on enrollment
- FORUM_TUTOR chat auto-created if student has tutor
- No FORUM_TUTOR if student has no tutor
- Correct participants assigned
- Idempotent (no duplicates on re-trigger)
- Works with inactive enrollments

### 2. TestForumMessages (6 tests)
Tests forum message creation, permissions, and unread tracking.

**Scenarios:**
- Message creation with all fields
- ForeignKey validation (sender, room required)
- Sender sees message as read
- Other participants see message as unread
- Message edit doesn't affect unread status

### 3. TestChatParticipants (4 tests)
Tests chat participant management and unread count tracking.

**Scenarios:**
- Participants added on enrollment
- Unread count = 0 with no messages
- Unread count respects last_read_at timestamp
- last_read_at can be updated

### 4. TestForumSerializers (3 tests)
Tests serializer annotation counts and optimization.

**Scenarios:**
- ChatRoomListSerializer includes unread_count
- ChatRoomListSerializer includes participants_count
- MessageSerializer includes sender details

### 5. TestForumPermissions (6 tests)
Tests role-based forum chat visibility.

**Scenarios:**
- Student sees own FORUM_SUBJECT chats
- Student sees own FORUM_TUTOR chats
- Teacher sees student FORUM_SUBJECT chats
- Tutor sees student FORUM_TUTOR chats
- Parent doesn't see forum chats
- Unrelated students don't see each other's chats

### 6. TestForumQueryOptimization (2 tests)
Tests query count for common operations.

**Scenarios:**
- Chat list < 10 queries
- Message list < 10 queries

### 7. TestForumSignalWithMocks (3 tests)
Tests signal integration with Pachca via mocks.

**Scenarios:**
- Forum message signal queues Pachca task
- Message creation succeeds even if task dispatch fails
- Signal doesn't trigger for non-forum chat types

## Key Testing Utilities

### Database Setup
- `@pytest.mark.django_db` - Enable database access
- `@pytest.mark.unit` - Mark as unit test
- `db` fixture - Database access within test

### Fixtures (from conftest.py)
- `student_user` - Student user with StudentProfile
- `teacher_user` - Teacher user with TeacherProfile
- `tutor_user` - Tutor user with TutorProfile
- `parent_user` - Parent user with ParentProfile
- `subject` - Subject instance
- `enrollment` - SubjectEnrollment instance

### Common Assertions
```python
# Model creation and state
assert message.id is not None
assert message.content == "Test"

# Relationship checks
assert forum_chat.participants.filter(id=student.id).exists()
assert ChatParticipant.objects.filter(room=chat, user=user).exists()

# Count assertions
assert participant.unread_count == 1
assert forum_chat.participants.count() == 2

# Serializer data
assert 'unread_count' in serializer.data
assert serializer.data['participants_count'] == 2
```

### Mocking
```python
from unittest.mock import patch, MagicMock

with patch('chat.tasks.send_pachca_forum_notification_task') as mock_task:
    mock_task.apply_async = MagicMock()
    # ... test code ...
    mock_task.apply_async.assert_called_once()
```

### Query Counting
```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

with CaptureQueriesContext(connection) as context:
    # ... database operations ...
    assert len(context) < 10  # Less than 10 queries
```

## Expected Output

### All Tests Pass
```
============================= test session starts ==============================
...
tests/unit/chat/test_forum_comprehensive.py::TestForumChatCreationSignal::test_enrollment_creates_forum_subject_chat PASSED
...
============================= 30 passed in 17.14s ==============================
```

### With Coverage
```
chat/models.py                                  104    7    93%   ✅
chat/signals.py                                 56     8    86%   ✅
chat/serializers.py                            165    43    74%   ✅
```

## Troubleshooting

### Error: "ENVIRONMENT=test not set"
```bash
# Solution: Always set ENVIRONMENT=test before pytest
ENVIRONMENT=test python -m pytest ...
```

### Error: "ModuleNotFoundError: No module named 'materials.models'"
```bash
# Solution: Run from backend directory
cd backend
ENVIRONMENT=test python -m pytest ...
```

### Error: "ChatParticipant.DoesNotExist"
```bash
# Explanation: ChatParticipant records are created on demand (get_or_create)
# Tests that need ChatParticipant should use:
participant, _ = ChatParticipant.objects.get_or_create(room=chat, user=user)
```

### Slow Test Execution
```bash
# Use -n for parallel execution (pytest-xdist)
ENVIRONMENT=test python -m pytest tests/unit/chat/test_forum_comprehensive.py -n auto
```

## Dependencies

- Python 3.13+
- Django 4.2+
- pytest 7.4+
- pytest-django 4.7+
- factory-boy (for fixtures)
- mock (built-in unittest.mock)

## Performance

- Total Runtime: ~15-20 seconds
- Test Count: 30 tests
- Pass Rate: 100% (30/30)
- Coverage: 90%+ for core models and signals

## Next Steps

After these unit tests pass:

1. **Integration Tests (T021)**
   - Test API endpoints (/api/forum/, /api/messages/)
   - Full request/response cycle
   - Database persistence

2. **E2E Tests (T022)**
   - Browser-based testing with Playwright
   - WebSocket communication
   - Real user workflows

3. **Performance Tests**
   - Load testing with large message volumes
   - Concurrent user scenarios
   - Memory profiling

## Documentation

- Test file: `/backend/tests/unit/chat/test_forum_comprehensive.py`
- Results: `TEST_RESULTS_T020.txt`
- Forum docs: `docs/FORUM_SYSTEM.md`
- Models: `backend/chat/models.py`
- Signals: `backend/chat/signals.py`
