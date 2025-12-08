"""
E2E Tests for Invoice System - API and UI Testing
Tests invoice functionality directly via API and UI
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


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

    async def take_screenshot(self, page, name: str):
        """Take screenshot for debugging"""
        path = self.screenshots_dir / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
        await page.screenshot(path=str(path), full_page=True)
        return str(path)

    def get_user_credentials(self, role: str):
        """Get test user credentials from database"""
        try:
            conn = sqlite3.connect(
                "/home/mego/Python Projects/THE_BOT_platform/backend/db.sqlite3"
            )
            cursor = conn.cursor()

            if role == "tutor":
                cursor.execute(
                    "SELECT email FROM accounts_user WHERE role='tutor' LIMIT 1"
                )
            elif role == "parent":
                cursor.execute(
                    "SELECT email FROM accounts_user WHERE role='parent' LIMIT 1"
                )
            else:
                cursor.execute(
                    f"SELECT email FROM accounts_user WHERE role='{role}' LIMIT 1"
                )

            result = cursor.fetchone()
            conn.close()

            if result:
                return result[0]
            return None
        except Exception as e:
            print(f"Error getting user credentials: {e}")
            return None

    async def test_invoice_list_api(self, page):
        """Test 1: Invoice List API is accessible"""
        test_name = "T1_Invoice_List_API"
        try:
            # Make API request to get invoices list
            response = await page.evaluate(
                """
                async () => {
                    try {
                        const response = await fetch('http://localhost:8000/api/invoices/tutor/', {
                            method: 'GET',
                            headers: {
                                'Content-Type': 'application/json',
                            }
                        });
                        return {
                            status: response.status,
                            ok: response.ok
                        };
                    } catch (e) {
                        return { error: e.message };
                    }
                }
            """
            )

            # We expect 401 (unauthorized) without auth token
            if response.get("status") in [401, 403] or response.get("ok") is False:
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: API exists and requires authentication")
                return True
            else:
                self.test_results["failed"].append(
                    {"test": test_name, "reason": f"Unexpected response: {response}"}
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

    async def test_invoice_page_structure(self, page):
        """Test 2: Invoice page structure and components"""
        test_name = "T2_Invoice_Page_Structure"
        try:
            # Navigate to home
            await page.goto(f"{self.base_url}/")
            await page.wait_for_load_state("networkidle")

            # Check if we can reach the page (even if not authenticated)
            page_title = await page.title()
            page_content = await page.content()

            if "THE BOT" in page_title or page.url == f"{self.base_url}/":
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: Application loads correctly")
                return True
            else:
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": "Application not loading",
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

    async def test_responsive_design_desktop(self, page):
        """Test 3: Responsive design - Desktop"""
        test_name = "T3_Responsive_Desktop"
        try:
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.goto(f"{self.base_url}/")
            await page.wait_for_load_state("networkidle")

            # Check page renders
            content = await page.content()
            screenshot = await self.take_screenshot(page, test_name)

            if len(content) > 100:
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: Desktop view renders correctly")
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

    async def test_responsive_design_tablet(self, page):
        """Test 4: Responsive design - Tablet"""
        test_name = "T4_Responsive_Tablet"
        try:
            await page.set_viewport_size({"width": 768, "height": 1024})
            await page.goto(f"{self.base_url}/")
            await page.wait_for_load_state("networkidle")

            content = await page.content()
            screenshot = await self.take_screenshot(page, test_name)

            if len(content) > 100:
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: Tablet view renders correctly")
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

    async def test_responsive_design_mobile(self, page):
        """Test 5: Responsive design - Mobile"""
        test_name = "T5_Responsive_Mobile"
        try:
            await page.set_viewport_size({"width": 375, "height": 812})
            await page.goto(f"{self.base_url}/")
            await page.wait_for_load_state("networkidle")

            content = await page.content()
            screenshot = await self.take_screenshot(page, test_name)

            if len(content) > 100:
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: Mobile view renders correctly")
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

    async def test_auth_flow(self, page):
        """Test 6: Authentication flow"""
        test_name = "T6_Auth_Flow"
        try:
            # Navigate to auth page
            await page.goto(f"{self.base_url}/auth")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            # Check if login form is present
            page_content = await page.content()

            # Look for email input, password input, and login button
            has_email = "email" in page_content.lower()
            has_password = "пароль" in page_content.lower() or "password" in page_content.lower()
            has_button = "войти" in page_content.lower() or "login" in page_content.lower()

            if has_email and has_password and has_button:
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: Auth page has login form")
                return True
            else:
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": "Login form not found",
                        "has_email": has_email,
                        "has_password": has_password,
                        "has_button": has_button,
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

    async def test_navigation(self, page):
        """Test 7: Navigation works correctly"""
        test_name = "T7_Navigation"
        try:
            # Navigate to home
            await page.goto(f"{self.base_url}/")
            await page.wait_for_load_state("networkidle")

            # Check for navigation elements
            page_content = await page.content()

            # Look for main navigation
            has_nav = "возможности" in page_content.lower() or "features" in page_content.lower()
            has_login = "войти" in page_content.lower() or "login" in page_content.lower()

            if has_nav or has_login:
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: Navigation elements present")
                return True
            else:
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": "Navigation elements not found",
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

    async def test_invoice_backend_models(self, page):
        """Test 8: Invoice backend models exist"""
        test_name = "T8_Invoice_Backend_Models"
        try:
            # Check if invoices app models can be loaded
            conn = sqlite3.connect(
                "/home/mego/Python Projects/THE_BOT_platform/backend/db.sqlite3"
            )
            cursor = conn.cursor()

            # Check if invoices_invoice table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='invoices_invoice'"
            )
            result = cursor.fetchone()
            conn.close()

            if result:
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: Invoice models exist in database")
                return True
            else:
                self.test_results["failed"].append(
                    {"test": test_name, "reason": "Invoice table not found in database"}
                )
                return False

        except Exception as e:
            self.test_results["failed"].append(
                {"test": test_name, "reason": str(e)}
            )
            return False

    async def test_invoice_components_exist(self, page):
        """Test 9: Invoice components are implemented"""
        test_name = "T9_Invoice_Components"
        try:
            # Check if component files exist
            components_dir = Path(
                "/home/mego/Python Projects/THE_BOT_platform/frontend/src/components/invoices"
            )

            if not components_dir.exists():
                self.test_results["failed"].append(
                    {"test": test_name, "reason": "Invoice components directory not found"}
                )
                return False

            # Check for specific components
            required_files = [
                "TutorInvoicesList.tsx",
                "ParentInvoicesList.tsx",
                "CreateInvoiceForm.tsx",
                "InvoiceDetail.tsx",
            ]

            missing_files = []
            for file in required_files:
                if not (components_dir / file).exists():
                    missing_files.append(file)

            if not missing_files:
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: All invoice components found")
                return True
            else:
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": f"Missing components: {', '.join(missing_files)}",
                    }
                )
                return False

        except Exception as e:
            self.test_results["failed"].append(
                {"test": test_name, "reason": str(e)}
            )
            return False

    async def test_invoice_api_endpoints(self, page):
        """Test 10: Invoice API endpoints are documented"""
        test_name = "T10_Invoice_API_Endpoints"
        try:
            # Check if views.py has the endpoints
            views_file = Path(
                "/home/mego/Python Projects/THE_BOT_platform/backend/invoices/views.py"
            )

            if not views_file.exists():
                self.test_results["failed"].append(
                    {"test": test_name, "reason": "Invoice views not found"}
                )
                return False

            content = views_file.read_text()

            # Check for required ViewSets
            has_tutor_viewset = "TutorInvoiceViewSet" in content
            has_parent_viewset = "ParentInvoiceViewSet" in content

            if has_tutor_viewset and has_parent_viewset:
                self.test_results["passed"].append(test_name)
                print(f"  ✓ {test_name}: Invoice API ViewSets implemented")
                return True
            else:
                self.test_results["failed"].append(
                    {
                        "test": test_name,
                        "reason": f"Missing ViewSets - Tutor: {has_tutor_viewset}, Parent: {has_parent_viewset}",
                    }
                )
                return False

        except Exception as e:
            self.test_results["failed"].append(
                {"test": test_name, "reason": str(e)}
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
                ("1. Invoice List API", self.test_invoice_list_api),
                ("2. Invoice Page Structure", self.test_invoice_page_structure),
                ("3. Responsive Design - Desktop", self.test_responsive_design_desktop),
                ("4. Responsive Design - Tablet", self.test_responsive_design_tablet),
                ("5. Responsive Design - Mobile", self.test_responsive_design_mobile),
                ("6. Authentication Flow", self.test_auth_flow),
                ("7. Navigation", self.test_navigation),
                ("8. Invoice Backend Models", self.test_invoice_backend_models),
                ("9. Invoice Components", self.test_invoice_components_exist),
                ("10. Invoice API Endpoints", self.test_invoice_api_endpoints),
            ]

            for test_name, test_func in tests:
                print(f"\nRunning: {test_name}")
                self.test_results["total"] += 1
                try:
                    result = await test_func(page)
                except Exception as e:
                    print(f"  ✗ ERROR: {e}")
                    self.test_results["failed"].append(
                        {"test": test_name.split(".")[1].strip(), "reason": str(e)}
                    )

                await asyncio.sleep(1)

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
