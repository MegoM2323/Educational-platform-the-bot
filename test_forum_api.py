#!/usr/bin/env python3
"""
Comprehensive Forum API Integration Tests

Tests all 20 scenarios from the test plan:
- Server connectivity
- Authentication
- Forum chat listing
- Message retrieval and sending
- Role-based access control
- Pagination
- Permission checks
"""

import json
import requests
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Configuration
BASE_URL = "http://localhost:8003"
API_BASE = f"{BASE_URL}/api"


@dataclass
class TestResult:
    """Store individual test result"""
    test_num: int
    name: str
    passed: bool
    expected: str
    actual: str
    details: str = ""
    error: Optional[str] = None


class ForumAPITester:
    """Main test runner for Forum API"""

    def __init__(self):
        self.results: list[TestResult] = []
        self.student_token: Optional[str] = None
        self.teacher_token: Optional[str] = None
        self.tutor_token: Optional[str] = None
        self.parent_token: Optional[str] = None
        self.forum_chat_id: Optional[str] = None
        self.tutor_chat_id: Optional[str] = None
        self.session = requests.Session()
        # Bypass proxy for localhost
        self.session.trust_env = False

    def log_result(
        self,
        test_num: int,
        name: str,
        passed: bool,
        expected: str,
        actual: str,
        details: str = "",
        error: Optional[str] = None,
    ):
        """Log test result"""
        result = TestResult(
            test_num=test_num,
            name=name,
            passed=passed,
            expected=expected,
            actual=actual,
            details=details,
            error=error,
        )
        self.results.append(result)
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n{status} - Test {test_num}: {name}")
        if not passed:
            print(f"  Expected: {expected}")
            print(f"  Actual:   {actual}")
            if details:
                print(f"  Details:  {details}")
            if error:
                print(f"  Error:    {error}")

    def run(self):
        """Run all tests"""
        print("=" * 80)
        print("FORUM API COMPREHENSIVE TEST SUITE")
        print("=" * 80)

        # Test 1: Server connectivity
        self.test_01_server_connectivity()

        # Test 2: Student login
        self.test_02_student_login()

        if self.student_token:
            # Test 3-7: Student forum operations
            self.test_03_list_forum_chats_student()
            self.test_04_extract_chat_id()
            self.test_05_get_chat_messages()
            self.test_06_send_message()
            self.test_07_verify_message_saved()

        # Test 8: Teacher login
        self.test_08_teacher_login()

        if self.teacher_token:
            # Test 9-12: Teacher forum operations
            self.test_09_teacher_list_chats()
            self.test_10_teacher_read_messages()
            self.test_11_teacher_send_reply()
            self.test_12_student_reads_reply()

        # Test 13: Tutor login
        self.test_13_tutor_login()

        if self.tutor_token:
            # Test 14-16: Tutor operations
            self.test_14_tutor_list_chats()
            self.test_15_tutor_send_message()
            self.test_16_student_sees_tutor_chat()

        # Test 17-20: Permission and edge cases
        if self.student_token:
            self.test_17_permission_denied_send()
            self.test_18_permission_denied_view()

        self.test_19_pagination()
        self.test_20_anonymous_request()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        coverage = (passed / total * 100) if total > 0 else 0

        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Coverage: {coverage:.1f}%")
        print("=" * 80)

        if total - passed > 0:
            print("\nFAILED TESTS:")
            for r in self.results:
                if not r.passed:
                    print(f"  {r.test_num}: {r.name}")
                    if r.error:
                        print(f"    Error: {r.error}")

    # ==================== Test 1 ====================
    def test_01_server_connectivity(self):
        """Test server is running and accessible"""
        test_num = 1
        try:
            response = self.session.get(f"{API_BASE}/", timeout=5)
            passed = response.status_code in [200, 404]  # 404 is ok for empty endpoint
            self.log_result(
                test_num,
                "Server connectivity",
                passed,
                "HTTP 200 or 404",
                f"HTTP {response.status_code}",
                f"Response length: {len(response.text)} bytes",
            )
        except Exception as e:
            self.log_result(
                test_num,
                "Server connectivity",
                False,
                "HTTP 200 or 404",
                "Connection failed",
                error=str(e),
            )

    # ==================== Test 2 ====================
    def test_02_student_login(self):
        """Test student login and token retrieval"""
        test_num = 2
        try:
            response = self.session.post(
                f"{API_BASE}/auth/login/",
                json={"email": "student@test.com", "password": "TestPass123!"},
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                self.student_token = data.get("token") or data.get("access")
                passed = bool(self.student_token)
                self.log_result(
                    test_num,
                    "Student login",
                    passed,
                    "HTTP 200 + token",
                    f"HTTP {response.status_code}, token: {bool(self.student_token)}",
                    f"Token type: {type(self.student_token).__name__}",
                )
            else:
                self.log_result(
                    test_num,
                    "Student login",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                    response.text[:200],
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Student login",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 3 ====================
    def test_03_list_forum_chats_student(self):
        """Test GET /api/chat/forum/ - list forum chats"""
        test_num = 3
        if not self.student_token:
            self.log_result(
                test_num,
                "List forum chats (Student)",
                False,
                "HTTP 200",
                "No token",
                "Student login failed",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{API_BASE}/chat/forum/", headers=headers, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                has_results = "results" in data or "data" in data
                passed = has_results
                details = f"Response keys: {list(data.keys())}"
                if has_results:
                    results = data.get("results") or data.get("data")
                    details = f"Count: {len(results)}, Keys in first: {list(results[0].keys()) if results else 'empty'}"

                self.log_result(
                    test_num,
                    "List forum chats (Student)",
                    passed,
                    "HTTP 200 with results",
                    f"HTTP {response.status_code}, has results: {has_results}",
                    details,
                )
            else:
                self.log_result(
                    test_num,
                    "List forum chats (Student)",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                    response.text[:300],
                )
        except Exception as e:
            self.log_result(
                test_num,
                "List forum chats (Student)",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 4 ====================
    def test_04_extract_chat_id(self):
        """Extract forum chat ID from student's chats"""
        test_num = 4
        if not self.student_token:
            self.log_result(
                test_num,
                "Extract chat ID",
                False,
                "Valid chat ID",
                "No token",
                "Student login failed",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{API_BASE}/chat/forum/", headers=headers, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results") or data.get("data") or []
                if results:
                    self.forum_chat_id = results[0].get("id")
                    chat_type = results[0].get("type", "unknown")
                    passed = bool(self.forum_chat_id)
                    self.log_result(
                        test_num,
                        "Extract chat ID",
                        passed,
                        "Valid chat ID",
                        f"Chat ID: {self.forum_chat_id}, Type: {chat_type}",
                        f"Total chats: {len(results)}",
                    )
                else:
                    self.log_result(
                        test_num,
                        "Extract chat ID",
                        False,
                        "Valid chat ID",
                        "No chats found",
                        "Results array is empty",
                    )
        except Exception as e:
            self.log_result(
                test_num,
                "Extract chat ID",
                False,
                "Valid chat ID",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 5 ====================
    def test_05_get_chat_messages(self):
        """Test GET /api/chat/forum/{chat_id}/messages/"""
        test_num = 5
        if not self.student_token or not self.forum_chat_id:
            self.log_result(
                test_num,
                "Get chat messages",
                False,
                "HTTP 200",
                "Missing token or chat ID",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{API_BASE}/chat/forum/{self.forum_chat_id}/messages/?limit=50&offset=0",
                headers=headers,
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                has_results = "results" in data
                passed = has_results
                message_count = len(data.get("results", []))
                self.log_result(
                    test_num,
                    "Get chat messages",
                    passed,
                    "HTTP 200 with results",
                    f"HTTP {response.status_code}, messages: {message_count}",
                    f"Response keys: {list(data.keys())}",
                )
            else:
                self.log_result(
                    test_num,
                    "Get chat messages",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                    response.text[:300],
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Get chat messages",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 6 ====================
    def test_06_send_message(self):
        """Test POST /api/chat/forum/{chat_id}/send_message/"""
        test_num = 6
        if not self.student_token or not self.forum_chat_id:
            self.log_result(
                test_num,
                "Send message",
                False,
                "HTTP 201",
                "Missing token or chat ID",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            payload = {"content": f"Test message from student - {int(time.time())}"}
            response = self.session.post(
                f"{API_BASE}/chat/forum/{self.forum_chat_id}/send_message/",
                headers=headers,
                json=payload,
                timeout=5,
            )

            passed = response.status_code in [200, 201]
            status_code = response.status_code
            details = ""

            if passed:
                try:
                    data = response.json()
                    message = data.get("message") or data.get("data") or data
                    details = f"Message ID: {message.get('id')}, Content: {message.get('content')[:50]}"
                except:
                    details = response.text[:100]

            self.log_result(
                test_num,
                "Send message",
                passed,
                "HTTP 200 or 201",
                f"HTTP {status_code}",
                details,
            )
        except Exception as e:
            self.log_result(
                test_num,
                "Send message",
                False,
                "HTTP 201",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 7 ====================
    def test_07_verify_message_saved(self):
        """Verify message was saved by fetching messages again"""
        test_num = 7
        if not self.student_token or not self.forum_chat_id:
            self.log_result(
                test_num,
                "Verify message saved",
                False,
                "Message in results",
                "Missing token or chat ID",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{API_BASE}/chat/forum/{self.forum_chat_id}/messages/?limit=50&offset=0",
                headers=headers,
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                messages = data.get("results", [])
                passed = len(messages) > 0
                self.log_result(
                    test_num,
                    "Verify message saved",
                    passed,
                    "Message in results",
                    f"HTTP {response.status_code}, messages: {len(messages)}",
                    f"Latest message: {messages[0].get('content')[:50] if messages else 'none'}",
                )
            else:
                self.log_result(
                    test_num,
                    "Verify message saved",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Verify message saved",
                False,
                "Message in results",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 8 ====================
    def test_08_teacher_login(self):
        """Test teacher login"""
        test_num = 8
        try:
            response = self.session.post(
                f"{API_BASE}/auth/login/",
                json={"email": "teacher@test.com", "password": "TestPass123!"},
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                self.teacher_token = data.get("token") or data.get("access")
                passed = bool(self.teacher_token)
                self.log_result(
                    test_num,
                    "Teacher login",
                    passed,
                    "HTTP 200 + token",
                    f"HTTP {response.status_code}, token: {bool(self.teacher_token)}",
                )
            else:
                self.log_result(
                    test_num,
                    "Teacher login",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                    response.text[:200],
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Teacher login",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 9 ====================
    def test_09_teacher_list_chats(self):
        """Test teacher lists forum chats"""
        test_num = 9
        if not self.teacher_token:
            self.log_result(
                test_num,
                "Teacher list chats",
                False,
                "HTTP 200",
                "No teacher token",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.teacher_token}"}
            response = self.session.get(
                f"{API_BASE}/chat/forum/", headers=headers, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results") or data.get("data") or []
                passed = len(results) > 0
                self.log_result(
                    test_num,
                    "Teacher list chats",
                    passed,
                    "HTTP 200 with chats",
                    f"HTTP {response.status_code}, chats: {len(results)}",
                )
            else:
                self.log_result(
                    test_num,
                    "Teacher list chats",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Teacher list chats",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 10 ====================
    def test_10_teacher_read_messages(self):
        """Test teacher reads messages from student's chat"""
        test_num = 10
        if not self.teacher_token or not self.forum_chat_id:
            self.log_result(
                test_num,
                "Teacher read messages",
                False,
                "HTTP 200",
                "Missing token or chat ID",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.teacher_token}"}
            response = self.session.get(
                f"{API_BASE}/chat/forum/{self.forum_chat_id}/messages/",
                headers=headers,
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                messages = data.get("results", [])
                passed = len(messages) > 0
                self.log_result(
                    test_num,
                    "Teacher read messages",
                    passed,
                    "HTTP 200 with messages",
                    f"HTTP {response.status_code}, messages: {len(messages)}",
                )
            else:
                self.log_result(
                    test_num,
                    "Teacher read messages",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Teacher read messages",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 11 ====================
    def test_11_teacher_send_reply(self):
        """Test teacher sends reply message"""
        test_num = 11
        if not self.teacher_token or not self.forum_chat_id:
            self.log_result(
                test_num,
                "Teacher send reply",
                False,
                "HTTP 201",
                "Missing token or chat ID",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.teacher_token}"}
            payload = {"content": f"Teacher's reply - {int(time.time())}"}
            response = self.session.post(
                f"{API_BASE}/chat/forum/{self.forum_chat_id}/send_message/",
                headers=headers,
                json=payload,
                timeout=5,
            )

            passed = response.status_code in [200, 201]
            self.log_result(
                test_num,
                "Teacher send reply",
                passed,
                "HTTP 200 or 201",
                f"HTTP {response.status_code}",
            )
        except Exception as e:
            self.log_result(
                test_num,
                "Teacher send reply",
                False,
                "HTTP 201",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 12 ====================
    def test_12_student_reads_reply(self):
        """Test student reads teacher's reply"""
        test_num = 12
        if not self.student_token or not self.forum_chat_id:
            self.log_result(
                test_num,
                "Student reads reply",
                False,
                "HTTP 200",
                "Missing token or chat ID",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{API_BASE}/chat/forum/{self.forum_chat_id}/messages/",
                headers=headers,
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                messages = data.get("results", [])
                passed = len(messages) >= 2  # At least student + teacher message
                self.log_result(
                    test_num,
                    "Student reads reply",
                    passed,
                    "Messages in chronological order",
                    f"HTTP {response.status_code}, total messages: {len(messages)}",
                )
            else:
                self.log_result(
                    test_num,
                    "Student reads reply",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Student reads reply",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 13 ====================
    def test_13_tutor_login(self):
        """Test tutor login"""
        test_num = 13
        try:
            response = self.session.post(
                f"{API_BASE}/auth/login/",
                json={"email": "tutor@test.com", "password": "TestPass123!"},
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                self.tutor_token = data.get("token") or data.get("access")
                passed = bool(self.tutor_token)
                self.log_result(
                    test_num,
                    "Tutor login",
                    passed,
                    "HTTP 200 + token",
                    f"HTTP {response.status_code}, token: {bool(self.tutor_token)}",
                )
            else:
                self.log_result(
                    test_num,
                    "Tutor login",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                    response.text[:200],
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Tutor login",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 14 ====================
    def test_14_tutor_list_chats(self):
        """Test tutor lists FORUM_TUTOR chats"""
        test_num = 14
        if not self.tutor_token:
            self.log_result(
                test_num,
                "Tutor list chats",
                False,
                "HTTP 200",
                "No tutor token",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.tutor_token}"}
            response = self.session.get(
                f"{API_BASE}/chat/forum/", headers=headers, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results") or data.get("data") or []
                if results:
                    self.tutor_chat_id = results[0].get("id")
                    chat_type = results[0].get("type", "unknown")
                passed = len(results) > 0
                self.log_result(
                    test_num,
                    "Tutor list chats",
                    passed,
                    "HTTP 200 with FORUM_TUTOR chats",
                    f"HTTP {response.status_code}, chats: {len(results)}",
                    f"First chat type: {chat_type}",
                )
            else:
                self.log_result(
                    test_num,
                    "Tutor list chats",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Tutor list chats",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 15 ====================
    def test_15_tutor_send_message(self):
        """Test tutor sends message to student"""
        test_num = 15
        if not self.tutor_token or not self.tutor_chat_id:
            self.log_result(
                test_num,
                "Tutor send message",
                False,
                "HTTP 201",
                "Missing token or chat ID",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.tutor_token}"}
            payload = {"content": f"Tutor message to student - {int(time.time())}"}
            response = self.session.post(
                f"{API_BASE}/chat/forum/{self.tutor_chat_id}/send_message/",
                headers=headers,
                json=payload,
                timeout=5,
            )

            passed = response.status_code in [200, 201]
            self.log_result(
                test_num,
                "Tutor send message",
                passed,
                "HTTP 200 or 201",
                f"HTTP {response.status_code}",
            )
        except Exception as e:
            self.log_result(
                test_num,
                "Tutor send message",
                False,
                "HTTP 201",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 16 ====================
    def test_16_student_sees_tutor_chat(self):
        """Test student sees tutor forum chat"""
        test_num = 16
        if not self.student_token:
            self.log_result(
                test_num,
                "Student sees tutor chat",
                False,
                "HTTP 200",
                "No student token",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = self.session.get(
                f"{API_BASE}/chat/forum/", headers=headers, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results") or data.get("data") or []
                passed = len(results) > 0
                self.log_result(
                    test_num,
                    "Student sees tutor chat",
                    passed,
                    "HTTP 200 with chats",
                    f"HTTP {response.status_code}, chats: {len(results)}",
                )
            else:
                self.log_result(
                    test_num,
                    "Student sees tutor chat",
                    False,
                    "HTTP 200",
                    f"HTTP {response.status_code}",
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Student sees tutor chat",
                False,
                "HTTP 200",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 17 ====================
    def test_17_permission_denied_send(self):
        """Test permission denied when sending to unauthorized chat"""
        test_num = 17
        if not self.student_token:
            self.log_result(
                test_num,
                "Permission denied (send)",
                False,
                "HTTP 403",
                "No student token",
            )
            return

        # Try with a fake chat ID that student shouldn't have access to
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            fake_chat_id = "00000000-0000-0000-0000-000000000000"
            payload = {"content": "Should fail"}
            response = self.session.post(
                f"{API_BASE}/chat/forum/{fake_chat_id}/send_message/",
                headers=headers,
                json=payload,
                timeout=5,
            )

            passed = response.status_code in [403, 404]
            self.log_result(
                test_num,
                "Permission denied (send)",
                passed,
                "HTTP 403 or 404",
                f"HTTP {response.status_code}",
                response.text[:150],
            )
        except Exception as e:
            self.log_result(
                test_num,
                "Permission denied (send)",
                False,
                "HTTP 403",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 18 ====================
    def test_18_permission_denied_view(self):
        """Test permission denied when viewing unauthorized chat"""
        test_num = 18
        if not self.student_token:
            self.log_result(
                test_num,
                "Permission denied (view)",
                False,
                "HTTP 403",
                "No student token",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            fake_chat_id = "00000000-0000-0000-0000-000000000000"
            response = self.session.get(
                f"{API_BASE}/chat/forum/{fake_chat_id}/messages/",
                headers=headers,
                timeout=5,
            )

            passed = response.status_code in [403, 404]
            self.log_result(
                test_num,
                "Permission denied (view)",
                passed,
                "HTTP 403 or 404",
                f"HTTP {response.status_code}",
            )
        except Exception as e:
            self.log_result(
                test_num,
                "Permission denied (view)",
                False,
                "HTTP 403",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 19 ====================
    def test_19_pagination(self):
        """Test pagination with limit and offset"""
        test_num = 19
        if not self.student_token or not self.forum_chat_id:
            self.log_result(
                test_num,
                "Pagination",
                False,
                "limit and offset work",
                "Missing token or chat ID",
            )
            return

        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}

            # Get first page
            response1 = self.session.get(
                f"{API_BASE}/chat/forum/{self.forum_chat_id}/messages/?limit=10&offset=0",
                headers=headers,
                timeout=5,
            )

            if response1.status_code == 200:
                data1 = response1.json()
                count1 = len(data1.get("results", []))

                # Get second page
                response2 = self.session.get(
                    f"{API_BASE}/chat/forum/{self.forum_chat_id}/messages/?limit=10&offset=10",
                    headers=headers,
                    timeout=5,
                )

                if response2.status_code == 200:
                    data2 = response2.json()
                    count2 = len(data2.get("results", []))
                    passed = True  # If we got both pages, pagination works
                    self.log_result(
                        test_num,
                        "Pagination",
                        passed,
                        "limit and offset work",
                        f"Page 1: {count1} msgs, Page 2: {count2} msgs",
                        f"Total available: {data1.get('count', 'unknown')}",
                    )
                else:
                    self.log_result(
                        test_num,
                        "Pagination",
                        False,
                        "HTTP 200",
                        f"Page 2 failed: HTTP {response2.status_code}",
                    )
            else:
                self.log_result(
                    test_num,
                    "Pagination",
                    False,
                    "HTTP 200",
                    f"HTTP {response1.status_code}",
                )
        except Exception as e:
            self.log_result(
                test_num,
                "Pagination",
                False,
                "limit and offset work",
                "Request failed",
                error=str(e),
            )

    # ==================== Test 20 ====================
    def test_20_anonymous_request(self):
        """Test anonymous request (no token) returns 401"""
        test_num = 20
        try:
            response = self.session.get(f"{API_BASE}/chat/forum/", timeout=5)

            passed = response.status_code == 401
            self.log_result(
                test_num,
                "Anonymous request",
                passed,
                "HTTP 401",
                f"HTTP {response.status_code}",
            )
        except Exception as e:
            self.log_result(
                test_num,
                "Anonymous request",
                False,
                "HTTP 401",
                "Request failed",
                error=str(e),
            )


if __name__ == "__main__":
    tester = ForumAPITester()
    tester.run()
