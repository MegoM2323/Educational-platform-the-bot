import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TutorProfileForm } from '../TutorProfileForm';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('TutorProfileForm', () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должна отобразить форму', () => {
    render(<TutorProfileForm initialData={{}} onSubmit={mockOnSubmit} />);
    expect(screen.getByText('Профиль репетитора')).toBeInTheDocument();
  });

  it('должна отобразить все поля', () => {
    render(<TutorProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText('Имя репетитора')).toBeInTheDocument();
    expect(screen.getByLabelText('Биография репетитора')).toBeInTheDocument();
  });

  it('должна валидировать опыт (0-80)', async () => {
    const user = userEvent.setup();
    render(<TutorProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    await user.type(screen.getByLabelText('Имя репетитора'), 'Александр');
    await user.type(screen.getByLabelText('Фамилия репетитора'), 'Иванов');
    await user.type(screen.getByLabelText('Опыт работы репетитора'), '100');

    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(screen.getByText('Опыт не может превышать 80 лет')).toBeInTheDocument();
    });
  });

  it('должна успешно отправить форму', async () => {
    mockOnSubmit.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<TutorProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    await user.type(screen.getByLabelText('Имя репетитора'), 'Александр');
    await user.type(screen.getByLabelText('Фамилия репетитора'), 'Иванов');

    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
    });
  });

  it('должна иметь правильные aria-label', () => {
    render(<TutorProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText('Имя репетитора')).toBeInTheDocument();
    expect(screen.getByLabelText('Telegram репетитора')).toBeInTheDocument();
  });
});
