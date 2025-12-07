# Student Knowledge Graph Tab - Implementation Guide

## Overview

The Student Knowledge Graph Tab provides a visual representation of student learning progress through an interactive D3.js graph visualization. Students can see their lessons, progress, and dependencies in an intuitive visual format.

## Files Created

### 1. API Client
**File:** `/frontend/src/integrations/api/knowledgeGraphAPI.ts`

Provides methods to interact with knowledge graph backend endpoints:
- `getStudentGraph(studentId, subjectId)` - Get full graph with lessons and dependencies
- `getLessonProgress(lessonId, studentId)` - Get detailed progress for a lesson
- `getLessonDependencies(graphId, lessonId)` - Get lesson dependencies
- `canStartLesson(graphId, lessonId)` - Check if prerequisites are met
- `getStudentSubjects()` - Get all subjects for subject selector

**TypeScript Types:**
- `KnowledgeGraph` - Complete graph structure
- `GraphLesson` - Lesson with position and progress
- `GraphDependency` - Prerequisite/suggested relationships
- `LessonProgressDetail` - Detailed progress information
- `Subject` - Subject metadata

### 2. Custom Hooks
**File:** `/frontend/src/hooks/useKnowledgeGraph.ts`

Provides TanStack Query hooks for data fetching:
- `useKnowledgeGraph(studentId, subjectId)` - Main hook for fetching graph data
  - Returns: `{ data, isLoading, error, refreshGraph }`
  - Caches for 1 minute
  - Refetches on subject change
  - Provides manual refresh function

- `useStudentSubjects()` - Fetches available subjects for selector
  - Returns: `{ data, isLoading, error }`
  - Caches for 5 minutes (subjects don't change often)

- `useGraphLessonProgress(lessonId, studentId)` - Fetches lesson progress
  - Returns: `{ data, isLoading, error }`
  - Caches for 30 seconds (progress changes frequently)

### 3. Main Component
**File:** `/frontend/src/pages/dashboard/student/KnowledgeGraphTab.tsx`

React component implementing the complete student knowledge graph page.

**Features:**
- ✅ Subject selector (if multiple subjects enrolled)
- ✅ Visual graph with D3.js (via GraphVisualization component)
- ✅ Progress indicators (colors, percentages)
- ✅ Lesson click navigation
- ✅ Lock/unlock based on dependencies
- ✅ Loading states with skeleton
- ✅ Error states with retry button
- ✅ Empty states (no subjects, no lessons)
- ✅ Responsive design (mobile-first)
- ✅ Legend explaining status colors
- ✅ Help text with usage instructions
- ✅ Progress summary (X of Y lessons completed)
- ✅ Manual refresh button

**Component Structure:**
```tsx
<KnowledgeGraphTab>
  ├─ Subject Selector Card
  │  ├─ Subject dropdown (if multiple)
  │  ├─ Progress summary
  │  └─ Refresh button
  │
  ├─ Legend Card
  │  └─ Status colors explanation
  │
  ├─ Graph Visualization Card
  │  └─ D3 graph (zoom, pan, click)
  │
  └─ Help Card
     └─ Usage instructions
</KnowledgeGraphTab>
```

### 4. Examples & Documentation
**File:** `/frontend/src/pages/dashboard/student/KnowledgeGraphTab.example.tsx`

Comprehensive examples demonstrating:
- Basic usage
- Tab layout integration
- Routing setup
- State diagram
- Data flow
- Testing scenarios
- Mock data
- Accessibility features
- Performance considerations
- Mobile responsive behavior

## Integration

### Step 1: Add Route

In your routing file (e.g., `App.tsx`):

```tsx
import { KnowledgeGraphTab } from '@/pages/dashboard/student/KnowledgeGraphTab';

<Routes>
  <Route path="/dashboard/student" element={<StudentDashboard />}>
    <Route path="knowledge-graph" element={<KnowledgeGraphTab />} />
  </Route>
</Routes>
```

### Step 2: Add Navigation Link

In your student dashboard sidebar/navigation:

```tsx
<NavLink to="/dashboard/student/knowledge-graph">
  <BookOpen className="h-4 w-4 mr-2" />
  Граф знаний
</NavLink>
```

### Step 3: Backend API

Ensure backend endpoints are configured in `backend/knowledge_graph/urls.py`:

```python
# GET /api/knowledge-graph/students/{student_id}/subject/{subject_id}/
path('students/<int:student_id>/subject/<int:subject_id>/',
     graph_views.GetOrCreateGraphView.as_view(),
     name='graph-get-or-create'),

# GET /api/knowledge-graph/lessons/{lesson_id}/progress/{student_id}/
path('lessons/<int:lesson_id>/progress/<int:student_id>/',
     progress_views.GetLessonProgressView.as_view(),
     name='lesson-progress-get'),
```

## User Flow

1. **Landing:** Student navigates to knowledge graph page
2. **Loading:** Skeleton shown while fetching subjects
3. **Subject Selection:**
   - If 1 subject: Auto-selected
   - If multiple: Dropdown selector shown
4. **Graph Loading:** Skeleton shown while fetching graph
5. **Graph Display:** D3 visualization rendered with:
   - Gray nodes: Not started (clickable)
   - Blue nodes: In progress (clickable)
   - Green nodes: Completed (clickable)
   - Red nodes: Locked (shows alert on click)
6. **Lesson Click:** Navigate to `/lessons/{lessonId}` (if unlocked)
7. **Locked Lesson:** Alert shown: "Prerequisites not met"
8. **Subject Change:** Graph refreshes for new subject
9. **Manual Refresh:** Button to reload current graph

## State Management

### Loading States
- `subjectsLoading`: Fetching available subjects
- `graphLoading`: Fetching graph data for selected subject
- Combined skeleton shown during either loading state

### Error States
- `subjectsError`: Failed to fetch subjects
- `graphError`: Failed to fetch graph
- Alert shown with error message and retry button

### Empty States
- No subjects enrolled: "Contact your teacher"
- No subject selected: "Please select a subject"
- Graph has no lessons: "Teacher will add materials soon"

### Data States
- `subjects`: Array of enrolled subjects
- `selectedSubjectId`: Currently selected subject
- `graphData`: Complete graph with lessons and dependencies
- `visualizationData`: Transformed data for D3 (nodes, links)

## Accessibility

- **Keyboard Navigation:** Tab through interactive elements
- **Screen Readers:** All labels and descriptions provided
- **Focus Management:** Focus preserved on interactions
- **Color Contrast:** WCAG AA compliant
- **Alternative Text:** Icons have aria-labels
- **Semantic HTML:** Proper heading hierarchy

## Performance

### Caching Strategy
- **Subjects:** 5 minutes (rarely change)
- **Graph:** 1 minute (moderate updates)
- **Lesson Progress:** 30 seconds (frequent updates)

### Optimizations
- Memoized graph data transformation
- Debounced window resize (250ms)
- D3 force simulation limited to 150 iterations
- TanStack Query automatic deduplication
- Lazy loading potential for GraphVisualization

## Responsive Design

### Breakpoints
- **< 640px (mobile):**
  - Stacked layout
  - Subject selector full width
  - 2-column legend
  - Larger touch targets

- **640px - 1024px (tablet):**
  - 2-column legend
  - Optimized spacing

- **> 1024px (desktop):**
  - Full layout
  - Compact spacing

### Touch Interactions
- Tap node to open lesson
- Pinch to zoom graph
- Pan graph with finger drag

## Testing Checklist

- [ ] Renders loading state while fetching subjects
- [ ] Shows error if subjects fetch fails
- [ ] Shows "no subjects" message if empty
- [ ] Auto-selects first subject if only one
- [ ] Renders subject selector if multiple subjects
- [ ] Fetches graph when subject selected
- [ ] Shows "no lessons" message if graph empty
- [ ] Renders GraphVisualization with correct data
- [ ] Navigates to lesson on node click (if unlocked)
- [ ] Shows alert on locked lesson click
- [ ] Refreshes graph when refresh button clicked
- [ ] Updates graph when subject changed
- [ ] Displays progress percentage correctly
- [ ] Shows legend with status colors
- [ ] Responsive on mobile (320px+)
- [ ] No TypeScript errors
- [ ] No console errors
- [ ] Passes accessibility audit

## Dependencies

### Required
- `react` (^18.0.0)
- `react-router-dom` (^6.0.0)
- `@tanstack/react-query` (^5.0.0)
- `d3` (^7.0.0)
- `lucide-react` (icons)

### UI Components (ShadcN)
- `Card`
- `Button`
- `Alert`
- `Skeleton`
- `Select`
- `Progress`

### Custom Components
- `GraphVisualization` (from knowledge-graph components)

## API Endpoints Used

```
GET /api/knowledge-graph/students/{student_id}/subject/{subject_id}/
Response: KnowledgeGraph

GET /api/knowledge-graph/lessons/{lesson_id}/progress/{student_id}/
Response: LessonProgressDetail

GET /api/materials/enrollments/
Response: { enrollments: [] } (for subjects)
```

## Troubleshooting

### Graph Not Loading
1. Check browser console for errors
2. Verify student has enrollments
3. Check backend API is running
4. Verify authentication token is valid

### Locked Lesson Doesn't Show Alert
1. Check `lesson.can_start` property
2. Verify `handleLessonClick` logic
3. Check browser blocks native `alert()`

### Graph Visualization Not Rendering
1. Verify `visualizationData` is correctly transformed
2. Check D3 library is installed
3. Verify `GraphVisualization` component exists
4. Check container has proper height/width

### Subject Selector Not Showing
1. Verify student has multiple subjects
2. Check `subjects` array length
3. Verify Select component imports

## Future Enhancements

- [ ] Export graph as image
- [ ] Fullscreen mode
- [ ] Filter lessons by difficulty
- [ ] Search lessons by title
- [ ] Minimap for large graphs
- [ ] Lesson preview on hover
- [ ] Keyboard shortcuts (e.g., R for refresh)
- [ ] Dark mode support
- [ ] Offline mode with cached data
- [ ] Progress animations on completion

## Support

For issues or questions:
1. Check this README
2. Review example file
3. Check PLAN.md for task details
4. Review backend API documentation
5. Contact development team
