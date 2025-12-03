#!/usr/bin/env python
"""
Test script for WebSocket token authentication
Tests the TokenAuthMiddleware implementation
"""

import asyncio
import websockets
import json
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from chat.models import ChatRoom

User = get_user_model()


async def test_websocket_connection(token, room_id):
    """Test WebSocket connection with token authentication"""

    ws_url = f"ws://127.0.0.1:8000/ws/chat/{room_id}/?token={token}"

    print(f"\n{'='*70}")
    print(f"Testing WebSocket Connection")
    print(f"{'='*70}")
    print(f"URL: {ws_url}")
    print(f"Room ID: {room_id}")
    print(f"Token: {token[:20]}...")

    try:
        async with websockets.connect(ws_url) as websocket:
            print(f"\n✅ Connection successful! Status: {websocket.open}")
            print(f"Protocol: {websocket.subprotocol}")

            # Wait for room history
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            print(f"\n📨 Received initial message:")
            print(f"Type: {data.get('type')}")

            if data.get('type') == 'room_history':
                print(f"Message count: {len(data.get('messages', []))}")

            # Send a test message
            test_message = {
                'type': 'chat_message',
                'content': 'Test message from WebSocket auth verification script'
            }

            await websocket.send(json.dumps(test_message))
            print(f"\n📤 Sent test message")

            # Receive echo
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            print(f"\n📨 Received echo:")
            print(f"Type: {data.get('type')}")
            if data.get('type') == 'chat_message':
                msg = data.get('message', {})
                print(f"Sender: {msg.get('sender', {}).get('email')}")
                print(f"Content: {msg.get('content')}")

            print(f"\n✅ WebSocket token authentication working correctly!")
            return True

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n❌ Connection failed with status code: {e.status_code}")
        print(f"Reason: {e}")

        if e.status_code == 403:
            print("\n🔍 Diagnosis: Token authentication failed")
            print("   - Check TokenAuthMiddleware is loaded in ASGI")
            print("   - Verify token is valid in database")
            print("   - Check user has access to this room")

        return False

    except asyncio.TimeoutError:
        print(f"\n⚠️ Timeout waiting for response")
        print("   Connection established but no data received")
        return False

    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}")
        print(f"   {str(e)}")
        return False


def main():
    """Main test function"""

    print("\n" + "="*70)
    print("WebSocket Token Authentication Test")
    print("="*70)

    # Get test user (student)
    try:
        user = User.objects.filter(role='student').first()
        if not user:
            print("\n❌ No student user found in database")
            print("   Create a student user first")
            return

        print(f"\nTest User: {user.email} (role: {user.role})")

        # Get or create token
        token, created = Token.objects.get_or_create(user=user)
        print(f"Token: {'created' if created else 'existing'}")

        # Get test chat room (first room user has access to)
        rooms = ChatRoom.objects.filter(participants=user)

        if not rooms.exists():
            print("\n❌ User has no chat rooms")
            print("   Create a forum chat or subject enrollment first")
            return

        room = rooms.first()
        print(f"Test Room: {room.name} (ID: {room.id}, Type: {room.type})")

        # Run WebSocket test
        result = asyncio.run(test_websocket_connection(token.key, room.id))

        print("\n" + "="*70)
        if result:
            print("✅ TEST PASSED: WebSocket token authentication working")
        else:
            print("❌ TEST FAILED: WebSocket token authentication broken")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Test setup failed: {type(e).__name__}")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
