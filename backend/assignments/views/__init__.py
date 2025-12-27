"""
Assignments views package

Organizes views into logical modules:
- grading: Grading-related views
- history: Assignment history and versioning views
- late_submissions: Late submission handling views
"""

from .late_submissions import LateSubmissionViewSet

__all__ = [
    'LateSubmissionViewSet',
]
