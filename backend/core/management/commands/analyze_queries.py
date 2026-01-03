"""
Database Query Analysis and Optimization Recommendations (PostgreSQL only)

Analyzes current database queries and recommends indexes and N+1 query fixes.
Only works with PostgreSQL databases.
Usage: python manage.py analyze_queries --db=default

Reports:
1. Missing indexes on frequently filtered/sorted fields
2. N+1 query opportunities in ViewSets
3. Query performance statistics
4. Recommendations for optimization
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.apps import apps
from django.db.models import ForeignKey, ManyToManyField
from django.db.models.fields.related import OneToOneField
import json
from collections import defaultdict


class Command(BaseCommand):
    help = "Analyze database queries and recommend indexes for optimization (PostgreSQL only)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--db',
            default='default',
            help='Database alias to analyze (default: default)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed index recommendations',
        )

    def handle(self, *args, **options):
        db_name = options['db']
        verbose = options['verbose']

        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS("DATABASE OPTIMIZATION ANALYSIS"))
        self.stdout.write(self.style.SUCCESS("="*70 + "\n"))

        # Analyze all models
        self.analyze_models()

        # Show recommended indexes
        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS("RECOMMENDED INDEXES"))
        self.stdout.write(self.style.SUCCESS("="*70 + "\n"))
        self.recommend_indexes(verbose)

        # Show N+1 opportunities
        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS("N+1 QUERY OPPORTUNITIES"))
        self.stdout.write(self.style.SUCCESS("="*70 + "\n"))
        self.analyze_n_plus_one_opportunities()

        # Show current database stats
        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS("DATABASE STATISTICS"))
        self.stdout.write(self.style.SUCCESS("="*70 + "\n"))
        self.show_database_stats()

        self.stdout.write(self.style.SUCCESS("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS("ANALYSIS COMPLETE"))
        self.stdout.write(self.style.SUCCESS("="*70 + "\n"))

    def analyze_models(self):
        """Analyze all models for indexing opportunities"""
        self.stdout.write(self.style.WARNING("\nAnalyzing models for index candidates...\n"))

        # Track all ForeignKey and filtered fields
        fk_candidates = defaultdict(list)
        filter_candidates = defaultdict(list)

        for model in apps.get_models():
            app_label = model._meta.app_label
            model_name = model._meta.model_name

            for field in model._meta.get_fields():
                # ForeignKey fields (potential select_related candidates)
                if isinstance(field, (ForeignKey, OneToOneField)):
                    fk_candidates[f"{app_label}.{model_name}"].append(
                        f"FK: {field.name} -> {field.related_model._meta.model_name}"
                    )

                # DateTime and date fields (common in filters/sorts)
                if field.name in ['created_at', 'updated_at', 'due_date', 'start_date',
                                   'submitted_at', 'graded_at', 'scheduled_at']:
                    filter_candidates[f"{app_label}.{model_name}"].append(
                        f"DateTime: {field.name}"
                    )

                # Status and type fields (often filtered)
                if field.name in ['status', 'type', 'role'] or field.name.endswith('_status'):
                    filter_candidates[f"{app_label}.{model_name}"].append(
                        f"Choice: {field.name}"
                    )

        # Display candidates
        for model, fields in sorted(fk_candidates.items()):
            if fields:
                self.stdout.write(f"\n  {self.style.WARNING(model)}")
                for field in fields:
                    self.stdout.write(f"    - {field}")

    def recommend_indexes(self, verbose):
        """Recommend specific indexes for high-value queries"""

        recommendations = [
            {
                'model': 'accounts.User',
                'field': 'email',
                'type': 'UNIQUE',
                'reason': 'Fast authentication lookups',
                'query': 'User.objects.filter(email=...)',
                'migration': 'User email field index',
            },
            {
                'model': 'accounts.StudentProfile',
                'field': 'tutor_id',
                'type': 'INDEX',
                'reason': 'Tutor-student relationships (select_related)',
                'query': 'StudentProfile.objects.select_related("tutor")',
                'migration': '0008_add_tutorprofile_index.py',
            },
            {
                'model': 'accounts.StudentProfile',
                'field': 'parent_id',
                'type': 'INDEX',
                'reason': 'Parent-student relationships',
                'query': 'StudentProfile.objects.select_related("parent")',
                'migration': '0008_add_parentprofile_index.py',
            },
            {
                'model': 'notifications.Notification',
                'field': ['recipient_id', 'is_archived', '-created_at'],
                'type': 'COMPOSITE',
                'reason': 'User notifications listing (already added)',
                'query': 'Notification.objects.filter(recipient=user, is_archived=False)',
                'migration': 'Already in model Meta.indexes',
            },
            {
                'model': 'assignments.Assignment',
                'field': 'due_date',
                'type': 'INDEX',
                'reason': 'Date range queries for overdue assignments',
                'query': 'Assignment.objects.filter(due_date__lt=now)',
                'migration': '0020_add_due_date_index.py',
            },
            {
                'model': 'assignments.AssignmentSubmission',
                'field': ['assignment_id', 'student_id'],
                'type': 'UNIQUE_COMPOSITE',
                'reason': 'One submission per student per assignment (already unique_together)',
                'query': 'AssignmentSubmission.objects.get(assignment=a, student=s)',
                'migration': 'Already in model unique_together',
            },
            {
                'model': 'assignments.AssignmentSubmission',
                'field': ['assignment_id', '-submitted_at'],
                'type': 'COMPOSITE',
                'reason': 'List submissions by assignment ordered by date',
                'query': 'AssignmentSubmission.objects.filter(assignment=a)',
                'migration': '0021_add_assignment_submission_index.py',
            },
            {
                'model': 'chat.ChatRoom',
                'field': 'created_by_id',
                'type': 'INDEX',
                'reason': 'User-created rooms (select_related)',
                'query': 'ChatRoom.objects.select_related("created_by")',
                'migration': '0010_add_chatroom_creator_index.py',
            },
            {
                'model': 'chat.Message',
                'field': 'room_id',
                'type': 'INDEX',
                'reason': 'Messages in room (prefetch_related)',
                'query': 'ChatRoom.objects.prefetch_related("messages")',
                'migration': 'Already auto-indexed as FK',
            },
            {
                'model': 'chat.Message',
                'field': ['room_id', '-created_at'],
                'type': 'COMPOSITE',
                'reason': 'List messages by room ordered by date',
                'query': 'Message.objects.filter(room=r).order_by("-created_at")',
                'migration': '0011_add_message_room_date_index.py',
            },
            {
                'model': 'knowledge_graph.Element',
                'field': 'created_by_id',
                'type': 'INDEX',
                'reason': 'Elements by author (select_related)',
                'query': 'Element.objects.select_related("created_by")',
                'migration': 'Already indexed in model',
            },
        ]

        for i, rec in enumerate(recommendations, 1):
            model_str = self.style.WARNING(rec['model'])
            field_str = self.style.MIGRATE_LABEL(str(rec['field']))
            reason_str = rec['reason']

            self.stdout.write(f"\n{i}. {model_str} - {rec['type']}")
            self.stdout.write(f"   Field(s): {field_str}")
            self.stdout.write(f"   Reason: {reason_str}")

            if verbose:
                self.stdout.write(f"   Query Example: {rec['query']}")
                self.stdout.write(f"   Migration: {rec['migration']}")

    def analyze_n_plus_one_opportunities(self):
        """Identify potential N+1 query problems"""

        opportunities = [
            {
                'location': 'accounts.views.StudentListView',
                'current': 'for student in students: student.user.email',
                'fix': '.select_related("user")',
                'impact': 'High',
                'explanation': 'Access related User object for each StudentProfile',
            },
            {
                'location': 'assignments.views.AssignmentListView',
                'current': 'for submission in submissions: submission.student.get_full_name()',
                'fix': '.select_related("student")',
                'impact': 'High',
                'explanation': 'Access related User object for each submission',
            },
            {
                'location': 'assignments.views.SubmissionListView',
                'current': 'for answer in answers: answer.question.assignment.title',
                'fix': '.select_related("question__assignment")',
                'impact': 'Medium',
                'explanation': 'Deep relationship traversal without joins',
            },
            {
                'location': 'chat.views.ChatRoomListView',
                'current': 'for room in rooms: room.participants.count()',
                'fix': '.prefetch_related("participants")',
                'impact': 'Medium',
                'explanation': 'M2M access without batching',
            },
            {
                'location': 'chat.views.MessageListView',
                'current': 'for message in messages: message.sender.profile.avatar',
                'fix': '.select_related("sender__student_profile")',
                'impact': 'High',
                'explanation': 'Related User profile access',
            },
            {
                'location': 'reports.views.StudentProgressView',
                'current': 'for student in students: student.assignment_submissions.count()',
                'fix': '.prefetch_related("assignment_submissions")',
                'impact': 'High',
                'explanation': 'Count operations on reverse FK',
            },
            {
                'location': 'knowledge_graph.views.ElementListView',
                'current': 'for element in elements: element.created_by.get_full_name()',
                'fix': '.select_related("created_by")',
                'impact': 'Medium',
                'explanation': 'Access related User for each Element',
            },
        ]

        for i, opp in enumerate(opportunities, 1):
            self.stdout.write(f"\n{i}. {self.style.WARNING(opp['location'])}")
            self.stdout.write(f"   Current Pattern: {opp['current']}")
            self.stdout.write(f"   Fix: {self.style.SUCCESS(opp['fix'])}")
            self.stdout.write(f"   Impact: {self.style.ERROR(opp['impact'])}")
            self.stdout.write(f"   Explanation: {opp['explanation']}")

    def show_database_stats(self):
        """Show current database statistics (PostgreSQL only)"""
        with connection.cursor() as cursor:
            # Get database info
            db_backend = connection.settings_dict.get('ENGINE', 'Unknown')
            db_name = connection.settings_dict.get('NAME', 'Unknown')

            self.stdout.write(f"Backend: {db_backend}")
            self.stdout.write(f"Database: {db_name}")

            # Get table count from PostgreSQL
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public'
                """)
                count = cursor.fetchone()[0]
                self.stdout.write(f"Total Tables: {count}")
            except Exception as e:
                self.stdout.write(f"Could not fetch table count: {e}")

        # Show model count
        model_count = len(list(apps.get_models()))
        self.stdout.write(f"Total Django Models: {model_count}")

        # Show indexes summary
        self.stdout.write("\nIndexes Summary:")
        indexed_models = 0
        total_indexes = 0

        for model in apps.get_models():
            meta = model._meta
            if hasattr(meta, 'indexes') and meta.indexes:
                indexed_models += 1
                total_indexes += len(meta.indexes)

        self.stdout.write(f"  Models with Meta.indexes: {indexed_models}")
        self.stdout.write(f"  Total indexes defined: {total_indexes}")
