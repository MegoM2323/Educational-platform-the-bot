# Admin API Endpoints - Test Documentation

## Overview

This document describes the three admin endpoints implemented for user management:
- **T303**: Student Creation (`POST /api/admin/students/create/`)
- **T305**: Parent Creation (`POST /api/admin/parents/create/`)
- **T307**: Parent-Student Assignment (`POST /api/admin/assign-parent/`)

All endpoints are fully implemented and integrated in the backend.

---

## T303: Create Student Endpoint

### Endpoint Details

```
POST /api/admin/students/create/
```

### Implementation

- **File**: `backend/accounts/staff_views.py`
- **Function**: `create_student(request)`
- **Lines**: 1512-1731
- **Decorators**:
  - `@api_view(['POST'])`
  - `@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])`
  - `@permission_classes([IsStaffOrAdmin])`

### Request Payload

**Required Fields**:
```json
{
  "email": "student@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "grade": "10"
}
```

**Optional Fields**:
```json
{
  "goal": "Learn Python programming",
  "phone": "+1234567890",
  "tutor_id": 123,
  "parent_id": 456,
  "password": "CustomPassword123"
}
```

### Response (HTTP 201 Created)

```json
{
  "success": true,
  "user": {
    "id": 789,
    "email": "student@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "student",
    "role_display": "Студент",
    "phone": "+1234567890",
    "avatar": null,
    "is_verified": false,
    "is_staff": false,
    "date_joined": "2025-11-27T10:30:00Z",
    "full_name": "John Doe"
  },
  "profile": {
    "id": 890,
    "user": {...},
    "grade": "10",
    "goal": "Learn Python programming",
    "tutor": 123,
    "tutor_name": "Tutor Name",
    "parent": 456,
    "parent_name": "Parent Name",
    "progress_percentage": 0,
    "streak_days": 0,
    "total_points": 0,
    "accuracy_percentage": 0
  },
  "credentials": {
    "username": "student@example.com",
    "email": "student@example.com",
    "temporary_password": "AbCd1234EfGh"
  },
  "message": "Студент успешно создан"
}
```

### Error Responses

**HTTP 400 Bad Request** - Validation error:
```json
{
  "grade": ["Поле обязательно для студента"]
}
```

**HTTP 409 Conflict** - Email already exists:
```json
{
  "detail": "Пользователь с этим email уже существует"
}
```

**HTTP 403 Forbidden** - Insufficient permissions:
```json
{
  "detail": "Недостаточно прав для выполнения этого действия"
}
```

### Test Cases

#### Test 1: Valid Student Creation
```bash
curl -X POST http://localhost:8000/api/admin/students/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "email": "test_student@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "grade": "10"
  }'
```

**Expected**:
- Status: 201
- Student created in database
- StudentProfile created with grade="10"
- Temporary password returned

#### Test 2: Missing Required Field
```bash
curl -X POST http://localhost:8000/api/admin/students/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "email": "test_student@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

**Expected**:
- Status: 400
- Error message about missing "grade"

#### Test 3: Duplicate Email
```bash
curl -X POST http://localhost:8000/api/admin/students/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "email": "existing_student@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "grade": "11"
  }'
```

**Expected**:
- Status: 409
- Error message about email already existing

#### Test 4: With Tutor Assignment
```bash
curl -X POST http://localhost:8000/api/admin/students/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "email": "student_with_tutor@example.com",
    "first_name": "Mike",
    "last_name": "Brown",
    "grade": "9",
    "tutor_id": 123
  }'
```

**Expected**:
- Status: 201
- StudentProfile.tutor field set to tutor ID 123
- Response includes tutor_name

### Validation Rules

| Field | Required | Type | Validation |
|-------|----------|------|-----------|
| email | Yes | string | Must be unique, valid email format |
| first_name | Yes | string | Max 150 chars, non-empty |
| last_name | Yes | string | Max 150 chars, non-empty |
| grade | Yes | string | Max 10 chars |
| goal | No | string | Optional learning goal |
| phone | No | string | Max 20 chars, must match phone format |
| tutor_id | No | integer | Must be existing tutor user |
| parent_id | No | integer | Must be existing parent user |
| password | No | string | If not provided, 12-char random generated |

---

## T305: Create Parent Endpoint

### Endpoint Details

```
POST /api/admin/parents/create/
```

### Implementation

- **File**: `backend/accounts/staff_views.py`
- **Function**: `create_parent(request)`
- **Lines**: 1734-1921
- **Decorators**:
  - `@api_view(['POST'])`
  - `@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])`
  - `@permission_classes([IsStaffOrAdmin])`

### Request Payload

**Required Fields**:
```json
{
  "email": "parent@example.com",
  "first_name": "Jane",
  "last_name": "Doe"
}
```

**Optional Fields**:
```json
{
  "phone": "+9876543210",
  "password": "CustomPassword123"
}
```

### Response (HTTP 201 Created)

```json
{
  "success": true,
  "user": {
    "id": 456,
    "email": "parent@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "role": "parent",
    "role_display": "Родитель",
    "phone": "+9876543210",
    "avatar": null,
    "is_verified": false,
    "is_staff": false,
    "date_joined": "2025-11-27T10:35:00Z",
    "full_name": "Jane Doe"
  },
  "profile": {
    "id": 567,
    "user": {...},
    "children": []
  },
  "credentials": {
    "username": "parent@example.com",
    "email": "parent@example.com",
    "temporary_password": "XyZa5678BcDe"
  },
  "message": "Родитель успешно создан"
}
```

### Error Responses

**HTTP 400 Bad Request** - Missing required field:
```json
{
  "detail": "first_name и last_name обязательны"
}
```

**HTTP 409 Conflict** - Email already exists:
```json
{
  "detail": "Пользователь с этим email уже существует"
}
```

### Test Cases

#### Test 1: Valid Parent Creation
```bash
curl -X POST http://localhost:8000/api/admin/parents/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "email": "new_parent@example.com",
    "first_name": "Jane",
    "last_name": "Smith"
  }'
```

**Expected**:
- Status: 201
- Parent created in database
- ParentProfile created with empty children list
- Temporary password returned

#### Test 2: Missing Last Name
```bash
curl -X POST http://localhost:8000/api/admin/parents/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "email": "incomplete_parent@example.com",
    "first_name": "John"
  }'
```

**Expected**:
- Status: 400
- Error message about missing first_name/last_name

### Validation Rules

| Field | Required | Type | Validation |
|-------|----------|------|-----------|
| email | Yes | string | Must be unique, valid email format |
| first_name | Yes | string | Max 150 chars, non-empty |
| last_name | Yes | string | Max 150 chars, non-empty |
| phone | No | string | Max 20 chars |
| password | No | string | If not provided, 12-char random generated |

---

## T307: Assign Parent to Students Endpoint

### Endpoint Details

```
POST /api/admin/assign-parent/
```

### Implementation

- **File**: `backend/accounts/staff_views.py`
- **Function**: `assign_parent_to_students(request)`
- **Lines**: 1924-1993
- **Decorators**:
  - `@api_view(['POST'])`
  - `@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])`
  - `@permission_classes([IsStaffOrAdmin])`

### Request Payload

```json
{
  "parent_id": 456,
  "student_ids": [789, 790, 791]
}
```

### Response (HTTP 200 OK)

```json
{
  "success": true,
  "parent_id": 456,
  "assigned_students": [789, 790, 791],
  "message": "3 студентов успешно назначено родителю"
}
```

### Error Responses

**HTTP 400 Bad Request** - Missing or invalid fields:
```json
{
  "detail": "parent_id обязателен"
}
```

**HTTP 400 Bad Request** - Empty student list:
```json
{
  "detail": "student_ids должен быть непустым списком"
}
```

**HTTP 404 Not Found** - Parent doesn't exist:
```json
{
  "detail": "Родитель не найден"
}
```

### Test Cases

#### Test 1: Assign Parent to Single Student
```bash
curl -X POST http://localhost:8000/api/admin/assign-parent/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "parent_id": 456,
    "student_ids": [789]
  }'
```

**Expected**:
- Status: 200
- StudentProfile(user_id=789).parent = 456
- assigned_count = 1

#### Test 2: Assign Parent to Multiple Students
```bash
curl -X POST http://localhost:8000/api/admin/assign-parent/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "parent_id": 456,
    "student_ids": [789, 790, 791, 792, 793]
  }'
```

**Expected**:
- Status: 200
- All 5 students have parent_id = 456
- assigned_count = 5

#### Test 3: Invalid Parent ID
```bash
curl -X POST http://localhost:8000/api/admin/assign-parent/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "parent_id": 99999,
    "student_ids": [789]
  }'
```

**Expected**:
- Status: 404
- Error message about parent not found

#### Test 4: Empty Student List
```bash
curl -X POST http://localhost:8000/api/admin/assign-parent/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "parent_id": 456,
    "student_ids": []
  }'
```

**Expected**:
- Status: 400
- Error message about empty student_ids

### Validation Rules

| Field | Required | Type | Validation |
|-------|----------|------|-----------|
| parent_id | Yes | integer | Must be existing parent user, must be active |
| student_ids | Yes | array | Non-empty, all must be existing student users |

### Behavior

- **Atomic Operation**: Either all students are assigned or none (transaction)
- **Replacement**: If student already has a parent, it will be replaced
- **No Duplicates**: Assigning same parent multiple times is idempotent

---

## Helper Endpoint: Get Parents List

### Endpoint Details

```
GET /api/admin/parents/
```

### Implementation

- **File**: `backend/accounts/staff_views.py`
- **Function**: `list_parents(request)`
- **Lines**: 1996-2028

### Response (HTTP 200 OK)

```json
{
  "results": [
    {
      "id": 456,
      "user": {
        "id": 456,
        "email": "parent1@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        ...
      },
      "children": [
        {
          "id": 789,
          "email": "student1@example.com",
          ...
        }
      ],
      "children_count": 2
    }
  ]
}
```

---

## Integration Tests

### Test Suite Setup

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile, ParentProfile

User = get_user_model()

class AdminEndpointsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.client.force_login(self.admin)
```

### Test: T303 Create Student

```python
def test_create_student_success(self):
    response = self.client.post('/api/admin/students/create/', {
        'email': 'student@test.com',
        'first_name': 'John',
        'last_name': 'Doe',
        'grade': '10'
    }, content_type='application/json')

    self.assertEqual(response.status_code, 201)
    data = response.json()
    self.assertTrue(data['success'])
    self.assertEqual(data['user']['email'], 'student@test.com')

    # Verify database
    student = User.objects.get(id=data['user']['id'])
    self.assertEqual(student.role, 'student')
    self.assertTrue(hasattr(student, 'student_profile'))

def test_create_student_missing_grade(self):
    response = self.client.post('/api/admin/students/create/', {
        'email': 'student2@test.com',
        'first_name': 'Jane',
        'last_name': 'Smith'
    }, content_type='application/json')

    self.assertEqual(response.status_code, 400)
    data = response.json()
    self.assertIn('grade', data)
```

### Test: T305 Create Parent

```python
def test_create_parent_success(self):
    response = self.client.post('/api/admin/parents/create/', {
        'email': 'parent@test.com',
        'first_name': 'John',
        'last_name': 'Doe'
    }, content_type='application/json')

    self.assertEqual(response.status_code, 201)
    data = response.json()
    self.assertTrue(data['success'])

    # Verify database
    parent = User.objects.get(id=data['user']['id'])
    self.assertEqual(parent.role, 'parent')
    self.assertTrue(hasattr(parent, 'parent_profile'))
```

### Test: T307 Assign Parent

```python
def test_assign_parent_to_student(self):
    # Create parent and student
    parent = User.objects.create(
        email='parent@test.com',
        first_name='Jane',
        role='parent'
    )
    ParentProfile.objects.create(user=parent)

    student = User.objects.create(
        email='student@test.com',
        first_name='John',
        role='student'
    )
    StudentProfile.objects.create(user=student)

    # Assign parent to student
    response = self.client.post('/api/admin/assign-parent/', {
        'parent_id': parent.id,
        'student_ids': [student.id]
    }, content_type='application/json')

    self.assertEqual(response.status_code, 200)

    # Verify assignment
    student_profile = StudentProfile.objects.get(user=student)
    self.assertEqual(student_profile.parent_id, parent.id)
```

---

## Database Changes

### No migrations required

All models already exist:
- `User` model with role field (student, teacher, tutor, parent)
- `StudentProfile` with parent ForeignKey
- `ParentProfile` with reverse relation to StudentProfile

---

## Security

✓ All endpoints require authentication (TokenAuthentication or SessionAuthentication)
✓ All endpoints require IsStaffOrAdmin permission
✓ Input validation on all fields
✓ Unique email constraint enforced
✓ Database transactions ensure consistency
✓ Password auto-generated if not provided
✓ Credentials returned only once during creation

---

## Implementation Checklist

- [x] T303: Student creation endpoint implemented
- [x] T305: Parent creation endpoint implemented
- [x] T307: Parent assignment endpoint implemented
- [x] All endpoints registered in urls.py
- [x] All endpoints have proper permissions
- [x] All endpoints have input validation
- [x] All endpoints have error handling
- [x] All endpoints support Supabase sync with fallback
- [x] Password generation implemented
- [x] Audit logging added
- [x] Test cases documented

---

## Files Referenced

- `backend/accounts/staff_views.py` - Main endpoint implementations
- `backend/accounts/urls.py` - URL registration
- `backend/accounts/models.py` - User, StudentProfile, ParentProfile models
- `backend/accounts/serializers.py` - Data serialization (StudentCreateSerializer, etc.)
- `backend/accounts/permissions.py` - IsStaffOrAdmin permission class
