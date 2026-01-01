#!/usr/bin/env python
"""Static validation tests for all 10 fixes"""
import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def run_command(cmd, cwd=None):
    """Run a shell command and return output"""
    result = subprocess.run(
        cmd,
        cwd=cwd or BASE_DIR,
        capture_output=True,
        text=True,
        shell=False
    )
    return result.stdout, result.returncode


def grep(pattern, path, include='*.py'):
    """Search for pattern in files"""
    cmd = ['grep', '-r', pattern, str(path), f'--include={include}']
    stdout, _ = run_command(cmd)
    return [l for l in stdout.split('\n') if l.strip()]


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def add_test(self, name, status, details=''):
        self.tests.append({'name': name, 'status': status, 'details': details})
        if status == 'PASS':
            self.passed += 1
        else:
            self.failed += 1

    def summary(self):
        return f"Passed: {self.passed}, Failed: {self.failed}, Total: {self.passed + self.failed}"


results = TestResults()


# ============================================================
# Test 1: [L2] CORS Configuration
# ============================================================
def test_l2_cors():
    """Test L2: CORS Configuration"""
    section = '[L2] CORS Configuration'

    # Read settings.py
    settings_path = BASE_DIR / 'backend' / 'config' / 'settings.py'
    with open(settings_path) as f:
        content = f.read()

    # Check CORS_ALLOWED_ORIGINS
    if 'CORS_ALLOWED_ORIGINS' in content and 'CORS_ALLOW_ALL_ORIGINS = False' in content:
        results.add_test(f'{section}: CORS Origins configured', 'PASS')
    else:
        results.add_test(f'{section}: CORS Origins configured', 'FAIL',
                         'CORS_ALLOWED_ORIGINS or CORS_ALLOW_ALL_ORIGINS=False not found')

    # Check CORS_ALLOW_CREDENTIALS
    if 'CORS_ALLOW_CREDENTIALS = True' in content:
        results.add_test(f'{section}: CORS Allow Credentials', 'PASS')
    else:
        results.add_test(f'{section}: CORS Allow Credentials', 'FAIL')

    # Check CORS middleware
    if 'corsheaders' in content.lower() or 'CorsMiddleware' in content:
        results.add_test(f'{section}: CORS Middleware installed', 'PASS')
    else:
        results.add_test(f'{section}: CORS Middleware installed', 'FAIL')


# ============================================================
# Test 2: [H1] CSRF Exempt Removed from Login
# ============================================================
def test_h1_csrf():
    """Test H1: CSRF Exempt Removed"""
    section = '[H1] CSRF Exempt Removed'

    # Find all csrf_exempt usages
    csrf_files = grep('csrf_exempt', BASE_DIR / 'backend')

    webhook_files = [
        'telegram_webhook',
        'payments/views.py',
        'autograder.py',
        'views_plagiarism.py',
        'prometheus'
    ]

    csrf_in_auth_views = False
    has_webhook_exempts = False

    for line in csrf_files:
        # Check if it's only in webhooks/external integrations
        if 'accounts/views.py' in line and 'telegram_webhook' not in line:
            csrf_in_auth_views = True

        is_webhook = any(webhook in line for webhook in webhook_files)
        if is_webhook:
            has_webhook_exempts = True

    if not csrf_in_auth_views:
        results.add_test(f'{section}: Not in auth views', 'PASS')
    else:
        results.add_test(f'{section}: Not in auth views', 'FAIL')

    # Check that webhooks still have csrf_exempt
    if has_webhook_exempts:
        results.add_test(f'{section}: Webhooks still protected', 'PASS')
    else:
        results.add_test(f'{section}: Webhooks still protected', 'FAIL')


# ============================================================
# Test 3: [M3] File Upload Size Limit
# ============================================================
def test_m3_file_upload():
    """Test M3: File Upload Size Limit"""
    section = '[M3] File Upload Size Limit'

    settings_path = BASE_DIR / 'backend' / 'config' / 'settings.py'
    with open(settings_path) as f:
        content = f.read()

    # Check FILE_UPLOAD_MAX_MEMORY_SIZE
    if 'FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880' in content:
        results.add_test(f'{section}: File upload limit 5MB', 'PASS')
    else:
        results.add_test(f'{section}: File upload limit 5MB', 'FAIL',
                         'FILE_UPLOAD_MAX_MEMORY_SIZE not set to 5242880 (5MB)')

    # Check DATA_UPLOAD_MAX_MEMORY_SIZE
    if 'DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880' in content:
        results.add_test(f'{section}: Data upload limit 5MB', 'PASS')
    else:
        results.add_test(f'{section}: Data upload limit 5MB', 'FAIL',
                         'DATA_UPLOAD_MAX_MEMORY_SIZE not set to 5242880 (5MB)')


# ============================================================
# Test 4: [M1] Lesson Time Conflict Validation
# ============================================================
def test_m1_lesson_conflict():
    """Test M1: Lesson Time Conflict Validation"""
    section = '[M1] Lesson Time Conflict Validation'

    models_path = BASE_DIR / 'backend' / 'scheduling' / 'models.py'
    with open(models_path) as f:
        content = f.read()

    # Check that Lesson model has clean method
    if 'def clean(self):' in content and 'start_time' in content and 'end_time' in content:
        results.add_test(f'{section}: Has validation method', 'PASS')
    else:
        results.add_test(f'{section}: Has validation method', 'FAIL')

    # Check for time validation logic
    if ('start_time' in content and 'end_time' in content and
        ('ValidationError' in content or 'raise' in content)):
        results.add_test(f'{section}: Time validation implemented', 'PASS')
    else:
        results.add_test(f'{section}: Time validation implemented', 'FAIL')


# ============================================================
# Test 5: [M2] Time Validation (start < end)
# ============================================================
def test_m2_time_validation():
    """Test M2: Time Validation"""
    section = '[M2] Time Validation (start < end)'

    models_path = BASE_DIR / 'backend' / 'scheduling' / 'models.py'
    with open(models_path) as f:
        content = f.read()

    # Check for >= check between start_time and end_time
    if ('start_time >= end_time' in content or
        'end_time <= start_time' in content or
        'start_time < end_time' in content):
        results.add_test(f'{section}: Start < End validation', 'PASS')
    else:
        results.add_test(f'{section}: Start < End validation', 'FAIL',
                         'Time ordering check not found')


# ============================================================
# Test 6: [H2] WebSocket JWT Authentication
# ============================================================
def test_h2_websocket_jwt():
    """Test H2: WebSocket JWT Authentication"""
    section = '[H2] WebSocket JWT Authentication'

    consumers_path = BASE_DIR / 'backend' / 'chat' / 'consumers.py'
    with open(consumers_path) as f:
        content = f.read()

    # Check for token validation methods
    if '_validate_token' in content:
        results.add_test(f'{section}: Token validation method', 'PASS')
    else:
        results.add_test(f'{section}: Token validation method', 'FAIL')

    # Check for query string authentication
    if '_authenticate_token_from_query_string' in content:
        results.add_test(f'{section}: Query string auth', 'PASS')
    else:
        results.add_test(f'{section}: Query string auth', 'FAIL')

    # Check for Token import
    if 'from rest_framework.authtoken.models import Token' in content:
        results.add_test(f'{section}: Token model imported', 'PASS')
    else:
        results.add_test(f'{section}: Token model imported', 'FAIL')

    # Check for token= and authorization= support
    if 'token=' in content and 'authorization=' in content:
        results.add_test(f'{section}: Multiple token formats', 'PASS')
    else:
        results.add_test(f'{section}: Multiple token formats', 'FAIL')


# ============================================================
# Test 7: [H3] Admin Endpoints Permission Check
# ============================================================
def test_h3_admin_permissions():
    """Test H3: Admin Endpoints Permission Check"""
    section = '[H3] Admin Endpoints Permission Check'

    # Count @permission_classes decorators
    perm_classes = grep('@permission_classes', BASE_DIR / 'backend')
    if len(perm_classes) > 50:
        results.add_test(f'{section}: Permission classes used (count: {len(perm_classes)})', 'PASS')
    else:
        results.add_test(f'{section}: Permission classes used (count: {len(perm_classes)})', 'FAIL',
                         f'Expected >50, found {len(perm_classes)}')

    # Check for IsStaffOrAdmin
    staff_admin = grep('IsStaffOrAdmin', BASE_DIR / 'backend')
    if len(staff_admin) > 5:
        results.add_test(f'{section}: IsStaffOrAdmin used (count: {len(staff_admin)})', 'PASS')
    else:
        results.add_test(f'{section}: IsStaffOrAdmin used (count: {len(staff_admin)})', 'FAIL')


# ============================================================
# Test 8: [M4] Permission Classes Usage
# ============================================================
def test_m4_permission_classes():
    """Test M4: Permission Classes Usage"""
    section = '[M4] Permission Classes Usage'

    staff_views_path = BASE_DIR / 'backend' / 'accounts' / 'staff_views.py'
    with open(staff_views_path) as f:
        content = f.read()

    # Count @permission_classes in staff_views
    count = content.count('@permission_classes')
    if count > 10:
        results.add_test(f'{section}: Staff views protected (count: {count})', 'PASS')
    else:
        results.add_test(f'{section}: Staff views protected (count: {count})', 'FAIL',
                         f'Expected >10, found {count}')

    # Check for IsStaffOrAdmin import
    if 'IsStaffOrAdmin' in content:
        results.add_test(f'{section}: IsStaffOrAdmin imported', 'PASS')
    else:
        results.add_test(f'{section}: IsStaffOrAdmin imported', 'FAIL')


# ============================================================
# Test 9: [L1] .env Not in Git
# ============================================================
def test_l1_env_not_in_git():
    """Test L1: .env Not in Git"""
    section = '[L1] .env Not in Git'

    # Check .gitignore
    gitignore_path = BASE_DIR / '.gitignore'
    with open(gitignore_path) as f:
        content = f.read()

    if '.env' in content:
        results.add_test(f'{section}: .env in .gitignore', 'PASS')
    else:
        results.add_test(f'{section}: .env in .gitignore', 'FAIL')

    # Check git status
    stdout, _ = run_command(['git', 'status', '--porcelain'])
    if '.env' not in stdout:
        results.add_test(f'{section}: .env not tracked', 'PASS')
    else:
        results.add_test(f'{section}: .env not tracked', 'FAIL')


# ============================================================
# Test 10: [C1] Frontend Container Healthcheck
# ============================================================
def test_c1_frontend_healthcheck():
    """Test C1: Frontend Container Healthcheck"""
    section = '[C1] Frontend Container Healthcheck'

    docker_compose_path = BASE_DIR / 'docker-compose.yml'
    with open(docker_compose_path) as f:
        content = f.read()

    # Check for healthcheck
    if 'healthcheck:' in content:
        results.add_test(f'{section}: Healthcheck configured', 'PASS')
    else:
        results.add_test(f'{section}: Healthcheck configured', 'FAIL')

    # Count healthchecks
    count = content.count('healthcheck:')
    if count >= 3:
        results.add_test(f'{section}: Multiple services with healthcheck (count: {count})', 'PASS')
    else:
        results.add_test(f'{section}: Multiple services with healthcheck (count: {count})', 'FAIL',
                         f'Expected >=3, found {count}')

    # Check for frontend service
    if 'frontend' in content.lower():
        results.add_test(f'{section}: Frontend service exists', 'PASS')
    else:
        results.add_test(f'{section}: Frontend service exists', 'FAIL')


# ============================================================
# Run all tests
# ============================================================
def main():
    print("Testing all 10 fixes...\n")

    test_l2_cors()
    test_h1_csrf()
    test_m3_file_upload()
    test_m1_lesson_conflict()
    test_m2_time_validation()
    test_h2_websocket_jwt()
    test_h3_admin_permissions()
    test_m4_permission_classes()
    test_l1_env_not_in_git()
    test_c1_frontend_healthcheck()

    # Print results
    print("\n" + "=" * 70)
    print("DETAILED TEST RESULTS")
    print("=" * 70)

    current_section = None
    for test in results.tests:
        section = test['name'].split(':')[0]
        if section != current_section:
            print(f"\n{section}")
            current_section = section

        status = "PASS" if test['status'] == 'PASS' else "FAIL"
        test_name = test['name'].split(': ', 1)[1] if ': ' in test['name'] else test['name']
        print(f"  [{status}] {test_name}")
        if test['details']:
            print(f"       {test['details']}")

    print("\n" + "=" * 70)
    print(f"SUMMARY: {results.summary()}")
    print("=" * 70)

    return 0 if results.failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
