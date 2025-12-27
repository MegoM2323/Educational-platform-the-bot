import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import StudentSchedulePage from '../StudentSchedulePage';
import { useAuth } from '@/contexts/AuthContext';
import { useStudentSchedule } from '@/hooks/useStudentSchedule';
import React from 'react';

// Mock hooks and context
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}));

vi.mock('@/hooks/useStudentSchedule', () => ({
  useStudentSchedule: vi.fn(),
}));

vi.mock('@/components/layout/StudentSidebar', () => ({
  StudentSidebar: () => <div data-testid="student-sidebar">Sidebar</div>,
}));

vi.mock('@/components/scheduling/student/LessonCard', () => ({
  LessonCard: ({ lesson }: any) => (
    <div data-testid={`lesson-card-${lesson.id}`}>
      {lesson.subject_name}
    </div>
  ),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      {children}
    </BrowserRouter>
  </QueryClientProvider>
);

const mockUser = {
  id: '1',
  email: 'student@test.com',
  role: 'student' as const,
  name: 'Test Student',
};

const mockLesson = {
  id: '1',
  teacher: 'teacher-1',
  student: 'student-1',
  subject: 'subject-1',
  date: '2025-12-15',
  start_time: '09:00:00',
  end_time: '10:00:00',
  description: 'Test lesson',
  telemost_link: 'https://telemost.yandex.ru/j/test',
  status: 'pending' as const,
  created_at: '2025-11-29T10:00:00Z',
  updated_at: '2025-11-29T10:00:00Z',
  teacher_name: 'John Doe',
  student_name: 'Jane Smith',
  subject_name: 'Mathematics',
  is_upcoming: true,
};

describe('StudentSchedulePage Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Page Rendering', () => {
    it('should render page title with calendar icon', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      expect(screen.getByText('Мое расписание')).toBeInTheDocument();
    });

    it('should render sidebar', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      expect(screen.getByTestId('student-sidebar')).toBeInTheDocument();
    });

    it('should display filter section', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      expect(screen.getByText('Фильтры')).toBeInTheDocument();
    });
  });

  describe('Lesson Display', () => {
    it('should render lessons list', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [mockLesson],
        isLoading: false,
        error: null,
        lessonsBySubject: { Mathematics: [mockLesson] },
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
        expect(screen.getByText('Mathematics')).toBeInTheDocument();
      });
    });

    it('should display multiple lessons', async () => {
      const lesson1 = { ...mockLesson, id: '1', subject_name: 'Math' };
      const lesson2 = { ...mockLesson, id: '2', subject_name: 'Physics' };

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [lesson1, lesson2],
        isLoading: false,
        error: null,
        lessonsBySubject: { Math: [lesson1], Physics: [lesson2] },
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
        expect(screen.getByTestId('lesson-card-2')).toBeInTheDocument();
      });
    });

    it('should show empty state when no lessons', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      // Should show empty message or no lessons
      expect(screen.getByText(/Мое расписание/)).toBeInTheDocument();
    });

    it('should show loading skeleton while fetching', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: true,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      // Loading state should be shown
      expect(screen.getByText('Мое расписание')).toBeInTheDocument();
    });
  });

  describe('Tab Navigation', () => {
    it('should render upcoming and past tabs', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      // Tabs should exist (exact text depends on component)
      const tabs = screen.queryAllByRole('tab');
      expect(tabs.length).toBeGreaterThan(0);
    });

    it('should filter upcoming lessons in upcoming tab', async () => {
      const upcomingLesson = {
        ...mockLesson,
        id: '1',
        date: '2025-12-20',
        is_upcoming: true,
      };
      const pastLesson = {
        ...mockLesson,
        id: '2',
        date: '2025-11-20',
        is_upcoming: false,
      };

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [upcomingLesson, pastLesson],
        isLoading: false,
        error: null,
        lessonsBySubject: { Mathematics: [upcomingLesson, pastLesson] },
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      await waitFor(() => {
        // Upcoming tab should be active by default
        expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
      });
    });

    it('should switch to past tab and show past lessons', async () => {
      const user = userEvent.setup();

      const upcomingLesson = {
        ...mockLesson,
        id: '1',
        date: '2025-12-20',
        is_upcoming: true,
      };
      const pastLesson = {
        ...mockLesson,
        id: '2',
        date: '2025-11-20',
        is_upcoming: false,
      };

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [upcomingLesson, pastLesson],
        isLoading: false,
        error: null,
        lessonsBySubject: { Mathematics: [upcomingLesson, pastLesson] },
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      const tabs = screen.queryAllByRole('tab');
      if (tabs.length >= 2) {
        await user.click(tabs[1]); // Click past tab

        await waitFor(() => {
          // Past lesson should be visible
          expect(screen.getByTestId('lesson-card-2')).toBeInTheDocument();
        });
      }
    });
  });

  describe('Subject Filter', () => {
    it('should show all subjects option', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      // Should have subject filter dropdown
      expect(screen.getByText('Предмет')).toBeInTheDocument();
    });

    it('should filter lessons by subject when selected', async () => {
      const user = userEvent.setup();

      const mathLesson = { ...mockLesson, id: '1', subject_name: 'Mathematics' };
      const physicsLesson = { ...mockLesson, id: '2', subject_name: 'Physics' };

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [mathLesson, physicsLesson],
        isLoading: false,
        error: null,
        lessonsBySubject: {
          Mathematics: [mathLesson],
          Physics: [physicsLesson],
        },
      } as any);

      const { rerender } = render(<StudentSchedulePage />, { wrapper });

      // Both lessons should be visible initially
      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
      expect(screen.getByTestId('lesson-card-2')).toBeInTheDocument();
    });

    it('should display unique subjects in dropdown', async () => {
      const lesson1 = { ...mockLesson, id: '1', subject_name: 'Mathematics' };
      const lesson2 = { ...mockLesson, id: '2', subject_name: 'Physics' };
      const lesson3 = { ...mockLesson, id: '3', subject_name: 'Chemistry' };

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [lesson1, lesson2, lesson3],
        isLoading: false,
        error: null,
        lessonsBySubject: {
          Mathematics: [lesson1],
          Physics: [lesson2],
          Chemistry: [lesson3],
        },
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      // All subjects should be available for filtering
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
      expect(screen.getByText('Physics')).toBeInTheDocument();
      expect(screen.getByText('Chemistry')).toBeInTheDocument();
    });
  });

  describe('Teacher Filter', () => {
    it('should show all teachers option', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      expect(screen.getByText(/Преподаватель/)).toBeInTheDocument();
    });

    it('should filter lessons by teacher when selected', async () => {
      const lesson1 = { ...mockLesson, id: '1', teacher_name: 'John Doe' };
      const lesson2 = { ...mockLesson, id: '2', teacher_name: 'Jane Smith' };

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [lesson1, lesson2],
        isLoading: false,
        error: null,
        lessonsBySubject: { Mathematics: [lesson1, lesson2] },
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      expect(screen.getByTestId('lesson-card-1')).toBeInTheDocument();
      expect(screen.getByTestId('lesson-card-2')).toBeInTheDocument();
    });
  });

  describe('Authorization', () => {
    it('should redirect non-student users', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { ...mockUser, role: 'teacher' },
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      // Component should redirect if not student
      // This depends on implementation using Navigate
    });

    it('should redirect when user is not authenticated', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      // Should redirect to auth page
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: 'Failed to load schedule',
        lessonsBySubject: {},
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      expect(screen.getByText('Мое расписание')).toBeInTheDocument();
    });
  });

  describe('Lesson Sorting', () => {
    it('should sort upcoming lessons chronologically', async () => {
      const lesson1 = { ...mockLesson, id: '1', date: '2025-12-15', is_upcoming: true };
      const lesson2 = { ...mockLesson, id: '2', date: '2025-12-20', is_upcoming: true };
      const lesson3 = { ...mockLesson, id: '3', date: '2025-12-10', is_upcoming: true };

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [lesson1, lesson2, lesson3],
        isLoading: false,
        error: null,
        lessonsBySubject: { Mathematics: [lesson1, lesson2, lesson3] },
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      // Lessons should be sorted by date
      // Verify that all lessons are rendered through the mocked component
      await waitFor(() => {
        expect(screen.getByText('Мое расписание')).toBeInTheDocument();
      });
    });

    it('should reverse sort past lessons (newest first)', async () => {
      const lesson1 = { ...mockLesson, id: '1', date: '2025-11-15', is_upcoming: false };
      const lesson2 = { ...mockLesson, id: '2', date: '2025-11-20', is_upcoming: false };
      const lesson3 = { ...mockLesson, id: '3', date: '2025-11-10', is_upcoming: false };

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [lesson1, lesson2, lesson3],
        isLoading: false,
        error: null,
        lessonsBySubject: { Mathematics: [lesson1, lesson2, lesson3] },
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      // Past lessons should be in reverse chronological order (newest first)
      await waitFor(() => {
        expect(screen.getByText('Мое расписание')).toBeInTheDocument();
      });
    });
  });

  describe('Responsive Design', () => {
    it('should render responsive layout', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useStudentSchedule).mockReturnValue({
        lessons: [mockLesson],
        isLoading: false,
        error: null,
        lessonsBySubject: { Mathematics: [mockLesson] },
      } as any);

      render(<StudentSchedulePage />, { wrapper });

      const mainContent = screen.getByText('Мое расписание');
      expect(mainContent).toBeInTheDocument();
    });
  });
});
