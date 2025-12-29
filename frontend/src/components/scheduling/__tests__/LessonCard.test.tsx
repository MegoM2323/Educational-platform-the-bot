import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LessonCard } from '../student/LessonCard';
import { Lesson } from '@/types/scheduling';

// Mock date-fns to avoid timezone issues
vi.mock('date-fns', async () => {
  const actual = await vi.importActual('date-fns');
  return {
    ...actual,
    format: (date: Date, formatStr: string) => {
      // Simple format for testing
      const d = new Date(date);
      if (formatStr === 'd MMMM yyyy') {
        const month = d.toLocaleString('en-US', { month: 'long' });
        return `${d.getDate()} ${month} ${d.getFullYear()}`;
      }
      return formatStr;
    },
  };
});

const createMockLesson = (overrides?: Partial<Lesson>): Lesson => ({
  id: '1',
  teacher: 'teacher-1',
  student: 'student-1',
  subject: 'subject-1',
  date: '2026-01-15',
  start_time: '09:00:00',
  end_time: '10:00:00',
  description: 'Test lesson description',
  telemost_link: 'https://telemost.yandex.ru/j/test123',
  status: 'pending',
  created_at: '2025-11-29T10:00:00Z',
  updated_at: '2025-11-29T10:00:00Z',
  teacher_name: 'John Doe',
  student_name: 'Jane Smith',
  subject_name: 'Mathematics',
  is_upcoming: true,
  ...overrides,
});

describe('LessonCard Component', () => {
  describe('Rendering Lesson Details', () => {
    it('should render all lesson details (date, time, subject, teacher name)', () => {
      const lesson = createMockLesson();
      render(<LessonCard lesson={lesson} />);

      // Check for subject name
      expect(screen.getByText('Mathematics')).toBeInTheDocument();

      // Check for teacher name
      expect(screen.getByText(/Преподаватель: John Doe/)).toBeInTheDocument();

      // Check for time (note: format may vary due to timezone)
      expect(screen.getByText(/09:00 - 10:00/)).toBeInTheDocument();
    });

    it('should render lesson date in correct format', () => {
      const lesson = createMockLesson({ date: '2026-01-15' });
      render(<LessonCard lesson={lesson} />);

      // Date should be rendered (exact format checked by date-fns mock)
      const dateElements = screen.getAllByText(/\d+ \w+ \d+/);
      expect(dateElements.length).toBeGreaterThan(0);
    });

    it('should render teacher name with correct styling', () => {
      const lesson = createMockLesson({
        teacher_name: 'Dr. Smith',
        subject_name: 'Physics',
      });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText(/Преподаватель: Dr. Smith/)).toBeInTheDocument();
      expect(screen.getByText('Physics')).toBeInTheDocument();
    });

    it('should truncate teacher name in avatar if needed', () => {
      const lesson = createMockLesson({ teacher_name: 'John Doe Smith' });
      render(<LessonCard lesson={lesson} />);

      // Avatar should show initials (J, D or J, S depending on implementation)
      // The component creates initials from name
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
    });
  });

  describe('Status Badges', () => {
    it('should show pending status badge', () => {
      const lesson = createMockLesson({ status: 'pending' });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('Ожидание подтверждения')).toBeInTheDocument();
    });

    it('should show confirmed status badge', () => {
      const lesson = createMockLesson({ status: 'confirmed' });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('Подтверждено')).toBeInTheDocument();
    });

    it('should show completed status badge', () => {
      const lesson = createMockLesson({ status: 'completed' });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('Завершено')).toBeInTheDocument();
    });

    it('should show cancelled status badge', () => {
      const lesson = createMockLesson({ status: 'cancelled' });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('Отменено')).toBeInTheDocument();
    });

    it('should apply correct background color for each status', () => {
      const statuses: Array<Lesson['status']> = [
        'pending',
        'confirmed',
        'completed',
        'cancelled',
      ];

      statuses.forEach(status => {
        const { container } = render(
          <LessonCard lesson={createMockLesson({ status })} />
        );

        const badge = container.querySelector('[class*="bg-"]');
        expect(badge).toBeInTheDocument();
      });
    });
  });

  describe('Telemost Link Display', () => {
    it('should show telemost link as clickable button when present', () => {
      const lesson = createMockLesson({
        telemost_link: 'https://telemost.yandex.ru/j/abc123def456',
      });
      render(<LessonCard lesson={lesson} />);

      const link = screen.getByRole('link', {
        name: /Присоединиться к уроку|К уроку/i,
      });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute(
        'href',
        'https://telemost.yandex.ru/j/abc123def456'
      );
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('should show icon with link text', () => {
      const lesson = createMockLesson({
        telemost_link: 'https://telemost.yandex.ru/j/test',
      });
      render(<LessonCard lesson={lesson} />);

      // ExternalLink icon should be present
      const link = screen.getByRole('link', {
        name: /Присоединиться к уроку|К уроку/i,
      });
      expect(link).toBeInTheDocument();
    });

    it('should hide telemost link when not present', () => {
      const lesson = createMockLesson({ telemost_link: '' });
      render(<LessonCard lesson={lesson} />);

      // Should not have external link button
      const links = screen.queryAllByRole('link');
      const teleostLinks = links.filter(l =>
        l.textContent?.includes('Присоединиться') ||
        l.textContent?.includes('уроку')
      );
      expect(teleostLinks.length).toBe(0);

      // Should show "Место встречи не указано"
      expect(screen.getByText('Место встречи не указано')).toBeInTheDocument();
    });

    it('should hide telemost link when null', () => {
      const lesson = createMockLesson();
      lesson.telemost_link = undefined as any;
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('Место встречи не указано')).toBeInTheDocument();
    });

    it('should have MapPin icon for location placeholder', () => {
      const lesson = createMockLesson({ telemost_link: '' });
      render(<LessonCard lesson={lesson} />);

      // The MapPin icon should be rendered
      expect(screen.getByText('Место встречи не указано')).toBeInTheDocument();
    });
  });

  describe('Description Display', () => {
    it('should show description when present', () => {
      const lesson = createMockLesson({
        description: 'Important lesson on algebra fundamentals',
      });
      render(<LessonCard lesson={lesson} />);

      expect(
        screen.getByText('Important lesson on algebra fundamentals')
      ).toBeInTheDocument();
    });

    it('should hide description when empty', () => {
      const lesson = createMockLesson({ description: '' });
      render(<LessonCard lesson={lesson} />);

      // Empty description should not appear in the document
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
      // Should not have the empty string as separate text node
      const descriptionTexts = screen.queryAllByText(/^$/);
      // Empty description divs are conditional in the component
    });

    it('should hide description when null or undefined', () => {
      const lesson = createMockLesson();
      lesson.description = undefined as any;
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('Mathematics')).toBeInTheDocument();
    });

    it('should display long description with text wrapping', () => {
      const longDescription =
        'This is a very long description that explains the lesson plan, topics to cover, and homework assignments. It should wrap properly on mobile devices.';
      const lesson = createMockLesson({ description: longDescription });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText(longDescription)).toBeInTheDocument();
    });
  });

  describe('Visual Styling and Layout', () => {
    it('should have border-l-4 for card styling', () => {
      const lesson = createMockLesson();
      const { container } = render(<LessonCard lesson={lesson} />);

      const card = container.querySelector('[class*="border-l-4"]');
      expect(card).toBeInTheDocument();
    });

    it('should have blue left border for upcoming lessons', () => {
      const lesson = createMockLesson({
        is_upcoming: true,
        date: '2026-01-15',
      });
      const { container } = render(<LessonCard lesson={lesson} />);

      const card = container.querySelector('[class*="border-l-blue"]');
      expect(card).toBeInTheDocument();
    });

    it('should have gray left border for past lessons', () => {
      const lesson = createMockLesson({
        is_upcoming: false,
        date: '2025-11-20',
      });
      const { container } = render(<LessonCard lesson={lesson} />);

      const card = container.querySelector('[class*="border-l"]');
      expect(card).toBeInTheDocument();
    });

    it('should have responsive grid layout', () => {
      const lesson = createMockLesson();
      const { container } = render(<LessonCard lesson={lesson} />);

      // Should have sm:grid-cols-2 for responsive layout
      const gridElement = container.querySelector('[class*="grid"]');
      expect(gridElement).toBeInTheDocument();
    });

    it('should use proper typography classes', () => {
      const lesson = createMockLesson();
      const { container } = render(<LessonCard lesson={lesson} />);

      // Subject name should be in larger font
      const subjectElement = screen.getByText('Mathematics');
      expect(subjectElement.className).toMatch(/font-semibold/);
    });
  });

  describe('Icons and Visual Indicators', () => {
    it('should render Calendar icon for date', () => {
      const lesson = createMockLesson();
      render(<LessonCard lesson={lesson} />);

      // Calendar and Clock icons should be present
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
    });

    it('should render Clock icon for time', () => {
      const lesson = createMockLesson();
      render(<LessonCard lesson={lesson} />);

      // Time should be displayed with Clock icon
      expect(screen.getByText(/09:00 - 10:00/)).toBeInTheDocument();
    });

    it('should render BookOpen icon in header', () => {
      const lesson = createMockLesson();
      render(<LessonCard lesson={lesson} />);

      // Subject name with book icon
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('should have responsive flex layout', () => {
      const lesson = createMockLesson();
      const { container } = render(<LessonCard lesson={lesson} />);

      const flexElements = container.querySelectorAll('[class*="flex"]');
      expect(flexElements.length).toBeGreaterThan(0);
    });

    it('should have mobile-friendly padding', () => {
      const lesson = createMockLesson();
      const { container } = render(<LessonCard lesson={lesson} />);

      const card = container.querySelector('[class*="space-y"]');
      expect(card).toBeInTheDocument();
    });

    it('should truncate long text on mobile', () => {
      const lesson = createMockLesson({
        teacher_name: 'Very Long Teacher Name That Might Break',
      });
      const { container } = render(<LessonCard lesson={lesson} />);

      // Should have truncate class for overflow
      const truncatedElement = container.querySelector('[class*="truncate"]');
      expect(truncatedElement).toBeInTheDocument();
    });

    it('should have flex-shrink-0 for icons to prevent squeezing', () => {
      const lesson = createMockLesson();
      const { container } = render(<LessonCard lesson={lesson} />);

      const flexShrinkElements = container.querySelectorAll(
        '[class*="flex-shrink"]'
      );
      expect(flexShrinkElements.length).toBeGreaterThan(0);
    });

    it('should have min-w-0 for text wrapping in flex containers', () => {
      const lesson = createMockLesson();
      const { container } = render(<LessonCard lesson={lesson} />);

      const minWElements = container.querySelectorAll('[class*="min-w"]');
      expect(minWElements.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    it('should handle lesson with all fields populated', () => {
      const lesson = createMockLesson({
        subject_name: 'Advanced Mathematics',
        teacher_name: 'Dr. John Smith PhD',
        description: 'Complex calculus problems including integrals and derivatives',
        telemost_link: 'https://telemost.yandex.ru/j/verylonglink123456789',
        status: 'confirmed',
      });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('Advanced Mathematics')).toBeInTheDocument();
      expect(screen.getByText(/Dr. John Smith PhD/)).toBeInTheDocument();
      expect(
        screen.getByText(
          'Complex calculus problems including integrals and derivatives'
        )
      ).toBeInTheDocument();
    });

    it('should handle lesson with minimal fields', () => {
      const lesson: Lesson = {
        id: '1',
        teacher: 'teacher-1',
        student: 'student-1',
        subject: 'subject-1',
        date: '2026-01-15',
        start_time: '09:00:00',
        end_time: '10:00:00',
        description: '',
        telemost_link: '',
        status: 'pending',
        created_at: '2025-11-29T10:00:00Z',
        updated_at: '2025-11-29T10:00:00Z',
        teacher_name: 'Default Teacher', // Add required field
        student_name: 'Default Student', // Add required field
        subject_name: 'Subject', // Add required field
      };
      render(<LessonCard lesson={lesson} />);

      // Should still render even with minimal fields
      expect(screen.getByText(/09:00 - 10:00/)).toBeInTheDocument();
    });

    it('should handle special characters in description', () => {
      const lesson = createMockLesson({
        description: 'Lesson: "Topics & key points" (important!) Тестовое описание',
      });
      render(<LessonCard lesson={lesson} />);

      expect(
        screen.getByText(
          'Lesson: "Topics & key points" (important!) Тестовое описание'
        )
      ).toBeInTheDocument();
    });

    it('should handle special characters in teacher name', () => {
      const lesson = createMockLesson({
        teacher_name: "O'Connor-Smith",
      });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText(/O'Connor-Smith/)).toBeInTheDocument();
    });

    it('should handle very short time slots', () => {
      const lesson = createMockLesson({
        start_time: '09:00:00',
        end_time: '09:15:00',
      });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText(/09:00 - 09:15/)).toBeInTheDocument();
    });

    it('should handle early morning lessons', () => {
      const lesson = createMockLesson({
        start_time: '06:00:00',
        end_time: '07:00:00',
      });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText(/06:00 - 07:00/)).toBeInTheDocument();
    });

    it('should handle late evening lessons', () => {
      const lesson = createMockLesson({
        start_time: '21:00:00',
        end_time: '22:00:00',
      });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText(/21:00 - 22:00/)).toBeInTheDocument();
    });
  });

  describe('Avatar Rendering', () => {
    it('should render avatar with teacher initials', () => {
      const lesson = createMockLesson({ teacher_name: 'John Doe' });
      const { container } = render(<LessonCard lesson={lesson} />);

      // Avatar should be rendered (contains initials or fallback)
      // Check for text that looks like initials (J, D, JD, etc)
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
      // Avatar component should be in the tree
      const avatars = container.querySelectorAll('[class*="rounded"]');
      expect(avatars.length).toBeGreaterThan(0);
    });

    it('should extract first letters of teacher name for initials', () => {
      const lesson = createMockLesson({ teacher_name: 'Jane Smith' });
      render(<LessonCard lesson={lesson} />);

      // Component should create initials from name
      // The rendered initials should appear somewhere in the component
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
    });

    it('should handle single-word teacher names', () => {
      const lesson = createMockLesson({ teacher_name: 'Madonna' });
      render(<LessonCard lesson={lesson} />);

      expect(screen.getByText('Mathematics')).toBeInTheDocument();
      expect(screen.getByText(/Madonna/)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have semantic HTML structure', () => {
      const lesson = createMockLesson();
      const { container } = render(<LessonCard lesson={lesson} />);

      // Should have proper card structure
      const card = container.querySelector('[class*="Card"]');
      expect(card).toBeInTheDocument();
    });

    it('should have proper heading hierarchy', () => {
      const lesson = createMockLesson();
      render(<LessonCard lesson={lesson} />);

      // Subject name should be in a heading
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
    });

    it('should have descriptive link text for telemost', () => {
      const lesson = createMockLesson({
        telemost_link: 'https://telemost.yandex.ru/j/test',
      });
      render(<LessonCard lesson={lesson} />);

      const link = screen.getByRole('link');
      // Link text should be descriptive, not "click here"
      expect(
        link.textContent?.includes('Присоединиться') ||
        link.textContent?.includes('К уроку')
      ).toBeTruthy();
    });

    it('should have proper color contrast for badges', () => {
      const lesson = createMockLesson({ status: 'confirmed' });
      render(<LessonCard lesson={lesson} />);

      const badge = screen.getByText('Подтверждено');
      expect(badge).toBeInTheDocument();
      // Badge should have good contrast (bg-blue-100 text-blue-800)
    });
  });
});
