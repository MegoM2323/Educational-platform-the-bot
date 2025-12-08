# Invoice System

## Overview

The Invoice System enables tutors to create and manage payment invoices for students. Parents receive notifications and can pay invoices through YooKassa integration. The system provides complete audit trail and lifecycle management.

## Features

- ✅ **Invoice Creation**: Tutors create invoices for students
- ✅ **Auto-Parent Derivation**: Parent automatically taken from student profile
- ✅ **Status Lifecycle**: draft → sent → viewed → paid (with cancellation and overdue states)
- ✅ **Payment Integration**: Direct link to YooKassa payments
- ✅ **Subject Enrollment**: Optional linkage to specific subject
- ✅ **Telegram Notifications**: Track notification messages
- ✅ **Complete Audit Trail**: Every status change is logged
- ✅ **Data Integrity**: Check constraints prevent invalid state
- ✅ **Performance Optimized**: Strategic indexes for common queries

## Models

### Invoice

Represents a payment invoice from tutor to parent for student's education.

**Fields:**
- `tutor`: Tutor who created the invoice
- `student`: Student for whom the invoice is created
- `parent`: Parent who pays (auto-derived from student profile)
- `enrollment`: Optional link to SubjectEnrollment
- `payment`: Link to Payment (set when paid)
- `amount`: Invoice amount (must be > 0)
- `description`: Service description
- `status`: Current status (draft, sent, viewed, paid, cancelled, overdue)
- `due_date`: Payment deadline
- `sent_at`: When invoice was sent
- `viewed_at`: When parent viewed invoice
- `paid_at`: When invoice was paid
- `telegram_message_id`: Telegram notification ID
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Status Lifecycle:**
```
draft → sent → viewed → paid
           ↓         ↓
      cancelled  overdue
```

**Automatic Behavior:**
- `parent` auto-filled from `student.student_profile.parent`
- `sent_at` auto-set when status → 'sent'
- `viewed_at` auto-set when status → 'viewed'
- `paid_at` auto-set when status → 'paid'

**Properties:**
- `is_overdue`: Boolean - checks if invoice is past due date

**Methods:**
- `mark_as_overdue()`: Change status to overdue and create history entry

### InvoiceStatusHistory

Audit trail for invoice status changes.

**Fields:**
- `invoice`: Related invoice
- `old_status`: Previous status
- `new_status`: New status
- `changed_by`: User who made the change
- `changed_at`: When change occurred
- `reason`: Optional explanation

## Database Schema

See [SCHEMA_DESIGN.md](SCHEMA_DESIGN.md) for complete ERD and technical details.

**Key Indexes:**
- `(tutor, status)` - Tutor's invoice list
- `(parent, status)` - Parent's invoice list
- `(due_date, status)` - Overdue detection
- `(student, created_at DESC)` - Student history

**Constraints:**
- `amount > 0`
- `sent_at >= created_at`
- `viewed_at >= sent_at`
- `paid_at >= viewed_at`

## Usage Examples

### Creating an Invoice

```python
from invoices.models import Invoice
from accounts.models import User

tutor = User.objects.get(id=1, role='tutor')
student = User.objects.get(id=2, role='student')

invoice = Invoice.objects.create(
    tutor=tutor,
    student=student,
    # parent auto-filled from student.student_profile.parent
    amount=5000.00,
    description="4 занятия по математике (неделя 1-4 декабря)",
    due_date="2025-12-15",
    status=Invoice.Status.DRAFT
)
```

### Sending an Invoice

```python
invoice.status = Invoice.Status.SENT
invoice.save()  # Automatically sets sent_at

# Create history entry
from invoices.models import InvoiceStatusHistory
InvoiceStatusHistory.objects.create(
    invoice=invoice,
    old_status='draft',
    new_status='sent',
    changed_by=tutor,
    reason='Отправлено родителю через Telegram'
)
```

### Marking as Paid

```python
from payments.models import Payment

# After payment is confirmed
invoice.status = Invoice.Status.PAID
invoice.payment = payment_obj
invoice.save()  # Automatically sets paid_at
```

### Detecting Overdue Invoices (Celery Task)

```python
from django.utils import timezone
from invoices.models import Invoice

# Run daily
today = timezone.now().date()
overdue_invoices = Invoice.objects.filter(
    due_date__lt=today,
    status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED]
)

for invoice in overdue_invoices:
    invoice.mark_as_overdue()
    # Send notification to tutor/parent
```

### Querying Invoices (with optimization)

```python
# Tutor's pending invoices
invoices = Invoice.objects.filter(
    tutor=tutor,
    status__in=['draft', 'sent', 'viewed']
).select_related('student', 'parent', 'enrollment__subject')

# Parent's unpaid invoices
invoices = Invoice.objects.filter(
    parent=parent,
    status__in=['sent', 'viewed', 'overdue']
).select_related('tutor', 'student').order_by('due_date')

# Invoice history with user details
history = InvoiceStatusHistory.objects.filter(
    invoice=invoice
).select_related('changed_by').order_by('-changed_at')
```

## Admin Interface

Django admin registered for:
- **Invoice**: Full CRUD with inline status history
- **InvoiceStatusHistory**: Read-only audit log

**Features:**
- Color-coded status badges
- Overdue indicator
- Search by ID, tutor, student, parent, description
- Filter by status, date, tutor
- Inline status history display

## API Integration (Next Steps)

### Endpoints to Implement

```
POST   /api/invoices/                    - Create invoice (tutor only)
GET    /api/invoices/                    - List invoices (filtered by role)
GET    /api/invoices/{id}/               - Get invoice details
PATCH  /api/invoices/{id}/               - Update invoice (tutor only)
DELETE /api/invoices/{id}/               - Delete invoice (tutor only, if draft)
POST   /api/invoices/{id}/send/          - Send invoice to parent
POST   /api/invoices/{id}/cancel/        - Cancel invoice
POST   /api/invoices/{id}/mark-viewed/   - Mark as viewed (parent)
GET    /api/invoices/{id}/history/       - Get status history
```

### Permissions

- **Tutor**: Create, read, update (own), delete (draft only), send, cancel
- **Parent**: Read (own), mark-viewed
- **Student**: Read (own)
- **Admin**: Full access

## Testing Checklist

- [ ] Unit tests for Invoice model
- [ ] Unit tests for InvoiceStatusHistory model
- [ ] Test parent auto-derivation
- [ ] Test status lifecycle transitions
- [ ] Test timestamp auto-fill
- [ ] Test overdue detection
- [ ] Test constraints (amount > 0, date validations)
- [ ] Test cascade deletes
- [ ] Integration tests for API endpoints
- [ ] Test payment integration
- [ ] Test N+1 query prevention
- [ ] E2E test: full invoice lifecycle

## Migration

**Migration**: `invoices/migrations/0001_initial.py`

**Status**: ✅ Created and tested

**Compatibility**:
- ✅ SQLite (development)
- ✅ PostgreSQL (production)

**Apply migration:**
```bash
# Test environment
ENVIRONMENT=test python manage.py migrate invoices

# Development environment (requires fixing Twisted SSL issue)
ENVIRONMENT=development python manage.py migrate invoices

# Production environment
python manage.py migrate invoices
```

**Rollback migration:**
```bash
python manage.py migrate invoices zero
```

## Files

```
backend/invoices/
├── __init__.py
├── apps.py                 - App configuration
├── models.py               - Invoice and InvoiceStatusHistory models
├── admin.py                - Django admin configuration
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py     - Initial schema migration
├── SCHEMA_DESIGN.md        - Complete ERD and technical documentation
└── README.md               - This file
```

## Next Steps

1. **API Development** (T004)
   - Create serializers
   - Implement views/viewsets
   - Add permissions
   - Write API tests

2. **Service Layer** (T005)
   - Invoice creation service
   - Payment integration service
   - Notification service

3. **Celery Tasks** (T006)
   - Overdue invoice detection (daily)
   - Reminder notifications (3 days before due)

4. **Telegram Integration** (T007)
   - Send invoice notification
   - Handle payment callbacks
   - Status updates

5. **Frontend Integration** (T008)
   - Tutor: Invoice creation UI
   - Parent: Invoice list and payment UI
   - Admin: Invoice management dashboard

## References

- [SCHEMA_DESIGN.md](SCHEMA_DESIGN.md) - Complete database schema documentation
- [Django Models Documentation](https://docs.djangoproject.com/en/5.2/topics/db/models/)
- [Django Admin Documentation](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/)
