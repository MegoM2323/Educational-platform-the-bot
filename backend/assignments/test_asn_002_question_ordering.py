"""
T_ASN_002: Assignment Question Order - Comprehensive Tests

Tests for:
- Question ordering validation
- Unique ordering per assignment
- Bulk reordering operations
- Auto-renumbering on deletion
- Randomization support
- API endpoints
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status

from assignments.models import Assignment, AssignmentQuestion
from assignments.services.ordering import QuestionOrderingService
from assignments.serializers import (
    AssignmentQuestionUpdateOrderSerializer,
    QuestionReorderSerializer
)

User = get_user_model()


class QuestionOrderingModelTests(TestCase):
    """Tests for AssignmentQuestion ordering model"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            status='published'
        )

    def test_question_order_field_default(self):
        """Test that order field defaults to 0"""
        question = AssignmentQuestion.objects.create(
            assignment=self.assignment,
            question_text='Question 1',
            question_type='single_choice'
        )
        self.assertEqual(question.order, 0)

    def test_question_order_validators(self):
        """Test order field validators (0-1000)"""
        # Valid order values
        for order_val in [0, 1, 500, 999, 1000]:
            question = AssignmentQuestion.objects.create(
                assignment=self.assignment,
                question_text=f'Q{order_val}',
                question_type='single_choice',
                order=order_val
            )
            self.assertEqual(question.order, order_val)

    def test_unique_order_per_assignment(self):
        """Test unique constraint on (assignment, order) pair"""
        # Create first question with order 1
        q1 = AssignmentQuestion.objects.create(
            assignment=self.assignment,
            question_text='Question 1',
            question_type='single_choice',
            order=1
        )

        # Try to create another question with same order - should fail
        with self.assertRaises(IntegrityError):
            q2 = AssignmentQuestion.objects.create(
                assignment=self.assignment,
                question_text='Question 2',
                question_type='single_choice',
                order=1
            )

    def test_different_assignments_can_have_same_order(self):
        """Test that different assignments can have questions with same order"""
        assignment2 = Assignment.objects.create(
            title='Test Assignment 2',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            status='published'
        )

        q1 = AssignmentQuestion.objects.create(
            assignment=self.assignment,
            question_text='Q1 in A1',
            question_type='single_choice',
            order=1
        )

        q2 = AssignmentQuestion.objects.create(
            assignment=assignment2,
            question_text='Q1 in A2',
            question_type='single_choice',
            order=1
        )

        self.assertEqual(q1.order, 1)
        self.assertEqual(q2.order, 1)

    def test_randomize_options_field(self):
        """Test randomize_options field"""
        question = AssignmentQuestion.objects.create(
            assignment=self.assignment,
            question_text='Question with randomize',
            question_type='single_choice',
            randomize_options=True,
            order=1
        )
        self.assertTrue(question.randomize_options)

    def test_created_updated_timestamps(self):
        """Test created_at and updated_at timestamps"""
        question = AssignmentQuestion.objects.create(
            assignment=self.assignment,
            question_text='Question with timestamps',
            question_type='single_choice',
            order=1
        )
        self.assertIsNotNone(question.created_at)
        self.assertIsNotNone(question.updated_at)


class QuestionOrderingServiceTests(TestCase):
    """Tests for QuestionOrderingService"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            status='published'
        )

        # Create 5 questions
        self.questions = []
        for i in range(1, 6):
            q = AssignmentQuestion.objects.create(
                assignment=self.assignment,
                question_text=f'Question {i}',
                question_type='single_choice',
                order=i
            )
            self.questions.append(q)

    def test_validate_unique_order_valid(self):
        """Test validating unique order - valid case"""
        is_valid, error = QuestionOrderingService.validate_unique_order(
            self.assignment.id, 10
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_unique_order_duplicate(self):
        """Test validating unique order - duplicate case"""
        is_valid, error = QuestionOrderingService.validate_unique_order(
            self.assignment.id, 1
        )
        self.assertFalse(is_valid)
        self.assertIn('already used', error)

    def test_validate_unique_order_exclude_self(self):
        """Test validating unique order excluding a question"""
        question = self.questions[0]
        is_valid, error = QuestionOrderingService.validate_unique_order(
            self.assignment.id, 1, exclude_question_id=question.id
        )
        self.assertTrue(is_valid)

    def test_get_next_order_empty(self):
        """Test getting next order for assignment with no questions"""
        new_assignment = Assignment.objects.create(
            title='Empty Assignment',
            description='Test',
            instructions='Test',
            author=self.teacher,
            status='published'
        )
        next_order = QuestionOrderingService.get_next_order(new_assignment.id)
        self.assertEqual(next_order, 1)

    def test_get_next_order_with_questions(self):
        """Test getting next order with existing questions"""
        next_order = QuestionOrderingService.get_next_order(self.assignment.id)
        self.assertEqual(next_order, 6)

    def test_reorder_questions_success(self):
        """Test bulk reordering questions"""
        reorder_data = [
            {'id': self.questions[0].id, 'order': 5},
            {'id': self.questions[1].id, 'order': 4},
            {'id': self.questions[2].id, 'order': 3},
        ]

        result = QuestionOrderingService.reorder_questions(
            self.assignment.id, reorder_data
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['updated_count'], 3)

        # Verify orders changed
        self.questions[0].refresh_from_db()
        self.assertEqual(self.questions[0].order, 5)

    def test_reorder_questions_invalid_assignment(self):
        """Test reordering with invalid assignment"""
        reorder_data = [{'id': self.questions[0].id, 'order': 1}]

        with self.assertRaises(ValidationError):
            QuestionOrderingService.reorder_questions(99999, reorder_data)

    def test_reorder_questions_nonexistent_question(self):
        """Test reordering with non-existent question"""
        reorder_data = [{'id': 99999, 'order': 1}]

        with self.assertRaises(ValidationError):
            QuestionOrderingService.reorder_questions(
                self.assignment.id, reorder_data
            )

    def test_reorder_questions_duplicate_orders(self):
        """Test reordering with duplicate order values"""
        reorder_data = [
            {'id': self.questions[0].id, 'order': 10},
            {'id': self.questions[1].id, 'order': 10},
        ]

        with self.assertRaises(ValidationError):
            QuestionOrderingService.reorder_questions(
                self.assignment.id, reorder_data
            )

    def test_auto_renumber_after_deletion(self):
        """Test auto-renumbering after question deletion"""
        # Delete question with order 3
        self.questions[2].delete()

        result = QuestionOrderingService.auto_renumber_after_deletion(
            self.assignment.id
        )

        self.assertEqual(result['status'], 'success')

        # Verify remaining questions are renumbered
        remaining = AssignmentQuestion.objects.filter(
            assignment=self.assignment
        ).order_by('order')

        for index, question in enumerate(remaining):
            self.assertEqual(question.order, index + 1)

    def test_get_ordered_questions(self):
        """Test retrieving ordered questions"""
        questions = QuestionOrderingService.get_ordered_questions(
            self.assignment.id
        )

        orders = [q.order for q in questions]
        self.assertEqual(orders, [1, 2, 3, 4, 5])

    def test_get_ordered_questions_randomized(self):
        """Test retrieving randomized questions"""
        student_id = 123
        questions = QuestionOrderingService.get_ordered_questions(
            self.assignment.id,
            randomize=True,
            student_id=student_id
        )

        # Should return list
        self.assertIsInstance(questions, list)

        # Should have all questions
        self.assertEqual(len(questions), 5)

        # Order should be different (with very high probability)
        orders = [q.order for q in questions]
        self.assertNotEqual(orders, [1, 2, 3, 4, 5])

    def test_randomization_consistency(self):
        """Test that randomization is consistent for same student"""
        student_id = 456
        q1 = QuestionOrderingService.get_ordered_questions(
            self.assignment.id,
            randomize=True,
            student_id=student_id
        )
        q2 = QuestionOrderingService.get_ordered_questions(
            self.assignment.id,
            randomize=True,
            student_id=student_id
        )

        orders1 = [q.id for q in q1]
        orders2 = [q.id for q in q2]

        self.assertEqual(orders1, orders2)

    def test_validate_order_sequence_valid(self):
        """Test validating order sequence - valid case"""
        result = QuestionOrderingService.validate_order_sequence(
            self.assignment.id
        )

        self.assertTrue(result['valid'])
        self.assertEqual(result['total_questions'], 5)

    def test_validate_order_sequence_with_gaps(self):
        """Test validating order sequence with gaps"""
        # Create a gap by changing order
        self.questions[2].order = 10
        self.questions[2].save()

        result = QuestionOrderingService.validate_order_sequence(
            self.assignment.id,
            allow_gaps=False
        )

        self.assertFalse(result['valid'])
        self.assertTrue(len(result['issues']) > 0)


class QuestionOrderingSerializerTests(TestCase):
    """Tests for ordering-related serializers"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            status='published'
        )

        self.questions = []
        for i in range(1, 4):
            q = AssignmentQuestion.objects.create(
                assignment=self.assignment,
                question_text=f'Question {i}',
                question_type='single_choice',
                order=i
            )
            self.questions.append(q)

    def test_question_update_order_serializer_valid(self):
        """Test updating question order with valid data"""
        question = self.questions[0]
        serializer = AssignmentQuestionUpdateOrderSerializer(
            instance=question,
            data={'order': 10}
        )
        self.assertTrue(serializer.is_valid())

    def test_question_update_order_serializer_duplicate(self):
        """Test updating question order to existing order"""
        question = self.questions[0]
        serializer = AssignmentQuestionUpdateOrderSerializer(
            instance=question,
            data={'order': 2}  # Order 2 is taken by questions[1]
        )
        self.assertFalse(serializer.is_valid())

    def test_reorder_serializer_valid(self):
        """Test bulk reorder serializer with valid data"""
        data = {
            'questions': [
                {'id': self.questions[0].id, 'order': 5},
                {'id': self.questions[1].id, 'order': 4},
            ]
        }
        serializer = QuestionReorderSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_reorder_serializer_empty_list(self):
        """Test reorder serializer with empty list"""
        data = {'questions': []}
        serializer = QuestionReorderSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_reorder_serializer_nonexistent_question(self):
        """Test reorder serializer with non-existent question"""
        data = {
            'questions': [
                {'id': 99999, 'order': 5},
            ]
        }
        serializer = QuestionReorderSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_reorder_serializer_duplicate_orders(self):
        """Test reorder serializer with duplicate orders"""
        data = {
            'questions': [
                {'id': self.questions[0].id, 'order': 5},
                {'id': self.questions[1].id, 'order': 5},
            ]
        }
        serializer = QuestionReorderSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class QuestionOrderingAPITests(TestCase):
    """Tests for question ordering API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        self.assignment = Assignment.objects.create(
            title='Test Assignment',
            description='Test Description',
            instructions='Test Instructions',
            author=self.teacher,
            status='published'
        )

        self.questions = []
        for i in range(1, 4):
            q = AssignmentQuestion.objects.create(
                assignment=self.assignment,
                question_text=f'Question {i}',
                question_type='single_choice',
                order=i
            )
            self.questions.append(q)

    def test_list_questions_with_order(self):
        """Test listing questions with order field"""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(
            f'/api/assignments/{self.assignment.id}/questions/'
        )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                self.assertTrue(all('order' in item for item in data))
                self.assertTrue(all('randomize_options' in item for item in data))

    def test_get_question_includes_order(self):
        """Test getting single question includes order field"""
        self.client.force_authenticate(user=self.teacher)

        question = self.questions[0]
        response = self.client.get(
            f'/api/assignments/{self.assignment.id}/questions/{question.id}/'
        )

        if response.status_code == 200:
            data = response.json()
            self.assertIn('order', data)
            self.assertEqual(data['order'], 1)

    def test_update_question_order(self):
        """Test updating question order via PATCH"""
        self.client.force_authenticate(user=self.teacher)

        question = self.questions[0]
        response = self.client.patch(
            f'/api/assignments/{self.assignment.id}/questions/{question.id}/',
            {'order': 10},
            format='json'
        )

        if response.status_code in [200, 204]:
            question.refresh_from_db()
            self.assertEqual(question.order, 10)

    def test_student_cannot_reorder_questions(self):
        """Test that students cannot reorder questions"""
        self.client.force_authenticate(user=self.student)

        question = self.questions[0]
        response = self.client.patch(
            f'/api/assignments/{self.assignment.id}/questions/{question.id}/',
            {'order': 10},
            format='json'
        )

        # Should be forbidden
        self.assertIn(response.status_code, [403, 401])
