# Integration Guide - T_ASN_010: Assignment Submission UI

This guide explains how to integrate the Assignment Submission UI components with your backend API.

## Components Checklist

- [x] AssignmentSubmitForm.tsx - Main submission form
- [x] AssignmentSubmit.tsx - Full page component
- [x] SubmissionHistory.tsx - Submission history display
- [x] QuestionNavigator.tsx - Question sidebar
- [x] useSubmissionTracking.ts - Custom hook for tracking

## Integration Steps

### 1. Routing Setup

Add the following route to your router configuration:

```typescript
// In your main router file (e.g., src/App.tsx or src/routes/index.tsx)
import { AssignmentSubmit } from '@/pages/AssignmentSubmit';

const routes = [
  {
    path: '/assignment/:assignmentId/submit',
    element: <AssignmentSubmit />,
    requireAuth: true,
    allowedRoles: ['student'],
  },
  // ... other routes
];
```

### 2. Update API Integration

The components expect these API endpoints. Ensure your backend has:

```typescript
// Get assignment details
GET /api/assignments/assignments/{id}/
Response: Assignment object

// Get submission history
GET /api/assignments/assignments/{assignmentId}/submissions/
Response: AssignmentSubmission[]

// Submit assignment
POST /api/assignments/assignments/{assignmentId}/submit/
Body: FormData {
  content: string,
  file?: File
}
Response: AssignmentSubmission

// Get questions for assignment
GET /api/assignments/questions/?assignment={id}
Response: AssignmentQuestion[]

// Get answers for submission
GET /api/assignments/submissions/{submissionId}/answers/
Response: AssignmentAnswer[]
```

### 3. Verify Existing Hooks

The implementation uses existing hooks from `useAssignments`. Verify these are working:

```typescript
// In frontend/src/hooks/useAssignments.ts
export const useAssignment = (id: number) => { /* ... */ };
export const useSubmitAssignment = (assignmentId: number) => { /* ... */ };
export const useAssignmentSubmissions = (assignmentId: number) => { /* ... */ };
```

All hooks should already exist and be integrated with React Query.

### 4. Update Student Dashboard

Add link to assignment submission page in student dashboard:

```typescript
// In your student assignments component
import { useNavigate } from 'react-router-dom';

const StudentAssignments: React.FC = () => {
  const navigate = useNavigate();

  const handleSubmit = (assignmentId: number) => {
    navigate(`/assignment/${assignmentId}/submit`);
  };

  return (
    <div>
      {/* Assignment list */}
      {assignments.map(assignment => (
        <Button
          onClick={() => handleSubmit(assignment.id)}
        >
          Отправить ответы
        </Button>
      ))}
    </div>
  );
};
```

### 5. Backend API Requirements

#### AssignmentSubmitForm Expects

```typescript
interface Assignment {
  id: number;
  title: string;
  description: string;
  instructions: string;
  type: 'homework' | 'test' | 'project' | 'essay' | 'practical';
  status: 'draft' | 'published' | 'closed';
  max_score: number;
  time_limit?: number;        // minutes
  attempts_limit: number;
  start_date: string;          // ISO date
  due_date: string;            // ISO date
  tags: string;
  difficulty_level: number;
  author: { id: number; email: string; full_name: string };
  assigned_to: number[];
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
}
```

#### File Upload Handling

The form sends files via FormData:

```typescript
const formData = new FormData();
formData.append('content', textContent);
files.forEach(file => {
  formData.append('files', file);
});

// Or if single file:
formData.append('file', file);
```

Backend should:
- Accept multipart/form-data
- Validate file types (whitelist)
- Validate file sizes (max 50MB each, 200MB total)
- Scan for malware (optional, recommended)
- Store files securely
- Return file URLs or IDs

#### Time Limit Handling

If `time_limit` is set:
- Validate submission time doesn't exceed limit
- Track time spent per submission
- Warn user at thresholds

#### Attempts Limit

- Enforce maximum attempts
- Don't allow submission after limit reached
- Return appropriate error (409 Conflict)
- Show remaining attempts to user

### 6. Error Handling

The form handles these HTTP responses:

```typescript
// Success
200 OK - Submission saved
201 Created - Submission created

// Client Errors
400 Bad Request - Validation error (invalid file type, size, etc.)
409 Conflict - Attempt limit reached
429 Too Many Requests - Rate limited

// Server Errors
500 Internal Server Error - Server error
503 Service Unavailable - Maintenance
504 Gateway Timeout - Timeout
```

Ensure your API returns appropriate status codes with error messages.

### 7. Draft Auto-Save Implementation

The form auto-saves to localStorage. To sync with backend:

```typescript
// Optional: Override auto-save to sync with backend
const handleDraftSave = async (draft: DraftData) => {
  await api.post(`/assignments/${assignmentId}/draft/`, draft);
};
```

Add endpoint if desired:
```
POST /api/assignments/{id}/draft/
Body: { answers: {}, notes: string }
Response: { success: boolean }
```

### 8. Submission Confirmation

The confirmation dialog shows:
- Number of answered questions
- Number of uploaded files
- Total file size
- Warning if not all questions answered

Customize in `AssignmentSubmitForm.tsx` lines 350-400.

### 9. Submission History

The `SubmissionHistory` component expects:

```typescript
interface SubmissionHistoryItem {
  id: number;
  attemptNumber: number;
  submittedAt: string;
  status: 'submitted' | 'graded' | 'returned';
  score?: number;
  maxScore?: number;
  feedback?: string;
  timeSpent?: number;        // seconds
  filesCount?: number;
  answersCount?: number;
}
```

Data comes from:
```
GET /api/assignments/{id}/submissions/
```

### 10. Time Remaining Calculation

The page calculates remaining time based on `due_date`:

```typescript
const now = new Date();
const dueDate = new Date(assignment.due_date);
const remaining = dueDate - now;
```

Warnings appear at:
- < 72 hours: "Скоро"
- < 24 hours: Yellow warning
- < 1 hour: Red critical warning
- After deadline: "Просрочено"

### 11. Responsive Images

Add responsive images for assignment files:

```typescript
// In SubmissionHistory or submission detail
<img
  src={filePreviewUrl}
  alt={fileName}
  className="max-w-full h-auto"
  loading="lazy"
/>
```

### 12. Accessibility Setup

All components include ARIA labels. Ensure:
- Form labels are properly associated
- Buttons have clear labels
- Color is not the only status indicator
- Keyboard navigation works
- Screen readers can announce all content

### 13. Mobile Testing

Test on devices/emulators:
- iPhone 12/13/14
- iPad Mini
- Android phones (Samsung, Google Pixel)
- Landscape and portrait modes

Key things to test:
- File upload on mobile
- Drag-and-drop (may not work on mobile)
- Form scrolling and layout
- Touch targets (min 44x44px)

### 14. Performance Optimization

For large assignments:
- Paginate question list (show 10 at a time)
- Lazy load question navigator
- Virtualize submission history if >100 items
- Optimize file uploads (chunked upload for large files)

### 15. Notification Integration

When submission succeeds, optionally notify:

```typescript
// In AssignmentSubmit.tsx after successful submission
const showNotification = () => {
  toast.success('Ваш ответ успешно отправлен!');
};
```

Or send server-side notifications:
```
POST /api/notifications/
Body: {
  user_id: studentId,
  type: 'assignment_submitted',
  title: 'Ответ отправлен',
  message: `Ваш ответ на задание "${assignmentTitle}" успешно отправлен`
}
```

### 16. Analytics/Logging

Track submission metrics:

```typescript
// Log submission event
analytics.track('assignment_submitted', {
  assignmentId: assignment.id,
  assignmentType: assignment.type,
  filCount: files.length,
  timeSpent: submissionTime,
  attempts: attemptNumber,
});
```

## Testing the Integration

### Manual Testing Checklist

- [ ] Load assignment submission page
- [ ] Fill form with text
- [ ] Auto-save draft indicator appears
- [ ] Upload single file
- [ ] Upload multiple files
- [ ] Remove file
- [ ] Attempt drag-and-drop
- [ ] See time remaining update
- [ ] See progress indicator
- [ ] Click submit → confirmation appears
- [ ] Confirm submission → submits and shows success
- [ ] Check draft deleted from localStorage
- [ ] Check submission history displays
- [ ] Test on mobile device
- [ ] Test keyboard navigation
- [ ] Test accessibility (screen reader)

### Automated Testing

```bash
# Run test suite
npm test -- AssignmentSubmitForm.test.tsx

# Watch mode
npm test -- AssignmentSubmitForm.test.tsx --watch

# Coverage
npm test -- AssignmentSubmitForm.test.tsx --coverage
```

### API Testing with Postman/Insomnia

```
POST /api/assignments/assignments/1/submit/
Content-Type: multipart/form-data

Body:
- content: "My essay text"
- files: [file.pdf]

Expected Response:
{
  "id": 123,
  "assignment": 1,
  "student": { ... },
  "content": "My essay text",
  "status": "submitted",
  "submitted_at": "2025-12-27T10:30:00Z",
  "file": "https://..."
}
```

## Troubleshooting

### Form doesn't submit
- Check API endpoint is correct
- Verify authentication token is valid
- Check browser console for errors
- Check network tab in DevTools

### File upload fails
- Verify file size < 50MB
- Check file type is in whitelist
- Verify total size < 200MB
- Check file count < 10

### Draft not saving
- Check localStorage is enabled
- Check browser quota (usually 5-10MB)
- Clear localStorage if corrupted
- Check browser console for errors

### Time remaining not updating
- Check due_date format is ISO
- Check server time is synchronized
- Verify useEffect is running
- Check interval is set correctly (60s)

### Submission history empty
- Verify API endpoint returns data
- Check assignment ID is correct
- Verify user has permission to view
- Check API response format

### Mobile layout broken
- Check Tailwind CSS responsive classes
- Test on actual device or emulator
- Check viewport meta tag in HTML
- Verify touch targets are 44x44px+

## Deployment Checklist

- [ ] All files created and in correct locations
- [ ] Routes configured
- [ ] API endpoints implemented
- [ ] Backend validation in place
- [ ] File upload service configured
- [ ] localStorage permissions set
- [ ] HTTPS enforced (if on production)
- [ ] CORS headers configured
- [ ] Rate limiting configured
- [ ] Error logging setup
- [ ] Analytics tracking added
- [ ] Mobile tested
- [ ] Accessibility audit passed
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Team notified of new feature

## Support & Maintenance

For issues or questions:
1. Check README.md in components directory
2. Review test cases for usage examples
3. Check browser console for errors
4. Verify API responses match expected format
5. Test with mock data if needed

## Version History

- **v1.0.0** (2025-12-27)
  - Initial release
  - Basic form submission
  - File upload with validation
  - Draft auto-save
  - Submission history
  - Question navigator
  - Time tracking

Future versions may include:
- Real-time collaboration
- Offline-first support
- Rich text editor
- Voice/video recording
- Mathematical notation
