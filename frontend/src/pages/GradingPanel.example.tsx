/**
 * Grading Interface Example & Usage Guide
 *
 * This file demonstrates how to use the Grading Interface components
 * and the complete workflow for teachers grading student submissions.
 *
 * ## Usage Scenarios
 *
 * ### Scenario 1: Basic Grading Workflow
 * 1. Teacher navigates to /grading/:assignmentId
 * 2. GradingPanel displays all submissions for the assignment
 * 3. Teacher selects a submission from the left panel
 * 4. Right panel shows student answer and grading form
 * 5. Teacher either:
 *    - Accepts auto-grade (if available)
 *    - Overrides auto-grade with manual score
 * 6. Teacher adds feedback
 * 7. Teacher clicks "Save grade" or "Return for rework"
 * 8. System automatically moves to next submission
 *
 * ### Scenario 2: Late Submission Handling
 * - System detects late submission (submitted_at > due_date)
 * - Shows orange warning: "Ответ отправлен с опозданием на X дней"
 * - Auto-calculates penalty: 5% per day (customizable)
 * - Teacher can override penalty with custom amount
 * - Penalty is applied to final grade automatically
 *
 * ### Scenario 3: Batch Grading
 * - Filter by "На проверке" (submitted status)
 * - Grade each submission in sequence
 * - Component auto-selects next submission after each grade
 * - Teacher can quickly process multiple submissions
 *
 * ### Scenario 4: Grade History Review
 * - Switch to "История оценок" tab
 * - View all previous grading attempts
 * - See grader information and timestamps
 * - Review all feedback and comments
 * - Track score progression and improvements
 *
 * ## Component Structure
 *
 * GradingPanel (Main Page)
 * ├── Left Panel (Submission List)
 * │   ├── Statistics (total, submitted, graded, returned)
 * │   ├── Search Input
 * │   ├── Filter Dropdown
 * │   └── Submission List Items
 * │       └── SubmissionListItem
 * │           ├── Student name & email
 * │           ├── Status badge
 * │           └── Score (if graded)
 * └── Right Panel (Grading)
 *     ├── Tabs (Grading / History)
 *     ├── Student Info Card
 *     ├── SubmissionAnswerDisplay
 *     │   ├── Auto-grade breakdown
 *     │   ├── Question-answer pairs
 *     │   └── File attachments
 *     ├── GradingForm
 *     │   ├── Late penalty warning
 *     │   ├── Auto-grade display
 *     │   ├── Manual grade input
 *     │   ├── Grade summary (score/percentage/letter)
 *     │   ├── Penalty override
 *     │   └── Feedback textarea
 *     └── GradeHistoryView
 *         ├── Grade timeline
 *         ├── Statistics summary
 *         └── Feedback comments
 *
 * ## API Integration
 *
 * The component uses these hooks:
 * - useAssignment(id): Get assignment details
 * - useAssignmentSubmissions(id): Get all submissions for assignment
 * - useGradeSubmission(id): Submit grade for submission
 *
 * API Endpoints:
 * - GET /api/assignments/{id}/ - Get assignment
 * - GET /api/assignments/{id}/submissions/ - Get submissions
 * - POST /api/submissions/{id}/grade/ - Submit grade
 *
 * Payload for grading:
 * {
 *   score: number,          // Final score after penalties
 *   feedback?: string,      // Teacher feedback (max 5000 chars)
 *   status: 'graded' | 'returned'  // Grade or return for rework
 * }
 *
 * ## Features
 *
 * ### Search & Filter
 * - Search by student name (case-insensitive)
 * - Search by student email
 * - Filter by submission status
 * - Real-time filtering as user types
 *
 * ### Auto-Grading
 * - Displays auto-graded score with breakdown
 * - Shows points per question
 * - Teacher can accept or override
 * - Override preserves manual input
 *
 * ### Late Submission Handling
 * - Auto-detects late submissions
 * - Shows days late and penalty amount
 * - Default penalty: 5% per day
 * - Teacher can override with custom penalty
 * - Penalty applied to final effective score
 *
 * ### Grade Display
 * - Score in points (e.g., "85 / 100")
 * - Percentage (e.g., "85%")
 * - Letter grade (A-F based on percentage)
 * - Color-coded by performance
 *   - Green (A/B): Passing grades
 *   - Orange (C/D): Low passing
 *   - Red (F): Failing
 *
 * ### Feedback
 * - Multi-line textarea for detailed comments
 * - Character counter (max 5000)
 * - Preserved across grading sessions
 * - Full feedback history in grade history tab
 *
 * ### Grade Actions
 * - Save Grade: Mark as "graded" and move forward
 * - Return for Rework: Mark as "returned" for student to fix
 *
 * ### Batch Operations
 * - After grading, automatically select next ungraded submission
 * - Teacher can process multiple submissions quickly
 * - No need to manually select next submission
 *
 * ### Grade History
 * - Complete timeline of all grading events
 * - Shows grader name, email, date/time
 * - Displays score progression
 * - Shows improvement percentage
 * - Lists all feedback comments
 *
 * ## Responsive Design
 *
 * ### Desktop (lg and above)
 * - Two-column layout: left panel + right panel
 * - Side-by-side submission list and grading form
 * - Optimal for efficient batch grading
 *
 * ### Tablet (sm-lg)
 * - Stack panels vertically
 * - Full-width submission list
 * - Below it, full-width grading form
 *
 * ### Mobile
 * - Single column layout
 * - May require scrolling between sections
 * - Touch-friendly buttons and inputs
 * - Optimized spacing for small screens
 *
 * ## Accessibility
 *
 * - ARIA labels on buttons and inputs
 * - Keyboard navigation supported
 * - Tab order follows logical flow
 * - Color not sole indicator (uses icons/badges)
 * - Screen reader friendly status messages
 * - High contrast mode compatible
 *
 * ## Example Usage in Routing
 *
 * ```tsx
 * // In your router configuration:
 * import GradingPanel from '@/pages/GradingPanel';
 *
 * const routes = [
 *   {
 *     path: '/grading/:assignmentId',
 *     element: <GradingPanel />,
 *     protected: true,
 *     roles: ['teacher'],
 *   },
 * ];
 * ```
 *
 * ## Example Navigation
 *
 * ```tsx
 * // Navigate to grading interface:
 * import { useNavigate } from 'react-router-dom';
 *
 * const navigate = useNavigate();
 * const assignmentId = 1;
 *
 * // From assignment list page:
 * <Button onClick={() => navigate(`/grading/${assignmentId}`)}>
 *   Начать проверку
 * </Button>
 * ```
 *
 * ## Testing
 *
 * The component includes comprehensive tests covering:
 * - Rendering all UI elements
 * - Submission list display and selection
 * - Search and filter functionality
 * - Grading form submission
 * - Grade history display
 * - Responsive layout
 * - Error handling
 *
 * Run tests:
 * ```bash
 * npm test GradingPanel.test.tsx
 * ```
 *
 * ## Performance Considerations
 *
 * - Uses React Query for caching (60 second stale time)
 * - Memoized filtered submissions to prevent unnecessary re-renders
 * - ScrollArea component for efficient large lists
 * - Lazy loading of submission details
 * - Auto-refetch after grading to sync state
 *
 * ## Error Handling
 *
 * - Network errors: Shows alert with retry option
 * - Missing assignment: Shows "Задание не найдено"
 * - Missing submissions: Shows "Нет ответов для отображения"
 * - Failed grade submission: Shows error alert
 * - Invalid input: Input validation on grade number
 *
 * ## Future Enhancements
 *
 * - [ ] Rubric-based grading UI (T_ASN_011 extended)
 * - [ ] Batch grading shortcuts (Ctrl+S to save, Ctrl+N for next)
 * - [ ] Grade templates/shortcuts
 * - [ ] Grading speed metrics
 * - [ ] Plagiarism detection integration
 * - [ ] Student feedback notifications
 * - [ ] Grade appeals/re-submission workflow
 * - [ ] Multi-language feedback templates
 * - [ ] Voice/video feedback support
 * - [ ] Peer review features
 *
 */

// Example: Navigate to Grading Interface
export const GradingPanelNavigationExample = () => {
  const navigate = require('react-router-dom').useNavigate();

  const handleStartGrading = (assignmentId: number) => {
    // Navigate to grading panel for specific assignment
    navigate(`/grading/${assignmentId}`);
  };

  return (
    <button onClick={() => handleStartGrading(1)}>
      Начать проверку
    </button>
  );
};

// Example: Custom Grading Workflow
export const CustomGradingWorkflow = () => {
  /**
   * This example shows a custom workflow that could be implemented
   * using the Grading Interface components:
   *
   * 1. Load all submissions
   * 2. For each submission:
   *    a. Load auto-grade if available
   *    b. Show submission answers
   *    c. Get teacher input
   *    d. Apply late penalty if needed
   *    e. Save grade and feedback
   * 3. Repeat until all submissions graded
   * 4. Generate summary report
   */

  return null;
};

// Example: Grade Submission Data Structure
const exampleSubmission = {
  id: 1,
  assignment: 1,
  student: {
    id: 101,
    full_name: 'Иван Петров',
    email: 'ivan@test.com',
  },
  content: 'Student answer text...',
  file: 'https://example.com/submission.pdf',
  status: 'submitted',
  submitted_at: '2024-12-27T10:30:00Z',
  updated_at: '2024-12-27T10:30:00Z',
  feedback: '',
  // After grading:
  // score: 85,
  // max_score: 100,
  // percentage: 85,
  // graded_at: '2024-12-27T11:00:00Z',
  // status: 'graded',
};

// Example: Grade Submission Payload
const exampleGradePayload = {
  score: 85,
  feedback:
    'Хорошая работа! Обратите внимание на вторую часть задания в следующих работах.',
  status: 'graded' as const,
};

// Example: Auto-Grade Breakdown
const exampleAutoGradeBreakdown = {
  score: 82,
  breakdown: [
    {
      question: 'Question 1 - Multiple Choice',
      points: 10,
      earned: 10,
    },
    {
      question: 'Question 2 - Text Answer',
      points: 15,
      earned: 12,
    },
    {
      question: 'Question 3 - Numeric',
      points: 10,
      earned: 8,
    },
  ],
};

// Example: Grade History Entry
const exampleGradeHistory = {
  id: 1,
  date: '2024-12-27T11:00:00Z',
  grader: {
    name: 'Иван Петров',
    email: 'teacher@example.com',
  },
  score: 85,
  maxScore: 100,
  feedback: 'Хорошая работа!',
  status: 'graded' as const,
};
