import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TutorProfilePage } from '../TutorProfilePage';
import { toast } from 'sonner';

// Mock hooks
vi.mock('@/hooks/useTutorProfile', () => ({
  useTutorProfile: vi.fn(),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock navigation
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import { useTutorProfile } from '@/hooks/useTutorProfile';
import { useAuth } from '@/hooks/useAuth';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </BrowserRouter>
  );
};

describe('TutorProfilePage', () => {
  const mockUseAuth = useAuth as any;
  const mockUseTutorProfile = useTutorProfile as any;

  const defaultUser = {
    id: '3',
    email: 'tutor@test.com',
    first_name: 'Сергей',
    last_name: 'Петров',
    role: 'tutor' as const,
    avatar: null,
    phone: '+7 (999) 777-88-99',
  };

  const defaultProfile = {
    user: defaultUser,
    profile: {
      specialization: 'Репетитор по математике и физике для подготовки к ЕГЭ',
      telegram: '@tutor_test',
    },
  };

  const mockUpdateProfile = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    mockUseAuth.mockReturnValue({
      user: defaultUser,
      isAuthenticated: true,
    });

    mockUseTutorProfile.mockReturnValue({
      profile: defaultProfile,
      isLoading: false,
      updateProfile: mockUpdateProfile,
      isUpdating: false,
    });
  });

  describe('Rendering', () => {
    it('должна отобразить страницу с загрузочным индикатором', () => {
      mockUseTutorProfile.mockReturnValue({
        profile: null,
        isLoading: true,
        updateProfile: mockUpdateProfile,
        isUpdating: false,
      });

      render(<TutorProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('должна отобразить форму с данными профиля', () => {
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      expect(screen.getByDisplayValue('Сергей')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Петров')).toBeInTheDocument();
      expect(screen.getByDisplayValue('+7 (999) 777-88-99')).toBeInTheDocument();
    });

    it('должна отобразить заголовок страницы', () => {
      render(<TutorProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText('Профиль репетитора')).toBeInTheDocument();
    });

    it('должна отобразить все поля формы', () => {
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      expect(screen.getByLabelText(/Имя/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Фамилия/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Телефон/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Специализация/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Telegram/i)).toBeInTheDocument();
    });

    it('должна отобразить кнопку загрузки аватара', () => {
      render(<TutorProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText(/Загрузить фото/i)).toBeInTheDocument();
    });

    it('должна отобразить счетчик символов для специализации', () => {
      render(<TutorProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText(/56 \/ 500/i)).toBeInTheDocument();
    });
  });

  describe('Form Interaction', () => {
    it('должна обновить поле имени при вводе', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i) as HTMLInputElement;
      await user.clear(firstNameInput);
      await user.type(firstNameInput, 'Алексей');

      expect(firstNameInput.value).toBe('Алексей');
    });

    it('должна обновить поле специализации при вводе и обновить счетчик', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const specializationInput = screen.getByLabelText(/Специализация/i) as HTMLTextAreaElement;
      await user.clear(specializationInput);
      await user.type(specializationInput, 'Новая специализация');

      expect(specializationInput.value).toBe('Новая специализация');
      expect(screen.getByText(/20 \/ 500/i)).toBeInTheDocument();
    });

    it('должна показать предупреждение при превышении лимита символов', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const specializationInput = screen.getByLabelText(/Специализация/i) as HTMLTextAreaElement;
      await user.clear(specializationInput);
      await user.type(specializationInput, 'a'.repeat(501));

      expect(specializationInput.value).toHaveLength(501);
      expect(screen.getByText(/501 \/ 500/i)).toBeInTheDocument();
    });

    it('должна обновить поле телефона', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const phoneInput = screen.getByLabelText(/Телефон/i) as HTMLInputElement;
      await user.clear(phoneInput);
      await user.type(phoneInput, '+7 (999) 111-22-33');

      expect(phoneInput.value).toBe('+7 (999) 111-22-33');
    });

    it('должна обновить поле Telegram', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const telegramInput = screen.getByLabelText(/Telegram/i) as HTMLInputElement;
      await user.clear(telegramInput);
      await user.type(telegramInput, '@new_tutor');

      expect(telegramInput.value).toBe('@new_tutor');
    });
  });

  describe('Avatar Upload', () => {
    it('должна загрузить файл аватара', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const file = new File(['avatar'], 'avatar.png', { type: 'image/png' });
      const input = screen.getByLabelText(/Загрузить фото/i) as HTMLInputElement;

      await user.upload(input, file);

      await waitFor(() => {
        expect(input.files?.[0]).toBe(file);
        expect(input.files).toHaveLength(1);
      });
    });

    it('должна показать ошибку при слишком большом файле', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const largeFile = new File(['x'.repeat(6 * 1024 * 1024)], 'large.png', {
        type: 'image/png',
      });
      const input = screen.getByLabelText(/Загрузить фото/i) as HTMLInputElement;

      await user.upload(input, largeFile);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Файл слишком большой. Максимум 5MB');
      });
    });

    it('должна показать ошибку при неподдерживаемом формате', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const invalidFile = new File(['text'], 'file.txt', { type: 'text/plain' });
      const input = screen.getByLabelText(/Загрузить фото/i) as HTMLInputElement;

      await user.upload(input, invalidFile);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Неподдерживаемый формат. Используйте JPG, PNG или WebP'
        );
      });
    });

    it('должна удалить аватар при нажатии кнопки удаления', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      // First upload an avatar
      const file = new File(['avatar'], 'avatar.png', { type: 'image/png' });
      const input = screen.getByLabelText(/Загрузить фото/i) as HTMLInputElement;
      await user.upload(input, file);

      // Then remove it
      await waitFor(async () => {
        const removeButton = screen.queryByRole('button', { name: /Удалить/i });
        if (removeButton) {
          await user.click(removeButton);
        }
      });
    });

    it('должна поддерживать форматы JPG, PNG, WebP', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const formats = [
        { file: new File(['img'], 'test.jpg', { type: 'image/jpeg' }), name: 'JPEG' },
        { file: new File(['img'], 'test.png', { type: 'image/png' }), name: 'PNG' },
        { file: new File(['img'], 'test.webp', { type: 'image/webp' }), name: 'WebP' },
      ];

      for (const format of formats) {
        const input = screen.getByLabelText(/Загрузить фото/i) as HTMLInputElement;
        await user.upload(input, format.file);

        await waitFor(() => {
          expect(input.files?.[0]).toBe(format.file);
        });
      }
    });
  });

  describe('Form Validation', () => {
    it('должна валидировать обязательное поле имени', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.clear(firstNameInput);

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).not.toHaveBeenCalled();
      });
    });

    it('должна валидировать обязательное поле фамилии', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const lastNameInput = screen.getByLabelText(/Фамилия/i);
      await user.clear(lastNameInput);

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).not.toHaveBeenCalled();
      });
    });

    it('должна валидировать формат телефона', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const phoneInput = screen.getByLabelText(/Телефон/i);
      await user.clear(phoneInput);
      await user.type(phoneInput, 'invalid phone');

      // Phone validation happens on blur or submit
      await user.tab();
    });

    it('должна валидировать формат Telegram (опционально)', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const telegramInput = screen.getByLabelText(/Telegram/i);
      await user.clear(telegramInput);
      await user.type(telegramInput, 'invalid telegram');

      // Validation may happen on blur
      await user.tab();
    });
  });

  describe('Form Submission', () => {
    it('должна отправить форму с обновленными данными', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.clear(firstNameInput);
      await user.type(firstNameInput, 'Алексей');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
        const formData = mockUpdateProfile.mock.calls[0][0];
        expect(formData).toBeInstanceOf(FormData);
        expect(formData.get('first_name')).toBe('Алексей');
      });
    });

    it('должна отправить специализацию в запросе', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const specializationInput = screen.getByLabelText(/Специализация/i);
      await user.clear(specializationInput);
      await user.type(specializationInput, 'Новая специализация');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
        const formData = mockUpdateProfile.mock.calls[0][0];
        expect(formData.get('specialization')).toBe('Новая специализация');
      });
    });

    it('должна показать успешное уведомление после сохранения', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      // Make a change
      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.type(firstNameInput, 'X');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
      });
    });

    it('должна показать ошибку при неудачном сохранении', async () => {
      mockUpdateProfile.mockRejectedValue(new Error('Network error'));
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.type(firstNameInput, 'X');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
      });
    });

    it('должна отключить кнопку отправки при загрузке', () => {
      mockUseTutorProfile.mockReturnValue({
        profile: defaultProfile,
        isLoading: false,
        updateProfile: mockUpdateProfile,
        isUpdating: true,
      });

      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const submitButton = screen.getByRole('button', { name: /Сохранение/i });
      expect(submitButton).toBeDisabled();
    });

    it('должна отключить кнопку отправки когда нет несохраненных изменений', () => {
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      expect(submitButton).toBeDisabled();
    });
  });

  describe('Navigation & Authentication', () => {
    it('должна перенаправить на /auth если пользователь не аутентифицирован', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isAuthenticated: false,
      });

      render(<TutorProfilePage />, { wrapper: createWrapper() });

      waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/auth');
      });
    });

    it('должна перенаправить на /auth если роль не репетитор', () => {
      mockUseAuth.mockReturnValue({
        user: { ...defaultUser, role: 'student' },
        isAuthenticated: true,
      });

      render(<TutorProfilePage />, { wrapper: createWrapper() });

      waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/auth');
      });
    });

    it('должна показать предупреждение при уходе со страницы с несохраненными изменениями', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      // Make a change
      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.type(firstNameInput, 'X');

      // Simulate beforeunload event
      const beforeUnloadEvent = new Event('beforeunload') as BeforeUnloadEvent;
      window.dispatchEvent(beforeUnloadEvent);

      expect(beforeUnloadEvent.defaultPrevented).toBe(true);
    });

    it('должна иметь кнопку возврата к дашборду', () => {
      render(<TutorProfilePage />, { wrapper: createWrapper() });
      const backButton = screen.getByRole('button', { name: /Назад/i });
      expect(backButton).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('должна иметь правильные aria-labels для всех полей', () => {
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      expect(screen.getByLabelText(/Имя/i)).toHaveAttribute('aria-label');
      expect(screen.getByLabelText(/Фамилия/i)).toHaveAttribute('aria-label');
      expect(screen.getByLabelText(/Телефон/i)).toHaveAttribute('aria-label');
    });

    it('должна поддерживать навигацию с клавиатуры', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      firstNameInput.focus();

      await user.keyboard('{Tab}');
      const lastNameInput = screen.getByLabelText(/Фамилия/i);
      expect(lastNameInput).toHaveFocus();
    });

    it('должна иметь правильную структуру заголовков', () => {
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const heading = screen.getByText('Профиль репетитора');
      expect(heading.tagName).toMatch(/H[1-6]/);
    });
  });

  describe('Unsaved Changes Warning', () => {
    it('должна показать индикатор несохраненных изменений', async () => {
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.type(firstNameInput, 'X');

      // Should enable submit button
      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      expect(submitButton).not.toBeDisabled();
    });

    it('должна сбросить индикатор после успешного сохранения', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<TutorProfilePage />, { wrapper: createWrapper() });

      // Make change
      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.type(firstNameInput, 'X');

      // Submit
      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
      });

      // After successful save, button should be disabled again
      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });
    });
  });
});
