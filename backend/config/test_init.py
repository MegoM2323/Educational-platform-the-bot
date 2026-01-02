"""
Initialization for test environment
This module MUST be imported before Django settings are loaded
"""
import os
import sys

def init_test_environment():
    """Set up test environment variables BEFORE Django loads settings"""
    # Check if we're running tests
    is_testing = (
        "pytest" in sys.modules
        or "pytest" in sys.argv[0] if sys.argv else False
        or any("pytest" in str(arg) for arg in sys.argv)
    )

    if is_testing:
        os.environ['ENVIRONMENT'] = 'test'

        # Remove production DB variables
        for var in ['DATABASE_URL', 'DIRECT_URL']:
            if var in os.environ:
                del os.environ[var]


# Auto-initialize when imported
init_test_environment()
