#!/usr/bin/env python3
"""
Comprehensive messaging integration test for THE_BOT platform.
Tests communication between all user roles:
- Student <-> Teacher
- Student <-> Tutor
- Parent (read-only access)
- Admin (view access)
"""

import json
import time
import requests
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

# Disable proxy for localhost
os.environ['no_proxy'] = '127.0.0.1,localhost'
os.environ['NO_PROXY'] = '127.0.0.1,localhost'


BASE_URL = "http://127.0.0.1:9000"
API_HEADERS = {"Content-Type": "application/json"}
RATE_LIMIT_DELAY = 5  # seconds between requests


@dataclass
class User:
    email: str
    password: str
    role: str
    token: Optional[str] = None


@dataclass
class TestResult:
    test_name: str
    status: str  # "PASS", "FAIL", "ERROR"
    message: str
    response_code: Optional[int] = None
    details: Dict = None


class MessagingTestSuite:
    def __init__(self):
        self.results: List[TestResult] = []
        self.users = {
            "student": User("test_student@example.com", "test123", "student"),
            "teacher": User("test_teacher@example.com", "test123", "teacher"),
            "tutor": User("test_tutor@example.com", "test123", "tutor"),
            "parent": User("test_parent@example.com", "test123", "parent"),
            "admin": User("admin@example.com", "admin12345", "admin"),
        }
        self.chat_rooms = {}

    def log(self, msg: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {msg}")

    def delay(self, reason: str = "rate limiting"):
        """Apply rate limiting delay"""
        self.log(f"Waiting {RATE_LIMIT_DELAY}s ({reason})", "WAIT")
        time.sleep(RATE_LIMIT_DELAY)

    def add_result(self, result: TestResult):
        """Track test result"""
        self.results.append(result)
        status_marker = "✓" if result.status == "PASS" else "✗"
        self.log(
            f"{status_marker} {result.test_name}: {result.message} (HTTP {result.response_code})",
            result.status,
        )

    def authenticate(self, user_key: str) -> bool:
        """Authenticate user and get JWT token"""
        user = self.users[user_key]
        url = f"{BASE_URL}/api/auth/login/"

        self.log(f"Authenticating {user_key} ({user.email})", "AUTH")

        try:
            self.log(f"POST {url}", "DEBUG")
            self.log(f"Payload: email={user.email}, password={'*'*len(user.password)}", "DEBUG")
            response = requests.post(
                url,
                json={"email": user.email, "password": user.password},
                headers=API_HEADERS,
                timeout=30,  # Increased timeout
                verify=False,  # Disable SSL verification if any
            )

            self.log(f"Response status: {response.status_code}", "DEBUG")
            self.log(f"Response headers: {dict(response.headers)}", "DEBUG")
            if response.status_code not in [200, 201]:
                self.log(f"Response body: {response.text[:500]}", "DEBUG")

            if response.status_code in [200, 201]:
                data = response.json()
                # Try different token locations
                if "data" in data and "token" in data["data"]:
                    user.token = data["data"]["token"]
                else:
                    user.token = data.get("access") or data.get("token")

                if user.token:
                    self.add_result(
                        TestResult(
                            f"Auth {user_key}",
                            "PASS",
                            f"Got token for {user.email}",
                            response.status_code,
                            {"token_length": len(user.token)},
                        )
                    )
                    self.delay("after authentication")
                    return True
                else:
                    self.add_result(
                        TestResult(
                            f"Auth {user_key}",
                            "FAIL",
                            f"No token in response",
                            response.status_code,
                            {"response": data},
                        )
                    )
                    return False
            else:
                self.add_result(
                    TestResult(
                        f"Auth {user_key}",
                        "FAIL",
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        response.status_code,
                    )
                )
                return False

        except Exception as e:
            self.add_result(
                TestResult(
                    f"Auth {user_key}",
                    "ERROR",
                    f"Exception: {str(e)}",
                    None,
                    {"exception": str(e)},
                )
            )
            return False

    def get_forum_chats(self, user_key: str) -> bool:
        """Get list of forum chats for user"""
        user = self.users[user_key]
        if not user.token:
            self.add_result(
                TestResult(
                    f"Get forum chats {user_key}",
                    "ERROR",
                    "No token available",
                    None,
                )
            )
            return False

        url = f"{BASE_URL}/api/chat/forum/"
        # Try both token formats
        headers = {**API_HEADERS, "Authorization": f"Token {user.token}"}

        self.log(f"Fetching forum chats for {user_key}", "REQUEST")

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                chats = data if isinstance(data, list) else data.get("results", [])

                self.add_result(
                    TestResult(
                        f"Get forum chats {user_key}",
                        "PASS",
                        f"Found {len(chats)} chats",
                        response.status_code,
                        {"chat_count": len(chats)},
                    )
                )

                if chats:
                    self.chat_rooms[user_key] = chats
                    self.log(f"Forum chats for {user_key}: {len(chats)}", "INFO")
                    for chat in chats[:3]:  # Show first 3
                        self.log(
                            f"  - {chat.get('name', 'Unknown')} "
                            f"(ID: {chat.get('id')}, Type: {chat.get('type')})",
                            "INFO",
                        )

                self.delay("after fetching chats")
                return True
            else:
                self.add_result(
                    TestResult(
                        f"Get forum chats {user_key}",
                        "FAIL",
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        response.status_code,
                    )
                )
                return False

        except Exception as e:
            self.add_result(
                TestResult(
                    f"Get forum chats {user_key}",
                    "ERROR",
                    f"Exception: {str(e)}",
                    None,
                )
            )
            return False

    def find_chat_by_type_and_participants(
        self, user_key: str, chat_type: str, other_user: str = None
    ) -> Optional[Dict]:
        """Find chat by type and optionally check participants"""
        chats = self.chat_rooms.get(user_key, [])

        for chat in chats:
            if chat.get("type") == chat_type:
                if other_user:
                    participants = chat.get("participants", [])
                    other_user_obj = self.users.get(other_user)
                    if other_user_obj:
                        # Check if other user is in participants
                        participant_names = [p.get("full_name", "") for p in participants]
                        if any(other_user_obj.email in str(p) for p in participant_names):
                            return chat

                else:
                    return chat
        return None

    def send_message(self, user_key: str, chat_id: int, content: str) -> bool:
        """Send message to forum chat"""
        user = self.users[user_key]
        if not user.token:
            self.add_result(
                TestResult(
                    f"Send message {user_key}",
                    "ERROR",
                    "No token available",
                    None,
                )
            )
            return False

        url = f"{BASE_URL}/api/chat/forum/{chat_id}/send_message/"
        headers = {**API_HEADERS, "Authorization": f"Token {user.token}"}
        payload = {"content": content}

        self.log(f"Sending message from {user_key} to chat {chat_id}", "REQUEST")
        self.log(f"Message: {content}", "MESSAGE")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code in [200, 201]:
                data = response.json()
                msg_id = data.get("id")

                self.add_result(
                    TestResult(
                        f"Send message {user_key} to chat {chat_id}",
                        "PASS",
                        f"Message sent (ID: {msg_id})",
                        response.status_code,
                        {"message_id": msg_id, "content": content},
                    )
                )

                self.delay("after sending message")
                return True
            else:
                self.add_result(
                    TestResult(
                        f"Send message {user_key} to chat {chat_id}",
                        "FAIL",
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        response.status_code,
                    )
                )
                return False

        except Exception as e:
            self.add_result(
                TestResult(
                    f"Send message {user_key} to chat {chat_id}",
                    "ERROR",
                    f"Exception: {str(e)}",
                    None,
                )
            )
            return False

    def get_chat_messages(self, user_key: str, chat_id: int) -> Optional[List[Dict]]:
        """Get messages from specific chat"""
        user = self.users[user_key]
        if not user.token:
            self.add_result(
                TestResult(
                    f"Get messages {user_key}",
                    "ERROR",
                    "No token available",
                    None,
                )
            )
            return None

        url = f"{BASE_URL}/api/chat/forum/{chat_id}/messages/"
        headers = {**API_HEADERS, "Authorization": f"Token {user.token}"}

        self.log(f"Fetching messages from chat {chat_id} for {user_key}", "REQUEST")

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                messages = data if isinstance(data, list) else data.get("results", [])

                self.add_result(
                    TestResult(
                        f"Get messages {user_key} from chat {chat_id}",
                        "PASS",
                        f"Found {len(messages)} messages",
                        response.status_code,
                        {"message_count": len(messages)},
                    )
                )

                self.delay("after fetching messages")
                return messages
            else:
                self.add_result(
                    TestResult(
                        f"Get messages {user_key} from chat {chat_id}",
                        "FAIL",
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        response.status_code,
                    )
                )
                return None

        except Exception as e:
            self.add_result(
                TestResult(
                    f"Get messages {user_key} from chat {chat_id}",
                    "ERROR",
                    f"Exception: {str(e)}",
                    None,
                )
            )
            return None

    def verify_message_visibility(
        self, chat_id: int, user1: str, user2: str, message_content: str
    ) -> bool:
        """Verify that both users see the message"""
        messages1 = self.get_chat_messages(user1, chat_id)
        messages2 = self.get_chat_messages(user2, chat_id)

        if not messages1 or not messages2:
            self.add_result(
                TestResult(
                    f"Verify message visibility {user1}↔{user2}",
                    "FAIL",
                    "Could not fetch messages from one or both users",
                    None,
                )
            )
            return False

        # Find message in both lists
        found_in_user1 = any(
            message_content in msg.get("content", "") for msg in messages1
        )
        found_in_user2 = any(
            message_content in msg.get("content", "") for msg in messages2
        )

        if found_in_user1 and found_in_user2:
            self.add_result(
                TestResult(
                    f"Verify message visibility {user1}↔{user2}",
                    "PASS",
                    f"Message visible to both users",
                    200,
                )
            )
            return True
        else:
            self.add_result(
                TestResult(
                    f"Verify message visibility {user1}↔{user2}",
                    "FAIL",
                    f"Message not visible: user1={found_in_user1}, user2={found_in_user2}",
                    200,
                )
            )
            return False

    def test_student_teacher_communication(self) -> bool:
        """Test: Student -> Teacher -> Student"""
        self.log("=" * 60, "SECTION")
        self.log("TEST 1: Student ↔ Teacher Communication", "SECTION")
        self.log("=" * 60, "SECTION")

        # Authenticate both users
        if not self.authenticate("student"):
            return False
        if not self.authenticate("teacher"):
            return False

        # Get forum chats
        if not self.get_forum_chats("student"):
            return False
        if not self.get_forum_chats("teacher"):
            return False

        # Find chat with matching participants
        student_chats = self.chat_rooms.get("student", [])
        teacher_chats = self.chat_rooms.get("teacher", [])

        self.log(f"Student has {len(student_chats)} forum chats", "INFO")
        self.log(f"Teacher has {len(teacher_chats)} forum chats", "INFO")

        # Find matching FORUM_SUBJECT chat
        student_forum = self.find_chat_by_type_and_participants(
            "student", "forum_subject"
        )
        if not student_forum:
            self.add_result(
                TestResult(
                    "Find student-teacher chat",
                    "FAIL",
                    "No forum_subject chat found for student",
                    None,
                )
            )
            return False

        chat_id = student_forum["id"]
        self.log(f"Found shared chat: {student_forum['name']} (ID: {chat_id})", "INFO")

        # Student sends message
        self.log("-> Student sends message to Teacher", "ACTION")
        if not self.send_message(
            "student", chat_id, "Привет учитель, это сообщение от студента"
        ):
            return False

        # Teacher responds
        self.log("-> Teacher sends message to Student", "ACTION")
        if not self.send_message(
            "teacher", chat_id, "Привет студент, это ответ от учителя"
        ):
            return False

        # Verify both see each other's messages
        self.log("-> Verifying message visibility", "ACTION")
        if not self.verify_message_visibility(
            chat_id, "student", "teacher", "это сообщение от студента"
        ):
            return False

        if not self.verify_message_visibility(
            chat_id, "teacher", "student", "это ответ от учителя"
        ):
            return False

        return True

    def test_student_tutor_communication(self) -> bool:
        """Test: Student -> Tutor -> Student"""
        self.log("=" * 60, "SECTION")
        self.log("TEST 2: Student ↔ Tutor Communication", "SECTION")
        self.log("=" * 60, "SECTION")

        # Authenticate tutor if not already
        if not self.users["tutor"].token:
            if not self.authenticate("tutor"):
                return False

        # Get tutor's forum chats
        if not self.get_forum_chats("tutor"):
            return False

        # Find FORUM_TUTOR chat
        tutor_chats = self.chat_rooms.get("tutor", [])
        student_chats = self.chat_rooms.get("student", [])

        self.log(f"Tutor has {len(tutor_chats)} forum chats", "INFO")

        # Find matching FORUM_TUTOR chat
        student_tutor_chat = None
        for chat in student_chats:
            if chat.get("type") == "forum_tutor":
                student_tutor_chat = chat
                break

        if not student_tutor_chat:
            self.add_result(
                TestResult(
                    "Find student-tutor chat",
                    "FAIL",
                    "No forum_tutor chat found for student",
                    None,
                )
            )
            return False

        chat_id = student_tutor_chat["id"]
        self.log(f"Found shared chat: {student_tutor_chat['name']} (ID: {chat_id})", "INFO")

        # Student sends message
        self.log("-> Student sends message to Tutor", "ACTION")
        if not self.send_message(
            "student", chat_id, "Привет тьютор, это сообщение от студента"
        ):
            return False

        # Tutor responds
        self.log("-> Tutor sends message to Student", "ACTION")
        if not self.send_message(
            "tutor", chat_id, "Привет студент, это ответ от тьютора"
        ):
            return False

        # Verify visibility
        self.log("-> Verifying message visibility", "ACTION")
        if not self.verify_message_visibility(
            chat_id, "student", "tutor", "это сообщение от студента"
        ):
            return False

        if not self.verify_message_visibility(
            chat_id, "tutor", "student", "это ответ от тьютора"
        ):
            return False

        return True

    def test_parent_access(self) -> bool:
        """Test: Parent can view student's chats (read-only)"""
        self.log("=" * 60, "SECTION")
        self.log("TEST 3: Parent Access (Read-Only)", "SECTION")
        self.log("=" * 60, "SECTION")

        # Authenticate parent
        if not self.authenticate("parent"):
            return False

        # Get parent's forum chats
        if not self.get_forum_chats("parent"):
            return False

        parent_chats = self.chat_rooms.get("parent", [])
        self.log(f"Parent can see {len(parent_chats)} student chats", "INFO")

        if len(parent_chats) > 0:
            self.add_result(
                TestResult(
                    "Parent forum access",
                    "PASS",
                    f"Parent can view {len(parent_chats)} chats",
                    200,
                )
            )

            # Show first chat details
            chat = parent_chats[0]
            self.log(f"Sample chat: {chat.get('name')} (Type: {chat.get('type')})", "INFO")

            # Try to fetch messages (should work - read-only)
            messages = self.get_chat_messages("parent", chat["id"])
            if messages is not None:
                self.log(f"Parent can see {len(messages)} messages in this chat", "INFO")
                return True
            else:
                return False
        else:
            self.add_result(
                TestResult(
                    "Parent forum access",
                    "FAIL",
                    "Parent has no chats to view",
                    200,
                )
            )
            return False

    def test_admin_access(self) -> bool:
        """Test: Admin can view chats"""
        self.log("=" * 60, "SECTION")
        self.log("TEST 4: Admin Access", "SECTION")
        self.log("=" * 60, "SECTION")

        # Authenticate admin
        if not self.authenticate("admin"):
            return False

        # Get admin's forum chats
        if not self.get_forum_chats("admin"):
            return False

        admin_chats = self.chat_rooms.get("admin", [])
        self.log(f"Admin can access {len(admin_chats)} forum chats", "INFO")

        if len(admin_chats) > 0:
            self.add_result(
                TestResult(
                    "Admin forum access",
                    "PASS",
                    f"Admin can view {len(admin_chats)} chats",
                    200,
                )
            )
            return True
        else:
            self.add_result(
                TestResult(
                    "Admin forum access",
                    "FAIL",
                    "Admin has no chats to view",
                    200,
                )
            )
            return False

    def print_summary(self):
        """Print test summary"""
        self.log("=" * 60, "SUMMARY")
        self.log("TEST RESULTS SUMMARY", "SUMMARY")
        self.log("=" * 60, "SUMMARY")

        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        errors = sum(1 for r in self.results if r.status == "ERROR")
        total = len(self.results)

        print("\n")
        print("=" * 80)
        print("| TEST RESULTS |".center(80))
        print("=" * 80)

        for result in self.results:
            status_icon = "✓" if result.status == "PASS" else "✗"
            status_str = f"{status_icon} {result.status}"
            http_code = f"HTTP {result.response_code}" if result.response_code else "N/A"
            print(f"{status_str:20} | {result.test_name:40} | {http_code:12}")
            if result.details:
                for key, value in result.details.items():
                    print(f"  {key}: {value}")

        print("=" * 80)
        print(f"TOTAL: {total} tests | PASSED: {passed} | FAILED: {failed} | ERRORS: {errors}")
        print("=" * 80)
        print()

        # Calculate success rate
        if total > 0:
            success_rate = (passed / total) * 100
            print(f"Success Rate: {success_rate:.1f}%")
            print()

            if failed > 0 or errors > 0:
                print("FAILED/ERROR TESTS:")
                for result in self.results:
                    if result.status != "PASS":
                        print(f"  - {result.test_name}: {result.message}")
                print()

        return passed, failed, errors, total

    def run_all_tests(self):
        """Run complete test suite"""
        self.log("Starting THE_BOT Platform Messaging Integration Tests", "START")
        self.log(f"Base URL: {BASE_URL}", "INFO")
        self.log(f"Rate limit delay: {RATE_LIMIT_DELAY}s", "INFO")

        print("\n")

        try:
            # Run all test suites
            test1_pass = self.test_student_teacher_communication()
            test2_pass = self.test_student_tutor_communication()
            test3_pass = self.test_parent_access()
            test4_pass = self.test_admin_access()

            # Print summary
            passed, failed, errors, total = self.print_summary()

            # Return overall status
            return failed == 0 and errors == 0

        except Exception as e:
            self.log(f"Fatal error during test execution: {str(e)}", "ERROR")
            return False


def main():
    """Main entry point"""
    suite = MessagingTestSuite()
    success = suite.run_all_tests()

    exit(0 if success else 1)


if __name__ == "__main__":
    main()
