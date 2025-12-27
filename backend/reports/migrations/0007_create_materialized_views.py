# Generated migration to create data warehouse materialized views

from django.db import migrations
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps


def create_materialized_views(apps, schema_editor):
    """Create materialized views for data warehouse operations."""

    # Only run on PostgreSQL
    if 'postgresql' not in schema_editor.connection.settings_dict.get('ENGINE', ''):
        return

    with schema_editor.connection.cursor() as cursor:
        # Student Grade Summary View
        cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS student_grade_summary AS
            SELECT
                sp.user_id as student_id,
                m.subject_id,
                COUNT(DISTINCT sr.id)::INTEGER as submission_count,
                ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
                MAX(sr.created_at)::TIMESTAMP as last_submission_date,
                MIN(sr.created_at)::TIMESTAMP as first_submission_date,
                ROUND(CAST(COUNT(CASE WHEN sr.score >= 70 THEN 1 END) AS DECIMAL) * 100 / COUNT(*), 2)::DECIMAL as pass_rate
            FROM accounts_studentprofile sp
            JOIN materials_materialsubmission sr ON sp.user_id = sr.student_id
            JOIN materials_material m ON sr.material_id = m.id
            WHERE sr.score IS NOT NULL
            GROUP BY sp.user_id, m.subject_id
            WITH DATA;
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_grade_summary_student_subject
            ON student_grade_summary(student_id, subject_id);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_grade_summary_student_id
            ON student_grade_summary(student_id);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_grade_summary_subject_id
            ON student_grade_summary(subject_id);
        """)

        # Class Progress Summary View
        cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS class_progress_summary AS
            SELECT
                se.class_id,
                m.subject_id,
                COUNT(DISTINCT se.student_id)::INTEGER as student_count,
                ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
                COUNT(DISTINCT sr.id)::INTEGER as total_submissions,
                ROUND(CAST(COUNT(CASE WHEN sr.score >= 70 THEN 1 END) AS DECIMAL) * 100 /
                    NULLIF(COUNT(DISTINCT sr.id), 0), 2)::DECIMAL as pass_rate,
                ROUND(CAST(COUNT(DISTINCT CASE WHEN sr.created_at >= CURRENT_DATE - INTERVAL '7 days' THEN sr.id END) AS DECIMAL) * 100 /
                    NULLIF(COUNT(DISTINCT sr.id), 0), 2)::DECIMAL as recent_submission_rate
            FROM materials_studentsubjectenrollment se
            JOIN materials_material m ON se.subject_id = m.subject_id
            LEFT JOIN materials_materialsubmission sr ON se.student_id = sr.student_id AND m.id = sr.material_id
            WHERE se.is_active = true
            GROUP BY se.class_id, m.subject_id
            WITH DATA;
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_class_progress_summary_class_subject
            ON class_progress_summary(class_id, subject_id);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_class_progress_summary_class_id
            ON class_progress_summary(class_id);
        """)

        # Teacher Workload View
        cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS teacher_workload AS
            SELECT
                ae.created_by_id as teacher_id,
                COUNT(DISTINCT ae.id)::INTEGER as total_assignments,
                COUNT(DISTINCT CASE WHEN assub.status = 'pending' THEN assub.id END)::INTEGER as pending_reviews,
                COUNT(DISTINCT CASE WHEN assub.status = 'graded' THEN assub.id END)::INTEGER as graded_submissions,
                COUNT(DISTINCT assub.id)::INTEGER as total_submissions,
                ROUND(AVG(EXTRACT(EPOCH FROM (assub.graded_at - assub.created_at))/60)::DECIMAL, 2)::DECIMAL as avg_grade_time_minutes,
                MAX(assub.graded_at)::TIMESTAMP as last_graded_time,
                ROUND(CAST(COUNT(DISTINCT CASE WHEN assub.status = 'pending' AND assub.created_at < CURRENT_TIMESTAMP - INTERVAL '1 week' THEN assub.id END) AS DECIMAL) * 100 /
                    NULLIF(COUNT(DISTINCT CASE WHEN assub.status = 'pending' THEN assub.id END), 0), 2)::DECIMAL as overdue_percentage
            FROM assignments_assignment ae
            LEFT JOIN assignments_assignmentsubmission assub ON ae.id = assub.assignment_id
            WHERE ae.created_by_id IS NOT NULL
            GROUP BY ae.created_by_id
            WITH DATA;
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_teacher_workload_teacher_id
            ON teacher_workload(teacher_id);
        """)

        # Subject Performance View
        cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS subject_performance AS
            SELECT
                m.subject_id,
                s.name as subject_name,
                COUNT(DISTINCT sr.student_id)::INTEGER as student_count,
                COUNT(DISTINCT sr.id)::INTEGER as total_submissions,
                ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
                MIN(CAST(sr.score AS DECIMAL))::DECIMAL as min_grade,
                MAX(CAST(sr.score AS DECIMAL))::DECIMAL as max_grade,
                ROUND(CAST(COUNT(CASE WHEN sr.score >= 90 THEN 1 END) AS DECIMAL) * 100 /
                    NULLIF(COUNT(DISTINCT sr.id), 0), 2)::DECIMAL as excellent_rate,
                ROUND(CAST(COUNT(CASE WHEN sr.score >= 70 AND sr.score < 90 THEN 1 END) AS DECIMAL) * 100 /
                    NULLIF(COUNT(DISTINCT sr.id), 0), 2)::DECIMAL as good_rate,
                ROUND(CAST(COUNT(CASE WHEN sr.score < 70 THEN 1 END) AS DECIMAL) * 100 /
                    NULLIF(COUNT(DISTINCT sr.id), 0), 2)::DECIMAL as below_average_rate,
                MAX(sr.created_at)::TIMESTAMP as last_submission_date
            FROM materials_material m
            JOIN materials_subject s ON m.subject_id = s.id
            LEFT JOIN materials_materialsubmission sr ON m.id = sr.material_id AND sr.score IS NOT NULL
            GROUP BY m.subject_id, s.name
            WITH DATA;
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subject_performance_subject_id
            ON subject_performance(subject_id);
        """)


def drop_materialized_views(apps, schema_editor):
    """Drop materialized views (reverse migration)."""

    # Only run on PostgreSQL
    if 'postgresql' not in schema_editor.connection.settings_dict.get('ENGINE', ''):
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS student_grade_summary CASCADE;")
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS class_progress_summary CASCADE;")
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS teacher_workload CASCADE;")
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS subject_performance CASCADE;")


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_add_parent_report_sharing'),
    ]

    operations = [
        migrations.RunPython(create_materialized_views, drop_materialized_views),
    ]
