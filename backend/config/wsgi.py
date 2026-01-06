"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

try:
    from config.sentry import init_sentry
    import logging

    logger = logging.getLogger(__name__)
    init_sentry(sys.modules["config.settings"])
    logger.info("[WSGI] Sentry initialized successfully")
except Exception as e:
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"[WSGI] Sentry initialization failed: {e}", exc_info=True)
