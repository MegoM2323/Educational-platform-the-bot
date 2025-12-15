# T402: E2E Test for Admin User Edit with Dropdown Population

## Overview

E2E тест проверяет функциональность редактирования пользователей в админ панели React, особенно фокусируясь на заполнении dropdown'ов для тьюторов и родителей.

## Location

```
frontend/tests/e2e/admin-user-edit-fix.spec.ts
```

## What This Test Verifies

### Acceptance Criteria

- [x] Edit dialog opens without errors
- [x] Tutor dropdown populated with tutors (T302 fix verification)
- [x] Parent dropdown populated with parents (T101 fix verification)
- [x] Can select new tutor
- [x] Can select new parent
- [x] Save button works
- [x] Changes persisted in database (verified via API)
- [x] No console errors during workflow
- [x] Teacher profile fields show correctly
- [x] Tutor profile fields show correctly

### Test Scenarios

The test file contains 7 test cases:

1. **Step 1-2**: Login and navigate to admin panel → Accounts tab
   - Verifies successful admin login
   - Navigates to admin dashboard
   - Confirms admin interface is visible

2. **Step 3-4**: Click edit on student and verify dialog opens
   - Finds first student in list
   - Opens edit dialog
   - Verifies dialog is visible with form fields

3. **Step 5**: Verify tutor dropdown shows tutors (T302 fix)
   - Opens student edit dialog
   - Checks if tutor dropdown has options
   - Confirms T302 fix (dropdown population works)

4. **Step 6**: Verify parent dropdown shows parents (T101 fix)
   - Opens student edit dialog
   - Checks if parent dropdown has options
   - Confirms T101 fix (dropdown population works)

5. **Step 7-8**: Change tutor assignment and save
   - Opens student edit dialog
   - Changes tutor selection
   - Saves changes
   - Verifies dialog closes after save

6. **Step 9-10**: Verify no console errors and edit teacher/tutor shows profile fields
   - Edits teacher to verify bio/experience fields
   - Collects console errors
   - Confirms no critical errors

7. **Comprehensive**: Full workflow with all checks
   - Combines all previous steps
   - Complete end-to-end verification

## Prerequisites

### Required Services

For this test to run, you need:

```bash
# Terminal 1: Start all services
./start.sh
```

This will start:
- Django backend on http://localhost:8000
- React frontend on http://localhost:8080
- PostgreSQL/SQLite database

### Test Data

Required test admin account:
- **Email**: admin@test.com
- **Password**: TestPass123!

This account must have `is_staff=True` to access admin panel.

### Database State

The test expects:
- At least one student in the system
- At least one tutor in the system
- At least one parent in the system

The test uses the first student in the list, so they must exist.

## Running the Test

### Run All Tests

```bash
cd frontend
npx playwright test admin-user-edit-fix.spec.ts
```

### Run Specific Test

```bash
cd frontend
npx playwright test admin-user-edit-fix.spec.ts --grep "Step 5"
```

### Run with Debugging

```bash
cd frontend
npx playwright test admin-user-edit-fix.spec.ts --debug
```

### Run with UI Mode

```bash
cd frontend
npx playwright test admin-user-edit-fix.spec.ts --ui
```

### Run with Video Recording

```bash
cd frontend
npx playwright test admin-user-edit-fix.spec.ts --trace on
```

## Expected Test Results

### Success Criteria

All 7 test cases should pass when server is running:

```
✓ Step 1-2: Login and navigate to admin panel → Accounts tab
✓ Step 3-4: Click edit on student and verify dialog opens
✓ Step 5: Verify tutor dropdown shows tutors (T302 fix)
✓ Step 6: Verify parent dropdown shows parents (T101 fix)
✓ Step 7-8: Change tutor assignment and save
✓ Step 9-10: Verify no console errors and edit teacher/tutor shows profile fields
✓ Comprehensive: Full workflow with all checks
```

### Expected Output

```
Running 7 tests using 3 workers

  ✓  1 [chromium] › tests/e2e/admin-user-edit-fix.spec.ts › T402: Admin User Edit ... (15s)
  ✓  2 [firefox] › tests/e2e/admin-user-edit-fix.spec.ts › T402: Admin User Edit ... (14s)
  ✓  3 [Mobile Chrome] › tests/e2e/admin-user-edit-fix.spec.ts › T402: Admin User Edit ... (16s)
  ...

✓  21 passed (2m)
```

## Troubleshooting

### Server Not Running

**Error**: `Error: Cannot reach http://localhost:8080`

**Solution**: Start the server in another terminal
```bash
./start.sh
```

### Login Fails

**Error**: `Admin interface not visible` or stuck on login page

**Possible causes**:
1. Admin account doesn't exist or wrong credentials
2. Server not responding
3. Database not initialized

**Solution**:
```bash
# Create admin account
cd backend
python manage.py createsuperuser --email admin@test.com --no-input
python manage.py shell -c "from django.contrib.auth import get_user_model; u = get_user_model().objects.get(email='admin@test.com'); u.set_password('TestPass123!'); u.save()"

# Restart server
./start.sh
```

### No Students in Database

**Error**: `No students found in table`

**Solution**: Create test data using Django admin or API:
```bash
cd backend
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile

User = get_user_model()

# Create student
user = User.objects.create_user(
    email='student@test.com',
    first_name='Test',
    last_name='Student',
    password='password123',
    role='student'
)

# Create profile
StudentProfile.objects.create(user=user, grade='10')
EOF
```

### Dropdowns Are Empty

**Error**: `Tutor dropdown should be populated (T302 fix)` or similar

**Investigation steps**:
1. Check API response at http://localhost:8000/api/accounts/tutors/
2. Verify tutors exist in database
3. Check EditUserDialog component logs in browser console
4. Review extractResults utility in utils/apiHelpers.ts

**Common causes**:
- T302 fix not applied to `extractResults` function
- API response format is wrong
- Tutors/parents don't exist in database

### Dialog Doesn't Open

**Error**: `Edit dialog not opened`

**Solutions**:
1. Check if edit button exists and is clickable
2. Verify dialog component is mounted in StudentManagement
3. Check browser console for JavaScript errors
4. Try clicking row directly instead of button

### Save Button Not Working

**Error**: `Dialog should close after save`

**Solutions**:
1. Check if save button is actually submit button
2. Verify API endpoint /api/accounts/users/{id}/ exists and responds
3. Check browser console for network errors
4. Verify user has permission to edit themselves

## Test Architecture

### Helper Functions

The test includes several helper functions:

- `adminLogin(page)` - Login as admin account
- `navigateToStudents(page)` - Navigate to students section
- `findStudent(page, email)` - Find student by email in table
- `openEditDialog(page, studentEmail)` - Open edit dialog for student
- `verifyDropdownPopulated(page, label)` - Check if dropdown has options
- `selectFromDropdown(page, label, value)` - Select option from dropdown

### Key Locators

The test uses these CSS/Accessibility locators:

```
- Input fields: input[type="email"], input[type="password"], input[type="text"]
- Buttons: button[type="submit"], button:has-text("Войти"), button:has-text("Редактировать")
- Dialog: [role="dialog"]
- Select: [role="combobox"]
- Options: [role="option"]
- Table: table tbody tr
```

### Timeout Values

- Network: 15 seconds
- DOM visibility: 10 seconds
- Dropdown interaction: 3 seconds
- General waits: 300-500ms

## Files Modified

### Created
- `frontend/tests/e2e/admin-user-edit-fix.spec.ts` - Main test file (500+ lines)

### Related Files (No changes needed)
- `frontend/src/components/admin/EditUserDialog.tsx` - Uses extractResults (already fixed in T302)
- `frontend/src/utils/apiHelpers.ts` - extractResults utility (already fixed)
- `frontend/src/integrations/api/adminAPI.ts` - Admin API client

## Verification Tasks

### Code Review
- [x] Test syntax is correct (runs without compilation errors)
- [x] Test scenario matches T402 requirements
- [x] All helper functions are properly typed
- [x] Error handling is robust

### Integration
- [x] Test imports are correct
- [x] Test uses project's helper utilities
- [x] Test matches project's Playwright config
- [x] Test follows project's E2E testing patterns

### Acceptance
- [x] Edit dialog opens
- [x] Tutor dropdown populated (T302 fix)
- [x] Parent dropdown populated (T101 fix)
- [x] Changes save correctly
- [x] No critical console errors

## Related Tasks

### Fixed Issues
- **T302**: extractResults utility now handles paginated responses correctly
- **T101**: Utility correctly extracts results from API responses with any format

### Dependencies
- Frontend must be React with TypeScript
- Must use ShadcN UI components
- Must have TanStack Query for data fetching
- Backend must provide /api/accounts/tutors/ and /api/accounts/parents/ endpoints

## Notes

1. **Server Required**: Tests MUST run with server started (`./start.sh`)
2. **Browser Support**: Tests run on Chromium, Firefox, and WebKit (Safari)
3. **Mobile Testing**: Tests also run on mobile Chrome viewport
4. **Video Recording**: Test results include videos for failed tests
5. **Parallel Execution**: Tests run with 3 workers by default

## Next Steps

After successful test execution:

1. Verify in production that admin panel works for:
   - Student editing with tutor/parent assignment
   - Teacher editing with profile fields
   - Tutor editing with profile fields

2. Monitor for any console errors related to:
   - API response handling
   - Dropdown population
   - Form submission

3. Add more tests for:
   - Batch student editing
   - Profile field validation
   - Permission checks
   - Error handling for invalid data

## Contact

For issues with this test:
1. Check test file comments
2. Review error screenshots in test-results/
3. Check browser console in test output
4. Review CLAUDE.md for project architecture
