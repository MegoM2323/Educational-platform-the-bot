#!/usr/bin/env python3
"""
QA Test: Parent Chat API Testing
Tests chat functionality for PARENT user via API (no browser)

Test Scenarios:
1. Login as parent
2. Get access token
3. List chat rooms
4. Initiate chat
5. Send message
6. Receive messages
"""

import http.client
import json
from datetime import datetime

# Configuration
HOST = "127.0.0.1"
PORT = 8000
PARENT_EMAIL = "parent@test.com"
PARENT_PASSWORD = "TestPass123!"

class ChatAPITester:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.token = None
        self.user_id = None
        self.results = []

    def make_request(self, method, path, payload=None, headers=None, timeout=30):
        """Make HTTP request and return status, headers, and body"""
        if headers is None:
            headers = {}

        if payload:
            body = json.dumps(payload)
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(body))
        else:
            body = None

        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        try:
            conn.request(method, path, body, headers)
            response = conn.getresponse()
            data = response.read().decode('utf-8', errors='ignore')

            # Try to parse as JSON
            try:
                json_data = json.loads(data) if data else None
            except:
                json_data = None

            return response.status, dict(response.getheaders()), json_data or data
        finally:
            conn.close()

    def log(self, test_name, status, message, details=None):
        """Log test result"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = {
            "timestamp": timestamp,
            "test": test_name,
            "status": status,
            "message": message,
            "details": details
        }
        self.results.append(result)
        status_symbol = "✓" if status == "PASS" else "✗"
        print(f"[{timestamp}] {status_symbol} {test_name}: {message}")
        if details:
            print(f"    Details: {details}")

    def test_login(self):
        """Test 1: Login and get access token"""
        test_name = "T1: Login as parent"
        try:
            payload = {
                "email": PARENT_EMAIL,
                "password": PARENT_PASSWORD
            }

            status_code, headers, response_data = self.make_request(
                "POST", "/api/auth/login/", payload
            )

            if status_code == 200:
                if isinstance(response_data, dict) and response_data.get('success'):
                    token = response_data.get('data', {}).get('token')
                    user = response_data.get('data', {}).get('user', {})

                    if token and user:
                        self.token = token
                        self.user_id = user.get('id')
                        self.log(test_name, "PASS", "Login successful",
                                 f"Token: {token[:20]}..., User ID: {self.user_id}, "
                                 f"User: {user.get('email')} ({user.get('role')})")
                        return True
                    else:
                        self.log(test_name, "FAIL", "No token/user in response",
                                 json.dumps(response_data, indent=2, ensure_ascii=False)[:200])
                        return False
                else:
                    self.log(test_name, "FAIL", "Response not successful",
                             json.dumps(response_data, indent=2, ensure_ascii=False)[:200])
                    return False
            else:
                self.log(test_name, "FAIL", f"HTTP {status_code}",
                         str(response_data)[:200])
                return False

        except Exception as e:
            self.log(test_name, "FAIL", f"Exception: {str(e)}", None)
            return False

    def test_list_chat_rooms(self):
        """Test 2: List all chat rooms"""
        test_name = "T2: List chat rooms"
        if not self.token:
            self.log(test_name, "SKIP", "No token available", None)
            return False

        try:
            headers = {"Authorization": f"Token {self.token}"}
            status_code, response_headers, response_data = self.make_request(
                "GET", "/api/chat/rooms/", headers=headers
            )

            if status_code == 200:
                if isinstance(response_data, dict):
                    room_count = len(response_data.get("results", []))
                    self.log(test_name, "PASS", f"Got {room_count} rooms",
                             f"Response keys: {list(response_data.keys())}")
                else:
                    self.log(test_name, "PASS", f"Got response",
                             str(response_data)[:200])
                return True
            elif status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", str(response_data)[:200])
                return False
            else:
                self.log(test_name, "FAIL", f"HTTP {status_code}",
                         str(response_data)[:200])
                return False

        except Exception as e:
            self.log(test_name, "FAIL", f"Exception: {str(e)}", None)
            return False

    def test_get_available_contacts(self):
        """Test 3: Get available contacts to chat"""
        test_name = "T3: Get available contacts"
        if not self.token:
            self.log(test_name, "SKIP", "No token available", None)
            return False, []

        try:
            headers = {"Authorization": f"Token {self.token}"}
            status_code, response_headers, response_data = self.make_request(
                "GET", "/api/chat/available-contacts/", headers=headers
            )

            if status_code == 200:
                contacts = response_data.get("results", []) if isinstance(response_data, dict) else response_data
                contact_count = len(contacts) if isinstance(contacts, list) else 0
                self.log(test_name, "PASS", f"Got {contact_count} available contacts",
                         f"Sample: {json.dumps(contacts[:1], ensure_ascii=False)[:200] if contacts else 'Empty'}")
                return True, contacts
            elif status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", str(response_data)[:200])
                return False, []
            else:
                self.log(test_name, "FAIL", f"HTTP {status_code}",
                         str(response_data)[:200])
                return False, []

        except Exception as e:
            self.log(test_name, "FAIL", f"Exception: {str(e)}", None)
            return False, []

    def test_initiate_chat(self, target_user_id=2):
        """Test 4: Initiate chat with another user"""
        test_name = f"T4: Initiate chat with user {target_user_id}"
        if not self.token:
            self.log(test_name, "SKIP", "No token available", None)
            return False, None

        try:
            headers = {"Authorization": f"Token {self.token}"}
            payload = {"contact_user_id": target_user_id}

            status_code, response_headers, response_data = self.make_request(
                "POST", "/api/chat/initiate-chat/", payload, headers
            )

            if status_code in [200, 201]:
                if isinstance(response_data, dict):
                    # Try different ways to find room_id
                    room_id = (response_data.get("id") or
                              response_data.get("room", {}).get("id") or
                              response_data.get("chat", {}).get("id"))
                    self.log(test_name, "PASS", f"Chat initiated",
                             f"Room ID: {room_id}, Data keys: {list(response_data.keys())}")
                    return True, room_id
                else:
                    self.log(test_name, "FAIL", "Non-dict response",
                             str(response_data)[:200])
                    return False, None
            elif status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", str(response_data)[:200])
                return False, None
            elif status_code == 404:
                self.log(test_name, "FAIL", "Target user not found (404)", str(response_data)[:200])
                return False, None
            else:
                self.log(test_name, "FAIL", f"HTTP {status_code}",
                         str(response_data)[:200])
                return False, None

        except Exception as e:
            self.log(test_name, "FAIL", f"Exception: {str(e)}", None)
            return False, None

    def test_send_message(self, room_id):
        """Test 5: Send message to chat room"""
        test_name = f"T5: Send message to room {room_id}"
        if not self.token or not room_id:
            self.log(test_name, "SKIP", "No token or room ID available", None)
            return False

        try:
            headers = {"Authorization": f"Token {self.token}"}
            message_content = "Test message from parent API"
            payload = {"content": message_content, "room": room_id}

            status_code, response_headers, response_data = self.make_request(
                "POST", f"/api/chat/messages/", payload, headers
            )

            if status_code in [200, 201]:
                if isinstance(response_data, dict):
                    message_id = response_data.get("id")
                    self.log(test_name, "PASS", "Message sent successfully",
                             f"Message ID: {message_id}, Content: '{message_content}'")
                else:
                    self.log(test_name, "PASS", "Message sent",
                             str(response_data)[:200])
                return True
            elif status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", str(response_data)[:200])
                return False
            elif status_code == 404:
                self.log(test_name, "FAIL", "Room not found (404)", str(response_data)[:200])
                return False
            else:
                self.log(test_name, "FAIL", f"HTTP {status_code}",
                         str(response_data)[:200])
                return False

        except Exception as e:
            self.log(test_name, "FAIL", f"Exception: {str(e)}", None)
            return False

    def test_list_room_messages(self, room_id):
        """Test 6: List messages in room"""
        test_name = f"T6: List messages in room {room_id}"
        if not self.token or not room_id:
            self.log(test_name, "SKIP", "No token or room ID available", None)
            return False

        try:
            headers = {"Authorization": f"Token {self.token}"}
            # Use query parameter to filter by room
            status_code, response_headers, response_data = self.make_request(
                "GET", f"/api/chat/messages/?room={room_id}", headers=headers
            )

            if status_code == 200:
                if isinstance(response_data, dict):
                    messages = response_data.get("results", [])
                    message_count = len(messages)
                    self.log(test_name, "PASS", f"Got {message_count} messages",
                             f"Latest: {json.dumps(messages[0], ensure_ascii=False)[:100] if messages else 'No messages'}")
                else:
                    self.log(test_name, "PASS", "Got messages",
                             str(response_data)[:200])
                return True
            elif status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", str(response_data)[:200])
                return False
            else:
                self.log(test_name, "FAIL", f"HTTP {status_code}",
                         str(response_data)[:200])
                return False

        except Exception as e:
            self.log(test_name, "FAIL", f"Exception: {str(e)}", None)
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("=" * 80)
        print("PARENT CHAT API TEST SUITE")
        print(f"Backend URL: http://{self.host}:{self.port}")
        print(f"Testing User: {PARENT_EMAIL}")
        print("=" * 80)
        print()

        # Test 1: Login
        if not self.test_login():
            print("\n[ERROR] Login failed, cannot continue tests")
            return False

        # Test 2: List rooms
        self.test_list_chat_rooms()

        # Test 3: Get available contacts
        success, contacts = self.test_get_available_contacts()

        # Test 4: Initiate chat (with teacher)
        success, room_id = self.test_initiate_chat(target_user_id=4)

        # Test 5: Send message (if room created)
        if room_id:
            self.test_send_message(room_id)

            # Test 6: List messages
            self.test_list_room_messages(room_id)

        return True

    def print_summary(self):
        """Print test summary"""
        print()
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "N/A")
        print()

        if failed > 0:
            print("FAILED TESTS:")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['message']}")

        print()
        return passed == total

if __name__ == "__main__":
    import sys
    tester = ChatAPITester()
    tester.run_all_tests()
    success = tester.print_summary()
    sys.exit(0 if success else 1)
