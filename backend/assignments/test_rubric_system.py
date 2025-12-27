"""
T_ASSIGN_004: Tests for Grading Rubric System

Comprehensive tests for:
- Rubric CRUD operations
- Criterion creation and validation
- Point scales validation
- Template cloning
- Permission checks (teacher only)
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from assignments.models import GradingRubric, RubricCriterion

User = get_user_model()


class TestGradingRubricModel:
    """Test GradingRubric model functionality"""

    @pytest.fixture
    def teacher(self):
        """Create a teacher user"""
        return User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Teacher",
            role="teacher"
        )

    @pytest.fixture
    def rubric(self, teacher):
        """Create a test rubric"""
        return GradingRubric.objects.create(
            name="Assessment Rubric",
            description="Test rubric for assignments",
            created_by=teacher,
            is_template=False,
            total_points=100
        )

    def test_create_rubric(self, teacher):
        """Test creating a basic rubric"""
        rubric = GradingRubric.objects.create(
            name="Test Rubric",
            description="Test description",
            created_by=teacher,
            is_template=True,
            total_points=50
        )
        assert rubric.id is not None
        assert rubric.name == "Test Rubric"
        assert rubric.total_points == 50
        assert rubric.is_template is True
        assert rubric.is_deleted is False

    def test_rubric_string_representation(self, rubric):
        """Test rubric __str__ method"""
        assert str(rubric) == "Assessment Rubric (100 баллов)"

    def test_create_rubric_with_criteria(self, teacher):
        """Test creating rubric and adding criteria"""
        rubric = GradingRubric.objects.create(
            name="Complete Rubric",
            created_by=teacher,
            is_template=True,
            total_points=100
        )

        criterion = RubricCriterion.objects.create(
            rubric=rubric,
            name="Content Quality",
            description="Quality of assignment content",
            max_points=50,
            point_scales=[[50, "Excellent"], [40, "Good"], [30, "Fair"]],
            order=1
        )

        assert criterion.rubric == rubric
        assert criterion.name == "Content Quality"
        assert rubric.criteria.count() == 1

    def test_clone_rubric(self, teacher, rubric):
        """Test cloning a rubric with criteria"""
        # Add criteria to original rubric
        RubricCriterion.objects.create(
            rubric=rubric,
            name="Criterion 1",
            description="First criterion",
            max_points=50,
            point_scales=[[50, "Excellent"], [25, "Good"]],
            order=1
        )
        RubricCriterion.objects.create(
            rubric=rubric,
            name="Criterion 2",
            description="Second criterion",
            max_points=50,
            point_scales=[[50, "Excellent"], [25, "Good"]],
            order=2
        )

        # Create another teacher for cloning
        other_teacher = User.objects.create_user(
            email="other@test.com",
            password="TestPass123!",
            role="teacher"
        )

        # Clone the rubric
        cloned_rubric = rubric.clone(other_teacher)

        # Verify cloned rubric
        assert cloned_rubric.id != rubric.id
        assert cloned_rubric.created_by == other_teacher
        assert cloned_rubric.name == f"{rubric.name} (копия)"
        assert cloned_rubric.total_points == rubric.total_points
        assert cloned_rubric.criteria.count() == 2

        # Verify criteria are cloned
        cloned_criteria = cloned_rubric.criteria.all()
        original_criteria = rubric.criteria.all()
        assert cloned_criteria.count() == original_criteria.count()

    def test_soft_delete_rubric(self, rubric):
        """Test soft deletion of rubric"""
        assert rubric.is_deleted is False

        rubric.is_deleted = True
        rubric.save()

        rubric.refresh_from_db()
        assert rubric.is_deleted is True

        # Verify soft deleted rubric is excluded from queryset
        assert GradingRubric.objects.filter(is_deleted=False).count() == 0


class TestRubricCriterionModel:
    """Test RubricCriterion model functionality"""

    @pytest.fixture
    def teacher(self):
        """Create a teacher user"""
        return User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

    @pytest.fixture
    def rubric(self, teacher):
        """Create a test rubric"""
        return GradingRubric.objects.create(
            name="Test Rubric",
            created_by=teacher,
            is_template=True,
            total_points=100
        )

    def test_create_criterion_with_scales(self, rubric):
        """Test creating criterion with point scales"""
        criterion = RubricCriterion.objects.create(
            rubric=rubric,
            name="Test Criterion",
            description="Test description",
            max_points=50,
            point_scales=[
                [50, "Excellent"],
                [40, "Good"],
                [30, "Fair"],
                [20, "Poor"]
            ],
            order=1
        )

        assert criterion.id is not None
        assert criterion.name == "Test Criterion"
        assert criterion.max_points == 50
        assert len(criterion.point_scales) == 4

    def test_criterion_string_representation(self, rubric):
        """Test criterion __str__ method"""
        criterion = RubricCriterion.objects.create(
            rubric=rubric,
            name="Quality",
            description="Content quality",
            max_points=50,
            point_scales=[[50, "Excellent"]],
            order=1
        )

        assert str(criterion) == f"{rubric.name} - Quality"

    def test_validate_point_scales_invalid_list(self, rubric):
        """Test validation of invalid point scales"""
        with pytest.raises(ValidationError):
            criterion = RubricCriterion(
                rubric=rubric,
                name="Invalid",
                description="Invalid scales",
                max_points=50,
                point_scales="not a list"
            )
            criterion.clean()

    def test_validate_point_scales_empty(self, rubric):
        """Test validation with empty point scales"""
        with pytest.raises(ValidationError):
            criterion = RubricCriterion(
                rubric=rubric,
                name="Empty",
                description="Empty scales",
                max_points=50,
                point_scales=[]
            )
            criterion.clean()

    def test_validate_point_scales_invalid_format(self, rubric):
        """Test validation with invalid scale format"""
        with pytest.raises(ValidationError):
            criterion = RubricCriterion(
                rubric=rubric,
                name="Invalid Format",
                description="Invalid format",
                max_points=50,
                point_scales=[[50]]  # Missing description
            )
            criterion.clean()

    def test_validate_points_exceed_max(self, rubric):
        """Test validation when points exceed max_points"""
        with pytest.raises(ValidationError):
            criterion = RubricCriterion(
                rubric=rubric,
                name="Excess Points",
                description="Points exceed max",
                max_points=50,
                point_scales=[[100, "Too Much"]]
            )
            criterion.clean()

    def test_validate_empty_description(self, rubric):
        """Test validation with empty description"""
        with pytest.raises(ValidationError):
            criterion = RubricCriterion(
                rubric=rubric,
                name="Empty Desc",
                description="Empty",
                max_points=50,
                point_scales=[[50, ""]]
            )
            criterion.clean()

    def test_criterion_unique_constraint(self, rubric):
        """Test unique constraint on criterion names within rubric"""
        RubricCriterion.objects.create(
            rubric=rubric,
            name="Unique Criterion",
            description="First",
            max_points=50,
            point_scales=[[50, "Excellent"]],
            order=1
        )

        with pytest.raises(Exception):  # IntegrityError
            RubricCriterion.objects.create(
                rubric=rubric,
                name="Unique Criterion",  # Same name
                description="Second",
                max_points=50,
                point_scales=[[50, "Excellent"]],
                order=2
            )


class TestGradingRubricAPI:
    """Test Grading Rubric API endpoints"""

    @pytest.fixture
    def client(self):
        """Create API client"""
        return APIClient()

    @pytest.fixture
    def teacher(self):
        """Create a teacher user"""
        return User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Teacher",
            role="teacher"
        )

    @pytest.fixture
    def student(self):
        """Create a student user"""
        return User.objects.create_user(
            email="student@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Student",
            role="student"
        )

    @pytest.fixture
    def rubric(self, teacher):
        """Create a test rubric"""
        rubric = GradingRubric.objects.create(
            name="Test Rubric",
            description="Test description",
            created_by=teacher,
            is_template=True,
            total_points=100
        )

        RubricCriterion.objects.create(
            rubric=rubric,
            name="Criterion 1",
            description="First criterion",
            max_points=50,
            point_scales=[[50, "Excellent"], [25, "Good"]],
            order=1
        )

        return rubric

    def test_create_rubric_as_teacher(self, client, teacher):
        """Test creating a rubric as teacher"""
        client.force_authenticate(user=teacher)

        data = {
            "name": "New Rubric",
            "description": "Test rubric",
            "is_template": True,
            "total_points": 100,
            "criteria": [
                {
                    "name": "Criterion 1",
                    "description": "First criterion",
                    "max_points": 50,
                    "point_scales": [[50, "Excellent"], [25, "Good"]],
                    "order": 1
                },
                {
                    "name": "Criterion 2",
                    "description": "Second criterion",
                    "max_points": 50,
                    "point_scales": [[50, "Excellent"], [25, "Good"]],
                    "order": 2
                }
            ]
        }

        response = client.post("/api/rubrics/", data, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "New Rubric"
        assert response.data["total_points"] == 100

        # Verify criteria were created
        rubric = GradingRubric.objects.get(name="New Rubric")
        assert rubric.criteria.count() == 2

    def test_create_rubric_as_student_forbidden(self, client, student):
        """Test that students cannot create rubrics"""
        client.force_authenticate(user=student)

        data = {
            "name": "Student Rubric",
            "description": "Should fail",
            "is_template": False,
            "total_points": 100
        }

        response = client.post("/api/rubrics/", data, format="json")

        assert response.status_code == 403

    def test_list_rubrics(self, client, teacher, rubric):
        """Test listing rubrics"""
        client.force_authenticate(user=teacher)

        response = client.get("/api/rubrics/")

        assert response.status_code == 200
        assert len(response.data["results"]) >= 1
        assert any(r["name"] == "Test Rubric" for r in response.data["results"])

    def test_retrieve_rubric_detail(self, client, teacher, rubric):
        """Test retrieving rubric detail"""
        client.force_authenticate(user=teacher)

        response = client.get(f"/api/rubrics/{rubric.id}/")

        assert response.status_code == 200
        assert response.data["name"] == "Test Rubric"
        assert response.data["total_points"] == 100
        assert len(response.data["criteria"]) == 1

    def test_update_rubric(self, client, teacher, rubric):
        """Test updating rubric"""
        client.force_authenticate(user=teacher)

        data = {
            "name": "Updated Rubric",
            "description": "Updated description",
            "is_template": False
        }

        response = client.patch(f"/api/rubrics/{rubric.id}/", data, format="json")

        assert response.status_code == 200
        assert response.data["name"] == "Updated Rubric"

    def test_delete_rubric_soft_delete(self, client, teacher, rubric):
        """Test soft deletion of rubric"""
        client.force_authenticate(user=teacher)

        response = client.delete(f"/api/rubrics/{rubric.id}/")

        assert response.status_code == 204

        # Verify soft deletion
        rubric.refresh_from_db()
        assert rubric.is_deleted is True

    def test_list_template_rubrics(self, client, teacher, rubric):
        """Test listing template rubrics"""
        client.force_authenticate(user=teacher)

        response = client.get("/api/rubrics/templates/")

        assert response.status_code == 200
        assert any(r["name"] == "Test Rubric" for r in response.data["results"])

    def test_clone_rubric(self, client, teacher, rubric):
        """Test cloning a rubric"""
        # Create another teacher for cloning
        other_teacher = User.objects.create_user(
            email="other@test.com",
            password="TestPass123!",
            role="teacher"
        )

        client.force_authenticate(user=other_teacher)

        response = client.post(f"/api/rubrics/{rubric.id}/clone/")

        assert response.status_code == 201
        assert response.data["name"] == f"{rubric.name} (копия)"
        assert response.data["created_by"] == other_teacher.id

    def test_permission_update_other_teacher_rubric(self, client, teacher, rubric):
        """Test that teachers cannot update other teacher's rubrics"""
        other_teacher = User.objects.create_user(
            email="other@test.com",
            password="TestPass123!",
            role="teacher"
        )

        client.force_authenticate(user=other_teacher)

        data = {"name": "Hacked Rubric"}

        response = client.patch(f"/api/rubrics/{rubric.id}/", data, format="json")

        assert response.status_code == 403

    def test_permission_delete_other_teacher_rubric(self, client, teacher, rubric):
        """Test that teachers cannot delete other teacher's rubrics"""
        other_teacher = User.objects.create_user(
            email="other@test.com",
            password="TestPass123!",
            role="teacher"
        )

        client.force_authenticate(user=other_teacher)

        response = client.delete(f"/api/rubrics/{rubric.id}/")

        assert response.status_code == 403


class TestRubricCriterionAPI:
    """Test Rubric Criterion API endpoints"""

    @pytest.fixture
    def client(self):
        """Create API client"""
        return APIClient()

    @pytest.fixture
    def teacher(self):
        """Create a teacher user"""
        return User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

    @pytest.fixture
    def rubric(self, teacher):
        """Create a test rubric"""
        return GradingRubric.objects.create(
            name="Test Rubric",
            created_by=teacher,
            is_template=True,
            total_points=100
        )

    def test_create_criterion(self, client, teacher, rubric):
        """Test creating a criterion"""
        client.force_authenticate(user=teacher)

        data = {
            "rubric": rubric.id,
            "name": "New Criterion",
            "description": "New criterion description",
            "max_points": 50,
            "point_scales": [[50, "Excellent"], [25, "Good"]],
            "order": 1
        }

        response = client.post("/api/criteria/", data, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "New Criterion"

    def test_list_criteria_by_rubric(self, client, teacher, rubric):
        """Test listing criteria for a rubric"""
        RubricCriterion.objects.create(
            rubric=rubric,
            name="Criterion 1",
            description="First",
            max_points=50,
            point_scales=[[50, "Excellent"]],
            order=1
        )

        client.force_authenticate(user=teacher)

        response = client.get(f"/api/criteria/?rubric={rubric.id}")

        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_permission_create_criterion_other_rubric(self, client, teacher):
        """Test that teachers cannot add criteria to other's rubrics"""
        other_teacher = User.objects.create_user(
            email="other@test.com",
            password="TestPass123!",
            role="teacher"
        )

        other_rubric = GradingRubric.objects.create(
            name="Other Rubric",
            created_by=other_teacher,
            is_template=True,
            total_points=100
        )

        client.force_authenticate(user=teacher)

        data = {
            "rubric": other_rubric.id,
            "name": "Hacked Criterion",
            "description": "Should fail",
            "max_points": 50,
            "point_scales": [[50, "Excellent"]],
            "order": 1
        }

        response = client.post("/api/criteria/", data, format="json")

        assert response.status_code == 403


class TestRubricAssignmentIntegration:
    """Test integration of rubrics with assignments"""

    @pytest.fixture
    def teacher(self):
        """Create a teacher user"""
        return User.objects.create_user(
            email="teacher@test.com",
            password="TestPass123!",
            role="teacher"
        )

    @pytest.fixture
    def rubric(self, teacher):
        """Create a test rubric"""
        return GradingRubric.objects.create(
            name="Test Rubric",
            created_by=teacher,
            is_template=True,
            total_points=100
        )

    def test_assignment_can_reference_rubric(self, teacher, rubric):
        """Test that assignments can reference rubrics"""
        from assignments.models import Assignment
        from materials.models import Subject
        from django.utils import timezone

        subject = Subject.objects.create(
            name="Test Subject",
            created_by=teacher
        )

        assignment = Assignment.objects.create(
            title="Test Assignment",
            description="Test",
            author=teacher,
            subject=subject,
            rubric=rubric,
            start_date=timezone.now(),
            due_date=timezone.now()
        )

        assert assignment.rubric == rubric

    def test_rubric_deletion_does_not_break_assignment(self, teacher, rubric):
        """Test that soft deleting rubric doesn't delete assignments"""
        from assignments.models import Assignment
        from materials.models import Subject
        from django.utils import timezone

        subject = Subject.objects.create(
            name="Test Subject",
            created_by=teacher
        )

        assignment = Assignment.objects.create(
            title="Test Assignment",
            description="Test",
            author=teacher,
            subject=subject,
            rubric=rubric,
            start_date=timezone.now(),
            due_date=timezone.now()
        )

        # Soft delete the rubric
        rubric.is_deleted = True
        rubric.save()

        # Assignment should still exist
        assignment.refresh_from_db()
        assert assignment.id is not None
        assert assignment.rubric_id is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
