import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import AssignmentCreate from '../AssignmentCreate';
import * as assignmentsAPI from '@/integrations/api/assignmentsAPI';
import { toast } from 'sonner';

// Mock the API
vi.mock('@/integrations/api/assignmentsAPI');
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({}),
  };
});

const renderComponent = () => {
  return render(
    <BrowserRouter>
      <AssignmentCreate />
    </BrowserRouter>
  );
};

describe('AssignmentCreate Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Form Rendering', () => {
    it('should render all form fields', () => {
      renderComponent();

      expect(screen.getByLabelText(/Название задания/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Описание/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Инструкции/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Тип задания/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Максимальный балл/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Уровень сложности/i)).toBeInTheDocument();
    });

    it('should render tabs for form sections', () => {
      renderComponent();

      expect(screen.getByRole('tab', { name: /Общие/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Вопросы/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Рубрика/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Параметры/i })).toBeInTheDocument();
    });

    it('should have default form values', () => {
      renderComponent();

      const titleInput = screen.getByLabelText(/Название задания/i) as HTMLInputElement;
      const typeSelect = screen.getByLabelText(/Тип задания/i) as HTMLSelectElement;

      expect(titleInput.value).toBe('');
    });
  });

  describe('Form Validation', () => {
    it('should show validation error for empty title', async () => {
      const user = userEvent.setup();
      renderComponent();

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Название должно содержать минимум 3 символа/i)
        ).toBeInTheDocument();
      });
    });

    it('should show validation error for short description', async () => {
      const user = userEvent.setup();
      renderComponent();

      const descriptionInput = screen.getByLabelText(/Описание/i);
      await user.clear(descriptionInput);
      await user.type(descriptionInput, 'Short');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Описание должно содержать минимум 10 символов/i)
        ).toBeInTheDocument();
      });
    });

    it('should show validation error for past due date', async () => {
      const user = userEvent.setup();
      renderComponent();

      // Click on settings tab
      const settingsTab = screen.getByRole('tab', { name: /Параметры/i });
      await user.click(settingsTab);

      const dueDate = screen.getByLabelText(/Дата сдачи/i);
      const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0];

      await user.clear(dueDate);
      await user.type(dueDate, yesterday);

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Дата сдачи должна быть в будущем/i)
        ).toBeInTheDocument();
      });
    });

    it('should validate due_date > start_date', async () => {
      const user = userEvent.setup();
      renderComponent();

      // Click on settings tab
      const settingsTab = screen.getByRole('tab', { name: /Параметры/i });
      await user.click(settingsTab);

      const startDate = screen.getByLabelText(/Дата начала/i);
      const dueDate = screen.getByLabelText(/Дата сдачи/i);

      const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0];
      const today = new Date().toISOString().split('T')[0];

      await user.clear(startDate);
      await user.type(startDate, tomorrow);

      await user.clear(dueDate);
      await user.type(dueDate, today);

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Дата сдачи должна быть позже даты начала/i)
        ).toBeInTheDocument();
      });
    });

    it('should validate max_score range', async () => {
      const user = userEvent.setup();
      renderComponent();

      const maxScoreInput = screen.getByLabelText(/Максимальный балл/i);

      await user.clear(maxScoreInput);
      await user.type(maxScoreInput, '0');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/Максимальный балл должен быть больше 0/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('should submit form with valid data', async () => {
      const user = userEvent.setup();
      const mockCreateAssignment = vi.fn().mockResolvedValue({
        id: 1,
        title: 'Test Assignment',
        description: 'Test Description',
      });
      (assignmentsAPI.createAssignment as any) = mockCreateAssignment;

      renderComponent();

      const titleInput = screen.getByLabelText(/Название задания/i);
      const descriptionInput = screen.getByLabelText(/Описание/i);
      const instructionsInput = screen.getByLabelText(/Инструкции/i);

      await user.type(titleInput, 'Test Assignment');
      await user.type(descriptionInput, 'This is a test description for assignment');
      await user.type(instructionsInput, 'Complete all questions');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockCreateAssignment).toHaveBeenCalled();
        expect(toast.success).toHaveBeenCalledWith('Задание создано');
      });
    });

    it('should show error message on API failure', async () => {
      const user = userEvent.setup();
      const mockError = new Error('API Error');
      (mockError as any).response = {
        data: { detail: 'Server error' },
      };
      const mockCreateAssignment = vi.fn().mockRejectedValue(mockError);
      (assignmentsAPI.createAssignment as any) = mockCreateAssignment;

      renderComponent();

      const titleInput = screen.getByLabelText(/Название задания/i);
      const descriptionInput = screen.getByLabelText(/Описание/i);
      const instructionsInput = screen.getByLabelText(/Инструкции/i);

      await user.type(titleInput, 'Test Assignment');
      await user.type(descriptionInput, 'This is a test description');
      await user.type(instructionsInput, 'Complete questions');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Server error');
      });
    });
  });

  describe('Character Counters', () => {
    it('should display character count for title', async () => {
      const user = userEvent.setup();
      renderComponent();

      const titleInput = screen.getByLabelText(/Название задания/i);

      expect(screen.getByText('0/200 символов')).toBeInTheDocument();

      await user.type(titleInput, 'Test');

      expect(screen.getByText('4/200 символов')).toBeInTheDocument();
    });

    it('should display character count for description', async () => {
      const user = userEvent.setup();
      renderComponent();

      const descriptionInput = screen.getByLabelText(/Описание/i);

      expect(screen.getByText('0/5000 символов')).toBeInTheDocument();

      await user.type(descriptionInput, 'Description text');

      expect(screen.getByText('16/5000 символов')).toBeInTheDocument();
    });
  });

  describe('Question Management', () => {
    it('should show "Add Question" button in Questions tab', async () => {
      const user = userEvent.setup();
      renderComponent();

      const questionsTab = screen.getByRole('tab', { name: /Вопросы/i });
      await user.click(questionsTab);

      expect(screen.getByRole('button', { name: /Добавить вопрос/i })).toBeInTheDocument();
    });

    it('should toggle question form visibility', async () => {
      const user = userEvent.setup();
      renderComponent();

      const questionsTab = screen.getByRole('tab', { name: /Вопросы/i });
      await user.click(questionsTab);

      const addButton = screen.getByRole('button', { name: /Добавить вопрос/i });

      await user.click(addButton);
      expect(screen.getByRole('button', { name: /Отмена/i })).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: /Отмена/i }));
      expect(screen.queryByText(/Текст вопроса/i)).not.toBeInTheDocument();
    });

    it('should display empty state when no questions added', async () => {
      const user = userEvent.setup();
      renderComponent();

      const questionsTab = screen.getByRole('tab', { name: /Вопросы/i });
      await user.click(questionsTab);

      expect(screen.getByText(/Вопросы еще не добавлены/i)).toBeInTheDocument();
    });
  });

  describe('Rubric Management', () => {
    it('should show "Add Rubric" button in Rubric tab', async () => {
      const user = userEvent.setup();
      renderComponent();

      const rubricTab = screen.getByRole('tab', { name: /Рубрика/i });
      await user.click(rubricTab);

      expect(
        screen.getByRole('button', { name: /Добавить критерий/i })
      ).toBeInTheDocument();
    });

    it('should display empty state when no rubric criteria added', async () => {
      const user = userEvent.setup();
      renderComponent();

      const rubricTab = screen.getByRole('tab', { name: /Рубрика/i });
      await user.click(rubricTab);

      expect(screen.getByText(/Критерии оценки еще не добавлены/i)).toBeInTheDocument();
    });
  });

  describe('Settings Tab', () => {
    it('should display date fields in settings tab', async () => {
      const user = userEvent.setup();
      renderComponent();

      const settingsTab = screen.getByRole('tab', { name: /Параметры/i });
      await user.click(settingsTab);

      expect(screen.getByLabelText(/Дата начала/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Дата сдачи/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Время на выполнение/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Количество попыток/i)).toBeInTheDocument();
    });

    it('should allow setting optional time limit', async () => {
      const user = userEvent.setup();
      renderComponent();

      const settingsTab = screen.getByRole('tab', { name: /Параметры/i });
      await user.click(settingsTab);

      const timeLimitInput = screen.getByLabelText(/Время на выполнение/i);
      await user.type(timeLimitInput, '60');

      expect(timeLimitInput).toHaveValue(60);
    });
  });

  describe('Form Reset', () => {
    it('should cancel and navigate back', async () => {
      const user = userEvent.setup();
      renderComponent();

      const cancelButton = screen.getByRole('button', { name: /Отмена/i });
      await user.click(cancelButton);

      expect(mockNavigate).toHaveBeenCalledWith(-1);
    });
  });

  describe('Responsive Design', () => {
    it('should render properly on mobile screens', () => {
      // Simulate mobile viewport
      global.innerWidth = 375;
      renderComponent();

      const card = screen.getByRole('heading', { name: /Создание задания/i });
      expect(card).toBeInTheDocument();

      // Check that form elements are still accessible
      expect(screen.getByLabelText(/Название задания/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper form labels', () => {
      renderComponent();

      expect(screen.getByLabelText(/Название задания/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Описание/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Инструкции/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Тип задания/i)).toBeInTheDocument();
    });

    it('should have descriptive helper text', () => {
      renderComponent();

      expect(
        screen.getByText(/Максимальное количество баллов за выполнение задания/i)
      ).toBeInTheDocument();
    });
  });
});
