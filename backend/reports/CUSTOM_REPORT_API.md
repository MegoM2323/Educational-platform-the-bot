# Custom Report Builder API Documentation

## Overview

The Custom Report Builder allows teachers to create, configure, generate, and share custom reports with flexible data selection, filtering, sorting, and visualization options.

## Endpoints

### Custom Reports Management

#### List Custom Reports
```
GET /api/reports/custom-reports/
```

Query Parameters:
- `status`: Filter by status (draft, active, archived)
- `is_shared`: Filter by sharing status (true/false)
- `created_by`: Filter by creator user ID
- `search`: Search by name or description
- `ordering`: Order by field (created_at, updated_at)

Response:
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Class Progress Report",
      "description": "Track overall class progress",
      "created_by": 2,
      "created_by_name": "John Doe",
      "is_shared": false,
      "shared_count": 0,
      "status": "draft",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z",
      "last_execution": {
        "executed_at": "2025-01-15T11:00:00Z",
        "rows_returned": 25,
        "execution_time_ms": 145
      }
    }
  ]
}
```

#### Create Custom Report
```
POST /api/reports/custom-reports/
```

Request Body:
```json
{
  "name": "My Custom Report",
  "description": "A detailed description of the report",
  "status": "draft",
  "config": {
    "fields": ["student_name", "grade", "submission_count"],
    "filters": {
      "subject_id": 5,
      "date_range": {
        "start": "2025-01-01",
        "end": "2025-12-31"
      }
    },
    "chart_type": "bar",
    "sort_by": "grade",
    "sort_order": "desc",
    "limit": 100
  }
}
```

Available Fields:
- Student fields: `student_name`, `student_email`, `grade`, `submission_count`, `progress`, `attendance`, `last_submission_date`
- Assignment fields: `title`, `due_date`, `avg_score`, `submission_rate`, `completion_rate`, `late_submissions`, `total_submissions`
- Submission fields: `score`, `feedback`, `graded_by`, `graded_at`, `status`

Available Chart Types: `bar`, `line`, `pie`, `histogram`, `scatter`

Available Filters:
- `subject_id`: Subject ID (integer)
- `date_range`: Object with start and end ISO dates
- `grade_range`: Object with min and max values (0-100)
- `status`: Submission status (submitted, graded, late, pending)
- `student_id`: Individual student ID
- `class_id`: Class/Group ID
- `assignment_id`: Assignment ID

Response: 201 Created with report details

#### Get Report Details
```
GET /api/reports/custom-reports/{id}/
```

Response:
```json
{
  "id": 1,
  "name": "Class Progress Report",
  "description": "Track overall class progress",
  "created_by": 2,
  "created_by_name": "John Doe",
  "is_shared": false,
  "shared_with_list": [],
  "config": {
    "fields": ["student_name", "grade"],
    "filters": {},
    "chart_type": "bar"
  },
  "status": "draft",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "execution_history": [
    {
      "id": 1,
      "executed_by": 2,
      "executed_by_name": "John Doe",
      "rows_returned": 25,
      "execution_time_ms": 145,
      "result_summary": {
        "field_count": 2,
        "has_chart": true,
        "filter_count": 0
      },
      "executed_at": "2025-01-15T11:00:00Z"
    }
  ],
  "available_fields": {
    "description": "Available fields for this report type",
    "options": {
      "student": [...],
      "assignment": [...],
      "grade": [...]
    }
  },
  "available_filters": {
    "description": "Available filter options",
    "options": {
      "subject_id": "Subject ID (integer)",
      "date_range": "Date range..."
    }
  }
}
```

#### Update Report
```
PATCH /api/reports/custom-reports/{id}/
```

Request Body (all fields optional):
```json
{
  "name": "Updated Report Name",
  "description": "Updated description",
  "config": {
    "fields": ["student_name", "grade"],
    "filters": {},
    "chart_type": "line"
  },
  "status": "active",
  "is_shared": true
}
```

Response: 200 OK with updated report

#### Delete Report
```
DELETE /api/reports/custom-reports/{id}/
```

Performs soft delete (can be restored).

Response: 204 No Content

#### Generate Report
```
POST /api/reports/custom-reports/{id}/generate/
```

Generates report data based on current configuration.

Response:
```json
{
  "report_name": "Class Progress Report",
  "description": "Track overall class progress",
  "config": {
    "fields": ["student_name", "grade"],
    "filters": {},
    "chart_type": "bar"
  },
  "fields": ["student_name", "grade"],
  "data": [
    {
      "student_name": "Alice Johnson",
      "grade": 95.5
    },
    {
      "student_name": "Bob Smith",
      "grade": 87.0
    }
  ],
  "row_count": 2,
  "execution_time_ms": 145,
  "chart": {
    "type": "bar",
    "labels": ["Alice Johnson", "Bob Smith"],
    "datasets": [
      {
        "label": "Values",
        "data": [95.5, 87.0],
        "backgroundColor": "rgba(75, 192, 192, 0.6)",
        "borderColor": "rgba(75, 192, 192, 1)",
        "borderWidth": 1
      }
    ]
  },
  "generated_at": "2025-01-15T11:05:00Z"
}
```

#### Share Report
```
POST /api/reports/custom-reports/{id}/share/
```

Share report with other teachers.

Request Body:
```json
{
  "user_ids": [3, 4, 5]
}
```

Response:
```json
{
  "success": true,
  "message": "Report shared with 3 users",
  "shared_with": [
    {
      "id": 3,
      "name": "Jane Smith",
      "email": "jane@example.com"
    }
  ]
}
```

#### Unshare Report
```
POST /api/reports/custom-reports/{id}/unshare/
```

Remove sharing from specific users.

Request Body:
```json
{
  "user_ids": [3]
}
```

Response:
```json
{
  "success": true,
  "message": "Sharing removed for 1 user"
}
```

#### Clone Report
```
POST /api/reports/custom-reports/{id}/clone/
```

Create a new report based on this one.

Request Body:
```json
{
  "name": "Cloned Report Name",
  "description": "Optional new description",
  "config_overrides": {
    "chart_type": "line"
  }
}
```

Response: 201 Created with cloned report

#### Get Execution History
```
GET /api/reports/custom-reports/{id}/executions/?limit=20
```

Get execution history for the report.

Query Parameters:
- `limit`: Number of recent executions (default: 20)

Response:
```json
{
  "report_id": 1,
  "report_name": "Class Progress Report",
  "total_executions": 5,
  "executions": [...]
}
```

#### Soft Delete
```
DELETE /api/reports/custom-reports/{id}/soft-delete/
```

Response: 200 OK

#### Restore Deleted Report
```
POST /api/reports/custom-reports/{id}/restore/
```

Response: 200 OK with restored report

### Report Templates

#### List System Templates
```
GET /api/reports/custom-templates/
```

Query Parameters:
- `template_type`: Filter by type (class_progress, student_grades, etc.)
- `is_system`: Filter by system templates (true/false)
- `search`: Search templates

Response:
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "name": "Class Progress Report",
      "description": "Track overall class progress on assigned materials",
      "template_type": "class_progress",
      "base_config": {...},
      "is_system": true,
      "created_by": null,
      "created_by_name": null,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z",
      "can_clone": true,
      "clone_url": "/api/custom-templates/1/clone/"
    }
  ]
}
```

#### Clone Template to Report
```
POST /api/reports/custom-templates/{id}/clone/
```

Request Body:
```json
{
  "name": "My Class Progress Report",
  "description": "Customized version",
  "config_overrides": {
    "sort_order": "asc"
  }
}
```

Response: 201 Created with new custom report

## Configuration Format

### Config Structure
```json
{
  "fields": ["student_name", "grade", "submission_count"],
  "filters": {
    "subject_id": 5,
    "date_range": {
      "start": "2025-01-01",
      "end": "2025-12-31"
    },
    "status": "submitted"
  },
  "chart_type": "bar",
  "sort_by": "grade",
  "sort_order": "desc",
  "limit": 100
}
```

### Config Validation Rules
- `fields` (required): Must be a non-empty list of valid field names
- `filters` (optional): Dictionary of filter conditions
- `chart_type` (optional): One of bar, line, pie, histogram, scatter
- `sort_by` (optional): Must be in the fields list
- `sort_order` (optional): 'asc' or 'desc'
- `limit` (optional): Maximum rows to return

## Permissions

- **Create/Update/Delete**: Only report owner or admin
- **View**: Report owner, admin, or users the report is shared with
- **Generate**: Report owner, admin, or users the report is shared with
- **Share**: Only report owner or admin
- **Clone**: Authenticated teachers

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid fields specified: invalid_field_name",
  "details": ["Validation details here"]
}
```

### 403 Forbidden
```json
{
  "error": "You do not have permission to perform this action"
}
```

### 404 Not Found
```json
{
  "error": "Report not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to generate report",
  "details": "Error details"
}
```

## Performance Considerations

- Reports cache execution results (optional)
- Execution time is recorded for optimization
- Large datasets (10000+ rows) may be paginated
- Chart data is limited to 50 items for readability
- Database indexes on frequently filtered fields

## Examples

### Example 1: Create and Generate a Student Grades Report
```bash
# Create
curl -X POST http://localhost:8000/api/reports/custom-reports/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Grade Overview",
    "description": "All student grades",
    "config": {
      "fields": ["student_name", "grade", "submission_count"],
      "filters": {},
      "chart_type": "bar",
      "sort_by": "grade",
      "sort_order": "desc"
    }
  }'

# Generate
curl -X POST http://localhost:8000/api/reports/custom-reports/1/generate/ \
  -H "Authorization: Token YOUR_TOKEN"
```

### Example 2: Create and Share a Class Progress Report
```bash
# Create
curl -X POST http://localhost:8000/api/reports/custom-reports/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Class Progress",
    "config": {
      "fields": ["student_name", "progress", "submission_count"],
      "filters": {"subject_id": 5},
      "chart_type": "bar"
    }
  }'

# Share
curl -X POST http://localhost:8000/api/reports/custom-reports/1/share/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": [3, 4, 5]
  }'
```

### Example 3: Clone a System Template
```bash
curl -X POST http://localhost:8000/api/reports/custom-templates/1/clone/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Grade Report",
    "description": "Based on system template",
    "config_overrides": {
      "sort_order": "asc"
    }
  }'
```

## Testing

Run tests:
```bash
ENVIRONMENT=test python manage.py pytest reports/test_custom_reports_core.py -v
```

Create system templates:
```bash
python manage.py create_report_templates
```
