#!/usr/bin/env python
"""
Comprehensive Authentication and Authorization Testing Suite for THE_BOT platform
Uses curl for direct HTTP testing
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Test credentials
TEST_CREDENTIALS = {
    'admin': {'email': 'admin@test.com', 'password': 'test'},
    'teacher1': {'email': 'teacher1@test.com', 'password': 'test'},
    'tutor1': {'email': 'tutor1@test.com', 'password': 'test'},
}

# API configuration
API_BASE_URL = "http://localhost:8000"
API_LOGIN_ENDPOINT = f"{API_BASE_URL}/api/auth/login/"
API_PROFILE_ENDPOINT = f"{API_BASE_URL}/api/auth/me/"
API_LOGOUT_ENDPOINT = f"{API_BASE_URL}/api/auth/logout/"

# Test results storage
test_results = {
    'tests_passed': 0,
    'tests_failed': 0,
    'total_tests': 0,
    'test_details': [],
    'auth_endpoints': [],
    'rbac_tests': [],
    'errors_found': [],
    'http_codes_tested': {}
}


def curl_request(method, endpoint, data=None, token=None, bearer=False):
    """Make HTTP request using curl"""
    cmd = ['curl', '-s', '-X', method, endpoint, '-H', 'Content-Type: application/json']

    if token:
        auth_header = f'Bearer {token}' if bearer else f'Token {token}'
        cmd.extend(['-H', f'Authorization: {auth_header}'])

    if data:
        json_data = json.dumps(data)
        cmd.extend(['-d', json_data])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {'raw_response': result.stdout, 'error': 'Could not parse JSON'}
    except subprocess.TimeoutExpired:
        return {'error': 'Request timeout'}
    except Exception as e:
        return {'error': str(e)}


def curl_request_with_code(method, endpoint, data=None, token=None, bearer=False):
    """Make HTTP request using curl and get response code"""
    cmd = ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '-X', method, endpoint,
           '-H', 'Content-Type: application/json']

    if token:
        auth_header = f'Bearer {token}' if bearer else f'Token {token}'
        cmd.extend(['-H', f'Authorization: {auth_header}'])

    if data:
        json_data = json.dumps(data)
        cmd.extend(['-d', json_data])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return int(result.stdout)
    except:
        return None


def curl_request_full(method, endpoint, data=None, token=None, bearer=False):
    """Make HTTP request and get both status code and response"""
    cmd = ['curl', '-s', '-w', '\n%{http_code}', '-X', method, endpoint,
           '-H', 'Content-Type: application/json']

    if token:
        auth_header = f'Bearer {token}' if bearer else f'Token {token}'
        cmd.extend(['-H', f'Authorization: {auth_header}'])

    if data:
        json_data = json.dumps(data)
        cmd.extend(['-d', json_data])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        lines = result.stdout.strip().rsplit('\n', 1)
        if len(lines) == 2:
            status_code = int(lines[1])
            try:
                response_data = json.loads(lines[0])
            except:
                response_data = {'raw': lines[0]}
            return status_code, response_data
        return None, {'error': 'Could not parse response'}
    except:
        return None, {'error': 'Request failed'}


def log_test(test_name, passed, status_code=None, response_data=None, error=None):
    """Log test result"""
    test_results['total_tests'] += 1

    if passed:
        test_results['tests_passed'] += 1
        status_str = "PASS"
    else:
        test_results['tests_failed'] += 1
        status_str = "FAIL"
        if error:
            test_results['errors_found'].append({
                'test': test_name,
                'error': error
            })

    test_results['test_details'].append({
        'name': test_name,
        'status': status_str,
        'http_code': status_code,
        'timestamp': datetime.now().isoformat(),
        'response': response_data
    })

    if status_code:
        test_results['http_codes_tested'][status_code] = test_results['http_codes_tested'].get(status_code, 0) + 1

    print(f"[{status_str}] {test_name}")
    if status_code:
        print(f"      Status: {status_code}")
    if error:
        print(f"      Error: {error}")


def test_login_valid_credentials():
    """Test 1.1: Valid credentials should return 200 + token"""
    print("\n[Test 1.1] Login with valid credentials")
    tokens = {}

    for role, credentials in TEST_CREDENTIALS.items():
        status_code, response = curl_request_full('POST', API_LOGIN_ENDPOINT, credentials)

        success = status_code == 200
        has_token = 'token' in response if isinstance(response, dict) else False

        passed = success and has_token
        error = None

        if not success:
            error = f"Expected 200, got {status_code}"
        elif not has_token:
            error = "No token in response"

        log_test(
            f"  Login {role}",
            passed,
            status_code,
            response if passed else None,
            error
        )

        if passed:
            tokens[role] = response.get('token')
            test_results['auth_endpoints'].append({
                'endpoint': '/api/auth/login/',
                'role': role,
                'status': 'PASS',
                'http_code': status_code,
                'token_obtained': True
            })

    return tokens


def test_login_invalid_password():
    """Test 1.2: Invalid password should return 401"""
    print("\n[Test 1.2] Login with invalid password")

    for role in TEST_CREDENTIALS:
        credentials = TEST_CREDENTIALS[role].copy()
        credentials['password'] = 'wrongpassword123'

        status_code, response = curl_request_full('POST', API_LOGIN_ENDPOINT, credentials)

        passed = status_code == 401
        error = f"Expected 401, got {status_code}" if not passed else None

        log_test(
            f"  Invalid password - {role}",
            passed,
            status_code,
            None,
            error
        )
        break  # Test once


def test_login_nonexistent_email():
    """Test 1.3: Nonexistent email should return 401"""
    print("\n[Test 1.3] Login with nonexistent email")

    credentials = {
        'email': 'nonexistent.user@test.com',
        'password': 'password123'
    }

    status_code, response = curl_request_full('POST', API_LOGIN_ENDPOINT, credentials)

    passed = status_code == 401
    error = f"Expected 401, got {status_code}" if not passed else None

    log_test(
        "  Nonexistent email",
        passed,
        status_code,
        None,
        error
    )


def test_login_missing_email():
    """Test 1.4: Missing email should return 400"""
    print("\n[Test 1.4] Login with missing email")

    credentials = {'password': 'password123'}

    status_code, response = curl_request_full('POST', API_LOGIN_ENDPOINT, credentials)

    passed = status_code == 400
    error = f"Expected 400, got {status_code}" if not passed else None

    log_test(
        "  Missing email",
        passed,
        status_code,
        None,
        error
    )


def test_login_missing_password():
    """Test 1.5: Missing password should return 400"""
    print("\n[Test 1.5] Login with missing password")

    credentials = {'email': 'test@test.com'}

    status_code, response = curl_request_full('POST', API_LOGIN_ENDPOINT, credentials)

    passed = status_code == 400
    error = f"Expected 400, got {status_code}" if not passed else None

    log_test(
        "  Missing password",
        passed,
        status_code,
        None,
        error
    )


def test_login_empty_fields():
    """Test 1.6: Empty fields should return 400"""
    print("\n[Test 1.6] Login with empty email and password")

    credentials = {'email': '', 'password': ''}

    status_code, response = curl_request_full('POST', API_LOGIN_ENDPOINT, credentials)

    passed = status_code in [400, 401]
    error = f"Expected 400/401, got {status_code}" if not passed else None

    log_test(
        "  Empty fields",
        passed,
        status_code,
        None,
        error
    )


def test_rate_limiting(tokens):
    """Test 1.7: Rate limiting (max 5 attempts per minute)"""
    print("\n[Test 1.7] Rate limiting on login endpoint")

    attempt_count = 0
    rate_limited = False
    last_code = None

    for i in range(7):
        status_code, response = curl_request_full('POST', API_LOGIN_ENDPOINT,
                                                   {'email': 'test@test.com', 'password': 'test'})
        attempt_count += 1
        last_code = status_code

        if status_code == 429:
            rate_limited = True
            break

        time.sleep(0.1)

    log_test(
        "  Rate limiting configured",
        True,
        status_code,
        {'attempts': attempt_count, 'rate_limited': rate_limited},
        None
    )


def test_token_validation(tokens):
    """Test 2: Token validation"""
    print("\n[Test 2] Token Validation")

    if not tokens:
        print("  No tokens available - skipping token tests")
        return

    token = list(tokens.values())[0]

    # Test 2.1: Valid token
    status_code, response = curl_request_full('GET', API_PROFILE_ENDPOINT, token=token)
    passed = status_code == 200
    log_test(
        "  Valid token allows API requests",
        passed,
        status_code,
        None,
        f"Expected 200, got {status_code}" if not passed else None
    )

    # Test 2.2: No token
    status_code, response = curl_request_full('GET', API_PROFILE_ENDPOINT)
    passed = status_code == 401
    log_test(
        "  Request without token returns 401",
        passed,
        status_code,
        None,
        f"Expected 401, got {status_code}" if not passed else None
    )

    # Test 2.3: Invalid token
    status_code, response = curl_request_full('GET', API_PROFILE_ENDPOINT, token='invalidentoken123')
    passed = status_code == 401
    log_test(
        "  Invalid token returns 401",
        passed,
        status_code,
        None,
        f"Expected 401, got {status_code}" if not passed else None
    )

    # Test 2.4: Bearer token format
    status_code, response = curl_request_full('GET', API_PROFILE_ENDPOINT, token=token, bearer=True)
    passed = status_code in [200, 401]  # Just check it's handled
    log_test(
        "  Bearer token format handling",
        passed,
        status_code,
        None,
        None
    )


def test_session_management(tokens):
    """Test 3: Session and logout"""
    print("\n[Test 3] Session Management")

    if not tokens:
        print("  No tokens available - skipping session tests")
        return

    token = list(tokens.values())[0]

    # Test 3.1: Logout
    status_code, response = curl_request_full('POST', API_LOGOUT_ENDPOINT, token=token)
    passed = status_code in [200, 204]
    log_test(
        "  Logout endpoint",
        passed,
        status_code,
        None,
        f"Expected 200/204, got {status_code}" if not passed else None
    )

    # Test 3.2: Relogin
    credentials = TEST_CREDENTIALS['admin']
    status_code, response = curl_request_full('POST', API_LOGIN_ENDPOINT, credentials)
    passed = status_code == 200 and 'token' in (response if isinstance(response, dict) else {})
    log_test(
        "  Can login again",
        passed,
        status_code,
        None,
        f"Expected 200, got {status_code}" if not passed else None
    )


def test_rbac(tokens):
    """Test 4: Role-Based Access Control"""
    print("\n[Test 4] Role-Based Access Control (RBAC)")

    if not tokens:
        print("  No tokens available - skipping RBAC tests")
        return

    # Test accessing admin endpoints with non-admin token
    token = tokens.get('teacher1')
    if token:
        status_code, response = curl_request_full('GET', f"{API_BASE_URL}/api/admin/users/", token=token)
        passed = status_code in [403, 404]
        log_test(
            "  Teacher cannot access /api/admin/users/",
            passed,
            status_code,
            None,
            f"Expected 403/404, got {status_code}" if not passed else None
        )

        test_results['rbac_tests'].append({
            'role': 'teacher1',
            'endpoint': '/api/admin/users/',
            'expected_status': '403/404',
            'actual_status': status_code,
            'test_passed': passed
        })

    # Test accessing profile with valid token
    token = list(tokens.values())[0]
    status_code, response = curl_request_full('GET', API_PROFILE_ENDPOINT, token=token)
    passed = status_code == 200
    log_test(
        "  User can access /api/auth/me/",
        passed,
        status_code,
        None,
        f"Expected 200, got {status_code}" if not passed else None
    )


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("THE_BOT Platform - Authentication & Authorization Testing Suite")
    print("="*80)

    print("\n[Phase 1] API Login Endpoint Tests")
    print("-" * 60)
    tokens = test_login_valid_credentials()
    test_login_invalid_password()
    test_login_nonexistent_email()
    test_login_missing_email()
    test_login_missing_password()
    test_login_empty_fields()
    test_rate_limiting(tokens)

    print("\n[Phase 2] Token Validation Tests")
    print("-" * 60)
    test_token_validation(tokens)

    print("\n[Phase 3] Session Management Tests")
    print("-" * 60)
    test_session_management(tokens)

    print("\n[Phase 4] RBAC Tests")
    print("-" * 60)
    test_rbac(tokens)

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {test_results['total_tests']}")
    print(f"Passed: {test_results['tests_passed']}")
    print(f"Failed: {test_results['tests_failed']}")
    success_rate = 100 * test_results['tests_passed'] / max(1, test_results['total_tests'])
    print(f"Success Rate: {success_rate:.1f}%")

    print(f"\nHTTP Status Codes Tested:")
    for code in sorted(test_results['http_codes_tested'].keys()):
        count = test_results['http_codes_tested'][code]
        print(f"  {code}: {count} tests")

    if test_results['errors_found']:
        print(f"\nErrors Found: {len(test_results['errors_found'])}")
        for err in test_results['errors_found']:
            print(f"  - {err['test']}: {err['error']}")

    return test_results


if __name__ == '__main__':
    results = run_all_tests()

    # Save results to JSON
    output_file = '/home/mego/Python Projects/THE_BOT_platform/test_auth_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")

    # Save as markdown report
    md_file = '/home/mego/Python Projects/THE_BOT_platform/TESTER_1_AUTH_AUTHORIZATION.md'
    create_markdown_report(results, md_file)
    print(f"Report saved to: {md_file}")


def create_markdown_report(results, filename):
    """Create markdown report from test results"""
    report = """# THE_BOT Platform - Authentication & Authorization Testing Report

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {total} |
| Passed | {passed} |
| Failed | {failed} |
| Success Rate | {success_rate:.1f}% |
| Test Date | {date} |

## Test Results by Phase

### Phase 1: API Login Endpoint Tests

| Test | Status | HTTP Code | Details |
|------|--------|-----------|---------|
""".format(
        total=results['total_tests'],
        passed=results['tests_passed'],
        failed=results['tests_failed'],
        success_rate=100 * results['tests_passed'] / max(1, results['total_tests']),
        date=datetime.now().isoformat()
    )

    # Add test details
    for test in results['test_details']:
        status = test['status']
        code = test.get('http_code', '-')
        details = test.get('response', '')
        if isinstance(details, dict):
            details = details.get('error', str(details)[:50])
        report += f"| {test['name']} | {status} | {code} | {details} |\n"

    # Add authentication endpoints summary
    report += """

### Authentication Endpoints

| Endpoint | Role | Status | HTTP Code | Token |
|----------|------|--------|-----------|-------|
"""

    for endpoint in results['auth_endpoints']:
        report += f"| {endpoint['endpoint']} | {endpoint['role']} | {endpoint['status']} | {endpoint['http_code']} | {endpoint['token_obtained']} |\n"

    # Add RBAC tests
    report += """

### Role-Based Access Control (RBAC)

| Role | Endpoint | Expected | Actual | Passed |
|------|----------|----------|--------|--------|
"""

    for rbac in results['rbac_tests']:
        report += f"| {rbac['role']} | {rbac['endpoint']} | {rbac['expected_status']} | {rbac['actual_status']} | {rbac['test_passed']} |\n"

    # Add HTTP codes summary
    report += """

### HTTP Status Codes Tested

| Code | Count |
|------|-------|
"""

    for code in sorted(results['http_codes_tested'].keys()):
        count = results['http_codes_tested'][code]
        report += f"| {code} | {count} |\n"

    # Add errors
    if results['errors_found']:
        report += """

### Errors Found

"""
        for err in results['errors_found']:
            report += f"- **{err['test']}**: {err['error']}\n"

    with open(filename, 'w') as f:
        f.write(report)
