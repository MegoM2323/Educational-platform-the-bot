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

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"
PARENT_EMAIL = "parent@test.com"
PARENT_PASSWORD = "TestPass123!"

class ChatAPITester:
    def __init__(self, base_url=API_BASE):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.headers = {"Content-Type": "application/json"}
        self.results = []

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
            response = requests.post(
                f"{self.base_url}/auth/login/",
                headers=self.headers,
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                if "access" in data:
                    self.token = data["access"]
                    self.user_id = data.get("user", {}).get("id")
                    self.headers["Authorization"] = f"Bearer {self.token}"
                    self.log(test_name, "PASS", "Login successful",
                             f"Token: {self.token[:20]}..., User ID: {self.user_id}")
                    return True
                else:
                    self.log(test_name, "FAIL", "No access token in response",
                             json.dumps(data, indent=2))
                    return False
            else:
                self.log(test_name, "FAIL", f"HTTP {response.status_code}",
                         response.text[:200])
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
            response = requests.get(
                f"{self.base_url}/chat/rooms/",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                room_count = len(data.get("results", []))
                self.log(test_name, "PASS", f"Got {room_count} rooms",
                         f"Response: {json.dumps(data, indent=2)[:300]}...")
                return True
            elif response.status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", response.text[:200])
                return False
            else:
                self.log(test_name, "FAIL", f"HTTP {response.status_code}",
                         response.text[:200])
                return False

        except Exception as e:
            self.log(test_name, "FAIL", f"Exception: {str(e)}", None)
            return False

    def test_get_available_contacts(self):
        """Test 3: Get available contacts to chat"""
        test_name = "T3: Get available contacts"
        if not self.token:
            self.log(test_name, "SKIP", "No token available", None)
            return False

        try:
            response = requests.get(
                f"{self.base_url}/chat/available-contacts/",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                contacts = data.get("results", []) if isinstance(data, dict) else data
                contact_count = len(contacts) if isinstance(contacts, list) else 0
                self.log(test_name, "PASS", f"Got {contact_count} available contacts",
                         f"Contacts: {json.dumps(contacts[:2], indent=2)[:200]}...")
                return True, contacts
            elif response.status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", response.text[:200])
                return False, []
            else:
                self.log(test_name, "FAIL", f"HTTP {response.status_code}",
                         response.text[:200])
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
            response = requests.post(
                f"{self.base_url}/chat/initiate-chat/",
                headers=self.headers,
                json={"target_user_id": target_user_id}
            )

            if response.status_code in [200, 201]:
                data = response.json()
                room_id = data.get("id") or data.get("room", {}).get("id")
                self.log(test_name, "PASS", f"Chat initiated",
                         f"Room ID: {room_id}, Response: {json.dumps(data, indent=2)[:200]}...")
                return True, room_id
            elif response.status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", response.text[:200])
                return False, None
            elif response.status_code == 404:
                self.log(test_name, "FAIL", "Target user not found (404)", response.text[:200])
                return False, None
            else:
                self.log(test_name, "FAIL", f"HTTP {response.status_code}",
                         response.text[:200])
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
            message_content = "Test message from parent API"
            response = requests.post(
                f"{self.base_url}/chat/rooms/{room_id}/messages/",
                headers=self.headers,
                json={"content": message_content}
            )

            if response.status_code in [200, 201]:
                data = response.json()
                message_id = data.get("id")
                self.log(test_name, "PASS", "Message sent successfully",
                         f"Message ID: {message_id}, Content: '{message_content}'")
                return True
            elif response.status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", response.text[:200])
                return False
            elif response.status_code == 404:
                self.log(test_name, "FAIL", "Room not found (404)", response.text[:200])
                return False
            else:
                self.log(test_name, "FAIL", f"HTTP {response.status_code}",
                         response.text[:200])
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
            response = requests.get(
                f"{self.base_url}/chat/rooms/{room_id}/messages/",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                messages = data.get("results", [])
                message_count = len(messages)
                self.log(test_name, "PASS", f"Got {message_count} messages",
                         f"Latest: {json.dumps(messages[0], indent=2)[:200] if messages else 'No messages'}...")
                return True
            elif response.status_code == 403:
                self.log(test_name, "FAIL", "Forbidden (403)", response.text[:200])
                return False
            else:
                self.log(test_name, "FAIL", f"HTTP {response.status_code}",
                         response.text[:200])
                return False

        except Exception as e:
            self.log(test_name, "FAIL", f"Exception: {str(e)}", None)
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("=" * 80)
        print("PARENT CHAT API TEST SUITE")
        print(f"Backend URL: {self.base_url}")
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

        # Test 4: Initiate chat
        success, room_id = self.test_initiate_chat(target_user_id=2)

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
    tester = ChatAPITester()
    tester.run_all_tests()
    success = tester.print_summary()
    sys.exit(0 if success else 1)
