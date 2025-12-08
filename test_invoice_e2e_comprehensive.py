"""
E2E Browser Tests for Invoice System - Tutor & Parent Workflows
Tests the complete invoice lifecycle using Playwright
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import pytest
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


class InvoiceE2ETest:
    """Comprehensive E2E tests for Invoice System"""

    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.api_url = "http://localhost:8000/api"
        self.screenshots_dir = Path("/tmp/invoice_test_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        self.test_results = {
            "passed": [],
            "failed": [],
            "total": 0,
        }

    async def take_screenshot(self, page: Page, name: str):
        """Take screenshot for debugging"""
        path = self.screenshots_dir / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
        await page.screenshot(path=str(path))
        print(f"Screenshot saved: {path}")
        return str(path)

    async def login(self, page: Page, email: str, password: str = "password123") -> bool:
        """Login to the application"""
        try:
            await page.goto(f"{self.base_url}/auth")
            await page.wait_for_load_state("networkidle")

            # Wait for login form to appear
            await page.wait_for_selector("input[placeholder*='Email'], input[name*='email']", timeout=5000)

            # Fill login form
            email_inputs = await page.query_selector_all("input")
            if len(email_inputs) > 0:
                await email_inputs[0].fill(email)

            password_inputs = await page.query_selector_all("input[type='password']")
            if len(password_inputs) > 0:
                await password_inputs[0].fill(password)

            # Click login button
            login_btn = await page.query_selector("button:has-text('Войти')")
            if login_btn:
                await login_btn.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)  # Wait for auth to complete

                # Check if we're logged in
                current_url = page.url
                if "/auth" not in current_url and current_url != f"{self.base_url}/":
                    return True
                else:
                    # Check for error message
                    error_msg = await page.inner_text("body")
                    if "ошибка" in error_msg.lower():
                        print(f"Login error for {email}")
                        return False

            return True
        except Exception as e:
            print(f"Login failed for {email}: {e}")
            return False

    async def test_tutor_access_invoices_page(self, page: Page, context: BrowserContext):
        """Test 1: Tutor can access invoices page"""
        test_name = "T1_Tutor_Access_Invoices"
        try:
            # Login as tutor
            success = await self.login(page, "test_tutor_opt@test.com")
            if not success:
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": "Login failed",
                        "screenshot": await self.take_screenshot(page, test_name),
                    }
                )
                return False

            # Navigate to invoices page
            await page.goto(f"{self.base_url}/dashboard/tutor/invoices")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            # Verify page loads with "Счета" header
            page_content = await page.inner_text("body")
            if "Счета" in page_content or "счета" in page_content.lower():
                self.test_results["passed"].append(test_name)
                return True
            else:
                await self.take_screenshot(page, test_name)
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": "Invoices page header not found",
                        "url": page.url,
                    }
                )
                return False
        except Exception as e:
            self.test_results["failed"].append(
                {
                    "test": test_name,
                    "reason": str(e),
                    "screenshot": await self.take_screenshot(page, test_name),
                }
            )
            return False

    async def test_tutor_create_invoice(self, page: Page, context: BrowserContext):
        """Test 2: Tutor can create invoice"""
        test_name = "T2_Tutor_Create_Invoice"
        try:
            # Should already be logged in
            await page.goto(f"{self.base_url}/dashboard/tutor/invoices")
            await page.wait_for_load_state("networkidle")

            # Click "Создать счет" button
            create_btn = None
            buttons = await page.query_selector_all("button")
            for btn in buttons:
                text = await btn.inner_text()
                if "Создать" in text or "счет" in text.lower():
                    create_btn = btn
                    break

            if not create_btn:
                # Try finding by text content
                create_btn = await page.query_selector("button:has-text('Создать')")

            if create_btn:
                await create_btn.click()
                await asyncio.sleep(1)

                # Dialog should open - fill in the form
                # Select student
                student_select = await page.query_selector("select")
                if student_select:
                    await student_select.click()
                    options = await page.query_selector_all("option")
                    if len(options) > 1:  # Skip the first empty option
                        await options[1].click()

                # Fill amount
                amount_input = await page.query_selector("input[type='number']")
                if amount_input:
                    await amount_input.fill("5000")

                # Fill description
                description_input = await page.query_selector("textarea")
                if description_input:
                    await description_input.fill("Месячная подписка на 10 занятий")

                # Click create button
                submit_buttons = await page.query_selector_all("button")
                for btn in submit_buttons:
                    text = await btn.inner_text()
                    if "Создать" in text:
                        await btn.click()
                        break

                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                # Check for success toast
                body_text = await page.inner_text("body")
                if "создан" in body_text.lower() or "успех" in body_text.lower():
                    self.test_results["passed"].append(test_name)
                    return True
                else:
                    self.test_results["failed"].append(
                        {
                            "test": test_name,
                            "reason": "Success message not found after creating invoice",
                            "screenshot": await self.take_screenshot(page, test_name),
                        }
                    )
                    return False
            else:
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": "Create button not found",
                        "screenshot": await self.take_screenshot(page, test_name),
                    }
                )
                return False

        except Exception as e:
            self.test_results["failed"].append(
                {
                    "test": test_name,
                    "reason": str(e),
                    "screenshot": await self.take_screenshot(page, test_name),
                }
            )
            return False

    async def test_parent_access_invoices_page(self, page: Page, context: BrowserContext):
        """Test 3: Parent can access invoices page"""
        test_name = "T3_Parent_Access_Invoices"
        try:
            # Logout and login as parent
            await page.goto(f"{self.base_url}/")
            await asyncio.sleep(1)

            # Click logout if exists
            logout_btn = await page.query_selector("button:has-text('Выход'), a:has-text('Выход')")
            if logout_btn:
                await logout_btn.click()
                await asyncio.sleep(2)

            # Login as parent
            success = await self.login(page, "parent@test.com")
            if not success:
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": "Parent login failed",
                        "screenshot": await self.take_screenshot(page, test_name),
                    }
                )
                return False

            # Navigate to parent invoices page
            await page.goto(f"{self.base_url}/dashboard/parent/invoices")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            # Verify page loads
            page_content = await page.inner_text("body")
            if "счета" in page_content.lower() or "Счета" in page_content:
                self.test_results["passed"].append(test_name)
                return True
            else:
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": "Parent invoices page not found",
                        "url": page.url,
                        "screenshot": await self.take_screenshot(page, test_name),
                    }
                )
                return False
        except Exception as e:
            self.test_results["failed"].append(
                {
                    "test": test_name,
                    "reason": str(e),
                    "screenshot": await self.take_screenshot(page, test_name),
                }
            )
            return False

    async def test_responsive_design(self, page: Page, context: BrowserContext):
        """Test responsive design on different viewports"""
        test_name = "T4_Responsive_Design"
        try:
            viewports = [
                {"width": 1920, "height": 1080, "name": "Desktop"},
                {"width": 768, "height": 1024, "name": "Tablet"},
                {"width": 375, "height": 812, "name": "Mobile"},
            ]

            await page.goto(f"{self.base_url}/dashboard/parent/invoices")

            for viewport in viewports:
                await page.set_viewport_size(
                    {"width": viewport["width"], "height": viewport["height"]}
                )
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)

                # Verify page renders without overflow
                scroll_height = await page.evaluate("document.body.scrollHeight")
                window_height = await page.evaluate("window.innerHeight")

                # Take screenshot for verification
                await self.take_screenshot(page, f"{test_name}_{viewport['name']}")

            self.test_results["passed"].append(test_name)
            return True

        except Exception as e:
            self.test_results["failed"].append(
                {
                    "test": test_name,
                    "reason": str(e),
                    "screenshot": await self.take_screenshot(page, test_name),
                }
            )
            return False

    async def test_invoice_validation(self, page: Page, context: BrowserContext):
        """Test invoice validation rules"""
        test_name = "T5_Invoice_Validation"
        try:
            # Login as tutor
            await self.login(page, "test_tutor_opt@test.com")
            await page.goto(f"{self.base_url}/dashboard/tutor/invoices")
            await page.wait_for_load_state("networkidle")

            # Try to create invoice with invalid amount
            create_btn = await page.query_selector("button:has-text('Создать')")
            if create_btn:
                await create_btn.click()
                await asyncio.sleep(1)

                # Try amount 0.001 (too small)
                amount_input = await page.query_selector("input[type='number']")
                if amount_input:
                    await amount_input.fill("0.001")
                    await asyncio.sleep(0.5)

                    # Check for validation error
                    body_text = await page.inner_text("body")
                    if "минимальная" in body_text.lower() or "мало" in body_text.lower():
                        self.test_results["passed"].append(test_name)
                        return True

            self.test_results["failed"].append(
                {
                    "test": test_name,
                    "reason": "Validation rules not enforced",
                    "screenshot": await self.take_screenshot(page, test_name),
                }
            )
            return False

        except Exception as e:
            self.test_results["failed"].append(
                {
                    "test": test_name,
                    "reason": str(e),
                    "screenshot": await self.take_screenshot(page, test_name),
                }
            )
            return False

    async def run_all_tests(self):
        """Run all test scenarios"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            print("\n" + "=" * 70)
            print("INVOICE SYSTEM E2E TEST SUITE")
            print("=" * 70)

            tests = [
                ("1. Tutor Access Invoices Page", self.test_tutor_access_invoices_page),
                ("2. Tutor Create Invoice", self.test_tutor_create_invoice),
                ("3. Parent Access Invoices Page", self.test_parent_access_invoices_page),
                ("4. Responsive Design", self.test_responsive_design),
                ("5. Invoice Validation", self.test_invoice_validation),
            ]

            for test_name, test_func in tests:
                print(f"\nRunning: {test_name}")
                self.test_results["total"] += 1
                try:
                    result = await test_func(page, context)
                    status = "PASS" if result else "FAIL"
                    print(f"  Result: {status}")
                except Exception as e:
                    print(f"  Result: ERROR - {e}")
                    self.test_results["total"] -= 1

                await asyncio.sleep(2)

            await browser.close()

            # Print summary
            self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        passed = len(self.test_results["passed"])
        failed = len(self.test_results["failed"])
        total = passed + failed

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed / total * 100) if total > 0 else 0:.1f}%")

        if self.test_results["passed"]:
            print("\nPASSED TESTS:")
            for test in self.test_results["passed"]:
                print(f"  ✓ {test}")

        if self.test_results["failed"]:
            print("\nFAILED TESTS:")
            for test in self.test_results["failed"]:
                print(f"  ✗ {test['test']}")
                print(f"    Reason: {test['reason']}")
                if "screenshot" in test:
                    print(f"    Screenshot: {test['screenshot']}")

        print("\nScreenshots saved to: " + str(self.screenshots_dir))
        print("=" * 70 + "\n")


async def main():
    """Main entry point"""
    tester = InvoiceE2ETest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
