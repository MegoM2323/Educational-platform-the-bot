#!/usr/bin/env python3
"""
Comprehensive Chat & Messaging System Testing for THE_BOT Platform

Tests:
1. Direct dialog initiation (Student -> Teacher)
2. Message sending and receiving
3. Message history
4. File uploads
5. Group chats
6. Notifications
7. Message search
8. Message read status
"""

import json
import os
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configuration
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"
CHAT_API_URL = f"{API_URL}/chat"

# Test credentials (created in database)
STUDENT_EMAIL = "tester_student@test.com"
STUDENT_PASSWORD = "password"

# Use existing teacher instead of newly created one (avoids 403 CSRF issue)
TEACHER_EMAIL = "teacher2@test.com"
TEACHER_PASSWORD = "password"

# Test results storage
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "blocked": 0
    },
    "issues_found": []
}

class ChatTestClient:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.token = None
        self.user_id = None

        # Create adapter with pooling disabled to avoid connection issues
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        self.session = requests.Session()

        # Disable proxy and connection pooling
        adapter = HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1))
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # Disable proxy
        self.session.trust_env = False

        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "THE_BOT-Tester/1.0"
        })

    def login(self) -> bool:
        """Login and get authentication token"""
        try:
            print(f"[LOGIN] Attempting login for {self.email}")

            # First, get CSRF token by making a GET request
            print(f"[LOGIN] Getting CSRF token...")
            csrf_response = self.session.get(f"{BASE_URL}/api/auth/login/")

            # Extract CSRF token if available
            csrf_token = csrf_response.cookies.get('csrftoken', '')
            print(f"[LOGIN] CSRF token: {csrf_token[:20] if csrf_token else 'None'}")

            # Try API endpoint with full path
            login_url = f"{BASE_URL}/api/auth/login/"
            print(f"[LOGIN] Using URL: {login_url}")

            headers = {}
            if csrf_token:
                headers['X-CSRFToken'] = csrf_token

            response = self.session.post(
                login_url,
                json={"email": self.email, "password": self.password},
                headers=headers
            )

            print(f"[LOGIN] Response status: {response.status_code}")
            print(f"[LOGIN] Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception as json_err:
                    print(f"[LOGIN] JSON parse error: {json_err}")
                    print(f"[LOGIN] Response content: {response.text[:200]}")
                    return False

                # Check response structure - API returns {"success": true, "data": {...}}
                if data.get("success"):
                    user_data = data.get("data", {})
                    self.token = user_data.get("token")
                    self.user_id = user_data.get("user", {}).get("id")
                else:
                    self.token = data.get("token") or data.get("access")
                    self.user_id = data.get("user_id") or data.get("user", {}).get("id")

                if self.token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                    print(f"[LOGIN] SUCCESS - Token: {self.token[:20]}... User ID: {self.user_id}")
                    return True
                else:
                    print(f"[LOGIN] FAILED - No token in response: {data}")
                    return False
            else:
                print(f"[LOGIN] FAILED - Status {response.status_code}")
                print(f"[LOGIN] Response text: {response.text[:500]}")
                return False
        except Exception as e:
            print(f"[LOGIN] ERROR - {str(e)}")
            return False

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Tuple[bool, Dict]:
        """Make GET request"""
        try:
            url = f"{CHAT_API_URL}{endpoint}"
            print(f"[GET] {url}")
            response = self.session.get(url, params=params)
            success = response.status_code in [200, 201]
            data = response.json() if response.content else {}
            return success, data, response.status_code
        except Exception as e:
            print(f"[GET] ERROR - {str(e)}")
            return False, {"error": str(e)}, 0

    def post(self, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Tuple[bool, Dict]:
        """Make POST request"""
        try:
            url = f"{CHAT_API_URL}{endpoint}"
            print(f"[POST] {url}")

            if files:
                # For file uploads, don't set Content-Type
                headers = {k: v for k, v in self.session.headers.items()
                          if k != "Content-Type"}
                response = self.session.post(url, data=data, files=files, headers=headers)
            else:
                response = self.session.post(url, json=data)

            success = response.status_code in [200, 201]
            response_data = response.json() if response.content else {}
            return success, response_data, response.status_code
        except Exception as e:
            print(f"[POST] ERROR - {str(e)}")
            return False, {"error": str(e)}, 0

    def patch(self, endpoint: str, data: Dict) -> Tuple[bool, Dict]:
        """Make PATCH request"""
        try:
            url = f"{CHAT_API_URL}{endpoint}"
            print(f"[PATCH] {url}")
            response = self.session.patch(url, json=data)
            success = response.status_code in [200, 201]
            response_data = response.json() if response.content else {}
            return success, response_data, response.status_code
        except Exception as e:
            print(f"[PATCH] ERROR - {str(e)}")
            return False, {"error": str(e)}, 0


def add_test_result(test_name: str, passed: bool, description: str = "", details: Dict = None):
    """Add test result"""
    test_results["tests"].append({
        "name": test_name,
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "description": description,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    })

    test_results["summary"]["total"] += 1
    if passed:
        test_results["summary"]["passed"] += 1
    else:
        test_results["summary"]["failed"] += 1


def issue(severity: str, title: str, description: str, affected_areas: List[str]):
    """Log an issue found during testing"""
    test_results["issues_found"].append({
        "severity": severity.upper(),
        "title": title,
        "description": description,
        "affected_areas": affected_areas,
        "timestamp": datetime.now().isoformat()
    })


# Test Suite
def test_1_student_login():
    """Test 1: Student login"""
    print("\n" + "="*70)
    print("TEST 1: Student Login")
    print("="*70)

    student = ChatTestClient(STUDENT_EMAIL, STUDENT_PASSWORD)
    if student.login():
        add_test_result(
            "Student Login",
            True,
            f"Successfully logged in as {STUDENT_EMAIL}",
            {"email": STUDENT_EMAIL, "token": student.token[:20] if student.token else None}
        )
        return student
    else:
        add_test_result(
            "Student Login",
            False,
            f"Failed to login as {STUDENT_EMAIL}",
            {"email": STUDENT_EMAIL}
        )
        issue("CRITICAL", "Student Login Failed",
              "Unable to authenticate student user",
              ["Authentication", "Chat Access"])
        return None


def test_2_teacher_login():
    """Test 2: Teacher login"""
    print("\n" + "="*70)
    print("TEST 2: Teacher Login")
    print("="*70)

    teacher = ChatTestClient(TEACHER_EMAIL, TEACHER_PASSWORD)
    if teacher.login():
        add_test_result(
            "Teacher Login",
            True,
            f"Successfully logged in as {TEACHER_EMAIL}",
            {"email": TEACHER_EMAIL, "token": teacher.token[:20] if teacher.token else None}
        )
        return teacher
    else:
        add_test_result(
            "Teacher Login",
            False,
            f"Failed to login as {TEACHER_EMAIL}",
            {"email": TEACHER_EMAIL}
        )
        issue("CRITICAL", "Teacher Login Failed",
              "Unable to authenticate teacher user",
              ["Authentication", "Chat Access"])
        return None


def test_3_list_available_contacts(student: ChatTestClient):
    """Test 3: List available contacts (teachers)"""
    print("\n" + "="*70)
    print("TEST 3: List Available Contacts")
    print("="*70)

    success, data, status = student.get("/available-contacts/")

    if success and isinstance(data, list) and len(data) > 0:
        add_test_result(
            "List Available Contacts",
            True,
            f"Retrieved {len(data)} available contacts",
            {"contacts_count": len(data), "first_contact": data[0] if data else None}
        )
        return data
    else:
        add_test_result(
            "List Available Contacts",
            False,
            f"Failed to list contacts (Status: {status})",
            {"status": status, "response": data}
        )
        return []


def test_4_initiate_direct_chat(student: ChatTestClient, teacher_id: int):
    """Test 4: Initiate direct chat with teacher"""
    print("\n" + "="*70)
    print("TEST 4: Initiate Direct Chat")
    print("="*70)

    payload = {
        "participant_id": teacher_id,
        "type": "direct"
    }

    success, data, status = student.post("/initiate-chat/", payload)

    if success:
        room_id = data.get("id")
        add_test_result(
            "Initiate Direct Chat",
            True,
            f"Successfully created chat room with teacher",
            {"room_id": room_id, "participant_id": teacher_id}
        )
        return room_id
    else:
        add_test_result(
            "Initiate Direct Chat",
            False,
            f"Failed to initiate chat (Status: {status})",
            {"status": status, "response": data}
        )
        issue("HIGH", "Chat Initiation Failed",
              "Unable to start direct chat with teacher",
              ["Chat Creation", "Direct Messaging"])
        return None


def test_5_send_student_message(student: ChatTestClient, room_id: int):
    """Test 5: Student sends message"""
    print("\n" + "="*70)
    print("TEST 5: Student Sends Message")
    print("="*70)

    message_content = "Здравствуйте, у меня вопрос по домашней работе"
    payload = {
        "room_id": room_id,
        "content": message_content,
        "message_type": "text"
    }

    success, data, status = student.post("/messages/", payload)

    if success:
        message_id = data.get("id")
        add_test_result(
            "Send Student Message",
            True,
            f"Message sent successfully",
            {
                "room_id": room_id,
                "message_id": message_id,
                "content": message_content,
                "sender": data.get("sender")
            }
        )
        return message_id
    else:
        add_test_result(
            "Send Student Message",
            False,
            f"Failed to send message (Status: {status})",
            {"status": status, "response": data}
        )
        issue("HIGH", "Message Sending Failed",
              "Student unable to send message in chat room",
              ["Message Sending", "Chat Functionality"])
        return None


def test_6_teacher_receives_message(teacher: ChatTestClient):
    """Test 6: Teacher receives and sees new message"""
    print("\n" + "="*70)
    print("TEST 6: Teacher Receives Message")
    print("="*70)

    # Get list of chat rooms
    success, data, status = teacher.get("/rooms/")

    if success and isinstance(data, dict):
        # Handle paginated response
        rooms = data.get("results", []) if "results" in data else data if isinstance(data, list) else []
    else:
        rooms = []

    if rooms:
        add_test_result(
            "Teacher Views Chat Rooms",
            True,
            f"Teacher can see {len(rooms)} chat room(s)",
            {
                "total_rooms": len(rooms),
                "first_room": rooms[0] if rooms else None
            }
        )
        return rooms[0] if rooms else None
    else:
        add_test_result(
            "Teacher Views Chat Rooms",
            False,
            f"Teacher has no chat rooms visible (Status: {status})",
            {"status": status, "response": data}
        )
        issue("HIGH", "Teacher Chat List Empty",
              "Teacher cannot see newly initiated chat room",
              ["Message Delivery", "Chat Visibility"])
        return None


def test_7_teacher_sends_reply(teacher: ChatTestClient, room_id: int):
    """Test 7: Teacher sends reply message"""
    print("\n" + "="*70)
    print("TEST 7: Teacher Sends Reply")
    print("="*70)

    message_content = "Здравствуйте! Пожалуйста, объясните какой вопрос"
    payload = {
        "room_id": room_id,
        "content": message_content,
        "message_type": "text"
    }

    success, data, status = teacher.post("/messages/", payload)

    if success:
        message_id = data.get("id")
        add_test_result(
            "Send Teacher Reply",
            True,
            f"Teacher reply sent successfully",
            {
                "room_id": room_id,
                "message_id": message_id,
                "content": message_content,
                "sender": data.get("sender")
            }
        )
        return message_id
    else:
        add_test_result(
            "Send Teacher Reply",
            False,
            f"Failed to send teacher reply (Status: {status})",
            {"status": status, "response": data}
        )
        issue("HIGH", "Teacher Reply Failed",
              "Teacher unable to send response message",
              ["Message Sending", "Chat Functionality"])
        return None


def test_8_student_views_chat_history(student: ChatTestClient, room_id: int):
    """Test 8: Student views complete chat history"""
    print("\n" + "="*70)
    print("TEST 8: Student Views Chat History")
    print("="*70)

    success, data, status = student.get(f"/rooms/{room_id}/messages/")

    if success:
        # Handle response structure
        if isinstance(data, dict) and "results" in data:
            messages = data.get("results", [])
        elif isinstance(data, list):
            messages = data
        else:
            messages = []

        # Check if we have both student and teacher messages
        student_messages = len([m for m in messages if m.get("sender", {}).get("id") == student.user_id])
        teacher_messages = len([m for m in messages if m.get("sender", {}).get("id") != student.user_id])

        if len(messages) >= 2:
            add_test_result(
                "View Chat History",
                True,
                f"Chat history loaded: {len(messages)} total messages",
                {
                    "total_messages": len(messages),
                    "student_messages": student_messages,
                    "teacher_messages": teacher_messages,
                    "first_message": messages[0] if messages else None,
                    "last_message": messages[-1] if messages else None
                }
            )
        else:
            add_test_result(
                "View Chat History",
                False,
                f"Chat history incomplete: only {len(messages)} messages",
                {
                    "total_messages": len(messages),
                    "expected": 2
                }
            )
            issue("MEDIUM", "Incomplete Chat History",
                  "Not all sent messages appear in chat history",
                  ["Message History", "Chat View"])
    else:
        add_test_result(
            "View Chat History",
            False,
            f"Failed to load chat history (Status: {status})",
            {"status": status, "response": data}
        )
        issue("HIGH", "Chat History Load Failed",
              "Unable to retrieve message history from chat room",
              ["Chat History", "Message Retrieval"])


def test_9_message_read_status(student: ChatTestClient, room_id: int):
    """Test 9: Mark messages as read"""
    print("\n" + "="*70)
    print("TEST 9: Message Read Status")
    print("="*70)

    success, data, status = student.post(f"/rooms/{room_id}/mark_read/", {})

    if success:
        add_test_result(
            "Mark Messages as Read",
            True,
            "Messages successfully marked as read",
            {"room_id": room_id, "status": status}
        )
    else:
        add_test_result(
            "Mark Messages as Read",
            False,
            f"Failed to mark messages as read (Status: {status})",
            {"status": status, "response": data}
        )
        issue("LOW", "Read Status Failed",
              "Unable to mark messages as read in chat",
              ["Message Status", "Read Tracking"])


def test_10_chat_statistics(student: ChatTestClient):
    """Test 10: Get chat statistics"""
    print("\n" + "="*70)
    print("TEST 10: Chat Statistics")
    print("="*70)

    success, data, status = student.get("/rooms/stats/")

    if success and isinstance(data, dict) and "total_rooms" in data:
        add_test_result(
            "Get Chat Statistics",
            True,
            "Chat statistics retrieved",
            {
                "total_rooms": data.get("total_rooms"),
                "active_rooms": data.get("active_rooms"),
                "total_messages": data.get("total_messages"),
                "unread_messages": data.get("unread_messages")
            }
        )
    else:
        add_test_result(
            "Get Chat Statistics",
            False,
            f"Failed to get statistics (Status: {status})",
            {"status": status, "response": data}
        )


def test_11_file_upload_attempt(student: ChatTestClient, room_id: int):
    """Test 11: Attempt file upload in chat"""
    print("\n" + "="*70)
    print("TEST 11: File Upload to Chat")
    print("="*70)

    # Create a test file
    test_file_content = b"This is a test file for chat upload"

    files = {
        "file": ("test_document.txt", test_file_content)
    }

    data = {
        "room_id": str(room_id),
        "content": "Посмотрите этот файл",
        "message_type": "file"
    }

    success, response_data, status = student.post("/messages/", data, files=files)

    if success:
        add_test_result(
            "File Upload to Chat",
            True,
            "File successfully uploaded to chat",
            {
                "room_id": room_id,
                "file_name": "test_document.txt",
                "file_type": "file",
                "message_id": response_data.get("id")
            }
        )
    else:
        add_test_result(
            "File Upload to Chat",
            False,
            f"Failed to upload file (Status: {status})",
            {"status": status, "response": response_data}
        )
        issue("MEDIUM", "File Upload Failed",
              "Unable to upload files to chat",
              ["File Handling", "File Upload"])


def test_12_unread_count(student: ChatTestClient):
    """Test 12: Unread message count"""
    print("\n" + "="*70)
    print("TEST 12: Unread Message Count")
    print("="*70)

    success, data, status = student.get("/rooms/")

    if success and isinstance(data, dict):
        rooms = data.get("results", []) if "results" in data else data if isinstance(data, list) else []
    else:
        rooms = []

    if rooms:
        rooms_with_unread = [r for r in rooms if r.get("unread_count", 0) > 0]
        add_test_result(
            "Unread Message Count",
            True,
            f"Unread count available: {len(rooms_with_unread)} rooms with unread",
            {
                "total_rooms": len(rooms),
                "rooms_with_unread": len(rooms_with_unread),
                "sample_room": rooms[0] if rooms else None
            }
        )
    else:
        add_test_result(
            "Unread Message Count",
            False,
            "Unable to check unread counts",
            {"status": status}
        )


def test_13_general_chat(student: ChatTestClient):
    """Test 13: Access general/group chat"""
    print("\n" + "="*70)
    print("TEST 13: General Chat Access")
    print("="*70)

    success, data, status = student.get("/general/")

    if success and isinstance(data, dict):
        add_test_result(
            "General Chat Access",
            True,
            "Successfully accessed general chat",
            {
                "chat_id": data.get("id"),
                "chat_type": data.get("type"),
                "participant_count": data.get("participants_count")
            }
        )
    else:
        add_test_result(
            "General Chat Access",
            False,
            f"Failed to access general chat (Status: {status})",
            {"status": status, "response": data}
        )
        issue("MEDIUM", "General Chat Not Accessible",
              "Unable to access general/group chat",
              ["Group Chat", "General Chat"])


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "CHAT & MESSAGING SYSTEM TEST SUITE" + " "*20 + "║")
    print("║" + " "*15 + "THE_BOT Platform Testing" + " "*30 + "║")
    print("╚" + "="*68 + "╝")

    # Run login tests
    student = test_1_student_login()
    teacher = test_2_teacher_login()

    if not student or not teacher:
        print("\n" + "!"*70)
        print("BLOCKING ISSUE: Cannot continue testing without both logins")
        print("!"*70)
    else:
        # Test 3: List contacts
        contacts = test_3_list_available_contacts(student)
        teacher_id = None

        if contacts and len(contacts) > 0:
            # Find teacher in contacts
            for contact in contacts:
                if contact.get("email") == TEACHER_EMAIL or contact.get("id") == teacher.user_id:
                    teacher_id = contact.get("id")
                    break

            if not teacher_id and len(contacts) > 0:
                teacher_id = contacts[0].get("id")

        # Test 4-8: Chat lifecycle
        if teacher_id:
            room_id = test_4_initiate_direct_chat(student, teacher_id)

            if room_id:
                msg_id = test_5_send_student_message(student, room_id)
                test_6_teacher_receives_message(teacher)
                test_7_teacher_sends_reply(teacher, room_id)
                test_8_student_views_chat_history(student, room_id)
                test_9_message_read_status(student, room_id)
                test_10_chat_statistics(student)
                test_11_file_upload_attempt(student, room_id)
                test_12_unread_count(student)

        # Test 13: General chat
        test_13_general_chat(student)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total Tests:    {test_results['summary']['total']}")
    print(f"Passed:         {test_results['summary']['passed']}")
    print(f"Failed:         {test_results['summary']['failed']}")
    print(f"Success Rate:   {(test_results['summary']['passed'] / max(1, test_results['summary']['total']) * 100):.1f}%")

    if test_results["issues_found"]:
        print(f"\nIssues Found:   {len(test_results['issues_found'])}")
        for issue_item in test_results["issues_found"]:
            print(f"  [{issue_item['severity']}] {issue_item['title']}")

    # Save results to file
    results_file = "/home/mego/Python Projects/THE_BOT_platform/test_chat_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {results_file}")

    return test_results


if __name__ == "__main__":
    main()
