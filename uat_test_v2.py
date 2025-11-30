#!/usr/bin/env python3
"""
User Acceptance Testing (UAT) for THE BOT Platform - Version 2
Tests critical user flows with improved debugging
"""

import asyncio
from playwright.async_api import async_playwright
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

BASE_URL = "http://127.0.0.1:8081"  # Port 8081 if 8080 is busy
SCREENSHOTS_DIR = "/tmp/uat-screenshots"
TIMEOUT = 15000  # 15 seconds

# Ensure screenshots directory exists
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Test credentials
TEST_USERS = {
    "student": ("student@test.com", "TestPass123!"),
    "teacher": ("teacher@test.com", "TestPass123!"),
    "tutor": ("tutor@test.com", "TestPass123!"),
    "admin": ("admin@test.com", "TestPass123!"),
}

class TestResult:
    def __init__(self, scenario: str):
        self.scenario = scenario
        self.status = "PENDING"
        self.details = ""
        self.errors: List[str] = []
        self.screenshot = None
        self.start_time = datetime.now()

    def pass_test(self, details: str = ""):
        self.status = "PASS"
        self.details = details
        print(f"✓ PASS: {self.scenario}")

    def fail_test(self, error: str):
        self.status = "FAIL"
        self.details = error
        print(f"✗ FAIL: {self.scenario} - {error}")

    def block_test(self, reason: str):
        self.status = "BLOCK"
        self.details = reason
        print(f"⏸ BLOCK: {self.scenario} - {reason}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "status": self.status,
            "details": self.details,
            "errors": self.errors if self.errors else None,
            "screenshot": self.screenshot,
            "duration_ms": int((datetime.now() - self.start_time).total_seconds() * 1000),
        }


async def login_user_improved(page, email: str, password: str) -> bool:
    """Login a user with better error handling and debugging"""
    try:
        # Navigate to base URL
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        print(f"  Logging in as {email}...")

        # First, check if we need to click "Sign In" button on landing page
        sign_in_buttons = page.locator('button:has-text("Войти"), button:has-text("Sign In"), button:has-text("sign in")')
        if await sign_in_buttons.count() > 0:
            # We're on the landing page, need to click Sign In
            print(f"  Clicking Sign In button on landing page...")
            await sign_in_buttons.first.click()
            await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        # Get page content for debugging
        content = await page.content()

        # Try to find email input with multiple strategies
        email_locator = page.locator('input[type="email"]')
        if await email_locator.count() == 0:
            email_locator = page.locator('input[name="email"]')
        if await email_locator.count() == 0:
            email_locator = page.locator('input[placeholder*="email"], input[placeholder*="Email"]')

        # Check if email input was found
        email_input_count = await email_locator.count()
        if email_input_count == 0:
            print(f"  ✗ Email input not found. Page length: {len(content)}")
            # Save screenshot for debugging
            await page.screenshot(path=f"{SCREENSHOTS_DIR}/login_failed_{email}.png")
            return False

        # Fill email and password
        await email_locator.first.fill(email)

        password_locator = page.locator('input[type="password"]')
        if await password_locator.count() == 0:
            password_locator = page.locator('input[name="password"]')

        if await password_locator.count() > 0:
            await password_locator.first.fill(password)
        else:
            print(f"  ✗ Password input not found")
            return False

        # Find and click sign in button
        sign_in_locator = page.locator('button:has-text("Sign In"), button:has-text("sign in"), button:has-text("Войти")')
        if await sign_in_locator.count() > 0:
            await sign_in_locator.first.click()
            print(f"  ✓ Sign in button clicked")
        else:
            # Try any button with "submit"
            submit_btn_locator = page.locator('button[type="submit"]')
            if await submit_btn_locator.count() > 0:
                await submit_btn_locator.first.click()
                print(f"  ✓ Submit button clicked")
            else:
                print(f"  ✗ Sign in button not found")
                return False

        # Wait for either dashboard or error
        try:
            await page.wait_for_url("**/dashboard/**", timeout=8000)
            print(f"  ✓ Logged in successfully")
            return True
        except:
            # Check if we're still on login page or got redirected to error
            current_url = page.url()
            print(f"  ✗ Login redirect failed. Current URL: {current_url}")

            # Check for error messages
            try:
                error_text = await page.inner_text("body")
                if "error" in error_text.lower() or "invalid" in error_text.lower():
                    print(f"  Error detected: {error_text[:100]}")
            except:
                pass

            return False

    except Exception as e:
        print(f"  ✗ Login exception: {str(e)}")
        return False


async def test_login_form_exists(browser) -> TestResult:
    """Test 1: Verify login form exists and is accessible"""
    result = TestResult("Login Form - Exists and Is Accessible")

    try:
        page = await browser.new_page()

        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        # Check for email and password inputs
        email_input = page.locator('input[type="email"], input[name="email"]').first
        password_input = page.locator('input[type="password"], input[name="password"]').first

        if await email_input.count() > 0 and await password_input.count() > 0:
            result.pass_test("Login form with email and password inputs found")
        else:
            result.fail_test(f"Login form not found (email: {await email_input.count()}, pwd: {await password_input.count()})")

        await page.close()
    except Exception as e:
        result.fail_test(str(e))

    return result


async def test_student_dashboard_simple(browser) -> TestResult:
    """Test 2: Student can login and access dashboard"""
    result = TestResult("Student Dashboard - Login and Load")

    try:
        page = await browser.new_page()

        if await login_user_improved(page, TEST_USERS["student"][0], TEST_USERS["student"][1]):
            # Verify dashboard page
            url = page.url()
            if "/dashboard" in url:
                # Get page title or heading
                title = await page.title()
                result.pass_test(f"Student logged in and dashboard loaded (URL: {url})")
            else:
                result.fail_test(f"Login succeeded but wrong page: {url}")
        else:
            result.fail_test("Student login failed")

        await page.close()
    except Exception as e:
        result.fail_test(str(e))

    return result


async def test_student_profile_navigation(browser) -> TestResult:
    """Test 3: Student can access profile page"""
    result = TestResult("Student - Access Profile Page (/profile/student)")

    try:
        page = await browser.new_page()

        # First login
        if not await login_user_improved(page, TEST_USERS["student"][0], TEST_USERS["student"][1]):
            result.fail_test("Login failed")
            await page.close()
            return result

        # Navigate directly to profile page
        await page.goto(f"{BASE_URL}/profile/student")
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        # Check if we're on the profile page (not redirected to auth)
        url = page.url()
        if "/profile/student" in url:
            result.pass_test(f"Student profile page accessible")
        else:
            # Take screenshot for debugging
            await page.screenshot(path=f"{SCREENSHOTS_DIR}/student_profile_fail.png")
            result.fail_test(f"Expected /profile/student, got {url}")

        await page.close()
    except Exception as e:
        result.fail_test(str(e))

    return result


async def test_teacher_dashboard_simple(browser) -> TestResult:
    """Test 4: Teacher can login and access dashboard"""
    result = TestResult("Teacher Dashboard - Login and Load")

    try:
        page = await browser.new_page()

        if await login_user_improved(page, TEST_USERS["teacher"][0], TEST_USERS["teacher"][1]):
            url = page.url()
            if "/dashboard" in url:
                result.pass_test(f"Teacher logged in and dashboard loaded")
            else:
                result.fail_test(f"Login succeeded but wrong page: {url}")
        else:
            result.fail_test("Teacher login failed")

        await page.close()
    except Exception as e:
        result.fail_test(str(e))

    return result


async def test_teacher_profile_navigation(browser) -> TestResult:
    """Test 5: Teacher can access profile page"""
    result = TestResult("Teacher - Access Profile Page (/profile/teacher)")

    try:
        page = await browser.new_page()

        # First login
        if not await login_user_improved(page, TEST_USERS["teacher"][0], TEST_USERS["teacher"][1]):
            result.fail_test("Login failed")
            await page.close()
            return result

        # Navigate directly to profile page
        await page.goto(f"{BASE_URL}/profile/teacher")
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        # Check if we're on the profile page (not redirected to auth)
        url = page.url()
        if "/profile/teacher" in url:
            result.pass_test(f"Teacher profile page accessible")
        else:
            await page.screenshot(path=f"{SCREENSHOTS_DIR}/teacher_profile_fail.png")
            result.fail_test(f"Expected /profile/teacher, got {url}")

        await page.close()
    except Exception as e:
        result.fail_test(str(e))

    return result


async def test_tutor_dashboard_simple(browser) -> TestResult:
    """Test 6: Tutor can login and access dashboard"""
    result = TestResult("Tutor Dashboard - Login and Load")

    try:
        page = await browser.new_page()

        if await login_user_improved(page, TEST_USERS["tutor"][0], TEST_USERS["tutor"][1]):
            url = page.url()
            if "/dashboard" in url:
                result.pass_test(f"Tutor logged in and dashboard loaded")
            else:
                result.fail_test(f"Login succeeded but wrong page: {url}")
        else:
            result.fail_test("Tutor login failed")

        await page.close()
    except Exception as e:
        result.fail_test(str(e))

    return result


async def test_tutor_profile_navigation(browser) -> TestResult:
    """Test 7: Tutor can access profile page"""
    result = TestResult("Tutor - Access Profile Page (/profile/tutor)")

    try:
        page = await browser.new_page()

        # First login
        if not await login_user_improved(page, TEST_USERS["tutor"][0], TEST_USERS["tutor"][1]):
            result.fail_test("Login failed")
            await page.close()
            return result

        # Navigate directly to profile page
        await page.goto(f"{BASE_URL}/profile/tutor")
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

        # Check if we're on the profile page (not redirected to auth)
        url = page.url()
        if "/profile/tutor" in url:
            result.pass_test(f"Tutor profile page accessible")
        else:
            await page.screenshot(path=f"{SCREENSHOTS_DIR}/tutor_profile_fail.png")
            result.fail_test(f"Expected /profile/tutor, got {url}")

        await page.close()
    except Exception as e:
        result.fail_test(str(e))

    return result


async def test_admin_dashboard_access(browser) -> TestResult:
    """Test 8: Admin can access admin panel"""
    result = TestResult("Admin Panel - Access and Load")

    try:
        page = await browser.new_page()

        if await login_user_improved(page, TEST_USERS["admin"][0], TEST_USERS["admin"][1]):
            # Try to navigate to admin
            await page.goto(f"{BASE_URL}/admin/students")
            await page.wait_for_load_state("networkidle", timeout=TIMEOUT)

            url = page.url()
            if "/admin" in url:
                result.pass_test(f"Admin panel accessible")
            else:
                result.fail_test(f"Expected /admin path, got {url}")
        else:
            result.fail_test("Admin login failed")

        await page.close()
    except Exception as e:
        result.fail_test(str(e))

    return result


async def run_all_tests():
    """Run all UAT tests"""
    print("🚀 Starting User Acceptance Testing v2 for THE BOT Platform")
    print(f"📍 Base URL: {BASE_URL}")
    print(f"⏰ Started: {datetime.now().isoformat()}")
    print("=" * 80)

    # Clear proxy environment variables to allow localhost connections
    import os
    for var in ['http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
        os.environ.pop(var, None)

    results: List[TestResult] = []

    async with async_playwright() as p:
        # Launch browser with no-proxy for localhost
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-proxy-server']
        )

        # Run tests
        print("\n▶ Running tests...")
        results.append(await test_login_form_exists(browser))
        results.append(await test_student_dashboard_simple(browser))
        results.append(await test_student_profile_navigation(browser))
        results.append(await test_teacher_dashboard_simple(browser))
        results.append(await test_teacher_profile_navigation(browser))
        results.append(await test_tutor_dashboard_simple(browser))
        results.append(await test_tutor_profile_navigation(browser))
        results.append(await test_admin_dashboard_access(browser))

        await browser.close()

    # Generate report
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)

    passed = len([r for r in results if r.status == "PASS"])
    failed = len([r for r in results if r.status == "FAIL"])
    blocked = len([r for r in results if r.status == "BLOCK"])
    total = len(results)

    print(f"\n✓ Passed:  {passed}/{total}")
    print(f"✗ Failed:  {failed}/{total}")
    print(f"⏸ Blocked: {blocked}/{total}")

    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for result in results:
            if result.status == "FAIL":
                print(f"  • {result.scenario}")
                print(f"    Details: {result.details}")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
        },
        "results": [r.to_dict() for r in results],
    }

    report_path = "/home/mego/Python Projects/THE_BOT_platform/USER_ACCEPTANCE_TEST_FINAL.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📄 Full report saved: {report_path}")
    print(f"🖼️  Screenshots saved: {SCREENSHOTS_DIR}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
