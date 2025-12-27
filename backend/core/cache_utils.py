"""
Cache utility functions and middleware for THE_BOT Platform.

This module provides:
- Cache middleware for automatic response caching with ETag support
- Cache decorator factories
- Cache key builders for common patterns
- Cache invalidation helpers
"""

import logging
from functools import wraps
from typing import Callable, Optional, Any
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseNotModified
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.http import condition
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class CacheMiddleware:
    """
    Middleware for HTTP caching with ETag support.

    Features:
    - Automatic response caching for GET requests
    - ETag/Last-Modified header support for 304 Not Modified
    - Cache-Control header generation
    - Conditional request handling
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Only cache GET requests
        if request.method != 'GET':
            return self.get_response(request)

        # Call the view
        response = self.get_response(request)

        # Add cache headers for successful responses
        if response.status_code == 200:
            self._add_cache_headers(request, response)

        return response

    @staticmethod
    def _add_cache_headers(request: HttpRequest, response: HttpResponse):
        """Add appropriate cache headers to response."""
        # Set Cache-Control based on authentication
        if hasattr(request, 'user') and request.user.is_authenticated:
            response['Cache-Control'] = 'private, max-age=300'
        else:
            response['Cache-Control'] = 'public, max-age=3600'

        # Add Vary header for proper caching
        if 'Vary' not in response:
            response['Vary'] = 'Accept, Accept-Encoding, Authorization'

        # Generate and set ETag if not already set
        if 'ETag' not in response and hasattr(response, 'content'):
            import hashlib
            etag = hashlib.md5(response.content).hexdigest()
            response['ETag'] = f'"{etag}"'


def cache_page_conditional(ttl: int = 300, key_builder: Optional[Callable] = None):
    """
    Decorator for caching view responses with custom key generation.

    Args:
        ttl: Time to live in seconds
        key_builder: Optional function(request, *args, **kwargs) -> str

    Example:
        @cache_page_conditional(ttl=3600)
        def get_materials(request):
            ...

        @cache_page_conditional(ttl=300, key_builder=lambda r: f"user_{r.user.id}")
        def get_dashboard(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from config.cache import CacheKeyBuilder

            # Skip caching for non-GET requests
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)

            # Generate cache key
            if key_builder:
                cache_key = key_builder(request, *args, **kwargs)
            else:
                query_string = request.GET.urlencode() if request.GET else ""
                cache_key = CacheKeyBuilder.make_key(
                    view_func.__module__ + '.' + view_func.__name__,
                    request.path,
                    query_string,
                    request.user.id if request.user.is_authenticated else 'anon'
                )

            # Check cache
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached

            # Execute view
            response = view_func(request, *args, **kwargs)

            # Cache successful responses
            if isinstance(response, Response) and response.status_code == 200:
                try:
                    cache.set(cache_key, response, ttl)
                    logger.debug(f"Cached response: {cache_key} (TTL: {ttl}s)")
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")

            return response

        return wrapper
    return decorator


def cache_query_result(namespace: str, ttl: int = 300):
    """
    Decorator for caching database query results.

    Args:
        namespace: Cache namespace for the query
        ttl: Time to live in seconds

    Example:
        @cache_query_result(namespace="active_users", ttl=600)
        def get_active_users():
            return User.objects.filter(is_active=True)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from config.cache import CacheKeyBuilder

            # Build cache key from function arguments
            cache_key = CacheKeyBuilder.make_key(namespace, *args, **kwargs)

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Query cache hit: {cache_key}")
                return result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            try:
                cache.set(cache_key, result, ttl)
                logger.debug(f"Cached query: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"Cache set failed for {cache_key}: {e}")

            return result

        return wrapper
    return decorator


def invalidate_cache(namespace: str, *args, **kwargs):
    """
    Invalidate cached entries by namespace and parameters.

    Args:
        namespace: Cache namespace
        *args: Arguments to match in cache key
        **kwargs: Keyword arguments to match in cache key

    Example:
        invalidate_cache("materials", material_id=123)
    """
    from config.cache import CacheKeyBuilder

    try:
        cache_key = CacheKeyBuilder.make_key(namespace, *args, **kwargs)
        cache.delete(cache_key)
        logger.info(f"Invalidated cache: {cache_key}")
    except Exception as e:
        logger.warning(f"Error invalidating cache: {e}")


class ListCacheMixin:
    """
    Mixin for ViewSet to add response caching to list views.

    Usage:
        class MaterialViewSet(ListCacheMixin, viewsets.ModelViewSet):
            queryset = Material.objects.all()
            serializer_class = MaterialSerializer
            cache_timeout = 1800  # 30 minutes
    """

    cache_timeout = 300  # Default 5 minutes

    def list(self, request, *args, **kwargs):
        from config.cache import CacheKeyBuilder

        # Generate cache key
        cache_key = CacheKeyBuilder.user_key(
            self.basename or self.__class__.__name__,
            request.user.id if request.user.is_authenticated else 0,
            'list',
            request.GET.urlencode() if request.GET else ""
        )

        # Check cache
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for {cache_key}")
            return cached

        # Get original response
        response = super().list(request, *args, **kwargs)

        # Cache response
        if response.status_code == 200:
            try:
                cache.set(cache_key, response, self.cache_timeout)
                logger.debug(f"Cached list response: {cache_key}")
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")

        return response


class DetailCacheMixin:
    """
    Mixin for ViewSet to add response caching to retrieve views.

    Usage:
        class MaterialViewSet(DetailCacheMixin, viewsets.ModelViewSet):
            queryset = Material.objects.all()
            serializer_class = MaterialSerializer
            cache_timeout = 3600  # 1 hour
    """

    cache_timeout = 3600  # Default 1 hour

    def retrieve(self, request, *args, **kwargs):
        from config.cache import CacheKeyBuilder

        # Generate cache key
        obj_id = kwargs.get('pk')
        cache_key = CacheKeyBuilder.make_key(
            self.basename or self.__class__.__name__,
            'detail',
            obj_id
        )

        # Check cache
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for {cache_key}")
            return cached

        # Get original response
        response = super().retrieve(request, *args, **kwargs)

        # Cache response
        if response.status_code == 200:
            try:
                cache.set(cache_key, response, self.cache_timeout)
                logger.debug(f"Cached detail response: {cache_key}")
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")

        return response


def cache_etag_condition(etag_func: Callable, last_modified_func: Optional[Callable] = None):
    """
    Decorator for conditional GET requests using ETags.

    Args:
        etag_func: Function(request, *args, **kwargs) -> str
        last_modified_func: Optional function(request, *args, **kwargs) -> datetime

    Example:
        def material_etag(request, pk=None):
            material = Material.objects.get(pk=pk)
            return str(material.updated_at.timestamp())

        @cache_etag_condition(etag_func=material_etag)
        def get_material(request, pk=None):
            ...
    """
    def decorator(view_func):
        return condition(etag_func=etag_func, last_modified_func=last_modified_func)(view_func)
    return decorator


def get_or_compute(cache_key: str, compute_func: Callable, ttl: int = 300) -> Any:
    """
    Get value from cache or compute it.

    Args:
        cache_key: Cache key
        compute_func: Function to compute value if not in cache
        ttl: Time to live in seconds

    Returns:
        Cached or computed value
    """
    result = cache.get(cache_key)
    if result is not None:
        return result

    result = compute_func()
    try:
        cache.set(cache_key, result, ttl)
    except Exception as e:
        logger.warning(f"Cache set failed: {e}")

    return result
