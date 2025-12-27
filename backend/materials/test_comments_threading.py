"""
Tests for Material Comment Threading (T_MAT_007)

Tests:
- Creating top-level comments
- Creating replies to comments
- Depth limit validation (max 3 levels)
- Reply count annotation
- Author can delete own comment
- Teacher can delete any comment
- Pagination for replies
- Sorting by creation date (oldest first)
- Soft delete verification
- Moderation workflow
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from materials.models import Material, MaterialComment, Subject

User = get_user_model()


class MaterialCommentThreadingTestCase(APITestCase):
    """
    Test suite for Material Comment Threading (T_MAT_007)
    """

    def setUp(self):
        """Set up test data"""
        # Create users
        self.student = User.objects.create_user(
            email="student@test.com",
            password="testpass123",
            role="student",
            first_name="Student",
            last_name="User",
        )
        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role="teacher",
            first_name="Teacher",
            last_name="User",
        )
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            role="admin",
            first_name="Admin",
            last_name="User",
        )

        # Create subject
        self.subject = Subject.objects.create(
            name="Test Subject",
            description="Test subject for comments",
        )

        # Create material
        self.material = Material.objects.create(
            title="Test Material",
            description="Test material for comment threading",
            content="This is test content",
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE,
        )

        self.client = APIClient()

    def test_create_top_level_comment(self):
        """Test creating a top-level comment"""
        self.client.force_authenticate(user=self.student)

        data = {
            "material": self.material.id,
            "content": "This is a top-level comment",
            "is_question": False,
        }

        response = self.client.post(
            f"/api/materials/{self.material.id}/comments/",
            data=data,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["content"] == "This is a top-level comment"
        assert response.data["author_id"] == self.student.id
        assert response.data["parent_comment"] is None
        assert response.data["reply_count"] == 0

    def test_create_reply_to_comment(self):
        """Test creating a reply to a comment"""
        # Create top-level comment
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Original comment",
        )

        self.client.force_authenticate(user=self.student)

        data = {
            "material": self.material.id,
            "content": "This is a reply",
            "is_question": False,
            "parent_comment": comment.id,
        }

        response = self.client.post(
            f"/api/materials/{self.material.id}/comments/",
            data=data,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["parent_comment"] == comment.id
        assert response.data["content"] == "This is a reply"

    def test_create_reply_via_create_reply_action(self):
        """Test creating a reply using the create_reply action"""
        # Create top-level comment
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Original comment",
        )

        self.client.force_authenticate(user=self.student)

        data = {
            "content": "Reply via action",
            "is_question": False,
        }

        response = self.client.post(
            f"/api/materials/{self.material.id}/comments/{comment.id}/create_reply/",
            data=data,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["parent_comment"] == comment.id
        assert response.data["content"] == "Reply via action"

    def test_depth_limit_validation(self):
        """Test that maximum depth of 3 levels is enforced"""
        # Create level 1 comment
        level1 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Level 1 comment",
        )

        # Create level 2 comment (reply to level 1)
        level2 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Level 2 comment",
            parent_comment=level1,
        )

        # Create level 3 comment (reply to level 2)
        level3 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Level 3 comment",
            parent_comment=level2,
        )

        # Verify get_depth() method
        assert level1.get_depth() == 1
        assert level2.get_depth() == 2
        assert level3.get_depth() == 3

        # Try to create level 4 (should fail)
        self.client.force_authenticate(user=self.student)

        data = {
            "content": "Level 4 comment (should fail)",
            "is_question": False,
        }

        response = self.client.post(
            f"/api/materials/{self.material.id}/comments/{level3.id}/create_reply/",
            data=data,
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "максимальная глубина вложенности" in response.data["error"].lower()
        )

    def test_reply_count_annotation(self):
        """Test that reply_count is correctly calculated"""
        # Create top-level comment
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Original comment",
        )

        # Create 3 replies
        for i in range(3):
            MaterialComment.objects.create(
                material=self.material,
                author=self.student,
                content=f"Reply {i+1}",
                parent_comment=comment,
            )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/",
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"][0]["reply_count"] == 3

    def test_get_replies_with_pagination(self):
        """Test getting replies with pagination"""
        # Create top-level comment
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Original comment",
        )

        # Create 15 replies to test pagination
        for i in range(15):
            MaterialComment.objects.create(
                material=self.material,
                author=self.student,
                content=f"Reply {i+1}",
                parent_comment=comment,
            )

        self.client.force_authenticate(user=self.student)

        # Test first page (default 10 items)
        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/{comment.id}/replies/",
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 15
        assert len(response.data["results"]) == 10  # Default page size
        assert response.data["next"] is not None  # Has next page

        # Test second page
        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/{comment.id}/replies/?page=2",
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 5
        assert response.data["previous"] is not None  # Has previous page

    def test_replies_sorted_by_creation_date(self):
        """Test that replies are sorted by creation date (oldest first)"""
        # Create top-level comment
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Original comment",
        )

        # Create replies in specific order
        reply1 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Reply 1",
            parent_comment=comment,
        )

        reply2 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Reply 2",
            parent_comment=comment,
        )

        reply3 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Reply 3",
            parent_comment=comment,
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/{comment.id}/replies/",
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3
        # Check order (oldest first)
        assert response.data["results"][0]["id"] == reply1.id
        assert response.data["results"][1]["id"] == reply2.id
        assert response.data["results"][2]["id"] == reply3.id

    def test_author_can_delete_own_comment(self):
        """Test that comment author can delete their own comment"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Student's comment",
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.delete(
            f"/api/materials/{self.material.id}/comments/{comment.id}/",
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify soft delete
        comment.refresh_from_db()
        assert comment.is_deleted is True
        assert comment.deleted_at is not None

    def test_author_cannot_delete_others_comment(self):
        """Test that author cannot delete others' comments"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Student's comment",
        )

        # Another student tries to delete
        other_student = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            role="student",
        )
        self.client.force_authenticate(user=other_student)

        response = self.client.delete(
            f"/api/materials/{self.material.id}/comments/{comment.id}/",
            format="json",
        )

        # Should fail (403 Forbidden)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_teacher_can_delete_any_comment(self):
        """Test that teacher can delete any comment"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Student's comment",
        )

        self.client.force_authenticate(user=self.teacher)

        response = self.client.delete(
            f"/api/materials/{self.material.id}/comments/{comment.id}/",
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        comment.refresh_from_db()
        assert comment.is_deleted is True

    def test_admin_can_delete_any_comment(self):
        """Test that admin can delete any comment"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Student's comment",
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            f"/api/materials/{self.material.id}/comments/{comment.id}/",
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        comment.refresh_from_db()
        assert comment.is_deleted is True

    def test_deleted_comments_not_shown_in_list(self):
        """Test that deleted comments are not shown in list"""
        # Create 3 comments
        comment1 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Comment 1",
        )
        comment2 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Comment 2",
        )
        comment3 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Comment 3",
        )

        # Delete comment2
        comment2.delete()

        self.client.force_authenticate(user=self.student)

        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/",
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        ids = [c["id"] for c in response.data["results"]]
        assert comment1.id in ids
        assert comment3.id in ids
        assert comment2.id not in ids

    def test_can_delete_flag_in_response(self):
        """Test that can_delete flag is correctly set in response"""
        # Student creates a comment
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Student's comment",
        )

        # Student views - can delete
        self.client.force_authenticate(user=self.student)
        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/",
            format="json",
        )
        assert response.data["results"][0]["can_delete"] is True

        # Other student views - cannot delete
        other_student = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            role="student",
        )
        self.client.force_authenticate(user=other_student)
        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/",
            format="json",
        )
        assert response.data["results"][0]["can_delete"] is False

        # Teacher views - can delete
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/",
            format="json",
        )
        assert response.data["results"][0]["can_delete"] is True

    def test_can_reply_flag_in_response(self):
        """Test that can_reply flag is correctly set based on depth"""
        # Create level 1, 2, 3 comments
        level1 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Level 1",
        )

        level2 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Level 2",
            parent_comment=level1,
        )

        level3 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Level 3",
            parent_comment=level2,
        )

        self.client.force_authenticate(user=self.student)

        # Level 1 - can reply
        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/",
            format="json",
        )
        assert response.data["results"][0]["can_reply"] is True

        # Level 2 - can reply
        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/{level1.id}/replies/",
            format="json",
        )
        assert response.data["results"][0]["can_reply"] is True

        # Level 3 - cannot reply
        response = self.client.get(
            f"/api/materials/{self.material.id}/comments/{level2.id}/replies/",
            format="json",
        )
        assert response.data["results"][0]["can_reply"] is False

    def test_comment_approval_workflow(self):
        """Test comment approval workflow"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Student's comment",
            is_approved=True,  # Default is approved
        )

        # Teacher disapproves
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            f"/api/materials/{self.material.id}/comments/{comment.id}/disapprove/",
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        comment.refresh_from_db()
        assert comment.is_approved is False

        # Teacher approves again
        response = self.client.post(
            f"/api/materials/{self.material.id}/comments/{comment.id}/approve/",
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        comment.refresh_from_db()
        assert comment.is_approved is True

    def test_only_admin_can_approve(self):
        """Test that only admin/teacher can approve comments"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content="Student's comment",
        )

        # Student tries to approve - should fail
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f"/api/materials/{self.material.id}/comments/{comment.id}/approve/",
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class MaterialCommentModelTests(TestCase):
    """Unit tests for MaterialComment model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="test@test.com",
            password="testpass123",
            role="student",
        )
        self.subject = Subject.objects.create(name="Test Subject")
        self.material = Material.objects.create(
            title="Test Material",
            content="Test content",
            author=self.user,
            subject=self.subject,
        )

    def test_get_depth_level_1(self):
        """Test get_depth for level 1 comment"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Level 1",
        )
        assert comment.get_depth() == 1

    def test_get_depth_level_2(self):
        """Test get_depth for level 2 comment"""
        level1 = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Level 1",
        )
        level2 = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Level 2",
            parent_comment=level1,
        )
        assert level2.get_depth() == 2

    def test_get_depth_level_3(self):
        """Test get_depth for level 3 comment"""
        level1 = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Level 1",
        )
        level2 = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Level 2",
            parent_comment=level1,
        )
        level3 = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Level 3",
            parent_comment=level2,
        )
        assert level3.get_depth() == 3

    def test_get_reply_count(self):
        """Test get_reply_count method"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Parent comment",
        )

        # No replies initially
        assert comment.get_reply_count() == 0

        # Add 3 replies
        for i in range(3):
            MaterialComment.objects.create(
                material=self.material,
                author=self.user,
                content=f"Reply {i+1}",
                parent_comment=comment,
            )

        assert comment.get_reply_count() == 3

    def test_soft_delete(self):
        """Test soft delete functionality"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Test comment",
        )

        assert comment.is_deleted is False
        assert comment.deleted_at is None

        # Delete comment
        comment.delete()

        comment.refresh_from_db()
        assert comment.is_deleted is True
        assert comment.deleted_at is not None

        # Comment should still exist in database
        assert MaterialComment.objects.filter(id=comment.id).exists()

    def test_clean_depth_validation(self):
        """Test depth validation in clean method"""
        from django.core.exceptions import ValidationError

        level1 = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Level 1",
        )
        level2 = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Level 2",
            parent_comment=level1,
        )
        level3 = MaterialComment.objects.create(
            material=self.material,
            author=self.user,
            content="Level 3",
            parent_comment=level2,
        )

        # Try to create level 4
        level4 = MaterialComment(
            material=self.material,
            author=self.user,
            content="Level 4",
            parent_comment=level3,
        )

        with self.assertRaises(ValidationError):
            level4.clean()
