# Assignment Submission UI Components

Complete assignment submission interface for students in the THE_BOT educational platform.

## Components Overview

### 1. AssignmentSubmitForm

Main form component for submitting assignment responses with comprehensive validation and UX features.

**Features:**
- Drag-and-drop file upload
- File type/size validation (14 file types supported)
- Auto-save draft to localStorage
- Character counter for text responses
- Progress indicator for multi-question assignments
- Time limit and attempts warnings
- Submission confirmation dialog
- Support for multiple file uploads (up to 10 files, 200MB total)

**Props:**
```typescript
interface SubmissionFormProps {
  assignment: Assignment;
  questionCount?: number;
  onSubmit: (data: SubmissionFormData, files: File[]) => Promise<void>;
  isLoading?: boolean;
  showConfirmation?: boolean;
}
```

**Usage:**
```tsx
import { AssignmentSubmitForm } from '@/components/assignments/AssignmentSubmitForm';

const handleSubmit = async (data, files) => {
  await submitAssignmentAPI(data, files);
};

<AssignmentSubmitForm
  assignment={assignment}
  questionCount={10}
  onSubmit={handleSubmit}
  showConfirmation={true}
/>
```

### 2. AssignmentSubmit Page

Full page component for assignment submission with all necessary context and controls.

**Features:**
- Assignment header with instructions
- Due date countdown with visual warnings
- Attempts tracking and history
- Submission history with scores
- Responsive layout (mobile/tablet/desktop)
- Navigation back to assignments list
- Time remaining calculation
- Overdue handling

**Route:**
```tsx
<Route path="/assignment/:assignmentId/submit" element={<AssignmentSubmit />} />
```

**Usage:**
```tsx
import { AssignmentSubmit } from '@/pages/AssignmentSubmit';

// Used in router configuration
```

### 3. SubmissionHistory

Component displaying all submission attempts with scores and metadata.

**Features:**
- Submission attempts list with dates
- Score display with progress bars
- Time spent tracking
- File count indicators
- Summary statistics
- Color-coded score indicators
- View details and download options

**Props:**
```typescript
interface SubmissionHistoryProps {
  submissions: SubmissionHistoryItem[];
  isLoading?: boolean;
  onViewDetails?: (submissionId: number) => void;
  onDownloadFile?: (submissionId: number) => void;
}
```

**Usage:**
```tsx
import { SubmissionHistory } from '@/components/assignments/SubmissionHistory';

<SubmissionHistory
  submissions={submissions}
  onViewDetails={handleViewDetails}
  onDownloadFile={handleDownload}
/>
```

### 4. QuestionNavigator

Sidebar component for navigating between questions in multi-question assignments.

**Features:**
- Question list with progress indicators
- Answer status visualization
- Time tracking per question
- Flagging for review
- Progress bar
- Stats display (points, progress)
- Keyboard navigation support
- Responsive scrolling

**Props:**
```typescript
interface QuestionNavigatorProps {
  questions: Question[];
  currentQuestionId?: number | string;
  answeredQuestions?: (number | string)[];
  flaggedQuestions?: (number | string)[];
  timePerQuestion?: Record<number | string, number>;
  onSelectQuestion: (questionId: number | string) => void;
  disabled?: boolean;
}
```

**Usage:**
```tsx
import { QuestionNavigator } from '@/components/assignments/QuestionNavigator';

<QuestionNavigator
  questions={questions}
  currentQuestionId={currentId}
  answeredQuestions={answered}
  onSelectQuestion={handleSelectQuestion}
/>
```

## Custom Hooks

### useSubmissionTracking

Hook for managing submission attempts, answers, and time tracking.

**Features:**
- Attempt tracking with timestamps
- Answer storage and retrieval
- Time spent calculation
- Attempt history
- Draft persistence
- File management

**Usage:**
```tsx
import { useSubmissionTracking } from '@/hooks/useSubmissionTracking';

const {
  tracking,
  startAttempt,
  updateAnswer,
  addFile,
  removeFile,
  completeAttempt,
  currentTimeSpentFormatted,
  totalTimeSpentFormatted,
} = useSubmissionTracking(assignmentId);

// Start new attempt
startAttempt();

// Update answer
updateAnswer('question-1', 'My answer');

// Add file
addFile(file);

// Complete attempt
completeAttempt(true); // true = submitted, false = failed
```

## File Upload Specifications

### Supported File Types (14 types)
- Documents: pdf, doc, docx, txt
- Spreadsheets: xlsx, xls
- Presentations: ppt, pptx
- Images: jpg, jpeg, png, gif
- Archives: zip, rar, 7z

### Size Limits
- Per file: 50MB
- Total per submission: 200MB
- Maximum files: 10

### Validation
- MIME type checking
- File extension validation
- Size validation
- Filename sanitization

## Submission Confirmation

When `showConfirmation={true}`, a dialog appears before submission showing:
- Number of answered questions
- Number of uploaded files
- Total file size
- Warning if not all questions are answered

## Draft Auto-Save

The form automatically saves drafts to localStorage every 1 second with:
- Timestamp
- Current answers
- Notes text
- Draft recovery on page reload

Storage key: `assignment-draft-{assignmentId}`

## Time Tracking

The form displays:
- Time remaining until due date
- Warning at < 24 hours
- Critical alert at < 1 hour
- Overdue status when time runs out

## Responsive Design

All components are fully responsive:
- Mobile: Vertical layout, touch-optimized
- Tablet: 2-column layout possible
- Desktop: Full sidebar navigation

## Accessibility

- ARIA labels on all inputs
- Keyboard navigation support
- Color-coded status (not color-only)
- Focus management
- Screen reader friendly

## Testing

Comprehensive test suite includes:
- Form submission flow
- File upload validation
- Draft auto-save
- Time tracking
- Confirmation dialog
- Error handling
- Mobile responsiveness

Run tests:
```bash
npm test -- AssignmentSubmitForm.test.tsx
```

## Examples

See `AssignmentSubmitForm.example.tsx` for 5 complete usage examples:
1. Simple essay submission
2. Quiz with time limit
3. Project submission with files
4. Form with validation
5. Full multi-part assignment flow

## Integration with API

The components expect these API endpoints:

```typescript
// Get assignment
GET /api/assignments/{id}/

// Get submissions
GET /api/assignments/{id}/submissions/

// Submit assignment
POST /api/assignments/{id}/submit/
Body: { content: string, file?: File }

// Get questions
GET /api/assignments/questions/?assignment={id}

// Get answers
GET /api/submissions/{id}/answers/
```

## Error Handling

The form includes comprehensive error handling:
- Network errors with retry
- Validation errors inline
- File upload errors
- Submission timeout handling
- Draft save failures

## Styling

Uses Tailwind CSS with custom UI components from `@/components/ui/`:
- Card
- Button
- Input/Textarea
- Dialog
- Badge
- Progress
- Tabs
- ScrollArea

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile browsers: iOS Safari 13+, Chrome Mobile

## Performance

- Lazy loading of questions
- Virtualized scrolling in question navigator
- Debounced draft auto-save
- Memoized components
- Optimized re-renders

## Internationalization

All text is in Russian. For other languages:
1. Replace hardcoded strings with i18n keys
2. Use date-fns locale utilities
3. Adjust time formatting

## Future Enhancements

Potential improvements:
- Real-time collaboration
- Offline-first support
- Voice recording for answers
- Mathematical equation editor
- Code syntax highlighting
- Video recording
- AI-powered answer suggestions
