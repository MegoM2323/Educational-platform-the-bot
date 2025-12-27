#!/usr/bin/env python
"""
Simple test to verify middleware is called
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from config.asgi import application
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()


@database_sync_to_async
def get_test_user_and_token():
    """Get test user and token"""
    user = User.objects.filter(role='student').first()
    if not user:
        return None, None
    token = Token.objects.get(user=user)
    return user, token.key


async def test_middleware():
    """Test that TokenAuthMiddleware processes WebSocket connections"""

    # Get test user and token
    user, token_key = await get_test_user_and_token()
    if not user:
        print("❌ No student user found")
        return False

    print(f"\n{'='*70}")
    print(f"Testing TokenAuthMiddleware")
    print(f"{'='*70}")
    print(f"User: {user.email}")
    print(f"Token: {token_key[:20]}...")

    # Create communicator with token in query string
    communicator = WebsocketCommunicator(
        application,
        f"/ws/chat/241/?token={token_key}"
    )

    print(f"\nConnecting to WebSocket...")

    try:
        connected, subprotocol = await communicator.connect()

        if connected:
            print(f"✅ Connected! (subprotocol: {subprotocol})")

            # Try to receive message
            response = await communicator.receive_from(timeout=5)
            print(f"📨 Received: {response[:100] if response else 'None'}...")

            await communicator.disconnect()
            return True
        else:
            print(f"❌ Connection rejected")
            return False

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False


if __name__ == '__main__':
    import asyncio
    result = asyncio.run(test_middleware())
    sys.exit(0 if result else 1)
