import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GradingPanel } from '../../../pages/GradingPanel';

// Mock the dependencies
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 1, role: 'teacher', email: 'teacher@test.com' },
  }),
}));

vi.mock('@/hooks/useAssignments', () => ({
  useAssignment: () => ({
    data: {
      id: 1,
      title: 'Test Assignment',
      description: 'Test Description',
      max_score: 100,
      due_date: new Date(Date.now() + 86400000).toISOString(),
      status: 'published',
      type: 'homework',
      difficulty_level: 2,
      author: { id: 1, full_name: 'Teacher', email: 'teacher@test.com' },
      assigned_to: [1, 2, 3],
      is_overdue: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    isLoading: false,
    error: null,
  }),
  useAssignmentSubmissions: () => ({
    data: [
      {
        id: 1,
        assignment: 1,
        student: { id: 101, full_name: 'Иван Петров', email: 'ivan@test.com' },
        content: 'Student answer 1',
        status: 'submitted',
        submitted_at: new Date(Date.now() - 3600000).toISOString(),
        updated_at: new Date().toISOString(),
        feedback: '',
      },
      {
        id: 2,
        assignment: 1,
        student: { id: 102, full_name: 'Мария Сидорова', email: 'maria@test.com' },
        content: 'Student answer 2',
        status: 'graded',
        score: 85,
        max_score: 100,
        percentage: 85,
        submitted_at: new Date(Date.now() - 7200000).toISOString(),
        graded_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        feedback: 'Good work',
      },
    ],
    isLoading: false,
    refetch: vi.fn(),
  }),
  useGradeSubmission: () => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    isError: false,
  }),
}));

vi.mock('@/components/assignments/GradingForm', () => ({
  GradingForm: () => <div data-testid="grading-form">Grading Form</div>,
}));

vi.mock('@/components/assignments/SubmissionAnswerDisplay', () => ({
  SubmissionAnswerDisplay: () => <div data-testid="submission-answer">Submission Answers</div>,
}));

vi.mock('@/components/assignments/GradeHistoryView', () => ({
  GradeHistoryView: () => <div data-testid="grade-history">Grade History</div>,
}));

const queryClient = new QueryClient();

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    </BrowserRouter>
  );
};

describe('GradingPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render the grading panel with assignment title', () => {
    renderWithProviders(<GradingPanel />);
    expect(screen.getByText(/Проверка задания/i)).toBeInTheDocument();
  });

  it('should display submission statistics', async () => {
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      expect(screen.getByText(/2 ответов/i)).toBeInTheDocument();
      expect(screen.getByText(/На проверке: 1/i)).toBeInTheDocument();
      expect(screen.getByText(/Оценено: 1/i)).toBeInTheDocument();
    });
  });

  it('should list all submissions', async () => {
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      expect(screen.getByText('Иван Петров')).toBeInTheDocument();
      expect(screen.getByText('Мария Сидорова')).toBeInTheDocument();
    });
  });

  it('should filter submissions by status', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    });

    // Filter to show only graded submissions
    const filterButton = screen.getByRole('combobox');
    await user.click(filterButton);

    const gradedOption = screen.getByRole('option', { name: /Оценено/i });
    await user.click(gradedOption);

    await waitFor(() => {
      expect(screen.queryByText('Иван Петров')).not.toBeInTheDocument();
      expect(screen.getByText('Мария Сидорова')).toBeInTheDocument();
    });
  });

  it('should search submissions by student name', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Поиск по имени или email/i);
    await user.type(searchInput, 'Мария');

    await waitFor(() => {
      expect(screen.queryByText('Иван Петров')).not.toBeInTheDocument();
      expect(screen.getByText('Мария Сидорова')).toBeInTheDocument();
    });
  });

  it('should select a submission and display grading form', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    });

    const submissionButton = screen.getByRole('button', { name: /Иван Петров/i });
    await user.click(submissionButton);

    await waitFor(() => {
      expect(screen.getByTestId('grading-form')).toBeInTheDocument();
      expect(screen.getByTestId('submission-answer')).toBeInTheDocument();
    });
  });

  it('should display selected submission details', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    });

    const submissionButton = screen.getByRole('button', { name: /Иван Петров/i });
    await user.click(submissionButton);

    await waitFor(() => {
      expect(screen.getByText('ivan@test.com')).toBeInTheDocument();
    });
  });

  it('should show grade history tab', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      expect(screen.getByText('Мария Сидорова')).toBeInTheDocument();
    });

    const submissionButton = screen.getByRole('button', { name: /Мария Сидорова/i });
    await user.click(submissionButton);

    const historyTab = screen.getByRole('tab', { name: /История оценок/i });
    await user.click(historyTab);

    await waitFor(() => {
      expect(screen.getByTestId('grade-history')).toBeInTheDocument();
    });
  });

  it('should have responsive layout on mobile', () => {
    renderWithProviders(<GradingPanel />);

    const mainContent = screen.getByRole('main');
    // Check for flex-col lg:flex-row classes (responsive)
    expect(mainContent).toHaveClass('flex-col', 'lg:flex-row');
  });

  it('should display statistics for all submissions', async () => {
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      const stats = screen.getByText(/2 ответов/i).closest('div');
      expect(stats).toBeInTheDocument();
    });
  });

  it('should show default message when no submission selected', () => {
    renderWithProviders(<GradingPanel />);

    expect(screen.getByText(/Выберите ответ для оценивания/i)).toBeInTheDocument();
  });

  it('should handle empty submissions list gracefully', () => {
    vi.mock('@/hooks/useAssignments', () => ({
      useAssignment: () => ({
        data: null,
        isLoading: false,
        error: null,
      }),
      useAssignmentSubmissions: () => ({
        data: [],
        isLoading: false,
        refetch: vi.fn(),
      }),
      useGradeSubmission: () => ({
        mutateAsync: vi.fn(),
        isPending: false,
        isError: false,
      }),
    }));

    renderWithProviders(<GradingPanel />);

    expect(screen.getByText(/Нет ответов для отображения/i)).toBeInTheDocument();
  });
});

describe('Grading Panel - Responsive Design', () => {
  it('should render left panel with submission list', async () => {
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      const leftPanel = screen.getByText(/Ответы на проверку/).closest('div');
      expect(leftPanel).toBeInTheDocument();
    });
  });

  it('should render right panel for grading form', async () => {
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      const rightPanel = screen.getByText(/Выберите ответ для оценивания/).closest('div');
      expect(rightPanel).toBeInTheDocument();
    });
  });
});

describe('Grading Panel - Filter and Search', () => {
  it('should clear search query', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Поиск по имени или email/i) as HTMLInputElement;
    await user.type(searchInput, 'Мария');

    expect(searchInput.value).toBe('Мария');

    await user.clear(searchInput);
    expect(searchInput.value).toBe('');
  });

  it('should search by email', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GradingPanel />);

    await waitFor(() => {
      expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Поиск по имени или email/i);
    await user.type(searchInput, 'ivan@test.com');

    await waitFor(() => {
      expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    });
  });
});
