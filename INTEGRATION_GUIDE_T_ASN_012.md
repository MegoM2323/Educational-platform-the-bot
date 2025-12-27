# Integration Guide - T_ASN_012: Assignment Analytics Dashboard

## Quick Start

### 1. Import the Component

```tsx
import { AssignmentAnalytics } from '@/components/assignments/AssignmentAnalytics';
```

### 2. Add to Your Page

```tsx
<AssignmentAnalytics
  assignmentId={assignmentId}
  assignmentTitle={assignment.title}
/>
```

### 3. Test in Browser

Navigate to `/assignments/{assignmentId}/analytics` to see the dashboard.

---

## Detailed Integration

### Step 1: Route Setup

Add route to your router configuration:

```tsx
// src/routes.ts or router configuration file
import AssignmentAnalyticsPage from '@/pages/AssignmentAnalytics';

const routes = [
  {
    path: '/assignments/:assignmentId/analytics',
    element: <AssignmentAnalyticsPage />,
    requireAuth: true,
    roles: ['teacher', 'tutor', 'admin'], // Only these roles can access
  },
];
```

### Step 2: Add Navigation Links

In your assignment detail page or teacher dashboard:

```tsx
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { BarChart3 } from 'lucide-react';

export function AssignmentActions({ assignmentId }) {
  const navigate = useNavigate();

  return (
    <Button
      variant="outline"
      onClick={() => navigate(`/assignments/${assignmentId}/analytics`)}
      className="gap-2"
    >
      <BarChart3 className="h-4 w-4" />
      View Analytics
    </Button>
  );
}
```

### Step 3: API Integration

Ensure your backend implements these endpoints:

#### Endpoint 1: Grade Distribution Analytics

```
GET /api/assignments/assignments/{id}/analytics/
```

**Response Format**:
```json
{
  "assignment_id": 1,
  "assignment_title": "Quiz 1",
  "max_score": 100,
  "statistics": {
    "mean": 78.5,
    "median": 80,
    "mode": 85,
    "std_dev": 12.3,
    "min": 45,
    "max": 100,
    "q1": 70,
    "q2": 80,
    "q3": 88,
    "sample_size": 32
  },
  "distribution": {
    "buckets": {
      "A": {
        "label": "Excellent (90-100%)",
        "count": 8,
        "percentage": 25.0
      },
      "B": {
        "label": "Good (80-89%)",
        "count": 12,
        "percentage": 37.5
      },
      "C": {
        "label": "Satisfactory (70-79%)",
        "count": 8,
        "percentage": 25.0
      },
      "D": {
        "label": "Passing (60-69%)",
        "count": 3,
        "percentage": 9.4
      },
      "F": {
        "label": "Failing (<60%)",
        "count": 1,
        "percentage": 3.1
      }
    },
    "total": 32,
    "pie_chart_data": [
      { "label": "A", "value": 8, "percentage": 25.0 },
      { "label": "B", "value": 12, "percentage": 37.5 },
      { "label": "C", "value": 8, "percentage": 25.0 },
      { "label": "D", "value": 3, "percentage": 9.4 },
      { "label": "F", "value": 1, "percentage": 3.1 }
    ]
  },
  "submission_rate": {
    "assigned_count": 35,
    "submitted_count": 32,
    "graded_count": 32,
    "late_count": 5,
    "submission_rate": 91.43,
    "grading_rate": 100,
    "late_rate": 15.63
  },
  "comparison": {
    "assignment_average": 78.5,
    "assignment_count": 32,
    "class_average": 76.2,
    "difference": 2.3,
    "performance": "Average"
  },
  "generated_at": "2025-12-27T10:30:00Z"
}
```

#### Endpoint 2: Statistics (Questions & Time Analysis)

```
GET /api/assignments/assignments/{id}/statistics/
```

**Response Format**:
```json
{
  "assignment_id": 1,
  "total_questions": 5,
  "questions": [
    {
      "question_id": 1,
      "question_text": "What is the capital of France?",
      "question_type": "single_choice",
      "points": 20,
      "total_answers": 32,
      "correct_answers": 30,
      "wrong_answers": 2,
      "correct_rate": 93.75,
      "wrong_rate": 6.25,
      "difficulty_score": 6.25
    }
  ],
  "difficulty_ranking": [
    {
      "question_id": 3,
      "question_text": "Select all countries in the EU",
      "difficulty_score": 43.75
    }
  ],
  "average_difficulty": 25.0,
  "submission_timing": {
    "on_time_submissions": 27,
    "late_submissions": 5,
    "average_days_before_deadline": 2.5,
    "total_submissions": 32
  },
  "grading_speed": {
    "average_time_to_grade_hours": 24.5,
    "average_time_to_grade_days": 1.02,
    "fastest_grade_hours": 2.5,
    "slowest_grade_hours": 72.0,
    "total_graded": 32
  },
  "late_submissions": {
    "late_submission_count": 5,
    "late_submission_rate": 15.63,
    "average_days_late": 1.2,
    "most_days_late": 3
  },
  "response_times": {
    "first_grade_at": "2025-12-24T15:30:00Z",
    "last_grade_at": "2025-12-27T10:30:00Z",
    "grading_period_days": 3,
    "total_graded": 32
  },
  "generated_at": "2025-12-27T10:30:00Z"
}
```

### Step 4: Update API Client

The API client is already updated with:

```tsx
// src/integrations/api/assignmentsAPI.ts

export const assignmentsAPI = {
  // ... existing methods ...

  // Analytics endpoints
  getAssignmentAnalytics: async (assignmentId: number): Promise<any> => {
    const response = await apiClient.get(
      `/assignments/assignments/${assignmentId}/analytics/`
    );
    return response.data;
  },

  getAssignmentStatistics: async (
    assignmentId: number,
    filters?: Record<string, any>
  ): Promise<any> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    const url = `/assignments/assignments/${assignmentId}/statistics/${
      params.toString() ? `?${params.toString()}` : ''
    }`;
    const response = await apiClient.get(url);
    return response.data;
  },
};
```

---

## Usage Scenarios

### Scenario 1: Teacher Views Assignment Analytics

```tsx
// In TeacherDashboard component
import { AssignmentAnalytics } from '@/components/assignments/AssignmentAnalytics';
import { Card } from '@/components/ui/card';

export function AssignmentDetail({ assignmentId }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Assignment Performance Analytics</CardTitle>
      </CardHeader>
      <CardContent>
        <AssignmentAnalytics
          assignmentId={assignmentId}
          assignmentTitle="Quiz 1"
          onlyTeachers={true}
        />
      </CardContent>
    </Card>
  );
}
```

### Scenario 2: Using Custom Hooks

```tsx
// Fetch only specific analytics
import { useAssignmentGradeAnalytics } from '@/hooks/useAssignmentAnalytics';

export function GradeDistributionWidget({ assignmentId }) {
  const { data, loading } = useAssignmentGradeAnalytics(assignmentId);

  if (loading) return <Spinner />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Grade Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <p>Mean: {data?.statistics.mean}</p>
        <p>Submissions: {data?.distribution.total}</p>
      </CardContent>
    </Card>
  );
}
```

### Scenario 3: Multiple Assignments Comparison

```tsx
// Compare analytics across multiple assignments
import { useAssignmentAnalytics } from '@/hooks/useAssignmentAnalytics';

export function AssignmentComparison({ assignmentIds }) {
  const analyticsData = assignmentIds.map(id =>
    useAssignmentAnalytics(id)
  );

  return (
    <div className="grid grid-cols-2 gap-4">
      {analyticsData.map((data, idx) => (
        <Card key={idx}>
          <CardHeader>
            <CardTitle>{data.analytics?.assignment_title}</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Mean: {data.analytics?.statistics.mean}</p>
            <p>Students: {data.analytics?.distribution.total}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

---

## Customization

### Customize Colors

Edit in `AssignmentAnalytics.tsx`:

```tsx
const GRADE_COLORS = {
  A: '#10b981',  // Change to your preferred color
  B: '#3b82f6',
  C: '#f59e0b',
  D: '#ef4444',
  F: '#6b7280',
};
```

### Add Custom Metrics

```tsx
// Extend the component with custom business logic
<AssignmentAnalytics assignmentId={assignmentId} />

// Or create a wrapper component
export function CustomAnalytics({ assignmentId }) {
  const { analytics } = useAssignmentAnalytics(assignmentId);

  return (
    <>
      <AssignmentAnalytics assignmentId={assignmentId} />

      {/* Add custom metrics */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Custom Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Pass Rate: {
            ((analytics?.distribution.buckets.A.count || 0) +
             (analytics?.distribution.buckets.B.count || 0) +
             (analytics?.distribution.buckets.C.count || 0) +
             (analytics?.distribution.buckets.D.count || 0)) /
            (analytics?.distribution.total || 1) * 100
          }%</p>
        </CardContent>
      </Card>
    </>
  );
}
```

---

## Error Handling

### Handle Missing Data

```tsx
import { Alert, AlertDescription } from '@/components/ui/alert';

export function SafeAnalytics({ assignmentId }) {
  const { analytics, error, loading } = useAssignmentAnalytics(assignmentId);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Unable to load analytics. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  if (loading) {
    return <Spinner />;
  }

  if (!analytics) {
    return (
      <Alert>
        <AlertDescription>
          No analytics data available for this assignment.
        </AlertDescription>
      </Alert>
    );
  }

  return <AssignmentAnalytics assignmentId={assignmentId} />;
}
```

### Handle Permission Errors

```tsx
export function ProtectedAnalytics({ assignmentId }) {
  const { analytics, error } = useAssignmentAnalytics(assignmentId);

  if (error?.status === 403) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          You don't have permission to view this assignment's analytics.
        </AlertDescription>
      </Alert>
    );
  }

  return <AssignmentAnalytics assignmentId={assignmentId} />;
}
```

---

## Testing

### Unit Tests

```bash
npm test -- AssignmentAnalytics.test.tsx
```

### E2E Tests

```bash
npm run test:e2e -- analytics.spec.ts
```

### Manual Testing Checklist

- [ ] Component loads without errors
- [ ] All tabs are functional
- [ ] Charts render correctly
- [ ] Filters work properly
- [ ] Export button exports CSV
- [ ] Mobile responsive design works
- [ ] Keyboard navigation works
- [ ] Screen reader compatible

---

## Deployment

### Production Checklist

- [ ] Backend endpoints implemented and tested
- [ ] API response times < 500ms
- [ ] Analytics caching enabled (5-minute TTL)
- [ ] Error handling implemented
- [ ] Rate limiting configured
- [ ] Monitoring/logging enabled
- [ ] Security headers configured
- [ ] CORS enabled for analytics endpoints
- [ ] Performance optimization verified

### Performance Optimization

```tsx
// Enable React Query caching
import { useQuery } from '@tanstack/react-query';

useQuery({
  queryKey: ['assignment-analytics', assignmentId],
  queryFn: () => assignmentsAPI.getAssignmentAnalytics(assignmentId),
  staleTime: 1000 * 60 * 5, // 5 minutes
  gcTime: 1000 * 60 * 30,    // 30 minutes
});
```

---

## Troubleshooting

### Charts Not Rendering

1. Check if Recharts is installed: `npm list recharts`
2. Verify data is loading in browser DevTools
3. Check for console errors
4. Clear browser cache and reload

### Analytics Data Not Loading

1. Verify backend endpoints are implemented
2. Check network requests in DevTools
3. Verify authentication token is sent
4. Check backend logs for errors

### Slow Performance

1. Check if caching is enabled
2. Monitor API response times
3. Reduce date range if needed
4. Check browser performance in DevTools

---

## Support & Resources

- **Component Docs**: `ANALYTICS_README.md`
- **API Endpoints**: Backend API documentation
- **Test Examples**: `AssignmentAnalytics.test.tsx`
- **Backend Implementation**:
  - `backend/assignments/services/analytics.py`
  - `backend/assignments/services/statistics.py`
  - `backend/assignments/views.py`

---

## Related Tasks

- **T_ASSIGN_007**: Grade Distribution Analytics (Backend)
- **T_ASN_005**: Assignment Statistics Service (Backend)
- **T_ASN_010**: Assignment Submission UI (Frontend)
- **T_ASN_008**: Assignment Grading Interface (Frontend)

---

## Next Steps

1. Implement backend endpoints if not done
2. Add route to router configuration
3. Add navigation links in relevant pages
4. Test with real data
5. Deploy to production
6. Monitor performance and user feedback
