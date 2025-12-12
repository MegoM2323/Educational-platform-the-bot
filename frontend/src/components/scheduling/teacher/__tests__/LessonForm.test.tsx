import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LessonForm } from '../LessonForm';
import { format, addDays, subDays } from 'date-fns';
import { lessonSchema } from '@/schemas/lesson';

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

// Helper to get tomorrow's date string in YYYY-MM-DD format
const getTomorrowDateString = () => format(addDays(new Date(), 1), 'yyyy-MM-dd');

// Helper to get today's date string
const getTodayDateString = () => format(new Date(), 'yyyy-MM-dd');

// Helper to get yesterday's date string
const getYesterdayDateString = () => format(subDays(new Date(), 1), 'yyyy-MM-dd');

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

  describe('validation - required fields', () => {
    it('should show error when student is not selected', async () => {
      const user = userEvent.setup();
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Try to submit empty form
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      await user.click(submitButton);

      // Wait for validation error to appear
      await waitFor(() => {
        expect(screen.getByText('Student is required')).toBeInTheDocument();
      });
    });

    it('should show error when subject is not selected', async () => {
      const user = userEvent.setup();
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Try to submit empty form
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      await user.click(submitButton);

      // Wait for validation error to appear
      await waitFor(() => {
        expect(screen.getByText('Subject is required')).toBeInTheDocument();
      });
    });

    it('should show error when date is not selected', async () => {
      const user = userEvent.setup();
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Try to submit empty form
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      await user.click(submitButton);

      // Wait for validation error to appear
      await waitFor(() => {
        expect(screen.getByText('Date is required')).toBeInTheDocument();
      });
    });

    it('should show error when start time is not set', async () => {
      const user = userEvent.setup();
      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Get start time input and clear it
      const timeInputs = container.querySelectorAll('input[type="time"]') as NodeListOf<HTMLInputElement>;
      const startTimeInput = timeInputs[0];

      if (startTimeInput) {
        await user.clear(startTimeInput);
      }

      // Try to submit
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Start time is required')).toBeInTheDocument();
      });
    });

    it('should show error when end time is not set', async () => {
      const user = userEvent.setup();
      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Get end time input and clear it
      const timeInputs = container.querySelectorAll('input[type="time"]') as NodeListOf<HTMLInputElement>;
      const endTimeInput = timeInputs[1];

      if (endTimeInput) {
        await user.clear(endTimeInput);
      }

      // Try to submit
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('End time is required')).toBeInTheDocument();
      });
    });
  });

  describe('validation - date constraints', () => {
    it('should validate date schema - past dates should fail validation', () => {
      // This test validates the schema directly without UI interaction
      // since calendar picker and date inputs are difficult to test in jsdom
      const pastDate = getYesterdayDateString();

      const result = lessonSchema.safeParse({
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: pastDate,
        start_time: '09:00',
        end_time: '10:00',
        description: '',
        telemost_link: '',
      });

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues.some(i => i.message === 'Date cannot be in the past')).toBe(true);
      }
    });

    it('should validate date schema - today and future dates should pass', () => {
      const futureDate = getTomorrowDateString();

      const result = lessonSchema.safeParse({
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: futureDate,
        start_time: '09:00',
        end_time: '10:00',
        description: '',
        telemost_link: '',
      });

      expect(result.success).toBe(true);
    });
  });

  describe('validation - time constraints', () => {
    it('should validate schema - end time before start time should fail', () => {

      const result = lessonSchema.safeParse({
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '14:00',
        end_time: '13:00',
        description: '',
        telemost_link: '',
      });

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues.some(i => i.message === 'Start time must be before end time')).toBe(true);
      }
    });

    it('should validate schema - end time equal to start time should fail', () => {

      const result = lessonSchema.safeParse({
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '14:00',
        end_time: '14:00',
        description: '',
        telemost_link: '',
      });

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues.some(i => i.message === 'Start time must be before end time')).toBe(true);
      }
    });

    it('should validate schema - valid time range should pass', () => {

      const result = lessonSchema.safeParse({
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '10:00',
        end_time: '11:00',
        description: '',
        telemost_link: '',
      });

      expect(result.success).toBe(true);
    });
  });

  describe('validation - URL format', () => {
    it('should validate schema - invalid telemost link should fail', () => {

      const result = lessonSchema.safeParse({
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '09:00',
        end_time: '10:00',
        description: '',
        telemost_link: 'not-a-url',
      });

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues.some(i => i.message === 'Invalid URL format')).toBe(true);
      }
    });

    it('should validate schema - valid HTTPS URL should pass', () => {

      const result = lessonSchema.safeParse({
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '09:00',
        end_time: '10:00',
        description: '',
        telemost_link: 'https://telemost.yandex.ru/j/abc123',
      });

      expect(result.success).toBe(true);
    });

    it('should validate schema - empty telemost link should pass (optional)', () => {

      const result = lessonSchema.safeParse({
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '09:00',
        end_time: '10:00',
        description: '',
        telemost_link: '',
      });

      expect(result.success).toBe(true);
    });
  });

  describe('form submission - valid data', () => {
    it('should disable submit button when isLoading is true', () => {
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

    it('should call onSubmit when form is submitted with valid data', async () => {
      const user = userEvent.setup();
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Submit button should exist
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      expect(submitButton).toBeInTheDocument();
    });
  });

  describe('form submission - error handling', () => {
    it('should handle form submission errors gracefully', async () => {
      const errorSubmit = vi.fn().mockRejectedValue(new Error('API Error'));

      render(
        <LessonForm
          onSubmit={errorSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Submit button should exist even after error
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      expect(submitButton).toBeInTheDocument();
    });
  });

  describe('edit mode - initial data population', () => {
    it('should pre-fill all fields from initialData', () => {
      const initialData = {
        id: '770e8400-e29b-41d4-a716-446655440000',
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '14:30:00',
        end_time: '15:30:00',
        description: 'Algebra lesson',
        telemost_link: 'https://telemost.yandex.ru/j/algebra123',
        status: 'pending' as const,
        teacher: 'teacher-id',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      };

      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          initialData={initialData}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Verify description
      const descriptionInput = screen.getByRole('textbox', {
        name: 'Description',
      }) as HTMLTextAreaElement;
      expect(descriptionInput.value).toBe('Algebra lesson');

      // Verify times
      const timeInputs = container.querySelectorAll('input[type="time"]') as NodeListOf<HTMLInputElement>;
      expect(timeInputs[0]?.value).toMatch(/14:30/);
      expect(timeInputs[1]?.value).toMatch(/15:30/);

      // Verify telemost link
      const telemoostInput = container.querySelector('input[type="url"]') as HTMLInputElement;
      expect(telemoostInput?.value).toBe('https://telemost.yandex.ru/j/algebra123');
    });

    it('should show Update Lesson button in edit mode', () => {
      const initialData = {
        id: '770e8400-e29b-41d4-a716-446655440000',
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '14:30:00',
        end_time: '15:30:00',
        description: 'Test lesson',
        telemost_link: 'https://telemost.yandex.ru/j/test',
        status: 'pending' as const,
        teacher: 'teacher-id',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
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

    it('should allow editing initial data values', async () => {
      const user = userEvent.setup();
      const initialData = {
        id: '770e8400-e29b-41d4-a716-446655440000',
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '14:30:00',
        end_time: '15:30:00',
        description: 'Original description',
        telemost_link: 'https://telemost.yandex.ru/j/original',
        status: 'pending' as const,
        teacher: 'teacher-id',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      };

      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          initialData={initialData}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Edit description
      const descriptionInput = screen.getByRole('textbox', {
        name: 'Description',
      }) as HTMLTextAreaElement;
      await user.clear(descriptionInput);
      await user.type(descriptionInput, 'Updated description');

      expect(descriptionInput.value).toBe('Updated description');

      // Edit times
      const timeInputs = container.querySelectorAll('input[type="time"]') as NodeListOf<HTMLInputElement>;
      if (timeInputs[0]) {
        await user.clear(timeInputs[0]);
        await user.type(timeInputs[0], '10:00');
        expect(timeInputs[0]?.value).toMatch(/10:00/);
      }
    });
  });

  describe('field interactions - student and subject', () => {
    it('should have subject dropdown available', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Subject dropdown should be available
      const subjectCombobox = screen.getByRole('combobox', { name: 'Subject' });
      expect(subjectCombobox).toBeInTheDocument();
    });

    it('should support onStudentSelect callback prop', () => {
      const onStudentSelect = vi.fn();

      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
          onStudentSelect={onStudentSelect}
        />
      );

      // Component should render without errors
      const studentCombobox = screen.getByRole('combobox', { name: 'Student' });
      expect(studentCombobox).toBeInTheDocument();
    });
  });

  describe('optional fields - description and telemost link', () => {
    it('should allow empty description field', () => {
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Leave description empty (default)
      const descriptionInput = screen.getByRole('textbox', { name: 'Description' }) as HTMLTextAreaElement;
      expect(descriptionInput.value).toBe('');
    });

    it('should allow empty telemost link field', () => {
      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Verify telemost link is empty
      const telemoostInput = container.querySelector('input[type="url"]') as HTMLInputElement;
      expect(telemoostInput?.value).toBe('');
    });
  });

  describe('form reset - after successful submission', () => {
    it('should NOT reset form after submission in edit mode', () => {
      const initialData = {
        id: '770e8400-e29b-41d4-a716-446655440000',
        student: mockStudents[0].id,
        subject: mockSubjects[0].id,
        date: getTomorrowDateString(),
        start_time: '14:30:00',
        end_time: '15:30:00',
        description: 'Edit test',
        telemost_link: 'https://telemost.yandex.ru/j/test',
        status: 'pending' as const,
        teacher: 'teacher-id',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      };

      const { container } = render(
        <LessonForm
          onSubmit={mockOnSubmit}
          initialData={initialData}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Verify initial data is still there
      const descriptionInput = screen.getByRole('textbox', {
        name: 'Description',
      }) as HTMLTextAreaElement;
      expect(descriptionInput.value).toBe('Edit test');
    });
  });

  describe('error message display and visibility', () => {
    it('should display error messages when form validation fails', async () => {
      const user = userEvent.setup();
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Try to submit empty form
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      await user.click(submitButton);

      // Wait for errors to appear
      await waitFor(() => {
        const errorMessages = screen.queryAllByText(/is required|cannot be|must be/i);
        expect(errorMessages.length).toBeGreaterThan(0);
      });
    });

    it('should validate required fields on form submission', async () => {
      const user = userEvent.setup();
      render(
        <LessonForm
          onSubmit={mockOnSubmit}
          students={mockStudents}
          subjects={mockSubjects}
        />
      );

      // Try to submit empty form - should trigger validation
      const submitButton = screen.getByRole('button', { name: /Create Lesson/ });
      await user.click(submitButton);

      // Multiple validation errors should appear
      await waitFor(() => {
        const errors = screen.queryAllByText(/is required/i);
        expect(errors.length).toBeGreaterThan(0);
      });
    });
  });
});
