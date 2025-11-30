import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TeacherProfileForm } from '../TeacherProfileForm';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('TeacherProfileForm', () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должна отобразить форму', () => {
    render(<TeacherProfileForm initialData={{}} onSubmit={mockOnSubmit} />);
    expect(screen.getByText('Профиль учителя')).toBeInTheDocument();
  });

  it('должна отобразить все поля', () => {
    render(<TeacherProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText('Имя учителя')).toBeInTheDocument();
    expect(screen.getByLabelText('Биография учителя')).toBeInTheDocument();
    expect(screen.getByLabelText('Опыт работы учителя')).toBeInTheDocument();
  });

  it('должна валидировать опыт (максимум 80)', async () => {
    const user = userEvent.setup();
    render(<TeacherProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    await user.type(screen.getByLabelText('Имя учителя'), 'Мария');
    await user.type(screen.getByLabelText('Фамилия учителя'), 'Сидорова');
    await user.type(screen.getByLabelText('Опыт работы учителя'), '81');

    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(screen.getByText('Опыт не может превышать 80 лет')).toBeInTheDocument();
    });
  });

  it('должна успешно отправить форму', async () => {
    mockOnSubmit.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<TeacherProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    await user.type(screen.getByLabelText('Имя учителя'), 'Мария');
    await user.type(screen.getByLabelText('Фамилия учителя'), 'Сидорова');

    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
    });
  });

  it('должна иметь правильные aria-label', () => {
    render(<TeacherProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText('Имя учителя')).toBeInTheDocument();
    expect(screen.getByLabelText('Биография учителя')).toBeInTheDocument();
  });
});
