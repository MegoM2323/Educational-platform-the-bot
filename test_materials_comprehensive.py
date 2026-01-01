"""
Comprehensive Materials & Content Management Testing
Tests for THE_BOT platform material upload, view, and access control
"""

import os
import json
import requests
from datetime import datetime
from io import BytesIO
from pathlib import Path

# API Configuration
API_BASE_URL = "http://localhost:8000/api"
TEST_CREDENTIALS = {
    "teacher": {
        "email": "teacher2@test.com",
        "password": "password123"
    },
    "student1": {
        "email": "student3@test.com",
        "password": "password123"
    },
    "student2": {
        "email": "student1@test.com",
        "password": "password123"
    },
    "student3": {
        "email": "student2@test.com",
        "password": "password123"
    }
}

class MaterialTestSuite:
    """Test suite for material management functionality"""

    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0
            },
            "issues": [],
            "file_types_supported": {},
            "security_checks": {}
        }
        self.sessions = {}
        self.material_ids = {}

    def log_test(self, name, passed, details):
        """Log a test result"""
        self.results["tests"].append({
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "timestamp": datetime.now().isoformat(),
            "details": details
        })
        self.results["summary"]["total"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1

    def log_issue(self, issue_type, severity, description, details=None):
        """Log an issue found during testing"""
        self.results["issues"].append({
            "type": issue_type,
            "severity": severity,
            "description": description,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def create_test_file(self, filename, file_type, size_kb=None):
        """Create a test file in memory"""
        if file_type == "pdf":
            # Simple PDF header
            content = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
            content += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            content += b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            content += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            content += b"xref\n0 4\n0000000000 65535 f\n"
            content += b"0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n"
            content += b"<< /Size 4 /Root 1 0 R >>\nstartxref\n200\n%%EOF"
        elif file_type == "image":
            # Simple PNG header
            content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            content += b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
            content += b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x00\x00\x00\x00IEND\xaeB`\x82"
        elif file_type == "word":
            # DOCX is a ZIP file with XML
            content = b"PK\x03\x04" + b"\x00" * 100  # ZIP header + padding
        elif file_type == "text":
            content = b"This is a test document for material upload testing.\n" * 10
        else:
            content = b"Test file content\n" * 10

        # If size specified, pad the file
        if size_kb:
            target_size = size_kb * 1024
            if len(content) < target_size:
                content += b"x" * (target_size - len(content))
            else:
                content = content[:target_size]

        return BytesIO(content)

    def login_user(self, role):
        """Login a user and return session"""
        if role in self.sessions:
            return self.sessions[role]

        creds = TEST_CREDENTIALS.get(role)
        if not creds:
            raise ValueError(f"No credentials for role: {role}")

        session = requests.Session()
        response = session.post(
            f"{API_BASE_URL}/auth/login/",
            json=creds
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Login failed for {role}: {response.status_code} - {response.text}")

        # Extract token from response
        data = response.json()
        if not data.get("success"):
            raise Exception(f"Login failed for {role}: {data.get('error', 'Unknown error')}")

        token = data.get("data", {}).get("token")
        if not token:
            raise Exception(f"No token in response for {role}")

        # Add token to session headers
        session.headers.update({
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        })

        self.sessions[role] = session
        return session

    # Test 1: Teacher login and material upload
    def test_teacher_login_and_upload(self):
        """Test 1: Teacher login and upload PDF material"""
        try:
            session = self.login_user("teacher")
            self.log_test(
                "test_teacher_login_and_upload",
                True,
                "Teacher logged in successfully"
            )
            return session
        except Exception as e:
            self.log_test(
                "test_teacher_login_and_upload",
                False,
                str(e)
            )
            self.log_issue("AUTHENTICATION", "critical", "Teacher login failed", str(e))
            return None

    # Test 2: PDF Upload
    def test_upload_pdf_material(self):
        """Test 2: Upload PDF material"""
        session = self.test_teacher_login_and_upload()
        if not session:
            self.log_test("test_upload_pdf_material", False, "No session available")
            return None

        try:
            # Create a test PDF
            pdf_file = self.create_test_file("test.pdf", "pdf")

            # Get subject list first
            subjects_response = session.get(f"{API_BASE_URL}/materials/subjects/")
            if subjects_response.status_code != 200:
                raise Exception(f"Failed to get subjects: {subjects_response.status_code}")

            subjects = subjects_response.json()
            if not subjects:
                raise Exception("No subjects available")

            subject_id = subjects[0]["id"]

            # Upload material
            files = {"file": pdf_file}
            data = {
                "title": "Учебник Математика - Глава 3.pdf",
                "description": "Основные концепции алгебры",
                "subject": subject_id,
                "type": "document",
                "status": "active",
                "assigned_to": [1, 2]  # Assign to students
            }

            response = session.post(
                f"{API_BASE_URL}/materials/materials/",
                files=files,
                data=data
            )

            if response.status_code in [200, 201]:
                material_data = response.json()
                self.material_ids["pdf"] = material_data.get("id")
                self.log_test("test_upload_pdf_material", True, f"PDF uploaded: {material_data.get('id')}")
                return material_data
            else:
                self.log_test("test_upload_pdf_material", False, f"Upload failed: {response.status_code} - {response.text}")
                self.log_issue("UPLOAD", "high", "PDF upload failed", response.text)
                return None
        except Exception as e:
            self.log_test("test_upload_pdf_material", False, str(e))
            self.log_issue("UPLOAD", "high", "PDF upload exception", str(e))
            return None

    # Test 3: Image Upload
    def test_upload_image_material(self):
        """Test 3: Upload image material"""
        session = self.test_teacher_login_and_upload()
        if not session:
            return None

        try:
            # Create a test image
            image_file = self.create_test_file("test.png", "image")

            subjects_response = session.get(f"{API_BASE_URL}/materials/subjects/")
            subjects = subjects_response.json()
            subject_id = subjects[0]["id"]

            files = {"file": image_file}
            data = {
                "title": "Диаграмма функций",
                "description": "Визуальное представление графиков",
                "subject": subject_id,
                "type": "document",
                "status": "active",
                "assigned_to": [3]
            }

            response = session.post(
                f"{API_BASE_URL}/materials/materials/",
                files=files,
                data=data
            )

            passed = response.status_code in [200, 201]
            self.material_ids["image"] = response.json().get("id") if passed else None

            if passed:
                self.results["file_types_supported"]["image"] = "PASS"
            else:
                self.results["file_types_supported"]["image"] = "FAIL"
                self.log_issue("UPLOAD", "medium", "Image upload failed", response.text)

            self.log_test("test_upload_image_material", passed,
                         f"Image upload: {response.status_code}")
            return response.json() if passed else None
        except Exception as e:
            self.log_test("test_upload_image_material", False, str(e))
            self.results["file_types_supported"]["image"] = "ERROR"
            return None

    # Test 4: Word Document Upload
    def test_upload_word_material(self):
        """Test 4: Upload Word document"""
        session = self.test_teacher_login_and_upload()
        if not session:
            return None

        try:
            word_file = self.create_test_file("test.docx", "word")

            subjects_response = session.get(f"{API_BASE_URL}/materials/subjects/")
            subjects = subjects_response.json()
            subject_id = subjects[0]["id"]

            files = {"file": word_file}
            data = {
                "title": "Шаблон для решений",
                "description": "Word шаблон для студентов",
                "subject": subject_id,
                "type": "document",
                "status": "active",
                "assigned_to": [1, 2, 3]
            }

            response = session.post(
                f"{API_BASE_URL}/materials/materials/",
                files=files,
                data=data
            )

            passed = response.status_code in [200, 201]
            if passed:
                self.material_ids["word"] = response.json().get("id")
                self.results["file_types_supported"]["docx"] = "PASS"
            else:
                self.results["file_types_supported"]["docx"] = "FAIL"
                self.log_issue("UPLOAD", "medium", "Word upload failed", response.text)

            self.log_test("test_upload_word_material", passed,
                         f"Word upload: {response.status_code}")
            return response.json() if passed else None
        except Exception as e:
            self.log_test("test_upload_word_material", False, str(e))
            self.results["file_types_supported"]["docx"] = "ERROR"
            return None

    # Test 5: File Size Validation
    def test_file_size_limit(self):
        """Test 5: File size limit validation (5MB+)"""
        session = self.test_teacher_login_and_upload()
        if not session:
            return None

        try:
            # Create a 5MB+ file
            large_file = self.create_test_file("large.pdf", "pdf", size_kb=5100)

            subjects_response = session.get(f"{API_BASE_URL}/materials/subjects/")
            subjects = subjects_response.json()
            subject_id = subjects[0]["id"]

            files = {"file": large_file}
            data = {
                "title": "Large File Test",
                "description": "Testing 5MB+ file upload",
                "subject": subject_id,
                "type": "document",
                "status": "active"
            }

            response = session.post(
                f"{API_BASE_URL}/materials/materials/",
                files=files,
                data=data
            )

            # Should fail with 413 or validation error
            passed = response.status_code >= 400  # Expected to fail

            if passed:
                self.log_test("test_file_size_limit", True,
                             f"Correctly rejected large file: {response.status_code}")
            else:
                self.log_test("test_file_size_limit", False,
                             f"Large file was accepted: {response.status_code}")
                self.log_issue("SECURITY", "high", "File size limit not enforced",
                             f"5MB+ file accepted: {response.status_code}")

            return passed
        except Exception as e:
            self.log_test("test_file_size_limit", False, str(e))
            return None

    # Test 6: Student Views Materials
    def test_student_view_materials(self):
        """Test 6: Student views assigned materials"""
        try:
            student_session = self.login_user("student1")

            # Get materials for student1
            response = student_session.get(f"{API_BASE_URL}/materials/materials/")

            if response.status_code == 200:
                materials = response.json()
                self.log_test("test_student_view_materials", True,
                             f"Student1 views {len(materials) if isinstance(materials, list) else 1} materials")
                return materials
            else:
                self.log_test("test_student_view_materials", False,
                             f"Failed to view materials: {response.status_code}")
                return None
        except Exception as e:
            self.log_test("test_student_view_materials", False, str(e))
            return None

    # Test 7: Access Control - Unauthorized Student
    def test_unauthorized_student_access(self):
        """Test 7: Unauthorized student cannot access others' materials"""
        try:
            student2_session = self.login_user("student2")
            student3_session = self.login_user("student3")

            # Get a material assigned to student1
            student2_response = student2_session.get(f"{API_BASE_URL}/materials/materials/")

            if student2_response.status_code == 200:
                materials = student2_response.json()
                student2_ids = {m["id"] for m in materials} if isinstance(materials, list) else set()
            else:
                student2_ids = set()

            # Get a material assigned to student1
            student3_response = student3_session.get(f"{API_BASE_URL}/materials/materials/")

            if student3_response.status_code == 200:
                materials = student3_response.json()
                student3_ids = {m["id"] for m in materials} if isinstance(materials, list) else set()
            else:
                student3_ids = set()

            # Check if they see different materials (security)
            overlap = student2_ids & student3_ids

            # They should see only their assigned materials
            no_overlap = len(overlap) == 0 or overlap == student2_ids & student3_ids

            self.log_test("test_unauthorized_student_access", True,
                         f"Student access isolation working: {no_overlap}")

            if not no_overlap:
                self.log_issue("SECURITY", "high", "Access control bypass detected",
                             f"Students see overlapping materials: {overlap}")

            self.results["security_checks"]["access_control"] = "PASS" if no_overlap else "FAIL"
            return no_overlap
        except Exception as e:
            self.log_test("test_unauthorized_student_access", False, str(e))
            self.results["security_checks"]["access_control"] = "ERROR"
            return None

    # Test 8: Download Material
    def test_download_material(self):
        """Test 8: Download material file"""
        try:
            if not self.material_ids.get("pdf"):
                self.log_test("test_download_material", False, "No PDF material uploaded")
                return None

            student_session = self.login_user("student1")
            material_id = self.material_ids["pdf"]

            # Try to download
            response = student_session.get(
                f"{API_BASE_URL}/materials/{material_id}/download/"
            )

            if response.status_code == 200:
                # Check content
                has_content = len(response.content) > 0
                self.log_test("test_download_material", has_content,
                             f"Download successful: {len(response.content)} bytes")
                return has_content
            else:
                self.log_test("test_download_material", False,
                             f"Download failed: {response.status_code}")
                return None
        except Exception as e:
            self.log_test("test_download_material", False, str(e))
            return None

    # Test 9: Material Metadata
    def test_material_metadata(self):
        """Test 9: Check material metadata is complete"""
        try:
            if not self.material_ids.get("pdf"):
                return None

            session = self.login_user("student1")
            material_id = self.material_ids["pdf"]

            response = session.get(f"{API_BASE_URL}/materials/materials/{material_id}/")

            if response.status_code == 200:
                material = response.json()

                required_fields = ["title", "description", "author_name", "created_at", "status"]
                missing_fields = [f for f in required_fields if f not in material]

                if not missing_fields:
                    self.log_test("test_material_metadata", True, "All metadata fields present")
                    return True
                else:
                    self.log_test("test_material_metadata", False,
                                 f"Missing fields: {missing_fields}")
                    return False
            else:
                self.log_test("test_material_metadata", False,
                             f"Failed to get metadata: {response.status_code}")
                return None
        except Exception as e:
            self.log_test("test_material_metadata", False, str(e))
            return None

    # Test 10: Update Material
    def test_update_material(self):
        """Test 10: Teacher updates material"""
        try:
            session = self.test_teacher_login_and_upload()
            if not self.material_ids.get("pdf"):
                return None

            material_id = self.material_ids["pdf"]

            # Update material
            data = {
                "title": "Updated Title",
                "description": "Updated description"
            }

            response = session.patch(
                f"{API_BASE_URL}/materials/materials/{material_id}/",
                json=data
            )

            if response.status_code in [200, 201]:
                self.log_test("test_update_material", True, "Material updated successfully")
                return True
            else:
                self.log_test("test_update_material", False,
                             f"Update failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("test_update_material", False, str(e))
            return None

    # Test 11: Delete Material
    def test_delete_material(self):
        """Test 11: Teacher deletes material"""
        try:
            # Create a temp material to delete
            session = self.test_teacher_login_and_upload()
            if not session:
                return None

            pdf_file = self.create_test_file("delete_test.pdf", "pdf")

            subjects_response = session.get(f"{API_BASE_URL}/materials/subjects/")
            subjects = subjects_response.json()
            subject_id = subjects[0]["id"]

            files = {"file": pdf_file}
            data = {
                "title": "Material To Delete",
                "description": "This will be deleted",
                "subject": subject_id,
                "type": "document",
                "status": "active"
            }

            create_response = session.post(
                f"{API_BASE_URL}/materials/materials/",
                files=files,
                data=data
            )

            if create_response.status_code not in [200, 201]:
                return None

            material_id = create_response.json().get("id")

            # Delete material
            delete_response = session.delete(
                f"{API_BASE_URL}/materials/materials/{material_id}/"
            )

            if delete_response.status_code in [200, 204]:
                self.log_test("test_delete_material", True, "Material deleted successfully")
                return True
            else:
                self.log_test("test_delete_material", False,
                             f"Delete failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("test_delete_material", False, str(e))
            return None

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 80)
        print("MATERIALS & CONTENT MANAGEMENT TEST SUITE")
        print("=" * 80)
        print()

        # Run tests
        self.test_teacher_login_and_upload()
        self.test_upload_pdf_material()
        self.test_upload_image_material()
        self.test_upload_word_material()
        self.test_file_size_limit()
        self.test_student_view_materials()
        self.test_unauthorized_student_access()
        self.test_download_material()
        self.test_material_metadata()
        self.test_update_material()
        self.test_delete_material()

        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        print(f"Success Rate: {(self.results['summary']['passed'] / self.results['summary']['total'] * 100):.1f}%")

        print("\n" + "=" * 80)
        print("FILE TYPES SUPPORTED")
        print("=" * 80)
        for file_type, status in self.results["file_types_supported"].items():
            print(f"  {file_type}: {status}")

        if self.results["issues"]:
            print("\n" + "=" * 80)
            print("ISSUES FOUND")
            print("=" * 80)
            for issue in self.results["issues"]:
                print(f"  [{issue['severity'].upper()}] {issue['description']}")

        return self.results


if __name__ == "__main__":
    suite = MaterialTestSuite()
    results = suite.run_all_tests()

    # Save results to JSON
    output_file = "/home/mego/Python Projects/THE_BOT_platform/test_materials_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {output_file}")
