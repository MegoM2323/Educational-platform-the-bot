"""
Simple Materials Testing with Direct HTTP Requests
"""

import os
import json
import requests
from datetime import datetime
from io import BytesIO

API_BASE_URL = "http://localhost:8000/api"

class SimpleMaterialTests:
    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "tests": [],
            "passed": 0,
            "failed": 0,
            "issues": []
        }
        self.token = None
        self.user_data = None

    def test_login(self):
        """Test 1: User Login"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/login/",
                json={"email": "teacher2@test.com", "password": "password123"},
                timeout=10
            )

            print(f"Login status: {response.status_code}")
            print(f"Response: {response.text[:300]}")

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.token = data.get("data", {}).get("token")
                    self.user_data = data.get("data", {}).get("user")
                    print(f"✓ Login successful: {self.token[:20]}...")
                    self.results["tests"].append({
                        "name": "test_login",
                        "status": "PASS",
                        "user": self.user_data.get("email")
                    })
                    self.results["passed"] += 1
                    return True
                else:
                    print(f"✗ Login failed: {data.get('error', 'Unknown error')}")
            else:
                print(f"✗ Wrong status code: {response.status_code}")
        except Exception as e:
            print(f"✗ Login error: {e}")
            self.results["issues"].append(f"Login failed: {e}")
            self.results["failed"] += 1
        return False

    def get_subjects(self):
        """Get list of subjects"""
        try:
            response = requests.get(
                f"{API_BASE_URL}/materials/subjects/",
                headers={"Authorization": f"Token {self.token}"},
                timeout=10
            )

            if response.status_code == 200:
                subjects = response.json()
                if isinstance(subjects, list) and subjects:
                    print(f"✓ Found {len(subjects)} subjects")
                    return subjects
                elif isinstance(subjects, dict) and "results" in subjects:
                    return subjects.get("results", [])
        except Exception as e:
            print(f"✗ Get subjects error: {e}")
        return []

    def test_pdf_upload(self):
        """Test 2: PDF File Upload"""
        if not self.token:
            print("✗ Cannot upload: not logged in")
            return False

        try:
            subjects = self.get_subjects()
            if not subjects:
                print("✗ No subjects available")
                self.results["issues"].append("No subjects found for material upload")
                return False

            subject_id = subjects[0].get("id") if isinstance(subjects[0], dict) else subjects[0]

            # Create PDF content
            pdf_content = b"%PDF-1.4\n" + b"Sample PDF content\n" * 100

            files = {
                "file": ("test.pdf", BytesIO(pdf_content), "application/pdf")
            }
            data = {
                "title": "Test PDF Material",
                "description": "Testing PDF upload",
                "subject": subject_id,
                "type": "document",
                "status": "active"
            }

            response = requests.post(
                f"{API_BASE_URL}/materials/materials/",
                files=files,
                data=data,
                headers={"Authorization": f"Token {self.token}"},
                timeout=20
            )

            if response.status_code in [200, 201]:
                print(f"✓ PDF uploaded successfully: {response.status_code}")
                self.results["tests"].append({
                    "name": "test_pdf_upload",
                    "status": "PASS",
                    "material_id": response.json().get("id")
                })
                self.results["passed"] += 1
                return response.json()
            else:
                print(f"✗ PDF upload failed: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                self.results["issues"].append(f"PDF upload failed: {response.status_code}")
                self.results["failed"] += 1
        except Exception as e:
            print(f"✗ PDF upload error: {e}")
            self.results["issues"].append(f"PDF upload exception: {e}")
            self.results["failed"] += 1

        return False

    def test_image_upload(self):
        """Test 3: Image Upload"""
        if not self.token:
            return False

        try:
            subjects = self.get_subjects()
            if not subjects:
                return False

            subject_id = subjects[0].get("id") if isinstance(subjects[0], dict) else subjects[0]

            # Simple PNG binary
            png_content = b"\x89PNG\r\n\x1a\n" + b"Test PNG\n" * 100

            files = {
                "file": ("test.png", BytesIO(png_content), "image/png")
            }
            data = {
                "title": "Test Image",
                "description": "Testing image upload",
                "subject": subject_id,
                "type": "document",
                "status": "active"
            }

            response = requests.post(
                f"{API_BASE_URL}/materials/materials/",
                files=files,
                data=data,
                headers={"Authorization": f"Token {self.token}"},
                timeout=20
            )

            if response.status_code in [200, 201]:
                print(f"✓ Image uploaded: {response.status_code}")
                self.results["tests"].append({
                    "name": "test_image_upload",
                    "status": "PASS"
                })
                self.results["passed"] += 1
                return True
            else:
                print(f"✗ Image upload failed: {response.status_code}")
                self.results["tests"].append({
                    "name": "test_image_upload",
                    "status": "FAIL",
                    "reason": response.text[:100]
                })
                self.results["failed"] += 1
        except Exception as e:
            print(f"✗ Image upload error: {e}")
            self.results["failed"] += 1

        return False

    def test_view_materials(self):
        """Test 4: View Materials List"""
        if not self.token:
            return False

        try:
            response = requests.get(
                f"{API_BASE_URL}/materials/materials/",
                headers={"Authorization": f"Token {self.token}"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # Handle pagination
                if isinstance(data, dict) and "results" in data:
                    materials = data.get("results", [])
                else:
                    materials = data if isinstance(data, list) else []

                print(f"✓ View materials: {len(materials)} items")
                self.results["tests"].append({
                    "name": "test_view_materials",
                    "status": "PASS",
                    "material_count": len(materials)
                })
                self.results["passed"] += 1
                return True
            else:
                print(f"✗ View materials failed: {response.status_code}")
                self.results["failed"] += 1
        except Exception as e:
            print(f"✗ View materials error: {e}")
            self.results["failed"] += 1

        return False

    def run_tests(self):
        """Run all tests"""
        print("=" * 80)
        print("MATERIALS TESTING SUITE")
        print("=" * 80)
        print()

        self.test_login()
        if not self.token:
            print("\n✗ Cannot proceed - login failed")
            self.save_results()
            return

        self.test_pdf_upload()
        self.test_image_upload()
        self.test_view_materials()

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")
        print(f"Total: {self.results['passed'] + self.results['failed']}")

        if self.results["issues"]:
            print("\nIssues:")
            for issue in self.results["issues"]:
                print(f"  - {issue}")

        self.save_results()

    def save_results(self):
        """Save results to JSON"""
        output_file = "/home/mego/Python Projects/THE_BOT_platform/test_materials_simple_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    tester = SimpleMaterialTests()
    tester.run_tests()
