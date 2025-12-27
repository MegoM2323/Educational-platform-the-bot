# Report N+1 Query Optimization (T_REPORT_002)

## Problem

The `ReportListSerializer` used `SerializerMethodField` with `.count()` calls on ManyToMany relationships:

```python
def get_target_students_count(self, obj):
    return obj.target_students.count()  # N+1 query!
```

For a list of 100 reports, this caused **300+ extra database queries**:
- 1 query to fetch all reports
- 100 queries for `target_students.count()` per report
- 100 queries for `target_parents.count()` per report
- 100 queries for `recipients.count()` per report

## Solution

### 1. ViewSet Optimization (views.py)

Added database annotations in `ReportViewSet.get_queryset()`:

```python
queryset = Report.objects.select_related(
    "author"
).prefetch_related(
    "target_students",
    "target_parents",
    "recipients",
).annotate(
    target_students_count=Count("target_students", distinct=True),
    target_parents_count=Count("target_parents", distinct=True),
    recipients_count=Count("recipients", distinct=True)
)
```

This moves count calculations into a single SQL query using database aggregation.

### 2. Serializer Optimization (serializers.py)

Updated `ReportListSerializer` methods to use annotations with smart fallback:

```python
def get_target_students_count(self, obj):
    # Use annotation if available (list view optimization)
    if hasattr(obj, "target_students_count"):
        return obj.target_students_count
    # Fallback for single object access
    return obj.target_students.count()
```

This ensures:
- **List views** use pre-calculated annotations (fast)
- **Detail views** still work with fallback to `.count()` (acceptable since single object)

## Performance Impact

### Before
- List 50 reports: ~150 queries (1 + 3 per report)
- List 100 reports: ~300 queries (1 + 3 per report)

### After
- List 50 reports: ~5-7 queries (1 list + 4 optimization queries)
- List 100 reports: ~5-7 queries (same as 50 reports!)
- Detail view: ~2-3 queries (fallback works fine)

### Query Breakdown (After Optimization)

For any list size:
1. SELECT reports... (with author JOINs)
2. SELECT COUNT(target_students) for each report (single aggregation query)
3. SELECT COUNT(target_parents) for each report (single aggregation query)
4. SELECT COUNT(recipients) for each report (single aggregation query)
5. Prefetch related data (bulk loading, not N+1)

## Database Requirements

- Uses Django's `Count()` with `distinct=True` for ManyToMany fields
- Compatible with PostgreSQL, MySQL, SQLite
- No migrations required (annotations are query-level only)

## Testing

Run tests to verify N+1 fix:
```bash
cd backend
pytest tests/test_reports_n1_queries.py -v
```

Key test cases:
1. `test_report_list_query_count` - Verifies <15 queries for 50 reports
2. `test_annotation_presence_in_list` - Confirms annotations are present
3. `test_serializer_fallback_without_annotation` - Verifies fallback logic

## Files Modified

1. `/backend/reports/views.py` - Added annotations in `ReportViewSet.get_queryset()`
2. `/backend/reports/serializers.py` - Updated serializer methods with fallback logic

## Backward Compatibility

✓ Fully backward compatible
✓ No API changes
✓ No database migrations needed
✓ Serializer works with or without annotations
✓ Detail views unaffected

## Future Improvements

1. Consider using `select_related()` for `report__author` in ReportRecipient queries
2. Add similar optimization to StudentReport, TeacherWeeklyReport, TutorWeeklyReport
3. Monitor slow query logs for other N+1 issues in reports app

## References

- Django optimization docs: https://docs.djangoproject.com/en/5.0/topics/db/optimization/
- Count() with distinct: https://docs.djangoproject.com/en/5.0/ref/models/querysets/#count
- Prefetch vs Select Related: https://docs.djangoproject.com/en/5.0/ref/models/querysets/#prefetch-related
