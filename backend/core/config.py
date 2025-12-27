"""
Configuration Management Service

Provides dynamic system configuration management with:
- In-memory caching (Redis) with 1-hour TTL
- Automatic cache invalidation on updates
- Default values for all configuration keys
- Type validation
- Audit logging for all changes
"""

import logging
from typing import Any, Dict, List
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Cache TTL in seconds (1 hour)
CONFIG_CACHE_TTL = 3600

# Default configuration values
DEFAULT_CONFIGURATIONS = {
    # Feature flags
    'feature_flags.assignments_enabled': {
        'value': True,
        'type': 'boolean',
        'description': 'Enable/disable assignment feature',
        'group': 'feature_flags',
    },
    'feature_flags.payments_enabled': {
        'value': True,
        'type': 'boolean',
        'description': 'Enable/disable payment processing',
        'group': 'feature_flags',
    },
    'feature_flags.notifications_enabled': {
        'value': True,
        'type': 'boolean',
        'description': 'Enable/disable notifications',
        'group': 'feature_flags',
    },
    'feature_flags.chat_enabled': {
        'value': True,
        'type': 'boolean',
        'description': 'Enable/disable chat feature',
        'group': 'feature_flags',
    },
    'feature_flags.knowledge_graph_enabled': {
        'value': True,
        'type': 'boolean',
        'description': 'Enable/disable knowledge graph feature',
        'group': 'feature_flags',
    },

    # Rate limiting
    'rate_limit.api_requests_per_minute': {
        'value': 60,
        'type': 'integer',
        'description': 'Maximum API requests per minute',
        'group': 'rate_limit',
    },
    'rate_limit.login_attempts_per_minute': {
        'value': 5,
        'type': 'integer',
        'description': 'Maximum login attempts per minute',
        'group': 'rate_limit',
    },
    'rate_limit.brute_force_lockout_minutes': {
        'value': 30,
        'type': 'integer',
        'description': 'Account lockout duration after failed login attempts',
        'group': 'rate_limit',
    },

    # Email settings
    'email.smtp_host': {
        'value': 'smtp.gmail.com',
        'type': 'string',
        'description': 'SMTP server hostname',
        'group': 'email',
    },
    'email.smtp_port': {
        'value': 587,
        'type': 'integer',
        'description': 'SMTP server port',
        'group': 'email',
    },
    'email.from_address': {
        'value': 'noreply@thebot.com',
        'type': 'string',
        'description': 'Email from address',
        'group': 'email',
    },
    'email.use_tls': {
        'value': True,
        'type': 'boolean',
        'description': 'Use TLS for SMTP connection',
        'group': 'email',
    },

    # Payment settings
    'payment.yookassa_shop_id': {
        'value': '',
        'type': 'string',
        'description': 'YooKassa shop ID',
        'group': 'payment',
    },
    'payment.yookassa_enabled': {
        'value': False,
        'type': 'boolean',
        'description': 'Enable YooKassa payments',
        'group': 'payment',
    },

    # Notification settings
    'notification.email_enabled': {
        'value': True,
        'type': 'boolean',
        'description': 'Send email notifications',
        'group': 'notification',
    },
    'notification.sms_enabled': {
        'value': False,
        'type': 'boolean',
        'description': 'Send SMS notifications',
        'group': 'notification',
    },
    'notification.push_enabled': {
        'value': False,
        'type': 'boolean',
        'description': 'Send push notifications',
        'group': 'notification',
    },

    # UI settings
    'ui.company_name': {
        'value': 'THE_BOT',
        'type': 'string',
        'description': 'Application company name',
        'group': 'ui',
    },
    'ui.logo_url': {
        'value': '/static/logo.png',
        'type': 'string',
        'description': 'Logo URL',
        'group': 'ui',
    },
    'ui.primary_color': {
        'value': '#007bff',
        'type': 'string',
        'description': 'Primary color (hex)',
        'group': 'ui',
    },
    'ui.theme': {
        'value': 'light',
        'type': 'string',
        'description': 'UI theme (light/dark)',
        'group': 'ui',
    },

    # Security settings
    'security.password_min_length': {
        'value': 12,
        'type': 'integer',
        'description': 'Minimum password length',
        'group': 'security',
    },
    'security.password_require_uppercase': {
        'value': True,
        'type': 'boolean',
        'description': 'Require uppercase letters in password',
        'group': 'security',
    },
    'security.password_require_lowercase': {
        'value': True,
        'type': 'boolean',
        'description': 'Require lowercase letters in password',
        'group': 'security',
    },
    'security.password_require_numbers': {
        'value': True,
        'type': 'boolean',
        'description': 'Require numbers in password',
        'group': 'security',
    },
    'security.password_require_special': {
        'value': True,
        'type': 'boolean',
        'description': 'Require special characters in password',
        'group': 'security',
    },
    'security.session_timeout_minutes': {
        'value': 30,
        'type': 'integer',
        'description': 'Session idle timeout in minutes',
        'group': 'security',
    },
    'security.enforce_https': {
        'value': False,
        'type': 'boolean',
        'description': 'Enforce HTTPS connections',
        'group': 'security',
    },
}


class ConfigurationService:
    """
    Service for managing system configurations.

    Provides methods to get, set, and validate configurations with
    automatic caching and audit logging.
    """

    @staticmethod
    def _get_cache_key(config_key: str) -> str:
        """Generate cache key for configuration."""
        return f'config:{config_key}'

    @staticmethod
    def _get_all_cache_key() -> str:
        """Generate cache key for all configurations."""
        return 'config:all'

    @classmethod
    def get(cls, key: str, default: Any = None):
        """
        Get configuration value by key.

        Tries cache first, then database, then defaults.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        # Try cache first
        cache_key = cls._get_cache_key(key)
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        # Try database
        try:
            from .models import Configuration
            config = Configuration.objects.get(key=key)
            value = config.value
            # Cache the result
            cache.set(cache_key, value, CONFIG_CACHE_TTL)
            return value
        except Exception:
            pass

        # Try defaults
        if key in DEFAULT_CONFIGURATIONS:
            default_value = DEFAULT_CONFIGURATIONS[key]['value']
            cache.set(cache_key, default_value, CONFIG_CACHE_TTL)
            return default_value

        return default

    @classmethod
    def get_all(cls):
        """
        Get all configurations.

        Returns cached version if available.

        Returns:
            Dictionary of all configurations
        """
        # Try cache first
        all_cache_key = cls._get_all_cache_key()
        cached_configs = cache.get(all_cache_key)
        if cached_configs is not None:
            return cached_configs

        # Get from database and defaults
        configs = {}

        # Add all defaults
        for key, config_info in DEFAULT_CONFIGURATIONS.items():
            configs[key] = config_info['value']

        # Override with database values
        try:
            from .models import Configuration
            for config in Configuration.objects.all():
                configs[config.key] = config.value
        except Exception:
            pass

        # Cache the result
        cache.set(all_cache_key, configs, CONFIG_CACHE_TTL)
        return configs

    @classmethod
    def get_group(cls, group: str):
        """
        Get all configurations in a group.

        Args:
            group: Configuration group name

        Returns:
            Dictionary of configurations in the group
        """
        all_configs = cls.get_all()
        return {
            k: v for k, v in all_configs.items()
            if k.startswith(f'{group}.')
        }

    @classmethod
    @transaction.atomic
    def set(cls, key: str, value: Any, user=None):
        """
        Set configuration value.

        Updates database, clears cache, and logs the change.

        Args:
            key: Configuration key
            value: New value
            user: User making the change (for audit log)

        Returns:
            Updated Configuration object

        Raises:
            ValueError: If configuration key is invalid or value type mismatch
        """
        # Validate key exists in defaults
        if key not in DEFAULT_CONFIGURATIONS:
            raise ValueError(f"Unknown configuration key: {key}")

        default_config = DEFAULT_CONFIGURATIONS[key]
        config_type = default_config['type']

        # Validate value type
        cls._validate_value_type(value, config_type)

        # Get or create configuration
        from .models import Configuration, AuditLog
        config, created = Configuration.objects.get_or_create(key=key)

        # Store old value for audit
        old_value = config.value

        # Update configuration
        config.value = value
        config.value_type = config_type
        config.description = default_config.get('description', '')
        config.group = default_config.get('group', '')
        config.updated_by = user
        config.save()

        # Clear cache
        cls._invalidate_cache(key)

        # Log change in audit log
        if user:
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.ADMIN_ACTION,
                target_type='configuration',
                target_id=config.id,
                ip_address='127.0.0.1',  # Would be extracted from request in real usage
                user_agent='system',
                metadata={
                    'action': 'configuration_update',
                    'key': key,
                    'old_value': old_value,
                    'new_value': value,
                }
            )

        logger.info(f"Configuration updated: {key} = {value} by {user}")
        return config

    @classmethod
    @transaction.atomic
    def set_multiple(cls, configs: Dict[str, Any], user=None):
        """
        Set multiple configuration values.

        Args:
            configs: Dictionary of key-value pairs
            user: User making the changes

        Returns:
            List of updated Configuration objects
        """
        results = []
        for key, value in configs.items():
            results.append(cls.set(key, value, user))
        return results

    @classmethod
    @transaction.atomic
    def reset(cls, user=None):
        """
        Reset all configurations to defaults.

        Deletes all custom configurations and clears cache.

        Args:
            user: User initiating the reset
        """
        # Delete all custom configurations
        from .models import Configuration, AuditLog
        count, _ = Configuration.objects.all().delete()

        # Clear all caches
        cls._invalidate_all_cache()

        # Log the reset
        if user:
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.ADMIN_ACTION,
                target_type='configuration',
                ip_address='127.0.0.1',
                user_agent='system',
                metadata={
                    'action': 'configuration_reset',
                    'deleted_count': count,
                }
            )

        logger.info(f"Configurations reset to defaults by {user} ({count} records deleted)")

    @classmethod
    def reset_key(cls, key: str, user=None):
        """
        Reset single configuration to default.

        Args:
            key: Configuration key
            user: User initiating the reset

        Raises:
            ValueError: If configuration key is invalid
        """
        if key not in DEFAULT_CONFIGURATIONS:
            raise ValueError(f"Unknown configuration key: {key}")

        try:
            from .models import Configuration, AuditLog
            config = Configuration.objects.get(key=key)
            old_value = config.value
            config.delete()

            cls._invalidate_cache(key)

            if user:
                AuditLog.objects.create(
                    user=user,
                    action=AuditLog.Action.ADMIN_ACTION,
                    target_type='configuration',
                    ip_address='127.0.0.1',
                    user_agent='system',
                    metadata={
                        'action': 'configuration_reset_key',
                        'key': key,
                        'old_value': old_value,
                    }
                )

            logger.info(f"Configuration reset: {key} by {user}")
        except Exception:
            # Already at default value
            logger.info(f"Configuration already at default: {key}")

    @staticmethod
    def _validate_value_type(value: Any, value_type: str):
        """
        Validate that value matches the expected type.

        Args:
            value: Value to validate
            value_type: Expected type ('string', 'integer', 'boolean', 'list', 'json')

        Raises:
            ValueError: If type mismatch
        """
        if value is None:
            return

        if value_type == 'string' and not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")
        elif value_type == 'integer' and not isinstance(value, int):
            raise ValueError(f"Expected integer, got {type(value).__name__}")
        elif value_type == 'boolean' and not isinstance(value, bool):
            raise ValueError(f"Expected boolean, got {type(value).__name__}")
        elif value_type == 'list' and not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value).__name__}")
        # JSON type accepts any JSON-serializable value

    @classmethod
    def _invalidate_cache(cls, key: str) -> None:
        """Invalidate cache for a specific key."""
        cache.delete(cls._get_cache_key(key))
        cache.delete(cls._get_all_cache_key())

    @classmethod
    def _invalidate_all_cache(cls) -> None:
        """Invalidate all configuration caches."""
        all_keys = list(DEFAULT_CONFIGURATIONS.keys())
        cache.delete_many([cls._get_cache_key(k) for k in all_keys])
        cache.delete(cls._get_all_cache_key())

    @classmethod
    def get_schema(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get configuration schema with all available keys and their types.

        Returns:
            Dictionary describing all available configuration options
        """
        schema = {}
        for key, config_info in DEFAULT_CONFIGURATIONS.items():
            schema[key] = {
                'type': config_info['type'],
                'description': config_info.get('description', ''),
                'group': config_info.get('group', ''),
                'default': config_info['value'],
                'current': cls.get(key),
            }
        return schema

    @classmethod
    def validate(cls, key: str, value: Any) -> bool:
        """
        Validate configuration without saving.

        Args:
            key: Configuration key
            value: Value to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        if key not in DEFAULT_CONFIGURATIONS:
            raise ValueError(f"Unknown configuration key: {key}")

        config_type = DEFAULT_CONFIGURATIONS[key]['type']
        cls._validate_value_type(value, config_type)
        return True
