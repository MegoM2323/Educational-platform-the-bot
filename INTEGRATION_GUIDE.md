# Cache Integration Guide - T_REPORT_007

## Quick Start

Follow these steps to integrate the caching strategy into your reports application.

---

## Step 1: Update `reports/apps.py`

Register the signals in the app config:

```python
from django.apps import AppConfig

class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'
    verbose_name = 'Reports'

    def ready(self):
        """Register signals for cache invalidation."""
        import reports.signals  # noqa: F401
```

---

## Step 2: Update `reports/views.py`

Add the cache mixins to your viewsets:

```python
from reports.cache.mixins import RedisCacheMixin

class ReportViewSet(RedisCacheMixin, viewsets.ModelViewSet):
    """ViewSet для отчетов"""

    queryset = Report.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    # Enable caching
    cache_enabled = True
    cache_report_types = {
        'list': 'analytics',
        'retrieve': 'custom',
        'stats': 'analytics',
    }

    # ... rest of your viewset implementation

class StudentReportViewSet(RedisCacheMixin, viewsets.ModelViewSet):
    """ViewSet для отчетов студентов"""

    queryset = StudentReport.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    cache_enabled = True
    cache_report_types = {
        'list': 'default',
        'retrieve': 'analytics',
    }

    # ... rest of your viewset implementation

class TutorWeeklyReportViewSet(RedisCacheMixin, viewsets.ModelViewSet):
    """ViewSet для еженедельных отчетов тьютора"""

    queryset = TutorWeeklyReport.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    cache_enabled = True
    cache_report_types = {
        'list': 'default',
        'retrieve': 'analytics',
    }

    # ... rest of your viewset implementation

class TeacherWeeklyReportViewSet(RedisCacheMixin, viewsets.ModelViewSet):
    """ViewSet для еженедельных отчетов учителя"""

    queryset = TeacherWeeklyReport.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    cache_enabled = True
    cache_report_types = {
        'list': 'default',
        'retrieve': 'analytics',
    }

    # ... rest of your viewset implementation
```

---

## Step 3: Update `reports/urls.py`

Register the cache control viewset:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from reports.cache.views import CacheControlViewSet
from reports.views import (
    ReportViewSet,
    StudentReportViewSet,
    TutorWeeklyReportViewSet,
    TeacherWeeklyReportViewSet,
    ReportTemplateViewSet,
    AnalyticsDataViewSet,
    ReportScheduleViewSet,
    ReportStatsViewSet,
)

router = DefaultRouter()
router.register(r'cache', CacheControlViewSet, basename='cache')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'student-reports', StudentReportViewSet, basename='student-report')
router.register(r'tutor-reports', TutorWeeklyReportViewSet, basename='tutor-report')
router.register(r'teacher-reports', TeacherWeeklyReportViewSet, basename='teacher-report')
router.register(r'templates', ReportTemplateViewSet, basename='template')
router.register(r'analytics', AnalyticsDataViewSet, basename='analytics')
router.register(r'schedules', ReportScheduleViewSet, basename='schedule')
router.register(r'stats', ReportStatsViewSet, basename='stats')

urlpatterns = [
    path('api/reports/', include(router.urls)),
]
```

---

## Step 4: Optional - Add Cache Warming on Login

In your authentication view or login endpoint, add cache warming for teachers:

```python
from reports.cache import cache_strategy
from reports.models import Report

class LoginView(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def login(self, request):
        # ... your login logic ...

        user = request.user

        # Warm cache for teachers on login
        if user.role in ['teacher', 'tutor']:
            # Get popular reports
            popular_reports = Report.objects.filter(
                author=user
            ).order_by('-updated_at')[:10]

            report_ids = list(popular_reports.values_list('id', flat=True))

            # Warm cache
            cache_strategy.warm_cache_for_user(
                user_id=user.id,
                report_ids=report_ids,
                report_type='analytics'
            )

        return Response({'token': token, ...})
```

---

## Step 5: Verify Configuration

Check that your `.env` has Redis configured:

```bash
# .env
USE_REDIS_CACHE=True
REDIS_URL=redis://localhost:6379/0
```

---

## Step 6: Test the Integration

### 1. Test Cache Storage

```bash
# Start Django shell
python manage.py shell

# Create a test report
from reports.models import Report
from django.contrib.auth import get_user_model
from reports.cache import cache_strategy

User = get_user_model()
user = User.objects.first()

# Get a report
report = Report.objects.first()

# Save to cache
cache_strategy.set_report_cache(
    report_id=report.id,
    user_id=user.id,
    data={'progress': 50, 'grade': 'A'},
    report_type='analytics'
)

# Retrieve from cache
hit, data, etag = cache_strategy.get_report_cache(
    report_id=report.id,
    user_id=user.id
)

print(f"Hit: {hit}, Data: {data}, ETag: {etag}")
```

### 2. Test API Cache Statistics

```bash
# Get cache stats
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/reports/cache/stats/

# Get hit rate
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/reports/cache/hit-rate/

# Warm cache
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"report_ids": [1, 2, 3], "report_type": "analytics"}' \
  http://localhost:8000/api/reports/cache/warm/
```

### 3. Test ETag Headers

```bash
# First request (cache miss)
curl -v http://localhost:8000/api/reports/42/

# Note the ETag header
# e.g., ETag: "abc123def456..."

# Second request with If-None-Match (should get 304)
curl -v -H 'If-None-Match: "abc123def456..."' \
  http://localhost:8000/api/reports/42/

# Should see: HTTP/1.1 304 Not Modified
```

---

## Step 7: Monitor Cache Performance

### View Cache Hit Rate

```python
from reports.cache import cache_strategy

stats = cache_strategy.get_hit_rate(user_id=123)
print(f"Hit rate: {stats['hit_rate']}%")
print(f"Total requests: {stats['total_requests']}")
```

### Clear Cache if Needed

```python
from reports.cache import cache_strategy

# Clear all user cache
cache_strategy.invalidate_user_cache(user_id=123)

# Clear specific report
cache_strategy.invalidate_report_cache(report_id=42, user_id=123)
```

---

## Configuration Options

### TTL by Report Type

Edit `backend/reports/cache/strategy.py`:

```python
class ReportCacheStrategy:
    TTL_MAP = {
        "student_progress": 300,      # 5 minutes
        "grade_distribution": 900,    # 15 minutes
        "analytics": 1800,            # 30 minutes
        "custom": 3600,               # 1 hour
        "default": 600,               # 10 minutes
    }
```

### Cache Size Limits

Edit `backend/reports/cache/strategy.py`:

```python
class ReportCacheStrategy:
    MAX_CACHE_PER_USER = 50 * 1024 * 1024  # 50MB
```

### Disable Caching for Specific ViewSet

```python
class ReportViewSet(RedisCacheMixin, viewsets.ModelViewSet):
    cache_enabled = False  # Disable caching
```

### Disable Caching for Specific Action

Override in viewset:

```python
class ReportViewSet(RedisCacheMixin, viewsets.ModelViewSet):
    def list(self, request):
        # Temporarily disable cache
        self.cache_enabled = False
        return super().list(request)
```

---

## Troubleshooting

### Cache Not Working?

1. **Check Redis connection**:
```bash
redis-cli ping
# Should return: PONG
```

2. **Check Django cache config**:
```python
from django.core.cache import cache
cache.set('test', 'value', 10)
print(cache.get('test'))  # Should print: 'value'
```

3. **Check settings**:
```python
from django.conf import settings
print(settings.CACHES)
print(settings.USE_REDIS_CACHE)
```

### High Cache Miss Rate?

1. **Check invalidation signals**:
   - Are signals registered in `apps.py`?
   - Check logs for invalidation messages

2. **Check filter consistency**:
   - Different filter orders might create different cache keys
   - Filters are sorted, so this shouldn't happen

3. **Increase TTL**:
   - Edit `TTL_MAP` in `strategy.py`
   - Longer TTL = higher hit rate but staler data

### Cache Size Growing?

1. **Monitor Redis memory**:
```bash
redis-cli info memory
```

2. **Check for cache leaks**:
   - Ensure `invalidate_*` methods are called
   - Check signal logs for missed invalidations

3. **Reduce cache size**:
   - Lower `MAX_CACHE_PER_USER`
   - Reduce `TTL_MAP` values

---

## Performance Optimization Tips

1. **Use cache warming on login**
   - Preload top 10 reports for teachers
   - Reduces first request latency

2. **Adjust TTL by usage**
   - More frequently accessed = longer TTL
   - Rarely accessed = shorter TTL

3. **Monitor hit rate**
   - Target: > 75%
   - If < 50%, check invalidation logic

4. **Use pagination**
   - Cache only helps with repeated requests
   - Large result sets = larger cache, lower hit rate

---

## Logging & Debugging

### Enable Debug Logging

In `config/settings.py`:

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'reports.cache': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

### View Cache Logs

```bash
# Start server with debug logging
python manage.py runserver --settings=config.settings

# Look for messages like:
# DEBUG Cache HIT: report:42:123:abc
# DEBUG Cache MISS: report:99:456:xyz
# INFO Cache invalidated: 5 keys for user 123
```

---

## Next Steps

1. Run tests to verify integration:
```bash
cd backend
python reports/test_cache_simple.py
```

2. Monitor cache performance in production

3. Adjust TTL values based on actual usage patterns

4. Implement database materialized views (L2) for even better performance

5. Add cache monitoring dashboard in admin panel

---

## Support

For issues or questions:
1. Check the implementation report: `CACHE_IMPLEMENTATION_REPORT.md`
2. Review test examples: `backend/reports/test_cache_simple.py`
3. Check signal registration: `backend/reports/signals.py`
4. Review API examples: `backend/reports/cache/views.py`

---

## Integration Checklist

- [ ] Update `reports/apps.py` with signal registration
- [ ] Update `reports/views.py` with `RedisCacheMixin`
- [ ] Update `reports/urls.py` with cache router
- [ ] Verify `.env` has Redis configured
- [ ] Run tests: `python reports/test_cache_simple.py`
- [ ] Test API endpoints with curl
- [ ] Monitor cache hit rate
- [ ] Adjust TTL based on usage
- [ ] Deploy to production
- [ ] Monitor performance metrics

**Integration Status**: Ready to deploy ✅
