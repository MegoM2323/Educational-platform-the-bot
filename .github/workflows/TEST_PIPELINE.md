# CI Test Pipeline Documentation

## Overview

The test pipeline (`test.yml`) is a comprehensive CI/CD workflow that executes all testing phases for the THE_BOT platform, including backend unit/integration tests, frontend unit tests, E2E tests with Playwright, and coverage analysis.

## Trigger Events

The test pipeline is triggered by:

1. **Workflow Dependency**: Runs after successful `build.yml` completion
2. **Pull Requests**: On PRs to `main` and `develop` branches
3. **Push**: On commits to `main` and `develop` branches
4. **Manual Trigger**: Via `workflow_dispatch` (Actions tab)

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: Setup Test Environment                                 │
│ └─ Generate cache keys, detect file changes                      │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 2: Backend Unit Tests (Parallel)                          │
│ └─ Run pytest on unit tests, generate coverage                  │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 3: Backend Integration Tests (Parallel)                   │
│ └─ Run pytest on integration tests with PostgreSQL              │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 4: Frontend Unit Tests                                     │
│ └─ Run Vitest with coverage reports                             │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 5: Coverage Analysis & Comparison                         │
│ └─ Merge reports, upload to codecov.io, generate badges        │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 6: E2E Tests (Playwright) - Conditional                   │
│ └─ Run Playwright tests if files changed or manual trigger      │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 7: Test Results Summary & PR Comment                      │
│ └─ Parse results, generate report, comment on PR                │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 8: Coverage Threshold Check                               │
│ └─ Verify coverage meets minimum requirements                   │
└─────────────────────────────────────────────────────────────────┘
```

## Phases Detailed

### Phase 1: Setup Test Environment
- Generates cache keys for Python and Node dependencies
- Detects file changes to conditionally run E2E tests
- Outputs cache keys for reuse in other jobs

**Outputs**:
- `backend_python_cache_key`: Cache key for Python dependencies
- `frontend_node_cache_key`: Cache key for Node dependencies
- `run_e2e`: Boolean indicating if E2E tests should run

### Phase 2: Backend Unit Tests
**Duration**: ~30 minutes

- **Dependencies**: PostgreSQL 15, Redis 7
- **Framework**: pytest
- **Test Markers**: `@pytest.mark.unit`

**Coverage**:
- `accounts`, `materials`, `chat`, `payments`, `core`, `scheduling`, `assignments`, `reports`, `notifications`, `knowledge_graph`

**Outputs**:
- `junit-backend-unit.xml` (JUnit format for integration)
- `backend-coverage.xml` (Cobertura format for codecov)
- `backend-html/` (HTML coverage report)

**Parallel Execution**: `-n auto` (uses pytest-xdist)

**Example Test**:
```bash
cd backend
ENVIRONMENT=test pytest tests/ -m unit -v --cov --cov-report=xml
```

### Phase 3: Backend Integration Tests
**Duration**: ~45 minutes

- **Dependencies**: PostgreSQL 15, Redis 7
- **Framework**: pytest
- **Test Markers**: `@pytest.mark.integration`

**Coverage**: Same modules as unit tests

**Outputs**:
- `junit-backend-integration.xml`
- `backend-integration-coverage.xml`
- `backend-integration-html/`

**Parallel Execution**: `-n auto`

**Example Test**:
```bash
cd backend
ENVIRONMENT=test pytest tests/ -m integration -v --cov --cov-report=xml
```

### Phase 4: Frontend Unit Tests
**Duration**: ~30 minutes

- **Framework**: Vitest
- **Coverage**: All TypeScript/React components

**Commands**:
```bash
cd frontend
npm run test:coverage  # Runs Vitest with coverage
```

**Outputs**:
- `vitest-results.json`
- `coverage/` (HTML coverage report)

**Coverage Thresholds**:
- Statements: 80%
- Branches: 75%
- Functions: 80%
- Lines: 80%

### Phase 5: Coverage Analysis & Comparison
**Duration**: ~15 minutes

- **Merges**: Combines backend and frontend coverage reports
- **Badges**: Generates coverage percentage badge with color coding
- **Upload**: Sends reports to codecov.io (if token available)
- **Artifacts**: Uploads merged reports for review

**Coverage Color Coding**:
- Green: >= 80%
- Yellow: 60-79%
- Red: < 60%

### Phase 6: E2E Tests with Playwright
**Duration**: ~60 minutes (conditional)

**Triggers**:
- Changes to `frontend/tests/e2e/` or `frontend/src/`
- Changes to authentication code (`backend/accounts/`)
- Changes to chat code (`backend/chat/`)
- Manual trigger via `workflow_dispatch`

**Browsers Tested**:
- Chromium (Desktop)
- Firefox (Desktop)
- Mobile Chrome

**Configuration**:
- Parallel: 1 worker (sequential execution)
- Retries: 2 on CI
- Timeout: 30 seconds per action
- Screenshots: On failure
- Videos: On failure

**Setup Steps**:
1. Install dependencies
2. Run Django migrations
3. Create test data (student & teacher users)
4. Start Django backend server
5. Start Vite frontend dev server
6. Wait for services to be ready
7. Run Playwright tests

**Test Data**:
```python
Username: test_student, Password: TestPass123!
Username: test_teacher, Password: TestPass123!
```

**Outputs**:
- `junit-*.xml` (JUnit format)
- `results.json` (JSON format)
- `test-results/` (HTML report)
- Screenshots and videos on failure

### Phase 7: Test Results Summary & PR Comment
**Duration**: ~15 minutes

**Functionality**:
1. Downloads all test artifacts
2. Parses JUnit XML files to count tests
3. Generates test summary report
4. Comments on PR with results (if PR event)
5. Creates GitHub Actions step summary

**PR Comment Example**:
```markdown
## Test Pipeline Results ✅

### Backend Tests
- Unit Tests: 450 executed
- Integration Tests: 280 executed

### Frontend Tests
- Unit Tests: Executed with coverage

### Coverage Analysis
- Backend coverage report available in artifacts
- Frontend coverage report available in artifacts

[View full test report](...)
```

### Phase 8: Coverage Threshold Check
**Duration**: ~10 minutes

**Validation**:
- Parses `backend-coverage.xml`
- Extracts line coverage rate
- Fails if coverage < 60% (minimum threshold)

**Coverage Levels**:
- Success: >= 60%
- Warning: 40-59% (still passes but logs warning)
- Failure: < 40% (build fails)

## Services Used

### Backend Services
- **PostgreSQL 15**: Test database
  - Database: `test_thebot`
  - User: `postgres`
  - Port: 5432

- **Redis 7**: Cache and messaging
  - Port: 6379

### Frontend Services
- **Vite Dev Server**: Frontend development server
  - Port: 5173 (default)
  - Base URL: http://localhost:5173

### Backend API
- **Django Runserver**: REST API and WebSocket server
  - Port: 8000 (default)
  - Base URL: http://localhost:8000

## Environment Variables

### Backend Testing
```bash
ENVIRONMENT=test                # Use test settings
DATABASE_URL=postgresql://...   # PostgreSQL test database
REDIS_URL=redis://localhost:6379/0
DEBUG=False                     # Production-like testing
SECRET_KEY=test-secret-key      # For session encryption
```

### Frontend Testing
```bash
CI=true                         # CI mode for test runners
BASE_URL=http://localhost:5173  # Base URL for Playwright
```

## Artifacts Generated

### Test Results
- `backend-unit-test-results/junit-backend-unit.xml`
- `backend-integration-test-results/junit-backend-integration.xml`
- `frontend-unit-test-results/junit-frontend-unit.xml`
- `e2e-test-results/` (Playwright JSON and HTML reports)

### Coverage Reports
- `backend-coverage-report/` (HTML + XML)
  - `backend-html/index.html` - Main report
  - `backend-coverage.xml` - Cobertura format
- `frontend-coverage-report/` (HTML)
  - `coverage/index.html` - Main report
- `merged-coverage-reports/` (Combined reports)

### Reports
- `test-summary/TEST_SUMMARY.md`
- `playwright-html-report/` (E2E test details)

## Accessing Results

### During Workflow Execution
1. Go to **Actions** tab in GitHub
2. Click on **Test Pipeline** workflow
3. Click on the specific run
4. View real-time logs for each job

### After Workflow Completion
1. Go to **Actions** → **Test Pipeline** → **Summary**
2. Scroll to **Artifacts** section
3. Download desired artifact (ZIP format)
4. Extract and view

### HTML Reports
```
backend-coverage-report/
  ├── backend-html/index.html      # Backend coverage
  └── backend-integration-html/index.html

frontend-coverage-report/
  ├── coverage/index.html          # Frontend coverage

playwright-html-report/
  └── index.html                   # E2E test details
```

### Opening HTML Reports Locally
```bash
# Backend unit coverage
open backend-coverage-report/backend-html/index.html

# Frontend coverage
open frontend-coverage-report/coverage/index.html

# Playwright E2E report
open playwright-html-report/index.html
```

## Caching Strategy

### Python Dependencies
- **Cache Key**: `python-3.10-{hash(requirements.txt)}`
- **Path**: `~/.cache/pip`
- **Restore Keys**: Falls back to any Python 3.10 cache

### Node Dependencies
- **Cache Key**: `node-18-{hash(package-lock.json)}`
- **Path**: `~/.npm` and `frontend/node_modules`
- **Restore Keys**: Falls back to any Node 18 cache

**Benefits**:
- Reduces install time by 60-70%
- Stable builds (locked versions)
- Automatic cache invalidation on dependency changes

## Parallel Execution

### Jobs Running in Parallel
1. Backend unit tests
2. Backend integration tests
3. Frontend unit tests
4. (Wait for above to complete)
5. Coverage analysis
6. E2E tests (if triggered)
7. (Wait for all to complete)
8. Test summary
9. Coverage check

### Within-Job Parallelization
- **Backend tests**: `pytest -n auto` (uses all CPU cores)
- **Frontend tests**: Single worker (Vitest default)
- **E2E tests**: 1 worker (Playwright sequential for stability)

## Failure Handling

### Test Failures
- Job continues to completion
- Coverage reports generated even if tests fail
- PR comment posted with results
- Build marked as failed in GitHub checks

### Service Failures
- Health checks every 10 seconds
- Max 5 retries before timeout
- Clear error messages in logs

### Coverage Threshold Failures
- Workflow continues (warning level)
- Logged in step summary
- Alerts team to coverage regression

## Debugging Failed Tests

### View Logs
1. Go to **Actions** → **Test Pipeline** → Failed run
2. Click on failed job
3. Expand failed step
4. Review error messages and stack traces

### Download Artifacts
1. Scroll to **Artifacts** section
2. Download test results (XML files)
3. Parse with IDE or test result viewer:
   ```bash
   # View with XML viewer
   cat junit-backend-unit.xml | xmllint --format -
   ```

### Playwright Failures
1. Download `playwright-html-report`
2. Extract: `unzip playwright-html-report.zip`
3. Open: `open index.html`
4. View screenshots and video recordings of failures

### Local Reproduction
```bash
# Run failed test locally
cd backend
ENVIRONMENT=test pytest tests/path/to/test.py::test_name -vv

# With coverage
ENVIRONMENT=test pytest tests/ -m unit --cov --cov-report=html
```

## Performance Metrics

### Typical Execution Times
- **Phase 1** (Setup): 2 minutes
- **Phase 2** (Backend unit tests): 20-30 minutes
- **Phase 3** (Backend integration tests): 30-45 minutes
- **Phase 4** (Frontend unit tests): 15-25 minutes
- **Phase 5** (Coverage analysis): 5-10 minutes
- **Phase 6** (E2E tests): 30-60 minutes (conditional)
- **Phase 7** (Summary): 5-10 minutes
- **Phase 8** (Coverage check): 2-5 minutes

**Total without E2E**: 80-130 minutes (1.5-2 hours)
**Total with E2E**: 110-190 minutes (2-3 hours)

### Optimization Tips
1. Use cache hits for faster dependency installation
2. Parallelize unit tests with `-n auto`
3. Conditional E2E tests (only on relevant changes)
4. Docker image caching from previous builds

## Integration with Other Workflows

### Depends On
- **build.yml**: Images built before tests run

### Triggers
- **deploy-staging.yml**: Deploys after tests pass
- **deploy-production.yml**: Requires successful tests

### PR Checks
- Tests must pass for PR merge (GitHub branch protection)
- Coverage reports comment added to PR
- Test results visible in PR checks section

## Common Issues & Solutions

### Issue: Tests timeout
**Solution**:
- Increase `--timeout=30` in pytest command
- Check database connection (PostgreSQL service health)
- Check Redis connectivity

### Issue: Coverage not increasing
**Solution**:
- Verify pytest is collecting correct modules
- Check `--cov=module_name` flags
- Ensure test files are in `tests/` directory

### Issue: Playwright tests fail
**Solution**:
- Verify backend server is running on port 8000
- Check frontend dev server on port 5173
- Review screenshots and videos in artifacts
- Run locally with `--headed --debug` flags

### Issue: Cache not being used
**Solution**:
- Verify `package-lock.json` or `requirements.txt` hash
- Clear cache manually if dependencies changed
- Check Actions settings for cache retention policy

## Recommendations

### Best Practices
1. Keep test database separate from production
2. Use markers for test organization
3. Run coverage analysis regularly
4. Monitor coverage trends over time
5. Archive old test results for comparison

### Team Guidelines
1. All tests must pass before merge
2. Coverage should not decrease (>5% allowed)
3. E2E tests run on main branches
4. PR comments with test results
5. Monitor test execution times

### Future Improvements
1. Parallel E2E tests with multiple workers
2. Test result trending dashboard
3. Slack notifications on failures
4. Automated coverage reports
5. Performance regression detection

## Support & Resources

### Documentation
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Vitest Documentation](https://vitest.dev/)
- [Playwright Documentation](https://playwright.dev/)

### Testing Guidelines
- Backend: See `backend/README_TESTS.md`
- Frontend: See `frontend/README_TESTS.md`

### Contact
For issues or questions about the test pipeline, contact the DevOps team or open an issue in the repository.
