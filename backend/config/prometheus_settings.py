"""
Prometheus metrics configuration for THE_BOT Platform backend.

This module sets up Django metrics collection including:
- HTTP request metrics (latency, error rates)
- Database query metrics
- Cache performance metrics
- Custom application metrics
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
import time

# Create a Prometheus registry for this application
PROMETHEUS_REGISTRY = CollectorRegistry()

# =============================================================================
# HTTP Request Metrics
# =============================================================================

DJANGO_REQUEST_TOTAL = Counter(
    'django_request_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_REQUEST_LATENCY_SECONDS = Histogram(
    'django_request_latency_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=PROMETHEUS_REGISTRY
)

DJANGO_REQUEST_EXCEPTIONS_TOTAL = Counter(
    'django_request_exceptions_total',
    'Total request exceptions',
    ['exception_type'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_REQUEST_BODY_SIZE_BYTES = Histogram(
    'django_request_body_size_bytes',
    'HTTP request body size in bytes',
    ['method'],
    buckets=(100, 1000, 10000, 100000, 1000000),
    registry=PROMETHEUS_REGISTRY
)

DJANGO_RESPONSE_BODY_SIZE_BYTES = Histogram(
    'django_response_body_size_bytes',
    'HTTP response body size in bytes',
    ['method', 'status'],
    buckets=(100, 1000, 10000, 100000, 1000000),
    registry=PROMETHEUS_REGISTRY
)

# =============================================================================
# Database Metrics
# =============================================================================

DJANGO_DB_EXECUTE_TOTAL = Counter(
    'django_db_execute_total',
    'Total database query executions',
    ['database', 'operation', 'table'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_DB_EXECUTE_TIME_SECONDS = Histogram(
    'django_db_execute_time_seconds',
    'Database query execution time in seconds',
    ['database', 'operation', 'table'],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0),
    registry=PROMETHEUS_REGISTRY
)

DJANGO_DB_CONNECTION_TOTAL = Gauge(
    'django_db_connection_total',
    'Total database connections',
    ['database'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_DB_CONNECTION_AVAILABLE = Gauge(
    'django_db_connection_available',
    'Available database connections',
    ['database'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_DB_SLOW_QUERY_TOTAL = Counter(
    'django_db_slow_query_total',
    'Total slow database queries (>100ms)',
    ['database', 'table'],
    registry=PROMETHEUS_REGISTRY
)

# =============================================================================
# Cache Metrics
# =============================================================================

DJANGO_CACHE_HITS_TOTAL = Counter(
    'django_cache_hits_total',
    'Total cache hits',
    ['cache_name'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_CACHE_MISSES_TOTAL = Counter(
    'django_cache_misses_total',
    'Total cache misses',
    ['cache_name'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_CACHE_OPERATIONS_LATENCY_SECONDS = Histogram(
    'django_cache_operations_latency_seconds',
    'Cache operation latency in seconds',
    ['cache_name', 'operation'],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0),
    registry=PROMETHEUS_REGISTRY
)

DJANGO_CACHE_SIZE_BYTES = Gauge(
    'django_cache_size_bytes',
    'Cache size in bytes',
    ['cache_name'],
    registry=PROMETHEUS_REGISTRY
)

# =============================================================================
# Authentication Metrics
# =============================================================================

DJANGO_AUTH_LOGIN_TOTAL = Counter(
    'django_auth_login_total',
    'Total login attempts',
    ['method', 'status'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_AUTH_LOGOUT_TOTAL = Counter(
    'django_auth_logout_total',
    'Total logout events',
    registry=PROMETHEUS_REGISTRY
)

DJANGO_AUTH_TOKEN_REFRESH_TOTAL = Counter(
    'django_auth_token_refresh_total',
    'Total token refresh attempts',
    ['status'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_AUTH_FAILED_ATTEMPTS = Counter(
    'django_auth_failed_attempts_total',
    'Total failed authentication attempts',
    ['reason'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_ACTIVE_SESSIONS = Gauge(
    'django_active_sessions',
    'Number of active user sessions',
    registry=PROMETHEUS_REGISTRY
)

# =============================================================================
# Custom Application Metrics
# =============================================================================

DJANGO_MESSAGES_SENT_TOTAL = Counter(
    'django_messages_sent_total',
    'Total messages sent (chat)',
    ['chat_type'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_ASSIGNMENTS_SUBMITTED_TOTAL = Counter(
    'django_assignments_submitted_total',
    'Total assignment submissions',
    ['status'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_MATERIALS_ACCESSED_TOTAL = Counter(
    'django_materials_accessed_total',
    'Total material accesses',
    ['material_type', 'user_role'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_PAYMENTS_PROCESSED_TOTAL = Counter(
    'django_payments_processed_total',
    'Total payment transactions',
    ['status', 'method'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_WEBSOCKET_CONNECTIONS = Gauge(
    'django_websocket_connections',
    'Active WebSocket connections',
    ['type'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_CELERY_TASKS_TOTAL = Counter(
    'django_celery_tasks_total',
    'Total Celery task executions',
    ['task_name', 'status'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_CELERY_TASK_DURATION_SECONDS = Histogram(
    'django_celery_task_duration_seconds',
    'Celery task execution duration in seconds',
    ['task_name'],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
    registry=PROMETHEUS_REGISTRY
)

DJANGO_MODEL_OPERATIONS_TOTAL = Counter(
    'django_model_operations_total',
    'Total model CRUD operations',
    ['model', 'operation'],
    registry=PROMETHEUS_REGISTRY
)

DJANGO_NOTIFICATIONS_SENT_TOTAL = Counter(
    'django_notifications_sent_total',
    'Total notifications sent',
    ['channel', 'status'],
    registry=PROMETHEUS_REGISTRY
)

# =============================================================================
# Performance Metrics
# =============================================================================

DJANGO_ORM_QUERY_COUNT_TOTAL = Gauge(
    'django_orm_query_count_total',
    'Total ORM queries executed in current request',
    registry=PROMETHEUS_REGISTRY
)

DJANGO_TEMPLATE_RENDER_SECONDS = Histogram(
    'django_template_render_seconds',
    'Template rendering time in seconds',
    ['template_name'],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5),
    registry=PROMETHEUS_REGISTRY
)

# =============================================================================
# System Metrics
# =============================================================================

DJANGO_STARTUP_TIME_SECONDS = Gauge(
    'django_startup_time_seconds',
    'Django application startup time in seconds',
    registry=PROMETHEUS_REGISTRY
)

DJANGO_MIGRATIONS_COMPLETED_TOTAL = Counter(
    'django_migrations_completed_total',
    'Total migrations completed',
    ['app', 'migration'],
    registry=PROMETHEUS_REGISTRY
)

# =============================================================================
# Middleware Context for Metrics Collection
# =============================================================================

class MetricsContext:
    """Context object for storing metrics data during request processing."""

    def __init__(self):
        self.start_time = None
        self.endpoint = None
        self.method = None
        self.db_queries_count = 0
        self.db_time = 0
        self.cache_hits = 0
        self.cache_misses = 0

    def start(self):
        """Mark the start of request processing."""
        self.start_time = time.time()

    def get_elapsed(self):
        """Get elapsed time since request start."""
        if self.start_time:
            return time.time() - self.start_time
        return 0

    def record_db_query(self, duration):
        """Record a database query."""
        self.db_queries_count += 1
        self.db_time += duration

    def record_cache_hit(self):
        """Record a cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self):
        """Record a cache miss."""
        self.cache_misses += 1


# =============================================================================
# Prometheus Exporter Configuration
# =============================================================================

PROMETHEUS_EXPORTER_PORT = 8001
PROMETHEUS_METRICS_PATH = '/api/system/metrics/prometheus/'

# Retention settings
PROMETHEUS_RETENTION_DAYS = 15
PROMETHEUS_RETENTION_SIZE = '50GB'  # Max storage size

# Scrape configuration
PROMETHEUS_SCRAPE_INTERVAL = 15  # seconds
PROMETHEUS_EVALUATION_INTERVAL = 15  # seconds

# Alert configuration
PROMETHEUS_ALERT_ENABLED = True
PROMETHEUS_ALERT_RULES_PATH = '/etc/prometheus/alert_rules.yml'
PROMETHEUS_RECORDING_RULES_PATH = '/etc/prometheus/recording_rules.yml'
