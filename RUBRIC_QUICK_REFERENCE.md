# Grading Rubric System - Quick Reference

## Task: T_ASSIGN_004

**Status**: COMPLETE | **Date**: 2025-12-27

---

## Models

### GradingRubric
```python
GradingRubric.objects.create(
    name="Assessment Rubric",
    description="Description here",
    created_by=teacher,
    is_template=True,
    total_points=100
)
```

**Key Fields**:
- `name`, `description` - Rubric metadata
- `created_by` - Teacher/tutor who created it
- `is_template` - Can other teachers clone it?
- `total_points` - Maximum points possible
- `is_deleted` - Soft delete flag

**Methods**:
- `.clone(new_creator)` - Create a copy for another teacher

### RubricCriterion
```python
RubricCriterion.objects.create(
    rubric=rubric,
    name="Content Quality",
    description="Quality of content",
    max_points=50,
    point_scales=[
        [50, "Excellent"],
        [40, "Good"],
        [30, "Fair"]
    ],
    order=1
)
```

**Key Fields**:
- `rubric` - Parent rubric
- `name`, `description` - Criterion details
- `max_points` - Points for this criterion
- `point_scales` - [[points, description], ...]
- `order` - Display order

---

## API Endpoints

### Rubric Management
```
GET    /api/rubrics/                  # List
POST   /api/rubrics/                  # Create
GET    /api/rubrics/{id}/             # Detail
PATCH  /api/rubrics/{id}/             # Update
DELETE /api/rubrics/{id}/             # Delete (soft)
GET    /api/rubrics/templates/        # Templates only
POST   /api/rubrics/{id}/clone/       # Clone
```

### Criterion Management
```
GET    /api/criteria/                 # List (filter by ?rubric=N)
POST   /api/criteria/                 # Create
PATCH  /api/criteria/{id}/            # Update
DELETE /api/criteria/{id}/            # Delete
```

---

## Common Operations

### Create Full Rubric with Criteria
```python
from assignments.models import GradingRubric, RubricCriterion

rubric = GradingRubric.objects.create(
    name="Essay Rubric",
    created_by=teacher,
    is_template=True,
    total_points=100
)

RubricCriterion.objects.create(
    rubric=rubric,
    name="Quality",
    max_points=50,
    point_scales=[[50, "Excellent"], [30, "Good"]],
    order=1
)
```

### Clone Template
```python
template = GradingRubric.objects.get(name="Standard Rubric")
cloned = template.clone(new_teacher)
# Result: name="Standard Rubric (копия)"
```

### Attach to Assignment
```python
assignment.rubric = rubric
assignment.save()
```

### Filter Rubrics
```python
# By creator
rubrics = GradingRubric.objects.filter(created_by=teacher)

# Templates only
templates = GradingRubric.objects.filter(is_template=True)

# Active (not deleted)
active = GradingRubric.objects.filter(is_deleted=False)
```

---

## Permissions

| Operation | Permission |
|-----------|-----------|
| Create rubric | Teacher/Tutor |
| Clone rubric | Teacher/Tutor |
| Update own rubric | Creator |
| Delete own rubric | Creator |
| View rubric | Authenticated |
| Add criteria to rubric | Creator |
| View criteria | Authenticated |

---

## Request Examples

### Create Rubric
```bash
POST /api/rubrics/
{
    "name": "Essay Assessment",
    "description": "For assessing essays",
    "is_template": true,
    "total_points": 100,
    "criteria": [
        {
            "name": "Content",
            "max_points": 50,
            "point_scales": [[50, "Excellent"], [30, "Good"]],
            "order": 1
        }
    ]
}
```

### Clone Rubric
```bash
POST /api/rubrics/1/clone/
# Returns: 201 Created with new rubric (name="X (копия)")
```

### List Templates
```bash
GET /api/rubrics/templates/
```

### Filter Criteria
```bash
GET /api/criteria/?rubric=1
```

---

## Validation Rules

### Point Scales
- ✓ Must be list of [points, description]
- ✓ At least one scale required
- ✓ Points: 0-max_points (integers)
- ✓ Descriptions: non-empty strings

### Rubric
- ✓ Name required, max 255 chars
- ✓ Total points ≥ 1
- ✓ Sum of criteria max_points ≤ total_points

### Criterion
- ✓ Name: required, unique within rubric
- ✓ Max points ≥ 1
- ✓ Valid point scales (see above)

---

## Error Codes

| Error | Cause | Fix |
|-------|-------|-----|
| 400 Bad Request | Invalid point scales | Check format: [[int, str], ...] |
| 400 Bad Request | Criteria sum exceeds total | Increase total_points or decrease criteria |
| 403 Forbidden | Not creator | Use your rubric or clone it |
| 404 Not Found | Rubric doesn't exist | Check ID |

---

## Files

| File | Purpose |
|------|---------|
| `backend/assignments/models.py` | GradingRubric, RubricCriterion models |
| `backend/assignments/serializers.py` | Rubric serializers |
| `backend/assignments/views_rubric.py` | API viewsets |
| `backend/assignments/urls_rubric.py` | URL routing |
| `backend/assignments/test_rubric_system.py` | Tests (35+ cases) |
| `docs/RUBRIC_SYSTEM.md` | Full documentation |
| `RUBRIC_SETUP_GUIDE.md` | Installation guide |
| `RUBRIC_QUICK_REFERENCE.md` | This file |

---

## Setup Steps

1. Run migration: `python manage.py migrate`
2. Register URLs in `config/urls.py`
3. Run tests: `pytest backend/assignments/test_rubric_system.py -v`
4. Create sample rubrics
5. Attach to assignments

---

## Testing

```bash
# Run all tests
pytest backend/assignments/test_rubric_system.py -v

# Run specific test class
pytest backend/assignments/test_rubric_system.py::TestGradingRubricModel -v

# Expected: 35+ tests passing
```

---

## Key Features

✓ Reusable templates
✓ Customizable point scales
✓ Soft delete support
✓ Cloning with auto-numbering
✓ Full permission model
✓ Comprehensive validation
✓ 35+ test cases
✓ Complete documentation

---

## Support Files

- **Setup**: `RUBRIC_SETUP_GUIDE.md`
- **Full Docs**: `docs/RUBRIC_SYSTEM.md`
- **Implementation**: `RUBRIC_IMPLEMENTATION_SUMMARY.md`
- **Tests**: `backend/assignments/test_rubric_system.py`

---

## Database Schema

```
GradingRubric
├── id (PK)
├── name (VARCHAR 255, indexed)
├── description (TEXT)
├── created_by_id (FK to User)
├── is_template (BOOLEAN)
├── total_points (INT, >=1)
├── is_deleted (BOOLEAN)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

RubricCriterion
├── id (PK)
├── rubric_id (FK)
├── name (VARCHAR 255, unique with rubric)
├── description (TEXT)
├── max_points (INT, >=1)
├── point_scales (JSON)
└── order (INT)
```

---

**Status**: All features implemented and tested
**Ready for**: Production deployment
