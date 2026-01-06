#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Python 3.13 compatibility patch for collections
import collections
import collections.abc

if not hasattr(collections, "MutableSet"):
    collections.MutableSet = collections.abc.MutableSet
if not hasattr(collections, "Mapping"):
    collections.Mapping = collections.abc.Mapping
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping
if not hasattr(collections, "Iterable"):
    collections.Iterable = collections.abc.Iterable
if not hasattr(collections, "Callable"):
    collections.Callable = collections.abc.Callable


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    try:
        from config.sentry import init_sentry
        from django.conf import settings
        import logging

        logger = logging.getLogger(__name__)
        init_sentry(settings)
        logger.info("[manage.py] Sentry initialized successfully")
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"[manage.py] Sentry initialization failed: {e}", exc_info=True)

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
