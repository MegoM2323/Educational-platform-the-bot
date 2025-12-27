"""
Logging configuration for THE_BOT platform
Integrates with ELK Stack (Elasticsearch, Logstash, Kibana)

Usage in Django settings.py:
    import sys
    import os
    from pathlib import Path

    # Import the logging config
    from logging_config import LOGGING

    LOGGING = LOGGING  # Use in Django settings
"""

import json
import logging
import logging.config
import logging.handlers
from datetime import datetime
from pythonjsonlogger import jsonlogger
import os

# Get environment variables
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_PATH = os.getenv('LOG_PATH', '/var/log/thebot')
LOGSTASH_HOST = os.getenv('LOGSTASH_HOST', 'localhost')
LOGSTASH_PORT = int(os.getenv('LOGSTASH_PORT', 5000))
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Create log directory if it doesn't exist
os.makedirs(LOG_PATH, exist_ok=True)


class RequestIdFilter(logging.Filter):
    """Add request ID to log records for tracing"""

    def filter(self, record):
        from django.http import HttpRequest
        from django.core.context_processors import request as request_processor

        # Try to get request ID from thread-local storage or request
        request_id = getattr(record, 'request_id', None)
        if not request_id:
            # Try to get from Django request context
            try:
                from django.contrib.auth.models import AnonymousUser
                # This would need to be set in middleware
                request_id = getattr(logging.currentFrame(), 'request_id', None)
            except:
                request_id = None

        record.request_id = request_id or 'unknown'
        return True


class UserIdFilter(logging.Filter):
    """Add user ID to log records"""

    def filter(self, record):
        # This should be set by middleware in thread-local storage
        user_id = getattr(record, 'user_id', None)
        record.user_id = user_id or 'anonymous'
        return True


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['level_number'] = record.levelno

        # Add exception info if present
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)

        # Add custom fields
        log_record['environment'] = ENVIRONMENT
        log_record['platform'] = 'thebot'
        log_record['version'] = '1.0.0'

        # Add request and user info if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = record.duration_ms

        return log_record


# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] [{levelname}] {name} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {name} - {message}',
            'style': '{',
        },
        'json': {
            '()': JSONFormatter,
            'format': '%(timestamp)s %(level)s %(name)s %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': logging.filters.CallbackFilter,
            'callback': lambda record: not os.getenv('DEBUG', 'False') == 'True',
        },
        'require_debug_true': {
            '()': logging.filters.CallbackFilter,
            'callback': lambda record: os.getenv('DEBUG', 'False') == 'True',
        },
        'request_id': {
            '()': RequestIdFilter,
        },
        'user_id': {
            '()': UserIdFilter,
        },
    },
    'handlers': {
        # Console handler - all levels
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['request_id', 'user_id'],
        },

        # File handler - all logs
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'{LOG_PATH}/django.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
            'filters': ['request_id', 'user_id'],
        },

        # JSON file handler - for ELK ingestion
        'json_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'{LOG_PATH}/django-json.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
            'filters': ['request_id', 'user_id'],
        },

        # Logstash handler - TCP connection
        'logstash': {
            'level': 'INFO',
            'class': 'pythonjsonlogger.handlers.TCPHandler',
            'host': LOGSTASH_HOST,
            'port': LOGSTASH_PORT,
            'formatter': 'json',
            'filters': ['request_id', 'user_id'],
        },

        # Error file - errors and critical
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'{LOG_PATH}/errors.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
            'filters': ['request_id', 'user_id'],
        },

        # Admin actions
        'admin_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'{LOG_PATH}/admin.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
            'filters': ['request_id', 'user_id'],
        },

        # Celery tasks
        'celery_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'{LOG_PATH}/celery.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
            'filters': ['request_id', 'user_id'],
        },

        # HTTP requests
        'http_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'{LOG_PATH}/http.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
            'filters': ['request_id', 'user_id'],
        },

        # Audit log
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'{LOG_PATH}/audit.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
            'filters': ['request_id', 'user_id'],
        },

        # Null handler - to suppress third-party logs if needed
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        # Django core
        'django': {
            'handlers': ['console', 'file', 'json_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },

        # Django requests
        'django.request': {
            'handlers': ['console', 'error_file', 'http_file', 'logstash'],
            'level': 'DEBUG',
            'propagate': False,
        },

        # Django database
        'django.db.backends': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if os.getenv('DEBUG') == 'True' else 'INFO',
            'propagate': False,
        },

        # Django security
        'django.security': {
            'handlers': ['console', 'error_file', 'audit_file', 'logstash'],
            'level': 'DEBUG',
            'propagate': False,
        },

        # Django admin
        'django.contrib.admin': {
            'handlers': ['console', 'admin_file'],
            'level': 'INFO',
            'propagate': False,
        },

        # Celery
        'celery': {
            'handlers': ['console', 'celery_file'],
            'level': 'INFO',
            'propagate': False,
        },

        # Application loggers
        'accounts': {
            'handlers': ['console', 'file', 'json_file', 'logstash'],
            'level': LOG_LEVEL,
            'propagate': False,
        },

        'chat': {
            'handlers': ['console', 'file', 'json_file', 'logstash'],
            'level': LOG_LEVEL,
            'propagate': False,
        },

        'knowledge_graph': {
            'handlers': ['console', 'file', 'json_file', 'logstash'],
            'level': LOG_LEVEL,
            'propagate': False,
        },

        'assignments': {
            'handlers': ['console', 'file', 'json_file', 'logstash'],
            'level': LOG_LEVEL,
            'propagate': False,
        },

        'reports': {
            'handlers': ['console', 'file', 'json_file', 'logstash'],
            'level': LOG_LEVEL,
            'propagate': False,
        },

        'payments': {
            'handlers': ['console', 'file', 'json_file', 'logstash'],
            'level': LOG_LEVEL,
            'propagate': False,
        },

        'notifications': {
            'handlers': ['console', 'file', 'json_file', 'logstash'],
            'level': LOG_LEVEL,
            'propagate': False,
        },

        'materials': {
            'handlers': ['console', 'file', 'json_file', 'logstash'],
            'level': LOG_LEVEL,
            'propagate': False,
        },

        # Suppress verbose third-party loggers
        'urllib3': {
            'handlers': ['null'],
            'level': 'WARNING',
            'propagate': False,
        },

        'requests': {
            'handlers': ['null'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': LOG_LEVEL,
    },
}


# Add Logstash handler only if available and environment is set
try:
    from pythonjsonlogger.handlers import TCPHandler
    if LOGSTASH_HOST and LOGSTASH_PORT:
        LOGGING['handlers']['logstash'] = {
            'level': 'INFO',
            'class': 'pythonjsonlogger.handlers.TCPHandler',
            'host': LOGSTASH_HOST,
            'port': LOGSTASH_PORT,
            'formatter': 'json',
            'filters': ['request_id', 'user_id'],
        }
except ImportError:
    pass


if __name__ == '__main__':
    # Test the logging configuration
    logging.config.dictConfig(LOGGING)

    logger = logging.getLogger('django')
    logger.info('ELK Stack logging configuration loaded successfully')
    logger.debug('This is a debug message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')
