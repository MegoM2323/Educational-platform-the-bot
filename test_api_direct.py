#!/usr/bin/env python
"""
Direct API testing using subprocess and curl
"""

import subprocess
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"

TEST_USERS = {
    "student": {"email": "student1@test.com", "password": "student123"},
    "teacher": {"email": "teacher1@test.com", "password": "teacher123"},
    "admin": {"email": "admin@test.com", "password": "admin123"},
    "tutor": {"email": "tutor1@test.com", "password": "tutor123"},
    "parent": {"email": "parent1@test.com", "password": "parent123"},
}

results = {
    "passed": 0,
    "failed": 0,
    "total": 0,
    "endpoints": []
}


def curl_request(method, endpoint, data=None, headers=None):
    """Make request using curl"""
    try:
        cmd = ["curl", "-s", "-w", "\n%{http_code}"]

        if method == "POST":
            cmd.append("-X")
            cmd.append("POST")

        if headers:
            for key, value in headers.items():
                cmd.extend(["-H", f"{key}: {value}"])

        if data:
            cmd.extend(["-d", json.dumps(data)])

        url = f"{BASE_URL}{endpoint}"
        cmd.append(url)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        output = result.stdout.strip()

        # Split output from status code (last line)
        lines = output.split("\n")
        status_code = int(lines[-1]) if lines[-1].isdigit() else 0
        body = "\n".join(lines[:-1])

        return status_code, body
    except Exception as e:
        return 0, str(e)


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

    headers = {
        "Content-Type": "application/json"
    }

    status_code, body = curl_request("POST", "/api/auth/login/", data=user, headers=headers)

    if status_code == 200 and body:
        try:
            data = json.loads(body)
            # Handle both response formats
            if "token" in data:
                token = data.get("token")
                if token:
                    return token
            elif "data" in data:
                token = data.get("data", {}).get("token")
                if token:
                    return token
        except Exception as e:
            pass

    return None


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE API ENDPOINT TESTING")
    print("THE_BOT PLATFORM (CURL)")
    print("=" * 60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")

    # Check if server is running
    status_code, _ = curl_request("GET", "/api/system/health/")
    if status_code > 0:
        print("✓ Backend server is running")
    else:
        print("✗ Backend server not responding")
        return

    # Test authentication
    print("\n" + "=" * 60)
    print("1. AUTHENTICATION ENDPOINTS (ALL ROLES)")
    print("=" * 60)

    for role, credentials in TEST_USERS.items():
        headers = {"Content-Type": "application/json"}
        status_code, body = curl_request("POST", "/api/auth/login/", data=credentials, headers=headers)
        passed = status_code == 200
        log_result(f"/api/auth/login/ ({role})", "POST", status_code, 200, passed)

        if passed and body:
            try:
                data = json.loads(body)
                has_token = "token" in data or ("data" in data and "token" in data.get("data", {}))
                if has_token:
                    print(f"  ✓ Token obtained for {role}")
            except:
                pass

    # Test profile endpoints (student)
    print("\n" + "=" * 60)
    print("2. PROFILE ENDPOINTS")
    print("=" * 60)

    token = get_token("student")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        status_code, _ = curl_request("GET", "/api/profile/", headers=headers)
        passed = status_code in [200, 400]
        log_result("/api/profile/", "GET", status_code, "200/400", passed)
    else:
        print("✗ Cannot get student token, skipping profile tests")

    # Test scheduling endpoints
    print("\n" + "=" * 60)
    print("3. SCHEDULING ENDPOINTS")
    print("=" * 60)

    token = get_token("student")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        status_code, _ = curl_request("GET", "/api/scheduling/lessons/", headers=headers)
        passed = status_code in [200, 404]
        log_result("/api/scheduling/lessons/", "GET", status_code, "200/404", passed)
    else:
        print("✗ Cannot get student token, skipping scheduling tests")

    # Test materials endpoints
    print("\n" + "=" * 60)
    print("4. MATERIALS ENDPOINTS")
    print("=" * 60)

    token = get_token("teacher")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        status_code, _ = curl_request("GET", "/api/materials/", headers=headers)
        passed = status_code in [200, 404]
        log_result("/api/materials/", "GET", status_code, "200/404", passed)
    else:
        print("✗ Cannot get teacher token, skipping materials tests")

    # Test assignments endpoints
    print("\n" + "=" * 60)
    print("5. ASSIGNMENTS ENDPOINTS")
    print("=" * 60)

    token = get_token("student")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        status_code, _ = curl_request("GET", "/api/assignments/", headers=headers)
        passed = status_code in [200, 404]
        log_result("/api/assignments/", "GET", status_code, "200/404", passed)
    else:
        print("✗ Cannot get student token, skipping assignments tests")

    # Test chat endpoints
    print("\n" + "=" * 60)
    print("6. CHAT ENDPOINTS")
    print("=" * 60)

    token = get_token("student")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        status_code, _ = curl_request("GET", "/api/chat/conversations/", headers=headers)
        passed = status_code in [200, 404]
        log_result("/api/chat/conversations/", "GET", status_code, "200/404", passed)
    else:
        print("✗ Cannot get student token, skipping chat tests")

    # Test admin endpoints permission
    print("\n" + "=" * 60)
    print("7. ADMIN ENDPOINTS (PERMISSION CHECKS)")
    print("=" * 60)

    token = get_token("student")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        status_code, _ = curl_request("GET", "/api/admin/users/", headers=headers)
        passed = status_code in [403, 404]
        log_result("/api/admin/users/ (student)", "GET", status_code, "403/404", passed)
    else:
        print("✗ Cannot get student token")

    token = get_token("admin")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        status_code, _ = curl_request("GET", "/api/admin/users/", headers=headers)
        passed = status_code in [200, 404]
        log_result("/api/admin/users/ (admin)", "GET", status_code, "200/404", passed)
    else:
        print("✗ Cannot get admin token")

    # Summary
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

    if failed > 0:
        print("\nFailed Tests:")
        for ep in results["endpoints"]:
            if not ep["passed"]:
                print(f"  - {ep['method']} {ep['endpoint']} (Got {ep['status_code']}, expected {ep['expected']})")

    print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
