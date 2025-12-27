"""
Raw SQL Analytics Queries for Data Warehouse.

Optimized queries for complex analytics operations:
- Student progress over time
- Subject performance comparison
- Teacher workload analysis
- Attendance vs grades correlation
- Top/bottom performers

All queries designed for:
- Large datasets (pagination support)
- Fast execution (<5 seconds)
- Database-level aggregation
"""

# ============================================================================
# STUDENT PROGRESS OVER TIME
# ============================================================================
# Tracks student progression across weeks/months
# Returns: student_id, period, avg_grade, submission_count, pass_rate

STUDENT_PROGRESS_OVER_TIME = """
SELECT
    sr.student_id,
    DATE_TRUNC('{granularity}', sr.created_at)::DATE as period,
    COUNT(DISTINCT sr.id)::INTEGER as submission_count,
    ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
    ROUND(CAST(COUNT(CASE WHEN sr.score >= 70 THEN 1 END) AS DECIMAL) * 100 /
        NULLIF(COUNT(*), 0), 2)::DECIMAL as pass_rate,
    MIN(CAST(sr.score AS DECIMAL))::DECIMAL as min_score,
    MAX(CAST(sr.score AS DECIMAL))::DECIMAL as max_score,
    STDDEV(CAST(sr.score AS DECIMAL))::DECIMAL as score_stddev
FROM materials_materialsubmission sr
WHERE sr.student_id = %s
    AND sr.score IS NOT NULL
    AND sr.created_at >= %s
    AND sr.created_at <= %s
GROUP BY sr.student_id, DATE_TRUNC('{granularity}', sr.created_at)
ORDER BY period ASC
LIMIT %s OFFSET %s;
"""

# ============================================================================
# SUBJECT PERFORMANCE COMPARISON
# ============================================================================
# Compares performance across subjects for an individual student
# Returns: subject_id, subject_name, metrics

SUBJECT_PERFORMANCE_COMPARISON = """
SELECT
    m.subject_id,
    s.name as subject_name,
    COUNT(DISTINCT sr.id)::INTEGER as submission_count,
    ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
    MIN(CAST(sr.score AS DECIMAL))::DECIMAL as min_grade,
    MAX(CAST(sr.score AS DECIMAL))::DECIMAL as max_grade,
    ROUND(STDDEV(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as grade_variance,
    ROUND(CAST(COUNT(CASE WHEN sr.score >= 70 THEN 1 END) AS DECIMAL) * 100 /
        NULLIF(COUNT(*), 0), 2)::DECIMAL as pass_rate,
    MAX(sr.created_at)::TIMESTAMP as last_submission,
    ROUND(AVG(EXTRACT(EPOCH FROM (sr.created_at - sr.created_at))::DECIMAL), 2) as avg_submission_interval_seconds
FROM materials_materialsubmission sr
JOIN materials_material m ON sr.material_id = m.id
JOIN materials_subject s ON m.subject_id = s.id
WHERE sr.student_id = %s
    AND sr.score IS NOT NULL
GROUP BY m.subject_id, s.name
ORDER BY avg_grade DESC
LIMIT %s OFFSET %s;
"""

# ============================================================================
# TEACHER WORKLOAD ANALYSIS
# ============================================================================
# Analyzes teacher review/grading workload
# Returns: teacher_id, assignment metrics, review speed, pending items

TEACHER_WORKLOAD_ANALYSIS = """
SELECT
    ae.teacher_id,
    COUNT(DISTINCT ae.id)::INTEGER as total_assignments,
    COUNT(DISTINCT assub.id)::INTEGER as total_submissions,
    COUNT(DISTINCT CASE WHEN assub.status = 'pending' THEN assub.id END)::INTEGER as pending_reviews,
    COUNT(DISTINCT CASE WHEN assub.status = 'graded' THEN assub.id END)::INTEGER as graded_submissions,
    ROUND(AVG(EXTRACT(EPOCH FROM (assub.graded_at - assub.created_at))/3600)::DECIMAL, 2)::DECIMAL as avg_grade_time_hours,
    MIN(EXTRACT(EPOCH FROM (assub.graded_at - assub.created_at))/3600)::DECIMAL as min_grade_time_hours,
    MAX(EXTRACT(EPOCH FROM (assub.graded_at - assub.created_at))/3600)::DECIMAL as max_grade_time_hours,
    ROUND(CAST(COUNT(CASE WHEN assub.created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
        AND assub.status = 'pending' THEN assub.id END) AS DECIMAL) * 100 /
        NULLIF(COUNT(CASE WHEN assub.status = 'pending' THEN assub.id END), 0), 2)::DECIMAL as overdue_percentage,
    MAX(assub.graded_at)::TIMESTAMP as last_graded_time
FROM assignments_assignment ae
LEFT JOIN assignments_assignmentsubmission assub ON ae.id = assub.assignment_id
WHERE ae.created_by_id = %s
    AND ae.created_at >= %s
    AND ae.created_at <= %s
GROUP BY ae.teacher_id
ORDER BY pending_reviews DESC;
"""

# ============================================================================
# ATTENDANCE VS GRADES CORRELATION
# ============================================================================
# Correlates attendance records with grade performance
# Returns: attendance_rate, avg_grade, student count, correlation metrics

ATTENDANCE_VS_GRADES_CORRELATION = """
SELECT
    ROUND(CAST(att.attendance_days AS DECIMAL) / NULLIF(att.total_days, 0) * 100, 2)::DECIMAL as attendance_rate_bucket,
    COUNT(DISTINCT sr.student_id)::INTEGER as student_count,
    ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
    MIN(CAST(sr.score AS DECIMAL))::DECIMAL as min_grade,
    MAX(CAST(sr.score AS DECIMAL))::DECIMAL as max_grade,
    COUNT(DISTINCT sr.id)::INTEGER as total_submissions,
    ROUND(STDDEV(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as score_stddev
FROM (
    -- Attendance summary
    SELECT
        user_id as student_id,
        COUNT(CASE WHEN status = 'present' THEN 1 END)::INTEGER as attendance_days,
        COUNT(*)::INTEGER as total_days
    FROM scheduling_attendance
    WHERE date >= %s AND date <= %s
    GROUP BY user_id
) att
LEFT JOIN materials_materialsubmission sr ON att.student_id = sr.student_id
    AND sr.score IS NOT NULL
    AND sr.created_at >= %s
    AND sr.created_at <= %s
GROUP BY ROUND(CAST(att.attendance_days AS DECIMAL) / NULLIF(att.total_days, 0) * 100, 2)
ORDER BY attendance_rate_bucket DESC;
"""

# ============================================================================
# TOP PERFORMERS BY SUBJECT
# ============================================================================
# Identifies top students in each subject
# Pagination: LIMIT 10 (default), OFFSET for more results

TOP_PERFORMERS = """
SELECT
    m.subject_id,
    s.name as subject_name,
    sr.student_id,
    au.first_name,
    au.last_name,
    COUNT(DISTINCT sr.id)::INTEGER as submission_count,
    ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
    MAX(CAST(sr.score AS DECIMAL))::DECIMAL as max_grade,
    MIN(sr.created_at)::TIMESTAMP as first_submission,
    MAX(sr.created_at)::TIMESTAMP as last_submission
FROM materials_materialsubmission sr
JOIN materials_material m ON sr.material_id = m.id
JOIN materials_subject s ON m.subject_id = s.id
JOIN accounts_user au ON sr.student_id = au.id
WHERE sr.score IS NOT NULL
    AND sr.created_at >= %s
GROUP BY m.subject_id, s.name, sr.student_id, au.first_name, au.last_name
HAVING COUNT(DISTINCT sr.id) >= %s  -- Minimum submissions filter
ORDER BY m.subject_id, avg_grade DESC
LIMIT %s OFFSET %s;
"""

# ============================================================================
# BOTTOM PERFORMERS BY SUBJECT
# ============================================================================
# Identifies students needing help in each subject
# Pagination: LIMIT 10 (default), OFFSET for more results

BOTTOM_PERFORMERS = """
SELECT
    m.subject_id,
    s.name as subject_name,
    sr.student_id,
    au.first_name,
    au.last_name,
    COUNT(DISTINCT sr.id)::INTEGER as submission_count,
    ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
    MAX(CAST(sr.score AS DECIMAL))::DECIMAL as max_grade,
    MIN(sr.created_at)::TIMESTAMP as first_submission,
    MAX(sr.created_at)::TIMESTAMP as last_submission,
    ROUND(CAST(COUNT(CASE WHEN sr.score < 70 THEN 1 END) AS DECIMAL) * 100 /
        NULLIF(COUNT(*), 0), 2)::DECIMAL as fail_rate
FROM materials_materialsubmission sr
JOIN materials_material m ON sr.material_id = m.id
JOIN materials_subject s ON m.subject_id = s.id
JOIN accounts_user au ON sr.student_id = au.id
WHERE sr.score IS NOT NULL
    AND sr.created_at >= %s
GROUP BY m.subject_id, s.name, sr.student_id, au.first_name, au.last_name
HAVING COUNT(DISTINCT sr.id) >= %s  -- Minimum submissions filter
ORDER BY m.subject_id, avg_grade ASC
LIMIT %s OFFSET %s;
"""

# ============================================================================
# STUDENT ENGAGEMENT METRICS
# ============================================================================
# Measures student activity and engagement patterns
# Returns: student metrics, submission frequency, participation indicators

STUDENT_ENGAGEMENT_METRICS = """
SELECT
    sr.student_id,
    au.first_name,
    au.last_name,
    COUNT(DISTINCT sr.id)::INTEGER as submission_count,
    COUNT(DISTINCT DATE(sr.created_at))::INTEGER as active_days,
    ROUND(CAST(COUNT(DISTINCT DATE(sr.created_at)) AS DECIMAL) / NULLIF({days_in_period}, 0) * 100, 2)::DECIMAL as engagement_percentage,
    ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
    MAX(sr.created_at)::TIMESTAMP as last_submission,
    ROUND(AVG(EXTRACT(EPOCH FROM (sr.created_at - LAG(sr.created_at, 1)
        OVER (PARTITION BY sr.student_id ORDER BY sr.created_at))))/86400::DECIMAL, 2)::DECIMAL as avg_days_between_submissions
FROM materials_materialsubmission sr
JOIN accounts_user au ON sr.student_id = au.id
WHERE sr.created_at >= %s
    AND sr.created_at <= %s
GROUP BY sr.student_id, au.first_name, au.last_name
ORDER BY engagement_percentage DESC
LIMIT %s OFFSET %s;
"""

# ============================================================================
# CLASS PERFORMANCE TRENDS
# ============================================================================
# Tracks class performance over time periods
# Useful for identifying class-level issues and improvements

CLASS_PERFORMANCE_TRENDS = """
SELECT
    se.class_id,
    DATE_TRUNC('{granularity}', sr.created_at)::DATE as period,
    COUNT(DISTINCT se.student_id)::INTEGER as student_count,
    COUNT(DISTINCT sr.id)::INTEGER as submission_count,
    ROUND(AVG(CAST(sr.score AS DECIMAL)), 2)::DECIMAL as avg_grade,
    MIN(CAST(sr.score AS DECIMAL))::DECIMAL as min_grade,
    MAX(CAST(sr.score AS DECIMAL))::DECIMAL as max_grade,
    ROUND(CAST(COUNT(CASE WHEN sr.score >= 70 THEN 1 END) AS DECIMAL) * 100 /
        NULLIF(COUNT(*), 0), 2)::DECIMAL as pass_rate
FROM materials_studentsubjectenrollment se
JOIN materials_material m ON se.subject_id = m.subject_id
LEFT JOIN materials_materialsubmission sr ON se.student_id = sr.student_id
    AND m.id = sr.material_id
    AND sr.score IS NOT NULL
WHERE se.is_active = true
    AND sr.created_at >= %s
    AND sr.created_at <= %s
GROUP BY se.class_id, DATE_TRUNC('{granularity}', sr.created_at)
ORDER BY se.class_id, period ASC;
"""
