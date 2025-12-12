# Admin Statistics API Documentation

## Overview

Enhanced statistics endpoints for the admin panel. All endpoints require `IsAdminUser` permission (staff or superuser only).

**Base URL:** `/api/system/admin/stats/`

## Authentication

All endpoints require:
- User must be authenticated
- User must have `is_staff=True` OR `is_superuser=True`
- Returns `403 Forbidden` for non-admin users

## Endpoints

### 1. Dashboard Statistics

**GET** `/api/system/admin/stats/dashboard/`

Main dashboard statistics with user counts, activity metrics, and performance indicators.

**Response:**
```json
{
  "users": {
    "total": 150,
    "students": 80,
    "teachers": 20,
    "tutors": 10,
    "parents": 40
  },
  "activity": {
    "online_now": 0,
    "active_today": 85,
    "lessons_today": 12,
    "invoices_unpaid": 5
  },
  "performance": {
    "avg_student_progress": 65.5,
    "lessons_completed_this_week": 34,
    "revenue_this_month": 150000.0
  }
}
```

**Fields:**
- `users.total` - Total registered users
- `users.students` - Count of students
- `users.teachers` - Count of teachers
- `users.tutors` - Count of tutors
- `users.parents` - Count of parents
- `activity.online_now` - Currently online users (always 0, requires Redis)
- `activity.active_today` - Users logged in today
- `activity.lessons_today` - Lessons scheduled for today
- `activity.invoices_unpaid` - Unpaid invoices (sent, viewed, overdue)
- `performance.avg_student_progress` - Average student progress percentage
- `performance.lessons_completed_this_week` - Completed lessons in last 7 days
- `performance.revenue_this_month` - Total revenue from paid invoices this month (RUB)

---

### 2. User Statistics

**GET** `/api/system/admin/stats/users/`

Detailed user statistics with optional role filtering.

**Query Parameters:**
- `role` (optional) - Filter by role: `student`, `teacher`, `tutor`, `parent`

**Response (without role filter):**
```json
{
  "role": "all",
  "total": 150,
  "active": 145,
  "inactive": 5,
  "created_today": 3,
  "created_this_week": 15
}
```

**Response (with role=student):**
```json
{
  "role": "student",
  "total": 80,
  "active": 75,
  "inactive": 5,
  "by_grade": {
    "9A": 10,
    "9B": 12,
    "10A": 15,
    "11A": 8,
    "Не указан": 35
  },
  "created_today": 3,
  "created_this_week": 15
}
```

**Fields:**
- `role` - Requested role or "all"
- `total` - Total users with this role
- `active` - Users with is_active=True
- `inactive` - Users with is_active=False
- `by_grade` - (students only) Distribution by grade/class
- `created_today` - New users created today
- `created_this_week` - New users created in last 7 days

**Errors:**
- `400 Bad Request` - Invalid role parameter

---

### 3. Lesson Statistics

**GET** `/api/system/admin/stats/lessons/`

Statistics for scheduling.Lesson model (teacher-student lessons).

**Response:**
```json
{
  "total_lessons": 250,
  "lessons_today": 12,
  "lessons_this_week": 45,
  "by_status": {
    "pending": 5,
    "confirmed": 35,
    "completed": 210,
    "cancelled": 0
  },
  "avg_duration_minutes": 45
}
```

**Fields:**
- `total_lessons` - Total lessons in system
- `lessons_today` - Lessons scheduled for today
- `lessons_this_week` - Lessons in last 7 days
- `by_status` - Count of lessons by status (pending, confirmed, completed, cancelled)
- `avg_duration_minutes` - Average lesson duration in minutes

---

### 4. Invoice Statistics

**GET** `/api/system/admin/stats/invoices/`

Financial statistics for invoices.Invoice model.

**Response:**
```json
{
  "total_invoices": 120,
  "unpaid": 5,
  "paid": 115,
  "total_revenue": 250000.0,
  "paid_revenue": 245000.0,
  "unpaid_amount": 5000.0,
  "avg_invoice_amount": 2083.33,
  "overdue_count": 2
}
```

**Fields:**
- `total_invoices` - Total invoices in system
- `unpaid` - Invoices with status sent/viewed/overdue
- `paid` - Invoices with status paid
- `total_revenue` - Sum of all invoice amounts (RUB)
- `paid_revenue` - Sum of paid invoice amounts (RUB)
- `unpaid_amount` - Sum of unpaid invoice amounts (RUB)
- `avg_invoice_amount` - Average invoice amount (RUB)
- `overdue_count` - Invoices with overdue status

---

### 5. Knowledge Graph Statistics

**GET** `/api/system/admin/stats/knowledge-graph/`

Statistics for knowledge_graph system (lessons, elements, progress).

**Response:**
```json
{
  "total_lessons": 45,
  "total_elements": 200,
  "students_with_progress": 30,
  "avg_completion_rate": 45.5,
  "most_difficult_lesson": "Интегралы"
}
```

**Fields:**
- `total_lessons` - Total knowledge graph lessons in lesson bank
- `total_elements` - Total elements (problems, questions, theory, videos)
- `students_with_progress` - Unique students with at least one lesson progress
- `avg_completion_rate` - Average completion percentage across all lesson progress
- `most_difficult_lesson` - Lesson with lowest average completion (min 3 attempts)

---

## Implementation Details

### Database Queries

All functions use optimized queries:
- `aggregate()` for counting and summing
- `select_related()` for OneToOne/ForeignKey relations
- `prefetch_related()` for reverse relations (minimized)
- Query limits for expensive operations (e.g., lesson duration calculation)

### Performance

- Dashboard stats: ~5-7 queries
- User stats: ~2-4 queries (3-5 with grade distribution)
- Lesson stats: ~3-4 queries + iteration (limited to 1000 lessons)
- Invoice stats: ~2 queries
- Knowledge graph stats: ~4-5 queries

### Caching (Optional)

Statistics can be cached with Django cache framework:

```python
from django.core.cache import cache

def get_dashboard_stats():
    cache_key = 'admin_stats_dashboard'
    cached = cache.get(cache_key)
    if cached:
        return cached

    stats = {...}  # Calculate stats
    cache.set(cache_key, stats, 3600)  # Cache for 1 hour
    return stats
```

## Error Handling

All endpoints return standard error format:

```json
{
  "error": "Error message"
}
```

**Status codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid parameters
- `403 Forbidden` - Not admin user
- `500 Internal Server Error` - Server error

## Usage Examples

### cURL

```bash
# Dashboard stats
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://the-bot.ru/api/system/admin/stats/dashboard/

# User stats (all)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://the-bot.ru/api/system/admin/stats/users/

# User stats (students only)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://the-bot.ru/api/system/admin/stats/users/?role=student

# Lesson stats
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://the-bot.ru/api/system/admin/stats/lessons/
```

### JavaScript (Frontend)

```javascript
// Using fetch
const response = await fetch('/api/system/admin/stats/dashboard/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const stats = await response.json();
console.log('Total users:', stats.users.total);
```

## Files

- `backend/core/admin_stats.py` - Service functions (business logic)
- `backend/core/stats_views.py` - API views (endpoints)
- `backend/core/urls.py` - URL routing
- `backend/accounts/permissions.py` - IsAdminUser permission class

## Testing

Run manual verification:
```bash
cd backend
python manage.py shell < core/test_stats.py
```

Or test via HTTP:
```bash
# Create admin user first
python manage.py createsuperuser

# Start server
./start.sh

# Test endpoint
curl -u admin:password http://localhost:8000/api/system/admin/stats/dashboard/
```

## Security

- All endpoints protected by `IsAdminUser` permission
- Only staff/superuser can access
- No sensitive data exposed (passwords, tokens, etc.)
- Rate limiting recommended for production (DRF throttling)

## Future Enhancements

1. **Redis caching** - Cache stats for 1 hour to reduce DB load
2. **Real-time online users** - Track WebSocket connections in Redis
3. **Date range filters** - Add `?start_date=...&end_date=...` parameters
4. **Export to CSV/Excel** - Add download endpoints
5. **Charts data** - Add time-series data for graphs (daily/weekly/monthly)
