import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ParentProfileForm } from '../ParentProfileForm';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('ParentProfileForm', () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должна отобразить форму', () => {
    render(<ParentProfileForm initialData={{}} onSubmit={mockOnSubmit} />);
    expect(screen.getByText('Профиль родителя')).toBeInTheDocument();
  });

  it('должна отобразить только базовые поля', () => {
    render(<ParentProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText('Имя родителя')).toBeInTheDocument();
    expect(screen.getByLabelText('Фамилия родителя')).toBeInTheDocument();
    expect(screen.getByLabelText('Номер телефона')).toBeInTheDocument();
  });

  it('должна не отправить форму с пустым именем', async () => {
    const user = userEvent.setup();
    render(
      <ParentProfileForm
        initialData={{ first_name: 'Анна', last_name: 'Смирнова' }}
        onSubmit={mockOnSubmit}
      />
    );

    await user.clear(screen.getByLabelText('Имя родителя'));
    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(screen.getByText('Имя обязательно')).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('должна успешно отправить форму', async () => {
    mockOnSubmit.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<ParentProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    await user.type(screen.getByLabelText('Имя родителя'), 'Анна');
    await user.type(screen.getByLabelText('Фамилия родителя'), 'Смирнова');

    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
    });
  });

  it('должна иметь правильные aria-label', () => {
    render(<ParentProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText('Имя родителя')).toBeInTheDocument();
    expect(screen.getByLabelText('Telegram родителя')).toBeInTheDocument();
  });
});
