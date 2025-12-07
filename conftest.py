"""
Root-level pytest configuration to set ENVIRONMENT=test BEFORE Django loads
This file is loaded by pytest BEFORE any other conftest.py files
"""
import os
import sys

# MUST set ENVIRONMENT before Django settings are imported
os.environ['ENVIRONMENT'] = 'test'
# Clean up production database settings if they exist
if 'DATABASE_URL' in os.environ:
    del os.environ['DATABASE_URL']
if 'DIRECT_URL' in os.environ:
    del os.environ['DIRECT_URL']
