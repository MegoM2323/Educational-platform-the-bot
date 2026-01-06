# Tester Task: Finance & Reports for Tutor Cabinet (T088-T102)

## Session: tutor_cabinet_test_20260107

## Test Users
- Tutor: tutor_test_20260107 (ID: 2186)
- Student: student_test_20260107 (ID: 2189)
- Parent: parent_test_20260107 (ID: 2191)
- Password for all: TestPass123!

## Test Framework Requirements
- Use pytest + Django test client
- Location: /home/mego/Python Projects/THE_BOT_platform/backend/tests/tutor_cabinet/
- Test file name: test_finance_reports_T088_T102.py
- Use conftest.py for fixtures
- Session ID: tutor_cabinet_test_20260107

## Finance Tests (T088-T094)

### T088: View Payments List
**File:** test_finance_reports_T088_T102.py::test_T088_view_payments_list
**API:** GET /api/invoices/tutor/
**Actions:**
- Authenticate as tutor_test_20260107
- Request invoice list with pagination (page=1, limit=10)
- Verify response 200
- Check pagination: page, limit, total, results
- Verify filtering by status parameter
**Expected:** List of invoices with pagination metadata

### T089: Create Invoice
**File:** test_finance_reports_T088_T102.py::test_T089_create_invoice
**API:** POST /api/invoices/tutor/
**Actions:**
- POST invoice data: {amount, due_date, description, student_id}
- Student: student_test_20260107 (ID: 2189)
- Due date: 30 days from now
- Verify response 201 Created
- Check invoice_number auto-generated (format: INV-XXXXX)
- Verify status = 'DRAFT'
**Expected:** Invoice created with metadata

### T090: Send Invoice
**File:** test_finance_reports_T088_T102.py::test_T090_send_invoice
**API:** POST /api/invoices/{id}/send/
**Actions:**
- Create invoice first (use T089 setup)
- POST to /api/invoices/{id}/send/ with recipient: parent_test_20260107
- Verify response 200
- Check status changed to 'SENT'
- Check sent_at timestamp is set
- Verify parent_email in response
**Expected:** Invoice sent, status updated

### T091: Track Invoice Status
**File:** test_finance_reports_T088_T102.py::test_T091_track_status
**API:** GET /api/invoices/{id}/
**Actions:**
- Create and send invoice
- Simulate parent viewing invoice (MOCK: parent_viewed = True, viewed_at = now)
- Simulate payment (status = 'PAID', paid_at = now)
- GET invoice details
- Verify status progression: DRAFT → SENT → VIEWED → PAID
- Verify all timestamps (sent_at, viewed_at, paid_at)
**Expected:** All timestamps and status transitions correct

### T092: Payment History & Statistics
**File:** test_finance_reports_T088_T102.py::test_T092_payment_history
**API:** GET /api/invoices/tutor/statistics/
**Actions:**
- Create 3 invoices: 2 paid, 1 pending
- GET statistics endpoint
- Verify response 200
- Check fields: total_revenue, paid_amount, pending_amount, invoice_count
- Verify payment history list (most recent first)
- Test date range filtering (from_date, to_date)
**Expected:** Statistics with correct calculations

### T093: Dispute Payment
**File:** test_finance_reports_T088_T102.py::test_T093_dispute_payment
**API:** POST /api/invoices/{id}/dispute/
**Actions:**
- Create and mark invoice as paid
- POST dispute data: {reason, comment}
- Verify response 200
- Check status changed to 'DISPUTED'
- Verify dispute_reason stored
- Verify dispute_date set
**Expected:** Dispute created, status changed

### T094: Export Payments
**File:** test_finance_reports_T088_T102.py::test_T094_export_payments
**API:** POST /api/invoices/tutor/export/ or GET with format=csv/excel
**Actions:**
- Create 5 invoices with various statuses
- POST/GET export with format='csv' or 'excel'
- Add date range filters
- Verify response 200 with file download
- Check file format (CSV/Excel)
- Verify data content (invoice_number, amount, status, etc.)
**Expected:** File with all invoices exported correctly

## Reports Tests (T095-T102)

### T095: Student Progress Report
**File:** test_finance_reports_T088_T102.py::test_T095_student_progress
**API:** GET /api/reports/student/{id}/progress/
**Actions:**
- Authenticate as tutor_test_20260107
- GET /api/reports/student/2189/progress/
- Create test data: grades, completed assignments
- Verify response 200
- Check fields: overall_progress, completion_percentage, subjects_performance
- Verify date range filtering
**Expected:** Progress metrics for student

### T096: Activity Report
**File:** test_finance_reports_T088_T102.py::test_T096_activity_report
**API:** GET /api/reports/student/{id}/activity/
**Actions:**
- GET activity report for student 2189
- Create test data: 3 lessons, 5 assignments, grades
- Verify response 200
- Check fields: lessons_count, assignments_completed, assignments_pending, grades_list
- Verify period filtering (last_7_days, last_30_days, last_semester)
**Expected:** Activity summary and breakdown

### T097: Grade Sheet (Ведомость)
**File:** test_finance_reports_T088_T102.py::test_T097_grade_sheet
**API:** GET /api/reports/student/{id}/grades/
**Actions:**
- GET grade sheet for student 2189
- Create grades: Math (90, 85, 95), English (88, 92)
- Verify response 200
- Check fields: subject, assignment_type, grades, average
- Group by subject and assignment type
- Verify average calculation
**Expected:** Grades table with averages

### T098: Attendance Report
**File:** test_finance_reports_T088_T102.py::test_T098_attendance
**API:** GET /api/reports/student/{id}/attendance/
**Actions:**
- GET attendance for student 2189
- Create attendance records: 15 present, 2 absent, 1 late
- Verify response 200
- Check fields: present_count, absent_count, late_count, attendance_percentage
- Verify period filtering
- Calculate percentage: present / (present + absent + late) * 100
**Expected:** Attendance stats with 88.9% attendance

### T099: Performance Analysis
**File:** test_finance_reports_T088_T102.py::test_T099_performance_analysis
**API:** GET /api/reports/student/{id}/performance/
**Actions:**
- GET performance analysis
- Create trend data: grades improving, weak subjects identified
- Verify response 200
- Check fields: trend, weak_areas, strong_areas, recommendations
- Analyze progress over time
**Expected:** Analysis with recommendations

### T100: Export to PDF
**File:** test_finance_reports_T088_T102.py::test_T100_export_pdf
**API:** POST /api/reports/{id}/export/pdf/ or GET with format=pdf
**Actions:**
- Create report (progress or activity)
- POST export with format='pdf'
- Verify response 200
- Check Content-Type: application/pdf
- Verify PDF has content (not empty)
- Check filename in Content-Disposition
**Expected:** PDF file with report data

### T101: Export to Excel
**File:** test_finance_reports_T088_T102.py::test_T101_export_excel
**API:** POST /api/reports/{id}/export/excel/ or GET with format=xlsx
**Actions:**
- Create report data
- POST export with format='excel'
- Verify response 200
- Check Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- Verify Excel structure (multiple sheets if applicable)
- Check data integrity
**Expected:** Excel file with report data

### T102: Scheduled Reports
**File:** test_finance_reports_T088_T102.py::test_T102_scheduled_reports
**API:** GET/POST /api/reports/schedules/
**Actions:**
- GET existing schedules
- POST new schedule: {frequency: 'weekly', recipients: [parent_test_20260107], report_type: 'progress'}
- Verify response 201 Created
- Check schedule active
- Verify next_send_date calculated
- Test with frequencies: 'weekly', 'monthly'
- Test recipients list (tutors, parents)
**Expected:** Schedule created, will auto-generate reports

## Error Cases to Test
1. Unauthenticated access → 401 Unauthorized
2. Non-tutor accessing tutor endpoints → 403 Forbidden
3. Parent trying to manage invoices → 403 Forbidden
4. Invalid invoice ID → 404 Not Found
5. Creating duplicate invoice for same student → 400 Bad Request
6. Invalid date range → 400 Bad Request
7. Export without permission → 403 Forbidden

## Test Data Setup
All tests should:
1. Use fixtures for user authentication
2. Create minimal valid test data
3. Clean up after each test
4. Mock external services (email, file uploads)
5. Use freeze_time for timestamp testing

## Success Criteria
- All 15 tests (T088-T102) PASS
- No permission bypass vulnerabilities
- All error cases handled correctly
- Response formats match specification
- Performance acceptable (< 500ms per endpoint)
