"""
T_ASN_004: Auto-Grading System for Multiple Choice and True/False Questions

Implements automatic grading for objective question types:
- Multiple choice (single and multiple selection)
- True/false questions
- Numeric answers with tolerance
- Fill-in-the-blank (exact match)

Features:
- Partial credit support (proportional scoring)
- Multiple grading modes (all-or-nothing, proportional)
- Handles unanswered questions
- Grade letter assignment (A, B, C, D, F)
- Detailed grading breakdown
- Score aggregation and percentage calculation
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from assignments.models import (
    AssignmentSubmission,
    AssignmentQuestion,
    AssignmentAnswer,
    Assignment
)

logger = logging.getLogger(__name__)


class GradingService:
    """
    Service for automatic grading of objective questions.

    Supports:
    - Single choice questions
    - Multiple choice questions
    - True/False questions
    - Numeric answers with tolerance
    - Fill-in-the-blank (exact match)
    """

    # Grading mode constants
    GRADING_MODE_ALL_OR_NOTHING = 'all_or_nothing'
    GRADING_MODE_PROPORTIONAL = 'proportional'

    # Grade letter thresholds (percentage)
    GRADE_THRESHOLDS = {
        'A': 90,
        'B': 80,
        'C': 70,
        'D': 60,
        'F': 0
    }

    # Default numeric tolerance (5%)
    DEFAULT_NUMERIC_TOLERANCE = 0.05

    def __init__(self):
        self.logger = logger

    def auto_grade_submission(
        self,
        submission: AssignmentSubmission,
        grading_mode: str = GRADING_MODE_PROPORTIONAL,
        numeric_tolerance: float = DEFAULT_NUMERIC_TOLERANCE
    ) -> Dict[str, Any]:
        """
        Auto-grade a complete submission with all questions.

        Args:
            submission: AssignmentSubmission instance
            grading_mode: 'all_or_nothing' or 'proportional'
            numeric_tolerance: Tolerance for numeric answers (0.05 = 5%)

        Returns:
            Dict with grading results including:
            - total_score: Total points earned
            - max_score: Maximum possible points
            - percentage: Percentage score
            - grade_letter: Letter grade (A-F)
            - question_results: List of per-question results
            - summary: Grading summary
        """
        try:
            # Get all questions and answers for this submission
            questions = submission.assignment.questions.all().order_by('order')

            if not questions.exists():
                self.logger.warning(
                    f"No questions found for assignment {submission.assignment_id}"
                )
                return self._empty_grading_result()

            # Grade each question
            question_results = []
            total_score = 0
            max_score = 0

            with transaction.atomic():
                for question in questions:
                    max_score += question.points

                    # Get student's answer
                    answer = AssignmentAnswer.objects.filter(
                        submission=submission,
                        question=question
                    ).first()

                    # Grade the answer
                    result = self._grade_question(
                        question=question,
                        answer=answer,
                        grading_mode=grading_mode,
                        numeric_tolerance=numeric_tolerance
                    )

                    question_results.append(result)
                    total_score += result['points_earned']

                    # Update answer record
                    if answer:
                        answer.points_earned = result['points_earned']
                        answer.is_correct = result['is_correct']
                        answer.save(update_fields=['points_earned', 'is_correct'])

                # Calculate final results
                percentage = self._calculate_percentage(total_score, max_score)
                grade_letter = self._assign_grade_letter(percentage)

                # Update submission
                submission.score = int(round(total_score))
                submission.max_score = max_score
                submission.status = AssignmentSubmission.Status.GRADED
                submission.graded_at = timezone.now()
                submission.save(
                    update_fields=['score', 'max_score', 'status', 'graded_at']
                )

            result = {
                'submission_id': submission.id,
                'total_score': int(round(total_score)),
                'max_score': max_score,
                'percentage': percentage,
                'grade_letter': grade_letter,
                'question_results': question_results,
                'summary': {
                    'total_questions': len(question_results),
                    'correct_answers': sum(1 for r in question_results if r['is_correct']),
                    'incorrect_answers': sum(1 for r in question_results if not r['is_correct']),
                    'unanswered': sum(1 for r in question_results if r['is_unanswered']),
                    'grading_mode': grading_mode,
                }
            }

            self.logger.info(
                f"Auto-graded submission {submission.id}: "
                f"{int(round(total_score))}/{max_score} ({percentage}%)"
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Error auto-grading submission {submission.id}: {e}"
            )
            raise

    def _grade_question(
        self,
        question: AssignmentQuestion,
        answer: Optional[AssignmentAnswer],
        grading_mode: str,
        numeric_tolerance: float
    ) -> Dict[str, Any]:
        """
        Grade a single question based on type.

        Args:
            question: AssignmentQuestion instance
            answer: AssignmentAnswer instance or None
            grading_mode: Grading mode
            numeric_tolerance: Numeric tolerance

        Returns:
            Dict with grading results
        """
        result = {
            'question_id': question.id,
            'question_text': question.question_text,
            'question_type': question.question_type,
            'points_possible': question.points,
            'is_unanswered': False,
            'is_correct': False,
            'points_earned': 0,
            'explanation': ''
        }

        # Check if answer exists
        if not answer or not answer.answer_text and not answer.answer_choice:
            result['is_unanswered'] = True
            result['explanation'] = 'Вопрос не отвечен'
            return result

        # Grade based on question type
        question_type = question.question_type

        if question_type == AssignmentQuestion.Type.SINGLE_CHOICE:
            return self._grade_single_choice(
                question, answer, result, grading_mode
            )

        elif question_type == AssignmentQuestion.Type.MULTIPLE_CHOICE:
            return self._grade_multiple_choice(
                question, answer, result, grading_mode
            )

        elif question_type == AssignmentQuestion.Type.TEXT:
            return self._grade_text(question, answer, result)

        elif question_type == AssignmentQuestion.Type.NUMBER:
            return self._grade_numeric(
                question, answer, result, numeric_tolerance
            )

        return result

    def _grade_single_choice(
        self,
        question: AssignmentQuestion,
        answer: AssignmentAnswer,
        result: Dict,
        grading_mode: str
    ) -> Dict:
        """Grade single choice (radio button) question."""
        correct_answer = question.correct_answer

        # Extract student answer (should be list with 1 item)
        student_answer = answer.answer_choice
        if isinstance(student_answer, str):
            student_answer = [student_answer]

        # Compare answers
        if student_answer and student_answer[0] == correct_answer:
            result['is_correct'] = True
            result['points_earned'] = question.points
            result['explanation'] = 'Правильный ответ'
        else:
            result['is_correct'] = False
            result['points_earned'] = 0
            result['explanation'] = f'Правильный ответ: {correct_answer}'

        return result

    def _grade_multiple_choice(
        self,
        question: AssignmentQuestion,
        answer: AssignmentAnswer,
        result: Dict,
        grading_mode: str
    ) -> Dict:
        """Grade multiple choice question with partial credit support."""
        correct_answers = set(question.correct_answer)
        if isinstance(correct_answers, str):
            correct_answers = {correct_answers}

        student_answers = set(answer.answer_choice) if answer.answer_choice else set()

        if grading_mode == self.GRADING_MODE_ALL_OR_NOTHING:
            # All or nothing: must match exactly
            if student_answers == correct_answers:
                result['is_correct'] = True
                result['points_earned'] = question.points
                result['explanation'] = 'Все ответы правильны'
            else:
                result['is_correct'] = False
                result['points_earned'] = 0
                result['explanation'] = (
                    f'Правильные ответы: {", ".join(str(a) for a in correct_answers)}'
                )

        else:  # PROPORTIONAL mode
            # Partial credit: calculate percentage of correct answers
            if not student_answers:
                result['points_earned'] = 0
                result['explanation'] = 'Ответы не выбраны'
                return result

            # Count correct and incorrect selections
            correct_selections = len(student_answers & correct_answers)
            incorrect_selections = len(student_answers - correct_answers)
            missed_correct = len(correct_answers - student_answers)

            # Calculate score: award for correct, penalize for incorrect
            if len(correct_answers) > 0:
                # Points for correct selections
                points = (correct_selections / len(correct_answers)) * question.points

                # Penalty for wrong selections
                if incorrect_selections > 0:
                    penalty = (incorrect_selections / len(correct_answers)) * question.points
                    points = max(0, points - penalty)

                result['is_correct'] = (student_answers == correct_answers)
                result['points_earned'] = int(round(points))

                if result['is_correct']:
                    result['explanation'] = 'Все ответы правильны'
                else:
                    result['explanation'] = (
                        f'Правильно: {correct_selections}/{len(correct_answers)}. '
                        f'Правильные ответы: {", ".join(str(a) for a in correct_answers)}'
                    )

        return result

    def _grade_text(
        self,
        question: AssignmentQuestion,
        answer: AssignmentAnswer,
        result: Dict
    ) -> Dict:
        """Grade text answer (exact match, case-insensitive)."""
        correct_answer = str(question.correct_answer).lower().strip()
        student_answer = answer.answer_text.lower().strip() if answer.answer_text else ''

        # Exact match comparison
        if student_answer == correct_answer:
            result['is_correct'] = True
            result['points_earned'] = question.points
            result['explanation'] = 'Правильный ответ'
        else:
            result['is_correct'] = False
            result['points_earned'] = 0
            result['explanation'] = f'Правильный ответ: {correct_answer}'

        return result

    def _grade_numeric(
        self,
        question: AssignmentQuestion,
        answer: AssignmentAnswer,
        result: Dict,
        tolerance: float
    ) -> Dict:
        """Grade numeric answer with tolerance."""
        try:
            correct_value = float(question.correct_answer)
            student_value = float(answer.answer_text) if answer.answer_text else None

            if student_value is None:
                result['is_unanswered'] = True
                result['explanation'] = 'Ответ не введен'
                return result

            # Calculate tolerance range
            tolerance_range = correct_value * tolerance
            min_acceptable = correct_value - tolerance_range
            max_acceptable = correct_value + tolerance_range

            # Check if student answer is within tolerance
            if min_acceptable <= student_value <= max_acceptable:
                result['is_correct'] = True
                result['points_earned'] = question.points
                result['explanation'] = 'Ответ в пределах допуска'
            else:
                result['is_correct'] = False
                result['points_earned'] = 0
                result['explanation'] = (
                    f'Правильный ответ: {correct_value} '
                    f'(допуск: {tolerance*100}%)'
                )

        except (ValueError, TypeError):
            result['is_correct'] = False
            result['points_earned'] = 0
            result['explanation'] = 'Некорректный числовой формат'

        return result

    def _calculate_percentage(self, score: float, max_score: float) -> float:
        """Calculate percentage score."""
        if max_score == 0:
            return 0.0
        return round((score / max_score) * 100, 2)

    def _assign_grade_letter(self, percentage: float) -> str:
        """
        Assign letter grade based on percentage.

        Thresholds:
        - A: 90%+
        - B: 80-89%
        - C: 70-79%
        - D: 60-69%
        - F: <60%
        """
        for grade, threshold in sorted(
            self.GRADE_THRESHOLDS.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if percentage >= threshold:
                return grade
        return 'F'

    def _empty_grading_result(self) -> Dict:
        """Return empty grading result when no questions exist."""
        return {
            'submission_id': None,
            'total_score': 0,
            'max_score': 0,
            'percentage': 0.0,
            'grade_letter': 'F',
            'question_results': [],
            'summary': {
                'total_questions': 0,
                'correct_answers': 0,
                'incorrect_answers': 0,
                'unanswered': 0,
                'grading_mode': self.GRADING_MODE_PROPORTIONAL,
            }
        }

    def auto_grade_assignment(
        self,
        assignment: Assignment,
        grading_mode: str = GRADING_MODE_PROPORTIONAL,
        numeric_tolerance: float = DEFAULT_NUMERIC_TOLERANCE
    ) -> Dict[str, Any]:
        """
        Auto-grade all submissions for an assignment.

        Args:
            assignment: Assignment instance
            grading_mode: Grading mode to use
            numeric_tolerance: Numeric tolerance

        Returns:
            Dict with bulk grading statistics
        """
        submissions = AssignmentSubmission.objects.filter(
            assignment=assignment,
            status=AssignmentSubmission.Status.SUBMITTED
        )

        stats = {
            'total': submissions.count(),
            'graded': 0,
            'failed': 0,
            'errors': [],
        }

        for submission in submissions:
            try:
                self.auto_grade_submission(
                    submission,
                    grading_mode=grading_mode,
                    numeric_tolerance=numeric_tolerance
                )
                stats['graded'] += 1
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append({
                    'submission_id': submission.id,
                    'error': str(e)
                })
                self.logger.error(
                    f"Failed to grade submission {submission.id}: {e}"
                )

        return stats

    def get_grading_breakdown(
        self,
        submission: AssignmentSubmission
    ) -> Dict[str, Any]:
        """
        Get detailed grading breakdown for a submission.

        Returns information about each question and answer.

        Args:
            submission: AssignmentSubmission instance

        Returns:
            Dict with detailed breakdown
        """
        questions = submission.assignment.questions.all().order_by('order')
        breakdown = {
            'submission_id': submission.id,
            'assignment_id': submission.assignment_id,
            'student_id': submission.student_id,
            'total_score': submission.score,
            'max_score': submission.max_score,
            'percentage': submission.percentage,
            'questions': []
        }

        for question in questions:
            answer = AssignmentAnswer.objects.filter(
                submission=submission,
                question=question
            ).first()

            question_info = {
                'question_id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'points_possible': question.points,
                'points_earned': answer.points_earned if answer else 0,
                'is_correct': answer.is_correct if answer else False,
                'student_answer': None,
                'correct_answer': question.correct_answer
            }

            # Format student answer based on type
            if answer:
                if answer.answer_choice:
                    question_info['student_answer'] = answer.answer_choice
                else:
                    question_info['student_answer'] = answer.answer_text

            breakdown['questions'].append(question_info)

        return breakdown
