# Quick Start: Report Export API

Export reports in CSV and Excel formats with advanced features.

## Installation

No additional installation needed. The export service is built into the Django application.

## Basic Usage

### Export via API

```bash
# Export reports as CSV
curl -X GET "http://localhost:8000/api/reports/export/?format=csv" \
  -H "Authorization: Token YOUR_TOKEN"

# Export as Excel
curl -X GET "http://localhost:8000/api/reports/export/?format=xlsx" \
  -H "Authorization: Token YOUR_TOKEN"

# Export with filters
curl -X GET "http://localhost:8000/api/reports/export/?format=xlsx&status=sent" \
  -H "Authorization: Token YOUR_TOKEN"
```

### Export via Python

```python
from rest_framework.test import APIClient

client = APIClient()
client.force_authenticate(user=teacher_user)

# CSV export
response = client.get('/api/reports/export/?format=csv')
with open('reports.csv', 'wb') as f:
    for chunk in response.streaming_content:
        f.write(chunk)

# Excel export
response = client.get('/api/reports/export/?format=xlsx')
with open('reports.xlsx', 'wb') as f:
    f.write(b''.join(response.streaming_content))
```

### Direct Service Usage

```python
from reports.services.export import ReportExportService

# Get your report data
data = [
    {'id': 1, 'title': 'Report 1', 'grade': 95.5},
    {'id': 2, 'title': 'Report 2', 'grade': 87.25}
]

# Export to CSV
response = ReportExportService.export_to_csv(data, 'my_reports')

# Export to Excel with formatting
response = ReportExportService.export_to_excel(data, 'my_reports', freeze_panes=True)

# Filter columns
filtered = ReportExportService.filter_by_columns(data, ['id', 'title'])
response = ReportExportService.export_to_csv(filtered)
```

## Available Endpoints

### General Reports
```
GET /api/reports/export/?format=csv|xlsx
    ?type=student_progress|class_performance|etc
    ?status=draft|generated|sent|archived
    ?author=USER_ID
```

### Student Reports
```
GET /api/student-reports/export/?format=csv|xlsx
    ?report_type=progress|behavior|achievement|etc
    ?status=draft|sent|read|archived
    ?student=USER_ID
```

### Tutor Weekly Reports
```
GET /api/tutor-weekly-reports/export/?format=csv|xlsx
    ?status=draft|sent|read|archived
    ?student=USER_ID
```

### Teacher Weekly Reports
```
GET /api/teacher-weekly-reports/export/?format=csv|xlsx
    ?status=draft|sent|read|archived
    ?student=USER_ID
    ?subject=SUBJECT_ID
```

## Export Formats

### CSV
- **Content-Type:** `text/csv; charset=utf-8-sig`
- **Encoding:** UTF-8 with BOM (Excel compatible)
- **Features:** Streaming, special character handling, configurable headers
- **Best For:** Data analysis, import to other tools, universal compatibility

### Excel
- **Content-Type:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Features:** Bold headers, frozen panes, number formatting, auto-fit columns
- **Number Format:** Grades/scores shown as 0.00 (2 decimals)
- **Best For:** Reports, presentations, professional sharing

## Common Patterns

### 1. Export and Save to File

```python
response = ReportExportService.export_to_csv(data, 'my_report')

# Save to file
with open('export.csv', 'wb') as f:
    f.write(b''.join(response.streaming_content))
```

### 2. Filter by Columns

```python
# Export only specific columns
columns = ['id', 'title', 'grade']
filtered = ReportExportService.filter_by_columns(data, columns)
response = ReportExportService.export_to_csv(filtered)
```

### 3. Check Dataset Size

```python
if ReportExportService.validate_dataset_size(data):
    response = ReportExportService.export_to_csv(data)
else:
    # Use filters or pagination
    print("Dataset too large, please filter")
```

### 4. Export with Custom Encoding

```python
# For international characters
response = ReportExportService.export_to_csv(
    data,
    encoding='utf-8-sig'  # Supports unicode
)
```

### 5. Export Without Headers

```python
response = ReportExportService.export_to_csv(
    data,
    include_headers=False
)
```

## Error Handling

```python
try:
    response = ReportExportService.export_to_csv(large_data)
except ValueError as e:
    if "too large" in str(e):
        # Handle size limit
        filtered_data = filter_data_by_status(large_data, 'sent')
        response = ReportExportService.export_to_csv(filtered_data)
```

## Limits

| Constraint | Value |
|-----------|-------|
| Max Rows | 100,000 |
| Max Column Width | 50 chars |
| Supported Formats | CSV, Excel (XLSX) |
| Encoding | Any Python codec |

## Troubleshooting

**Q: Excel file shows garbled text**
- A: Ensure encoding is `utf-8-sig` (includes BOM for Excel)

**Q: CSV headers missing**
- A: Check `include_headers=True` (it's the default)

**Q: Export times out**
- A: Use filters to reduce dataset size, or check if exceeds 100k rows

**Q: Column widths too narrow**
- A: Excel auto-fits based on content. For very long text, use CSV format

## API Authentication

All export endpoints require authentication:

```bash
# Token authentication
-H "Authorization: Token YOUR_TOKEN"

# Session authentication
curl -b "sessionid=YOUR_SESSION" ...
```

## Full Documentation

See `/docs/EXPORT_API_REFERENCE.md` for complete API reference and advanced features.

## Support

For issues or questions:
1. Check `/docs/EXPORT_API_REFERENCE.md` (Troubleshooting section)
2. Review test cases in `/backend/reports/test_exports_comprehensive.py`
3. Check example code above
