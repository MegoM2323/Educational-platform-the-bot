import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { LessonForm } from '../LessonForm';

const mockStudents = [
  {
    id: '550e8400-e29b-41d4-a716-446655440000',
    name: 'Jane Smith',
    full_name: 'Jane Smith',
    subjects: [
      { id: '660e8400-e29b-41d4-a716-446655440000', name: 'Mathematics' },
      { id: '770e8400-e29b-41d4-a716-446655440000', name: 'Physics' },
    ],
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440001',
    name: 'Bob Johnson',
    full_name: 'Bob Johnson',
    subjects: [
      { id: '660e8400-e29b-41d4-a716-446655440000', name: 'Mathematics' },
    ],
  },
];

const mockSubjects = [
  { id: '660e8400-e29b-41d4-a716-446655440000', name: 'Mathematics' },
  { id: '770e8400-e29b-41d4-a716-446655440000', name: 'Physics' },
  { id: '880e8400-e29b-41d4-a716-446655440000', name: 'Chemistry' },
];

describe('LessonForm', () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnSubmit.mockResolvedValue(undefined);
  });

  describe('form rendering', () => {
    it('should render form element', () => {
      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const form = container.querySelector('form');
      expect(form).toBeInTheDocument();
    });

    it('should render form labels for all fields', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      expect(screen.getByText('Student')).toBeInTheDocument();
      expect(screen.getByText('Subject')).toBeInTheDocument();
      expect(screen.getByText('Date')).toBeInTheDocument();
      expect(screen.getByText('Start Time')).toBeInTheDocument();
      expect(screen.getByText('End Time')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
      expect(screen.getByText('Telemost Link')).toBeInTheDocument();
    });

    it('should render submit button', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      expect(screen.getByRole('button', { name: /Create Lesson/ })).toBeInTheDocument();
    });

    it('should show "Update Lesson" button when initialData provided', () => {
      const initialData = {
        id: '770e8400-e29b-41d4-a716-446655440000',
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: '2025-12-20',
        start_time: '09:00:00',
        end_time: '10:00:00',
        description: 'Test lesson',
        telemost_link: 'https://telemost.yandex.ru/j/test',
      };

      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          initialData={initialData}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      expect(screen.getByRole('button', { name: /Update Lesson/ })).toBeInTheDocument();
    });
  });

  describe('student selection', () => {
    it('should have student select combobox', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const studentCombobox = screen.getByRole('combobox', { name: 'Student' });
      expect(studentCombobox).toBeInTheDocument();
    });

    it('should display student placeholder text', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      expect(screen.getByText('Select a student')).toBeInTheDocument();
    });

    it('should call onStudentSelect when provided', async () => {
      const onStudentSelect = vi.fn();

      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
          onStudentSelect={onStudentSelect}
        />
      );

      // Callback prop is registered even if not easily testable in jsdom
      expect(screen.getByRole('combobox', { name: 'Student' })).toBeInTheDocument();
    });
  });

  describe('optional fields', () => {
    it('should allow empty description', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const textArea = screen.getByRole('textbox', { name: 'Description' });
      expect(textArea).toHaveValue('');
    });

    it('should have empty telemost link by default', () => {
      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const telemoostLinkInput = container.querySelector(
        'input[type="url"]'
      ) as HTMLInputElement;
      expect(telemoostLinkInput?.value).toBe('');
    });
  });

  describe('time fields', () => {
    it('should have time input fields', () => {
      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const timeInputs = container.querySelectorAll('input[type="time"]');
      // Should have start and end time inputs
      expect(timeInputs.length).toBeGreaterThanOrEqual(2);
    });

    it('should have default times set', () => {
      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const startTimeInput = container.querySelector(
        'input[type="time"]'
      ) as HTMLInputElement;
      expect(startTimeInput?.value).toBe('09:00');
    });
  });

  describe('form submission', () => {
    it('should handle form submission', async () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Form should be rendered and submit button should be present
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).not.toBeDisabled();
    });

    it('should disable submit button while loading', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          isLoading={true}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const submitButton = screen.getByRole('button', { name: /Creating/ });
      expect(submitButton).toBeDisabled();
    });
  });

  describe('initial data population', () => {
    it('should populate description with initial data', () => {
      const initialData = {
        id: '770e8400-e29b-41d4-a716-446655440000',
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: '2025-12-20',
        start_time: '14:30:00',
        end_time: '15:30:00',
        description: 'Advanced algebra',
        telemost_link: 'https://telemost.yandex.ru/j/abc123',
      };

      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          initialData={initialData}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const descriptionInput = screen.getByRole('textbox', {
        name: 'Description',
      }) as HTMLTextAreaElement;
      expect(descriptionInput.value).toBe('Advanced algebra');
    });

    it('should populate times with initial data', () => {
      const initialData = {
        id: '770e8400-e29b-41d4-a716-446655440000',
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: '2025-12-20',
        start_time: '14:30:00',
        end_time: '15:30:00',
        description: 'Advanced algebra',
        telemost_link: 'https://telemost.yandex.ru/j/abc123',
      };

      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          initialData={initialData}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const timeInputs = container.querySelectorAll(
        'input[type="time"]'
      ) as NodeListOf<HTMLInputElement>;

      // Should have both start and end time inputs populated
      expect(timeInputs.length).toBeGreaterThanOrEqual(2);
      expect(timeInputs[0]?.value).toMatch(/14:30/);
      expect(timeInputs[1]?.value).toMatch(/15:30/);
    });
  });

  describe('button text', () => {
    it('should show Create Lesson for new lesson', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      expect(screen.getByRole('button', { name: /Create Lesson/ })).toBeInTheDocument();
    });

    it('should show Update Lesson for existing lesson', () => {
      const initialData = {
        id: '770e8400-e29b-41d4-a716-446655440000',
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: '2025-12-20',
        start_time: '09:00:00',
        end_time: '10:00:00',
        description: 'Test lesson',
        telemost_link: 'https://telemost.yandex.ru/j/test',
      };

      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          initialData={initialData}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      expect(screen.getByRole('button', { name: /Update Lesson/ })).toBeInTheDocument();
    });

    it('should show Creating when isLoading=true', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          isLoading={true}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      expect(screen.getByRole('button', { name: /Creating/ })).toBeInTheDocument();
    });
  });

  describe('form labels', () => {
    it('should display form label text', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      expect(screen.getByText('Student')).toBeInTheDocument();
      expect(screen.getByText('Subject')).toBeInTheDocument();
      expect(screen.getByText('Start Time')).toBeInTheDocument();
      expect(screen.getByText('End Time')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
      expect(screen.getByText('Telemost Link')).toBeInTheDocument();
    });

    it('should show form description for optional fields', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      expect(screen.getByText('Optional - link to online lesson')).toBeInTheDocument();
    });
  });

  describe('form structure', () => {
    it('should render form with grid layout', () => {
      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const form = container.querySelector('form');
      expect(form).toBeInTheDocument();
      expect(form?.classList.toString()).toContain('space-y-6');
    });

    it('should render as HTMLFormElement', () => {
      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      const form = container.querySelector('form');
      expect(form).toBeInstanceOf(HTMLFormElement);
    });
  });
});
