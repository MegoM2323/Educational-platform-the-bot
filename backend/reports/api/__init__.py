"""
API endpoints for analytics data consumption.

This module provides RESTful API endpoints for analytics data, leveraging
the data warehouse queries from T_REPORT_006 and caching from T_REPORT_007.

Endpoints:
- GET /api/analytics/students/ - Student analytics by subject
- GET /api/analytics/assignments/ - Assignment analytics by teacher
- GET /api/analytics/attendance/ - Attendance tracking analytics
- GET /api/analytics/engagement/ - Student engagement metrics
- GET /api/analytics/progress/ - Student progress over time
"""
