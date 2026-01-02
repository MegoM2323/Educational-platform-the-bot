# Generated migration to create data warehouse materialized views

from django.db import migrations


def create_materialized_views(apps, schema_editor):
    """Create materialized views for data warehouse operations."""

    # Only run on PostgreSQL
    if 'postgresql' not in schema_editor.connection.settings_dict.get('ENGINE', ''):
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS student_grade_summary AS
            SELECT
                sp.user_id as student_id,
                m.subject_id,
                COUNT(DISTINCT sr.id)::INTEGER as submission_count,
                ROUND(AVG(CAST(mf.grade AS DECIMAL)), 2)::DECIMAL as avg_grade,
                MAX(sr.submitted_at)::TIMESTAMP as last_submission_date,
                MIN(sr.submitted_at)::TIMESTAMP as first_submission_date,
                ROUND(CAST(COUNT(CASE WHEN mf.grade >= 4 THEN 1 END) AS DECIMAL) * 100 / NULLIF(COUNT(DISTINCT sr.id), 0), 2)::DECIMAL as pass_rate
            FROM accounts_studentprofile sp
            JOIN materials_materialsubmission sr ON sp.user_id = sr.student_id
            JOIN materials_material m ON sr.material_id = m.id
            LEFT JOIN materials_materialfeedback mf ON sr.id = mf.submission_id
            WHERE mf.grade IS NOT NULL
            GROUP BY sp.user_id, m.subject_id
            WITH DATA;
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_grade_summary_student_subject ON student_grade_summary(student_id, subject_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_grade_summary_student_id ON student_grade_summary(student_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_grade_summary_subject_id ON student_grade_summary(subject_id);")


def drop_materialized_views(apps, schema_editor):
    """Drop materialized views (reverse migration)."""

    # Only run on PostgreSQL
    if 'postgresql' not in schema_editor.connection.settings_dict.get('ENGINE', ''):
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS student_grade_summary CASCADE;")


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_add_parent_report_sharing'),
    ]

    operations = [
        migrations.RunPython(create_materialized_views, drop_materialized_views),
    ]
