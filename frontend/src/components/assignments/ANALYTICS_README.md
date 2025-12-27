# Assignment Analytics Dashboard

Professional-grade analytics dashboard for assignment performance tracking and analysis.

## Overview

The Assignment Analytics Dashboard provides comprehensive insights into assignment performance with:

- **Grade Distribution**: Pie and bar charts showing grade distribution across students
- **Per-Question Analysis**: Difficulty ranking and performance metrics for each question
- **Submission Timeline**: Analysis of on-time vs late submissions with trends
- **Class Comparison**: How assignment performance compares to class average
- **Responsive Charts**: Mobile-friendly visualizations using Recharts
- **Export to CSV**: Download analytics data for external reporting

## Components

### AssignmentAnalytics (Main Component)

The primary analytics dashboard component that displays all analytics data with filtering and export capabilities.

```tsx
import { AssignmentAnalytics } from '@/components/assignments/AssignmentAnalytics';

<AssignmentAnalytics
  assignmentId={123}
  assignmentTitle="Quiz 1"
  onlyTeachers={true}
/>
```

#### Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `assignmentId` | `number` | Yes | ID of the assignment to analyze |
| `assignmentTitle` | `string` | No | Display title (defaults to "Assignment Analytics") |
| `onlyTeachers` | `boolean` | No | If true, shows teacher-only features (default: true) |

## Hooks

### useAssignmentAnalytics

Main hook for fetching all analytics data with caching and filtering support.

```tsx
const { analytics, questions, time, loading, error, refetch } = useAssignmentAnalytics(
  assignmentId,
  {
    dateRange: 'month',
    studentGroup: 'all'
  }
);
```

#### Options

```typescript
interface UseAssignmentAnalyticsOptions {
  dateRange?: 'week' | 'month' | 'all';    // Filter by date range
  studentGroup?: 'all' | 'submitted' | 'not-submitted';  // Filter students
  enabled?: boolean;                         // Enable/disable fetching
}
```

#### Returns

```typescript
interface UseAssignmentAnalyticsResult {
  analytics: AnalyticsData | null;           // Grade distribution data
  questions: QuestionAnalysisData | null;    // Per-question analysis
  time: TimeAnalysisData | null;             // Submission timeline data
  loading: boolean;                          // Loading state
  error: Error | null;                       // Error information
  refetch: () => Promise<void>;              // Manual refetch function
}
```

### useAssignmentGradeAnalytics

Lightweight hook for grade distribution analytics only.

```tsx
const { data, loading, error } = useAssignmentGradeAnalytics(assignmentId);
```

### useAssignmentQuestionAnalytics

Focused hook for per-question difficulty analysis.

```tsx
const { data, loading, error } = useAssignmentQuestionAnalytics(assignmentId);
```

### useAssignmentTimeAnalytics

Specialized hook for submission timeline analysis.

```tsx
const { data, loading, error } = useAssignmentTimeAnalytics(assignmentId);
```

## Features

### 1. Grade Distribution Analysis

Displays grade distribution across all submissions with:
- Pie chart showing proportion of each grade
- Bar chart showing count per grade
- Detailed breakdown table
- Descriptive statistics (mean, median, mode, std dev, quartiles)

**Grade Buckets**:
- A (90-100%): Excellent
- B (80-89%): Good
- C (70-79%): Satisfactory
- D (60-69%): Passing
- F (<60%): Failing

### 2. Per-Question Analysis

Analyzes performance of each question:
- Difficulty ranking (based on wrong answer rate)
- Correct/wrong answer rates
- Question type indicators
- Points per question
- Visual difficulty badges (Easy, Medium, Hard)

```typescript
interface QuestionAnalysis {
  question_id: number;
  question_text: string;
  question_type: 'single_choice' | 'multiple_choice' | 'text' | 'number';
  points: number;
  total_answers: number;
  correct_answers: number;
  wrong_answers: number;
  correct_rate: number;
  wrong_rate: number;
  difficulty_score: number;
}
```

### 3. Submission Timeline

Tracks submission timing and patterns:
- On-time vs late submission counts
- Submission rate percentage
- Average days before/after deadline
- Late submission rate
- Days late statistics

### 4. Class Comparison

Compares assignment performance to class average:
- Assignment average vs class average
- Performance rating (Above/Average/Below)
- Difference indicator
- Trend visualization

### 5. Filtering

Users can filter analytics by:

**Date Range**:
- Last 7 days
- Last Month
- All Time

**Student Group**:
- All Students
- Submitted Only
- Not Submitted

### 6. Export to CSV

Export all analytics data in CSV format including:
- Assignment details
- Grade distribution
- Descriptive statistics
- Per-question analysis
- Submission metrics

Generated filename: `analytics_{assignmentId}_{date}.csv`

## Data Structures

### AnalyticsData

```typescript
interface AnalyticsData {
  assignment_id: number;
  assignment_title: string;
  max_score: number;
  statistics: {
    mean: number | null;
    median: number | null;
    mode: number | null;
    std_dev: number | null;
    min: number | null;
    max: number | null;
    q1: number | null;
    q2: number | null;
    q3: number | null;
    sample_size: number;
  };
  distribution: {
    buckets: { [key: string]: { label, count, percentage } };
    total: number;
    pie_chart_data: Array<{ label, value, percentage }>;
  };
  submission_rate: {
    assigned_count: number;
    submitted_count: number;
    graded_count: number;
    late_count: number;
    submission_rate: number;
    grading_rate: number;
    late_rate: number;
  };
  comparison: {
    assignment_average: number | null;
    assignment_count: number;
    class_average: number | null;
    difference: number | null;
    performance: string;
  };
  generated_at: string;
}
```

### QuestionAnalysisData

```typescript
interface QuestionAnalysisData {
  assignment_id: number;
  total_questions: number;
  questions: Array<{
    question_id: number;
    question_text: string;
    question_type: string;
    points: number;
    total_answers: number;
    correct_answers: number;
    wrong_answers: number;
    correct_rate: number;
    wrong_rate: number;
    difficulty_score: number;
  }>;
  difficulty_ranking: Array<{
    question_id: number;
    question_text: string;
    difficulty_score: number;
  }>;
  average_difficulty: number;
  generated_at: string;
}
```

### TimeAnalysisData

```typescript
interface TimeAnalysisData {
  assignment_id: number;
  submission_timing: {
    on_time_submissions: number;
    late_submissions: number;
    average_days_before_deadline: number | null;
    total_submissions: number;
  };
  grading_speed: {
    average_time_to_grade_hours: number | null;
    average_time_to_grade_days: number | null;
    fastest_grade_hours: number | null;
    slowest_grade_hours: number | null;
    total_graded: number;
  };
  late_submissions: {
    late_submission_count: number;
    late_submission_rate: number;
    average_days_late: number | null;
    most_days_late: number | null;
  };
  response_times: {
    first_grade_at: string | null;
    last_grade_at: string | null;
    grading_period_days: number | null;
    total_graded: number;
  };
  generated_at: string;
}
```

## API Integration

### Endpoints

The component integrates with these backend endpoints:

#### GET `/api/assignments/assignments/{id}/analytics/`

Returns grade distribution analytics (T_ASSIGN_007).

**Response**:
```json
{
  "assignment_id": 1,
  "assignment_title": "Quiz 1",
  "max_score": 100,
  "statistics": { ... },
  "distribution": { ... },
  "submission_rate": { ... },
  "comparison": { ... },
  "generated_at": "2025-12-27T10:30:00Z"
}
```

#### GET `/api/assignments/assignments/{id}/statistics/`

Returns per-question analysis and time metrics (T_ASN_005).

**Response**:
```json
{
  "assignment_id": 1,
  "total_questions": 5,
  "questions": [...],
  "difficulty_ranking": [...],
  "average_difficulty": 25.0,
  "submission_timing": { ... },
  "grading_speed": { ... },
  "late_submissions": { ... },
  "response_times": { ... },
  "generated_at": "2025-12-27T10:30:00Z"
}
```

#### Query Parameters

Both endpoints support filtering:

- `date_range`: 'week' | 'month' | 'all' (default: 'all')
- `student_group`: 'all' | 'submitted' | 'not-submitted' (default: 'all')

Example: `/api/assignments/assignments/1/analytics/?date_range=month&student_group=submitted`

## Caching

Analytics data is cached for **5 minutes** (300 seconds):

- Cache key: `assignment_analytics_{assignment_id}`
- Cache TTL: 300 seconds
- Invalidation: Automatic on grade changes

### Invalidating Cache

To refresh analytics data in the UI:

```tsx
const { refetch } = useAssignmentAnalytics(assignmentId);

// Manually refetch when grades are updated
await refetch();
```

## Usage Examples

### Basic Usage

```tsx
import { AssignmentAnalytics } from '@/components/assignments/AssignmentAnalytics';

export function MyPage() {
  return (
    <AssignmentAnalytics
      assignmentId={123}
      assignmentTitle="Quiz 1"
    />
  );
}
```

### With Custom Filtering

```tsx
import { useAssignmentAnalytics } from '@/hooks/useAssignmentAnalytics';

export function CustomAnalytics() {
  const { analytics, questions, loading } = useAssignmentAnalytics(123, {
    dateRange: 'month',
    studentGroup: 'submitted'
  });

  if (loading) return <Spinner />;

  return (
    <div>
      <h1>{analytics?.assignment_title}</h1>
      <p>Average: {analytics?.statistics.mean}</p>
      <p>Submission Rate: {analytics?.submission_rate.submission_rate}%</p>
    </div>
  );
}
```

### In a Teacher Dashboard

```tsx
import { AssignmentAnalytics } from '@/components/assignments/AssignmentAnalytics';
import { Card } from '@/components/ui/card';

export function TeacherDashboard() {
  const [selectedAssignment, setSelectedAssignment] = useState<number | null>(null);

  return (
    <div className="space-y-6">
      <AssignmentSelector onChange={setSelectedAssignment} />

      {selectedAssignment && (
        <Card>
          <AssignmentAnalytics
            assignmentId={selectedAssignment}
            onlyTeachers={true}
          />
        </Card>
      )}
    </div>
  );
}
```

### Exporting Analytics

```tsx
import { AssignmentAnalytics } from '@/components/assignments/AssignmentAnalytics';

export function ExportableAnalytics() {
  const handleExport = () => {
    // Export button is built-in to AssignmentAnalytics component
  };

  return (
    <AssignmentAnalytics
      assignmentId={123}
      assignmentTitle="Quiz 1"
    />
  );
}
```

## Styling

The component uses Tailwind CSS with shadcn/ui components. All colors are customizable:

**Grade Colors**:
```tsx
const GRADE_COLORS = {
  A: '#10b981',  // Green
  B: '#3b82f6',  // Blue
  C: '#f59e0b',  // Amber
  D: '#ef4444',  // Red
  F: '#6b7280',  // Gray
};
```

**Difficulty Colors**:
```tsx
const DIFFICULTY_COLORS = {
  easy: '#10b981',    // Green
  medium: '#f59e0b',  // Amber
  hard: '#ef4444',    // Red
};
```

## Responsive Design

The dashboard is fully responsive:

- **Desktop**: All tabs visible, full-width charts
- **Tablet**: Tabs in 2-3 columns, responsive grid
- **Mobile**: Tabs in single column, stacked charts

Breakpoints:
- sm: 640px
- md: 768px
- lg: 1024px
- xl: 1280px

## Accessibility

Features:
- ARIA labels on all interactive elements
- Keyboard navigation support
- Color contrast ratio: WCAG AA compliant
- Focus indicators on buttons
- Screen reader friendly

## Testing

Run tests with:

```bash
npm test -- AssignmentAnalytics.test.tsx
```

Test coverage includes:
- Component rendering
- Tab navigation
- Filter functionality
- Data visualization
- Export functionality
- Error handling
- Accessibility

## Performance

Optimizations:
- Data caching (5-minute TTL)
- Memoized chart data
- Lazy component loading
- Optimized re-renders
- Efficient state management

Expected metrics:
- Initial load: < 500ms
- Chart rendering: < 100ms
- Filter changes: < 50ms

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile: iOS 13+, Chrome Mobile 90+

## Known Limitations

1. **Maximum Students**: Dashboard optimized for < 1000 students per assignment
2. **Question Limit**: Supports up to 100 questions per assignment
3. **Date Range**: Limited to 2 years of historical data

## Future Enhancements

- Custom date range picker
- Student performance comparison
- Trend analysis with historical data
- Custom grade buckets
- Predictive analytics
- Real-time dashboard updates
- PDF export support
- Custom color schemes

## Troubleshooting

### Chart Not Rendering

If charts are not displaying:

1. Check browser console for errors
2. Verify Recharts is properly installed
3. Clear browser cache
4. Refresh the page

### Data Not Loading

If analytics data fails to load:

1. Check network tab for API errors
2. Verify assignment exists and user has permission
3. Check backend logs
4. Ensure backend analytics endpoints are implemented

### Slow Performance

If dashboard is slow:

1. Clear browser cache
2. Check network tab for slow requests
3. Verify backend caching is enabled
4. Consider using lighter date range

## Support

For issues or questions:

1. Check component documentation
2. Review test files for examples
3. Check backend API logs
4. Open GitHub issue with details

## Version History

- **1.0.0** (2025-12-27): Initial release
  - Grade distribution analysis
  - Per-question difficulty ranking
  - Submission timeline tracking
  - Class average comparison
  - CSV export functionality
  - Mobile-responsive design
