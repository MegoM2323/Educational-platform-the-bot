# Grading Rubric System - Setup Guide

## Installation & Configuration

This guide walks through integrating the Grading Rubric System (T_ASSIGN_004) into your Django project.

## Step 1: Database Migration

### Create Migration
```bash
cd backend
python manage.py makemigrations assignments --name add_grading_rubric_system
```

### Expected Output
The migration will create:
- `GradingRubric` table with columns: id, name, description, created_by_id, is_template, total_points, is_deleted, created_at, updated_at
- `RubricCriterion` table with columns: id, rubric_id, name, description, max_points, point_scales (JSON), order
- Database indexes for performance

### Apply Migration
```bash
python manage.py migrate
```

## Step 2: URL Registration

### Option A: Register in Main URLs (Recommended)

**File**: `backend/config/urls.py`

Add the rubric URLs to your main URL configuration:

```python
from django.urls import include, path

urlpatterns = [
    # ... existing URLs ...
    path('api/assignments/', include('assignments.urls')),
    path('api/', include('assignments.urls_rubric')),
]
```

### Option B: Register in API Router

If using Django REST Framework's router:

```python
from rest_framework.routers import DefaultRouter
from assignments.views_rubric import GradingRubricViewSet, RubricCriterionViewSet

router = DefaultRouter()
router.register(r'rubrics', GradingRubricViewSet, basename='rubric')
router.register(r'criteria', RubricCriterionViewSet, basename='criterion')

urlpatterns = [
    path('api/', include(router.urls)),
]
```

## Step 3: Verify Installation

### Check Models
```bash
python manage.py shell
>>> from assignments.models import GradingRubric, RubricCriterion
>>> GradingRubric.objects.all()
<QuerySet []>
```

### Test API Endpoints
```bash
# Start development server
python manage.py runserver

# In another terminal, test endpoints
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/rubrics/

# Expected: 200 OK with empty results array
```

## Step 4: Create Test Data (Optional)

### Script to Create Sample Rubric

```python
# Create test data script
from django.contrib.auth import get_user_model
from assignments.models import GradingRubric, RubricCriterion

User = get_user_model()

# Get or create teacher
teacher, _ = User.objects.get_or_create(
    email='teacher@example.com',
    defaults={
        'first_name': 'Sample',
        'last_name': 'Teacher',
        'role': 'teacher',
        'password': 'hashed_password'
    }
)

# Create template rubric
rubric = GradingRubric.objects.create(
    name="Standard Essay Rubric",
    description="Standard rubric for assessing essays",
    created_by=teacher,
    is_template=True,
    total_points=100
)

# Add criteria
criteria_data = [
    {
        "name": "Thesis Quality",
        "description": "Clarity and strength of thesis statement",
        "max_points": 25,
        "point_scales": [
            [25, "Exceptional - Clear, original thesis"],
            [20, "Strong - Clear, focused thesis"],
            [15, "Adequate - Thesis present but could be stronger"],
            [10, "Weak - Unclear or missing thesis"],
            [0, "No thesis"]
        ],
        "order": 1
    },
    {
        "name": "Evidence & Support",
        "description": "Quality and relevance of supporting evidence",
        "max_points": 25,
        "point_scales": [
            [25, "Exceptional - Strong, relevant evidence"],
            [20, "Strong - Relevant evidence supports thesis"],
            [15, "Adequate - Some relevant evidence"],
            [10, "Weak - Limited or weak evidence"],
            [0, "No evidence"]
        ],
        "order": 2
    },
    {
        "name": "Organization",
        "description": "Logical flow and structure of argument",
        "max_points": 25,
        "point_scales": [
            [25, "Exceptional - Excellent flow and structure"],
            [20, "Strong - Clear organization"],
            [15, "Adequate - Basic structure, mostly clear"],
            [10, "Weak - Difficult to follow"],
            [0, "Disorganized"]
        ],
        "order": 3
    },
    {
        "name": "Writing Quality",
        "description": "Grammar, clarity, and style",
        "max_points": 25,
        "point_scales": [
            [25, "Exceptional - Excellent grammar and style"],
            [20, "Strong - Clear writing, minor errors"],
            [15, "Adequate - Generally clear, some errors"],
            [10, "Weak - Multiple errors affect clarity"],
            [0, "Poor - Difficult to read"]
        ],
        "order": 4
    }
]

for data in criteria_data:
    RubricCriterion.objects.create(rubric=rubric, **data)

print(f"Created rubric: {rubric.name}")
print(f"Total criteria: {rubric.criteria.count()}")
```

Run the script:
```bash
python manage.py shell < create_rubric.py
```

## Step 5: Run Tests

### Run All Rubric Tests
```bash
pytest backend/assignments/test_rubric_system.py -v
```

### Run Specific Test Class
```bash
pytest backend/assignments/test_rubric_system.py::TestGradingRubricModel -v
```

### Expected Output
```
test_rubric_system.py::TestGradingRubricModel::test_create_rubric PASSED
test_rubric_system.py::TestGradingRubricModel::test_rubric_string_representation PASSED
test_rubric_system.py::TestGradingRubricModel::test_create_rubric_with_criteria PASSED
...

======================== 35 passed in 2.34s ========================
```

## Step 6: Access Documentation

View complete API documentation:

1. **User Guide**: `docs/RUBRIC_SYSTEM.md`
2. **Implementation Details**: `RUBRIC_IMPLEMENTATION_SUMMARY.md`
3. **This Setup Guide**: `RUBRIC_SETUP_GUIDE.md`

## Troubleshooting

### Issue: Import Error

```
ImportError: cannot import name 'GradingRubric' from 'assignments.models'
```

**Solution**: Ensure migration was applied
```bash
python manage.py migrate
python manage.py check
```

### Issue: Endpoint Returns 404

```
GET /api/rubrics/ → 404 Not Found
```

**Solution**: Check URL configuration in `config/urls.py`:
```python
# Make sure this is included:
path('api/', include('assignments.urls_rubric')),
```

### Issue: Permission Denied Creating Rubric

```
POST /api/rubrics/ → 403 Forbidden
```

**Solution**: Ensure user has teacher/tutor role:
```python
user.role = "teacher"  # or "tutor"
user.save()
```

### Issue: Validation Error for Point Scales

```
"point_scales": ["Each scale must be [points, description]"]
```

**Solution**: Ensure correct format:
```json
// Correct
"point_scales": [[50, "Excellent"], [40, "Good"]]

// Incorrect - missing description
"point_scales": [[50], [40]]

// Incorrect - not a list
"point_scales": "[[50, 'Excellent']]"
```

## Performance Considerations

### Indexes Created
The migration automatically creates these indexes:

- `(created_by, is_template)` - Filter by creator and type
- `(is_deleted, is_template)` - Filter active templates
- `(rubric, order)` - Sort criteria

### Query Optimization

When retrieving rubrics with criteria:
```python
# Good - uses prefetch_related
from django.db.models import Prefetch
rubrics = GradingRubric.objects.prefetch_related('criteria')

# Slow - causes N+1 queries
rubrics = GradingRubric.objects.all()
for rubric in rubrics:
    print(rubric.criteria.all())  # Extra query per rubric!
```

## Django Admin Integration

To manage rubrics in Django Admin, add to `assignments/admin.py`:

```python
from django.contrib import admin
from .models import GradingRubric, RubricCriterion

@admin.register(GradingRubric)
class GradingRubricAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'is_template', 'total_points', 'created_at')
    list_filter = ('is_template', 'is_deleted', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Settings', {
            'fields': ('is_template', 'total_points', 'is_deleted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(RubricCriterion)
class RubricCriterionAdmin(admin.ModelAdmin):
    list_display = ('name', 'rubric', 'max_points', 'order')
    list_filter = ('rubric', 'order')
    search_fields = ('name', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('rubric', 'name', 'description')
        }),
        ('Scoring', {
            'fields': ('max_points', 'point_scales', 'order')
        }),
    )
```

## Integration with Assignments

Once installed, attach rubrics to assignments:

```python
from assignments.models import Assignment, GradingRubric

assignment = Assignment.objects.get(id=1)
rubric = GradingRubric.objects.get(id=1)

assignment.rubric = rubric
assignment.save()
```

## Next Steps

1. **Create Templates**: Create reusable template rubrics
2. **Train Teachers**: Teach teachers how to use the system
3. **Monitor Usage**: Track rubric adoption and effectiveness
4. **Iterate**: Gather feedback and improve

## Support & Documentation

- **Full Documentation**: See `docs/RUBRIC_SYSTEM.md`
- **Implementation Details**: See `RUBRIC_IMPLEMENTATION_SUMMARY.md`
- **Test Examples**: See `backend/assignments/test_rubric_system.py`

## Files Included

```
backend/
├── assignments/
│   ├── models.py                    (Modified - Added GradingRubric, RubricCriterion)
│   ├── serializers.py               (Modified - Added rubric serializers)
│   ├── views_rubric.py              (NEW - Rubric viewsets)
│   ├── urls_rubric.py               (NEW - Rubric URL routing)
│   └── test_rubric_system.py        (NEW - Comprehensive tests)
│
docs/
└── RUBRIC_SYSTEM.md                 (NEW - User documentation)

RUBRIC_SETUP_GUIDE.md                (NEW - This file)
RUBRIC_IMPLEMENTATION_SUMMARY.md     (NEW - Implementation details)
```

## Configuration Checklist

- [ ] Migration created and applied
- [ ] URLs registered in `config/urls.py`
- [ ] Tests running successfully
- [ ] Sample data created
- [ ] Django Admin configured
- [ ] Documentation reviewed
- [ ] Team trained on usage

## Version Information

- **Feature**: Grading Rubric System
- **Task ID**: T_ASSIGN_004
- **Status**: Complete
- **Django Version**: 5.2+
- **Django REST Framework**: 3.14+
- **Python**: 3.10+
