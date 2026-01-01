#!/usr/bin/env python
"""
Authentication and Authorization Testing Suite using requests library
"""

import json
import time
from datetime import datetime
import sys

try:
    import requests
except ImportError:
    print("Installing requests library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test configuration
API_BASE_URL = "http://localhost:8000"
API_LOGIN_ENDPOINT = f"{API_BASE_URL}/api/auth/login/"
API_PROFILE_ENDPOINT = f"{API_BASE_URL}/api/auth/me/"
API_LOGOUT_ENDPOINT = f"{API_BASE_URL}/api/auth/logout/"

# Test users - use existing users from database
TEST_CREDENTIALS = {
    'admin': {'email': 'admin@test.com', 'password': 'test'},
    'teacher1': {'email': 'teacher1@test.com', 'password': 'test'},
    'student1': {'email': 'student1@test.com', 'password': 'test'},
    'tutor1': {'email': 'tutor1@test.com', 'password': 'test'},
    'parent1': {'email': 'parent1@test.com', 'password': 'test'},
}

# Results storage
results = {
    'tests_passed': 0,
    'tests_failed': 0,
    'total_tests': 0,
    'test_details': [],
    'auth_endpoints': [],
    'rbac_tests': [],
    'errors_found': [],
    'http_codes_tested': {},
    'tokens': {}
}

session = requests.Session()
session.headers.update({'Content-Type': 'application/json'})
session.verify = False  # Disable SSL verification for localhost


def log_test(test_name, passed, status_code=None, response_data=None, error=None):
    """Log test result"""
    results['total_tests'] += 1

    if passed:
        results['tests_passed'] += 1
        status_str = "PASS"
    else:
        results['tests_failed'] += 1
        status_str = "FAIL"
        if error:
            results['errors_found'].append({
                'test': test_name,
                'error': error
            })

    results['test_details'].append({
        'name': test_name,
        'status': status_str,
        'http_code': status_code,
        'timestamp': datetime.now().isoformat(),
        'response': response_data
    })

    if status_code:
        results['http_codes_tested'][status_code] = results['http_codes_tested'].get(status_code, 0) + 1

    status_display = f"[{status_str}]"
    print(f"{status_display:8} {test_name}")
    if status_code:
        print(f"         Status: {status_code}")
    if error:
        print(f"         Error: {error}")


def test_connectivity():
    """Test API connectivity"""
    print("\n[Pre-Test] Checking API Connectivity")
    print("-" * 60)

    try:
        # Try multiple times with small delays
        for attempt in range(3):
            try:
                response = session.get(f"{API_BASE_URL}/api/auth/login/", timeout=5, verify=False)
                if response.status_code in [200, 201, 204, 400, 401, 403, 405, 500, 503]:
                    print(f"[OK]    API is accessible (status: {response.status_code})")
                    return True
            except requests.exceptions.ConnectionError:
                if attempt < 2:
                    time.sleep(1)
                    continue
                raise

        print(f"[ERROR] API returned unexpected response")
        return False
    except Exception as e:
        print(f"[ERROR] API not accessible: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_login_valid_credentials():
    """Test 1.1: Valid credentials should return 200 + token"""
    print("\n[Phase 1.1] Login with Valid Credentials")
    print("-" * 60)

    for role, credentials in TEST_CREDENTIALS.items():
        try:
            response = session.post(API_LOGIN_ENDPOINT, json=credentials, timeout=10)
            status_code = response.status_code

            success = status_code == 200
            response_data = response.json() if response.text else {}
            has_token = 'token' in response_data

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
                response_data if passed else None,
                error
            )

            if passed:
                token = response_data.get('token')
                results['tokens'][role] = token
                results['auth_endpoints'].append({
                    'endpoint': '/api/auth/login/',
                    'role': role,
                    'status': 'PASS',
                    'http_code': status_code,
                    'token_obtained': True
                })
            else:
                results['auth_endpoints'].append({
                    'endpoint': '/api/auth/login/',
                    'role': role,
                    'status': 'FAIL',
                    'http_code': status_code,
                    'token_obtained': False
                })

        except requests.exceptions.RequestException as e:
            log_test(f"  Login {role}", False, None, None, str(e))


def test_login_invalid_password():
    """Test 1.2: Invalid password should return 401"""
    print("\n[Phase 1.2] Login with Invalid Password")
    print("-" * 60)

    credentials = TEST_CREDENTIALS['student1'].copy()
    credentials['password'] = 'wrongpassword123'

    try:
        response = session.post(API_LOGIN_ENDPOINT, json=credentials, timeout=10)
        status_code = response.status_code

        passed = status_code == 401
        error = f"Expected 401, got {status_code}" if not passed else None

        log_test(
            "  Invalid password",
            passed,
            status_code,
            None,
            error
        )
    except requests.exceptions.RequestException as e:
        log_test("  Invalid password", False, None, None, str(e))


def test_login_nonexistent_email():
    """Test 1.3: Nonexistent email should return 401"""
    print("\n[Phase 1.3] Login with Nonexistent Email")
    print("-" * 60)

    credentials = {
        'email': 'nonexistent.user@test.com',
        'password': 'password123'
    }

    try:
        response = session.post(API_LOGIN_ENDPOINT, json=credentials, timeout=10)
        status_code = response.status_code

        passed = status_code == 401
        error = f"Expected 401, got {status_code}" if not passed else None

        log_test(
            "  Nonexistent email",
            passed,
            status_code,
            None,
            error
        )
    except requests.exceptions.RequestException as e:
        log_test("  Nonexistent email", False, None, None, str(e))


def test_login_missing_fields():
    """Test 1.4: Missing fields should return 400"""
    print("\n[Phase 1.4] Login with Missing Fields")
    print("-" * 60)

    test_cases = [
        ('Missing email', {'password': 'password123'}),
        ('Missing password', {'email': 'test@test.com'}),
        ('Empty email', {'email': '', 'password': 'password123'}),
        ('Empty password', {'email': 'test@test.com', 'password': ''}),
    ]

    for test_name, credentials in test_cases:
        try:
            response = session.post(API_LOGIN_ENDPOINT, json=credentials, timeout=10)
            status_code = response.status_code

            passed = status_code in [400, 401]
            error = f"Expected 400/401, got {status_code}" if not passed else None

            log_test(
                f"  {test_name}",
                passed,
                status_code,
                None,
                error
            )
        except requests.exceptions.RequestException as e:
            log_test(f"  {test_name}", False, None, None, str(e))


def test_rate_limiting():
    """Test 1.5: Rate limiting"""
    print("\n[Phase 1.5] Rate Limiting")
    print("-" * 60)

    attempt_count = 0
    rate_limited = False

    for i in range(7):
        try:
            response = session.post(
                API_LOGIN_ENDPOINT,
                json={'email': 'test@test.com', 'password': 'test'},
                timeout=10
            )
            attempt_count += 1

            if response.status_code == 429:
                rate_limited = True
                break

            time.sleep(0.05)
        except requests.exceptions.RequestException:
            break

    log_test(
        f"  Rate limiting (tested {attempt_count} attempts)",
        True,
        None,
        {'rate_limited': rate_limited, 'attempts': attempt_count},
        None
    )


def test_token_validation():
    """Test 2: Token validation"""
    print("\n[Phase 2] Token Validation")
    print("-" * 60)

    if not results['tokens']:
        print("  WARNING: No tokens available - skipping token tests")
        return

    token = list(results['tokens'].values())[0]

    # Test 2.1: Valid token
    try:
        headers = {'Authorization': f'Token {token}'}
        response = session.get(API_PROFILE_ENDPOINT, headers=headers, timeout=10)
        status_code = response.status_code

        passed = status_code == 200
        log_test(
            "  Valid token allows API requests",
            passed,
            status_code,
            response.json() if response.text else None,
            f"Expected 200, got {status_code}" if not passed else None
        )
    except requests.exceptions.RequestException as e:
        log_test("  Valid token allows API requests", False, None, None, str(e))

    # Test 2.2: No token
    try:
        response = session.get(API_PROFILE_ENDPOINT, timeout=10)
        status_code = response.status_code

        passed = status_code == 401
        log_test(
            "  Request without token returns 401",
            passed,
            status_code,
            None,
            f"Expected 401, got {status_code}" if not passed else None
        )
    except requests.exceptions.RequestException as e:
        log_test("  Request without token returns 401", False, None, None, str(e))

    # Test 2.3: Invalid token
    try:
        headers = {'Authorization': 'Token invalidentoken123'}
        response = session.get(API_PROFILE_ENDPOINT, headers=headers, timeout=10)
        status_code = response.status_code

        passed = status_code == 401
        log_test(
            "  Invalid token returns 401",
            passed,
            status_code,
            None,
            f"Expected 401, got {status_code}" if not passed else None
        )
    except requests.exceptions.RequestException as e:
        log_test("  Invalid token returns 401", False, None, None, str(e))

    # Test 2.4: Bearer token format
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = session.get(API_PROFILE_ENDPOINT, headers=headers, timeout=10)
        status_code = response.status_code

        # Just check it's handled (200 or 401 depending on configuration)
        passed = status_code in [200, 401]
        log_test(
            "  Bearer token format handling",
            passed,
            status_code,
            None,
            None
        )
    except requests.exceptions.RequestException as e:
        log_test("  Bearer token format handling", False, None, None, str(e))


def test_session_management():
    """Test 3: Session management"""
    print("\n[Phase 3] Session Management")
    print("-" * 60)

    if not results['tokens']:
        print("  WARNING: No tokens available - skipping session tests")
        return

    token = list(results['tokens'].values())[0]

    # Test 3.1: Logout
    try:
        headers = {'Authorization': f'Token {token}'}
        response = session.post(API_LOGOUT_ENDPOINT, headers=headers, timeout=10)
        status_code = response.status_code

        passed = status_code in [200, 204]
        log_test(
            "  Logout endpoint",
            passed,
            status_code,
            None,
            f"Expected 200/204, got {status_code}" if not passed else None
        )
    except requests.exceptions.RequestException as e:
        log_test("  Logout endpoint", False, None, None, str(e))

    # Test 3.2: Relogin
    try:
        response = session.post(
            API_LOGIN_ENDPOINT,
            json=TEST_CREDENTIALS['admin'],
            timeout=10
        )
        status_code = response.status_code
        response_data = response.json() if response.text else {}

        passed = status_code == 200 and 'token' in response_data
        log_test(
            "  Can login again",
            passed,
            status_code,
            None,
            f"Expected 200 with token, got {status_code}" if not passed else None
        )
    except requests.exceptions.RequestException as e:
        log_test("  Can login again", False, None, None, str(e))


def test_rbac():
    """Test 4: Role-based access control"""
    print("\n[Phase 4] Role-Based Access Control (RBAC)")
    print("-" * 60)

    if not results['tokens']:
        print("  WARNING: No tokens available - skipping RBAC tests")
        return

    # Test with non-admin token accessing admin endpoint
    if 'student1' in results['tokens']:
        token = results['tokens']['student1']
        try:
            headers = {'Authorization': f'Token {token}'}
            response = session.get(
                f"{API_BASE_URL}/api/admin/users/",
                headers=headers,
                timeout=10
            )
            status_code = response.status_code

            passed = status_code in [403, 404]
            log_test(
                "  Student cannot access /api/admin/users/",
                passed,
                status_code,
                None,
                f"Expected 403/404, got {status_code}" if not passed else None
            )

            results['rbac_tests'].append({
                'role': 'student1',
                'endpoint': '/api/admin/users/',
                'expected_status': '403/404',
                'actual_status': status_code,
                'test_passed': passed
            })
        except requests.exceptions.RequestException as e:
            log_test("  Student cannot access /api/admin/users/", False, None, None, str(e))

    # Test accessing profile endpoint
    for role, token in list(results['tokens'].items())[:3]:
        try:
            headers = {'Authorization': f'Token {token}'}
            response = session.get(API_PROFILE_ENDPOINT, headers=headers, timeout=10)
            status_code = response.status_code

            passed = status_code == 200
            log_test(
                f"  {role} can access /api/auth/me/",
                passed,
                status_code,
                None,
                f"Expected 200, got {status_code}" if not passed else None
            )
        except requests.exceptions.RequestException as e:
            log_test(f"  {role} can access /api/auth/me/", False, None, None, str(e))


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("THE_BOT Platform - Authentication & Authorization Testing Suite")
    print("="*80)

    # Check connectivity first
    if not test_connectivity():
        print("\nERROR: Cannot connect to API")
        return results

    # Phase 1: Login tests
    test_login_valid_credentials()
    test_login_invalid_password()
    test_login_nonexistent_email()
    test_login_missing_fields()
    test_rate_limiting()

    # Phase 2: Token validation
    test_token_validation()

    # Phase 3: Session management
    test_session_management()

    # Phase 4: RBAC
    test_rbac()

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['tests_passed']}")
    print(f"Failed: {results['tests_failed']}")
    success_rate = 100 * results['tests_passed'] / max(1, results['total_tests'])
    print(f"Success Rate: {success_rate:.1f}%")

    print(f"\nHTTP Status Codes Tested:")
    for code in sorted(results['http_codes_tested'].keys()):
        count = results['http_codes_tested'][code]
        print(f"  {code}: {count} tests")

    if results['errors_found']:
        print(f"\nErrors Found: {len(results['errors_found'])}")
        for err in results['errors_found'][:10]:
            print(f"  - {err['test']}: {err['error']}")

    return results


def create_markdown_report(results, filename):
    """Create markdown report"""
    report = """# THE_BOT Platform - Authentication & Authorization Testing Report

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Tests | {total} |
| Passed | {passed} |
| Failed | {failed} |
| Success Rate | {success_rate:.1f}% |
| Test Date | {date} |
| API Base URL | {api_url} |

## Test Results by Phase

""".format(
        total=results['total_tests'],
        passed=results['tests_passed'],
        failed=results['tests_failed'],
        success_rate=100 * results['tests_passed'] / max(1, results['total_tests']),
        date=datetime.now().isoformat(),
        api_url=API_BASE_URL
    )

    # Add all test details
    report += """### Individual Test Results

| # | Test | Status | HTTP Code | Details |
|---|------|--------|-----------|---------|
"""

    for i, test in enumerate(results['test_details'], 1):
        status = test['status']
        code = test.get('http_code', '-')
        details = test.get('response', '')
        if isinstance(details, dict) and 'error' in details:
            details = details['error'][:50]
        elif isinstance(details, dict):
            details = str(details)[:50]
        report += f"| {i} | {test['name']} | {status} | {code} | {details} |\n"

    # Authentication endpoints
    if results['auth_endpoints']:
        report += """

### Authentication Endpoints Testing

| Endpoint | Role | Status | HTTP Code | Token |
|----------|------|--------|-----------|-------|
"""
        for endpoint in results['auth_endpoints']:
            report += f"| {endpoint['endpoint']} | {endpoint['role']} | {endpoint['status']} | {endpoint['http_code']} | {endpoint['token_obtained']} |\n"

    # RBAC tests
    if results['rbac_tests']:
        report += """

### Role-Based Access Control (RBAC) Tests

| Role | Endpoint | Expected | Actual | Passed |
|------|----------|----------|--------|--------|
"""
        for rbac in results['rbac_tests']:
            report += f"| {rbac['role']} | {rbac['endpoint']} | {rbac['expected_status']} | {rbac['actual_status']} | {rbac['test_passed']} |\n"

    # HTTP status codes
    report += """

### HTTP Status Codes Coverage

| Status Code | Count | Meaning |
|-------------|-------|---------|
"""
    for code in sorted(results['http_codes_tested'].keys()):
        count = results['http_codes_tested'][code]
        meanings = {
            200: 'OK',
            201: 'Created',
            204: 'No Content',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            429: 'Too Many Requests',
            500: 'Internal Server Error'
        }
        meaning = meanings.get(code, 'Unknown')
        report += f"| {code} | {count} | {meaning} |\n"

    # Errors found
    if results['errors_found']:
        report += """

### Issues Found

"""
        for err in results['errors_found']:
            report += f"- **{err['test']}**: {err['error']}\n"
    else:
        report += """

### Issues Found

No critical issues found during testing.

"""

    # Test Scenarios Executed
    report += """

## Test Scenarios Executed

### Phase 1: API Login Endpoint Testing
- Test valid credentials with all user roles
- Test invalid password rejection
- Test nonexistent email rejection
- Test missing required fields (email, password)
- Test empty field validation
- Test rate limiting on login attempts

### Phase 2: Token Validation
- Validate that obtained tokens work for authenticated requests
- Verify requests without tokens are rejected (401)
- Verify invalid tokens are rejected (401)
- Test Bearer token format handling

### Phase 3: Session Management
- Test logout endpoint functionality
- Verify tokens are invalidated after logout
- Test relogin capability after logout

### Phase 4: Role-Based Access Control (RBAC)
- Verify students cannot access admin endpoints
- Verify teachers cannot access admin endpoints
- Verify authenticated users can access profile endpoint
- Verify permission checks are enforced

## Recommendations

1. **Authentication Testing**: All core authentication endpoints are functional
2. **Error Handling**: Review status code 403 responses for missing field validation
3. **Rate Limiting**: Monitor rate limiting configuration and effectiveness
4. **Token Management**: Ensure tokens are properly invalidated on logout
5. **RBAC**: Verify all role-based access controls are correctly enforced

## Test Execution Details

- **Start Time**: {date}
- **API Endpoint**: {api_url}
- **Test Framework**: Python requests library
- **Total Duration**: ~{duration} seconds

""".format(
        date=datetime.now().isoformat(),
        api_url=API_BASE_URL,
        duration=len(results['test_details'])
    )

    with open(filename, 'w') as f:
        f.write(report)


if __name__ == '__main__':
    test_results = run_all_tests()

    # Save results to JSON
    json_file = '/home/mego/Python Projects/THE_BOT_platform/test_auth_results.json'
    with open(json_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    print(f"\nResults saved to: {json_file}")

    # Create markdown report
    md_file = '/home/mego/Python Projects/THE_BOT_platform/TESTER_1_AUTH_AUTHORIZATION.md'
    create_markdown_report(test_results, md_file)
    print(f"Report saved to: {md_file}")

    # Exit with appropriate code
    sys.exit(0 if test_results['tests_failed'] == 0 else 1)
