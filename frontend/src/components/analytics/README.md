# Analytics Dashboard Components

Comprehensive analytics and reporting UI components for THE_BOT educational platform.

## Components Overview

### AnalyticsDashboard
Main dashboard component displaying comprehensive learning metrics and analytics.

**Location**: `AnalyticsDashboard.tsx`

**Features**:
- Key Performance Indicators (KPIs) cards
- Learning progress trend charts
- Engagement metrics visualization
- Student performance rankings
- Class/section analytics
- Date range filtering with quick presets
- Period comparison
- Responsive design (mobile, tablet, desktop)
- Real-time updates via WebSocket
- Export functionality

**Props**:
```typescript
interface AnalyticsDashboardProps {
  initialDateFrom?: string;      // ISO date string (YYYY-MM-DD)
  initialDateTo?: string;        // ISO date string (YYYY-MM-DD)
  classId?: number;              // Filter by class
  studentId?: number;            // Filter by student
}
```

**Usage**:
```tsx
import { AnalyticsDashboard } from '@/components/analytics/AnalyticsDashboard';

<AnalyticsDashboard
  initialDateFrom="2025-01-01"
  initialDateTo="2025-01-31"
  classId={5}
/>
```

**Data Dependencies**:
- `/reports/analytics-data/` endpoint for dashboard metrics
- `/reports/analytics-data/learning-progress/` for progress trends
- `/reports/analytics-data/engagement/` for engagement metrics
- `/reports/analytics-data/performance/` for student rankings
- `/reports/analytics-data/classes/` for class analytics

---

### ExportButton
Flexible export button component supporting multiple formats.

**Location**: `ExportButton.tsx`

**Supported Formats**:
- CSV (comma-separated values)
- XLSX (Excel format)
- PDF (formatted reports)
- JSON (raw data export)

**Props**:
```typescript
interface ExportButtonProps {
  data?: Record<string, any>;              // In-memory data to export
  endpoint?: string;                       // Server endpoint for export
  queryParams?: Record<string, any>;       // Query parameters
  filename?: string;                       // Base filename (no extension)
  formats?: ('csv' | 'xlsx' | 'pdf' | 'json')[];
  showProgress?: boolean;                  // Show export progress
  onExportSuccess?: (format: string) => void;
  onExportError?: (error: Error, format: string) => void;
  variant?: 'default' | 'outline' | 'ghost' | 'secondary' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  asDropdown?: boolean;                    // Dropdown menu vs single button
}
```

**Usage**:
```tsx
import { ExportButton } from '@/components/analytics/ExportButton';

// Dropdown with multiple formats
<ExportButton
  data={dashboardData}
  filename="analytics_report"
  formats={['csv', 'xlsx', 'pdf']}
  onExportSuccess={(format) => console.log(`Exported as ${format}`)}
/>

// Export from API endpoint
<ExportButton
  endpoint="/reports/analytics-data/export/"
  queryParams={{ classId: 5, format: 'csv' }}
  filename="class_report"
  asDropdown={true}
/>
```

---

### MetricCard
Reusable card component for displaying KPI metrics.

**Location**: `MetricCard.tsx`

**Features**:
- Formatted values (percentage, currency, number)
- Trend indicators (up/down arrows)
- Icon support (Lucide icons)
- Badge support for additional data
- Interactive mode for drill-down navigation
- Customizable styling

**Props**:
```typescript
interface MetricCardProps {
  title: string;                                      // Card title
  description?: string;                              // Subtitle
  value: number | string;                            // Main value
  format?: 'number' | 'percentage' | 'currency' | 'custom';
  decimals?: number;                                 // Decimal places
  icon?: LucideIcon;                                 // Icon component
  iconColor?: string;                                // Icon color class
  badges?: Array<{                                   // Additional badges
    label: string;
    value: string | number;
    variant?: 'default' | 'secondary' | 'outline' | 'destructive';
  }>;
  trend?: {                                          // Trend indicator
    value: number;
    isPositive: boolean;
    label?: string;
  };
  showTrendPercent?: boolean;                        // Show % in trend
  bgColor?: string;                                  // Background color
  interactive?: boolean;                             // Clickable mode
  onClick?: () => void;                              // Click handler
  footer?: React.ReactNode;                          // Footer content
  className?: string;                                // CSS classes
}
```

**Usage**:
```tsx
import { MetricCard } from '@/components/analytics/MetricCard';
import { Users, Target, Award } from 'lucide-react';

// Simple KPI
<MetricCard
  title="Total Students"
  value={45}
  icon={Users}
/>

// With trend and badges
<MetricCard
  title="Average Score"
  value={72.3}
  format="percentage"
  decimals={1}
  icon={Award}
  trend={{ value: 5, isPositive: true, label: 'vs last month' }}
  badges={[
    { label: 'Max', value: 98 },
    { label: 'Min', value: 45 }
  ]}
/>

// Interactive card
<MetricCard
  title="Classes"
  value={8}
  icon={BookOpen}
  interactive
  onClick={() => navigate('/analytics/classes')}
/>
```

---

## Hooks

### useAnalyticsDashboard
Primary hook for fetching comprehensive analytics dashboard data.

**Location**: `../hooks/useAnalyticsDashboard.ts`

```typescript
const { data, loading, error, refetch, isRefetching } = useAnalyticsDashboard({
  dateFrom: '2025-01-01',
  dateTo: '2025-01-31',
  classId: 5,
  studentId: 42,
  enabled: true
});
```

**Return Value**:
```typescript
{
  data: AnalyticsDashboardData | null;     // Dashboard data
  loading: boolean;                         // Initial load state
  error: Error | null;                      // Error object
  refetch: () => Promise<void>;             // Manual refresh
  isRefetching: boolean;                    // Refetch in progress
}
```

**Data Structure**:
```typescript
interface AnalyticsDashboardData {
  metrics: {
    total_students: number;
    active_students: number;
    average_engagement: number;           // 0-100
    average_progress: number;             // 0-100
    total_assignments: number;
    completed_assignments: number;
    average_score: number;                // 0-100
    completion_rate: number;              // 0-100
  };
  learning_progress: LearningProgress[];   // Trend data by period
  engagement_trend: EngagementData[];      // Daily engagement metrics
  top_performers: StudentPerformance[];    // Top 10 students
  class_analytics: ClassAnalytics[];       // Per-class metrics
  date_range: {
    start_date: string;                   // ISO date
    end_date: string;                     // ISO date
  };
  generated_at: string;                    // ISO timestamp
}
```

### Additional Hooks

**useLearningProgress** - Fetch only learning progress data
```typescript
const { data, loading, error } = useLearningProgress(dateFrom, dateTo);
```

**useEngagementMetrics** - Fetch engagement trend data
```typescript
const { data, loading, error } = useEngagementMetrics(dateFrom, dateTo);
```

**useStudentPerformance** - Fetch student rankings
```typescript
const { data, loading, error } = useStudentPerformance(limit, classId);
```

**useClassAnalytics** - Fetch class-level metrics
```typescript
const { data, loading, error } = useClassAnalytics(classId);
```

---

## Page Component

### AnalyticsDashboardPage
Main page component with access control and routing.

**Location**: `../pages/AnalyticsDashboard.tsx`

**Route**: `/analytics`

**Query Parameters**:
- `?dateFrom=YYYY-MM-DD` - Start date
- `?dateTo=YYYY-MM-DD` - End date
- `?classId=123` - Filter by class
- `?studentId=456` - Filter by student

**Access Control**:
- Teachers: Own classes and students
- Tutors: Assigned students
- Admins: All classes and students
- Students: Redirected to `/dashboard/student`

**Usage in Router**:
```tsx
import { AnalyticsDashboardPage } from '@/pages/AnalyticsDashboard';

<Route path="/analytics" element={
  <ProtectedRoute requiredRole={['teacher', 'tutor', 'admin']}>
    <AnalyticsDashboardPage />
  </ProtectedRoute>
} />
```

---

## Chart Types

The dashboard uses Recharts for interactive visualizations:

### 1. Learning Progress Chart (ComposedChart)
- **Lines**: Average Progress %, Completion Rate %
- **Bars**: Active Students count
- **X-Axis**: Time period (week/month)
- **Interactive**: Hover tooltips, legend toggle

### 2. Engagement Chart (ComposedChart)
- **Lines**: Engagement Score
- **Bars**: Active Users, Submissions
- **X-Axis**: Date
- **Interactive**: Hover details, legends

### 3. Performance Rankings (List)
- Displays top 10 students
- Shows rank, name, score, progress, completion %
- Hover effects for interactivity

### 4. Score Distribution (PieChart)
- Excellent (90-100%)
- Good (80-89%)
- Fair (70-79%)
- Below Average (<70%)

### 5. Class Analytics (BarChart)
- Groups by class
- Metrics: Avg Score, Progress, Engagement
- Comparison view across classes

---

## Styling and Theme

### CSS Classes Used
- Tailwind CSS utility classes
- Responsive grid layouts (grid-cols-2, lg:grid-cols-4)
- Responsive padding/margins (p-4, md:p-6)
- Dark mode support via theme context

### Responsive Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

### Color Scheme
- Primary: Blue (#3b82f6)
- Success: Green (#10b981)
- Warning: Amber (#f59e0b)
- Error: Red (#ef4444)
- Secondary: Purple (#8b5cf6)
- Accent: Cyan (#06b6d4)

---

## Testing

### Component Tests
Location: `__tests__/AnalyticsDashboard.test.tsx`

**Coverage**:
- Rendering (title, cards, buttons)
- Loading/error states
- Filter interactions
- Chart tab switching
- Export functionality
- Data display formatting
- Responsive design
- Accessibility

**Running Tests**:
```bash
npm test -- AnalyticsDashboard
```

### Page Tests
Location: `../pages/__tests__/AnalyticsDashboard.test.tsx`

**Coverage**:
- Page rendering
- Auth guard
- Access control
- Query parameter handling
- Loading states

---

## Performance Optimizations

1. **Lazy Loading**: Charts load only when tab is active
2. **Memoization**: useCallback for event handlers
3. **Debounced Filters**: Date range changes debounced
4. **Pagination**: Large datasets paginated
5. **Caching**: 30-minute Redis cache on backend
6. **Code Splitting**: Component lazy loading via React.lazy()

---

## Accessibility Features

- ARIA labels on interactive elements
- Keyboard navigation support
- Color contrast compliance (WCAG AA)
- Focus indicators
- Alt text for icons
- Semantic HTML structure

---

## Future Enhancements

1. **Drill-down Capability**
   - Click on student to view individual progress
   - Click on class to view class details
   - Click on chart data points for filtering

2. **Comparison View**
   - Side-by-side period comparison
   - Year-over-year analytics
   - Class comparison reports

3. **Real-time Updates**
   - WebSocket integration for live metrics
   - Auto-refresh at configurable intervals
   - Activity stream widget

4. **Custom Reports**
   - Save filter combinations
   - Scheduled report generation
   - Email delivery of reports

5. **Advanced Analytics**
   - Predictive analytics (ML)
   - Anomaly detection
   - Recommendation engine

---

## API Endpoints

All endpoints require authentication and respect role-based access control.

### Dashboard Data
```
GET /api/reports/analytics-data/
  Query params: date_from, date_to, class_id, student_id
  Response: AnalyticsDashboardData
```

### Learning Progress
```
GET /api/reports/analytics-data/learning-progress/
  Query params: date_from, date_to, class_id
  Response: { learning_progress: LearningProgress[] }
```

### Engagement Metrics
```
GET /api/reports/analytics-data/engagement/
  Query params: date_from, date_to, class_id
  Response: { engagement_trend: EngagementData[] }
```

### Student Performance
```
GET /api/reports/analytics-data/performance/
  Query params: limit, class_id
  Response: { top_performers: StudentPerformance[] }
```

### Class Analytics
```
GET /api/reports/analytics-data/classes/
  Query params: class_id
  Response: { class_analytics: ClassAnalytics[] }
```

### Export
```
GET /api/reports/analytics-data/export/
  Query params: format (csv|xlsx|pdf|json), date_from, date_to, class_id
  Response: Binary file or JSON data
```

---

## Troubleshooting

### Charts Not Rendering
- Check if recharts is installed: `npm list recharts`
- Verify ResponsiveContainer has parent with height
- Check browser console for errors

### Data Not Loading
- Verify API endpoints are accessible
- Check authentication token is valid
- Check network tab for 401/403 responses
- Verify date range format (YYYY-MM-DD)

### Slow Performance
- Check number of data points being visualized
- Verify Redis cache is working
- Check database query performance
- Enable performance monitoring

### Export Not Working
- Check file download is not blocked
- Verify API endpoint supports requested format
- Check file size limits
- Verify CORS headers if cross-origin

---

## Version History

**v1.0.0** (December 27, 2025)
- Initial release
- AnalyticsDashboard component
- ExportButton component
- MetricCard component
- useAnalyticsDashboard hook
- Comprehensive test coverage
- Full documentation

---

## Contributing

When adding new features or components:

1. Follow existing code patterns
2. Add TypeScript types for all props
3. Include JSDoc comments
4. Add unit tests (min 80% coverage)
5. Update this README
6. Test responsive design
7. Check accessibility compliance
