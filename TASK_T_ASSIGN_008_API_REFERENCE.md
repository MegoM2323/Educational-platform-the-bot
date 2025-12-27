# T_ASSIGN_008: Assignment Comments API Reference

## Quick Reference Guide

### Base URL
```
http://localhost:8000/api/assignments/
```

### Authentication
All endpoints require authentication. Use either:
- Token: `Authorization: Token <token>`
- Session: Cookie-based authentication

---

## Comment Endpoints

### List Comments for Submission
```http
GET /submissions/{submission_id}/comments/
```

**Parameters:**
- `submission_id` (path, required) - Submission ID
- `page` (query, optional) - Page number (default: 1)
- `page_size` (query, optional) - Results per page (default: 20)

**Response:**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "submission": 1,
      "author": 5,
      "author_name": "John Teacher",
      "text": "Great work!",
      "selection_text": null,
      "selection_start": null,
      "selection_end": null,
      "media_url": null,
      "media_type": "",
      "is_draft": false,
      "is_pinned": true,
      "is_deleted": false,
      "created_at": "2025-12-27T10:30:00Z",
      "updated_at": "2025-12-27T10:30:00Z",
      "published_at": "2025-12-27T10:30:00Z",
      "unread_count": 0
    }
  ]
}
```

**Permissions:**
- Teachers see all comments (including drafts)
- Students see only published comments

**Status Codes:**
- 200: Success
- 404: Submission not found

---

### Create Comment
```http
POST /submissions/{submission_id}/comments/
```

**Body:**
```json
{
  "submission": 1,
  "text": "Good work, but needs improvement",
  "selection_text": "This part",
  "selection_start": 50,
  "selection_end": 60,
  "media_url": "https://example.com/feedback.mp4",
  "media_type": "video",
  "is_draft": true,
  "is_pinned": false
}
```

**Required Fields:**
- `submission` - Submission ID
- `text` - Comment text (non-empty)

**Optional Fields:**
- `selection_text` - Text from submission (requires selection_start/end)
- `selection_start` - Start position (0-indexed)
- `selection_end` - End position
- `media_url` - External audio/video URL (must be https)
- `media_type` - "audio" or "video"
- `is_draft` - Boolean (default: false)
- `is_pinned` - Boolean (default: false)

**Validation Rules:**
- Text cannot be empty
- If selection_text provided, must have selection_start < selection_end
- Media URL must start with http:// or https://
- If media_type provided, media_url is required

**Response:**
```json
{
  "id": 1,
  "submission": 1,
  "author": 5,
  "author_name": "John Teacher",
  "text": "Good work, but needs improvement",
  "selection_text": "This part",
  "selection_start": 50,
  "selection_end": 60,
  "media_url": "https://example.com/feedback.mp4",
  "media_type": "video",
  "is_draft": true,
  "is_pinned": false,
  "is_deleted": false,
  "created_at": "2025-12-27T10:30:00Z",
  "updated_at": "2025-12-27T10:30:00Z",
  "published_at": null,
  "unread_count": 1
}
```

**Permissions:**
- Only teachers/tutors can create comments
- Students get 403 Forbidden

**Status Codes:**
- 201: Created
- 400: Validation error
- 403: Permission denied
- 404: Submission not found

---

### Get Comment Details
```http
GET /submissions/{submission_id}/comments/{comment_id}/
```

**Response:**
```json
{
  "id": 1,
  "submission": 1,
  "author": 5,
  "author_name": "John Teacher",
  "text": "Good work!",
  "acknowledgments": [
    {
      "id": 1,
      "comment": 1,
      "student": 3,
      "is_read": true,
      "read_at": "2025-12-27T11:00:00Z",
      "created_at": "2025-12-27T10:30:00Z",
      "updated_at": "2025-12-27T11:00:00Z"
    }
  ],
  "is_editable": true
}
```

**Permissions:**
- Authenticated users can view
- Students see only published comments

**Auto-updates:**
- Marks comment as read for student if viewing

**Status Codes:**
- 200: Success
- 403: Comment not visible to user
- 404: Comment not found

---

### Update Comment
```http
PATCH /submissions/{submission_id}/comments/{comment_id}/
```

**Body:**
```json
{
  "text": "Updated feedback",
  "is_draft": false,
  "is_pinned": true
}
```

**Editable Fields:**
- `text` - Comment text
- `is_draft` - Draft status
- `is_pinned` - Pinned status
- `selection_text` - Highlighted text
- `selection_start/end` - Selection positions
- `media_url` - Media link
- `media_type` - Media type

**Permissions:**
- Only comment author can update

**Status Codes:**
- 200: Success
- 403: Not the author
- 404: Comment not found

---

### Delete Comment (Soft Delete)
```http
DELETE /submissions/{submission_id}/comments/{comment_id}/
```

**Effect:**
- Sets `is_deleted = true`
- Comment hidden but not removed from database
- Can be restored later

**Permissions:**
- Only comment author

**Status Codes:**
- 204: Success (no content)
- 403: Not the author
- 404: Comment not found

---

### Publish Draft Comment
```http
POST /submissions/{submission_id}/comments/{comment_id}/publish/
```

**Effect:**
- Sets `is_draft = false`
- Sets `published_at = now()`
- Sends notification to student

**Response:**
```json
{
  "id": 1,
  "is_draft": false,
  "published_at": "2025-12-27T10:31:00Z",
  ...
}
```

**Permissions:**
- Only comment author
- Only works on draft comments

**Status Codes:**
- 200: Success
- 400: Comment not a draft
- 403: Not the author
- 404: Comment not found

---

### Toggle Pin
```http
POST /submissions/{submission_id}/comments/{comment_id}/toggle_pin/
```

**Effect:**
- Flips `is_pinned` status
- Pinned comments sort to top

**Response:**
```json
{
  "id": 1,
  "is_pinned": true,
  ...
}
```

**Permissions:**
- Only comment author

**Status Codes:**
- 200: Success
- 403: Not the author
- 404: Comment not found

---

### Mark Comment as Read
```http
POST /submissions/{submission_id}/comments/{comment_id}/mark_read/
```

**Effect:**
- Creates/updates SubmissionCommentAcknowledgment
- Sets `is_read = true`
- Records `read_at` timestamp

**Response:**
```json
{
  "id": 1,
  "comment": 1,
  "student": 3,
  "is_read": true,
  "read_at": "2025-12-27T11:00:00Z",
  ...
}
```

**Permissions:**
- Only the student who received comment

**Status Codes:**
- 200: Success
- 403: Not the student
- 404: Comment not found

---

## Template Endpoints

### List Comment Templates
```http
GET /comment-templates/
```

**Query Parameters:**
- `search` - Search in title, content, category
- `ordering` - Order by: `-is_shared`, `-usage_count`, `-updated_at`
- `page` - Page number
- `page_size` - Results per page

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "author": 5,
      "author_name": "John Teacher",
      "title": "Great work!",
      "content": "Excellent work. Keep it up!",
      "category": "positive",
      "is_shared": true,
      "is_active": true,
      "usage_count": 23,
      "created_at": "2025-12-20T10:00:00Z",
      "updated_at": "2025-12-27T10:00:00Z"
    }
  ]
}
```

**Visibility:**
- Shows own templates + shared templates
- Inactive templates hidden

**Status Codes:**
- 200: Success

---

### Create Template
```http
POST /comment-templates/
```

**Body:**
```json
{
  "title": "Great work!",
  "content": "This is excellent work. Please continue...",
  "category": "positive",
  "is_shared": true
}
```

**Required Fields:**
- `title` - Template name (non-empty)
- `content` - Template text (non-empty)

**Optional Fields:**
- `category` - Classification string
- `is_shared` - Boolean (default: false)

**Response:**
```json
{
  "id": 1,
  "author": 5,
  "author_name": "John Teacher",
  "title": "Great work!",
  "content": "This is excellent work...",
  "category": "positive",
  "is_shared": true,
  "is_active": true,
  "usage_count": 0,
  "created_at": "2025-12-27T10:00:00Z",
  "updated_at": "2025-12-27T10:00:00Z"
}
```

**Permissions:**
- Only teachers/tutors

**Status Codes:**
- 201: Created
- 400: Validation error
- 403: Not a teacher

---

### Get Template
```http
GET /comment-templates/{template_id}/
```

**Status Codes:**
- 200: Success
- 404: Template not found

---

### Update Template
```http
PATCH /comment-templates/{template_id}/
```

**Permissions:**
- Only template author

**Status Codes:**
- 200: Success
- 403: Not the author
- 404: Template not found

---

### Delete Template
```http
DELETE /comment-templates/{template_id}/
```

**Effect:**
- Sets `is_active = false` (soft delete)

**Permissions:**
- Only template author

**Status Codes:**
- 204: Success
- 403: Not the author
- 404: Template not found

---

### Use Template
```http
POST /comment-templates/{template_id}/use/
```

**Effect:**
- Increments `usage_count`
- Returns template content for copying

**Response:**
```json
{
  "id": 1,
  "title": "Great work!",
  "content": "This is excellent work...",
  "usage_count": 24
}
```

**Status Codes:**
- 200: Success
- 404: Template not found

---

## Error Responses

### 400 Bad Request
```json
{
  "field_name": ["Error message"],
  "text": ["Comment text cannot be empty"]
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

---

## Examples

### Create and Publish a Comment
```bash
# 1. Create draft comment
curl -X POST http://localhost:8000/api/assignments/submissions/1/comments/ \
  -H "Authorization: Token abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "submission": 1,
    "text": "Good work!",
    "is_draft": true
  }'

# 2. Publish when ready
curl -X POST http://localhost:8000/api/assignments/submissions/1/comments/1/publish/ \
  -H "Authorization: Token abc123"
```

### Create Inline Comment
```bash
curl -X POST http://localhost:8000/api/assignments/submissions/1/comments/ \
  -H "Authorization: Token abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "submission": 1,
    "text": "This needs improvement",
    "selection_text": "the problematic part",
    "selection_start": 25,
    "selection_end": 45
  }'
```

### Add Media Feedback
```bash
curl -X POST http://localhost:8000/api/assignments/submissions/1/comments/ \
  -H "Authorization: Token abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "submission": 1,
    "text": "Check the video feedback",
    "media_url": "https://example.com/feedback.mp4",
    "media_type": "video"
  }'
```

### Use Template
```bash
curl -X POST http://localhost:8000/api/comment-templates/5/use/ \
  -H "Authorization: Token abc123"
```

---

## Permissions Summary

| Action | Student | Teacher | Tutor | Admin |
|--------|---------|---------|-------|-------|
| List comments | View published only | All comments | All comments | All |
| Create comment | Denied | Allowed | Allowed | Allowed |
| Edit own comment | N/A | Allowed | Allowed | Allowed |
| Edit others comment | Denied | Denied | Denied | Allowed |
| Delete own comment | N/A | Allowed (soft) | Allowed (soft) | Allowed |
| Publish draft | N/A | Own only | Own only | All |
| Pin comment | N/A | Own only | Own only | All |
| Mark as read | Own comments | Own comments | Own comments | All |
| View templates | Denied | Own + shared | Own + shared | All |
| Create template | Denied | Allowed | Allowed | Allowed |
| Use template | Denied | Allowed | Allowed | Allowed |

---

## Rate Limiting

(Can be enabled via settings)
- Comment creation: 10 per minute
- Template creation: 5 per minute
- General API: 100 per minute

---

## Pagination

Default: 20 items per page
Query parameters:
- `page=2` - Get page 2
- `page_size=50` - Get 50 items per page (max 100)

Response format:
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/...?page=2",
  "previous": null,
  "results": [...]
}
```

