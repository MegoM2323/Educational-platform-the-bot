# T_ASN_008: Assignment Clone - Quick Reference

## Endpoint

```
POST /api/assignments/{id}/clone/
```

## Authentication

Required: Bearer token or session authentication

## Request

### Minimal (all defaults)
```json
{}
```

### Full example
```json
{
  "new_title": "Copy of Math Midterm",
  "new_due_date": "2025-12-30T18:00:00Z",
  "randomize_questions": false
}
```

## Response (201 Created)

```json
{
  "id": 42,
  "title": "Copy of Math Midterm",
  "description": "...",
  "instructions": "...",
  "author": 1,
  "author_name": "John Teacher",
  "type": "test",
  "status": "draft",
  "max_score": 100,
  "time_limit": 90,
  "attempts_limit": 1,
  "start_date": "2025-12-01T00:00:00Z",
  "due_date": "2025-12-30T18:00:00Z",
  "tags": "math,midterm",
  "difficulty_level": 3,
  "created_at": "2025-12-27T16:07:00Z",
  "updated_at": "2025-12-27T16:07:00Z",
  "questions_count": 25,
  "is_overdue": false,
  "rubric": null,
  "allow_late_submission": true
}
```

## Error Responses

### 400 Bad Request
```json
{
  "new_title": ["Title must be 200 characters or less"],
  "new_due_date": ["Due date cannot be in the past"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "error": "Only the assignment creator can clone it"
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to clone assignment"
}
```

## Field Reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| new_title | string | No | Max 200 chars, auto-generated if omitted |
| new_due_date | ISO datetime | No | Must be in future, defaults to original |
| randomize_questions | boolean | No | Default: false |

## Validation Rules

**new_title**:
- Maximum 200 characters
- Cannot be empty or whitespace-only
- Recommended: Use "Copy of ..." format

**new_due_date**:
- ISO 8601 format: "2025-12-30T18:00:00Z"
- Must be in the future
- If omitted, uses original assignment's due_date

**randomize_questions**:
- Boolean: true or false
- If true, question options are shuffled
- Default: false

## What Gets Cloned

✅ **Cloned**:
- Assignment title (auto-prefixed with "Copy of")
- Description
- Instructions
- Type (homework, test, etc.)
- Max score
- Time limit
- Attempts limit
- Tags
- Difficulty level
- All questions with options
- Rubric reference

❌ **Not Cloned**:
- Author (set to requesting user)
- Status (always set to DRAFT)
- Students assigned_to (empty)
- Submissions (always empty)
- Created/updated timestamps (new values)

## Examples

### cURL
```bash
curl -X POST https://api.example.com/api/assignments/1/clone/ \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "new_title": "Copy of Math Quiz",
    "randomize_questions": false
  }'
```

### Python (requests)
```python
import requests
from datetime import datetime, timedelta

url = "https://api.example.com/api/assignments/1/clone/"
headers = {"Authorization": "Token YOUR_TOKEN"}
data = {
    "new_title": "Copy of Math Quiz",
    "new_due_date": (datetime.now() + timedelta(days=14)).isoformat(),
    "randomize_questions": False
}

response = requests.post(url, json=data, headers=headers)
if response.status_code == 201:
    cloned_assignment = response.json()
    print(f"Cloned: {cloned_assignment['id']}")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

### JavaScript (fetch)
```javascript
const url = "https://api.example.com/api/assignments/1/clone/";
const token = "YOUR_TOKEN_HERE";

const data = {
  new_title: "Copy of Math Quiz",
  new_due_date: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
  randomize_questions: false
};

fetch(url, {
  method: "POST",
  headers: {
    "Authorization": `Token ${token}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify(data)
})
.then(r => r.json())
.then(cloned => console.log(`Cloned: ${cloned.id}`))
.catch(e => console.error(e));
```

## Permissions

**Who Can Clone**:
- ✅ Assignment creator (author)

**Who Cannot Clone**:
- ❌ Other teachers/tutors (get 403)
- ❌ Students (get 403)
- ❌ Anonymous users (get 401)

**After Cloning**:
- Cloned assignment author = requesting user
- Cloned assignment status = draft (unpublished)
- Cloned assignment assigned_to = empty (no students)

## Common Workflows

### Reuse Assignment from Last Semester
```json
{
  "new_due_date": "2026-01-15T18:00:00Z"
}
```

### Create Practice Version
```json
{
  "new_title": "Practice: Math Quiz",
  "randomize_questions": true
}
```

### Create Multiple Versions
```bash
# Clone original
curl ... -d '{"new_title": "Version A"}'
curl ... -d '{"new_title": "Version B"}'
curl ... -d '{"new_title": "Version C"}'
```

### Quick Clone (Use All Defaults)
```bash
curl -X POST /api/assignments/1/clone/ \
  -H "Authorization: Token TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
# Result: "Copy of Original Assignment" created in DRAFT status
```

## Logging

Every clone is logged for audit trail:
```
Assignment cloned: source=1 'Original Assignment',
clone=42 'Copy of Original Assignment', user=5, randomized=False
```

Check logs in:
- Application logs
- Database audit trail
- CloudWatch (if deployed)

## Status After Clone

New assignments are always created with:
- Status: `draft` (not published)
- Author: Currently authenticated user
- Assigned_to: Empty (no students)
- Submissions: Empty (no submissions yet)
- Created_at: Current timestamp
- Updated_at: Current timestamp

## Modifying Cloned Assignment

After cloning, you can:
```bash
# Modify title
PATCH /api/assignments/42/
{"title": "Updated Title"}

# Add students
POST /api/assignments/42/assign/
{"student_ids": [1, 2, 3]}

# Publish
PATCH /api/assignments/42/
{"status": "published"}

# Add/remove questions
POST /api/questions/
{"assignment": 42, ...}
```

## Tips

1. **Check clone success**: Look for 201 status code and new ID
2. **Use auto-title**: Omit new_title for quick cloning
3. **Randomize for practice**: Set randomize_questions=true for different versions
4. **Always publish later**: Cloned assignments start as DRAFT for safety
5. **Clear students**: Assign new students after cloning
6. **Review questions**: Check randomized options before publishing

## Troubleshooting

**403 Forbidden**
- ✓ Check if you created the original assignment
- ✓ Ensure you're logged in as the creator

**400 Bad Request**
- ✓ Check title length (max 200 chars)
- ✓ Check due_date format (ISO 8601)
- ✓ Check due_date is in future

**404 Not Found**
- ✓ Check assignment ID exists
- ✓ Verify you have permission to view assignment

**500 Internal Error**
- ✓ Check server logs
- ✓ Retry the request
- ✓ Contact support if persists

## API Reference

Full API documentation: `/api/docs/` or `/api/redoc/`

Related endpoints:
- `GET /api/assignments/{id}/` - Get assignment details
- `PATCH /api/assignments/{id}/` - Update assignment
- `DELETE /api/assignments/{id}/` - Delete assignment
- `POST /api/assignments/{id}/assign/` - Assign to students
