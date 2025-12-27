# Cache System - Usage Examples

Quick reference for using the caching system in THE_BOT platform.

## Quick Start

### 1. Cache API Response

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from config.cache import cache_response

@api_view(['GET'])
@cache_response(ttl=1800)  # Cache for 30 minutes
def list_materials(request):
    materials = Material.objects.all()
    serializer = MaterialSerializer(materials, many=True)
    return Response(serializer.data)
```

### 2. Per-User Cache

```python
@api_view(['GET'])
@cache_response(ttl=300, key_func=lambda r: f"user_{r.user.id}_dashboard")
def get_user_dashboard(request):
    data = get_dashboard_data(request.user)
    return Response(data)
```

### 3. Invalidate Cache on Save

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from config.cache import CacheInvalidator

@receiver(post_save, sender=Material)
def invalidate_material_cache(sender, instance, **kwargs):
    CacheInvalidator.invalidate_material(instance.id)
```

### 4. Cache ViewSet Responses

```python
from rest_framework import viewsets
from core.cache_utils import ListCacheMixin, DetailCacheMixin

class MaterialViewSet(ListCacheMixin, DetailCacheMixin, viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    cache_timeout = 1800  # 30 minutes

    # List and retrieve methods are automatically cached
```

### 5. Utility: Get or Compute

```python
from core.cache_utils import get_or_compute

# Get value from cache or compute it
count = get_or_compute(
    cache_key='active_users_count',
    compute_func=lambda: User.objects.filter(is_active=True).count(),
    ttl=600  # Cache for 10 minutes
)
```

## Cache Key Management

### Generate Cache Keys

```python
from config.cache import CacheKeyBuilder

# Simple key
key = CacheKeyBuilder.make_key('materials', 'list')
# Result: "thebot:production::materials:list"

# With parameters
key = CacheKeyBuilder.make_key('search', query='python', page=1)
# Result: "thebot:production::search:page=1:query=python"

# Per-user key
key = CacheKeyBuilder.user_key('notifications', user_id=42)
# Result: "thebot:production::user_42:notifications"
```

### Pattern Deletion

```python
from config.cache import CacheKeyBuilder
from django.core.cache import cache

# Delete all materials cache
pattern = CacheKeyBuilder.pattern_key('materials', '*')
cache.delete_pattern(pattern)
```

## Cache Invalidation

### Manual Invalidation

```python
from config.cache import CacheInvalidator

# Invalidate material caches
CacheInvalidator.invalidate_material(material_id=123)

# Invalidate all user caches
CacheInvalidator.invalidate_user_data(user_id=42)

# Clear dashboard cache
CacheInvalidator.clear_dashboard_cache(user_id=42)

# Invalidate assignment caches
CacheInvalidator.invalidate_assignments(assignment_id=456)
```

### Automatic Invalidation with Signals

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from config.cache import CacheInvalidator

@receiver(post_save, sender=Material)
def material_saved(sender, instance, created, **kwargs):
    # Invalidate cache when material is saved
    CacheInvalidator.invalidate_material(instance.id)
    if not created:
        # If updating, also invalidate user caches if material affects them
        pass

@receiver(post_delete, sender=Material)
def material_deleted(sender, instance, **kwargs):
    # Invalidate cache when material is deleted
    CacheInvalidator.invalidate_material(instance.id)
```

## Cache Configuration

### TTL Presets

```python
from config.cache import CACHE_TIMEOUTS

# Available presets:
CACHE_TIMEOUTS['default']           # 300 seconds (5 minutes)
CACHE_TIMEOUTS['short']             # 60 seconds (1 minute)
CACHE_TIMEOUTS['medium']            # 600 seconds (10 minutes)
CACHE_TIMEOUTS['long']              # 3600 seconds (1 hour)
CACHE_TIMEOUTS['static']            # 86400 seconds (24 hours)

# Endpoint-specific:
CACHE_TIMEOUTS['materials_list']    # 1800 seconds (30 minutes)
CACHE_TIMEOUTS['material_detail']   # 3600 seconds (1 hour)
CACHE_TIMEOUTS['reports']           # 300 seconds (5 minutes)
```

### Use Presets in Decorators

```python
from config.cache import cache_response, CACHE_TIMEOUTS

@cache_response(ttl=CACHE_TIMEOUTS['materials_list'])
def list_materials(request):
    # Cached for 30 minutes by default
    pass

@cache_response(ttl=CACHE_TIMEOUTS['material_detail'])
def get_material(request, pk):
    # Cached for 1 hour by default
    pass
```

## Cache Headers

### Generate Appropriate Headers

```python
from config.cache import get_cache_headers
from rest_framework.response import Response

def list_materials(request):
    materials = Material.objects.all()
    response = Response(MaterialSerializer(materials, many=True).data)

    # Add cache headers
    headers = get_cache_headers(ttl=1800, is_private=False)
    for header, value in headers.items():
        if value is not None:
            response[header] = value

    return response
```

### Header Examples

```python
# Public data (static files, materials list)
headers = get_cache_headers(ttl=3600, is_private=False)
# Result: {'Cache-Control': 'public, max-age=3600', 'Vary': 'Accept, ...'}

# Private data (user dashboard, profile)
headers = get_cache_headers(ttl=300, is_private=True)
# Result: {'Cache-Control': 'private, max-age=300', 'Vary': 'Accept, ...'}

# Real-time data (notifications, live feeds)
# Use no-cache instead:
response['Cache-Control'] = 'no-cache'
```

## Monitoring Cache

### Check Cache Stats

```bash
# GET endpoint (requires authentication)
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/core/cache-stats/

# Response example:
{
    "status": "success",
    "cache_stats": {
        "backend": "redis",
        "memory_usage": 2097152,
        "memory_usage_human": "2.0M",
        "keys_count": 1234,
        "evicted_keys": 5,
        "hit_rate": 78.5,
        "uptime_seconds": 86400
    }
}
```

### Check Cache Health

```bash
# GET endpoint (requires admin)
curl -H "Authorization: Token ADMIN_TOKEN" \
  http://localhost:8000/api/core/cache-health/

# Response example:
{
    "status": "healthy",
    "backend": "RedisCache",
    "tests": {
        "set": "passed",
        "get": "passed",
        "delete": "passed"
    }
}
```

### Clear Cache

```bash
# POST endpoint (requires admin)
curl -X POST -H "Authorization: Token ADMIN_TOKEN" \
  http://localhost:8000/api/core/cache-clear/

# Response:
{
    "status": "success",
    "message": "Cache cleared"
}
```

### Reset Statistics

```bash
# POST endpoint (requires admin)
curl -X POST -H "Authorization: Token ADMIN_TOKEN" \
  http://localhost:8000/api/core/cache-reset-stats/

# Response:
{
    "status": "success",
    "message": "Cache statistics reset"
}
```

## Advanced Usage

### Conditional Caching

```python
from core.cache_utils import cache_page_conditional

@cache_page_conditional(ttl=600)
def get_report(request, report_id):
    # Caches response for 10 minutes
    report = Report.objects.get(id=report_id)
    return Response(ReportSerializer(report).data)
```

### Cache Query Results

```python
from core.cache_utils import cache_query_result

@cache_query_result(namespace="active_users", ttl=600)
def get_active_users_count():
    return User.objects.filter(is_active=True).count()

# Usage:
count = get_active_users_count()  # Cached for 10 minutes
```

### ETag Support

```python
from core.cache_utils import cache_etag_condition

def material_etag(request, pk=None):
    """Generate ETag from material's updated_at timestamp"""
    material = Material.objects.get(pk=pk)
    return str(material.updated_at.timestamp())

@cache_etag_condition(etag_func=material_etag)
def get_material(request, pk=None):
    material = Material.objects.get(pk=pk)
    return Response(MaterialSerializer(material).data)

# Returns 304 Not Modified if client's ETag matches
```

## Common Patterns

### Cache Everything Except Login

```python
from config.cache import cache_response

class AuthViewSet(viewsets.ViewSet):
    @cache_response(ttl=1800)
    def list(self, request):
        # GET is cached
        pass

    def create(self, request):
        # POST (login) is not cached
        pass
```

### Per-Department Cache

```python
@cache_response(ttl=600, key_func=lambda r: f"dept_{r.user.department_id}")
def get_department_materials(request):
    # Cache separated by department
    materials = Material.objects.filter(department=request.user.department)
    return Response(MaterialSerializer(materials, many=True).data)
```

### Progressive Cache Warming

```python
from django.core.management.base import BaseCommand
from config.cache import CacheInvalidator

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Warm up cache for popular materials
        popular = Material.objects.filter(popular=True)[:100]
        for material in popular:
            # This forces cache population
            CacheInvalidator.invalidate_material(material.id)
        print(f"Warmed cache for {len(popular)} materials")
```

### Cache Expiration Tracking

```python
from django.core.cache import cache
from config.cache import CacheKeyBuilder

def check_cache_freshness(namespace):
    """Check if cache is fresh or expired"""
    key = CacheKeyBuilder.pattern_key(namespace)
    value = cache.get(key)
    return value is not None  # True if cached, False if expired
```

## Best Practices

### DO's ✓

```python
# DO: Use appropriate TTLs
@cache_response(ttl=CACHE_TIMEOUTS['materials_list'])  # ✓ Good
def list_materials(request):
    pass

# DO: Invalidate on save
@receiver(post_save, sender=Material)
def invalidate(sender, instance, **kwargs):  # ✓ Good
    CacheInvalidator.invalidate_material(instance.id)

# DO: Include user ID in cache key
key = CacheKeyBuilder.user_key('profile', user_id=42)  # ✓ Good

# DO: Use per-user cache for sensitive data
@cache_response(ttl=300, key_func=lambda r: f"user_{r.user.id}")  # ✓ Good
def get_private_data(request):
    pass
```

### DON'Ts ✗

```python
# DON'T: Cache sensitive data without user isolation
@cache_response(ttl=3600)  # ✗ Bad - no user isolation
def get_private_data(request):
    pass

# DON'T: Cache forever
@cache_response(ttl=999999999)  # ✗ Bad - never expires
def get_material(request):
    pass

# DON'T: Forget to invalidate
def update_material(request):
    material = Material.objects.get(id=request.data['id'])
    material.title = request.data['title']
    material.save()  # ✗ Cache not invalidated!
    return Response(MaterialSerializer(material).data)

# DON'T: Cache POST/PUT/DELETE requests
@cache_response(ttl=300)  # ✗ Bad - only GET should be cached
def create_material(request):
    pass
```

## Troubleshooting

### Cache Not Working?

```python
from django.core.cache import cache

# Test cache operations
cache.set('test', 'value', 300)
print(cache.get('test'))  # Should print 'value'

# Check if Redis is running
import redis
r = redis.Redis(host='localhost', port=6379, db=1)
print(r.ping())  # Should print True
```

### Cache Growing Too Large?

```bash
# Clear specific namespace
curl -X POST -H "Authorization: Token ADMIN_TOKEN" \
  -d '{"namespace": "materials"}' \
  http://localhost:8000/api/core/cache-clear/

# Check memory usage
curl -H "Authorization: Token ADMIN_TOKEN" \
  http://localhost:8000/api/core/cache-stats/
```

### Cache Not Invalidating?

```python
# Check if signal is registered
from django.db.models.signals import post_save
from your_app.signals import invalidate_cache

# Verify connection
print(post_save.receivers)

# Manual invalidation for testing
from config.cache import CacheInvalidator
CacheInvalidator.invalidate_material(1)
```

## Integration Checklist

- [ ] Add @cache_response decorators to list/detail endpoints
- [ ] Setup signal receivers for post_save invalidation
- [ ] Configure appropriate TTLs for each endpoint
- [ ] Add cache headers to responses
- [ ] Monitor cache stats: `/api/core/cache-stats/`
- [ ] Test cache invalidation with unit tests
- [ ] Document cache behavior in API docs
- [ ] Set up cache warming for popular data
- [ ] Configure Redis in production
- [ ] Monitor memory usage and hit rates

## Related Documentation

- See [CACHING_STRATEGY.md](docs/CACHING_STRATEGY.md) for detailed architecture
- See [config/cache.py](backend/config/cache.py) for API reference
- See [core/test_caching.py](backend/core/test_caching.py) for test examples
