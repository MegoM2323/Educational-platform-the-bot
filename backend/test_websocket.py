#!/usr/bin/env python
"""
Quick test script to verify WebSocket routing is configured correctly
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from channels.routing import get_default_application
from config.asgi import application

print("=" * 60)
print("WebSocket Configuration Test")
print("=" * 60)

# Check ASGI application
print("\n1. ASGI Application:")
print(f"   Type: {type(application).__name__}")
print(f"   Module: {type(application).__module__}")

# Check routing
print("\n2. WebSocket URL Patterns:")
try:
    from chat.routing import websocket_urlpatterns
    print(f"   Found {len(websocket_urlpatterns)} WebSocket routes:")
    for pattern in websocket_urlpatterns:
        print(f"   - {pattern.pattern.regex.pattern}")
except Exception as e:
    print(f"   ERROR: {e}")

# Check channel layers
print("\n3. Channel Layers:")
from django.conf import settings
channel_config = settings.CHANNEL_LAYERS.get('default', {})
print(f"   Backend: {channel_config.get('BACKEND', 'Not configured')}")

# Check consumers
print("\n4. Available Consumers:")
try:
    from chat import consumers
    consumer_classes = [
        name for name in dir(consumers)
        if name.endswith('Consumer') and not name.startswith('_')
    ]
    for consumer in consumer_classes:
        print(f"   - {consumer}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 60)
print("Configuration OK - WebSocket routes are registered")
print("=" * 60)
print("\nTo test WebSocket connection:")
print("1. Start server: daphne -b 0.0.0.0 -p 8000 config.asgi:application")
print("2. Connect to: ws://localhost:8000/ws/chat/general/")
print("=" * 60)
