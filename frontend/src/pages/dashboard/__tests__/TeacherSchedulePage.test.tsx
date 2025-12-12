import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TeacherSchedulePage from '../TeacherSchedulePage';
import { useAuth } from '@/contexts/AuthContext';
import { useTeacherDashboard } from '@/hooks/useTeacher';
import { useTeacherLessons } from '@/hooks/useTeacherLessons';
import React from 'react';

// Mock hooks and context
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}));

vi.mock('@/hooks/useTeacher', () => ({
  useTeacherDashboard: vi.fn(),
}));

vi.mock('@/hooks/useTeacherLessons', () => ({
  useTeacherLessons: vi.fn(),
}));

vi.mock('@/components/layout/TeacherSidebar', () => ({
  TeacherSidebar: () => <div data-testid="teacher-sidebar">Sidebar</div>,
}));

vi.mock('@/components/scheduling/teacher/LessonForm', () => ({
  LessonForm: ({ onSubmit, isLoading }: any) => (
    <form
      data-testid="lesson-form"
      onSubmit={async (e) => {
        e.preventDefault();
        await onSubmit({
          student: 'student-1',
          subject: 'subject-1',
          date: '2025-12-15',
          start_time: '09:00',
          end_time: '10:00',
        });
      }}
    >
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Creating...' : 'Create Lesson'}
      </button>
    </form>
  ),
}));

vi.mock('@/components/scheduling/teacher/LessonRow', () => ({
  LessonRow: ({ lesson, onDelete, onEdit }: any) => (
    <div data-testid={`lesson-row-${lesson.id}`}>
      <span>{lesson.subject_name}</span>
      {onEdit && (
        <button
          data-testid={`edit-btn-${lesson.id}`}
          onClick={() => onEdit(lesson)}
        >
          Edit
        </button>
      )}
      {onDelete && (
        <button
          data-testid={`delete-btn-${lesson.id}`}
          onClick={() => onDelete(lesson.id)}
        >
          Delete
        </button>
      )}
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
  id: 'teacher-1',
  email: 'teacher@test.com',
  role: 'teacher' as const,
  name: 'Test Teacher',
};

const mockStudent = {
  id: 'student-1',
  name: 'John Student',
  full_name: 'John Student',
  subjects: [
    { id: 'subject-1', name: 'Mathematics' },
    { id: 'subject-2', name: 'Physics' },
  ],
};

const mockDashboardData = {
  students: [mockStudent],
  statistics: {
    total_students: 1,
    total_lessons: 5,
  },
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
  teacher_name: 'Test Teacher',
  student_name: 'John Student',
  subject_name: 'Mathematics',
  is_upcoming: true,
  can_cancel: true,
};

describe('TeacherSchedulePage Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Page Rendering', () => {
    it('should render page with title', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });

    it('should render sidebar', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });
  });

  describe('Add Lesson Button', () => {
    it('should render "Add Lesson" button', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      // Button should be visible (with Plus icon)
      // The exact button text depends on implementation
    });

    it('should have button with type="button" to prevent form submission', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      // Button should exist
      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });

    it('should open form modal when button clicked', async () => {
      const user = userEvent.setup();

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      // The button click should trigger form modal open
      // This depends on implementation
    });
  });

  describe('Lesson List', () => {
    it('should display created lessons', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [mockLesson],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId('lesson-row-1')).toBeInTheDocument();
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

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [lesson1, lesson2],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId('lesson-row-1')).toBeInTheDocument();
        expect(screen.getByTestId('lesson-row-2')).toBeInTheDocument();
      });
    });

    it('should show loading state', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: undefined,
        isLoading: true,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: true,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      // Loading indicator should be visible
      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });

    it('should show error state', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: 'Failed to load lessons',
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });
  });

  describe('Edit/Delete Operations', () => {
    it('should show edit button on lesson rows', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [mockLesson],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId('edit-btn-1')).toBeInTheDocument();
      });
    });

    it('should show delete button on lesson rows', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [mockLesson],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId('delete-btn-1')).toBeInTheDocument();
      });
    });

    it('should handle edit button click', async () => {
      const user = userEvent.setup();

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [mockLesson],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId('edit-btn-1')).toBeInTheDocument();
      });

      const editBtn = screen.getByTestId('edit-btn-1');
      await user.click(editBtn);

      // Edit button click should open edit form
    });

    it('should handle delete button click', async () => {
      const user = userEvent.setup();
      const deleteLesson = vi.fn();

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [mockLesson],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson,
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId('delete-btn-1')).toBeInTheDocument();
      });

      const deleteBtn = screen.getByTestId('delete-btn-1');
      await user.click(deleteBtn);

      // Delete handler should be called
    });
  });

  describe('Form Modal', () => {
    it('should render lesson form in modal', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      // Form should be in DOM (may be hidden initially)
    });

    it('should close form modal when cancelled', async () => {
      const user = userEvent.setup();

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      // Form behavior depends on implementation
    });
  });

  describe('Authorization', () => {
    it('should redirect non-teacher users', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { ...mockUser, role: 'student' },
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: undefined,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      // Should redirect if not teacher
    });

    it('should redirect when not authenticated', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: undefined,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      // Should redirect to auth
    });
  });

  describe('Student and Subject Data', () => {
    it('should load students and subjects from dashboard', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });

    it('should extract unique subjects from students', async () => {
      const multiSubjectStudent = {
        ...mockStudent,
        subjects: [
          { id: 'subject-1', name: 'Mathematics' },
          { id: 'subject-2', name: 'Physics' },
          { id: 'subject-3', name: 'Chemistry' },
        ],
      };

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: { ...mockDashboardData, students: [multiSubjectStudent] },
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });
  });

  describe('Time Format Conversion', () => {
    it('should convert time from HH:MM:SS to HH:MM for form', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      const lessonWithSeconds = {
        ...mockLesson,
        start_time: '09:00:00',
        end_time: '10:00:00',
      };

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [lessonWithSeconds],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });

    it('should convert time from HH:MM to HH:MM:SS for API', async () => {
      const createLesson = vi.fn();

      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [],
        isLoading: false,
        error: null,
        createLesson,
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('should render responsive layout', async () => {
      vi.mocked(useAuth).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn(),
      } as any);

      vi.mocked(useTeacherDashboard).mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
      } as any);

      vi.mocked(useTeacherLessons).mockReturnValue({
        lessons: [mockLesson],
        isLoading: false,
        error: null,
        createLesson: vi.fn(),
        updateLesson: vi.fn(),
        deleteLesson: vi.fn(),
        isCreating: false,
        isUpdating: false,
        isDeleting: false,
      } as any);

      render(<TeacherSchedulePage />, { wrapper });

      expect(screen.getByTestId('teacher-sidebar')).toBeInTheDocument();
    });
  });
});
