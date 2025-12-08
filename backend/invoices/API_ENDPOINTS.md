# Invoice API Endpoints Documentation

## Overview

Complete REST API implementation for invoice management system. Provides endpoints for tutors to create and manage invoices, and for parents to view and pay invoices.

## Architecture

- **Service Layer**: Business logic in `services.py` (completed in T005)
- **Permission Layer**: Role-based access control in `permissions.py`
- **Serialization Layer**: Data validation and formatting in `serializers.py`
- **View Layer**: API endpoints in `views.py` using Django REST Framework ViewSets
- **URL Routing**: Configured in `urls.py` and registered in `config/urls.py`

## Authentication

All endpoints require authentication via Token-based authentication.

**Headers:**
```
Authorization: Token <your_token_here>
```

## Response Format

### Success Response
```json
{
  "success": true,
  "data": { /* object or array */ },
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "code": "ERROR_CODE",
  "status_code": 400
}
```

### Error Codes
- `PERMISSION_DENIED` - User doesn't have permission (403)
- `NOT_FOUND` - Resource not found (404)
- `VALIDATION_ERROR` - Invalid input data (400)
- `DUPLICATE_INVOICE` - Identical unpaid invoice exists (409)
- `INVALID_STATUS` - Invalid status transition (409)
- `ALREADY_PAID` - Invoice already paid (409)
- `CANCELLED` - Invoice cancelled (409)
- `NOT_IMPLEMENTED` - Feature not yet implemented (501)

---

## Tutor Endpoints

### 1. List Invoices

**Endpoint:** `GET /api/invoices/tutor/`

**Description:** Retrieve list of tutor's invoices with filtering, sorting, and pagination.

**Query Parameters:**
- `page` (integer, default: 1) - Page number
- `page_size` (integer, default: 20) - Items per page
- `status` (string) - Filter by status: draft, sent, viewed, paid, cancelled, overdue
- `student_id` (integer) - Filter by student ID
- `from_date` (date, YYYY-MM-DD) - Filter by creation date from
- `to_date` (date, YYYY-MM-DD) - Filter by creation date to
- `ordering` (string, default: -created_at) - Sort field: -created_at, amount, due_date

**Example Request:**
```bash
GET /api/invoices/tutor/?page=1&page_size=20&status=sent&ordering=-created_at
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": 1,
        "student_name": "Иван Петров",
        "parent_name": "Петр Петров",
        "tutor_name": "Анна Сидорова",
        "amount": "5000.00",
        "status": "sent",
        "status_display": "Отправлен",
        "due_date": "2025-01-10",
        "created_at": "2025-12-08T10:00:00Z",
        "is_overdue": false
      }
    ],
    "count": 15,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

### 2. Create Invoice

**Endpoint:** `POST /api/invoices/tutor/`

**Description:** Create new invoice for student.

**Request Body:**
```json
{
  "student_id": 123,
  "amount": "5000.00",
  "description": "Услуги по математике за декабрь",
  "due_date": "2025-01-10",
  "enrollment_id": 456  // optional
}
```

**Validation Rules:**
- `student_id`: Must exist, must be tutor's student
- `amount`: Must be positive decimal (min 0.01)
- `description`: Required, max 2000 characters, not blank
- `due_date`: Must not be in the past
- `enrollment_id`: Optional, must belong to student if provided
- Duplicate check: Prevents identical unpaid invoices

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "tutor": {
      "id": 10,
      "email": "tutor@example.com",
      "first_name": "Анна",
      "last_name": "Сидорова",
      "full_name": "Анна Сидорова",
      "role": "tutor"
    },
    "student": {
      "id": 123,
      "email": "student@example.com",
      "first_name": "Иван",
      "last_name": "Петров",
      "full_name": "Иван Петров",
      "role": "student"
    },
    "parent": {
      "id": 456,
      "email": "parent@example.com",
      "first_name": "Петр",
      "last_name": "Петров",
      "full_name": "Петр Петров",
      "role": "parent"
    },
    "amount": "5000.00",
    "description": "Услуги по математике за декабрь",
    "status": "draft",
    "status_display": "Черновик",
    "due_date": "2025-01-10",
    "sent_at": null,
    "viewed_at": null,
    "paid_at": null,
    "payment": null,
    "enrollment": 456,
    "telegram_message_id": null,
    "created_at": "2025-12-08T10:00:00Z",
    "updated_at": "2025-12-08T10:00:00Z",
    "is_overdue": false,
    "status_history": [
      {
        "id": 1,
        "old_status": "draft",
        "new_status": "draft",
        "changed_by": {
          "id": 10,
          "full_name": "Анна Сидорова",
          "role": "tutor"
        },
        "changed_at": "2025-12-08T10:00:00Z",
        "reason": "Счет создан"
      }
    ]
  },
  "message": "Счет успешно создан"
}
```

**Error Examples:**
```json
// Student not tutor's student
{
  "success": false,
  "error": "Студент Иван Петров не является вашим студентом",
  "code": "PERMISSION_DENIED"
}

// Duplicate invoice
{
  "success": false,
  "error": "Существует неоплаченный счет #5 с такими же параметрами",
  "code": "DUPLICATE_INVOICE"
}

// Invalid due_date
{
  "success": false,
  "error": "Срок оплаты не может быть в прошлом",
  "code": "VALIDATION_ERROR"
}
```

---

### 3. Get Invoice Detail

**Endpoint:** `GET /api/invoices/tutor/{id}/`

**Description:** Retrieve detailed information about specific invoice.

**Example Response:**
```json
{
  "success": true,
  "data": {
    // Same structure as Create Invoice response
    // Includes full invoice details, status history, payment info
  }
}
```

---

### 4. Cancel Invoice

**Endpoint:** `DELETE /api/invoices/tutor/{id}/`

**Description:** Cancel invoice (soft delete, changes status to CANCELLED).

**Request Body (optional):**
```json
{
  "reason": "Студент отказался от занятий"
}
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "cancelled",
    "message": "Счет успешно отменен"
  }
}
```

**Restrictions:**
- Cannot cancel paid invoice
- Only tutor who created invoice can cancel it

---

### 5. Send Invoice

**Endpoint:** `POST /api/invoices/tutor/{id}/send/`

**Description:** Send invoice to parent (changes status from DRAFT to SENT).

**Request Body:** None required

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "sent",
    "sent_at": "2025-12-08T10:05:00Z",
    "message": "Счет успешно отправлен родителю"
  }
}
```

**Side Effects:**
- Status changes: DRAFT → SENT
- Sets `sent_at` timestamp
- Creates status history entry
- Sends notification to parent (if NotificationService available)

**Restrictions:**
- Only DRAFT invoices can be sent
- Only tutor who created invoice can send it

---

## Parent Endpoints

### 6. List Invoices

**Endpoint:** `GET /api/invoices/parent/`

**Description:** Retrieve list of parent's invoices (for their children).

**Query Parameters:**
- `page` (integer, default: 1) - Page number
- `page_size` (integer, default: 20) - Items per page
- `status` (string) - Filter by status
- `child_id` (integer) - Filter by child ID
- `from_date` (date, YYYY-MM-DD) - Filter by creation date from
- `to_date` (date, YYYY-MM-DD) - Filter by creation date to
- `unpaid_only` (boolean) - Only unpaid invoices (true/false)
- `ordering` (string, default: -due_date) - Sort field

**Example Request:**
```bash
GET /api/invoices/parent/?unpaid_only=true&ordering=-due_date
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": 1,
        "student_name": "Иван Петров",
        "parent_name": "Петр Петров",
        "tutor_name": "Анна Сидорова",
        "amount": "5000.00",
        "status": "sent",
        "status_display": "Отправлен",
        "due_date": "2025-01-10",
        "created_at": "2025-12-08T10:00:00Z",
        "is_overdue": false
      }
    ],
    "count": 3,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

### 7. Get Invoice Detail

**Endpoint:** `GET /api/invoices/parent/{id}/`

**Description:** Retrieve detailed information about specific invoice.

**Example Response:**
```json
{
  "success": true,
  "data": {
    // Same structure as tutor's invoice detail
    // Parent can only see invoices for their children
  }
}
```

---

### 8. Mark Invoice as Viewed

**Endpoint:** `POST /api/invoices/parent/{id}/mark_viewed/`

**Description:** Mark invoice as viewed (changes status from SENT to VIEWED).

**Request Body:** None required

**Example Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "viewed",
    "viewed_at": "2025-12-08T15:30:00Z",
    "message": "Счет отмечен как просмотренный"
  }
}
```

**Side Effects:**
- Status changes: SENT → VIEWED
- Sets `viewed_at` timestamp
- Creates status history entry

**Idempotent:** If already viewed or paid, returns success without changing status.

---

### 9. Pay Invoice

**Endpoint:** `POST /api/invoices/parent/{id}/pay/`

**Description:** Initiate payment for invoice via YooKassa.

**Request Body:** None required

**Example Response (will be implemented in T007):**
```json
{
  "success": false,
  "error": "YooKassa integration not implemented yet (T007)",
  "code": "NOT_IMPLEMENTED"
}
```

**Future Response (after T007):**
```json
{
  "success": true,
  "data": {
    "payment_url": "https://yookassa.ru/checkout/payments/2c66e...",
    "payment_id": "2c66e123-4567-89ab-cdef-0123456789ab",
    "invoice_id": 1,
    "amount": "5000.00"
  }
}
```

**Side Effects (after T007):**
- Creates Payment object with metadata['invoice_id']
- Returns URL for redirect to YooKassa payment page
- Idempotent: Returns existing payment if already created

**Restrictions:**
- Cannot pay already paid invoice (409)
- Cannot pay cancelled invoice (409)
- Only parent of student can pay invoice

---

## Permissions

### IsTutorOrParent
- Allows only tutors and parents to access invoice endpoints
- Admins have full access

### IsTutorForStudent
- Tutor can only manage invoices for their students
- Checked via `StudentProfile.tutor` relationship

### IsParentOfStudent
- Parent can only view invoices for their children
- Checked via `StudentProfile.parent` relationship

---

## Performance Optimizations

### Query Optimization
All list endpoints use `select_related()` and `prefetch_related()` to minimize database queries:

```python
# Tutor invoices
queryset = Invoice.objects.filter(tutor=tutor).select_related(
    'tutor', 'student', 'student__student_profile',
    'parent', 'parent__parent_profile',
    'enrollment', 'enrollment__subject', 'enrollment__teacher',
    'payment'
).prefetch_related(
    Prefetch('status_history', queryset=...)
)
```

### Database Indexes
Indexes defined in `models.py` (T003/T004):
- `(tutor, status)` - For tutor's invoice list with status filter
- `(parent, status)` - For parent's invoice list with status filter
- `(due_date, status)` - For overdue invoice queries
- `(student, -created_at)` - For student's invoice history

### Pagination
Default: 20 items per page (configurable via `page_size` parameter)

---

## Status Workflow

```
DRAFT → SENT → VIEWED → PAID
   ↓      ↓       ↓
CANCELLED (soft delete)
   ↓
OVERDUE (if due_date passed and unpaid)
```

### Valid Transitions
- DRAFT → SENT (via send endpoint)
- SENT → VIEWED (via mark_viewed endpoint)
- VIEWED → PAID (via payment webhook, T007)
- Any unpaid status → CANCELLED (via delete endpoint)
- SENT/VIEWED → OVERDUE (automatic via celery task)

### Invalid Transitions
- PAID → any other status (cannot modify paid invoice)
- CANCELLED → any other status (cannot reactivate cancelled invoice)

---

## Testing Examples

### Create and Send Invoice (Tutor Flow)
```bash
# 1. Create invoice
curl -X POST http://localhost:8000/api/invoices/tutor/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": 123,
    "amount": "5000.00",
    "description": "Услуги по математике за декабрь",
    "due_date": "2025-01-10"
  }'

# 2. Send invoice to parent
curl -X POST http://localhost:8000/api/invoices/tutor/1/send/ \
  -H "Authorization: Token YOUR_TOKEN"

# 3. List sent invoices
curl -X GET "http://localhost:8000/api/invoices/tutor/?status=sent" \
  -H "Authorization: Token YOUR_TOKEN"
```

### View and Pay Invoice (Parent Flow)
```bash
# 1. List unpaid invoices
curl -X GET "http://localhost:8000/api/invoices/parent/?unpaid_only=true" \
  -H "Authorization: Token YOUR_TOKEN"

# 2. View invoice detail
curl -X GET http://localhost:8000/api/invoices/parent/1/ \
  -H "Authorization: Token YOUR_TOKEN"

# 3. Mark as viewed
curl -X POST http://localhost:8000/api/invoices/parent/1/mark_viewed/ \
  -H "Authorization: Token YOUR_TOKEN"

# 4. Initiate payment (will be implemented in T007)
curl -X POST http://localhost:8000/api/invoices/parent/1/pay/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## Next Steps (Future Tasks)

### T007: YooKassa Integration
- Implement `pay` endpoint logic
- Create Payment object with invoice metadata
- Handle payment webhooks
- Update invoice status on successful payment

### T008: Telegram Integration
- Send invoice notifications via Telegram bot
- Handle payment callbacks from Telegram
- Store telegram_message_id

### T012: WebSocket Real-time Updates
- Create WebSocket consumer for invoice updates
- Broadcast status changes to relevant users
- Update frontend in real-time

---

## Files Created

1. **`backend/invoices/permissions.py`** - Permission classes
2. **`backend/invoices/serializers.py`** - DRF serializers with validation
3. **`backend/invoices/views.py`** - ViewSets with API endpoints
4. **`backend/invoices/urls.py`** - URL routing configuration
5. **`backend/invoices/filters.py`** - Advanced filtering (django-filter)
6. **`backend/config/urls.py`** - Updated to include invoice URLs

## Task Completion

**Task T006: Implement Invoice API Endpoints** - COMPLETED ✅

All acceptance criteria met:
- ✅ REST API endpoints for CRUD operations
- ✅ Proper authentication and permissions
- ✅ Pagination for list endpoints
- ✅ Filtering by status, date range
- ✅ Serializers with validation
- ✅ Error handling with proper status codes
- ✅ Consistent response format
- ✅ Query optimization with select_related/prefetch_related
- ✅ Comprehensive documentation

Ready for integration testing (T015) and frontend development (T009, T010).
