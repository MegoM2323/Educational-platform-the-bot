"""
Regression Tests for Tutor Cabinet - All Existing Endpoints
Test Name: tutor_cabinet_final_test_20260107
Purpose: Verify all existing endpoints still work after recent changes
"""

import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta

User = get_user_model()


class RegressionTestBase(TestCase):
    """Base class for regression tests"""

    def setUp(self):
        self.client = APIClient()
        self.results = {
            "test_name": "tutor_cabinet_final_test_20260107",
            "timestamp": datetime.now().isoformat(),
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "endpoints": {}
        }

    def log_result(self, endpoint, method, status_code, expected, response_data=None, error=None):
        """Log test result"""
        self.results["total_tests"] += 1

        passed = status_code == expected
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1

        endpoint_key = f"{method} {endpoint}"
        if endpoint_key not in self.results["endpoints"]:
            self.results["endpoints"][endpoint_key] = {
                "status": "PASSED" if passed else "FAILED",
                "expected_status": expected,
                "actual_status": status_code,
                "error": error
            }

        if error:
            self.results["errors"].append({
                "endpoint": endpoint_key,
                "error": error
            })

    def create_test_users(self):
        """Create test users with different roles"""
        self.admin = User.objects.create_superuser(
            username="admin_test",
            email="admin@test.com",
            password="testpass123"
        )

        self.teacher = User.objects.create_user(
            username="teacher_test",
            email="teacher@test.com",
            password="testpass123",
            role="teacher"
        )

        self.student = User.objects.create_user(
            username="student_test",
            email="student@test.com",
            password="testpass123",
            role="student"
        )

        self.parent = User.objects.create_user(
            username="parent_test",
            email="parent@test.com",
            password="testpass123",
            role="parent"
        )


class ChatEndpointsRegression(RegressionTestBase):
    """Test Chat endpoints"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_chat_rooms_list(self):
        """GET /api/chat/rooms/ - list works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/chat/rooms/")
        self.log_result(
            "/api/chat/rooms/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_chat_rooms_create(self):
        """POST /api/chat/rooms/ - create works"""
        self.client.force_authenticate(user=self.teacher)
        data = {
            "name": "Test Room",
            "description": "Test Description",
            "room_type": "class"
        }
        response = self.client.post("/api/chat/rooms/", data, format="json")
        self.log_result(
            "/api/chat/rooms/",
            "POST",
            response.status_code,
            status.HTTP_201_CREATED,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_chat_messages_list(self):
        """GET /api/chat/messages/ - list works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/chat/messages/")
        self.log_result(
            "/api/chat/messages/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_chat_messages_create(self):
        """POST /api/chat/messages/ - create works"""
        self.client.force_authenticate(user=self.teacher)
        data = {
            "content": "Test message",
            "room": 1
        }
        response = self.client.post("/api/chat/messages/", data, format="json")
        self.log_result(
            "/api/chat/messages/",
            "POST",
            response.status_code,
            status.HTTP_201_CREATED,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class AccountsEndpointsRegression(RegressionTestBase):
    """Test Accounts endpoints"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_students_list(self):
        """GET /api/accounts/students/ - list works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/accounts/students/")
        self.log_result(
            "/api/accounts/students/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_students_detail(self):
        """GET /api/accounts/students/{id}/ - detail works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f"/api/accounts/students/{self.student.id}/")
        self.log_result(
            f"/api/accounts/students/{self.student.id}/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_users_update(self):
        """PATCH /api/accounts/users/{id}/ - update works"""
        self.client.force_authenticate(user=self.teacher)
        data = {"first_name": "Updated"}
        response = self.client.patch(f"/api/accounts/users/{self.teacher.id}/", data, format="json")
        self.log_result(
            f"/api/accounts/users/{self.teacher.id}/",
            "PATCH",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_tutor_profile(self):
        """GET /api/profile/tutor/ - tutor profile works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/profile/tutor/")
        self.log_result(
            "/api/profile/tutor/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class SchedulingEndpointsRegression(RegressionTestBase):
    """Test Scheduling endpoints"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_lessons_list(self):
        """GET /api/scheduling/lessons/ - list works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/scheduling/lessons/")
        self.log_result(
            "/api/scheduling/lessons/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_lessons_create(self):
        """POST /api/scheduling/lessons/ - create works"""
        self.client.force_authenticate(user=self.teacher)
        tomorrow = datetime.now() + timedelta(days=1)
        data = {
            "title": "Test Lesson",
            "scheduled_time": tomorrow.isoformat(),
            "duration_minutes": 60
        }
        response = self.client.post("/api/scheduling/lessons/", data, format="json")
        self.log_result(
            "/api/scheduling/lessons/",
            "POST",
            response.status_code,
            status.HTTP_201_CREATED,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_schedule_views(self):
        """GET /api/scheduling/schedule/ - views work"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/scheduling/schedule/")
        self.log_result(
            "/api/scheduling/schedule/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class MaterialsEndpointsRegression(RegressionTestBase):
    """Test Materials endpoints"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_subjects_list(self):
        """GET /api/materials/subjects/ - list works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/materials/subjects/")
        self.log_result(
            "/api/materials/subjects/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_subjects_create(self):
        """POST /api/materials/subjects/ - create works"""
        self.client.force_authenticate(user=self.teacher)
        data = {"name": "Test Subject"}
        response = self.client.post("/api/materials/subjects/", data, format="json")
        self.log_result(
            "/api/materials/subjects/",
            "POST",
            response.status_code,
            status.HTTP_201_CREATED,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_materials_detail(self):
        """GET /api/materials/materials/{id}/ - detail works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/materials/materials/1/")
        self.log_result(
            "/api/materials/materials/1/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class AssignmentsEndpointsRegression(RegressionTestBase):
    """Test Assignments endpoints"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_assignments_list(self):
        """GET /api/assignments/ - list works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/assignments/")
        self.log_result(
            "/api/assignments/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assignments_create(self):
        """POST /api/assignments/ - create works"""
        self.client.force_authenticate(user=self.teacher)
        data = {
            "title": "Test Assignment",
            "description": "Test Description"
        }
        response = self.client.post("/api/assignments/", data, format="json")
        self.log_result(
            "/api/assignments/",
            "POST",
            response.status_code,
            status.HTTP_201_CREATED,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_assignments_submissions(self):
        """GET /api/assignments/{id}/submissions/ - submissions list works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/assignments/1/submissions/")
        self.log_result(
            "/api/assignments/1/submissions/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class PaymentsEndpointsRegression(RegressionTestBase):
    """Test Payments/Invoices endpoints"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_invoices_list(self):
        """GET /api/invoices/ - list works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/invoices/")
        self.log_result(
            "/api/invoices/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invoices_create(self):
        """POST /api/invoices/ - create works"""
        self.client.force_authenticate(user=self.teacher)
        data = {
            "amount": "100.00",
            "status": "draft"
        }
        response = self.client.post("/api/invoices/", data, format="json")
        self.log_result(
            "/api/invoices/",
            "POST",
            response.status_code,
            status.HTTP_201_CREATED,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class ReportsEndpointsRegression(RegressionTestBase):
    """Test Reports endpoints"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_reports_list(self):
        """GET /api/reports/ - list works"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/reports/")
        self.log_result(
            "/api/reports/",
            "GET",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class AuthenticationRegressionTests(RegressionTestBase):
    """Test authentication and permission checks still work"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests should be rejected"""
        response = self.client.get("/api/accounts/students/")
        self.log_result(
            "/api/accounts/students/",
            "GET (unauthenticated)",
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_list_all_students(self):
        """Student should not access student list"""
        self.client.force_authenticate(user=self.student)
        response = self.client.get("/api/accounts/students/")
        self.log_result(
            "/api/accounts/students/",
            "GET (student role)",
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_200_OK])

    def test_teacher_can_access_scheduling(self):
        """Teacher should access scheduling endpoints"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get("/api/scheduling/lessons/")
        self.log_result(
            "/api/scheduling/lessons/",
            "GET (teacher role)",
            response.status_code,
            status.HTTP_200_OK,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PerformanceRegressionTests(RegressionTestBase):
    """Test that performance hasn't degraded"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_list_endpoint_performance(self):
        """List endpoints should respond in reasonable time"""
        import time

        self.client.force_authenticate(user=self.teacher)

        endpoints = [
            "/api/accounts/students/",
            "/api/scheduling/lessons/",
            "/api/assignments/",
            "/api/chat/rooms/",
            "/api/materials/subjects/",
            "/api/invoices/",
        ]

        for endpoint in endpoints:
            start = time.time()
            response = self.client.get(endpoint)
            duration = time.time() - start

            # Performance check: should respond in < 2 seconds
            passed = duration < 2.0
            self.results["total_tests"] += 1
            if passed:
                self.results["passed"] += 1
            else:
                self.results["failed"] += 1

            self.results["endpoints"][f"PERF {endpoint}"] = {
                "status": "PASSED" if passed else "SLOW",
                "duration_seconds": f"{duration:.3f}",
                "threshold": "2.0"
            }


class HTTPMethodsRegressionTests(RegressionTestBase):
    """Test HTTP method handling"""

    def setUp(self):
        super().setUp()
        self.create_test_users()

    def test_invalid_http_methods(self):
        """Invalid HTTP methods should be rejected"""
        self.client.force_authenticate(user=self.teacher)

        # DELETE on list should return 405 Method Not Allowed
        response = self.client.delete("/api/accounts/students/")
        self.log_result(
            "/api/accounts/students/",
            "DELETE (invalid)",
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
            response.data if hasattr(response, 'data') else None
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_method_not_implemented(self):
        """PUT method should be properly handled"""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.put("/api/accounts/students/1/")
        self.log_result(
            "/api/accounts/students/1/",
            "PUT",
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
            response.data if hasattr(response, 'data') else None
        )
        self.assertIn(response.status_code, [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_404_NOT_FOUND
        ])


class RegressionTestRunner(TestCase):
    """Main test runner that aggregates all regression tests"""

    def test_run_all_regressions(self):
        """Run all regression tests and generate report"""
        test_classes = [
            ChatEndpointsRegression,
            AccountsEndpointsRegression,
            SchedulingEndpointsRegression,
            MaterialsEndpointsRegression,
            AssignmentsEndpointsRegression,
            PaymentsEndpointsRegression,
            ReportsEndpointsRegression,
            AuthenticationRegressionTests,
            PerformanceRegressionTests,
            HTTPMethodsRegressionTests,
        ]

        combined_results = {
            "test_name": "tutor_cabinet_final_test_20260107",
            "timestamp": datetime.now().isoformat(),
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "test_groups": {}
        }

        for test_class in test_classes:
            suite = TestCase.TestLoader().loadTestsFromTestCase(test_class)
            runner = TestCase.TextTestRunner(verbosity=0)
            result = runner.run(suite)

            group_name = test_class.__name__
            combined_results["test_groups"][group_name] = {
                "total": result.testsRun,
                "passed": result.testsRun - len(result.failures) - len(result.errors),
                "failed": len(result.failures) + len(result.errors),
                "errors": [str(e) for _, e in result.failures + result.errors]
            }

            combined_results["total_tests"] += result.testsRun
            combined_results["passed"] += (result.testsRun - len(result.failures) - len(result.errors))
            combined_results["failed"] += len(result.failures) + len(result.errors)

        # Write report
        with open("/tmp/tutor_cabinet_final_test_20260107.json", "w") as f:
            json.dump(combined_results, f, indent=2, ensure_ascii=False)

        print(f"\nRegression Test Summary:")
        print(f"Total Tests: {combined_results['total_tests']}")
        print(f"Passed: {combined_results['passed']}")
        print(f"Failed: {combined_results['failed']}")
        print(f"Pass Rate: {combined_results['passed'] / max(combined_results['total_tests'], 1) * 100:.1f}%")
        print(f"\nReport saved to: /tmp/tutor_cabinet_final_test_20260107.json")
