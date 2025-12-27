# ViewSet Optimization Patterns (T_SYS_006)

## Overview

This document provides concrete implementation examples for optimizing ViewSets to eliminate N+1 queries.

## Base Optimized ViewSet Class

Create this base class and inherit from it:

```python
# core/views/optimized_viewset.py

from rest_framework import viewsets
from django.db.models import Prefetch, Q, Count


class OptimizedViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet with automatic query optimization.

    Override get_queryset_optimizations() to define per-action optimizations.

    Example:
        class MyViewSet(OptimizedViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer

            def get_queryset_optimizations(self):
                return {
                    'list': lambda qs: qs.select_related('author', 'owner'),
                    'retrieve': lambda qs: qs.select_related('author')
                                             .prefetch_related('comments'),
                }
    """

    def get_queryset_optimizations(self):
        """
        Return dict of action -> optimization functions.

        {
            'list': lambda qs: qs.select_related('field'),
            'retrieve': lambda qs: qs.prefetch_related('related'),
        }
        """
        return {}

    def get_queryset(self):
        """Apply optimizations based on current action"""
        queryset = super().get_queryset()

        optimizations = self.get_queryset_optimizations()
        optimize_fn = optimizations.get(self.action)

        if optimize_fn:
            queryset = optimize_fn(queryset)

        return queryset
```

## Specific ViewSet Examples

### 1. StudentProfileViewSet

```python
# accounts/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch, Count, Q, F

from accounts.models import StudentProfile
from accounts.serializers import StudentProfileSerializer
from core.views.optimized_viewset import OptimizedViewSet


class StudentProfileViewSet(OptimizedViewSet):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer

    def get_queryset_optimizations(self):
        return {
            # List view: Include related User, Tutor, Parent
            'list': lambda qs: qs.select_related(
                'user',           # ForeignKey
                'tutor',          # ForeignKey to User (tutor)
                'parent'          # ForeignKey to User (parent)
            ).prefetch_related(
                # Optional: if needed for counts
                Prefetch('user__assignment_submissions')
            ).annotate(
                submission_count=Count('user__assignment_submissions', distinct=True),
                grade_points=Sum('user__assignment_submissions__score')
            ),

            # Retrieve view: Deep optimization for profile detail
            'retrieve': lambda qs: qs.select_related(
                'user',
                'tutor__teacher_profile',
                'parent__parent_profile'
            ).prefetch_related(
                Prefetch(
                    'user__chat_rooms',
                    queryset=ChatRoom.objects.select_related('created_by')
                ),
                Prefetch(
                    'user__assignment_submissions',
                    queryset=AssignmentSubmission.objects.select_related('assignment')
                )
            ),

            # Stats action: Count aggregations
            'stats': lambda qs: qs.annotate(
                total_submissions=Count('user__assignment_submissions'),
                avg_score=Avg('user__assignment_submissions__score'),
                completed_materials=Count(
                    'user__materialprogress',
                    filter=Q(user__materialprogress__is_completed=True)
                )
            )
        }

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get student statistics with optimized queries"""
        student = self.get_object()
        return Response({
            'total_submissions': student.total_submissions,
            'avg_score': float(student.avg_score or 0),
            'completed_materials': student.completed_materials,
            'progress': student.progress_percentage,
        })
```

### 2. AssignmentSubmissionViewSet

```python
# assignments/views.py

from rest_framework import viewsets
from django.db.models import Prefetch, Sum, Count, Avg

from assignments.models import AssignmentSubmission
from assignments.serializers import AssignmentSubmissionSerializer
from core.views.optimized_viewset import OptimizedViewSet


class AssignmentSubmissionViewSet(OptimizedViewSet):
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentSubmissionSerializer

    def get_queryset_optimizations(self):
        # Prefetch answers with related questions
        answers_prefetch = Prefetch(
            'answers',
            queryset=AssignmentAnswer.objects.select_related('question')
        )

        return {
            # List: Join student, assignment, author
            'list': lambda qs: qs.select_related(
                'student',                    # Who submitted
                'assignment',                 # The assignment
                'assignment__author'          # Who created it
            ).prefetch_related(
                answers_prefetch
            ).annotate(
                answer_count=Count('answers'),
                max_points=F('assignment__max_score')
            ),

            # Retrieve: Deep with feedback relationships
            'retrieve': lambda qs: qs.select_related(
                'student__student_profile',
                'assignment__author__teacher_profile'
            ).prefetch_related(
                answers_prefetch,
                Prefetch(
                    'versions',
                    queryset=SubmissionVersion.objects.order_by('version_number')
                )
            ),

            # List by assignment
            'by_assignment': lambda qs: qs.filter(
                assignment_id=self.request.query_params.get('assignment_id')
            ).select_related(
                'student'
            ).order_by('-submitted_at'),
        }
```

### 3. MessageViewSet

```python
# chat/views.py

from rest_framework import viewsets
from django.db.models import Prefetch, Count

from chat.models import Message, ChatRoom
from chat.serializers import MessageSerializer
from core.views.optimized_viewset import OptimizedViewSet


class MessageViewSet(OptimizedViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def get_queryset_optimizations(self):
        # Prefetch sender with profile
        sender_prefetch = Prefetch(
            'sender',
            queryset=User.objects.select_related(
                'student_profile',
                'teacher_profile'
            )
        )

        # Prefetch replies for threading
        replies_prefetch = Prefetch(
            'replies',
            queryset=Message.objects.select_related('sender').order_by('created_at')
        )

        return {
            # List messages in a room
            'list': lambda qs: qs.filter(
                room_id=self.request.query_params.get('room_id')
            ).select_related(
                'room'
            ).prefetch_related(
                sender_prefetch,
                Prefetch('reply_to__sender')
            ).order_by('-created_at'),

            # Retrieve single message with full context
            'retrieve': lambda qs: qs.select_related(
                'room',
                'sender__student_profile',
                'sender__teacher_profile',
                'reply_to__sender'
            ).prefetch_related(
                replies_prefetch
            ),

            # Messages by thread
            'by_thread': lambda qs: qs.filter(
                thread_id=self.request.query_params.get('thread_id')
            ).select_related(
                'sender',
                'room'
            ).prefetch_related(
                replies_prefetch
            ).order_by('created_at'),
        }
```

### 4. MaterialViewSet

```python
# materials/views.py

from rest_framework import viewsets
from django.db.models import Prefetch, Count, Q, F

from materials.models import Material, MaterialProgress
from materials.serializers import MaterialSerializer
from core.views.optimized_viewset import OptimizedViewSet


class MaterialViewSet(OptimizedViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer

    def get_queryset_optimizations(self):
        # Prefetch student progress
        progress_prefetch = Prefetch(
            'progress',
            queryset=MaterialProgress.objects.select_related('student')
        )

        # Prefetch files
        files_prefetch = Prefetch(
            'files',
            queryset=MaterialFile.objects.order_by('created_at')
        )

        return {
            # List published materials
            'list': lambda qs: qs.filter(
                status='published'
            ).select_related(
                'subject',
                'created_by__teacher_profile'
            ).prefetch_related(
                progress_prefetch,
                files_prefetch
            ).annotate(
                completion_count=Count(
                    'progress',
                    filter=Q(progress__is_completed=True)
                ),
                avg_score=Avg('progress__score')
            ),

            # Retrieve with full details
            'retrieve': lambda qs: qs.select_related(
                'subject',
                'created_by__teacher_profile',
                'created_by__tutor_profile'
            ).prefetch_related(
                progress_prefetch,
                files_prefetch,
                Prefetch(
                    'comments',
                    queryset=MaterialComment.objects.select_related('author')
                )
            ),

            # By subject
            'by_subject': lambda qs: qs.filter(
                subject_id=self.request.query_params.get('subject_id')
            ).select_related(
                'created_by'
            ).prefetch_related(
                progress_prefetch
            ),
        }
```

### 5. ChatRoomViewSet

```python
# chat/views.py

from rest_framework import viewsets
from django.db.models import Prefetch, Count, Max

from chat.models import ChatRoom, Message
from chat.serializers import ChatRoomSerializer
from core.views.optimized_viewset import OptimizedViewSet


class ChatRoomViewSet(OptimizedViewSet):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer

    def get_queryset_optimizations(self):
        # Prefetch last message
        last_message_prefetch = Prefetch(
            'messages',
            queryset=Message.objects.order_by('-created_at')[:1]
        )

        return {
            # List rooms
            'list': lambda qs: qs.select_related(
                'created_by'
            ).prefetch_related(
                'participants',
                last_message_prefetch
            ).annotate(
                participant_count=Count('participants', distinct=True),
                message_count=Count('messages'),
                last_message_time=Max('messages__created_at')
            ),

            # Retrieve room details
            'retrieve': lambda qs: qs.select_related(
                'created_by__student_profile',
                'created_by__teacher_profile'
            ).prefetch_related(
                Prefetch(
                    'participants',
                    queryset=User.objects.select_related('student_profile')
                ),
                Prefetch(
                    'messages',
                    queryset=Message.objects.select_related('sender')
                        .prefetch_related('replies')
                        .order_by('-created_at')[:50]  # Last 50 messages
                )
            ),

            # Active rooms for user
            'active': lambda qs: qs.filter(
                participants=self.request.user
            ).select_related(
                'created_by'
            ).prefetch_related(
                'participants',
                last_message_prefetch
            ).order_by('-updated_at'),
        }
```

### 6. ReportViewSet

```python
# reports/views.py

from rest_framework import viewsets
from django.db.models import Prefetch, Sum, Avg, Count

from reports.models import StudentReport
from reports.serializers import StudentReportSerializer
from core.views.optimized_viewset import OptimizedViewSet


class StudentReportViewSet(OptimizedViewSet):
    queryset = StudentReport.objects.all()
    serializer_class = StudentReportSerializer

    def get_queryset_optimizations(self):
        return {
            # List reports
            'list': lambda qs: qs.select_related(
                'student',
                'student__student_profile',
                'created_by__teacher_profile'
            ).order_by('-created_at'),

            # Report detail
            'retrieve': lambda qs: qs.select_related(
                'student__student_profile',
                'created_by'
            ).prefetch_related(
                Prefetch(
                    'assignments',
                    queryset=AssignmentSubmission.objects.select_related('assignment')
                )
            ),

            # By period
            'by_period': lambda qs: qs.filter(
                created_at__gte=self.request.query_params.get('start_date'),
                created_at__lt=self.request.query_params.get('end_date')
            ).select_related(
                'student'
            ).annotate(
                avg_score=Avg('score'),
                submission_count=Count('assignments')
            ),
        }
```

## 7. Common Query Optimization Patterns

### Pattern: Prefetch with Filtering

```python
# Get students with only their graded submissions
graded_submissions = AssignmentSubmission.objects.filter(status='graded')

students = StudentProfile.objects.prefetch_related(
    Prefetch(
        'user__assignment_submissions',
        queryset=graded_submissions
    )
)
```

### Pattern: Annotate for Counts

```python
from django.db.models import Count, Q

# Instead of n queries for .count(), use annotation
materials = Material.objects.annotate(
    completion_count=Count(
        'progress',
        filter=Q(progress__is_completed=True),
        distinct=True
    ),
    student_count=Count('progress__student', distinct=True)
)

for material in materials:
    print(material.completion_count)  # No query!
```

### Pattern: Combining select_related and prefetch_related

```python
# Good example of combined optimization
queryset = AssignmentSubmission.objects.select_related(
    'student',                    # FK: one query per list item
    'assignment__author'          # FK chain: no extra queries
).prefetch_related(
    Prefetch(
        'answers',
        queryset=AssignmentAnswer.objects.select_related('question')
    ),
    'assignment__subject'         # FK in prefetch is OK
).annotate(
    answer_count=Count('answers')
)
```

### Pattern: Caching Optimization

```python
from django.core.cache import cache

def get_student_with_cache(student_id):
    cache_key = f'student_profile:{student_id}'
    student = cache.get(cache_key)

    if student is None:
        student = StudentProfile.objects.select_related(
            'user', 'tutor', 'parent'
        ).get(pk=student_id)
        cache.set(cache_key, student, 3600)  # 1 hour

    return student
```

## 8. Performance Checklist

Before deploying new ViewSets:

- [ ] Define get_queryset_optimizations()
- [ ] Use select_related for FK fields
- [ ] Use prefetch_related for reverse FK and M2M
- [ ] Use Prefetch for complex prefetching with filters
- [ ] Use annotate for counts instead of .count() in loops
- [ ] Test with debug toolbar to verify query count
- [ ] Profile with locust or similar load testing
- [ ] Document N+1 hotspots if any remain
- [ ] Add indexes recommended in OPTIMIZATION_GUIDE.md

## 9. Testing Query Optimization

```python
# tests/test_optimization.py

from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

class StudentProfileOptimizationTestCase(TestCase):

    def test_student_list_queries(self):
        # Create test data
        for i in range(10):
            StudentProfile.objects.create(user_id=i+1)

        # Capture queries
        with CaptureQueriesContext(connection) as context:
            list(StudentProfile.objects.select_related('tutor', 'parent'))

        # Should be 1 query, not 21 (1 + 10 tutor + 10 parent)
        self.assertEqual(len(context), 1)

    def test_message_list_queries(self):
        # Test that message list uses select_related for sender
        with CaptureQueriesContext(connection) as context:
            # This should be 2-3 queries, not N queries
            list(Message.objects.filter(room_id=1)
                 .select_related('sender'))

        # Verify reasonable query count
        self.assertLess(len(context), 5)
```

## 10. Migration Checklist

When implementing these patterns:

1. Apply index migrations: `python manage.py migrate`
2. Update ViewSet get_queryset_optimizations()
3. Test with query inspection tool
4. Run tests to verify query counts
5. Load test with concurrent users
6. Monitor performance in production
7. Adjust prefetch_related if needed
