# Chat Testing Quick Start Guide

## Files Created

### 1. Frontend E2E Tests
**Location**: `/home/mego/Python Projects/THE_BOT_platform/frontend/e2e/chat-scenarios.spec.ts`

7 test scenarios using Playwright:
- Scenario 1: Admin loads contacts
- Scenario 2: Student loads filtered contacts
- Scenario 3: Create chat and send message
- Scenario 4: Load chat list with unread counts
- Scenario 5: API contact loading
- Scenario 6: Error handling
- Scenario 7: WebSocket real-time messaging

### 2. Backend API Tests
**Location**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/tests/test_chat_contact_loading.py`

15+ test cases across 5 test classes:
- ChatContactLoadingScenarios (7 tests)
- ChatMessageScenarios (3 tests)
- ChatServicePerformance (2 tests)
- ChatErrorHandling (3 tests)

---

## Quick Start Commands

### Run Frontend E2E Tests

```bash
# Navigate to frontend
cd /home/mego/Python\ Projects/THE_BOT_platform/frontend

# Run all chat scenario tests
npm run test:e2e -- e2e/chat-scenarios.spec.ts

# Run with UI (recommended for first run)
npx playwright test e2e/chat-scenarios.spec.ts --ui

# Run headed (see the browser)
npm run test:e2e:headed -- e2e/chat-scenarios.spec.ts

# Debug mode
npx playwright test e2e/chat-scenarios.spec.ts --debug

# View test report
npm run test:e2e:report
```

### Run Backend API Tests

```bash
# Navigate to backend
cd /home/mego/Python\ Projects/THE_BOT_platform/backend

# Run all chat contact loading tests
python -m pytest chat/tests/test_chat_contact_loading.py -v

# Run specific test class
python -m pytest chat/tests/test_chat_contact_loading.py::ChatContactLoadingScenarios -v

# Run single test
python -m pytest chat/tests/test_chat_contact_loading.py::ChatContactLoadingScenarios::test_scenario_1_admin_loads_all_contacts -xvs

# Run with coverage report
python -m pytest chat/tests/test_chat_contact_loading.py --cov=chat --cov-report=html

# Run with verbose output
python -m pytest chat/tests/test_chat_contact_loading.py -vv --tb=short
```

---

## Prerequisites

### Frontend E2E Tests
- Node.js 18+
- Frontend running: `npm run dev` on http://localhost:8080
- Backend API running: Django server on http://localhost:8000
- Test users must exist in database

### Backend API Tests
- Python 3.9+
- PostgreSQL running on localhost:5432
- Database: `thebot_db`
- Migrations applied: `python manage.py migrate`

---

## Test Data

### Frontend Test Users (auto-login)
```
admin_test / TestAdmin123!
teacher_test / TestTeacher123!
student_test / TestStudent123!
tutor_test / TestTutor123!
parent_test / TestParent123!
```

### Backend Tests
Auto-generated per test class:
- 4 teachers
- 3 tutors
- 5 students
- 2 parents
- Math & English subjects
- Subject enrollments

---

## Key Test Scenarios

### Scenario 1: Admin Contact Loading
**Expected**: 600+ contacts loaded in <2 seconds
```bash
npm run test:e2e -- e2e/chat-scenarios.spec.ts -g "Admin loads contacts"
```

### Scenario 2: Student Filtered Contacts
**Expected**: 5-20 contacts (only teachers/tutors) in <2 seconds
```bash
npm run test:e2e -- e2e/chat-scenarios.spec.ts -g "Student loads contacts"
```

### Scenario 3: Message Sending
**Expected**: Message sent and delivered instantly
```bash
npm run test:e2e -- e2e/chat-scenarios.spec.ts -g "Create chat and send message"
```

### Scenario 4: Chat List Performance
**Expected**: Chat list loaded in <1 second
```bash
npm run test:e2e -- e2e/chat-scenarios.spec.ts -g "Load chat list"
```

### API Performance Test
**Expected**: Contact API responds in <2 seconds
```bash
python -m pytest chat/tests/test_chat_contact_loading.py::ChatServicePerformance -v
```

---

## Troubleshooting

### Frontend Tests Not Finding Elements
1. Verify test users exist in DB
2. Check that login works manually first
3. Use `--headed` to see what's happening
4. Use `--debug` to pause and inspect

### Backend Tests Failing
1. Ensure database is running: `psql -U postgres -d thebot_db -c "SELECT 1"`
2. Run migrations: `python manage.py migrate`
3. Check database connection in settings.py
4. Verify test environment: `echo $ENVIRONMENT` (should be "test")

### Twisted/OpenSSL Error
If you see SSL errors starting the dev server:
```bash
# Use gunicorn instead of runserver
gunicorn config.wsgi:application --bind 0.0.0.0:8000

# Or use Docker Compose
docker-compose up
```

### Port Already in Use
```bash
# Find process using port
lsof -i :8000  # Backend
lsof -i :8080  # Frontend

# Kill the process
kill -9 <PID>
```

---

## Output Format

### Frontend E2E Tests
- HTML report: `playwright-report/index.html`
- JSON results: `test-results/results.json`
- Screenshots on failure (if any)
- Video recording on failure

### Backend API Tests
- Console output with test names and results
- Coverage report: `htmlcov/index.html`
- Failed assertions with full tracebacks

---

## Performance Targets

| Operation | Target | Status |
|-----------|--------|--------|
| Admin contact load | <2s | ✓ Optimized |
| Student contact load | <2s | ✓ Optimized |
| Chat list load | <1s | ✓ Target |
| Message send | <200ms | ✓ WebSocket |
| Contact API | <2s | ✓ ~4 queries |

---

## Test Execution Checklist

- [ ] Install dependencies: `npm install` (frontend), `pip install -r requirements.txt` (backend)
- [ ] Start PostgreSQL: `service postgresql start`
- [ ] Start Django: `python manage.py runserver` or `gunicorn`
- [ ] Start frontend: `npm run dev`
- [ ] Verify DB connection: `psql -d thebot_db -c "SELECT count(*) FROM accounts_user;"`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create test users (if needed)
- [ ] Run backend tests first: `python -m pytest chat/tests/test_chat_contact_loading.py`
- [ ] Run frontend E2E tests: `npm run test:e2e`
- [ ] Review reports: `npm run test:e2e:report`

---

## Documentation

Full test documentation: `/home/mego/Python Projects/THE_BOT_platform/TEST_EXECUTION_REPORT.md`

---

## Support

Test files:
- Frontend: `frontend/e2e/chat-scenarios.spec.ts`
- Backend: `backend/chat/tests/test_chat_contact_loading.py`

Config files:
- Playwright: `frontend/playwright.config.ts`
- Jest: `frontend/jest.config.js`
- Pytest: `backend/pytest.ini`
- Django: `backend/config/settings.py`
