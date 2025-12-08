#!/usr/bin/env python3
"""
E2E Test Script for Invoice System
Tests the complete invoice workflow from tutor creation to parent payment
"""

import socket
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class InvoiceE2ETester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.tutor_token = "522faa789d6ee261548a4ea775b1bef06d059764"
        self.parent_token = None  # Will get from parent user
        self.test_results = []

    def _make_request(self, method: str, endpoint: str, token: str,
                     data: Optional[Dict] = None) -> tuple[int, Dict]:
        """Make HTTP request to Django backend"""
        s = socket.socket()
        s.connect(('localhost', 8000))

        url_path = f"/api/{endpoint}"

        if method == "GET":
            request = f"""GET {url_path} HTTP/1.1\r
Host: localhost:8000\r
Authorization: Token {token}\r
Content-Type: application/json\r
Connection: close\r
\r
"""
        elif method == "POST" or method == "PATCH":
            body = json.dumps(data) if data else ""
            request = f"""{method} {url_path} HTTP/1.1\r
Host: localhost:8000\r
Authorization: Token {token}\r
Content-Type: application/json\r
Content-Length: {len(body)}\r
Connection: close\r
\r
{body}"""
        else:
            raise ValueError(f"Unsupported method: {method}")

        s.send(request.encode())
        response = s.recv(16384).decode()
        s.close()

        # Parse response
        headers, body = response.split('\r\n\r\n', 1)
        header_lines = headers.split('\r\n')
        status_line = header_lines[0]
        status_code = int(status_line.split()[1])

        try:
            response_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            response_data = {"raw": body[:200]}

        return status_code, response_data

    def test_1_get_tutor_invoices_list(self):
        """Test 1: Tutor can retrieve empty invoice list"""
        print("\n=== Test 1: Get Tutor Invoices List ===")
        status, data = self._make_request("GET", "invoices/tutor/", self.tutor_token)

        expected = 200
        passed = status == expected
        self.test_results.append(("Test 1: Get tutor invoices", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Tutor invoices list retrieved (status {status})")
            if 'data' in data:
                print(f"  - Count: {data['data']['count']}")
                print(f"  - Results: {len(data['data']['results'])}")
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")

        return passed

    def test_2_create_invoice(self):
        """Test 2: Tutor can create an invoice"""
        print("\n=== Test 2: Create Invoice ===")

        invoice_data = {
            "student_id": 156,  # opt_student_0
            "amount": "5000.00",
            "description": "Услуги по математике за декабрь",
            "due_date": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }

        status, data = self._make_request("POST", "invoices/tutor/",
                                        self.tutor_token, invoice_data)

        expected = 201
        passed = status == expected
        self.test_results.append(("Test 2: Create invoice", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Invoice created (status {status})")
            if 'data' in data:
                invoice = data['data']
                print(f"  - Invoice ID: {invoice.get('id')}")
                print(f"  - Amount: {invoice.get('amount')}")
                print(f"  - Status: {invoice.get('status')}")
                self.created_invoice_id = invoice.get('id')
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")
            print(f"  Response: {data}")

        return passed

    def test_3_get_invoice_detail(self):
        """Test 3: Tutor can retrieve invoice detail"""
        print("\n=== Test 3: Get Invoice Detail ===")

        if not hasattr(self, 'created_invoice_id'):
            print("⊘ SKIP: No invoice created in previous test")
            return False

        status, data = self._make_request("GET",
                                        f"invoices/tutor/{self.created_invoice_id}/",
                                        self.tutor_token)

        expected = 200
        passed = status == expected
        self.test_results.append(("Test 3: Get invoice detail", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Invoice detail retrieved (status {status})")
            if 'data' in data:
                invoice = data['data']
                print(f"  - ID: {invoice.get('id')}")
                print(f"  - Status: {invoice.get('status')}")
                print(f"  - Student: {invoice.get('student_id')}")
                print(f"  - Amount: {invoice.get('amount')}")
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")

        return passed

    def test_4_send_invoice(self):
        """Test 4: Tutor can send invoice to parent"""
        print("\n=== Test 4: Send Invoice ===")

        if not hasattr(self, 'created_invoice_id'):
            print("⊘ SKIP: No invoice created")
            return False

        status, data = self._make_request("POST",
                                        f"invoices/tutor/{self.created_invoice_id}/send/",
                                        self.tutor_token)

        expected = 200
        passed = status == expected
        self.test_results.append(("Test 4: Send invoice", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Invoice sent (status {status})")
            if 'data' in data:
                print(f"  - New status: {data['data'].get('status')}")
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")
            print(f"  Response: {data}")

        return passed

    def test_5_get_parent_invoices_list(self):
        """Test 5: Parent can retrieve invoice list"""
        print("\n=== Test 5: Get Parent Invoices List ===")

        # Parent token
        parent_token = "parent_test_token_1234567890abcdef"

        status, data = self._make_request("GET", "invoices/parent/", parent_token)

        expected = 200
        passed = status == expected
        self.test_results.append(("Test 5: Get parent invoices", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Parent invoices list retrieved (status {status})")
            if 'data' in data:
                print(f"  - Count: {data['data']['count']}")
                print(f"  - Results: {len(data['data']['results'])}")
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")

        return passed

    def test_6_invoice_status_persistence(self):
        """Test 6: Invoice status is persisted after send"""
        print("\n=== Test 6: Invoice Status Persistence ===")

        if not hasattr(self, 'created_invoice_id'):
            print("⊘ SKIP: No invoice created")
            return False

        status, data = self._make_request("GET",
                                        f"invoices/tutor/{self.created_invoice_id}/",
                                        self.tutor_token)

        expected = 200
        passed = status == expected and 'data' in data

        if passed and data['data'].get('status') != 'sent':
            passed = False

        self.test_results.append(("Test 6: Invoice status persistent", passed,
                                 f"Status should be 'sent'", data))

        if passed:
            print(f"✓ PASS: Invoice status persisted as '{data['data'].get('status')}'")
        else:
            print(f"✗ FAIL: Invoice status not 'sent'")

        return passed

    def test_7_list_invoices_count(self):
        """Test 7: Created invoice appears in list"""
        print("\n=== Test 7: Invoice Appears in List ===")

        status, data = self._make_request("GET", "invoices/tutor/", self.tutor_token)

        expected = 200
        passed = status == expected

        if passed and 'data' in data:
            count = data['data'].get('count', 0)
            passed = count > 0
            message = f"Count: {count}"
        else:
            message = f"Status: {status}"

        self.test_results.append(("Test 7: Invoice in list", passed, message, data))

        if passed:
            print(f"✓ PASS: Invoice found in list (count: {count})")
        else:
            print(f"✗ FAIL: Invoice not in list")

        return passed

    def test_8_invalid_amount_validation(self):
        """Test 8: Negative amount is rejected"""
        print("\n=== Test 8: Invalid Amount Validation ===")

        invoice_data = {
            "student_id": 157,
            "amount": "-1000.00",  # Invalid negative amount
            "description": "Test",
            "due_date": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }

        status, data = self._make_request("POST", "invoices/tutor/",
                                        self.tutor_token, invoice_data)

        # Should be 400 Bad Request
        expected = 400
        passed = status == expected

        self.test_results.append(("Test 8: Invalid amount rejected", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Invalid amount rejected (status {status})")
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")

        return passed

    def test_9_permission_check_student_cannot_create(self):
        """Test 9: Student cannot create invoices"""
        print("\n=== Test 9: Permission Check - Student Cannot Create ===")

        # Create a test student token if needed
        student_token = "a01205ca90d72543d76b8358ba30c78759a5ef56"  # opt_student_0 token

        invoice_data = {
            "student_id": 156,
            "amount": "5000.00",
            "description": "Test",
            "due_date": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }

        status, data = self._make_request("POST", "invoices/tutor/",
                                        student_token, invoice_data)

        # Should be 403 Forbidden
        expected = 403
        passed = status == expected

        self.test_results.append(("Test 9: Student cannot create", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Student creation rejected (status {status})")
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")

        return passed

    def test_10_get_tutor_statistics(self):
        """Test 10: Tutor can retrieve invoice statistics"""
        print("\n=== Test 10: Get Tutor Statistics ===")

        status, data = self._make_request("GET", "invoices/tutor/statistics/",
                                        self.tutor_token)

        expected = 200
        passed = status == expected

        self.test_results.append(("Test 10: Get statistics", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Statistics retrieved (status {status})")
            if 'data' in data:
                stats = data['data']
                print(f"  - Total invoices: {stats.get('total_invoices')}")
                print(f"  - Total amount: {stats.get('total_amount')}")
                print(f"  - Sent: {stats.get('sent_count')}")
                print(f"  - Paid: {stats.get('paid_count')}")
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")

        return passed

    def run_all_tests(self):
        """Run all tests and generate report"""
        print("=" * 70)
        print("INVOICE SYSTEM E2E TEST SUITE")
        print("=" * 70)

        self.test_1_get_tutor_invoices_list()
        self.test_2_create_invoice()
        self.test_3_get_invoice_detail()
        self.test_4_send_invoice()
        self.test_5_get_parent_invoices_list()
        self.test_6_invoice_status_persistence()
        self.test_7_list_invoices_count()
        self.test_8_invalid_amount_validation()
        self.test_9_permission_check_student_cannot_create()
        self.test_10_get_tutor_statistics()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        total = len(self.test_results)
        passed = sum(1 for _, p, _, _ in self.test_results if p)
        failed = total - passed

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Pass Rate: {(passed/total*100):.1f}%\n")

        print("Detailed Results:")
        print("-" * 70)
        for name, passed, detail, _ in self.test_results:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status} | {name}")
            print(f"       {detail}")
            print()

if __name__ == "__main__":
    tester = InvoiceE2ETester()
    tester.run_all_tests()

    def test_11_mark_invoice_viewed(self):
        """Test 11: Parent can mark invoice as viewed"""
        print("\n=== Test 11: Mark Invoice Viewed ===")

        parent_token = "parent_test_token_1234567890abcdef"
        invoice_id = 1  # From previous test

        status, data = self._make_request("POST",
                                        f"invoices/parent/{invoice_id}/mark_viewed/",
                                        parent_token)

        expected = 200
        passed = status == expected

        self.test_results.append(("Test 11: Mark invoice viewed", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Invoice marked as viewed (status {status})")
            if 'data' in data:
                print(f"  - Status: {data['data'].get('status')}")
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")

        return passed

    def test_12_initiate_payment(self):
        """Test 12: Parent can initiate payment for invoice"""
        print("\n=== Test 12: Initiate Payment ===")

        parent_token = "parent_test_token_1234567890abcdef"
        invoice_id = 1

        status, data = self._make_request("POST",
                                        f"invoices/parent/{invoice_id}/pay/",
                                        parent_token)

        expected = 200
        passed = status == expected and 'data' in data

        if passed:
            # Check if payment URL is returned
            payment_data = data.get('data', {})
            has_payment_url = 'payment_url' in payment_data or 'confirmation_url' in payment_data

            self.test_results.append(("Test 12: Initiate payment", has_payment_url,
                                     f"Payment URL present", data))

            if has_payment_url:
                print(f"✓ PASS: Payment initiated (status {status})")
                url = payment_data.get('payment_url') or payment_data.get('confirmation_url')
                print(f"  - Payment URL: {url[:50]}...")
                return True
            else:
                print(f"✗ FAIL: No payment URL returned")
                return False
        else:
            self.test_results.append(("Test 12: Initiate payment", False,
                                     f"Status {status} == {expected}", data))
            print(f"✗ FAIL: Expected status {expected}, got {status}")
            return False

    def test_13_create_multiple_invoices(self):
        """Test 13: Tutor can create multiple invoices"""
        print("\n=== Test 13: Create Multiple Invoices ===")

        invoice_ids = []
        for i in range(3):
            invoice_data = {
                "student_id": 156,
                "amount": f"{1000 * (i+1)}.00",
                "description": f"Invoice {i+1}",
                "due_date": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            }

            status, data = self._make_request("POST", "invoices/tutor/",
                                            self.tutor_token, invoice_data)

            if status == 201 and 'data' in data:
                invoice_ids.append(data['data']['id'])

        passed = len(invoice_ids) == 3

        self.test_results.append(("Test 13: Create multiple invoices", passed,
                                 f"Created {len(invoice_ids)} invoices", {}))

        if passed:
            print(f"✓ PASS: Created {len(invoice_ids)} invoices")
            for inv_id in invoice_ids:
                print(f"  - Invoice ID: {inv_id}")
        else:
            print(f"✗ FAIL: Failed to create 3 invoices")

        return passed

    def test_14_filter_invoices_by_status(self):
        """Test 14: Tutor can filter invoices by status"""
        print("\n=== Test 14: Filter Invoices by Status ===")

        status, data = self._make_request("GET", "invoices/tutor/?status=sent",
                                        self.tutor_token)

        expected = 200
        passed = status == expected

        self.test_results.append(("Test 14: Filter by status", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Filtered invoices retrieved (status {status})")
            if 'data' in data:
                count = data['data'].get('count', 0)
                print(f"  - Sent invoices: {count}")
        else:
            print(f"✗ FAIL: Expected status {expected}, got {status}")

        return passed

    def test_15_cancel_invoice(self):
        """Test 15: Tutor can cancel a draft invoice"""
        print("\n=== Test 15: Cancel Invoice ===")

        # Create a new invoice
        invoice_data = {
            "student_id": 156,
            "amount": "3000.00",
            "description": "Invoice to cancel",
            "due_date": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }

        create_status, create_data = self._make_request("POST", "invoices/tutor/",
                                                       self.tutor_token, invoice_data)

        if create_status != 201:
            self.test_results.append(("Test 15: Cancel invoice", False,
                                     "Failed to create invoice", {}))
            print("✗ FAIL: Could not create invoice to cancel")
            return False

        invoice_id = create_data['data']['id']

        # Cancel it
        status, data = self._make_request("DELETE",
                                        f"invoices/tutor/{invoice_id}/",
                                        self.tutor_token)

        expected = 204  # No content for successful delete
        passed = status == expected

        self.test_results.append(("Test 15: Cancel invoice", passed,
                                 f"Status {status} == {expected}", data))

        if passed:
            print(f"✓ PASS: Invoice cancelled (status {status})")
        else:
            # Try 200 as alternative success code
            if status == 200:
                print(f"✓ PASS: Invoice cancelled (status {status})")
                passed = True
            else:
                print(f"✗ FAIL: Expected status {expected}, got {status}")

        return passed

# Add new tests to run_all_tests
def run_all_tests_extended(self):
    """Run all tests including new ones"""
    print("=" * 70)
    print("INVOICE SYSTEM E2E TEST SUITE (EXTENDED)")
    print("=" * 70)

    self.test_1_get_tutor_invoices_list()
    self.test_2_create_invoice()
    self.test_3_get_invoice_detail()
    self.test_4_send_invoice()
    self.test_5_get_parent_invoices_list()
    self.test_6_invoice_status_persistence()
    self.test_7_list_invoices_count()
    self.test_8_invalid_amount_validation()
    self.test_9_permission_check_student_cannot_create()
    self.test_11_mark_invoice_viewed()
    self.test_12_initiate_payment()
    self.test_13_create_multiple_invoices()
    self.test_14_filter_invoices_by_status()
    self.test_15_cancel_invoice()

    # Print summary
    self.print_summary()

# Replace the main block
if __name__ == "__main__":
    tester = InvoiceE2ETester()
    tester.run_all_tests_extended()
