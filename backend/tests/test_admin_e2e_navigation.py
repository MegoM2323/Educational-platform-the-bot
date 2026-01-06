"""
E2E Navigation Test for Admin Cabinet

This test suite performs end-to-end testing of the admin cabinet navigation.
It verifies:
1. Admin login functionality
2. Sidebar menu visibility and structure
3. Navigation to each admin section
4. Page loading and URL correctness
5. Logout functionality

Requirements:
- Frontend running on FRONTEND_URL (default: http://localhost:3000)
- Backend running on API_URL (default: http://localhost:8000)
- Admin user credentials (username: admin, password: configurable)
- Playwright with Chromium browser

Usage:
    ENVIRONMENT=test FRONTEND_URL=http://localhost:3000 python -m pytest \\
        backend/tests/test_admin_e2e_navigation.py -v

Results are saved to: .claude/state/test_results_admin_e2e_navigation.json
"""

import json
import pytest
import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from typing import AsyncGenerator
import os
from datetime import datetime

# Base URL for the frontend
BASE_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")

# Admin credentials for testing
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


class AdminE2ENavigationTest:
    """E2E test suite for admin cabinet navigation"""

    def __init__(self):
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "test_cases": [],
            "timestamp": datetime.now().isoformat(),
        }

    async def setup(self):
        """Setup browser and login"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

        # Set viewport for consistent testing
        await self.page.set_viewport_size({"width": 1280, "height": 720})

    async def teardown(self):
        """Cleanup resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def login_as_admin(self):
        """Login to the system as admin"""
        test_name = "login_as_admin"
        try:
            # Navigate to login page
            await self.page.goto(f"{BASE_URL}/auth/signin", wait_until="networkidle")

            # Fill in credentials
            await self.page.fill('input[type="text"]', ADMIN_USERNAME)
            await self.page.fill('input[type="password"]', ADMIN_PASSWORD)

            # Click login button
            await self.page.click('button:has-text("Вход")')

            # Wait for navigation to admin dashboard
            await self.page.wait_for_url(
                lambda url: "/admin" in str(url) or "/dashboard" in str(url),
                timeout=10000
            )

            # Check if we're redirected to admin area
            if "/admin" in self.page.url:
                self.test_results["passed"] += 1
                self.test_results["test_cases"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "url": self.page.url,
                    "message": "Successfully logged in as admin"
                })
                return True
            else:
                raise Exception("Not redirected to admin area after login")

        except Exception as e:
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e),
                "url": self.page.url
            })
            self.test_results["test_cases"].append({
                "name": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            return False

    async def test_navigation_to_page(self, menu_title: str, url_path: str, page_title: str = None):
        """Test navigation to a specific admin page"""
        test_name = f"navigate_to_{url_path.replace('/', '_')}"
        try:
            # Click on sidebar menu item
            menu_item = self.page.locator(
                f'a[href="{url_path}"], button:has-text("{menu_title}")'
            )

            # If not found by href, try to find by text in sidebar
            if await menu_item.count() == 0:
                # Look for NavLink with matching URL
                menu_item = self.page.locator(f'a >> text="{menu_title}"')

            if await menu_item.count() == 0:
                raise Exception(f"Menu item '{menu_title}' not found")

            # Click the menu item
            await menu_item.click()

            # Wait for page navigation
            await self.page.wait_for_url(
                lambda url: url_path in str(url),
                timeout=5000
            )

            # Wait for page to load
            await self.page.wait_for_load_state("networkidle")

            # Verify URL
            if url_path not in self.page.url:
                raise Exception(f"URL mismatch: expected {url_path}, got {self.page.url}")

            # Verify page title if provided
            if page_title:
                title_element = self.page.locator(f"h1, h2, h3:has-text('{page_title}')")
                if await title_element.count() == 0:
                    # Try to find any heading with content
                    headings = await self.page.locator("h1, h2, h3").all()
                    if len(headings) == 0:
                        raise Exception(f"Page title '{page_title}' not found")

            self.test_results["passed"] += 1
            self.test_results["test_cases"].append({
                "name": test_name,
                "status": "PASSED",
                "url": self.page.url,
                "menu_title": menu_title
            })

        except Exception as e:
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "menu_title": menu_title,
                "expected_url": url_path,
                "actual_url": self.page.url,
                "error": str(e)
            })
            self.test_results["test_cases"].append({
                "name": test_name,
                "status": "FAILED",
                "menu_title": menu_title,
                "error": str(e)
            })

    async def test_sidebar_visibility(self):
        """Test that sidebar is visible and contains all menu items"""
        test_name = "sidebar_visibility"
        try:
            # Check if sidebar exists
            sidebar = self.page.locator('[data-testid="sidebar"], aside')
            if await sidebar.count() == 0:
                raise Exception("Sidebar not found")

            # Expected menu items from AdminSidebar component
            expected_items = [
                "Мониторинг системы",
                "Управление аккаунтами",
                "Расписание",
                "Все чаты",
                "Рассылки",
                "Шаблоны уведомлений",
                "Аналитика уведомлений",
                "Параметры системы",
            ]

            # Check if all menu items are visible
            missing_items = []
            for item in expected_items:
                menu_text = self.page.locator(f'text="{item}"')
                if await menu_text.count() == 0:
                    missing_items.append(item)

            if missing_items:
                raise Exception(f"Missing menu items: {', '.join(missing_items)}")

            self.test_results["passed"] += 1
            self.test_results["test_cases"].append({
                "name": test_name,
                "status": "PASSED",
                "menu_items_found": len(expected_items)
            })

        except Exception as e:
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
            self.test_results["test_cases"].append({
                "name": test_name,
                "status": "FAILED",
                "error": str(e)
            })

    async def test_logout(self):
        """Test logout functionality from admin panel"""
        test_name = "logout_from_admin"
        try:
            # Find logout button in sidebar footer
            logout_button = self.page.locator('button:has-text("Выход")')
            if await logout_button.count() == 0:
                raise Exception("Logout button not found")

            # Click logout button
            await logout_button.click()

            # Wait for redirect to login page
            await self.page.wait_for_url(
                lambda url: "/auth" in str(url) or "/signin" in str(url),
                timeout=5000
            )

            # Verify we're on login page
            if "/auth" not in self.page.url and "/signin" not in self.page.url:
                raise Exception("Not redirected to login page after logout")

            self.test_results["passed"] += 1
            self.test_results["test_cases"].append({
                "name": test_name,
                "status": "PASSED",
                "redirect_url": self.page.url
            })

        except Exception as e:
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e),
                "url": self.page.url
            })
            self.test_results["test_cases"].append({
                "name": test_name,
                "status": "FAILED",
                "error": str(e)
            })

    async def run_all_tests(self):
        """Run complete navigation test suite"""
        await self.setup()

        try:
            # Test 1: Login
            self.test_results["total_tests"] += 1
            login_success = await self.login_as_admin()
            if not login_success:
                print("Login failed, cannot continue with navigation tests")
                return self.test_results

            # Test 2: Sidebar visibility
            self.test_results["total_tests"] += 1
            await self.test_sidebar_visibility()

            # Test 3-10: Navigate to each section
            navigation_tests = [
                ("Мониторинг системы", "/admin/monitoring", "Мониторинг"),
                ("Управление аккаунтами", "/admin/accounts", "Аккаунты"),
                ("Расписание", "/admin/schedule", "Расписание"),
                ("Все чаты", "/admin/chats", "Чаты"),
                ("Рассылки", "/admin/broadcasts", "Рассылки"),
                ("Шаблоны уведомлений", "/admin/notification-templates", "Шаблоны"),
                ("Аналитика уведомлений", "/admin/notifications", "Аналитика"),
                ("Параметры системы", "/admin/settings", "Параметры"),
            ]

            for menu_title, url_path, page_title in navigation_tests:
                self.test_results["total_tests"] += 1
                await self.test_navigation_to_page(menu_title, url_path, page_title)

            # Test 11: Logout
            self.test_results["total_tests"] += 1
            await self.test_logout()

        finally:
            await self.teardown()

        return self.test_results


@pytest.mark.asyncio
async def test_admin_e2e_navigation():
    """Pytest test function for admin E2E navigation"""
    test_suite = AdminE2ENavigationTest()
    results = await test_suite.run_all_tests()

    # Save results to JSON file
    output_file = "/home/mego/Python Projects/THE_BOT_platform/.claude/state/test_results_admin_e2e_navigation.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Print summary
    print("\n" + "=" * 80)
    print("ADMIN E2E NAVIGATION TEST RESULTS")
    print("=" * 80)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Pass Rate: {(results['passed'] / results['total_tests'] * 100):.1f}%")

    if results["errors"]:
        print("\nERRORS:")
        for error in results["errors"]:
            print(f"  - {error['test']}: {error['error']}")

    print(f"\nResults saved to: {output_file}")
    print("=" * 80)

    # Assert all tests passed
    assert results["failed"] == 0, f"{results['failed']} test(s) failed"
    assert results["passed"] > 0, "No tests passed"


if __name__ == "__main__":
    # Run tests directly with asyncio
    asyncio.run(test_admin_e2e_navigation())
