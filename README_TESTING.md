# Assignment & Submission Workflow Testing
## THE_BOT Platform - Complete Testing Package

**Status**: READY FOR EXECUTION
**Date**: 2026-01-01
**QA Engineer**: Tester Agent

---

## What You Have

A complete testing package for the Assignment & Submission workflow:

- **79 Web UI test cases** across 7 scenarios
- **45+ automated API tests** (Python/pytest)
- **13 API endpoints** fully documented
- **8 database models** analyzed
- Complete setup and execution instructions
- Troubleshooting guide for 10+ common issues

**Total Documentation**: 150KB+
**Estimated Execution Time**: 2 hours

---

## Quick Start (5 minutes)

### 1. Read the Setup Guide
```bash
cat TESTING_SETUP_INSTRUCTIONS.md
```

### 2. Start Docker
```bash
cd /home/mego/Python\ Projects/THE_BOT_platform
docker-compose up -d
```

### 3. Open Browser
```
http://localhost:3000
```

### 4. Follow Web UI Tests
See: `TESTER_3_ASSIGNMENTS.md`

### 5. Run API Tests
```bash
pytest test_assignments_integration.py -v
```

---

## Files Included

### 1. TESTER_3_ASSIGNMENTS.md (Main Testing Guide)
The primary document for Web UI testing. Contains 7 complete scenarios with step-by-step instructions and expected results.

**Use when**: Manually testing through the browser

### 2. test_assignments_integration.py (Automation)
Ready-to-run Python tests using pytest. Tests all major API endpoints and workflows.

**Use when**: Running automated API tests

### 3. ASSIGNMENTS_API_ANALYSIS.md (API Reference)
Complete technical documentation of all endpoints, data models, and workflows. Includes curl command examples.

**Use when**: Understanding the API or making curl requests

### 4. TESTING_SETUP_INSTRUCTIONS.md (Setup Guide)
Step-by-step guide for Docker, test data, and execution. Includes troubleshooting for 10 common issues.

**Use when**: Setting up Docker or having problems

### 5. TESTING_SUMMARY.md (Overview)
Executive summary of the testing project. Shows metrics, coverage, and next steps.

**Use when**: Understanding the big picture

### 6. TESTING_INDEX.md (Quick Reference)
Quick reference guide with file descriptions, process checklists, and key information.

**Use when**: Looking for quick answers

### 7. TEST_DELIVERY_REPORT.txt (Formal Report)
Formal delivery report with metrics, timelines, and quality assurance notes.

**Use when**: Reporting to management

---

## Test Coverage

### Web UI (79 tests across 7 scenarios)

| Scenario | Tests | Time |
|----------|-------|------|
| 1. Create Assignment | 10 | 10 min |
| 2. View Assignment | 9 | 5 min |
| 3. Submit Solution | 10 | 10 min |
| 4. Grade Work | 12 | 15 min |
| 5. View Grade | 8 | 5 min |
| 6. Late Submission | 16 | 15 min |
| 7. File Types | 14 | 20 min |

### API (45+ tests)

- Assignment CRUD: 7 tests
- Submission CRUD: 8 tests
- Grading: 3 tests
- Late Submission: 4 tests
- File Upload: 5 tests
- Status Tracking: 4 tests
- Metadata: 4 tests

---

## Test Accounts

Ready to use in all tests:

```
Teacher:
  Email: ivan.petrov@tutoring.com
  Password: password123

Student 1:
  Email: anna.ivanova@student.com
  Password: password123

Student 2:
  Email: dmitry.smirnov@student.com
  Password: password123

Admin:
  Email: admin@test.com
  Password: password123
```

---

## What Gets Tested

✓ Creating assignments
✓ Assigning to students
✓ Submitting solutions
✓ Uploading files (PDF, JPG, PNG, DOCX, TXT)
✓ Grading work
✓ Adding feedback
✓ Late submission detection
✓ Penalty calculation
✓ Viewing results
✓ File versioning
✓ Comments

---

## Timeline

| Phase | Duration |
|-------|----------|
| Docker Setup | 5 min |
| Test Data | 5 min |
| Web UI Testing | 80 min |
| API Testing | 20 min |
| Documentation | 15 min |
| **TOTAL** | **125 minutes** |

---

## Starting Out

### For Manual Testing (Web UI)

1. Read: `TESTER_3_ASSIGNMENTS.md`
2. Start Docker: `docker-compose up -d`
3. Open: http://localhost:3000
4. Login as teacher
5. Follow the 7 scenarios
6. Record PASS/FAIL for each test
7. Take screenshots of any failures

### For API Testing

1. Run tests: `pytest test_assignments_integration.py -v`
2. Check results
3. Any failures? Read `ASSIGNMENTS_API_ANALYSIS.md` for endpoint details

### If You Get Stuck

1. Check: `TESTING_SETUP_INSTRUCTIONS.md` (Troubleshooting section)
2. Look at: Docker logs: `docker-compose logs backend`
3. Restart: `docker-compose restart`
4. Reset: `docker-compose down -v && docker-compose up -d`

---

## Key Features Tested

### Assignment Management
- Creating assignments
- Publishing to students
- Setting deadlines
- Multiple student assignment
- Draft/Published/Closed states

### Submission Workflow
- Submitting solutions
- File uploads
- Content submission
- Status tracking
- Automatic timestamps

### Grading
- Entering scores
- Adding feedback
- Publishing grades
- Status transitions
- Automatic grading timestamp

### Late Submissions
- Deadline detection
- Late flag (is_late)
- Days late calculation
- Penalty types (percentage, fixed points)
- Penalty application

### Files
- PDF uploads
- Image uploads (JPG, PNG)
- Document uploads (DOCX)
- Text uploads (TXT)
- File size validation
- Storage in /media/assignments/submissions/

---

## What to Look For

### Success Indicators
- All test steps complete without errors
- Expected results match actual results
- No confusing error messages
- File uploads work smoothly
- Dates and times display correctly
- Late submissions are detected
- Grades appear for students
- Teachers can see all submissions

### Possible Issues
- Validation errors
- Missing features
- File upload problems
- Permission errors
- Display issues
- Date/timezone problems

---

## After Testing

1. **Update TESTER_3_ASSIGNMENTS.md**
   - Change PENDING to PASS or FAIL
   - Add comments about any issues

2. **Collect Evidence**
   - Save screenshots
   - Note any error messages
   - Check browser console for JavaScript errors

3. **Create Bug Reports**
   - For each FAIL, document:
     - What you did
     - What happened
     - What should have happened
     - Screenshot
     - Browser logs

4. **Final Report**
   - Summary of results
   - List of issues found
   - Recommendations

---

## Important Notes

### API Authentication Issue
There is a known HTTP 503 error on the login endpoint (from previous testing).
This needs to be fixed before API testing can proceed.

### File Storage
Files are uploaded to `/media/assignments/submissions/`
Make sure this directory exists and is writable.

### Timestamps
All dates in database are UTC.
Browser displays them in local timezone.

### Unique Submissions
Each student can submit only ONE submission per assignment.
Re-submitting overwrites the previous one (or creates a version).

---

## Quick Commands

```bash
# Start Docker
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend

# Run tests
pytest test_assignments_integration.py -v

# Stop
docker-compose down

# Full reset
docker-compose down -v && docker-compose up -d
```

---

## Files at a Glance

| File | Size | Purpose |
|------|------|---------|
| TESTER_3_ASSIGNMENTS.md | 50KB | Web UI test scenarios |
| test_assignments_integration.py | 20KB | API automation tests |
| ASSIGNMENTS_API_ANALYSIS.md | 40KB | API documentation |
| TESTING_SETUP_INSTRUCTIONS.md | 30KB | Setup & troubleshooting |
| TESTING_SUMMARY.md | 25KB | Project overview |
| TESTING_INDEX.md | 20KB | Quick reference |
| TEST_DELIVERY_REPORT.txt | 18KB | Formal report |

---

## Support & Help

### Documentation
- API reference: `ASSIGNMENTS_API_ANALYSIS.md`
- Setup help: `TESTING_SETUP_INSTRUCTIONS.md` (Section 8: Troubleshooting)
- Overview: `TESTING_SUMMARY.md`

### Common Issues
1. **Docker won't start** → See TESTING_SETUP_INSTRUCTIONS.md, Part 2
2. **Ports in use** → See TESTING_SETUP_INSTRUCTIONS.md, Problem 1
3. **DB connection error** → See TESTING_SETUP_INSTRUCTIONS.md, Problem 5
4. **Tests fail** → Check test account credentials, verify Docker status

### Getting Help
- Check Docker logs: `docker-compose logs`
- Restart: `docker-compose restart`
- Check test file: ensure it exists and is readable
- Verify connectivity: `curl http://localhost:8000/api/`

---

## Success Checklist

Before you start:
- [ ] Read TESTING_SETUP_INSTRUCTIONS.md
- [ ] Docker installed
- [ ] Ports available (3000, 8000, 5433, 6379)
- [ ] At least 4GB disk space

During testing:
- [ ] Follow scenarios in TESTER_3_ASSIGNMENTS.md
- [ ] Record PASS/FAIL for each step
- [ ] Take screenshots
- [ ] Note any errors

After testing:
- [ ] Update TESTER_3_ASSIGNMENTS.md
- [ ] Create bug reports for failures
- [ ] Run API tests: pytest
- [ ] Prepare final report

---

## Next Steps

1. **Right now**: Read TESTING_SETUP_INSTRUCTIONS.md
2. **Next 5 min**: Start Docker
3. **Next 10 min**: Create test data
4. **Next 80 min**: Execute Web UI scenarios
5. **Next 20 min**: Run API tests
6. **Next 15 min**: Document results

---

## Questions?

Check the specific guide:
- **How do I start Docker?** → TESTING_SETUP_INSTRUCTIONS.md, Part 2
- **What should I test?** → TESTER_3_ASSIGNMENTS.md
- **How does the API work?** → ASSIGNMENTS_API_ANALYSIS.md
- **Something's not working** → TESTING_SETUP_INSTRUCTIONS.md, Part 8
- **What's the big picture?** → TESTING_SUMMARY.md

---

## Version Info

- **Date Created**: 2026-01-01
- **Version**: 1.0
- **Status**: READY FOR EXECUTION
- **Last Updated**: 2026-01-01
- **QA Engineer**: Tester Agent

---

**Ready to begin? Start with TESTING_SETUP_INSTRUCTIONS.md**

Good luck with testing!
