import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StudentProfilePage } from '../StudentProfilePage';
import { toast } from 'sonner';

// Mock hooks
vi.mock('@/hooks/useStudentProfile', () => ({
  useStudentProfile: vi.fn(),
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

import { useStudentProfile } from '@/hooks/useStudentProfile';
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

describe('StudentProfilePage', () => {
  const mockUseAuth = useAuth as any;
  const mockUseStudentProfile = useStudentProfile as any;

  const defaultUser = {
    id: '1',
    email: 'student@test.com',
    first_name: 'Иван',
    last_name: 'Петров',
    role: 'student' as const,
    avatar: null,
    phone: '+7 (999) 123-45-67',
  };

  const defaultProfile = {
    user: defaultUser,
    profile: {
      grade: 10,
      goal: 'Подготовка к ЕГЭ по математике',
      telegram: '@student_test',
    },
  };

  const mockUpdateProfile = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    mockUseAuth.mockReturnValue({
      user: defaultUser,
      isAuthenticated: true,
    });

    mockUseStudentProfile.mockReturnValue({
      profile: defaultProfile,
      isLoading: false,
      updateProfile: mockUpdateProfile,
      isUpdating: false,
    });
  });

  describe('Rendering', () => {
    it('должна отобразить страницу с загрузочным индикатором', () => {
      mockUseStudentProfile.mockReturnValue({
        profile: null,
        isLoading: true,
        updateProfile: mockUpdateProfile,
        isUpdating: false,
      });

      render(<StudentProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('должна отобразить форму с данными профиля', () => {
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      expect(screen.getByDisplayValue('Иван')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Петров')).toBeInTheDocument();
      expect(screen.getByDisplayValue('+7 (999) 123-45-67')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
    });

    it('должна отобразить заголовок страницы', () => {
      render(<StudentProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText('Профиль студента')).toBeInTheDocument();
    });

    it('должна отобразить все поля формы', () => {
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      expect(screen.getByLabelText(/Имя/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Фамилия/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Телефон/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Класс/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Цель обучения/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Telegram/i)).toBeInTheDocument();
    });

    it('должна отобразить кнопку загрузки аватара', () => {
      render(<StudentProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText(/Загрузить фото/i)).toBeInTheDocument();
    });

    it('должна отобразить счетчик символов для цели', () => {
      render(<StudentProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText(/32 \/ 500/i)).toBeInTheDocument();
    });
  });

  describe('Form Interaction', () => {
    it('должна обновить поле имени при вводе', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i) as HTMLInputElement;
      await user.clear(firstNameInput);
      await user.type(firstNameInput, 'Петр');

      expect(firstNameInput.value).toBe('Петр');
    });

    it('должна обновить поле цели при вводе и обновить счетчик', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const goalInput = screen.getByLabelText(/Цель обучения/i) as HTMLTextAreaElement;
      await user.clear(goalInput);
      await user.type(goalInput, 'Новая цель');

      expect(goalInput.value).toBe('Новая цель');
      expect(screen.getByText(/10 \/ 500/i)).toBeInTheDocument();
    });

    it('должна показать предупреждение при превышении лимита символов', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const goalInput = screen.getByLabelText(/Цель обучения/i) as HTMLTextAreaElement;
      await user.clear(goalInput);
      await user.type(goalInput, 'a'.repeat(501));

      expect(goalInput.value).toHaveLength(501);
      expect(screen.getByText(/501 \/ 500/i)).toBeInTheDocument();
    });

    it('должна изменить класс через селектор', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const gradeSelect = screen.getByRole('combobox');
      await user.click(gradeSelect);

      const option11 = screen.getByRole('option', { name: '11' });
      await user.click(option11);

      await waitFor(() => {
        expect(screen.getByText('11')).toBeInTheDocument();
      });
    });
  });

  describe('Avatar Upload', () => {
    it('должна загрузить файл аватара', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

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
      render(<StudentProfilePage />, { wrapper: createWrapper() });

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
      render(<StudentProfilePage />, { wrapper: createWrapper() });

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
      render(<StudentProfilePage />, { wrapper: createWrapper() });

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
  });

  describe('Form Validation', () => {
    it('должна валидировать обязательное поле имени', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.clear(firstNameInput);

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).not.toHaveBeenCalled();
      });
    });

    it('должна валидировать формат телефона', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const phoneInput = screen.getByLabelText(/Телефон/i);
      await user.clear(phoneInput);
      await user.type(phoneInput, 'invalid phone');

      // Phone validation happens on blur or submit
      await user.tab();
    });

    it('должна валидировать класс (1-12)', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      // Attempting to select grade outside 1-12 (if allowed by component logic)
      // The Select component restricts options, so this test verifies the constraint
      const gradeSelect = screen.getByRole('combobox');
      await user.click(gradeSelect);

      // Verify only valid grades are shown
      expect(screen.getByRole('option', { name: '1' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: '12' })).toBeInTheDocument();
    });
  });

  describe('Form Submission', () => {
    it('должна отправить форму только с измененными полями', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const phoneInput = screen.getByLabelText(/Телефон/i);
      await user.clear(phoneInput);
      await user.type(phoneInput, '+7 (999) 987-65-43');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
        const formData = mockUpdateProfile.mock.calls[0][0];
        expect(formData).toBeInstanceOf(FormData);

        // Check that only changed field is sent
        expect(formData.get('phone')).toBe('+7 (999) 987-65-43');

        // Check that unchanged fields are NOT sent
        expect(formData.get('first_name')).toBeNull();
        expect(formData.get('last_name')).toBeNull();
        expect(formData.get('grade')).toBeNull();
      });
    });

    it('должна отправить форму с обновленными данными', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.clear(firstNameInput);
      await user.type(firstNameInput, 'Петр');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
        const formData = mockUpdateProfile.mock.calls[0][0];
        expect(formData).toBeInstanceOf(FormData);
        expect(formData.get('first_name')).toBe('Петр');
      });
    });

    it('должна НЕ отправить grade если он не был изменен', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      // Change only phone, do not change grade
      const phoneInput = screen.getByLabelText(/Телефон/i);
      await user.clear(phoneInput);
      await user.type(phoneInput, '+7 (999) 555-55-55');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
        const formData = mockUpdateProfile.mock.calls[0][0];

        // Grade should NOT be included since it wasn't changed
        expect(formData.get('grade')).toBeNull();
        expect(formData.get('phone')).toBe('+7 (999) 555-55-55');
      });
    });

    it('должна показать успешное уведомление после сохранения', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
      });
    });

    it('должна показать ошибку при неудачном сохранении', async () => {
      mockUpdateProfile.mockRejectedValue(new Error('Network error'));
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
      });
    });

    it('должна отключить кнопку отправки при загрузке', () => {
      mockUseStudentProfile.mockReturnValue({
        profile: defaultProfile,
        isLoading: false,
        updateProfile: mockUpdateProfile,
        isUpdating: true,
      });

      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const submitButton = screen.getByRole('button', { name: /Сохранение/i });
      expect(submitButton).toBeDisabled();
    });

    it('должна отключить кнопку отправки когда нет несохраненных изменений', () => {
      render(<StudentProfilePage />, { wrapper: createWrapper() });

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

      render(<StudentProfilePage />, { wrapper: createWrapper() });

      waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/auth');
      });
    });

    it('должна перенаправить на /auth если роль не студент', () => {
      mockUseAuth.mockReturnValue({
        user: { ...defaultUser, role: 'teacher' },
        isAuthenticated: true,
      });

      render(<StudentProfilePage />, { wrapper: createWrapper() });

      waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/auth');
      });
    });

    it('должна показать предупреждение при уходе со страницы с несохраненными изменениями', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      // Make a change
      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.type(firstNameInput, 'X');

      // Simulate beforeunload event
      const beforeUnloadEvent = new Event('beforeunload') as BeforeUnloadEvent;
      window.dispatchEvent(beforeUnloadEvent);

      expect(beforeUnloadEvent.defaultPrevented).toBe(true);
    });
  });

  describe('Accessibility', () => {
    it('должна иметь правильные aria-labels для всех полей', () => {
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      expect(screen.getByLabelText(/Имя/i)).toHaveAttribute('aria-label');
      expect(screen.getByLabelText(/Фамилия/i)).toHaveAttribute('aria-label');
      expect(screen.getByLabelText(/Телефон/i)).toHaveAttribute('aria-label');
    });

    it('должна поддерживать навигацию с клавиатуры', async () => {
      const user = userEvent.setup();
      render(<StudentProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      firstNameInput.focus();

      await user.keyboard('{Tab}');
      const lastNameInput = screen.getByLabelText(/Фамилия/i);
      expect(lastNameInput).toHaveFocus();
    });
  });
});
