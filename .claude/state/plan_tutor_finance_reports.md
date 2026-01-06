# Test Plan: Tutor Cabinet Finance & Reports (T088-T102)

## Session: tutor_cabinet_test_20260107

### FINANCE TESTS (T088-T094)

#### T088: View Payments List
- Endpoint: GET /api/invoices/tutor/
- Actions:
  - List all invoices for authenticated tutor
  - Verify pagination (page, limit, total)
  - Check filtering by status
- Expected: 200 OK with paginated invoice list

#### T089: Create Invoice
- Endpoint: POST /api/invoices/tutor/
- Actions:
  - Create new invoice with amount, due_date, student_id
  - Verify invoice_number generated
  - Check status = 'DRAFT'
- Expected: 201 Created with invoice object

#### T090: Send Invoice
- Endpoint: POST /api/invoices/tutor/{id}/send/
- Actions:
  - Send invoice to parent (status DRAFT → SENT)
  - Verify email sent
  - Check sent_at timestamp
- Expected: 200 OK, status changed to SENT

#### T091: Track Invoice Status
- Endpoint: GET /api/invoices/tutor/{id}/
- Actions:
  - Check status transitions: DRAFT → SENT → VIEWED → PAID
  - Verify viewed_at, paid_at timestamps
  - Check parent_viewed flag
- Expected: 200 OK with correct status and timestamps

#### T092: Payment History
- Endpoint: GET /api/invoices/tutor/statistics/
- Actions:
  - Retrieve tutor statistics (total revenue, paid, pending)
  - Verify payment history list
  - Check date filtering
- Expected: 200 OK with statistics and history

#### T093: Dispute Payment
- Endpoint: POST /api/invoices/{id}/dispute/
- Actions:
  - Create dispute for paid invoice
  - Add dispute reason/comment
  - Verify status = 'DISPUTED'
- Expected: 200 OK, status changed

#### T094: Export Payments
- Endpoint: POST /api/invoices/tutor/export/
- Actions:
  - Export invoices to CSV/Excel
  - Filter by date range
  - Verify file format and content
- Expected: 200 OK with file download

### REPORTS TESTS (T095-T102)

#### T095: Student Progress Report
- Endpoint: GET /api/reports/student/{id}/progress/
- Actions:
  - Get overall student progress (grades, completion %)
  - Check by subject
  - Verify date range filtering
- Expected: 200 OK with progress metrics

#### T096: Activity Report
- Endpoint: GET /api/reports/student/{id}/activity/
- Actions:
  - Get lessons count, assignments completion
  - Check grades distribution
  - Verify period filtering
- Expected: 200 OK with activity data

#### T097: Grade Sheet (Ведомость)
- Endpoint: GET /api/reports/student/{id}/grades/
- Actions:
  - Get all grades for student by subject
  - Group by assignment type
  - Verify average calculation
- Expected: 200 OK with grades list

#### T098: Attendance Report
- Endpoint: GET /api/reports/student/{id}/attendance/
- Actions:
  - Get attendance stats (present, absent, late)
  - Filter by period
  - Calculate attendance percentage
- Expected: 200 OK with attendance data

#### T099: Performance Analysis
- Endpoint: GET /api/reports/student/{id}/performance/
- Actions:
  - Get trend analysis (improving/declining)
  - Identify weak areas
  - Suggest next steps
- Expected: 200 OK with analysis

#### T100: Export to PDF
- Endpoint: POST /api/reports/{id}/export/pdf/
- Actions:
  - Export progress/activity/grades to PDF
  - Verify PDF generation
  - Check format and content
- Expected: 200 OK with PDF file

#### T101: Export to Excel
- Endpoint: POST /api/reports/{id}/export/excel/
- Actions:
  - Export to Excel with multiple sheets
  - Check formatting and data integrity
- Expected: 200 OK with Excel file

#### T102: Scheduled Reports
- Endpoint: GET /api/reports/schedules/ + POST to create
- Actions:
  - Create weekly/monthly report schedule
  - Set recipients (tutors, parents)
  - Verify automatic generation/sending
- Expected: 201 Created, schedule active

### Dependencies
- All tests depend on: authenticated tutor user, student, subject enrollment
- Finance tests need: parent user, valid student-parent relationship
- Report tests need: grades, assignments, lessons, attendance data

### Test Infrastructure
- Use conftest fixtures: tutor_user, student_user, parent_user, subject, enrollment
- Create test data: invoices, reports, grades, attendance
- Mock email sending for invoice/report emails
- Use freeze_time for timestamp testing
