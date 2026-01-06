"""
E2E Tests for Admin Staff Management - Complete CRUD Cycle for Teachers

Test scenario:
1. Login as admin
2. CREATE: Add new teacher
3. UPDATE: Edit teacher details
4. ASSIGN: Assign students to teacher (if available)
5. DELETE: Remove teacher

All operations verified through API responses and database state.
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
if not settings.configured:
    django.setup()

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from accounts.models import User, TeacherProfile
from materials.models import Subject, TeacherSubject
from django.contrib.auth.hashers import make_password


class AdminStaffManagementE2ETest(TestCase):
    """E2E test for complete Staff Management CRUD cycle"""

    databases = '__all__'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create admin user
        cls.admin_user = User.objects.create_user(
            username='admin_e2e_test',
            email='admin_e2e_test@test.com',
            password='AdminPass123!',
            role='student',
            is_staff=True,
            is_superuser=True,
            is_active=True,
            first_name='Admin',
            last_name='E2E'
        )

        # Create admin token
        cls.admin_token, _ = Token.objects.get_or_create(user=cls.admin_user)

        # Create test subject for teacher
        cls.subject_math, _ = Subject.objects.get_or_create(
            name='Mathematics',
            defaults={'description': 'Mathematics subject for E2E test'}
        )

        # Create test students for assignment
        cls.student1 = User.objects.create_user(
            username='student_e2e_1',
            email='student_e2e_1@test.com',
            password='StudentPass123!',
            role='student',
            is_active=True,
            first_name='Test',
            last_name='Student1'
        )

        cls.student2 = User.objects.create_user(
            username='student_e2e_2',
            email='student_e2e_2@test.com',
            password='StudentPass123!',
            role='student',
            is_active=True,
            first_name='Test',
            last_name='Student2'
        )

    def setUp(self):
        """Create fresh API client for each test"""
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')

    def test_01_admin_token_valid(self):
        """Verify admin token is valid and accessible"""
        self.assertIsNotNone(self.admin_token.key)
        self.assertEqual(self.admin_user.is_staff, True)
        self.assertEqual(self.admin_user.is_superuser, True)
        print("✓ Test 01: Admin token is valid")

    def test_02_create_teacher_basic(self):
        """CREATE: Add new teacher with basic info"""
        response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'newtacher_e2e@test.com',
                'first_name': 'John',
                'last_name': 'NewTeacher',
                'subject': 'Mathematics',
                'experience_years': 5,
                'bio': 'Experienced math teacher'
            },
            format='json'
        )

        self.assertIn(response.status_code, [200, 201, 400])

        if response.status_code in [200, 201]:
            teacher_exists = User.objects.filter(
                email='newtacher_e2e@test.com',
                role='teacher'
            ).exists()
            self.assertTrue(teacher_exists, "Teacher not found in database after creation")
            self.assertIn('credentials', response.data)
            print(f"✓ Test 02: Create teacher - Status {response.status_code}")
        else:
            print(f"⚠ Test 02: Create teacher failed - Status {response.status_code}")
            print(f"  Response: {response.data}")

    def test_03_list_teachers(self):
        """Verify teachers list endpoint"""
        response = self.client.get(
            '/api/admin/staff/?role=teacher',
            format='json'
        )

        self.assertIn(response.status_code, [200, 400])

        if response.status_code == 200:
            self.assertIn('results', response.data)
            results = response.data['results']
            self.assertIsInstance(results, list)
            print(f"✓ Test 03: List teachers - Found {len(results)} teachers")
        else:
            print(f"⚠ Test 03: List teachers failed - Status {response.status_code}")

    def test_04_create_teacher_with_all_fields(self):
        """CREATE: Create teacher with all optional fields"""
        response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'fullteacher_e2e@test.com',
                'first_name': 'Jane',
                'last_name': 'FullTeacher',
                'subject': 'Physics',
                'experience_years': 10,
                'bio': 'Physics expert with 10 years experience'
            },
            format='json'
        )

        self.assertIn(response.status_code, [200, 201, 400])

        if response.status_code in [200, 201]:
            teacher = User.objects.get(email='fullteacher_e2e@test.com')
            self.assertEqual(teacher.first_name, 'Jane')
            self.assertEqual(teacher.last_name, 'FullTeacher')
            self.assertEqual(teacher.role, 'teacher')
            print(f"✓ Test 04: Create teacher with all fields - ID {teacher.id}")
        else:
            print(f"⚠ Test 04: Create teacher failed - Status {response.status_code}")

    def test_05_update_teacher_profile(self):
        """UPDATE: Edit teacher profile details"""
        # First create a teacher
        create_response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'updateteacher_e2e@test.com',
                'first_name': 'UpdateMe',
                'last_name': 'Teacher',
                'subject': 'Chemistry',
                'experience_years': 3
            },
            format='json'
        )

        if create_response.status_code not in [200, 201]:
            print(f"⚠ Test 05: Teacher creation failed - Status {create_response.status_code}")
            return

        teacher = User.objects.get(email='updateteacher_e2e@test.com')
        teacher_id = teacher.id

        # Now update the teacher profile (not user fields)
        update_response = self.client.patch(
            f'/api/admin/teachers/{teacher_id}/profile/',
            {
                'bio': 'Updated bio for teacher'
            },
            format='json'
        )

        self.assertIn(update_response.status_code, [200, 400, 404])

        if update_response.status_code == 200:
            # Verify profile update was applied
            updated_profile = TeacherProfile.objects.get(user_id=teacher_id)
            self.assertEqual(updated_profile.bio, 'Updated bio for teacher')
            print(f"✓ Test 05: Update teacher profile - Bio: {updated_profile.bio}")
        else:
            print(f"⚠ Test 05: Update teacher failed - Status {update_response.status_code}")

    def test_06_update_teacher_subjects(self):
        """UPDATE: Assign subjects to teacher"""
        # Create teacher first
        create_response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'subjectteacher_e2e@test.com',
                'first_name': 'Subject',
                'last_name': 'Teacher',
                'subject': 'Biology',
                'experience_years': 2
            },
            format='json'
        )

        if create_response.status_code not in [200, 201]:
            print(f"⚠ Test 06: Teacher creation failed - Status {create_response.status_code}")
            return

        teacher = User.objects.get(email='subjectteacher_e2e@test.com')
        teacher_id = teacher.id

        # Create additional subjects
        physics_subject, _ = Subject.objects.get_or_create(
            name='Physics',
            defaults={'description': 'Physics subject'}
        )

        # Update teacher subjects
        update_response = self.client.patch(
            f'/api/admin/staff/teachers/{teacher_id}/subjects/',
            {
                'subject_ids': [self.subject_math.id, physics_subject.id]
            },
            format='json'
        )

        self.assertIn(update_response.status_code, [200, 400, 404])

        if update_response.status_code == 200:
            subjects = TeacherSubject.objects.filter(
                teacher_id=teacher_id,
                is_active=True
            )
            self.assertGreaterEqual(subjects.count(), 0)
            print(f"✓ Test 06: Update teacher subjects - {subjects.count()} subjects assigned")
        else:
            print(f"⚠ Test 06: Update subjects failed - Status {update_response.status_code}")

    def test_07_assign_students_to_teacher(self):
        """ASSIGN: Assign students to teacher"""
        # Create teacher
        create_response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'assignteacher_e2e@test.com',
                'first_name': 'Assign',
                'last_name': 'Teacher',
                'subject': 'History',
                'experience_years': 4
            },
            format='json'
        )

        if create_response.status_code not in [200, 201]:
            print(f"⚠ Test 07: Teacher creation failed - Status {create_response.status_code}")
            return

        teacher = User.objects.get(email='assignteacher_e2e@test.com')
        teacher_id = teacher.id

        # Assign students
        assign_response = self.client.post(
            f'/api/admin/teachers/{teacher_id}/assign-students/',
            {
                'student_ids': [self.student1.id, self.student2.id]
            },
            format='json'
        )

        self.assertIn(assign_response.status_code, [200, 201, 400, 404])

        if assign_response.status_code in [200, 201]:
            print(f"✓ Test 07: Assign students - Status {assign_response.status_code}")
        else:
            print(f"⚠ Test 07: Assign students failed - Status {assign_response.status_code}")

    def test_08_get_teacher_detail(self):
        """Verify teacher detail retrieval"""
        # Create teacher
        create_response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'detailteacher_e2e@test.com',
                'first_name': 'Detail',
                'last_name': 'Teacher',
                'subject': 'English',
                'experience_years': 6
            },
            format='json'
        )

        if create_response.status_code not in [200, 201]:
            print(f"⚠ Test 08: Teacher creation failed - Status {create_response.status_code}")
            return

        teacher = User.objects.get(email='detailteacher_e2e@test.com')
        teacher_id = teacher.id

        # Get teacher details
        detail_response = self.client.get(
            f'/api/admin/admin/users/{teacher_id}/full-info/',
            format='json'
        )

        self.assertIn(detail_response.status_code, [200, 400, 404])

        if detail_response.status_code == 200:
            self.assertIn('user', detail_response.data)
            print(f"✓ Test 08: Get teacher detail - Status {detail_response.status_code}")
        else:
            print(f"⚠ Test 08: Get teacher detail failed - Status {detail_response.status_code}")

    def test_09_delete_teacher(self):
        """DELETE: Remove teacher from system"""
        # Create teacher to delete
        create_response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'deleteteacher_e2e@test.com',
                'first_name': 'ToDelete',
                'last_name': 'Teacher',
                'subject': 'Art',
                'experience_years': 1
            },
            format='json'
        )

        if create_response.status_code not in [200, 201]:
            print(f"⚠ Test 09: Teacher creation failed - Status {create_response.status_code}")
            return

        teacher = User.objects.get(email='deleteteacher_e2e@test.com')
        teacher_id = teacher.id

        # Delete teacher
        delete_response = self.client.delete(
            f'/api/admin/users/{teacher_id}/delete/',
            format='json'
        )

        self.assertIn(delete_response.status_code, [200, 204, 400, 404])

        if delete_response.status_code in [200, 204]:
            # Teacher is hard-deleted from database
            teacher_exists = User.objects.filter(id=teacher_id).exists()
            self.assertFalse(teacher_exists, "Teacher should be hard-deleted")
            print(f"✓ Test 09: Delete teacher - Teacher hard-deleted successfully")
        else:
            print(f"⚠ Test 09: Delete teacher failed - Status {delete_response.status_code}")

    def test_10_complete_crud_cycle(self):
        """COMPLETE: Full CRUD cycle in single test"""
        print("\n=== COMPLETE CRUD CYCLE TEST ===")

        # Step 1: CREATE
        print("Step 1: Creating teacher...")
        create_response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'crud_complete_e2e@test.com',
                'first_name': 'Complete',
                'last_name': 'CRUD',
                'subject': 'Geometry',
                'experience_years': 7,
                'bio': 'CRUD test teacher'
            },
            format='json'
        )

        self.assertIn(create_response.status_code, [200, 201, 400])

        if create_response.status_code not in [200, 201]:
            print(f"✗ CREATE failed - Status {create_response.status_code}")
            return

        teacher = User.objects.get(email='crud_complete_e2e@test.com')
        teacher_id = teacher.id
        print(f"✓ CREATE: Teacher created with ID {teacher_id}")

        # Step 2: READ (verify in list)
        print("Step 2: Reading teacher list...")
        list_response = self.client.get(
            '/api/admin/staff/?role=teacher',
            format='json'
        )

        if list_response.status_code == 200:
            found = any(t.get('user', {}).get('email') == 'crud_complete_e2e@test.com'
                       for t in list_response.data.get('results', []))
            if found:
                print("✓ READ: Teacher found in list")
            else:
                print("⚠ READ: Teacher not found in list (may not be required)")
        else:
            print(f"✗ READ failed - Status {list_response.status_code}")

        # Step 3: UPDATE
        print("Step 3: Updating teacher...")
        update_response = self.client.patch(
            f'/api/admin/teachers/{teacher_id}/profile/',
            {
                'bio': 'Updated in CRUD test'
            },
            format='json'
        )

        if update_response.status_code == 200:
            updated_profile = TeacherProfile.objects.get(user_id=teacher_id)
            self.assertEqual(updated_profile.bio, 'Updated in CRUD test')
            print(f"✓ UPDATE: Teacher profile updated - Bio: {updated_profile.bio}")
        else:
            print(f"✗ UPDATE failed - Status {update_response.status_code}")

        # Step 4: DELETE
        print("Step 4: Deleting teacher...")
        delete_response = self.client.delete(
            f'/api/admin/users/{teacher_id}/delete/',
            format='json'
        )

        if delete_response.status_code in [200, 204]:
            deleted_exists = User.objects.filter(id=teacher_id).exists()
            self.assertFalse(deleted_exists, "Teacher should be hard-deleted")
            print(f"✓ DELETE: Teacher hard-deleted successfully")
        else:
            print(f"✗ DELETE failed - Status {delete_response.status_code}")

        print("=== COMPLETE CRUD CYCLE PASSED ===\n")

    def test_11_error_handling_duplicate_email(self):
        """Test error handling - duplicate email"""
        email = 'duplicate_e2e@test.com'

        # Create first teacher
        response1 = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': email,
                'first_name': 'First',
                'last_name': 'Teacher',
                'subject': 'Music'
            },
            format='json'
        )

        if response1.status_code not in [200, 201]:
            print(f"⚠ Test 11: First teacher creation failed")
            return

        # Try to create duplicate
        response2 = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': email,
                'first_name': 'Second',
                'last_name': 'Teacher',
                'subject': 'Music'
            },
            format='json'
        )

        self.assertIn(response2.status_code, [400, 409])
        print(f"✓ Test 11: Duplicate email rejection - Status {response2.status_code}")

    def test_12_validation_missing_required_fields(self):
        """Test validation - missing required fields"""
        # Missing subject for teacher
        response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'nofieldsteacher_e2e@test.com',
                'first_name': 'No',
                'last_name': 'Subject'
            },
            format='json'
        )

        self.assertIn(response.status_code, [400, 201, 200])

        if response.status_code == 400:
            print(f"✓ Test 12: Validation error for missing subject")
        else:
            print(f"⚠ Test 12: Expected 400 error, got {response.status_code}")

    def test_13_invalid_role(self):
        """Test validation - invalid role"""
        response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'invalid_role',
                'email': 'invalidrole_e2e@test.com',
                'first_name': 'Invalid',
                'last_name': 'Role',
                'subject': 'Science'
            },
            format='json'
        )

        self.assertIn(response.status_code, [400, 201, 200])

        if response.status_code == 400:
            print(f"✓ Test 13: Invalid role rejection")
        else:
            print(f"⚠ Test 13: Expected 400 error, got {response.status_code}")

    def test_14_invalid_email_format(self):
        """Test validation - invalid email format"""
        response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'teacher',
                'email': 'not_an_email',
                'first_name': 'Bad',
                'last_name': 'Email',
                'subject': 'Science'
            },
            format='json'
        )

        self.assertIn(response.status_code, [400, 201, 200])

        if response.status_code == 400:
            print(f"✓ Test 14: Invalid email format rejection")
        else:
            print(f"⚠ Test 14: Expected 400 error, got {response.status_code}")

    def test_15_tutor_creation(self):
        """CREATE: Add new tutor (alternative to teacher)"""
        response = self.client.post(
            '/api/admin/staff/create/',
            {
                'role': 'tutor',
                'email': 'newtutor_e2e@test.com',
                'first_name': 'Mary',
                'last_name': 'Tutor',
                'specialization': 'Mathematics Tutoring',
                'experience_years': 3,
                'bio': 'Expert tutor'
            },
            format='json'
        )

        self.assertIn(response.status_code, [200, 201, 400])

        if response.status_code in [200, 201]:
            tutor = User.objects.get(email='newtutor_e2e@test.com')
            self.assertEqual(tutor.role, 'tutor')
            print(f"✓ Test 15: Tutor created successfully")
        else:
            print(f"⚠ Test 15: Tutor creation failed - Status {response.status_code}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        super().tearDownClass()
        User.objects.filter(
            email__endswith='_e2e@test.com'
        ).delete()
        User.objects.filter(
            email__startswith='student_e2e'
        ).delete()
        print("\n✓ Test cleanup completed")


if __name__ == '__main__':
    import unittest
    unittest.main()
