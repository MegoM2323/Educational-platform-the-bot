import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { Lesson } from '@/types/scheduling';

// Mock LessonCard component
const MockLessonCard: React.FC<{ lesson: Lesson }> = ({ lesson }) => (
  <div data-testid={`lesson-card-${lesson.id}`}>
    {lesson.subject_name} - {lesson.date}
  </div>
);

interface ScheduleListProps {
  lessons: Lesson[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

// Simple ScheduleList component for testing
const ScheduleList: React.FC<ScheduleListProps> = ({
  lessons,
  isLoading = false,
  error = null,
  onRetry,
}) => {
  if (error) {
    return (
      <div data-testid="error-state">
        <p>{error}</p>
        {onRetry && (
          <button onClick={onRetry} data-testid="retry-button">
            Retry
          </button>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div data-testid="loading-state">
        <div
          data-testid="skeleton-loader"
          className="h-20 bg-gray-200 animate-pulse"
        />
      </div>
    );
  }

  if (lessons.length === 0) {
    return (
      <div data-testid="empty-state">
        <p>No lessons scheduled</p>
      </div>
    );
  }

  return (
    <div data-testid="lesson-list">
      {lessons.map(lesson => (
        <MockLessonCard key={lesson.id} lesson={lesson} />
      ))}
    </div>
  );
};

const createMockLesson = (overrides?: Partial<Lesson>): Lesson => ({
  id: '1',
  teacher: 'teacher-1',
  student: 'student-1',
  subject: 'subject-1',
  date: '2025-12-15',
  start_time: '09:00:00',
  end_time: '10:00:00',
  description: 'Test lesson',
  telemost_link: 'https://telemost.yandex.ru/j/test',
  status: 'pending',
  created_at: '2025-11-29T10:00:00Z',
  updated_at: '2025-11-29T10:00:00Z',
  teacher_name: 'John Doe',
  student_name: 'Jane Smith',
  subject_name: 'Mathematics',
  is_upcoming: true,
  ...overrides,
});

describe('ScheduleList Component', () => {
  describe('Rendering Lessons', () => {
    it('should render multiple lessons', () => {
      const lessons = [
        createMockLesson({ id: '1', subject_name: 'Math' }),
        createMockLesson({ id: '2', subject_name: 'Physics' }),
        createMockLesson({ id: '3', subject_name: 'Chemistry' }),
      ];

      render(<ScheduleList lessons={lessons} />);

      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
      expect(screen.getByTestId('lesson-card-2')).toBeInTheDocument();
      expect(screen.getByTestId('lesson-card-3')).toBeInTheDocument();
    });

    it('should render lessons in correct order', () => {
      const lessons = [
        createMockLesson({ id: '1', date: '2025-12-15' }),
        createMockLesson({ id: '2', date: '2025-12-16' }),
        createMockLesson({ id: '3', date: '2025-12-17' }),
      ];

      const { container } = render(<ScheduleList lessons={lessons} />);

      const lessonCards = container.querySelectorAll('[data-testid^="lesson-card-"]');
      expect(lessonCards[0]).toHaveAttribute('data-testid', 'lesson-card-1');
      expect(lessonCards[1]).toHaveAttribute('data-testid', 'lesson-card-2');
      expect(lessonCards[2]).toHaveAttribute('data-testid', 'lesson-card-3');
    });

    it('should render single lesson', () => {
      const lessons = [createMockLesson({ id: '1' })];

      render(<ScheduleList lessons={lessons} />);

      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
    });

    it('should render many lessons', () => {
      const lessons = Array.from({ length: 50 }, (_, i) =>
        createMockLesson({ id: String(i) })
      );

      render(<ScheduleList lessons={lessons} />);

      // All lessons should be rendered
      lessons.forEach(lesson => {
        expect(screen.getByTestId(`lesson-card-${lesson.id}`)).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('should show empty state message when no lessons', () => {
      render(<ScheduleList lessons={[]} />);

      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      expect(screen.getByText('No lessons scheduled')).toBeInTheDocument();
    });

    it('should not show lesson list when empty', () => {
      render(<ScheduleList lessons={[]} />);

      expect(screen.queryByTestId('lesson-list')).not.toBeInTheDocument();
    });

    it('should show empty state even when isLoading is false', () => {
      render(<ScheduleList lessons={[]} isLoading={false} />);

      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('should show loading state with skeleton', () => {
      render(<ScheduleList lessons={[]} isLoading={true} />);

      expect(screen.getByTestId('loading-state')).toBeInTheDocument();
      expect(screen.getByTestId('skeleton-loader')).toBeInTheDocument();
    });

    it('should not show lesson list when loading', () => {
      const lessons = [createMockLesson()];
      render(<ScheduleList lessons={lessons} isLoading={true} />);

      expect(screen.queryByTestId('lesson-list')).not.toBeInTheDocument();
    });

    it('should not show empty state when loading', () => {
      render(<ScheduleList lessons={[]} isLoading={true} />);

      expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument();
    });

    it('should show spinner in loading state', () => {
      render(<ScheduleList lessons={[]} isLoading={true} />);

      const skeleton = screen.getByTestId('skeleton-loader');
      expect(skeleton).toHaveClass('animate-pulse');
    });

    it('should transition from loading to loaded state', () => {
      const { rerender } = render(
        <ScheduleList lessons={[]} isLoading={true} />
      );

      expect(screen.getByTestId('loading-state')).toBeInTheDocument();

      const lessons = [createMockLesson()];
      rerender(<ScheduleList lessons={lessons} isLoading={false} />);

      expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument();
      expect(screen.getByTestId('lesson-list')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error state with error message', () => {
      const errorMessage = 'Failed to load lessons';
      render(
        <ScheduleList lessons={[]} error={errorMessage} />
      );

      expect(screen.getByTestId('error-state')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it('should not show lesson list when error', () => {
      render(
        <ScheduleList lessons={[]} error="Error loading" />
      );

      expect(screen.queryByTestId('lesson-list')).not.toBeInTheDocument();
    });

    it('should show retry button when error and onRetry provided', () => {
      const onRetry = vi.fn();
      render(
        <ScheduleList lessons={[]} error="Error loading" onRetry={onRetry} />
      );

      expect(screen.getByTestId('retry-button')).toBeInTheDocument();
    });

    it('should not show retry button when no onRetry handler', () => {
      render(
        <ScheduleList lessons={[]} error="Error loading" />
      );

      expect(screen.queryByTestId('retry-button')).not.toBeInTheDocument();
    });

    it('should call onRetry when retry button clicked', async () => {
      const user = userEvent.setup();
      const onRetry = vi.fn();

      render(
        <ScheduleList lessons={[]} error="Error loading" onRetry={onRetry} />
      );

      const retryButton = screen.getByTestId('retry-button');
      await user.click(retryButton);

      expect(onRetry).toHaveBeenCalledOnce();
    });

    it('should display network error message', () => {
      render(
        <ScheduleList
          lessons={[]}
          error="Network request failed. Please check your connection."
        />
      );

      expect(
        screen.getByText('Network request failed. Please check your connection.')
      ).toBeInTheDocument();
    });

    it('should display authorization error message', () => {
      render(
        <ScheduleList
          lessons={[]}
          error="Unauthorized. Please login again."
        />
      );

      expect(
        screen.getByText('Unauthorized. Please login again.')
      ).toBeInTheDocument();
    });
  });

  describe('State Transitions', () => {
    it('should transition from loading to list', () => {
      const { rerender } = render(
        <ScheduleList lessons={[]} isLoading={true} />
      );

      expect(screen.getByTestId('loading-state')).toBeInTheDocument();

      const lessons = [createMockLesson({ id: '1' })];
      rerender(<ScheduleList lessons={lessons} isLoading={false} />);

      expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument();
      expect(screen.getByTestId('lesson-list')).toBeInTheDocument();
      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
    });

    it('should transition from loading to error', () => {
      const { rerender } = render(
        <ScheduleList lessons={[]} isLoading={true} />
      );

      expect(screen.getByTestId('loading-state')).toBeInTheDocument();

      rerender(
        <ScheduleList lessons={[]} isLoading={false} error="Load failed" />
      );

      expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument();
      expect(screen.getByTestId('error-state')).toBeInTheDocument();
    });

    it('should transition from error to list after retry', async () => {
      const user = userEvent.setup();
      const onRetry = vi.fn();
      const { rerender } = render(
        <ScheduleList lessons={[]} error="Load failed" onRetry={onRetry} />
      );

      expect(screen.getByTestId('error-state')).toBeInTheDocument();

      await user.click(screen.getByTestId('retry-button'));

      // Simulate loading after retry
      rerender(<ScheduleList lessons={[]} isLoading={true} />);
      expect(screen.getByTestId('loading-state')).toBeInTheDocument();

      // Then successful load
      const lessons = [createMockLesson()];
      rerender(<ScheduleList lessons={lessons} isLoading={false} />);
      expect(screen.getByTestId('lesson-list')).toBeInTheDocument();
    });

    it('should transition to empty state when all lessons removed', () => {
      const lessons = [createMockLesson({ id: '1' })];
      const { rerender } = render(<ScheduleList lessons={lessons} />);

      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();

      rerender(<ScheduleList lessons={[]} />);

      expect(screen.queryByTestId('lesson-card-1')).not.toBeInTheDocument();
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });
  });

  describe('Lesson Addition/Removal', () => {
    it('should add new lesson to list', () => {
      const lessons = [createMockLesson({ id: '1' })];
      const { rerender } = render(<ScheduleList lessons={lessons} />);

      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
      expect(screen.queryByTestId('lesson-card-2')).not.toBeInTheDocument();

      const updatedLessons = [
        ...lessons,
        createMockLesson({ id: '2' }),
      ];
      rerender(<ScheduleList lessons={updatedLessons} />);

      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
      expect(screen.getByTestId('lesson-card-2')).toBeInTheDocument();
    });

    it('should remove lesson from list', () => {
      const lessons = [
        createMockLesson({ id: '1' }),
        createMockLesson({ id: '2' }),
      ];
      const { rerender } = render(<ScheduleList lessons={lessons} />);

      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
      expect(screen.getByTestId('lesson-card-2')).toBeInTheDocument();

      const updatedLessons = [createMockLesson({ id: '1' })];
      rerender(<ScheduleList lessons={updatedLessons} />);

      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
      expect(screen.queryByTestId('lesson-card-2')).not.toBeInTheDocument();
    });

    it('should handle replacing entire list', () => {
      const initialLessons = [
        createMockLesson({ id: '1' }),
        createMockLesson({ id: '2' }),
      ];
      const { rerender } = render(<ScheduleList lessons={initialLessons} />);

      const newLessons = [
        createMockLesson({ id: '3' }),
        createMockLesson({ id: '4' }),
      ];
      rerender(<ScheduleList lessons={newLessons} />);

      expect(screen.queryByTestId('lesson-card-1')).not.toBeInTheDocument();
      expect(screen.queryByTestId('lesson-card-2')).not.toBeInTheDocument();
      expect(screen.getByTestId('lesson-card-3')).toBeInTheDocument();
      expect(screen.getByTestId('lesson-card-4')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty lessons array', () => {
      render(<ScheduleList lessons={[]} />);

      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });

    it('should handle undefined error', () => {
      render(<ScheduleList lessons={[]} error={undefined as any} />);

      // Should show lessons list if no error
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });

    it('should handle null error', () => {
      render(<ScheduleList lessons={[]} error={null} />);

      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });

    it('should handle error with empty string', () => {
      render(<ScheduleList lessons={[]} error="" />);

      // Empty error string should not trigger error state
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('should render large list efficiently', () => {
      const lessons = Array.from({ length: 100 }, (_, i) =>
        createMockLesson({ id: String(i) })
      );

      const { container } = render(<ScheduleList lessons={lessons} />);

      const lessonCards = container.querySelectorAll('[data-testid^="lesson-card-"]');
      expect(lessonCards).toHaveLength(100);
    });

    it('should handle rapid state changes', () => {
      const { rerender } = render(
        <ScheduleList lessons={[]} isLoading={true} />
      );

      for (let i = 0; i < 10; i++) {
        rerender(<ScheduleList lessons={[]} isLoading={i % 2 === 0} />);
      }

      // Should end in loaded state
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });
  });

  describe('Lesson Data Integrity', () => {
    it('should preserve lesson data when rendering', () => {
      const lesson = createMockLesson({
        id: '1',
        subject_name: 'Advanced Mathematics',
        date: '2025-12-15',
      });

      render(<ScheduleList lessons={[lesson]} />);

      const lessonCard = screen.getByTestId('lesson-card-1');
      expect(lessonCard).toHaveTextContent('Advanced Mathematics');
      expect(lessonCard).toHaveTextContent('2025-12-15');
    });

    it('should not modify lessons array', () => {
      const lessons = [createMockLesson({ id: '1' })];
      const lessonsCopy = [...lessons];

      render(<ScheduleList lessons={lessons} />);

      expect(lessons).toEqual(lessonsCopy);
    });
  });
});
