# Test Pipeline Quick Reference

## TL;DR

The test pipeline runs automatically on every push and PR. It tests backend (unit + integration), frontend (unit), and optionally E2E tests. All results appear in the PR as a comment.

## Trigger Events

| Event | Behavior |
|-------|----------|
| Push to `main`/`develop` | Auto-run all tests |
| Create/Update PR | Auto-run all tests |
| Manual dispatch | Via Actions tab |
| Build pipeline completes | Auto-run tests |

## Where to Find Results

### In GitHub
1. Go to **Actions** tab
2. Select **Test Pipeline** workflow
3. Click latest run
4. View results in real-time OR download artifacts

### In Pull Request
- Automatic comment with test summary
- Check marks next to test phases
- Link to full report in Actions

### Artifacts to Download
```
backend-coverage-report/          # Backend code coverage
frontend-coverage-report/         # Frontend code coverage
backend-unit-test-results/        # Unit test JUnit XML
backend-integration-test-results/ # Integration test JUnit XML
e2e-test-results/                 # Playwright test results
playwright-html-report/           # Detailed E2E results
```

## Quick Commands (Local)

```bash
# Run all tests locally
make test

# Run only unit tests
make test-unit

# Run coverage reports
make coverage

# Run E2E tests
make test-e2e

# View coverage report (HTML)
open backend/htmlcov/index.html
open frontend/coverage/index.html
```

## Pipeline Phases

| # | Phase | Duration | Status |
|---|-------|----------|--------|
| 1 | Setup | 2 min | Always |
| 2 | Backend Unit Tests | 20-30 min | Always |
| 3 | Backend Integration Tests | 30-45 min | Always |
| 4 | Frontend Unit Tests | 15-25 min | Always |
| 5 | Coverage Analysis | 5-10 min | Always |
| 6 | E2E Tests | 30-60 min | Conditional |
| 7 | Test Summary | 5-10 min | Always |
| 8 | Coverage Check | 2-5 min | Always |

**Total time**: 80-130 min (without E2E) / 110-190 min (with E2E)

## Test Coverage

**Backend Modules**:
- accounts, materials, chat, payments, core, scheduling, assignments, reports, notifications, knowledge_graph

**Frontend**: All React components

**E2E**: Login flows, messaging, dashboards, admin panel (all browsers)

## Coverage Requirements

| Level | Requirement | Status |
|-------|-------------|--------|
| Minimum | >= 60% | Required to pass |
| Target | >= 80% | Recommended |
| Excellent | >= 90% | Gold standard |

## Understanding Results

### All Tests Passed ✅
- No action needed
- Ready to merge (if PR)

### Coverage Decreased ❌
- Check what code changed
- Add tests for new code
- Aim for >= 80% coverage

### E2E Tests Failed
- Check Playwright HTML report
- View screenshots of failure
- Replay video recording
- Run locally with `--headed` flag

### Database Error
- Check PostgreSQL service health
- Verify `DATABASE_URL` in logs
- Review migration output

## Common Problems & Fixes

| Problem | Fix |
|---------|-----|
| "pytest not found" | Check requirements.txt has pytest |
| Coverage too low | Add tests to new code |
| E2E timeout | Increase wait time or check services |
| Database locked | Clear test database cache |
| Flaky E2E test | Increase retry count or add wait |

## Service URLs (For E2E Tests)

| Service | URL | Port |
|---------|-----|------|
| Backend API | http://localhost:8000 | 8000 |
| Frontend | http://localhost:5173 | 5173 |
| PostgreSQL | localhost | 5432 |
| Redis | localhost | 6379 |

## Important Files

| File | Purpose |
|------|---------|
| `.github/workflows/test.yml` | Main workflow definition |
| `backend/pytest.ini` | Backend test config |
| `frontend/vitest.config.ts` | Frontend test config |
| `frontend/playwright.config.ts` | E2E test config |
| `Makefile` | Local test commands |

## Test Data

### Default test users (auto-created in E2E):
```
Username: test_student
Email: student@test.com
Password: TestPass123!

Username: test_teacher
Email: teacher@test.com
Password: TestPass123!
```

## Environment Variables

```bash
# Backend tests require
ENVIRONMENT=test
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=...
DEBUG=False

# E2E tests require
BASE_URL=http://localhost:5173
CI=true (in GitHub Actions)
```

## CI/CD Status Badges

### PR Checks
- Green checkmark = All tests passed
- Red X = Tests failed
- Yellow dot = Tests running

### Required for Merge?
Check your branch protection rules in GitHub Settings

## Accessing Detailed Reports

### Backend Coverage HTML
```bash
# Download artifact
unzip backend-coverage-report.zip
open backend-html/index.html
```

### Frontend Coverage HTML
```bash
# Download artifact
unzip frontend-coverage-report.zip
open coverage/index.html
```

### E2E Test Report
```bash
# Download artifact
unzip playwright-html-report.zip
open index.html
```

### JUnit XML Results
```bash
# View in IDE
# VS Code: Test Explorer extension
# PyCharm: Built-in test runner
# Or parse: cat junit-backend-unit.xml
```

## Advanced Usage

### Run Specific Test Locally
```bash
cd backend
ENVIRONMENT=test pytest tests/unit/accounts/test_login.py::test_user_login -v
```

### Run E2E Tests with Video
```bash
cd frontend
npx playwright test --record
```

### Debug E2E Test
```bash
npx playwright test --debug --headed
```

### Generate Coverage Badge
```bash
make coverage
# Check badge color in report
```

## Performance Tips

1. **Cache hits**: Don't change requirements.txt without reason
2. **Parallel tests**: Backend uses `-n auto` automatically
3. **E2E optimization**: Runs only on file changes (not every commit)
4. **Dependencies**: Keep them updated to maintain build speed

## Security Notes

- Test database is isolated (auto-cleaned)
- No production data used
- Secrets managed via GitHub Secrets
- All credentials in environment variables

## Getting Help

1. **Check logs**: Click on failed job in Actions
2. **Review artifacts**: Download test reports
3. **Documentation**: See `TEST_PIPELINE.md` for details
4. **Local test**: Reproduce issue locally with same commands
5. **Ask team**: Contact DevOps or engineering lead

## Key Metrics to Monitor

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Coverage | >= 80% | 60-79% | < 60% |
| Test Pass Rate | 100% | >= 95% | < 95% |
| Execution Time | < 100 min | 100-130 min | > 130 min |
| Flaky Tests | 0 | 1-3 | > 3 |

## Next Steps

1. **First time setup**: Run locally with `make test`
2. **Before push**: Check coverage doesn't drop
3. **After push**: Monitor GitHub Actions
4. **On failure**: Check artifacts and reproduce locally
5. **Regularly**: Update dependencies, add tests, optimize

---

**Last Updated**: December 27, 2025
**Status**: Ready for Production
**Version**: 1.0.0
