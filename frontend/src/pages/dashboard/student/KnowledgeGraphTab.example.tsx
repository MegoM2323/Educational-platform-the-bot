/**
 * Knowledge Graph Tab - Usage Examples
 *
 * This file demonstrates how to use the KnowledgeGraphTab component
 * in different scenarios.
 */

import React from 'react';
import { KnowledgeGraphTab } from './KnowledgeGraphTab';

/**
 * Example 1: Basic usage in student dashboard
 *
 * The component is self-contained and handles:
 * - Student ID from useProfile hook
 * - Subject selection
 * - Graph fetching and visualization
 * - Lesson navigation
 */
export const Example1_BasicUsage = () => {
  return (
    <div className="h-screen">
      <KnowledgeGraphTab />
    </div>
  );
};

/**
 * Example 2: Embedded in a tab layout
 *
 * Use in a tab container alongside other student pages
 */
export const Example2_TabLayout = () => {
  return (
    <div className="flex flex-col h-screen">
      {/* Tabs navigation would go here */}
      <div className="flex-1 overflow-auto">
        <KnowledgeGraphTab />
      </div>
    </div>
  );
};

/**
 * Example 3: Integration with routing
 *
 * Typical setup in App.tsx or student dashboard routing
 */
export const Example3_RoutingSetup = () => {
  // In your App.tsx or routing file:
  /*
  import { KnowledgeGraphTab } from '@/pages/dashboard/student/KnowledgeGraphTab';

  <Routes>
    <Route path="/dashboard/student" element={<StudentDashboard />}>
      <Route path="knowledge-graph" element={<KnowledgeGraphTab />} />
    </Route>
  </Routes>
  */

  return null;
};

/**
 * Example 4: State diagram of component lifecycle
 *
 * KnowledgeGraphTab component states:
 *
 * 1. Loading subjects → Skeleton
 * 2. No subjects → Alert: "No subjects enrolled"
 * 3. Subjects loaded → Subject selector displayed
 * 4. Subject selected → Loading graph → Skeleton
 * 5. Graph loaded, empty → Alert: "No lessons in graph"
 * 6. Graph loaded, has lessons → GraphVisualization rendered
 * 7. Error at any stage → Error alert with retry button
 *
 * User interactions:
 * - Select subject → Fetches graph for that subject
 * - Click lesson node → Navigate to /lessons/{lessonId} (if not locked)
 * - Click locked lesson → Alert: "Prerequisites not met"
 * - Click refresh → Refetches current graph
 * - Zoom/pan graph → D3 interactions handled by GraphVisualization
 */

/**
 * Example 5: Data flow
 *
 * Component → useProfile → studentId
 * Component → useStudentSubjects → subjects[]
 * Component → useKnowledgeGraph(studentId, subjectId) → graphData
 * Component → transform graphData → GraphData (for D3)
 * Component → GraphVisualization(data, onNodeClick)
 * User clicks node → handleLessonClick → navigate(/lessons/{id})
 */

/**
 * Example 6: Testing scenarios
 *
 * Test cases to verify:
 * 1. ✓ Renders loading state while fetching subjects
 * 2. ✓ Shows error if subjects fetch fails
 * 3. ✓ Shows "no subjects" message if empty
 * 4. ✓ Auto-selects first subject if only one
 * 5. ✓ Renders subject selector if multiple subjects
 * 6. ✓ Fetches graph when subject selected
 * 7. ✓ Shows "no lessons" message if graph empty
 * 8. ✓ Renders GraphVisualization with correct data
 * 9. ✓ Navigates to lesson on node click (if unlocked)
 * 10. ✓ Shows alert on locked lesson click
 * 11. ✓ Refreshes graph when refresh button clicked
 * 12. ✓ Updates graph when subject changed
 * 13. ✓ Displays progress percentage correctly
 * 14. ✓ Shows legend with status colors
 * 15. ✓ Responsive on mobile (320px+)
 */

/**
 * Example 7: Mock data for testing
 */
export const mockGraphData = {
  id: 1,
  student_id: 123,
  student_name: 'Иван Иванов',
  subject_id: 456,
  subject_name: 'Математика',
  lessons: [
    {
      id: 1,
      lesson_id: 101,
      title: 'Введение в алгебру',
      description: 'Основные понятия',
      difficulty: 'easy' as const,
      element_count: 5,
      estimated_time_minutes: 30,
      position_x: 100,
      position_y: 100,
      status: 'completed' as const,
      completion_percent: 100,
      can_start: true,
    },
    {
      id: 2,
      lesson_id: 102,
      title: 'Линейные уравнения',
      description: 'Решение уравнений',
      difficulty: 'medium' as const,
      element_count: 8,
      estimated_time_minutes: 45,
      position_x: 300,
      position_y: 100,
      status: 'in_progress' as const,
      completion_percent: 50,
      can_start: true,
    },
    {
      id: 3,
      lesson_id: 103,
      title: 'Квадратные уравнения',
      description: 'Дискриминант и формула',
      difficulty: 'hard' as const,
      element_count: 10,
      estimated_time_minutes: 60,
      position_x: 500,
      position_y: 100,
      status: 'locked' as const,
      completion_percent: 0,
      can_start: false,
    },
  ],
  dependencies: [
    {
      id: 1,
      from_lesson_id: 101,
      to_lesson_id: 102,
      type: 'prerequisite' as const,
    },
    {
      id: 2,
      from_lesson_id: 102,
      to_lesson_id: 103,
      type: 'prerequisite' as const,
    },
  ],
  total_lessons: 3,
  completed_lessons: 1,
  overall_progress_percent: 33.33,
  created_at: '2025-12-08T00:00:00Z',
  updated_at: '2025-12-08T12:00:00Z',
};

/**
 * Example 8: Accessibility features
 *
 * - Keyboard navigation: Tab through interactive elements
 * - Screen readers: All labels and descriptions provided
 * - Focus management: Focus moves to graph when loaded
 * - Color contrast: All text meets WCAG AA standards
 * - Alternative text: Status icons have aria-labels
 */

/**
 * Example 9: Performance considerations
 *
 * - TanStack Query caching: Subjects cached for 5 minutes
 * - Graph cached for 1 minute
 * - D3 force simulation optimized (150 iterations max)
 * - Debounced window resize handler (250ms)
 * - Memoized graph data transformation
 * - Lazy loading of GraphVisualization component (if needed)
 */

/**
 * Example 10: Mobile responsive behavior
 *
 * Breakpoints:
 * - < 640px (mobile): Stack layout, subject selector full width
 * - 640px-1024px (tablet): 2-column legend, larger touch targets
 * - > 1024px (desktop): Full layout, smaller spacing
 *
 * Touch interactions:
 * - Tap node to open lesson
 * - Pinch to zoom graph
 * - Pan graph with finger drag
 */
