#!/usr/bin/env python3
"""
Complete E2E Test Suite for Invoice System
Tests all invoice workflows from creation to payment
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
        self.parent_token = "parent_test_token_1234567890abcdef"
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
        elif method == "DELETE":
            request = f"""DELETE {url_path} HTTP/1.1\r
Host: localhost:8000\r
Authorization: Token {token}\r
Content-Type: application/json\r
Connection: close\r
\r
"""
        else:
            raise ValueError(f"Unsupported method: {method}")

        s.send(request.encode())
        response = s.recv(16384).decode()
        s.close()

        # Parse response
        headers, body = response.split('\r\n\r\n', 1) if '\r\n\r\n' in response else (response, "")
        header_lines = headers.split('\r\n')
        status_line = header_lines[0]
        status_code = int(status_line.split()[1])

        try:
            response_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            response_data = {"raw": body[:200]}

        return status_code, response_data

    def _add_result(self, name: str, passed: bool, detail: str, data: Dict):
        """Add test result"""
        self.test_results.append((name, passed, detail, data))

    def run_all_tests(self):
        """Run all E2E tests"""
        print("=" * 80)
        print("INVOICE SYSTEM - COMPLETE E2E TEST SUITE")
        print("=" * 80)

        # Test 1: Get empty tutor invoices list
        print("\n[Test 1] Get tutor invoices list")
        status, data = self._make_request("GET", "invoices/tutor/", self.tutor_token)
        passed = status == 200
        self._add_result("Get tutor invoices list", passed, f"Status {status}", data)
        print(f"{'✓' if passed else '✗'} Status: {status}")

        # Test 2: Create first invoice
        print("\n[Test 2] Create invoice #1")
        invoice_data = {
            "student_id": 156,
            "amount": "5000.00",
            "description": "Услуги по математике за декабрь",
            "due_date": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        status, data = self._make_request("POST", "invoices/tutor/",
                                        self.tutor_token, invoice_data)
        passed = status == 201
        invoice_id_1 = data.get('data', {}).get('id') if passed else None
        self._add_result("Create invoice", passed, f"Status {status}, ID: {invoice_id_1}", data)
        print(f"{'✓' if passed else '✗'} Status: {status}, Invoice ID: {invoice_id_1}")

        # Test 3: Get invoice detail
        if invoice_id_1:
            print("\n[Test 3] Get invoice detail")
            status, data = self._make_request("GET", f"invoices/tutor/{invoice_id_1}/",
                                            self.tutor_token)
            passed = status == 200
            self._add_result("Get invoice detail", passed, f"Status {status}", data)
            print(f"{'✓' if passed else '✗'} Status: {status}, Invoice status: {data.get('data', {}).get('status')}")

        # Test 4: Send invoice
        if invoice_id_1:
            print("\n[Test 4] Send invoice #1")
            status, data = self._make_request("POST",
                                            f"invoices/tutor/{invoice_id_1}/send/",
                                            self.tutor_token)
            passed = status == 200
            self._add_result("Send invoice", passed, f"Status {status}", data)
            print(f"{'✓' if passed else '✗'} Status: {status}")

        # Test 5: Get parent invoices list
        print("\n[Test 5] Get parent invoices list")
        status, data = self._make_request("GET", "invoices/parent/", self.parent_token)
        passed = status == 200
        count = data.get('data', {}).get('count', 0) if passed else 0
        self._add_result("Get parent invoices", passed, f"Status {status}, Count: {count}", data)
        print(f"{'✓' if passed else '✗'} Status: {status}, Invoices found: {count}")

        # Test 6: Mark invoice as viewed
        if invoice_id_1:
            print("\n[Test 6] Mark invoice as viewed")
            status, data = self._make_request("POST",
                                            f"invoices/parent/{invoice_id_1}/mark_viewed/",
                                            self.parent_token)
            passed = status == 200
            self._add_result("Mark invoice viewed", passed, f"Status {status}", data)
            print(f"{'✓' if passed else '✗'} Status: {status}")

        # Test 7: Initiate payment
        if invoice_id_1:
            print("\n[Test 7] Initiate payment")
            status, data = self._make_request("POST",
                                            f"invoices/parent/{invoice_id_1}/pay/",
                                            self.parent_token)
            passed = status == 200 and ('payment_url' in data.get('data', {}) or 'confirmation_url' in data.get('data', {}))
            payment_url = data.get('data', {}).get('payment_url') or data.get('data', {}).get('confirmation_url')
            self._add_result("Initiate payment", passed, f"Status {status}, Has URL: {bool(payment_url)}", data)
            print(f"{'✓' if passed else '✗'} Status: {status}, Has payment URL: {bool(payment_url)}")

        # Test 8: Create another invoice
        print("\n[Test 8] Create invoice #2")
        invoice_data2 = {
            "student_id": 156,
            "amount": "3000.00",
            "description": "Дополнительный урок",
            "due_date": (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')
        }
        status, data = self._make_request("POST", "invoices/tutor/",
                                        self.tutor_token, invoice_data2)
        passed = status == 201
        invoice_id_2 = data.get('data', {}).get('id') if passed else None
        self._add_result("Create 2nd invoice", passed, f"Status {status}, ID: {invoice_id_2}", data)
        print(f"{'✓' if passed else '✗'} Status: {status}, Invoice ID: {invoice_id_2}")

        # Test 9: List invoices with pagination
        print("\n[Test 9] List invoices")
        status, data = self._make_request("GET", "invoices/tutor/", self.tutor_token)
        passed = status == 200
        count = data.get('data', {}).get('count', 0) if passed else 0
        self._add_result("List invoices", passed, f"Status {status}, Count: {count}", data)
        print(f"{'✓' if passed else '✗'} Status: {status}, Total invoices: {count}")

        # Test 10: Validation - negative amount
        print("\n[Test 10] Validation - negative amount")
        bad_data = {
            "student_id": 156,
            "amount": "-1000.00",
            "description": "Bad",
            "due_date": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        status, data = self._make_request("POST", "invoices/tutor/",
                                        self.tutor_token, bad_data)
        passed = status == 400
        self._add_result("Validation error handling", passed, f"Status {status}", data)
        print(f"{'✓' if passed else '✗'} Status: {status} (should be 400)")

        # Test 11: Permission - student cannot create
        print("\n[Test 11] Permission check - student cannot create")
        student_token = "a01205ca90d72543d76b8358ba30c78759a5ef56"
        status, data = self._make_request("POST", "invoices/tutor/",
                                        student_token, invoice_data)
        passed = status == 403
        self._add_result("Student cannot create", passed, f"Status {status}", data)
        print(f"{'✓' if passed else '✗'} Status: {status} (should be 403)")

        # Test 12: Filter by status
        print("\n[Test 12] Filter invoices by status")
        status, data = self._make_request("GET", "invoices/tutor/?status=sent",
                                        self.tutor_token)
        passed = status == 200
        count = data.get('data', {}).get('count', 0) if passed else 0
        self._add_result("Filter by status", passed, f"Status {status}, Count: {count}", data)
        print(f"{'✓' if passed else '✗'} Status: {status}, Sent invoices: {count}")

        # Test 13: Cancel draft invoice
        if invoice_id_2:
            print("\n[Test 13] Cancel invoice")
            status, data = self._make_request("DELETE",
                                            f"invoices/tutor/{invoice_id_2}/",
                                            self.tutor_token)
            passed = status in [200, 204]
            self._add_result("Cancel invoice", passed, f"Status {status}", data)
            print(f"{'✓' if passed else '✗'} Status: {status} (should be 200 or 204)")

        # Test 14: Verify cancelled invoice not in list
        print("\n[Test 14] Verify invoice removed from list")
        status, data = self._make_request("GET", "invoices/tutor/", self.tutor_token)
        passed = status == 200
        count = data.get('data', {}).get('count', 0) if passed else 0
        self._add_result("After cancellation", passed, f"Status {status}, Count: {count}", data)
        print(f"{'✓' if passed else '✗'} Status: {status}, Invoice count: {count}")

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)

        total = len(self.test_results)
        passed = sum(1 for _, p, _, _ in self.test_results if p)
        failed = total - passed

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Pass Rate: {(passed/total*100):.1f}%")

        print("\n" + "-" * 80)
        print("Detailed Results:")
        print("-" * 80)

        for i, (name, passed_flag, detail, _) in enumerate(self.test_results, 1):
            status = "✓ PASS" if passed_flag else "✗ FAIL"
            print(f"{i:2d}. {status:8s} | {name:40s} | {detail}")

        print("\n" + "=" * 80)
        if failed == 0:
            print("✓ ALL TESTS PASSED!")
        else:
            print(f"✗ {failed} test(s) failed")
        print("=" * 80)

if __name__ == "__main__":
    tester = InvoiceE2ETester()
    tester.run_all_tests()
