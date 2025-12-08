#!/usr/bin/env python3
"""Test WebSocket connection with token authentication."""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    token = "3df759d882109a16ee928dc63766a2844f9a3d59"  # Test student token
    room_id = 262  # Forum chat room ID

    # Test connecting to general chat
    print("Testing General Chat connection...")
    general_url = f"ws://localhost:8000/ws/chat/general/?token={token}"
    print(f"URL: {general_url}")

    try:
        async with websockets.connect(general_url) as websocket:
            print("✓ Connected to general chat!")

            # Wait for messages
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            print(f"Received: {message}")

            # Send a test message
            test_message = {
                "type": "chat_message",
                "content": "Test from WebSocket script"
            }
            await websocket.send(json.dumps(test_message))
            print("✓ Sent test message")

            # Wait for echo
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            print(f"Response: {response}")

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"✗ Connection closed: {e}")
    except asyncio.TimeoutError:
        print("✗ Timeout waiting for response")
    except Exception as e:
        print(f"✗ Error: {e}")

    print("\n" + "="*50)

    # Test connecting to specific room
    print(f"Testing Room {room_id} connection...")
    room_url = f"ws://localhost:8000/ws/chat/{room_id}/?token={token}"
    print(f"URL: {room_url}")

    try:
        async with websockets.connect(room_url) as websocket:
            print(f"✓ Connected to room {room_id}!")

            # Wait for messages
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            print(f"Received: {message}")

            # Send a test message
            test_message = {
                "type": "chat_message",
                "content": "Test from WebSocket to forum room"
            }
            await websocket.send(json.dumps(test_message))
            print("✓ Sent test message to room")

            # Wait for echo
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            print(f"Response: {response}")

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"✗ Connection closed: {e}")
    except asyncio.TimeoutError:
        print("✗ Timeout waiting for response")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())