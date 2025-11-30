# Test Data Generation Guide

This document describes how to generate and manage test data for THE BOT Platform.

## Quick Start

Generate complete test dataset with a single command:

```bash
cd backend
python manage.py reset_all_test_data
```

Clear old data and regenerate from scratch:

```bash
cd backend
python manage.py reset_all_test_data --clear
```

Verbose output for debugging:

```bash
cd backend
python manage.py reset_all_test_data --clear --verbose
```

## Test Credentials

After running the script, use these credentials to login:

| Role | Email | Password |
|------|-------|----------|
| **Student** | student@test.com | TestPass123! |
| **Student 2** | student2@test.com | TestPass123! |
| **Teacher** | teacher@test.com | TestPass123! |
| **Teacher 2** | teacher2@test.com | TestPass123! |
| **Tutor** | tutor@test.com | TestPass123! |
| **Parent** | parent@test.com | TestPass123! |
| **Admin** | admin@test.com | TestPass123! |

## What Gets Created

### Users & Profiles
- 7 test users with all roles (Student, Teacher, Tutor, Parent, Admin)
- User profiles for each role (StudentProfile, TeacherProfile, ParentProfile)
- TutorProfile for tutor user

### Academic Structure
- 8 subjects (Mathematics, Physics, Chemistry, Biology, History, Russian, English, Literature)
- 16 teacher-subject associations
- 5 subject enrollments linking students to teachers

### Relationships
- Parent linked to 2 students
- Tutor assigned to both students
- Teachers assigned to multiple subjects

### Learning Materials
- 20 educational materials across subjects
- 13 student submissions on materials
- 15 study plans with 22 attachment files
- 15 assignments with 10 student submissions

### Communication
- 5 chat rooms (student-teacher, student-tutor, tutor-parent, etc.)
- 36 messages across all chat rooms
- 54 notifications for all users

### Reports
- 3 student reports (teacher → tutor)
- 3 teacher weekly reports
- 2 tutor weekly reports (tutor → parent)

## Data Relationships

The test data is created in natural order, mimicking real usage:

```
1. Users & Profiles created
   ↓
2. Tutor links Parent to Students
   ↓
3. Tutor assigns Students to Subjects with Teachers
   ↓
4. Teachers create Materials & Study Plans
   ↓
5. Students submit work on Materials
   ↓
6. Teachers create Assignments & submit grades
   ↓
7. Teachers send Reports to Tutor
   ↓
8. Tutor sends Reports to Parent
   ↓
9. Chat rooms created between all participants
   ↓
10. Notifications generated for all users
```

## Database Cleanup

The `--clear` flag removes old test data but PRESERVES user accounts:

```bash
# Removes but keeps users:
python manage.py reset_all_test_data --clear

# Lists of what gets cleared:
# - Notifications
# - Chat messages and rooms
# - Reports (StudentReport, TeacherWeeklyReport, TutorWeeklyReport)
# - Assignments and submissions
# - Study plans and files
# - Materials and submissions
# - Subject enrollments
# - Teacher-subject assignments
```

## Using Test Data in Development

### Testing API Endpoints

```bash
# 1. Start backend
cd backend
python manage.py runserver

# 2. Generate test data
python manage.py reset_all_test_data --clear

# 3. Test login endpoint
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "student@test.com", "password": "TestPass123!"}'

# 4. Get token from response, use in headers
curl -X GET http://localhost:8000/api/profile/student/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### Testing Frontend

```bash
# 1. Start backend with test data
cd backend
python manage.py runserver

# 2. Start frontend in another terminal
cd frontend
npm start

# 3. Login with any test credentials
# Email: student@test.com
# Password: TestPass123!

# 4. Navigate through dashboards to see test data
```

### Running E2E Tests

```bash
# 1. Generate fresh test data
cd backend
python manage.py reset_all_test_data --clear

# 2. Ensure backend is running
python manage.py runserver

# 3. Run E2E tests
cd frontend
npx playwright test

# View test report
npx playwright show-report
```

## Troubleshooting

### Script Fails with "No module named X"

Make sure you're using the correct Python environment:

```bash
source .venv/bin/activate
cd backend
python manage.py reset_all_test_data
```

### Database Locked Error

The SQLite database can get locked if multiple processes access it. Solution:

```bash
# Ensure no Django processes running
pkill -f "manage.py"

# Then run script
python manage.py reset_all_test_data --clear
```

### Users Already Exist

The script uses `get_or_create()`, so it's safe to run multiple times:

```bash
# This will:
# - Update passwords if users exist
# - Create new profiles if missing
# - Regenerate all test data with --clear
python manage.py reset_all_test_data --clear
```

### Missing PDF Files in Submissions

If PDF files don't display, ensure reportlab is installed:

```bash
pip install reportlab
```

## Command Options

```bash
python manage.py reset_all_test_data [OPTIONS]

Options:
  --clear        Remove old test data before creating new (keeps users)
  --verbose      Show detailed output during creation
  --help         Display help message
```

## Statistics Generated

The script outputs final statistics showing:

- Users and profiles created
- Subjects and teacher assignments
- Subject enrollments
- Learning materials and submissions
- Study plans and files
- Assignments and submissions
- Reports by type
- Chat rooms and messages
- Total notifications

Example output:

```
FINAL STATISTICS
  Users created                   :     0
  User profiles                   :     7
  Subjects                        :     8
  Teacher-subject links           :    16
  Parent-student links            :     2
  Subject enrollments             :     5
  Materials                       :    20
  Material submissions            :    13
  Study plans                     :    15
  Study plan files                :    22
  Assignments                     :    15
  Assignment submissions          :    10
  Student reports                 :     3
  Teacher reports                 :     3
  Tutor reports                   :     2
  Chat rooms                      :     5
  Chat messages                   :    36
  Notifications                   :    54
  ────────────────────────────────
  TOTAL                           :   236
```

## Production Considerations

**DO NOT USE THESE CREDENTIALS IN PRODUCTION**

These test accounts should never exist in production. They use:
- Known passwords (TestPass123!)
- Test email addresses
- Minimal validation for security

For production, use proper authentication (Supabase, OAuth, etc.) and real user management.

## Related Documentation

- [DATABASE_CONFIG.md](./DATABASE_CONFIG.md) - Database setup and modes
- [CLAUDE.md](../CLAUDE.md) - Project overview and architecture
