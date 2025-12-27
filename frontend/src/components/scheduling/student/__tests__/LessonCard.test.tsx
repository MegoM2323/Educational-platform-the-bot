import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LessonCard } from '../LessonCard';
import { Lesson } from '@/types/scheduling';

const mockUpcomingLesson: Lesson = {
  id: '770e8400-e29b-41d4-a716-446655440000',
  teacher: '550e8400-e29b-41d4-a716-446655440001',
  student: '550e8400-e29b-41d4-a716-446655440000',
  subject: '660e8400-e29b-41d4-a716-446655440000',
  date: '2025-12-30',
  start_time: '09:00:00',
  end_time: '10:00:00',
  description: 'Algebra basics lesson',
  telemost_link: 'https://telemost.yandex.ru/j/abcd1234',
  status: 'confirmed',
  created_at: '2025-11-29T10:00:00Z',
  updated_at: '2025-11-29T10:00:00Z',
  teacher_name: 'John Doe',
  student_name: 'Jane Smith',
  subject_name: 'Mathematics',
  is_upcoming: true,
};

const mockPastLesson: Lesson = {
  ...mockUpcomingLesson,
  id: '880e8400-e29b-41d4-a716-446655440000',
  date: '2025-11-01',
  status: 'completed',
  is_upcoming: false,
};

const mockLessonWithoutLink: Lesson = {
  ...mockUpcomingLesson,
  id: '990e8400-e29b-41d4-a716-446655440000',
  telemost_link: '',
};

describe('LessonCard', () => {
  describe('rendering', () => {
    it('should render lesson subject name', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      expect(screen.getByText('Mathematics')).toBeInTheDocument();
    });

    it('should render teacher name', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      expect(screen.getByText(/Преподаватель: John Doe/)).toBeInTheDocument();
    });

    it('should render lesson date', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      // Date format: "30 декабря 2025"
      expect(screen.getByText(/30.*2025/)).toBeInTheDocument();
    });

    it('should render lesson time', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      expect(screen.getByText('09:00 - 10:00')).toBeInTheDocument();
    });

    it('should render description', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      expect(screen.getByText('Algebra basics lesson')).toBeInTheDocument();
    });

    it('should not render description if empty', () => {
      const lessonWithoutDescription = { ...mockUpcomingLesson, description: '' };

      render(<LessonCard lesson={lessonWithoutDescription} />);

      expect(screen.queryByText('Algebra basics lesson')).not.toBeInTheDocument();
    });
  });

  describe('status badge', () => {
    it('should display confirmed status badge', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      expect(screen.getByText('Подтверждено')).toBeInTheDocument();
    });

    it('should display completed status badge', () => {
      render(<LessonCard lesson={mockPastLesson} />);

      expect(screen.getByText('Завершено')).toBeInTheDocument();
    });

    it('should display pending status badge', () => {
      const pendingLesson = { ...mockUpcomingLesson, status: 'pending' as const };
      render(<LessonCard lesson={pendingLesson} />);

      expect(screen.getByText('Ожидание подтверждения')).toBeInTheDocument();
    });

    it('should display cancelled status badge', () => {
      const cancelledLesson = { ...mockUpcomingLesson, status: 'cancelled' as const };
      render(<LessonCard lesson={cancelledLesson} />);

      expect(screen.getByText('Отменено')).toBeInTheDocument();
    });
  });

  describe('telemost link', () => {
    it('should render telemost link button when link provided', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      const link = screen.getByRole('link', { name: /К уроку|Присоединиться/ });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://telemost.yandex.ru/j/abcd1234');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('should not render link button when telemost_link is empty', () => {
      render(<LessonCard lesson={mockLessonWithoutLink} />);

      expect(screen.queryByRole('link')).not.toBeInTheDocument();
    });

    it('should render location placeholder when no telemost link', () => {
      render(<LessonCard lesson={mockLessonWithoutLink} />);

      expect(screen.getByText('Место встречи не указано')).toBeInTheDocument();
    });

    it('should have correct external link icon behavior', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      const link = screen.getByRole('link', { name: /К уроку|Присоединиться/ });
      expect(link).toHaveAttribute('target', '_blank');
    });
  });

  describe('card styling', () => {
    it('should apply blue border for upcoming lessons', () => {
      const { container } = render(<LessonCard lesson={mockUpcomingLesson} />);

      const card = container.querySelector('[class*="border-l-blue"]');
      expect(card).toBeInTheDocument();
    });

    it('should apply gray border for past lessons', () => {
      const { container } = render(<LessonCard lesson={mockPastLesson} />);

      const card = container.querySelector('[class*="border-l-gray"]');
      expect(card).toBeInTheDocument();
    });
  });

  describe('avatar', () => {
    it('should display teacher initials in avatar', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      // Avatar should show first letters of teacher name: "JD" from "John Doe"
      expect(screen.getByText('JD')).toBeInTheDocument();
    });

    it('should handle single-name teachers', () => {
      const lesson = {
        ...mockUpcomingLesson,
        teacher_name: 'Madonna',
      };
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('M')).toBeInTheDocument();
    });

    it('should handle multiple word names for initials', () => {
      const lesson = {
        ...mockUpcomingLesson,
        teacher_name: 'John Michael Doe',
      };
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('JMD')).toBeInTheDocument();
    });
  });

  describe('responsive design', () => {
    it('should render all content in single card', () => {
      const { container } = render(<LessonCard lesson={mockUpcomingLesson} />);

      const card = container.querySelector('[class*="Card"]');
      expect(card).toBeInTheDocument();
    });

    it('should have flex layout for header', () => {
      const { container } = render(<LessonCard lesson={mockUpcomingLesson} />);

      const header = container.querySelector('[class*="flex"]');
      expect(header).toBeInTheDocument();
    });
  });

  describe('date and time formatting', () => {
    it('should format date correctly in Russian locale', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      // Format: "30 декабря 2025"
      expect(screen.getByText(/30/)).toBeInTheDocument();
      expect(screen.getByText(/2025/)).toBeInTheDocument();
    });

    it('should format time in 24-hour format', () => {
      const lesson = {
        ...mockUpcomingLesson,
        start_time: '14:30:00',
        end_time: '15:45:00',
      };
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('14:30 - 15:45')).toBeInTheDocument();
    });

    it('should handle midnight and noon times', () => {
      const lesson = {
        ...mockUpcomingLesson,
        start_time: '00:00:00',
        end_time: '12:00:00',
      };
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('00:00 - 12:00')).toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('should handle very long teacher names', () => {
      const lesson = {
        ...mockUpcomingLesson,
        teacher_name: 'Alexander Christopher Benjamin David William',
      };
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('ACBDW')).toBeInTheDocument();
    });

    it('should handle long description text', () => {
      const longDescription =
        'This is a very long description that talks about algebra basics, ' +
        'including equations, variables, functions, and more advanced topics ' +
        'that will be covered in this lesson series.';

      const lesson = {
        ...mockUpcomingLesson,
        description: longDescription,
      };
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText(longDescription)).toBeInTheDocument();
    });

    it('should handle URLs with special characters', () => {
      const lesson = {
        ...mockUpcomingLesson,
        telemost_link: 'https://telemost.yandex.ru/j/abc-def_123?key=value&other=test',
      };
      render(<LessonCard lesson={lesson} />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'href',
        'https://telemost.yandex.ru/j/abc-def_123?key=value&other=test'
      );
    });
  });

  describe('accessibility', () => {
    it('should have accessible external link', () => {
      render(<LessonCard lesson={mockUpcomingLesson} />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('should have semantic HTML structure', () => {
      const { container } = render(<LessonCard lesson={mockUpcomingLesson} />);

      expect(container.querySelector('h3')).toBeInTheDocument();
      expect(container.querySelector('p')).toBeInTheDocument();
    });
  });
});
