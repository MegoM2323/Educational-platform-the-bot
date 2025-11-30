import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StudentProfileForm } from '../StudentProfileForm';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('StudentProfileForm', () => {
  const mockOnSubmit = vi.fn();

  const defaultInitialData = {
    first_name: 'Иван',
    last_name: 'Петров',
    phone: '+7 (999) 123-45-67',
    grade: 10,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должна отобразить форму', () => {
    render(<StudentProfileForm initialData={{}} onSubmit={mockOnSubmit} />);
    expect(screen.getByText('Профиль студента')).toBeInTheDocument();
  });

  it('должна отобразить все поля', () => {
    render(<StudentProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText('Имя студента')).toBeInTheDocument();
    expect(screen.getByLabelText('Фамилия студента')).toBeInTheDocument();
    expect(screen.getByLabelText('Класс студента')).toBeInTheDocument();
  });

  it('должна заполнить поля из initialData', () => {
    render(
      <StudentProfileForm
        initialData={defaultInitialData}
        onSubmit={mockOnSubmit}
      />
    );

    expect((screen.getByLabelText('Имя студента') as HTMLInputElement).value).toBe('Иван');
    expect((screen.getByLabelText('Фамилия студента') as HTMLInputElement).value).toBe('Петров');
  });

  it('должна не отправить форму с пустым именем', async () => {
    const user = userEvent.setup();
    render(
      <StudentProfileForm
        initialData={defaultInitialData}
        onSubmit={mockOnSubmit}
      />
    );

    const firstNameInput = screen.getByLabelText('Имя студента');
    await user.clear(firstNameInput);
    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(screen.getByText('Имя обязательно')).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('должна валидировать класс (минимум 1)', async () => {
    const user = userEvent.setup();
    render(<StudentProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    await user.type(screen.getByLabelText('Имя студента'), 'Иван');
    await user.type(screen.getByLabelText('Фамилия студента'), 'Петров');
    await user.type(screen.getByLabelText('Класс студента'), '0');

    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(screen.getByText('Класс должен быть от 1')).toBeInTheDocument();
    });
  });

  it('должна валидировать класс (максимум 12)', async () => {
    const user = userEvent.setup();
    render(<StudentProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    await user.type(screen.getByLabelText('Имя студента'), 'Иван');
    await user.type(screen.getByLabelText('Фамилия студента'), 'Петров');
    await user.type(screen.getByLabelText('Класс студента'), '13');

    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(screen.getByText('Класс не должен превышать 12')).toBeInTheDocument();
    });
  });

  it('должна успешно отправить форму', async () => {
    mockOnSubmit.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(
      <StudentProfileForm
        initialData={defaultInitialData}
        onSubmit={mockOnSubmit}
      />
    );

    await user.click(screen.getByRole('button', { name: /Сохранить/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
    });
  });

  it('должна отключить форму при loading=true', () => {
    render(
      <StudentProfileForm
        initialData={defaultInitialData}
        onSubmit={mockOnSubmit}
        isLoading={true}
      />
    );

    expect((screen.getByLabelText('Имя студента') as HTMLInputElement).disabled).toBe(true);
  });

  it('должна иметь правильные aria-label', () => {
    render(<StudentProfileForm initialData={{}} onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText('Имя студента')).toBeInTheDocument();
    expect(screen.getByLabelText('Фамилия студента')).toBeInTheDocument();
  });
});
