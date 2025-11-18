# Cache Invalidation Guide

## Overview

This document describes the cache invalidation strategy for THE BOT Platform, ensuring parent dashboards and other user interfaces automatically update when data changes.

## Architecture

### Backend Cache Patterns

The backend uses `DashboardCacheManager` (defined in `materials/cache_utils.py`) to manage Redis cache invalidation patterns:

```python
# Student cache patterns
student_materials:{student_id}:*
student_progress:{student_id}
student_dashboard_data:{student_id}:*

# Teacher cache patterns
teacher_students:{teacher_id}
teacher_materials:{teacher_id}:*
teacher_dashboard_data:{teacher_id}:*

# Parent cache patterns
parent_children:{parent_id}
parent_child_progress:{parent_id}:*
parent_dashboard_data:{parent_id}:*
```

### Frontend TanStack Query Keys

The frontend uses TanStack Query for cache management. Key query keys:

```typescript
// Parent dashboard
['parent-dashboard']
['parent-children']
['parent-child-subjects', childId]

// Student dashboard
['student-dashboard']
['student-materials']
['student-progress']

// Teacher dashboard
['teacher-dashboard']
['teacher-students']
['teacher-materials']

// Reports
['teacher-weekly-reports']
['tutor-weekly-reports']
['student-reports', studentId]
```

## Automatic Invalidation (Django Signals)

### SubjectEnrollment Changes

**Signal:** `post_save`, `post_delete` on `SubjectEnrollment`
**File:** `materials/signals.py`
**Invalidates:**
- Student cache (student who was enrolled/unenrolled)
- Teacher cache (teacher assigned to subject)
- **Parent cache** (parent of the student)

**When triggered:**
- Tutor assigns subject to student
- Subject enrollment is deleted
- Enrollment is modified

### StudyPlan Changes

**Signal:** `post_save`, `post_delete` on `StudyPlan`
**File:** `materials/signals.py`
**Invalidates:**
- Student cache (student receiving the plan)
- Teacher cache (teacher who created the plan)
- **Parent cache** (parent of the student)

**When triggered:**
- Teacher creates study plan
- Teacher sends study plan (status changes to 'sent')
- Study plan is modified or deleted

### Material Changes

**Signal:** `post_save`, `post_delete` on `Material`
**File:** `materials/signals.py`
**Invalidates:**
- Student caches (all students assigned to material)
- Teacher cache (material author)

### MaterialProgress Changes

**Signal:** `post_save`, `post_delete` on `MaterialProgress`
**File:** `materials/signals.py`
**Invalidates:**
- Student cache
- Teacher cache (material author)
- **Parent cache** (parent of the student)

### StudentProfile Changes

**Signal:** `post_save` on `StudentProfile`
**File:** `materials/signals.py`
**Invalidates:**
- Student cache
- **Parent cache** (on create or update)

## Manual Invalidation (View Layer)

In addition to automatic signals, we explicitly invalidate parent cache in critical views:

### 1. Tutor Subject Assignment

**File:** `accounts/tutor_views.py`
**View:** `TutorStudentsViewSet.subjects()` (POST)
**Line:** ~327-341

```python
# After successful subject assignment
cache_manager = DashboardCacheManager()
parent = getattr(student_profile, 'parent', None)
if parent:
    cache_manager.invalidate_parent_cache(parent.id)
```

**Why explicit invalidation:**
- Ensures immediate parent dashboard refresh
- Provides detailed logging for debugging
- Complements signal-based invalidation

### 2. Teacher Study Plan Sending (POST endpoint)

**File:** `materials/teacher_dashboard_views.py`
**View:** `send_study_plan()`
**Line:** ~813-829

```python
# After changing status to SENT
cache_manager = DashboardCacheManager()
parent = getattr(student.student_profile, 'parent', None)
if parent:
    cache_manager.invalidate_parent_cache(parent.id)
```

### 3. Teacher Study Plan Sending (PATCH endpoint)

**File:** `materials/teacher_dashboard_views.py`
**View:** `teacher_study_plan_detail()` (PATCH)
**Line:** ~772-788

```python
# When status changes to SENT via PATCH
if status_changed_to_sent:
    cache_manager = DashboardCacheManager()
    parent = getattr(student.student_profile, 'parent', None)
    if parent:
        cache_manager.invalidate_parent_cache(parent.id)
```

## Query Key Invalidation Requirements

### Parent Dashboard Update Scenarios

When these actions occur, parent dashboard should refresh:

1. **Tutor assigns subject to student**
   - Backend: Invalidates `parent_dashboard_data:{parent_id}:*`
   - Frontend should refetch: `['parent-dashboard']`, `['parent-child-subjects', childId]`

2. **Teacher sends study plan to student**
   - Backend: Invalidates `parent_dashboard_data:{parent_id}:*`
   - Frontend should refetch: `['parent-dashboard']`, study plan related queries

3. **Student progress updated**
   - Backend: Invalidates `parent_child_progress:{parent_id}:*`
   - Frontend should refetch: `['parent-dashboard']`, `['student-progress']`

4. **Student profile modified**
   - Backend: Invalidates `parent_children:{parent_id}`, `parent_dashboard_data:{parent_id}:*`
   - Frontend should refetch: `['parent-children']`, `['parent-dashboard']`

## Testing Cache Invalidation

### Backend Testing

```python
from materials.cache_utils import DashboardCacheManager
from materials.models import SubjectEnrollment

# Test explicit invalidation
cache_manager = DashboardCacheManager()
cache_manager.invalidate_parent_cache(parent_id=1)

# Test signal-based invalidation
enrollment = SubjectEnrollment.objects.create(...)
# Parent cache should be automatically invalidated
```

### Frontend Testing

```typescript
// In parent dashboard component
const { data, refetch } = useQuery({
  queryKey: ['parent-dashboard'],
  queryFn: fetchParentDashboard,
});

// After tutor assigns subject, parent dashboard should auto-refresh
// due to backend invalidation signaling
```

## Debugging

### Backend Logs

When parent cache is invalidated, look for these log messages:

```
Parent cache invalidated: parent_id=X, student_id=Y, enrollment_id=Z
Parent cache invalidated after study plan sent: plan_id=X, parent_id=Y, student_id=Z
Parent cache invalidated via StudyPlan signal: plan_id=X, parent_id=Y, student_id=Z, status=sent
```

### Redis Commands

Check what's in cache:

```bash
redis-cli KEYS "parent_dashboard_data:*"
redis-cli KEYS "parent_children:*"
redis-cli KEYS "parent_child_progress:*"
```

Delete patterns manually:

```bash
redis-cli --scan --pattern "parent_dashboard_data:1:*" | xargs redis-cli DEL
```

## Performance Considerations

1. **Signal overhead:** Minimal - signals run in same transaction
2. **Redis performance:** Pattern deletion is fast, O(N) where N = matching keys
3. **Frontend refetch:** Only happens when parent is actively viewing dashboard

## Best Practices

1. **Always use DashboardCacheManager** - Don't access cache directly
2. **Log invalidations in production** - Helps debug stale data issues
3. **Fail silently** - Cache errors shouldn't break functionality
4. **Combine signals + explicit invalidation** - Provides redundancy

## Future Enhancements

1. **WebSocket notifications:** Push real-time updates to frontend
2. **Selective invalidation:** Only invalidate specific dashboard sections
3. **Cache warming:** Pre-populate cache for frequently accessed data
4. **Metrics:** Track cache hit/miss rates per user type

---

**Last Updated:** 2025-11-17
**Maintainer:** Django Core Architect
