"""
Materialized Views for Data Warehouse.

Optimized SQL definitions for common analytics aggregations.
These views are refreshed daily via Celery tasks.

Views:
  - student_grade_summary: per-student grade statistics
  - class_progress_summary: per-class progress statistics
  - teacher_workload: teacher review workload analysis
  - subject_performance: per-subject performance metrics
"""

# ============================================================================
# STUDENT GRADE SUMMARY VIEW
# ============================================================================
# Aggregates grades by student and subject for quick analytics
# Indexed on (student_id, subject_id) for fast lookups

STUDENT_GRADE_SUMMARY_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS student_grade_summary AS
SELECT
    sp.student_id,
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
GROUP BY sp.student_id, m.subject_id
WITH DATA;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_student_grade_summary_student_subject
    ON student_grade_summary(student_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_student_grade_summary_student_id
    ON student_grade_summary(student_id);
CREATE INDEX IF NOT EXISTS idx_student_grade_summary_subject_id
    ON student_grade_summary(subject_id);
"""

# ============================================================================
# CLASS PROGRESS SUMMARY VIEW
# ============================================================================
# Aggregates progress metrics at class level for teacher dashboards
# Indexed on class_id for efficient filtering

CLASS_PROGRESS_SUMMARY_VIEW = """
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_class_progress_summary_class_subject
    ON class_progress_summary(class_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_class_progress_summary_class_id
    ON class_progress_summary(class_id);
"""

# ============================================================================
# TEACHER WORKLOAD VIEW
# ============================================================================
# Measures teacher review/grading workload for capacity planning
# Indexed on teacher_id for quick lookups

TEACHER_WORKLOAD_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS teacher_workload AS
SELECT
    ae.teacher_id,
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
WHERE ae.created_by_id = teacher_id
GROUP BY ae.teacher_id
WITH DATA;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_teacher_workload_teacher_id
    ON teacher_workload(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_workload_pending_reviews
    ON teacher_workload(pending_reviews DESC);
"""

# ============================================================================
# SUBJECT PERFORMANCE VIEW
# ============================================================================
# Aggregates performance metrics by subject across all students
# Used for subject-level analytics and comparisons

SUBJECT_PERFORMANCE_VIEW = """
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_subject_performance_subject_id
    ON subject_performance(subject_id);
CREATE INDEX IF NOT EXISTS idx_subject_performance_avg_grade
    ON subject_performance(avg_grade DESC);
"""

# ============================================================================
# VIEW REFRESH STATEMENTS
# ============================================================================
# Used to refresh materialized views (typically via Celery daily)

REFRESH_ALL_VIEWS = """
REFRESH MATERIALIZED VIEW CONCURRENTLY student_grade_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY class_progress_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY teacher_workload;
REFRESH MATERIALIZED VIEW CONCURRENTLY subject_performance;
"""

# Individual refresh statements
REFRESH_STUDENT_GRADES = "REFRESH MATERIALIZED VIEW CONCURRENTLY student_grade_summary;"
REFRESH_CLASS_PROGRESS = "REFRESH MATERIALIZED VIEW CONCURRENTLY class_progress_summary;"
REFRESH_TEACHER_WORKLOAD = "REFRESH MATERIALIZED VIEW CONCURRENTLY teacher_workload;"
REFRESH_SUBJECT_PERFORMANCE = "REFRESH MATERIALIZED VIEW CONCURRENTLY subject_performance;"

# Cleanup statements (for development/testing)
DROP_ALL_VIEWS = """
DROP MATERIALIZED VIEW IF EXISTS student_grade_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS class_progress_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS teacher_workload CASCADE;
DROP MATERIALIZED VIEW IF EXISTS subject_performance CASCADE;
"""
