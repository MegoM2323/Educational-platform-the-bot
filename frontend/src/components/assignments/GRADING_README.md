# Grading Interface Components

Complete implementation of a teacher-facing grading interface for reviewing and grading student assignment submissions.

## Components

### 1. GradingPanel (Main Page)
**Location**: `frontend/src/pages/GradingPanel.tsx`

The main page component that provides a split-pane interface for grading submissions.

#### Features
- **Left Pane**: Submission list with search and filter
- **Right Pane**: Grading form and history
- **Statistics**: Total submissions, pending, graded, returned counts
- **Search**: By student name or email (case-insensitive)
- **Filter**: By submission status (submitted, graded, returned)
- **Responsive**: Two-column on desktop, single column on mobile

#### Props
```typescript
// No props required - uses URL params
// Access via: /grading/:assignmentId
```

#### Usage
```tsx
import { BrowserRouter } from 'react-router-dom';
import GradingPanel from '@/pages/GradingPanel';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/grading/:assignmentId" element={<GradingPanel />} />
      </Routes>
    </BrowserRouter>
  );
}
```

---

### 2. GradingForm
**Location**: `frontend/src/components/assignments/GradingForm.tsx`

Component for grading a single submission with auto-grade support and late penalty handling.

#### Features
- **Auto-Grade Display**: Shows auto-graded score with breakdown
- **Manual Override**: Switch to manual grading mode
- **Late Penalty**: Detects and displays late submission penalties
- **Feedback**: Multi-line textarea for teacher feedback
- **Grade Summary**: Score, percentage, and letter grade display
- **Actions**: Save grade or return for rework

#### Props
```typescript
interface GradingFormProps {
  submission: AssignmentSubmission;
  assignment?: Assignment;
  onGradingComplete?: () => void;
}
```

#### Usage
```tsx
import { GradingForm } from '@/components/assignments/GradingForm';

export function MyComponent() {
  return (
    <GradingForm
      submission={selectedSubmission}
      assignment={assignment}
      onGradingComplete={() => loadNextSubmission()}
    />
  );
}
```

#### Behavior
- Displays auto-grade (if available) with option to override
- Detects late submissions and calculates penalty
- Allows custom penalty override
- Grade letter calculation: A(90%+), B(80%+), C(70%+), D(60%+), F(<60%)
- Feedback max 5000 characters

---

### 3. SubmissionAnswerDisplay
**Location**: `frontend/src/components/assignments/SubmissionAnswerDisplay.tsx`

Component to display student answers in a readable format.

#### Features
- **Question-Answer Pairs**: Shows each question with student answer
- **Status Indicators**: Correct (green), incorrect (red), unknown (gray)
- **Expandable Answers**: Click to expand and see full answer
- **Correct Answer Comparison**: Shows correct answer for wrong answers
- **File Attachments**: Tab for viewing attached submission files
- **Statistics**: Answer count, correct/incorrect breakdown

#### Props
```typescript
interface SubmissionAnswerDisplayProps {
  submission: AssignmentSubmission;
}
```

#### Usage
```tsx
import { SubmissionAnswerDisplay } from '@/components/assignments/SubmissionAnswerDisplay';

export function MyComponent() {
  return (
    <SubmissionAnswerDisplay submission={selectedSubmission} />
  );
}
```

#### Display Format
- Question type badges (Multiple choice, Text, Numeric, etc.)
- Points earned/max points for each question
- Expandable sections with full answer text
- Comparison view for incorrect answers

---

### 4. GradeHistoryView
**Location**: `frontend/src/components/assignments/GradeHistoryView.tsx`

Component to display the complete grade history for a submission.

#### Features
- **Grade Timeline**: All grading events in chronological order
- **Grader Info**: Name, email, date/time of grading
- **Score Progression**: Track how grades changed
- **Improvement Metrics**: Percentage improvement calculation
- **Feedback History**: All comments from all graders
- **Statistics**: Latest grade, average, attempt count, improvement %

#### Props
```typescript
interface GradeHistoryViewProps {
  submission: AssignmentSubmission;
}
```

#### Usage
```tsx
import { GradeHistoryView } from '@/components/assignments/GradeHistoryView';

export function MyComponent() {
  return (
    <GradeHistoryView submission={selectedSubmission} />
  );
}
```

#### Display Elements
- Timeline cards for each grading event
- Statistics summary box
- Feedback comments section
- Status progression log

---

## Working Together

### Full Grading Workflow

```tsx
import { GradingPanel } from '@/pages/GradingPanel';

// In your router:
<Route path="/grading/:assignmentId" element={<GradingPanel />} />

// GradingPanel then uses:
// - GradingForm for inputting grades
// - SubmissionAnswerDisplay for viewing answers
// - GradeHistoryView for seeing previous grades
```

### Component Interaction
1. **GradingPanel** manages overall state and submission list
2. User selects submission from list
3. **SubmissionAnswerDisplay** shows student answers
4. **GradingForm** handles grade input
5. After grading, **GradeHistoryView** shows history

---

## Styling & Responsive Design

All components use the shadcn/ui component library and Tailwind CSS.

### Breakpoints
- **Mobile**: < 640px (single column)
- **Tablet**: 640px - 1024px (vertical stack)
- **Desktop**: > 1024px (side-by-side layout)

### Color Scheme
- **Success (Green)**: Correct answers, passing grades
- **Danger (Red)**: Incorrect answers, failing grades
- **Warning (Orange)**: Late submissions, needs attention
- **Info (Blue)**: Selected items, interactive elements

---

## Data Models

### AssignmentSubmission
```typescript
interface AssignmentSubmission {
  id: number;
  assignment: number;
  student: {
    id: number;
    email: string;
    full_name: string;
  };
  content: string;
  file?: string;
  status: 'submitted' | 'graded' | 'returned';
  score?: number;
  max_score?: number;
  percentage?: number;
  feedback: string;
  submitted_at: string;
  graded_at?: string;
  updated_at: string;
}
```

### GradeSubmissionPayload
```typescript
interface GradeSubmissionPayload {
  score: number;          // Final score after penalties
  feedback?: string;      // Teacher feedback
  status?: 'graded' | 'returned';  // Grade or return for rework
}
```

---

## API Integration

The components use React Query and the following hooks:

- `useAssignment(id)`: Get assignment details
- `useAssignmentSubmissions(id)`: Get all submissions
- `useGradeSubmission(id)`: Submit grade

### Example API Calls
```typescript
// GET /api/assignments/:id
// Returns: Assignment

// GET /api/assignments/:id/submissions
// Returns: AssignmentSubmission[]

// POST /api/submissions/:id/grade
// Payload: GradeSubmissionPayload
// Returns: AssignmentSubmission
```

---

## Testing

Comprehensive test suite included: `GradingPanel.test.tsx`

### Test Coverage
- Rendering and UI elements
- Submission list display and selection
- Search and filter functionality
- Grading form submission
- Grade history display
- Responsive layout
- Error handling

### Running Tests
```bash
cd frontend
npm test GradingPanel.test.tsx
npm test GradingForm.test.tsx
npm test SubmissionAnswerDisplay.test.tsx
npm test GradeHistoryView.test.tsx
```

---

## Accessibility

All components meet WCAG 2.1 AA standards:

- ✅ ARIA labels on interactive elements
- ✅ Keyboard navigation support
- ✅ Tab order follows logical flow
- ✅ Color not sole indicator (uses icons/badges)
- ✅ Screen reader friendly status messages
- ✅ High contrast mode compatible
- ✅ Focus indicators visible
- ✅ Error messages linked to form fields

---

## Internationalization

All UI text is in Russian. To support other languages:

1. Extract all strings to i18n JSON files
2. Use `useTranslation()` hook from react-i18next
3. Replace hardcoded strings with translation keys

Example:
```typescript
import { useTranslation } from 'react-i18next';

export const GradingForm = () => {
  const { t } = useTranslation('grading');

  return (
    <Button>{t('actions.saveGrade')}</Button>
  );
};
```

---

## Performance Optimization

### Techniques Used
1. **React Query Caching**: 60-second stale time for submissions
2. **Memoization**: `useMemo` for filtered submissions
3. **ScrollArea**: Efficient large list rendering
4. **Lazy Loading**: Details loaded on selection
5. **Callback Memoization**: `useCallback` for event handlers

### Optimization Tips
- Increase query stale time if submissions change infrequently
- Use `React.memo` to memoize submission list items
- Consider pagination for very large submission lists (1000+)

---

## Troubleshooting

### Issue: Submissions not loading
- Check that assignment ID is valid and exists
- Verify API endpoint is working
- Check browser console for error messages

### Issue: Grading form not submitting
- Verify score is between 0 and max_score
- Check feedback length (max 5000 characters)
- Ensure user has teacher role

### Issue: Late penalty not displaying
- Check that assignment.due_date is set
- Verify submitted_at is after due_date
- Check browser timezone settings

### Issue: Grade history not showing
- Verify submission has been graded before (graded_at is set)
- Check that feedback was saved
- Look for API errors in console

---

## Future Enhancements

- [ ] Rubric-based grading UI
- [ ] Batch grading shortcuts (Ctrl+S)
- [ ] Grade templates/quick responses
- [ ] Plagiarism detection
- [ ] Student feedback notifications
- [ ] Grade appeals workflow
- [ ] Peer review features
- [ ] Voice/video feedback

---

## File Structure

```
frontend/src/
├── pages/
│   ├── GradingPanel.tsx                  # Main page
│   ├── GradingPanel.example.tsx          # Usage examples
│   └── __tests__/
│       └── GradingPanel.test.tsx         # Page tests
└── components/
    └── assignments/
        ├── GradingForm.tsx                # Grading form
        ├── SubmissionAnswerDisplay.tsx    # Answer display
        ├── GradeHistoryView.tsx           # History view
        ├── GRADING_README.md              # This file
        └── __tests__/
            └── GradingPanel.test.tsx      # Component tests
```

---

## Summary

The Grading Interface provides a complete, production-ready solution for teachers to grade student assignments. With features like auto-grading, late penalty handling, and comprehensive feedback tools, it streamlines the grading workflow while providing detailed analytics and history tracking.
