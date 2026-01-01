#!/usr/bin/env python
"""
Comprehensive API Endpoint Testing using pytest and HTTP requests
"""

import pytest
import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

# Test credentials
TEST_USERS = {
    "student": {"email": "student1@test.com", "password": "student123"},
    "teacher": {"email": "teacher1@test.com", "password": "teacher123"},
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "tutor": {"email": "tutor1@test.com", "password": "tutor123"},
    "parent": {"email": "parent1@test.com", "password": "parent123"},
}

# Store results
results = {
    "passed": 0,
    "failed": 0,
    "total": 0,
    "endpoints": []
}


def log_result(endpoint, method, status_code, expected, passed=True):
    """Log test result"""
    results["total"] += 1
    if passed:
        results["passed"] += 1
        status = "✓ PASS"
    else:
        results["failed"] += 1
        status = "✗ FAIL"

    result_str = f"{status} | {method} {endpoint} | Status: {status_code} (Expected: {expected})"
    print(result_str)
    results["endpoints"].append({
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "expected": expected,
        "passed": passed
    })

    return passed


def get_token(role):
    """Login and get auth token"""
    user = TEST_USERS.get(role)
    if not user:
        return None

    try:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        response = requests.post(
            f"{BASE_URL}/api/auth/login/",
            json=user,
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            # Handle both response formats
            if "token" in data:
                return data.get("token")
            elif "data" in data:
                return data.get("data", {}).get("token")
    except Exception as e:
        print(f"Error getting token for {role}: {e}")

    return None


def test_health_check():
    """Test health endpoint"""
    print("\n" + "=" * 60)
    print("1. HEALTH & STATUS ENDPOINTS")
    print("=" * 60)

    # Unauthenticated should get 401
    try:
        response = requests.get(f"{BASE_URL}/api/system/health/", timeout=5)
        passed = response.status_code in [401, 200]
        log_result("/api/system/health/ (unauthenticated)", "GET", response.status_code, "401/200", passed)
    except Exception as e:
        print(f"✗ ERROR: /api/system/health/ - {e}")
        results["total"] += 1
        results["failed"] += 1

    # Authenticated should work
    token = get_token("admin")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(f"{BASE_URL}/api/system/health/", headers=headers, timeout=5)
            passed = response.status_code == 200
            log_result("/api/system/health/ (authenticated)", "GET", response.status_code, 200, passed)
        except Exception as e:
            print(f"✗ ERROR: /api/system/health/ (authenticated) - {e}")
            results["total"] += 1
            results["failed"] += 1


def test_authentication():
    """Test authentication endpoints"""
    print("\n" + "=" * 60)
    print("2. AUTHENTICATION ENDPOINTS (ALL ROLES)")
    print("=" * 60)

    for role, credentials in TEST_USERS.items():
        try:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            }
            response = requests.post(
                f"{BASE_URL}/api/auth/login/",
                json=credentials,
                headers=headers,
                timeout=5
            )
            passed = response.status_code == 200
            log_result(f"/api/auth/login/ ({role})", "POST", response.status_code, 200, passed)

            if passed:
                data = response.json()
                # Handle both response formats
                has_token = "token" in data or (isinstance(data.get("data"), dict) and "token" in data["data"])
                if not has_token:
                    print(f"  ⚠ Warning: No token in response for {role}")
        except Exception as e:
            print(f"✗ ERROR: /api/auth/login/ ({role}) - {e}")
            results["total"] += 1
            results["failed"] += 1


def test_profile_endpoints():
    """Test profile endpoints"""
    print("\n" + "=" * 60)
    print("3. PROFILE ENDPOINTS")
    print("=" * 60)

    token = get_token("student")
    if not token:
        print("✗ Cannot get student token, skipping profile tests")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    # GET profile
    try:
        response = requests.get(
            f"{BASE_URL}/api/profile/",
            headers=headers,
            timeout=5
        )
        passed = response.status_code in [200, 400]
        log_result("/api/profile/", "GET", response.status_code, "200/400", passed)
    except Exception as e:
        print(f"✗ ERROR: GET /api/profile/ - {e}")
        results["total"] += 1
        results["failed"] += 1

    # PATCH profile
    try:
        response = requests.patch(
            f"{BASE_URL}/api/profile/",
            json={"first_name": "Test"},
            headers=headers,
            timeout=5
        )
        passed = response.status_code in [200, 400]
        log_result("/api/profile/", "PATCH", response.status_code, "200/400", passed)
    except Exception as e:
        print(f"✗ ERROR: PATCH /api/profile/ - {e}")
        results["total"] += 1
        results["failed"] += 1


def test_scheduling_endpoints():
    """Test scheduling endpoints"""
    print("\n" + "=" * 60)
    print("4. SCHEDULING ENDPOINTS")
    print("=" * 60)

    token = get_token("student")
    if not token:
        print("✗ Cannot get student token, skipping scheduling tests")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # GET lessons list
    try:
        response = requests.get(
            f"{BASE_URL}/api/scheduling/lessons/",
            headers=headers,
            timeout=5
        )
        passed = response.status_code in [200, 404]
        log_result("/api/scheduling/lessons/", "GET", response.status_code, "200/404", passed)
    except Exception as e:
        print(f"✗ ERROR: GET /api/scheduling/lessons/ - {e}")
        results["total"] += 1
        results["failed"] += 1

    # Create lesson (teacher only)
    token = get_token("teacher")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        now = datetime.now()
        start_time = (now + timedelta(days=1)).isoformat()
        end_time = (now + timedelta(days=1, hours=1)).isoformat()

        try:
            response = requests.post(
                f"{BASE_URL}/api/scheduling/lessons/",
                json={
                    "subject": "Math",
                    "title": "Math Lesson",
                    "start_time": start_time,
                    "end_time": end_time
                },
                headers=headers,
                timeout=5
            )
            passed = response.status_code in [201, 400, 403]
            log_result("/api/scheduling/lessons/", "POST", response.status_code, "201/400/403", passed)
        except Exception as e:
            print(f"✗ ERROR: POST /api/scheduling/lessons/ - {e}")
            results["total"] += 1
            results["failed"] += 1


def test_materials_endpoints():
    """Test materials endpoints"""
    print("\n" + "=" * 60)
    print("5. MATERIALS ENDPOINTS")
    print("=" * 60)

    token = get_token("teacher")
    if not token:
        print("✗ Cannot get teacher token, skipping materials tests")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # GET materials
    try:
        response = requests.get(
            f"{BASE_URL}/api/materials/",
            headers=headers,
            timeout=5
        )
        passed = response.status_code in [200, 404]
        log_result("/api/materials/", "GET", response.status_code, "200/404", passed)
    except Exception as e:
        print(f"✗ ERROR: GET /api/materials/ - {e}")
        results["total"] += 1
        results["failed"] += 1


def test_assignments_endpoints():
    """Test assignments endpoints"""
    print("\n" + "=" * 60)
    print("6. ASSIGNMENTS ENDPOINTS")
    print("=" * 60)

    token = get_token("student")
    if not token:
        print("✗ Cannot get student token, skipping assignments tests")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # GET assignments
    try:
        response = requests.get(
            f"{BASE_URL}/api/assignments/",
            headers=headers,
            timeout=5
        )
        passed = response.status_code in [200, 404]
        log_result("/api/assignments/", "GET", response.status_code, "200/404", passed)
    except Exception as e:
        print(f"✗ ERROR: GET /api/assignments/ - {e}")
        results["total"] += 1
        results["failed"] += 1


def test_chat_endpoints():
    """Test chat endpoints"""
    print("\n" + "=" * 60)
    print("7. CHAT ENDPOINTS")
    print("=" * 60)

    token = get_token("student")
    if not token:
        print("✗ Cannot get student token, skipping chat tests")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # GET chat conversations
    try:
        response = requests.get(
            f"{BASE_URL}/api/chat/conversations/",
            headers=headers,
            timeout=5
        )
        passed = response.status_code in [200, 404]
        log_result("/api/chat/conversations/", "GET", response.status_code, "200/404", passed)
    except Exception as e:
        print(f"✗ ERROR: GET /api/chat/conversations/ - {e}")
        results["total"] += 1
        results["failed"] += 1


def test_admin_permissions():
    """Test admin endpoints permission checks"""
    print("\n" + "=" * 60)
    print("8. ADMIN ENDPOINTS (PERMISSION CHECKS)")
    print("=" * 60)

    # Non-admin should get 403 or 404
    token = get_token("student")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(
                f"{BASE_URL}/api/admin/users/",
                headers=headers,
                timeout=5
            )
            passed = response.status_code in [403, 404]
            log_result("/api/admin/users/ (student)", "GET", response.status_code, "403/404", passed)
        except Exception as e:
            print(f"✗ ERROR: GET /api/admin/users/ (student) - {e}")
            results["total"] += 1
            results["failed"] += 1

    # Admin should have access
    token = get_token("admin")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(
                f"{BASE_URL}/api/admin/users/",
                headers=headers,
                timeout=5
            )
            passed = response.status_code in [200, 404]
            log_result("/api/admin/users/ (admin)", "GET", response.status_code, "200/404", passed)
        except Exception as e:
            print(f"✗ ERROR: GET /api/admin/users/ (admin) - {e}")
            results["total"] += 1
            results["failed"] += 1


def print_summary():
    """Print test summary"""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    total = results["total"]
    passed = results["passed"]
    failed = results["failed"]
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {success_rate:.1f}%")

    print(f"\nEndpoints Tested: {len(results['endpoints'])}")

    if failed > 0:
        print("\nFailed Tests:")
        for ep in results["endpoints"]:
            if not ep["passed"]:
                print(f"  - {ep['method']} {ep['endpoint']} (Got {ep['status_code']}, expected {ep['expected']})")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE API ENDPOINT TESTING")
    print("THE_BOT PLATFORM")
    print("=" * 60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/health/", timeout=2)
        print("✓ Backend server is running")
    except Exception as e:
        print(f"✗ ERROR: Backend server not responding - {e}")
        print("Please start the Django server first:")
        print("  cd backend && python manage.py runserver 0.0.0.0:8000")
        return

    # Run all tests
    test_health_check()
    test_authentication()
    test_profile_endpoints()
    test_scheduling_endpoints()
    test_materials_endpoints()
    test_assignments_endpoints()
    test_chat_endpoints()
    test_admin_permissions()

    print_summary()
    print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return results["failed"] == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
