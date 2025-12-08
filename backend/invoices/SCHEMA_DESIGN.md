# Invoice System Database Schema Design

## Overview

The Invoice System enables tutors to create, send, and track payment invoices for students. Parents receive and pay these invoices. The system tracks the complete lifecycle of each invoice from draft to payment.

## Entity Relationship Diagram (ERD)

```
┌─────────────────────┐
│   User (accounts)   │
│─────────────────────│
│ • id (PK)           │
│ • role (choices)    │
│   - student         │
│   - teacher         │
│   - tutor           │
│   - parent          │
└──────┬──────────────┘
       │
       │ 1:N (tutor)
       ├──────────────────────────────────────┐
       │                                      │
       │ 1:N (student)                        │
       ├──────────────────────────┐           │
       │                          │           │
       │ 1:N (parent)             │           │
       ├──────────────────┐       │           │
       │                  │       │           │
       │                  ▼       ▼           ▼
       │            ┌─────────────────────────────────┐
       │            │      Invoice (invoices)         │
       │            │─────────────────────────────────│
       │            │ • id (PK)                       │
       │            │ • tutor_id (FK → User)          │
       │            │ • student_id (FK → User)        │
       │            │ • parent_id (FK → User)         │
       │            │ • enrollment_id (FK, optional)  │
       │            │ • payment_id (FK, optional)     │
       │            │ • amount (decimal, > 0)         │
       │            │ • description (text)            │
       │            │ • status (choices)              │
       │            │   - draft                       │
       │            │   - sent                        │
       │            │   - viewed                      │
       │            │   - paid                        │
       │            │   - cancelled                   │
       │            │   - overdue                     │
       │            │ • due_date (date)               │
       │            │ • sent_at (datetime, nullable)  │
       │            │ • viewed_at (datetime, nullable)│
       │            │ • paid_at (datetime, nullable)  │
       │            │ • telegram_message_id (char)    │
       │            │ • created_at (datetime)         │
       │            │ • updated_at (datetime)         │
       │            └───────────┬─────────────────────┘
       │                        │
       │ 1:N (changed_by)       │ 1:N (invoice)
       │                        │
       │                        ▼
       │            ┌──────────────────────────────────┐
       └───────────►│  InvoiceStatusHistory (invoices) │
                    │──────────────────────────────────│
                    │ • id (PK)                        │
                    │ • invoice_id (FK → Invoice)      │
                    │ • old_status (choices)           │
                    │ • new_status (choices)           │
                    │ • changed_by_id (FK → User)      │
                    │ • changed_at (datetime)          │
                    │ • reason (text, nullable)        │
                    └──────────────────────────────────┘

┌────────────────────────────────┐
│ SubjectEnrollment (materials)  │
│────────────────────────────────│
│ • id (PK)                      │
│ • student_id (FK → User)       │
│ • subject_id (FK → Subject)    │
│ • teacher_id (FK → User)       │
└────────────┬───────────────────┘
             │
             │ 1:N (enrollment, optional)
             │
             └─────────────────────► Invoice

┌────────────────────────────┐
│   Payment (payments)       │
│────────────────────────────│
│ • id (PK, UUID)            │
│ • yookassa_payment_id      │
│ • amount (decimal)         │
│ • status (choices)         │
│ • paid_at (datetime)       │
└──────────┬─────────────────┘
           │
           │ 1:1 (payment, optional)
           │
           └───────────────────────► Invoice
```

## Relationships

### Invoice → User (Tutor)
- **Type**: Many-to-One (N:1)
- **Foreign Key**: `tutor_id`
- **Cascade**: ON DELETE CASCADE
- **Constraint**: `limit_choices_to={'role': 'tutor'}`
- **Related Name**: `created_invoices`
- **Business Logic**: Tutor who creates the invoice

### Invoice → User (Student)
- **Type**: Many-to-One (N:1)
- **Foreign Key**: `student_id`
- **Cascade**: ON DELETE CASCADE
- **Constraint**: `limit_choices_to={'role': 'student'}`
- **Related Name**: `student_invoices`
- **Business Logic**: Student for whom the invoice is created

### Invoice → User (Parent)
- **Type**: Many-to-One (N:1)
- **Foreign Key**: `parent_id`
- **Cascade**: ON DELETE CASCADE
- **Constraint**: `limit_choices_to={'role': 'parent'}`
- **Related Name**: `parent_invoices`
- **Business Logic**: Parent who pays the invoice (auto-derived from student.student_profile.parent)

### Invoice → SubjectEnrollment
- **Type**: Many-to-One (N:1), Optional
- **Foreign Key**: `enrollment_id`
- **Cascade**: ON DELETE SET NULL
- **Related Name**: `invoices`
- **Business Logic**: Optional link to specific subject enrollment

### Invoice → Payment
- **Type**: One-to-One (1:1), Optional
- **Foreign Key**: `payment_id`
- **Cascade**: ON DELETE SET NULL
- **Related Name**: `invoice`
- **Business Logic**: Link to YooKassa payment (created when invoice is paid)

### InvoiceStatusHistory → Invoice
- **Type**: Many-to-One (N:1)
- **Foreign Key**: `invoice_id`
- **Cascade**: ON DELETE CASCADE
- **Related Name**: `status_history`
- **Business Logic**: Audit trail of all status changes

### InvoiceStatusHistory → User
- **Type**: Many-to-One (N:1)
- **Foreign Key**: `changed_by_id`
- **Cascade**: ON DELETE CASCADE
- **Related Name**: `invoice_status_changes`
- **Business Logic**: User who changed the status

## Indexes

### Performance Optimization Strategy

#### Invoice Model Indexes

1. **idx_invoice_tutor_status** (tutor_id, status)
   - **Purpose**: List tutor's invoices filtered by status
   - **Query**: `Invoice.objects.filter(tutor=tutor, status='sent')`
   - **Cardinality**: High (many tutors × 6 statuses)

2. **idx_invoice_parent_status** (parent_id, status)
   - **Purpose**: List parent's invoices filtered by status
   - **Query**: `Invoice.objects.filter(parent=parent, status__in=['sent', 'viewed'])`
   - **Cardinality**: High (many parents × 6 statuses)

3. **idx_invoice_due_status** (due_date, status)
   - **Purpose**: Detect overdue invoices (cron job)
   - **Query**: `Invoice.objects.filter(due_date__lt=today, status__in=['sent', 'viewed'])`
   - **Cardinality**: Medium (dates × 6 statuses)

4. **idx_invoice_student_date** (student_id, -created_at DESC)
   - **Purpose**: Student invoice history (chronological)
   - **Query**: `Invoice.objects.filter(student=student).order_by('-created_at')`
   - **Cardinality**: High (many students × many invoices)

5. **idx_invoice_payment** (payment_id) [PARTIAL: WHERE payment_id IS NOT NULL]
   - **Purpose**: Find invoice by payment (webhook processing)
   - **Query**: `Invoice.objects.get(payment=payment)`
   - **Cardinality**: Low (only paid invoices)
   - **Type**: Partial index (PostgreSQL only, ignored in SQLite)

6. **idx_invoice_telegram** (telegram_message_id) [PARTIAL: WHERE telegram_message_id IS NOT NULL]
   - **Purpose**: Find invoice by Telegram message (callback processing)
   - **Query**: `Invoice.objects.get(telegram_message_id=msg_id)`
   - **Cardinality**: Low (only sent invoices)
   - **Type**: Partial index (PostgreSQL only, ignored in SQLite)

#### InvoiceStatusHistory Model Indexes

1. **idx_history_invoice_date** (invoice_id, -changed_at DESC)
   - **Purpose**: Get chronological history for invoice
   - **Query**: `InvoiceStatusHistory.objects.filter(invoice=invoice).order_by('-changed_at')`
   - **Cardinality**: High (many invoices × many changes)

2. **idx_history_user_date** (changed_by_id, -changed_at DESC)
   - **Purpose**: Audit user's actions
   - **Query**: `InvoiceStatusHistory.objects.filter(changed_by=user).order_by('-changed_at')`
   - **Cardinality**: High (many users × many changes)

## Constraints

### Check Constraints

1. **check_invoice_amount_positive**
   ```sql
   CHECK (amount > 0)
   ```
   - **Purpose**: Prevent zero or negative invoices
   - **Compatibility**: SQLite ✓, PostgreSQL ✓

2. **check_invoice_sent_after_created**
   ```sql
   CHECK (sent_at IS NULL OR sent_at >= created_at)
   ```
   - **Purpose**: Ensure sent_at is not before creation
   - **Compatibility**: SQLite ✓, PostgreSQL ✓

3. **check_invoice_viewed_after_sent**
   ```sql
   CHECK (viewed_at IS NULL OR sent_at IS NULL OR viewed_at >= sent_at)
   ```
   - **Purpose**: Ensure viewed_at is not before sending
   - **Compatibility**: SQLite ✓, PostgreSQL ✓

4. **check_invoice_paid_after_viewed**
   ```sql
   CHECK (paid_at IS NULL OR viewed_at IS NULL OR paid_at >= viewed_at)
   ```
   - **Purpose**: Ensure paid_at is not before viewing
   - **Compatibility**: SQLite ✓, PostgreSQL ✓

### Foreign Key Constraints

All foreign keys use Django's default behavior:
- **ON DELETE CASCADE** for required references (tutor, student, parent)
- **ON DELETE SET NULL** for optional references (enrollment, payment)

### Unique Constraints

**Not implemented** - Duplicate invoice prevention is handled at application level:
- Tutors should not create duplicate invoices with same (tutor, student, amount, description)
- This is a soft rule, enforced in business logic, not database constraint
- Allows legitimate duplicates (e.g., recurring monthly invoices)

## Data Integrity Rules

### Business Logic Validation

1. **Parent Derivation**
   - `parent` field MUST match `student.student_profile.parent`
   - Auto-filled in `save()` method if not provided
   - Validated in `clean()` method

2. **Enrollment Validation**
   - If `enrollment` is set, `enrollment.student` MUST equal `student`
   - If `enrollment` is set, tutor SHOULD be student's tutor
   - Validated in `clean()` method

3. **Status Lifecycle**
   ```
   draft → sent → viewed → paid
              ↓         ↓
           cancelled  overdue
   ```
   - `draft`: Initial state
   - `sent`: Invoice sent to parent (auto-sets `sent_at`)
   - `viewed`: Parent opened invoice (auto-sets `viewed_at`)
   - `paid`: Payment completed (auto-sets `paid_at`, links `payment`)
   - `cancelled`: Cancelled by tutor
   - `overdue`: Auto-set by cron when `due_date` < today

4. **Timestamp Auto-Fill**
   - `sent_at`: Set when status changes to 'sent'
   - `viewed_at`: Set when status changes to 'viewed'
   - `paid_at`: Set when status changes to 'paid'
   - Implemented in `save()` method

5. **Overdue Detection**
   - Property: `is_overdue` checks if `due_date` < today AND status in ['sent', 'viewed']
   - Method: `mark_as_overdue()` updates status and creates history entry
   - Should be called by Celery periodic task

## SQL Schema (PostgreSQL)

```sql
-- Invoice table
CREATE TABLE invoices_invoice (
    id BIGSERIAL PRIMARY KEY,
    tutor_id INTEGER NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    parent_id INTEGER NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    enrollment_id INTEGER NULL REFERENCES materials_subjectenrollment(id) ON DELETE SET NULL,
    payment_id UUID NULL REFERENCES payments_payment(id) ON DELETE SET NULL UNIQUE,

    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    description TEXT NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    due_date DATE NOT NULL,

    sent_at TIMESTAMP NULL,
    viewed_at TIMESTAMP NULL,
    paid_at TIMESTAMP NULL,

    telegram_message_id VARCHAR(255) NULL,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Check constraints
    CONSTRAINT check_invoice_amount_positive CHECK (amount > 0),
    CONSTRAINT check_invoice_sent_after_created
        CHECK (sent_at IS NULL OR sent_at >= created_at),
    CONSTRAINT check_invoice_viewed_after_sent
        CHECK (viewed_at IS NULL OR sent_at IS NULL OR viewed_at >= sent_at),
    CONSTRAINT check_invoice_paid_after_viewed
        CHECK (paid_at IS NULL OR viewed_at IS NULL OR paid_at >= viewed_at)
);

-- Invoice indexes
CREATE INDEX idx_invoice_tutor_status ON invoices_invoice(tutor_id, status);
CREATE INDEX idx_invoice_parent_status ON invoices_invoice(parent_id, status);
CREATE INDEX idx_invoice_due_status ON invoices_invoice(due_date, status);
CREATE INDEX idx_invoice_student_date ON invoices_invoice(student_id, created_at DESC);
CREATE INDEX idx_invoice_payment ON invoices_invoice(payment_id) WHERE payment_id IS NOT NULL;
CREATE INDEX idx_invoice_telegram ON invoices_invoice(telegram_message_id) WHERE telegram_message_id IS NOT NULL;

-- Invoice status history table
CREATE TABLE invoices_invoicestatushistory (
    id BIGSERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices_invoice(id) ON DELETE CASCADE,
    old_status VARCHAR(20) NOT NULL,
    new_status VARCHAR(20) NOT NULL,
    changed_by_id INTEGER NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    changed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    reason TEXT NULL
);

-- Invoice status history indexes
CREATE INDEX idx_history_invoice_date ON invoices_invoicestatushistory(invoice_id, changed_at DESC);
CREATE INDEX idx_history_user_date ON invoices_invoicestatushistory(changed_by_id, changed_at DESC);
```

## Query Performance Analysis

### Expected Query Patterns

1. **Tutor Dashboard - Pending Invoices**
   ```python
   Invoice.objects.filter(
       tutor=tutor,
       status__in=['draft', 'sent', 'viewed']
   ).select_related('student', 'parent')
   ```
   - **Index Used**: `idx_invoice_tutor_status`
   - **Complexity**: O(log n) + O(k) where k = matching rows
   - **select_related**: Prevents N+1 queries for student/parent names

2. **Parent Dashboard - Unpaid Invoices**
   ```python
   Invoice.objects.filter(
       parent=parent,
       status__in=['sent', 'viewed', 'overdue']
   ).select_related('tutor', 'student', 'enrollment__subject').order_by('due_date')
   ```
   - **Index Used**: `idx_invoice_parent_status`
   - **Complexity**: O(log n) + O(k log k) where k = matching rows
   - **select_related**: Prevents N+1 for tutor/student/subject

3. **Cron Job - Overdue Detection**
   ```python
   from django.utils import timezone
   Invoice.objects.filter(
       due_date__lt=timezone.now().date(),
       status__in=['sent', 'viewed']
   )
   ```
   - **Index Used**: `idx_invoice_due_status`
   - **Complexity**: O(log n) + O(k) where k = overdue invoices
   - **Frequency**: Run daily via Celery beat

4. **Payment Webhook - Link Invoice to Payment**
   ```python
   invoice = Invoice.objects.get(id=invoice_id)
   invoice.payment = payment
   invoice.status = Invoice.Status.PAID
   invoice.save()
   ```
   - **Index Used**: Primary key
   - **Complexity**: O(log n)
   - **Transaction**: Wrap in database transaction

5. **Audit Trail - Invoice History**
   ```python
   InvoiceStatusHistory.objects.filter(
       invoice=invoice
   ).select_related('changed_by').order_by('-changed_at')
   ```
   - **Index Used**: `idx_history_invoice_date`
   - **Complexity**: O(log n) + O(k) where k = history entries
   - **select_related**: Prevents N+1 for changed_by names

6. **Admin - User Actions Audit**
   ```python
   InvoiceStatusHistory.objects.filter(
       changed_by=user
   ).select_related('invoice__student').order_by('-changed_at')
   ```
   - **Index Used**: `idx_history_user_date`
   - **Complexity**: O(log n) + O(k) where k = user's actions

### N+1 Query Prevention

Always use `select_related()` and `prefetch_related()`:

```python
# ✓ GOOD - Single query
invoices = Invoice.objects.filter(
    parent=parent
).select_related('tutor', 'student', 'enrollment__subject', 'payment')

for invoice in invoices:
    print(invoice.tutor.get_full_name())  # No additional query
    print(invoice.student.get_full_name())  # No additional query
    if invoice.enrollment:
        print(invoice.enrollment.subject.name)  # No additional query

# ✗ BAD - N+1 queries
invoices = Invoice.objects.filter(parent=parent)
for invoice in invoices:
    print(invoice.tutor.get_full_name())  # Query per invoice
    print(invoice.student.get_full_name())  # Query per invoice
```

## Migration Safety

### SQLite vs PostgreSQL Compatibility

This migration is **100% compatible** with both databases:

- ✓ Check constraints: Supported in both
- ✓ Foreign keys: Supported in both
- ✓ Indexes: Supported in both
- ⚠️ Partial indexes: PostgreSQL only (SQLite ignores `condition=` parameter)
- ✓ Decimal fields: Supported in both
- ✓ Date/DateTime fields: Supported in both

### Reversibility

The migration is **fully reversible**:

```bash
# Rollback
python manage.py migrate invoices zero

# Reapply
python manage.py migrate invoices
```

### Production Deployment Checklist

Before applying to production:

- [ ] Backup database
- [ ] Test migration on staging with production-like data
- [ ] Verify no lock timeout issues (large tables)
- [ ] Check disk space for indexes
- [ ] Plan rollback procedure
- [ ] Monitor query performance after deployment

### Zero Downtime Strategy

1. **Phase 1**: Add models (this migration)
   - No existing data affected
   - New tables created
   - Safe to run on live system

2. **Phase 2**: Add API endpoints
   - Start using new models
   - No breaking changes to existing functionality

3. **Phase 3**: Data migration (if needed)
   - Migrate existing payment data to invoices
   - Run as separate migration with batching

## Next Steps

After schema deployment:

1. **API Development**
   - Create serializers (DRF)
   - Implement views (list, create, retrieve, update)
   - Add permissions (tutor can create, parent can view/pay)

2. **Business Logic**
   - Service layer for invoice creation
   - Celery task for overdue detection
   - Payment integration (YooKassa webhook)
   - Telegram notifications

3. **Frontend Integration**
   - Tutor: Invoice creation form
   - Parent: Invoice list and payment UI
   - Admin: Invoice management interface

4. **Testing**
   - Unit tests for models
   - Integration tests for API
   - E2E tests for payment flow

## Conclusion

This schema design provides:

- ✓ Complete audit trail via `InvoiceStatusHistory`
- ✓ Optimized indexes for common queries
- ✓ Data integrity via check constraints
- ✓ Auto-derivation of parent from student
- ✓ Optional subject enrollment linkage
- ✓ Payment integration support
- ✓ Telegram notification support
- ✓ SQLite and PostgreSQL compatibility
- ✓ Reversible migrations
- ✓ N+1 query prevention guidelines
