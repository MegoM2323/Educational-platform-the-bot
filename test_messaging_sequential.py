#!/usr/bin/env python3
"""
Sequential messaging integration test for THE_BOT platform.
Runs tests one at a time to avoid SQLite database locks.
"""

import json
import time
import requests
import os
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# Disable proxy for localhost
os.environ['no_proxy'] = '127.0.0.1,localhost'
os.environ['NO_PROXY'] = '127.0.0.1,localhost'

BASE_URL = "http://127.0.0.1:9000"
API_HEADERS = {"Content-Type": "application/json"}
RATE_LIMIT_DELAY = 2  # Reduced from 5 for sequential execution
REQUEST_TIMEOUT = 30  # seconds


@dataclass
class TestResult:
    test_name: str
    status: str  # "PASS", "FAIL", "ERROR"
    message: str
    response_code: Optional[int] = None
    details: Dict = None


class SequentialMessagingTest:
    def __init__(self):
        self.results = []
        self.tokens = {}
        self.chats = {}

    def log(self, msg: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {msg}")

    def delay(self, reason: str = "rate limiting"):
        """Apply delay"""
        time.sleep(RATE_LIMIT_DELAY)

    def add_result(self, result: TestResult):
        """Track test result"""
        self.results.append(result)
        status_marker = "✓" if result.status == "PASS" else "✗"
        print(f"{status_marker} {result.test_name}: {result.message}")

    def login(self, user_email: str, password: str, user_role: str) -> bool:
        """Authenticate and store token"""
        url = f"{BASE_URL}/api/auth/login/"

        self.log(f"Logging in {user_role}: {user_email}", "AUTH")

        try:
            response = requests.post(
                url,
                json={"email": user_email, "password": password},
                headers=API_HEADERS,
                timeout=REQUEST_TIMEOUT,
                verify=False,
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "token" in data["data"]:
                    token = data["data"]["token"]
                    self.tokens[user_role] = token
                    self.add_result(
                        TestResult(
                            f"Auth {user_role}",
                            "PASS",
                            f"Token acquired for {user_email}",
                            response.status_code,
                        )
                    )
                    self.delay()
                    return True
                else:
                    self.add_result(
                        TestResult(
                            f"Auth {user_role}",
                            "FAIL",
                            f"No token in response",
                            response.status_code,
                        )
                    )
                    return False
            else:
                error_msg = response.json() if response.text else "Unknown error"
                self.add_result(
                    TestResult(
                        f"Auth {user_role}",
                        "FAIL",
                        f"HTTP {response.status_code}: {str(error_msg)[:100]}",
                        response.status_code,
                    )
                )
                return False

        except Exception as e:
            self.add_result(
                TestResult(
                    f"Auth {user_role}",
                    "ERROR",
                    f"Exception: {str(e)[:100]}",
                    None,
                )
            )
            return False

    def get_chats(self, user_role: str) -> bool:
        """Get forum chats for user"""
        if user_role not in self.tokens:
            self.add_result(
                TestResult(
                    f"Get chats {user_role}",
                    "ERROR",
                    "No token available",
                    None,
                )
            )
            return False

        url = f"{BASE_URL}/api/chat/forum/"
        token = self.tokens[user_role]
        headers = {**API_HEADERS, "Authorization": f"Token {token}"}

        self.log(f"Fetching chats for {user_role}", "REQUEST")

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=False,
            )

            if response.status_code == 200:
                data = response.json()
                chats = data if isinstance(data, list) else data.get("results", [])

                self.chats[user_role] = chats
                self.add_result(
                    TestResult(
                        f"Get chats {user_role}",
                        "PASS",
                        f"Found {len(chats)} chats",
                        response.status_code,
                    )
                )

                if chats:
                    for i, chat in enumerate(chats[:2]):
                        self.log(
                            f"  Chat {i+1}: {chat.get('name')} (ID: {chat.get('id')}, Type: {chat.get('type')})",
                            "INFO",
                        )

                self.delay()
                return True
            else:
                self.add_result(
                    TestResult(
                        f"Get chats {user_role}",
                        "FAIL",
                        f"HTTP {response.status_code}",
                        response.status_code,
                    )
                )
                return False

        except Exception as e:
            self.add_result(
                TestResult(
                    f"Get chats {user_role}",
                    "ERROR",
                    f"Exception: {str(e)[:100]}",
                    None,
                )
            )
            return False

    def find_chat_by_type(self, user_role: str, chat_type: str) -> Optional[int]:
        """Find first chat of given type"""
        chats = self.chats.get(user_role, [])
        for chat in chats:
            if chat.get("type") == chat_type:
                return chat.get("id")
        return None

    def send_message(self, user_role: str, chat_id: int, content: str) -> bool:
        """Send message to chat"""
        if user_role not in self.tokens:
            self.add_result(
                TestResult(
                    f"Send message {user_role}",
                    "ERROR",
                    "No token available",
                    None,
                )
            )
            return False

        url = f"{BASE_URL}/api/chat/forum/{chat_id}/send_message/"
        token = self.tokens[user_role]
        headers = {**API_HEADERS, "Authorization": f"Token {token}"}
        payload = {"content": content}

        self.log(f"Sending message from {user_role}: {content[:50]}...", "REQUEST")

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=False,
            )

            if response.status_code in [200, 201]:
                self.add_result(
                    TestResult(
                        f"Send message {user_role} to chat {chat_id}",
                        "PASS",
                        "Message sent successfully",
                        response.status_code,
                    )
                )
                self.delay()
                return True
            else:
                error = response.json() if response.text else "Unknown error"
                self.add_result(
                    TestResult(
                        f"Send message {user_role} to chat {chat_id}",
                        "FAIL",
                        f"HTTP {response.status_code}: {str(error)[:100]}",
                        response.status_code,
                    )
                )
                return False

        except Exception as e:
            self.add_result(
                TestResult(
                    f"Send message {user_role} to chat {chat_id}",
                    "ERROR",
                    f"Exception: {str(e)[:100]}",
                    None,
                )
            )
            return False

    def run_tests(self):
        """Run all sequential tests"""
        self.log("=" * 70, "SECTION")
        self.log("THE_BOT Platform - Sequential Messaging Integration Tests", "SECTION")
        self.log("=" * 70, "SECTION")
        print()

        print("TEST 1: Student & Teacher Login")
        print("-" * 70)
        self.login("test_student@example.com", "test123", "student")
        self.login("test_teacher@example.com", "test123", "teacher")

        print("\nTEST 2: Get Forum Chats")
        print("-" * 70)
        self.get_chats("student")
        self.get_chats("teacher")

        print("\nTEST 3: Student → Teacher Message")
        print("-" * 70)
        chat_id = self.find_chat_by_type("student", "forum_subject")
        if chat_id:
            self.log(f"Found forum_subject chat ID {chat_id}", "INFO")
            self.send_message(
                "student", chat_id, "Привет учитель, это сообщение от студента"
            )
        else:
            self.log("No forum_subject chat found for student", "ERROR")

        print("\nTEST 4: Tutor Login & Chat")
        print("-" * 70)
        self.login("test_tutor@example.com", "test123", "tutor")
        self.get_chats("tutor")

        print("\nTEST 5: Student → Tutor Message")
        print("-" * 70)
        chat_id = self.find_chat_by_type("student", "forum_tutor")
        if chat_id:
            self.log(f"Found forum_tutor chat ID {chat_id}", "INFO")
            self.send_message("student", chat_id, "Привет тьютор, это сообщение от студента")
        else:
            self.log("No forum_tutor chat found for student", "ERROR")

        print("\nTEST 6: Parent Login & Access")
        print("-" * 70)
        self.login("test_parent@example.com", "test123", "parent")
        self.get_chats("parent")

        print("\nTEST 7: Admin Login & Access")
        print("-" * 70)
        self.login("admin@example.com", "admin12345", "admin")
        self.get_chats("admin")

        self.print_summary()

    def print_summary(self):
        """Print final summary"""
        print()
        print("=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)

        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        errors = sum(1 for r in self.results if r.status == "ERROR")
        total = len(self.results)

        print()
        print("| Result | Test Name | Message |")
        print("|--------|-----------|---------|")

        for result in self.results:
            status_icon = "✓" if result.status == "PASS" else "✗"
            test_name = result.test_name[:30]
            message = result.message[:40]
            print(f"| {status_icon} {result.status:5} | {test_name:30} | {message:40} |")

        print()
        print(f"Total: {total} | PASSED: {passed} | FAILED: {failed} | ERRORS: {errors}")
        if total > 0:
            success_rate = (passed / total) * 100
            print(f"Success Rate: {success_rate:.1f}%")

        print("=" * 70)

        return passed, failed, errors, total


def main():
    """Main entry point"""
    test = SequentialMessagingTest()
    test.run_tests()


if __name__ == "__main__":
    main()
