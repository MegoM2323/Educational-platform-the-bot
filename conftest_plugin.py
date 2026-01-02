"""
pytest plugin to set ENVIRONMENT=test BEFORE Django is loaded
This must be loaded as a plugin before pytest-django
"""
import os
import sys

# Set ENVIRONMENT immediately when this module is imported
os.environ['ENVIRONMENT'] = 'test'

# Clean up production database variables
for var in ['DATABASE_URL', 'DIRECT_URL']:
    if var in os.environ:
        del os.environ[var]


class EnvironmentPlugin:
    """Ensure ENVIRONMENT=test is set during test discovery"""
    pass


# Register the plugin
pytest_plugins = [__name__]
