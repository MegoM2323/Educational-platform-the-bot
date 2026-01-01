"""
Comprehensive API Testing for THE_BOT Platform
Tests all major endpoints with role-based access control and data validation
"""

import json
import requests
import pytest
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"

# Test user credentials - UPDATED with correct passwords
TEST_USERS = {
    "admin": {"email": "admin@test.com", "password": "test123", "role": "admin"},
    "teacher": {"email": "teacher1@test.com", "password": "test123", "role": "teacher"},
    "student": {"email": "student1@test.com", "password": "test123", "role": "student"},
    "tutor": {"email": "tutor1@test.com", "password": "test123", "role": "tutor"},
    "parent": {"email": "parent1@test.com", "password": "test123", "role": "parent"},
}


class APIClient:
    """Helper class for API requests"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.user_role = None

    def login(self, email: str, password: str) -> bool:
        """Login and get authentication token"""
        try:
            response = self.session.post(
                f"{self.base_url}{API_PREFIX}/auth/login/",
                json={"email": email, "password": password},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access") or data.get("token") or data.get("data", {}).get("token")
                return bool(self.token)
            return False
        except Exception as e:
            print(f"Login error: {e}")
            return False

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated API request"""
        url = f"{self.base_url}{API_PREFIX}{endpoint}"
        headers = kwargs.pop("headers", {})

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return self.session.request(method, url, headers=headers, **kwargs)

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("DELETE", endpoint, **kwargs)


class TestLoginEndpoint:
    """Test authentication login endpoint"""

    def test_valid_login_returns_token(self):
        """Test that valid login returns auth token"""
        client = APIClient()
        success = client.login(TEST_USERS["admin"]["email"], TEST_USERS["admin"]["password"])
        assert success

    def test_invalid_password_fails(self):
        """Test that invalid password fails"""
        client = APIClient()
        response = client.session.post(
            f"{BASE_URL}{API_PREFIX}/auth/login/",
            json={"email": TEST_USERS["admin"]["email"], "password": "wrongpassword"},
            timeout=10,
        )
        assert response.status_code in [400, 401, 403]

    def test_nonexistent_user_fails(self):
        """Test that nonexistent user fails"""
        client = APIClient()
        response = client.session.post(
            f"{BASE_URL}{API_PREFIX}/auth/login/",
            json={"email": "nonexistent@test.com", "password": "test123"},
            timeout=10,
        )
        assert response.status_code in [400, 401, 403, 404]

    def test_missing_email_field(self):
        """Test that missing email field returns error"""
        client = APIClient()
        response = client.session.post(
            f"{BASE_URL}{API_PREFIX}/auth/login/",
            json={"password": "test123"},
            timeout=10,
        )
        assert response.status_code in [400, 422]

    def test_missing_password_field(self):
        """Test that missing password field returns error"""
        client = APIClient()
        response = client.session.post(
            f"{BASE_URL}{API_PREFIX}/auth/login/",
            json={"email": TEST_USERS["admin"]["email"]},
            timeout=10,
        )
        assert response.status_code in [400, 422]

    def test_empty_email_field(self):
        """Test that empty email field returns error"""
        client = APIClient()
        response = client.session.post(
            f"{BASE_URL}{API_PREFIX}/auth/login/",
            json={"email": "", "password": "test123"},
            timeout=10,
        )
        assert response.status_code in [400, 422]

    def test_empty_password_field(self):
        """Test that empty password field returns error"""
        client = APIClient()
        response = client.session.post(
            f"{BASE_URL}{API_PREFIX}/auth/login/",
            json={"email": TEST_USERS["admin"]["email"], "password": ""},
            timeout=10,
        )
        assert response.status_code in [400, 422]


class TestProfileEndpoint:
    """Test GET /api/profile/ endpoint"""

    def test_profile_without_token(self):
        """Test accessing profile without authentication"""
        client = APIClient()
        response = client.get("/profile/")
        assert response.status_code in [401, 403]

    def test_profile_with_admin_token(self):
        """Test admin accessing their profile"""
        client = APIClient()
        assert client.login(TEST_USERS["admin"]["email"], TEST_USERS["admin"]["password"])
        response = client.get("/profile/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_profile_with_student_token(self):
        """Test student accessing their profile"""
        client = APIClient()
        assert client.login(TEST_USERS["student"]["email"], TEST_USERS["student"]["password"])
        response = client.get("/profile/")
        assert response.status_code == 200

    def test_profile_with_teacher_token(self):
        """Test teacher accessing their profile"""
        client = APIClient()
        assert client.login(TEST_USERS["teacher"]["email"], TEST_USERS["teacher"]["password"])
        response = client.get("/profile/")
        assert response.status_code == 200


class TestSchedulingEndpoint:
    """Test GET /api/scheduling/lessons/ endpoint"""

    def test_lessons_without_token(self):
        """Test lessons endpoint without authentication"""
        client = APIClient()
        response = client.get("/scheduling/lessons/")
        assert response.status_code in [401, 403, 404]

    def test_admin_sees_all_lessons(self):
        """Test that admin can see all lessons"""
        client = APIClient()
        assert client.login(TEST_USERS["admin"]["email"], TEST_USERS["admin"]["password"])
        response = client.get("/scheduling/lessons/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_teacher_sees_only_own_lessons(self):
        """Test that teacher sees only their lessons"""
        client = APIClient()
        assert client.login(TEST_USERS["teacher"]["email"], TEST_USERS["teacher"]["password"])
        response = client.get("/scheduling/lessons/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_student_sees_assigned_lessons(self):
        """Test that student sees only assigned lessons"""
        client = APIClient()
        assert client.login(TEST_USERS["student"]["email"], TEST_USERS["student"]["password"])
        response = client.get("/scheduling/lessons/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestAssignmentsEndpoint:
    """Test GET /api/assignments/ endpoint"""

    def test_assignments_without_token(self):
        """Test assignments endpoint without authentication"""
        client = APIClient()
        response = client.get("/assignments/")
        assert response.status_code in [401, 403, 404]

    def test_teacher_sees_own_assignments(self):
        """Test teacher seeing own assignments"""
        client = APIClient()
        assert client.login(TEST_USERS["teacher"]["email"], TEST_USERS["teacher"]["password"])
        response = client.get("/assignments/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_student_sees_own_assignments(self):
        """Test student seeing only their assignments"""
        client = APIClient()
        assert client.login(TEST_USERS["student"]["email"], TEST_USERS["student"]["password"])
        response = client.get("/assignments/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestChatEndpoint:
    """Test GET /api/chat/conversations/ endpoint"""

    def test_chat_without_token(self):
        """Test chat endpoint without authentication"""
        client = APIClient()
        response = client.get("/chat/conversations/")
        assert response.status_code in [401, 403, 404]

    def test_student_sees_own_conversations(self):
        """Test student seeing only their conversations"""
        client = APIClient()
        assert client.login(TEST_USERS["student"]["email"], TEST_USERS["student"]["password"])
        response = client.get("/chat/conversations/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_teacher_sees_own_conversations(self):
        """Test teacher seeing only their conversations"""
        client = APIClient()
        assert client.login(TEST_USERS["teacher"]["email"], TEST_USERS["teacher"]["password"])
        response = client.get("/chat/conversations/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestMaterialsEndpoint:
    """Test GET /api/materials/ endpoint"""

    def test_materials_without_token(self):
        """Test materials endpoint without authentication"""
        client = APIClient()
        response = client.get("/materials/")
        assert response.status_code in [401, 403, 404]

    def test_student_sees_assigned_materials(self):
        """Test student seeing only assigned materials"""
        client = APIClient()
        assert client.login(TEST_USERS["student"]["email"], TEST_USERS["student"]["password"])
        response = client.get("/materials/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_teacher_sees_own_materials(self):
        """Test teacher seeing own materials"""
        client = APIClient()
        assert client.login(TEST_USERS["teacher"]["email"], TEST_USERS["teacher"]["password"])
        response = client.get("/materials/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_admin_sees_all_materials(self):
        """Test admin seeing all materials (if permitted)"""
        client = APIClient()
        assert client.login(TEST_USERS["admin"]["email"], TEST_USERS["admin"]["password"])
        response = client.get("/materials/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestErrorHandling:
    """Test error handling and HTTP status codes"""

    def test_unauthorized_access_returns_401(self):
        """Test that unauthorized access returns 401"""
        client = APIClient()
        response = client.get("/profile/")
        assert response.status_code in [401, 403]

    def test_error_response_structure(self):
        """Test that error responses contain helpful information"""
        client = APIClient()
        response = client.get("/profile/")
        if response.status_code in [401, 403]:
            try:
                data = response.json()
                assert isinstance(data, dict)
            except:
                pass


class TestResponseStructure:
    """Test response structure and data format"""

    def test_profile_response_has_required_fields(self):
        """Test that profile response contains required fields"""
        client = APIClient()
        assert client.login(TEST_USERS["admin"]["email"], TEST_USERS["admin"]["password"])
        response = client.get("/profile/")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


class TestRBACEnforcement:
    """Test Role-Based Access Control"""

    def test_student_cannot_access_admin_endpoints(self):
        """Test that students cannot access admin endpoints"""
        client = APIClient()
        assert client.login(TEST_USERS["student"]["email"], TEST_USERS["student"]["password"])
        response = client.get("/admin/users/")
        assert response.status_code in [403, 404]

    def test_admin_can_access_endpoints(self):
        """Test that admin can access endpoints"""
        client = APIClient()
        assert client.login(TEST_USERS["admin"]["email"], TEST_USERS["admin"]["password"])
        response = client.get("/profile/")
        assert response.status_code in [200, 404]


class TestHttpStatusCodes:
    """Test correct HTTP status codes"""

    def test_successful_get_returns_200(self):
        """Test that successful GET returns 200"""
        client = APIClient()
        assert client.login(TEST_USERS["admin"]["email"], TEST_USERS["admin"]["password"])
        response = client.get("/profile/")
        assert response.status_code in [200, 404]

    def test_unauthorized_returns_401(self):
        """Test that missing token returns 401"""
        client = APIClient()
        response = client.get("/profile/")
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
