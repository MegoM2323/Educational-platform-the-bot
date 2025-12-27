import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AssignmentSubmitForm } from '../AssignmentSubmitForm';
import { Assignment } from '@/integrations/api/assignmentsAPI';

describe('AssignmentSubmitForm', () => {
  const mockAssignment: Assignment = {
    id: 1,
    title: 'Test Assignment',
    description: 'Test description',
    instructions: 'Test instructions',
    type: 'homework',
    status: 'published',
    max_score: 100,
    time_limit: 60,
    attempts_limit: 3,
    start_date: new Date().toISOString(),
    due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    tags: 'test',
    difficulty_level: 2,
    author: {
      id: 1,
      email: 'teacher@example.com',
      full_name: 'Test Teacher',
    },
    assigned_to: [1],
    is_overdue: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
    localStorage.clear();
  });

  it('renders the form with all required elements', () => {
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByText('Отправить ответы')).toBeInTheDocument();
    expect(screen.getByText('Ответы и комментарии')).toBeInTheDocument();
    expect(screen.getByText('Загрузить файлы')).toBeInTheDocument();
  });

  it('shows time limit warning', () => {
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByText('Ограничение по времени')).toBeInTheDocument();
    expect(screen.getByText(/На выполнение задания отведено 60 минут/)).toBeInTheDocument();
  });

  it('shows attempts limit info', () => {
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByText('Ограничение попыток')).toBeInTheDocument();
    expect(screen.getByText(/Доступно 3 попыток отправки/)).toBeInTheDocument();
  });

  it('disables submit button when form is empty', () => {
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const submitButton = screen.getByRole('button', { name: /Отправить ответы/i });
    expect(submitButton).toBeDisabled();
  });

  it('enables submit button when notes are entered', async () => {
    const user = userEvent.setup();
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const textarea = screen.getByPlaceholderText('Введите ваши ответы...');
    await user.type(textarea, 'My answer');

    const submitButton = screen.getByRole('button', { name: /Отправить ответы/i });
    expect(submitButton).toBeEnabled();
  });

  it('shows character count for notes', async () => {
    const user = userEvent.setup();
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const textarea = screen.getByPlaceholderText('Введите ваши ответы...');
    await user.type(textarea, 'Test');

    expect(screen.getByText('4 / 5000')).toBeInTheDocument();
  });

  it('validates file types', async () => {
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const fileInput = screen.getByDisplayValue('') as HTMLInputElement;
    expect(fileInput.accept).toContain('.pdf');
    expect(fileInput.accept).toContain('.doc');
  });

  it('validates file size', async () => {
    const user = userEvent.setup();
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const file = new File(['x'.repeat(60 * 1024 * 1024)], 'large.pdf', {
      type: 'application/pdf',
    });

    const fileInput = screen.getByLabelText('нажмите для выбора').parentElement?.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/слишком большой/)).toBeInTheDocument();
    });
  });

  it('allows multiple file uploads', async () => {
    const user = userEvent.setup();
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const file1 = new File(['content1'], 'file1.pdf', { type: 'application/pdf' });
    const file2 = new File(['content2'], 'file2.doc', { type: 'application/msword' });

    const fileInput = screen.getByLabelText('нажмите для выбора').parentElement?.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file1, file2] } });

    await waitFor(() => {
      expect(screen.getByText('file1.pdf')).toBeInTheDocument();
      expect(screen.getByText('file2.doc')).toBeInTheDocument();
    });
  });

  it('shows draft saved indicator', async () => {
    const user = userEvent.setup();
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const textarea = screen.getByPlaceholderText('Введите ваши ответы...');
    await user.type(textarea, 'Test answer');

    // Wait for draft save
    await waitFor(
      () => {
        expect(screen.getByText('Черновик сохранен')).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it('loads draft from localStorage', () => {
    const draftData = {
      timestamp: new Date().toISOString(),
      answers: { question1: 'answer1' },
      notes: 'Saved draft text',
    };

    localStorage.setItem(
      `assignment-draft-${mockAssignment.id}`,
      JSON.stringify(draftData)
    );

    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const textarea = screen.getByPlaceholderText('Введите ваши ответы...');
    expect(textarea).toHaveValue('Saved draft text');
  });

  it('shows confirmation dialog with question count', async () => {
    const user = userEvent.setup();
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        questionCount={5}
        onSubmit={mockOnSubmit}
        showConfirmation={true}
      />
    );

    const textarea = screen.getByPlaceholderText('Введите ваши ответы...');
    await user.type(textarea, 'My answer');

    const submitButton = screen.getByRole('button', { name: /Отправить ответы/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Подтверждение отправки')).toBeInTheDocument();
      expect(screen.getByText(/Вы заполнили/)).toBeInTheDocument();
    });
  });

  it('submits form on confirmation', async () => {
    const user = userEvent.setup();
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
        showConfirmation={true}
      />
    );

    const textarea = screen.getByPlaceholderText('Введите ваши ответы...');
    await user.type(textarea, 'My answer');

    const submitButton = screen.getByRole('button', { name: /Отправить ответы/i });
    await user.click(submitButton);

    const confirmButton = await screen.findByRole('button', { name: /Подтвердить отправку/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
    });
  });

  it('shows progress indicator with question count', () => {
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        questionCount={10}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByText(/Прогресс ответов/)).toBeInTheDocument();
    expect(screen.getByText(/0 из 10/)).toBeInTheDocument();
  });

  it('displays loading state during submission', () => {
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
        isLoading={true}
      />
    );

    const submitButton = screen.getByRole('button');
    expect(submitButton).toBeDisabled();
    expect(screen.getByText('Отправка...')).toBeInTheDocument();
  });

  it('handles file removal', async () => {
    const user = userEvent.setup();
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const fileInput = screen.getByLabelText('нажмите для выбора').parentElement?.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
    });

    const removeButton = screen.getByRole('button', { name: '' });
    await user.click(removeButton);

    await waitFor(() => {
      expect(screen.queryByText('test.pdf')).not.toBeInTheDocument();
    });
  });

  it('shows drag and drop area', () => {
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByText('Перетащите файлы сюда')).toBeInTheDocument();
  });

  it('handles drag and drop files', async () => {
    render(
      <AssignmentSubmitForm
        assignment={mockAssignment}
        onSubmit={mockOnSubmit}
      />
    );

    const dropZone = screen.getByText('Перетащите файлы сюда').parentElement?.parentElement;
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    if (dropZone) {
      fireEvent.dragEnter(dropZone);
      expect(dropZone).toHaveClass('border-primary');

      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] },
      });

      await waitFor(() => {
        expect(screen.getByText('test.pdf')).toBeInTheDocument();
      });
    }
  });
});
