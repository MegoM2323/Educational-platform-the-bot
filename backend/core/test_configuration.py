"""
Tests for Configuration Management System (T_ADM_005)

Tests:
- ConfigurationService.get() / .set() / .reset()
- Caching with TTL
- Type validation
- Audit logging
- Permissions (admin only)
- Default values
- Configuration groups
"""

import pytest
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Configuration, AuditLog
from .config import ConfigurationService, DEFAULT_CONFIGURATIONS

User = get_user_model()


class ConfigurationServiceTests(TestCase):
    """Test ConfigurationService methods."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()
        Configuration.objects.all().delete()

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_get_default_value(self):
        """Test getting default configuration value."""
        value = ConfigurationService.get('feature_flags.assignments_enabled')
        self.assertEqual(value, True)

    def test_get_custom_value(self):
        """Test getting custom configuration value."""
        Configuration.objects.create(
            key='feature_flags.assignments_enabled',
            value=False,
            value_type='boolean',
            group='feature_flags',
            description='Test'
        )
        value = ConfigurationService.get('feature_flags.assignments_enabled')
        self.assertEqual(value, False)

    def test_get_nonexistent_key_returns_default(self):
        """Test getting non-existent key with default parameter."""
        value = ConfigurationService.get('nonexistent.key', default='default_value')
        self.assertEqual(value, 'default_value')

    def test_set_configuration(self):
        """Test setting configuration value."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        config = ConfigurationService.set(
            'feature_flags.assignments_enabled',
            False,
            user=admin_user
        )

        self.assertEqual(config.value, False)
        self.assertEqual(config.updated_by, admin_user)
        self.assertEqual(config.value_type, 'boolean')

    def test_set_invalid_type_raises_error(self):
        """Test setting invalid type raises ValueError."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        with self.assertRaises(ValueError):
            ConfigurationService.set(
                'feature_flags.assignments_enabled',
                'not_a_boolean',  # Should be boolean
                user=admin_user
            )

    def test_set_unknown_key_raises_error(self):
        """Test setting unknown configuration key raises ValueError."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        with self.assertRaises(ValueError):
            ConfigurationService.set(
                'unknown.configuration.key',
                'value',
                user=admin_user
            )

    def test_caching_get(self):
        """Test that get() uses caching."""
        # First get - should cache the default value
        value1 = ConfigurationService.get('feature_flags.assignments_enabled')

        # Verify it's cached
        cache_key = ConfigurationService._get_cache_key(
            'feature_flags.assignments_enabled'
        )
        cached_value = cache.get(cache_key)
        self.assertEqual(cached_value, value1)

    def test_cache_invalidation_on_set(self):
        """Test that cache is invalidated when setting value."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        # Get default value (caches it)
        value1 = ConfigurationService.get('feature_flags.assignments_enabled')
        self.assertEqual(value1, True)

        # Set new value
        ConfigurationService.set(
            'feature_flags.assignments_enabled',
            False,
            user=admin_user
        )

        # Get value again - should be new value (cache was invalidated)
        value2 = ConfigurationService.get('feature_flags.assignments_enabled')
        self.assertEqual(value2, False)

    def test_get_all_configurations(self):
        """Test getting all configurations."""
        configs = ConfigurationService.get_all()

        # Should include all default configurations
        self.assertGreater(len(configs), 0)
        self.assertIn('feature_flags.assignments_enabled', configs)
        self.assertIn('rate_limit.api_requests_per_minute', configs)

    def test_get_group(self):
        """Test getting configurations by group."""
        configs = ConfigurationService.get_group('feature_flags')

        # Should only include feature flags
        for key in configs:
            self.assertTrue(key.startswith('feature_flags.'))

        self.assertIn('feature_flags.assignments_enabled', configs)
        self.assertIn('feature_flags.payments_enabled', configs)

    def test_set_multiple(self):
        """Test setting multiple configurations at once."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        configs_to_set = {
            'feature_flags.assignments_enabled': False,
            'rate_limit.api_requests_per_minute': 100,
        }

        results = ConfigurationService.set_multiple(configs_to_set, user=admin_user)

        self.assertEqual(len(results), 2)
        self.assertEqual(
            ConfigurationService.get('feature_flags.assignments_enabled'),
            False
        )
        self.assertEqual(
            ConfigurationService.get('rate_limit.api_requests_per_minute'),
            100
        )

    def test_reset_all(self):
        """Test resetting all configurations to defaults."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        # Set some custom values
        ConfigurationService.set(
            'feature_flags.assignments_enabled',
            False,
            user=admin_user
        )
        ConfigurationService.set(
            'rate_limit.api_requests_per_minute',
            100,
            user=admin_user
        )

        # Verify custom values are set
        self.assertEqual(
            ConfigurationService.get('feature_flags.assignments_enabled'),
            False
        )

        # Reset all
        ConfigurationService.reset(user=admin_user)

        # Verify reset to defaults
        self.assertEqual(
            ConfigurationService.get('feature_flags.assignments_enabled'),
            True
        )

    def test_reset_key(self):
        """Test resetting single key to default."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        # Set custom value
        ConfigurationService.set(
            'feature_flags.assignments_enabled',
            False,
            user=admin_user
        )
        self.assertEqual(
            ConfigurationService.get('feature_flags.assignments_enabled'),
            False
        )

        # Reset key
        ConfigurationService.reset_key(
            'feature_flags.assignments_enabled',
            user=admin_user
        )

        # Verify reset to default
        self.assertEqual(
            ConfigurationService.get('feature_flags.assignments_enabled'),
            True
        )

    def test_validate_configuration(self):
        """Test validation without saving."""
        # Valid value
        self.assertTrue(
            ConfigurationService.validate(
                'feature_flags.assignments_enabled',
                True
            )
        )

        # Invalid key
        with self.assertRaises(ValueError):
            ConfigurationService.validate('unknown.key', 'value')

        # Invalid type
        with self.assertRaises(ValueError):
            ConfigurationService.validate(
                'feature_flags.assignments_enabled',
                'not_boolean'
            )

    def test_get_schema(self):
        """Test getting configuration schema."""
        schema = ConfigurationService.get_schema()

        # Should have all default configurations
        self.assertEqual(
            len(schema),
            len(DEFAULT_CONFIGURATIONS)
        )

        # Each schema item should have required fields
        for key, info in schema.items():
            self.assertIn('type', info)
            self.assertIn('description', info)
            self.assertIn('group', info)
            self.assertIn('default', info)
            self.assertIn('current', info)

    def test_audit_log_on_change(self):
        """Test that audit log is created on configuration change."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        # Set configuration
        ConfigurationService.set(
            'feature_flags.assignments_enabled',
            False,
            user=admin_user
        )

        # Check audit log
        audit_logs = AuditLog.objects.filter(
            user=admin_user,
            action=AuditLog.Action.ADMIN_ACTION,
            target_type='configuration'
        )

        self.assertEqual(audit_logs.count(), 1)
        audit_log = audit_logs.first()
        self.assertEqual(
            audit_log.metadata['action'],
            'configuration_update'
        )
        self.assertEqual(
            audit_log.metadata['key'],
            'feature_flags.assignments_enabled'
        )
        self.assertEqual(
            audit_log.metadata['new_value'],
            False
        )


class ConfigurationAPITests(APITestCase):
    """Test Configuration API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        Configuration.objects.all().delete()
        AuditLog.objects.all().delete()

        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_list_configurations_requires_admin(self):
        """Test that list endpoint requires admin permission."""
        # Not authenticated
        response = self.client.get('/api/admin/config/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated as regular user
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/admin/config/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_configurations_as_admin(self):
        """Test listing all configurations as admin."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/config/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertGreater(response.data['count'], 0)

    def test_get_single_configuration(self):
        """Test getting single configuration."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            '/api/admin/config/feature_flags.assignments_enabled/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['key'], 'feature_flags.assignments_enabled')
        self.assertEqual(response.data['value'], True)  # default

    def test_get_nonexistent_configuration(self):
        """Test getting non-existent configuration returns 404."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/config/nonexistent.key/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_configuration(self):
        """Test updating configuration."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(
            '/api/admin/config/feature_flags.assignments_enabled/',
            {'value': False},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['value'], False)

        # Verify change persisted
        self.assertEqual(
            ConfigurationService.get('feature_flags.assignments_enabled'),
            False
        )

    def test_update_with_invalid_type(self):
        """Test updating with invalid type returns 400."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(
            '/api/admin/config/feature_flags.assignments_enabled/',
            {'value': 'not_boolean'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_update_configurations(self):
        """Test bulk updating multiple configurations."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            '/api/admin/config/bulk_update/',
            {
                'configurations': {
                    'feature_flags.assignments_enabled': False,
                    'rate_limit.api_requests_per_minute': 100,
                }
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Verify changes
        self.assertEqual(
            ConfigurationService.get('feature_flags.assignments_enabled'),
            False
        )
        self.assertEqual(
            ConfigurationService.get('rate_limit.api_requests_per_minute'),
            100
        )

    def test_reset_configurations(self):
        """Test resetting all configurations."""
        self.client.force_authenticate(user=self.admin_user)

        # First set custom values
        ConfigurationService.set(
            'feature_flags.assignments_enabled',
            False,
            user=self.admin_user
        )

        # Reset
        response = self.client.post(
            '/api/admin/config/reset/',
            {'reset_type': 'all'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            ConfigurationService.get('feature_flags.assignments_enabled'),
            True
        )

    def test_reset_group(self):
        """Test resetting specific group."""
        self.client.force_authenticate(user=self.admin_user)

        # Set custom values in feature_flags group
        ConfigurationService.set(
            'feature_flags.assignments_enabled',
            False,
            user=self.admin_user
        )

        # Reset group
        response = self.client.post(
            '/api/admin/config/reset/',
            {'reset_type': 'group', 'group': 'feature_flags'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            ConfigurationService.get('feature_flags.assignments_enabled'),
            True
        )

    def test_get_schema(self):
        """Test getting configuration schema."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/config/schema/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('groups', response.data)
        self.assertIn('schema', response.data)

    def test_get_group(self):
        """Test getting configurations by group."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            '/api/admin/config/group/?group=feature_flags'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['group'], 'feature_flags')
        self.assertGreater(response.data['count'], 0)

        # Verify all items are from feature_flags group
        for item in response.data['results']:
            self.assertTrue(item['key'].startswith('feature_flags.'))


class ConfigurationModelTests(TestCase):
    """Test Configuration model."""

    def test_configuration_creation(self):
        """Test creating configuration."""
        config = Configuration.objects.create(
            key='test.config',
            value='test_value',
            value_type='string',
            description='Test configuration',
            group='test'
        )

        self.assertEqual(config.key, 'test.config')
        self.assertEqual(config.value, 'test_value')
        self.assertEqual(config.value_type, 'string')

    def test_configuration_unique_key(self):
        """Test that configuration keys are unique."""
        Configuration.objects.create(
            key='test.config',
            value='value1',
            value_type='string'
        )

        with self.assertRaises(Exception):  # IntegrityError
            Configuration.objects.create(
                key='test.config',
                value='value2',
                value_type='string'
            )

    def test_configuration_type_validation(self):
        """Test type validation on save."""
        config = Configuration(
            key='test.bool',
            value='not_a_boolean',
            value_type='boolean'
        )

        with self.assertRaises(ValueError):
            config.save()

    def test_configuration_ordering(self):
        """Test default ordering is by group and key."""
        Configuration.objects.create(
            key='z.config',
            value='z',
            value_type='string',
            group='z'
        )
        Configuration.objects.create(
            key='a.config',
            value='a',
            value_type='string',
            group='a'
        )

        configs = Configuration.objects.all()
        self.assertEqual(configs[0].key, 'a.config')
        self.assertEqual(configs[1].key, 'z.config')
