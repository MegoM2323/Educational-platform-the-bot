# T011: Forum with Pachca E2E Tests - Quick Start Guide

**Last Updated:** 2025-12-15

---

## What Was Created

Complete E2E test suite for Forum functionality with Pachca notifications:
- **File:** `frontend/tests/e2e/forum-with-pachca.spec.ts` (724 lines)
- **Tests:** 17+ test cases covering all scenarios
- **Coverage:** Teacher/Student messaging, real-time updates, responsive design, Pachca integration

---

## 1. Start the Application

```bash
cd /home/mego/Python\ Projects/THE_BOT_platform

# Start both backend and frontend
./start.sh

# Wait for startup messages:
# Backend: Daphne running on http://localhost:8000
# Frontend: Vite running on http://localhost:8080

# Both should be running before tests start
```

**What to check:**
- Backend ready: `http://localhost:8000/api/` (CORS headers working)
- Frontend ready: `http://localhost:8080/` (login page loads)

---

## 2. Run All Tests

```bash
cd /home/mego/Python\ Projects/THE_BOT_platform/frontend

# Run all 17+ forum-with-pachca tests
npx playwright test tests/e2e/forum-with-pachca.spec.ts

# Expected output:
# Running 54 tests using 3 workers
# ✓ All tests pass (30-60 seconds)
```

---

## 3. Common Commands

### Run with detailed output
```bash
npx playwright test tests/e2e/forum-with-pachca.spec.ts --reporter=list
```

### Run specific test
```bash
# Run test T011.3
npx playwright test tests/e2e/forum-with-pachca.spec.ts -g "T011.3"

# Run scenario 1 only
npx playwright test tests/e2e/forum-with-pachca.spec.ts -g "Scenario 1"

# Run responsive tests only
npx playwright test tests/e2e/forum-with-pachca.spec.ts -g "Responsive Design"
```

### Run with browser visible (debugging)
```bash
npx playwright test tests/e2e/forum-with-pachca.spec.ts --headed --browser=chromium
```

### View HTML report
```bash
npx playwright test tests/e2e/forum-with-pachca.spec.ts
npx playwright show-report
```

### Debug single test interactively
```bash
npx playwright test tests/e2e/forum-with-pachca.spec.ts -g "T011.3" --debug
```

---

## 4. Test Execution Flow

### Scenario 1: Teacher Creates Forum Chat
```
Login as teacher
  ↓
Navigate to /dashboard/teacher/forum
  ↓
See "Новый чат" button
  ↓
Post message "Hello, this is test message with Pachca"
  ↓
Message appears in chat (real-time)
  ↓
Pachca notification sent ✓
```

### Scenario 2: Student Receives & Replies
```
Login as student
  ↓
Navigate to /dashboard/student/forum
  ↓
See chat from teacher
  ↓
Open chat and post reply
  ↓
Reply appears in real-time
  ↓
Pachca notification sent ✓
```

### Scenario 3: Real-Time Updates
```
Open teacher in one tab, student in another
  ↓
Teacher posts message
  ↓
Student sees it in real-time (WebSocket)
  ↓
Student replies
  ↓
Teacher sees reply in real-time
  ↓
Both Pachca notifications sent ✓
```

---

## 5. Test Results Summary

### Expected: ✅ All Tests Pass
```
✓ Scenario 1: Teacher creates forum (4 tests)
✓ Scenario 2: Student replies (4 tests)
✓ Scenario 3: Real-time updates (2 tests)
✓ Responsive design (3 tests)
✓ Error handling (2 tests)
✓ All roles (2 tests)

Total: 17+ tests in ~30-60 seconds
```

### If Tests Fail: Check These

1. **Connection refused on localhost:8080**
   - Frontend not running
   - Fix: `./start.sh`

2. **Login timeout**
   - Backend not responding
   - Fix: Check port 8000, restart with `./start.sh`

3. **Pachca notifications not showing**
   - Backend env vars not set
   - Fix: Export variables before starting:
     ```bash
     export PACHCA_FORUM_API_TOKEN="Zeh9bxonciy0FMdasuNFJuxw-ExVRFzev856Xof8nM0"
     export PACHCA_FORUM_CHANNEL_ID="651412"
     ./start.sh
     ```

4. **Messages not appearing**
   - WebSocket connection issue
   - Fix: Check browser console for errors, restart servers

---

## 6. Verify Pachca Integration

### After tests run, check backend logs:
```bash
# In another terminal
tail -f backend.log | grep -i pachca

# Should show:
# INFO: Successfully sent Pachca forum notification: [Forum] Mathematics: Teacher Name → Student Name: Hello...
```

### What happens:
1. User posts message in forum chat
2. Django signal triggers `post_save` on Message
3. `PachcaService.notify_new_forum_message()` called
4. HTTP POST sent to Pachca API
5. Message appears in configured Pachca channel

---

## 7. Screenshots & Artifacts

### Screenshots generated during testing
```
/tmp/teacher-forum-loaded.png
/tmp/teacher-new-chat-button.png
/tmp/teacher-message-posted.png
/tmp/student-forum-loaded.png
/tmp/student-reply-posted.png
/tmp/realtime-teacher-view.png
/tmp/realtime-student-view.png
/tmp/forum-desktop-1920x1080.png
/tmp/forum-tablet-768x1024.png
/tmp/forum-mobile-375x667.png
... and more
```

### View test report
```bash
npx playwright show-report
# Opens HTML report in browser
```

---

## 8. Test Users (Auto-created)

| Role | Email | Password |
|------|-------|----------|
| Teacher | teacher@test.com | TestPass123! |
| Student | student@test.com | TestPass123! |
| Tutor | tutor@test.com | TestPass123! |
| Parent | parent@test.com | TestPass123! |
| Admin | admin@test.com | TestPass123! |

(No manual user creation needed - fixtures handle it)

---

## 9. Key Test Verifications

✅ **Message Posting**
- Teacher posts message in forum
- Student sees message in real-time
- Message appears in chat list

✅ **Real-Time WebSocket**
- Messages delivered without refresh
- Two-tab synchronization works
- WebSocket frames exchanged

✅ **Pachca Notifications**
- Notification sent on message creation
- Format: `[Forum] Subject: Sender → Recipient: Message`
- Retry logic works on failures

✅ **Responsive Design**
- Desktop view: 1920x1080 ✓
- Tablet view: 768x1024 ✓
- Mobile view: 375x667 ✓

✅ **Error Handling**
- Network latency (500ms) handled
- Console errors detected
- Graceful failure (no crashes)

✅ **All User Roles**
- Student: Sends/receives messages
- Teacher: Creates chats, posts messages
- Tutor: Can access forum
- Parent: Can access forum

---

## 10. Performance Expectations

| Item | Time |
|------|------|
| Single test | 200-1000ms |
| Full suite (serial) | 2-3 minutes |
| Full suite (parallel, 3 workers) | 30-60 seconds |
| Screenshot capture | +30-50ms per test |
| Video recording | +50-100ms per test |

---

## 11. CI/CD Integration

### Add to GitHub Actions
```yaml
- name: Run Forum Pachca E2E Tests
  run: |
    cd frontend
    npx playwright test tests/e2e/forum-with-pachca.spec.ts

- name: Upload Test Results
  if: always()
  uses: actions/upload-artifact@v2
  with:
    name: test-results
    path: frontend/test-results/
```

### Run locally before pushing
```bash
./start.sh  # Terminal 1
cd frontend
npx playwright test tests/e2e/forum-with-pachca.spec.ts  # Terminal 2
```

---

## 12. Troubleshooting Checklist

Before running tests, verify:

- [ ] Docker or local services running
- [ ] Backend on port 8000 (ASGI/Daphne)
- [ ] Frontend on port 8080 (Vite)
- [ ] Test database created
- [ ] Test users can be created
- [ ] Pachca env vars set (optional, but required for Pachca tests)
- [ ] WebSocket support enabled in Django
- [ ] CORS headers configured correctly

Quick check:
```bash
# Terminal 1
curl -I http://localhost:8000/api/

# Terminal 2
curl -I http://localhost:8080/

# Both should return 200/CORS headers
```

---

## 13. Documentation

For more detailed information:
- **Main Report:** `TEST_EXECUTION_REPORT_T011.md`
- **Deliverables:** `T011_DELIVERABLES.md`
- **Test File:** `frontend/tests/e2e/forum-with-pachca.spec.ts`

---

## 14. Support

### Common Questions

**Q: How do I run just one test?**
```bash
npx playwright test tests/e2e/forum-with-pachca.spec.ts -g "T011.3"
```

**Q: How do I see the browser while testing?**
```bash
npx playwright test tests/e2e/forum-with-pachca.spec.ts --headed --browser=chromium
```

**Q: How do I debug a failing test?**
```bash
npx playwright test tests/e2e/forum-with-pachca.spec.ts -g "T011.3" --debug
# Opens browser with debugger, step through code
```

**Q: Where are screenshots saved?**
```bash
# When tests run:
/tmp/forum-*.png

# In HTML report:
frontend/test-results/
```

**Q: How do I check Pachca notifications?**
```bash
# Check backend logs:
tail -f backend.log | grep -i pachca

# Or login to Pachca channel 651412 and look for messages
```

---

## 15. Success Criteria

Your tests are working correctly when:

1. ✅ All 17+ tests pass
2. ✅ No critical console errors
3. ✅ WebSocket connects successfully
4. ✅ Messages appear in real-time
5. ✅ Screenshots show correct UI state
6. ✅ Backend logs show Pachca notifications sent
7. ✅ Responsive layouts look correct
8. ✅ Test execution completes in 30-60 seconds

---

## Next Steps

1. **Run the tests now:**
   ```bash
   ./start.sh &
   cd frontend
   npx playwright test tests/e2e/forum-with-pachca.spec.ts
   ```

2. **View results:**
   ```bash
   npx playwright show-report
   ```

3. **Check Pachca in logs:**
   ```bash
   grep "Pachca" backend.log
   ```

4. **Fix any issues and re-run:**
   ```bash
   npx playwright test tests/e2e/forum-with-pachca.spec.ts --headed
   ```

---

**Happy Testing!** 🚀

---

**Created:** 2025-12-15
**Framework:** Playwright v1.40+
**Test Cases:** 17+
**Estimated Runtime:** 30-60 seconds
