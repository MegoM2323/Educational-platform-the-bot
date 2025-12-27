"""
Sentry error tracking configuration.

Integrates Sentry SDK for Django and Celery with:
- Environment separation (development, staging, production)
- Source maps support
- Error fingerprinting and grouping
- User context attachment
- Performance monitoring
- Custom alert rules
"""

import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

# SQLAlchemy интеграция опциональна
try:
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    HAS_SQLALCHEMY = True
except (ImportError, Exception):
    # Может выбросить DidNotEnable если sqlalchemy не установлен
    HAS_SQLALCHEMY = False
    SqlalchemyIntegration = None


def init_sentry(settings):
    """
    Initialize Sentry SDK with Django and Celery integrations.

    Args:
        settings: Django settings module with SENTRY_DSN and ENVIRONMENT

    Environment Variables:
        SENTRY_DSN: Sentry Data Source Name (project key)
        ENVIRONMENT: Environment name (development, staging, production)
        SENTRY_TRACES_SAMPLE_RATE: Performance monitoring sample rate (0.0-1.0)
        SENTRY_PROFILES_SAMPLE_RATE: Profiling sample rate (0.0-1.0)
    """

    sentry_dsn = os.getenv('SENTRY_DSN')
    environment = os.getenv('ENVIRONMENT', 'production').lower()
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    # Skip Sentry initialization in test environment or if DSN is not configured
    if environment == 'test' or not sentry_dsn:
        return

    # Determine trace sample rate based on environment
    # Production: 10%, Staging: 50%, Development: 100%
    traces_sample_rate = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', {
        'development': '1.0',
        'staging': '0.5',
        'production': '0.1'
    }.get(environment, '0.1')))

    # Profiling sample rate (subset of traces)
    profiles_sample_rate = float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', {
        'development': '1.0',
        'staging': '0.1',
        'production': '0.01'
    }.get(environment, '0.01')))

    sentry_sdk.init(
        dsn=sentry_dsn,

        # Environment separation
        environment=environment,
        debug=debug,

        # Release identification for source maps
        release=os.getenv('SENTRY_RELEASE', 'unknown'),

        # Integrations
        integrations=[
            DjangoIntegration(
                # Track database queries
                database_events=True,
                # Track cache operations
                cache_spans=True,
                # Middleware to capture request/response
                middleware_spans=True,
            ),
            CeleryIntegration(
                # Monitor task execution
                monitor_beat_tasks=True,
                # Track task results
                propagate_traces=True,
            ),
            RedisIntegration(),
            LoggingIntegration(
                # Capture logs at INFO level and above
                level=10,  # logging.DEBUG
                # Send logs that are ERROR and above to Sentry
                event_level=40,  # logging.ERROR
            ),
        ] + ([SqlalchemyIntegration()] if HAS_SQLALCHEMY else []),

        # Performance monitoring
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,

        # Source maps configuration
        # Sentry can match minified source maps to original source
        include_source_context=True,

        # Exception information
        attach_stacktrace=True,

        # Request body capture for debugging
        request_bodies='small',  # Capture small request bodies

        # Sensitive data filtering
        before_send=_before_send,
        before_send_transaction=_before_send_transaction,

        # Error filtering - ignore certain errors
        ignore_errors=[
            # Ignore common browser-related errors
            'NetworkError',
            'TimeoutError',
            # Ignore specific Django exceptions
            'django.http.response.Http404',
        ],

        # URL patterns to ignore
        ignore_transactions=[
            # Health check endpoints
            r'^GET /api/system/health/',
            r'^GET /api/system/readiness/',
            # Static files
            r'^GET /static/',
            r'^GET /assets/',
            # Admin actions that don't need monitoring
            r'^GET /admin/',
        ],
    )


def _before_send(event, hint):
    """
    Filter events before sending to Sentry.

    - Redact sensitive information (passwords, tokens)
    - Skip low-priority errors
    - Add custom fingerprinting

    Args:
        event: Sentry event dictionary
        hint: Exception hint with traceback info

    Returns:
        Modified event or None to drop the event
    """

    # Get exception info if available
    if 'exception' in event:
        exc_info = event['exception']
        if isinstance(exc_info, dict) and 'values' in exc_info:
            for exception in exc_info['values']:
                # Skip rate limit errors (429) - normal in high-load
                if exception.get('type') == 'Http429':
                    return None

                # Skip connection errors that are transient
                if exception.get('type') in ['ConnectionError', 'TimeoutError']:
                    # Only send if there's user context (actual user impact)
                    if not event.get('user'):
                        return None

    # Redact sensitive headers
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']

        # List of sensitive header patterns
        sensitive_patterns = [
            'authorization',
            'cookie',
            'x-token',
            'x-api-key',
            'password',
        ]

        for pattern in sensitive_patterns:
            for key in list(headers.keys()):
                if pattern.lower() in key.lower():
                    headers[key] = '[REDACTED]'

    # Add fingerprinting for error grouping
    if 'exception' in event:
        _add_fingerprinting(event)

    return event


def _before_send_transaction(event, hint):
    """
    Filter transactions before sending to Sentry.

    - Sample based on status codes
    - Skip slow but normal operations
    - Add custom tags

    Args:
        event: Sentry transaction event
        hint: Hint dictionary

    Returns:
        Modified event or None to drop the transaction
    """

    # Sample more aggressively for successful requests
    if event.get('status') == 'ok':
        import random
        # Sample 50% of successful transactions in production
        if os.getenv('ENVIRONMENT', 'production').lower() == 'production':
            if random.random() > 0.5:
                return None

    # Add performance tags
    if 'measurements' in event:
        measurements = event['measurements']

        # Tag slow transactions
        if 'duration' in measurements:
            duration = measurements['duration']['value']
            if duration > 2000:  # > 2 seconds
                if 'tags' not in event:
                    event['tags'] = {}
                event['tags']['performance_issue'] = 'slow_transaction'

    return event


def _add_fingerprinting(event):
    """
    Add custom fingerprinting for intelligent error grouping.

    Groups similar errors together even if stack traces differ slightly.
    This prevents error explosion from the same root cause.

    Args:
        event: Sentry event dictionary (modified in-place)
    """

    if 'exception' not in event or 'values' not in event['exception']:
        return

    fingerprint = []
    exception = event['exception']['values'][0] if event['exception']['values'] else None

    if not exception:
        return

    exc_type = exception.get('type', 'Unknown')
    exc_module = exception.get('module', '')

    # Group by exception type and module
    fingerprint.append(exc_type)

    # Add module for context
    if exc_module:
        fingerprint.append(exc_module.split('.')[-1])  # Last part of module

    # Special handling for common exceptions
    if exc_type == 'ValidationError':
        # Group validation errors by field (if available)
        if 'value' in exception and exception['value']:
            value = exception['value']
            if 'message' in value:
                # Extract field name if present
                message = value['message']
                if '.' in message:
                    field = message.split('.')[0]
                    fingerprint.append(field)

    elif exc_type == 'IntegrityError':
        # Group database constraint violations by constraint
        if 'value' in exception:
            value = exception['value']
            if 'UNIQUE constraint' in str(value):
                fingerprint.append('unique_constraint')
            elif 'FOREIGN KEY constraint' in str(value):
                fingerprint.append('foreign_key_constraint')

    elif exc_type == 'Http404' or exc_type == 'NotFound':
        # Group 404s by path pattern, not exact path
        if 'request' in event and 'url' in event['request']:
            url = event['request']['url']
            # Use path without ID numbers
            path_parts = url.split('/')
            normalized_path = '/'.join(
                part if not part.isdigit() else '{id}'
                for part in path_parts
            )
            fingerprint.append(normalized_path)

    elif exc_type == 'PermissionDenied' or exc_type == 'Http403':
        # Group by endpoint and method
        if 'request' in event:
            fingerprint.append(event['request'].get('method', 'UNKNOWN'))
            if 'url' in event['request']:
                url = event['request']['url']
                path = url.split('?')[0]  # Remove query string
                fingerprint.append(path.split('/')[-1])  # Last path segment

    # Only set custom fingerprint if we have useful grouping info
    if len(fingerprint) > 1:
        event['fingerprint'] = fingerprint
    else:
        # Use default grouping for simple cases
        event['fingerprint'] = ['{{ default }}']


def attach_user_context(user_id, email=None, username=None, role=None, metadata=None):
    """
    Attach user context to Sentry events.

    This helps identify which users are affected by errors and adds context
    for debugging (role, session info, etc.).

    Usage in Django view:
        from core.sentry import attach_user_context

        attach_user_context(
            user_id=request.user.id,
            email=request.user.email,
            username=request.user.username,
            role=request.user.profile.role,
            metadata={'session_id': request.session.session_key}
        )

    Args:
        user_id: User ID (required)
        email: User email address
        username: Username
        role: User role (student, teacher, tutor, admin, parent)
        metadata: Additional user metadata dictionary
    """

    if not user_id:
        return

    context = {
        'id': str(user_id),
    }

    if email:
        context['email'] = email

    if username:
        context['username'] = username

    if role:
        context['role'] = role

    # Add additional metadata
    if metadata:
        if not 'metadata' in context:
            context['other'] = {}
        context['other'].update(metadata)

    sentry_sdk.set_user(context)


def add_breadcrumb(message, category='default', level='info', data=None):
    """
    Add a breadcrumb to track user actions before an error occurs.

    Breadcrumbs appear in error context and help understand what led to the error.

    Usage:
        from core.sentry import add_breadcrumb

        add_breadcrumb('User clicked submit', category='user_action')
        add_breadcrumb('API call started', category='http', data={'url': '/api/data'})

    Args:
        message: Breadcrumb message
        category: Category name (http, user_action, database, etc.)
        level: Log level (debug, info, warning, error, critical)
        data: Additional context data dictionary
    """

    breadcrumb_data = {'message': message}
    if data:
        breadcrumb_data.update(data)

    sentry_sdk.capture_message(
        message=message,
        level=level,
        breadcrumb={
            'message': message,
            'category': category,
            'level': level,
            'data': data or {},
        }
    )


def capture_exception(exception, level='error', user_id=None, extra_data=None):
    """
    Explicitly capture an exception with additional context.

    Useful for catching exceptions that don't automatically trigger Sentry.

    Usage:
        try:
            risky_operation()
        except Exception as e:
            capture_exception(e, user_id=request.user.id, extra_data={'operation': 'payment'})

    Args:
        exception: Exception instance or exception info tuple
        level: Log level (debug, info, warning, error, critical)
        user_id: Associated user ID
        extra_data: Additional context dictionary
    """

    with sentry_sdk.push_scope() as scope:
        if user_id:
            attach_user_context(user_id)

        if extra_data:
            for key, value in extra_data.items():
                scope.set_extra(key, value)

        scope.set_level(level)
        sentry_sdk.capture_exception(exception)


def capture_message(message, level='info', extra_data=None):
    """
    Capture a custom message in Sentry.

    Useful for tracking important application events.

    Usage:
        from core.sentry import capture_message

        if unusual_condition:
            capture_message('Unusual condition detected', level='warning',
                          extra_data={'condition': 'high_error_rate'})

    Args:
        message: Message to send
        level: Log level (debug, info, warning, error, critical)
        extra_data: Additional context dictionary
    """

    with sentry_sdk.push_scope() as scope:
        if extra_data:
            for key, value in extra_data.items():
                scope.set_extra(key, value)

        sentry_sdk.capture_message(message, level=level)


def set_error_tag(key, value):
    """
    Set a tag on the current Sentry scope for categorization.

    Tags help organize and filter errors in the Sentry dashboard.

    Usage:
        from core.sentry import set_error_tag

        set_error_tag('payment_provider', 'yookassa')
        set_error_tag('feature', 'invoicing')

    Args:
        key: Tag key
        value: Tag value (should be string or can be coerced to string)
    """

    sentry_sdk.set_tag(key, str(value))


# Django Middleware for automatic request/response tracking
class SentryMiddleware:
    """
    Django middleware for automatic Sentry integration.

    Attaches request context (user, IP, headers) to errors.
    Add to MIDDLEWARE in settings.py:
        MIDDLEWARE = [
            ...
            'config.sentry.SentryMiddleware',
            ...
        ]
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Attach user context if authenticated
        if request.user and request.user.is_authenticated:
            try:
                role = getattr(request.user.profile, 'role', None) if hasattr(request.user, 'profile') else None

                attach_user_context(
                    user_id=request.user.id,
                    email=request.user.email,
                    username=request.user.username,
                    role=role,
                    metadata={
                        'session_id': request.session.session_key,
                        'ip_address': self.get_client_ip(request),
                    }
                )
            except Exception:
                # Silently ignore errors in middleware
                pass

        response = self.get_response(request)
        return response

    @staticmethod
    def get_client_ip(request):
        """Get client IP from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


__all__ = [
    'init_sentry',
    'attach_user_context',
    'add_breadcrumb',
    'capture_exception',
    'capture_message',
    'set_error_tag',
    'SentryMiddleware',
]
