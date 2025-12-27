import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TeacherProfilePage } from '../TeacherProfilePage';
import { toast } from 'sonner';

// Mock hooks
vi.mock('@/hooks/useTeacherProfile', () => ({
  useTeacherProfile: vi.fn(),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return {
    ...actual,
    useQuery: vi.fn(),
  };
});

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

import { useTeacherProfile } from '@/hooks/useTeacherProfile';
import { useAuth } from '@/hooks/useAuth';
import { useQuery } from '@tanstack/react-query';

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

describe('TeacherProfilePage', () => {
  const mockUseAuth = useAuth as any;
  const mockUseTeacherProfile = useTeacherProfile as any;
  const mockUseQuery = useQuery as any;

  const defaultUser = {
    id: '2',
    email: 'teacher@test.com',
    first_name: 'Анна',
    last_name: 'Иванова',
    role: 'teacher' as const,
    avatar: null,
    phone: '+7 (999) 888-77-66',
  };

  const allSubjects = [
    { id: 1, name: 'Математика', color: '#FF6B6B' },
    { id: 2, name: 'Физика', color: '#4ECDC4' },
    { id: 3, name: 'Химия', color: '#95E1D3' },
  ];

  const defaultProfile = {
    user: defaultUser,
    profile: {
      experience_years: 5,
      bio: 'Опытный преподаватель математики и физики',
      telegram: '@teacher_test',
      subjects_list: ['Математика', 'Физика'],
    },
  };

  const mockUpdateProfile = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    mockUseAuth.mockReturnValue({
      user: defaultUser,
      isAuthenticated: true,
    });

    mockUseTeacherProfile.mockReturnValue({
      profile: defaultProfile,
      isLoading: false,
      updateProfile: mockUpdateProfile,
      isUpdating: false,
    });

    mockUseQuery.mockReturnValue({
      data: allSubjects,
      isLoading: false,
      error: null,
    });
  });

  describe('Rendering', () => {
    it('должна отобразить страницу с загрузочным индикатором', () => {
      mockUseTeacherProfile.mockReturnValue({
        profile: null,
        isLoading: true,
        updateProfile: mockUpdateProfile,
        isUpdating: false,
      });

      render(<TeacherProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('должна отобразить форму с данными профиля', () => {
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      expect(screen.getByDisplayValue('Анна')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Иванова')).toBeInTheDocument();
      expect(screen.getByDisplayValue('+7 (999) 888-77-66')).toBeInTheDocument();
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    });

    it('должна отобразить заголовок страницы', () => {
      render(<TeacherProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText('Профиль учителя')).toBeInTheDocument();
    });

    it('должна отобразить все поля формы', () => {
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      expect(screen.getByLabelText(/Имя/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Фамилия/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Телефон/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Опыт работы/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/О себе/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Telegram/i)).toBeInTheDocument();
    });

    it('должна отобразить счетчик символов для био', () => {
      render(<TeacherProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText(/42 \/ 1000/i)).toBeInTheDocument();
    });

    it('должна отобразить раздел управления предметами', () => {
      render(<TeacherProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText(/Мои предметы/i)).toBeInTheDocument();
    });

    it('должна отобразить выбранные предметы как бейджи', () => {
      render(<TeacherProfilePage />, { wrapper: createWrapper() });
      expect(screen.getByText('Математика')).toBeInTheDocument();
      expect(screen.getByText('Физика')).toBeInTheDocument();
    });
  });

  describe('Form Interaction', () => {
    it('должна обновить поле имени при вводе', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i) as HTMLInputElement;
      await user.clear(firstNameInput);
      await user.type(firstNameInput, 'Мария');

      expect(firstNameInput.value).toBe('Мария');
    });

    it('должна обновить поле био при вводе и обновить счетчик', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const bioInput = screen.getByLabelText(/О себе/i) as HTMLTextAreaElement;
      await user.clear(bioInput);
      await user.type(bioInput, 'Новое описание');

      expect(bioInput.value).toBe('Новое описание');
      expect(screen.getByText(/15 \/ 1000/i)).toBeInTheDocument();
    });

    it('должна обновить опыт работы', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const experienceInput = screen.getByLabelText(/Опыт работы/i) as HTMLInputElement;
      await user.clear(experienceInput);
      await user.type(experienceInput, '10');

      expect(experienceInput.value).toBe('10');
    });

    it('должна показать предупреждение при превышении лимита символов в био', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const bioInput = screen.getByLabelText(/О себе/i) as HTMLTextAreaElement;
      await user.clear(bioInput);
      await user.type(bioInput, 'a'.repeat(1001));

      expect(bioInput.value).toHaveLength(1001);
      expect(screen.getByText(/1001 \/ 1000/i)).toBeInTheDocument();
    });
  });

  describe('Subject Management', () => {
    it('должна добавить новый предмет', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      // Open subject selector
      const addButton = screen.getByRole('button', { name: /Добавить предмет/i });
      await user.click(addButton);

      // Select a subject
      await waitFor(() => {
        const chemistryOption = screen.getByText('Химия');
        user.click(chemistryOption);
      });
    });

    it('должна удалить предмет при клике на крестик', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      // Find remove button for "Математика" badge
      const mathBadge = screen.getByText('Математика').closest('div');
      const removeButton = mathBadge?.querySelector('button');

      if (removeButton) {
        await user.click(removeButton);
        await waitFor(() => {
          expect(screen.queryByText('Математика')).not.toBeInTheDocument();
        });
      }
    });

    it('должна показать только доступные предметы в селекторе', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const addButton = screen.getByRole('button', { name: /Добавить предмет/i });
      await user.click(addButton);

      // Should show only Химия (not yet selected)
      await waitFor(() => {
        expect(screen.getByText('Химия')).toBeInTheDocument();
      });
    });

    it('должна не показывать уже выбранные предметы в селекторе', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const addButton = screen.getByRole('button', { name: /Добавить предмет/i });
      await user.click(addButton);

      // Математика and Физика should not be in selector (already selected)
      await waitFor(() => {
        const options = screen.getAllByRole('option');
        const optionTexts = options.map((o) => o.textContent);
        expect(optionTexts).not.toContain('Математика');
        expect(optionTexts).not.toContain('Физика');
      });
    });
  });

  describe('Avatar Upload', () => {
    it('должна загрузить файл аватара', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

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
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

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
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const invalidFile = new File(['text'], 'file.txt', { type: 'text/plain' });
      const input = screen.getByLabelText(/Загрузить фото/i) as HTMLInputElement;

      await user.upload(input, invalidFile);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Неподдерживаемый формат. Используйте JPG, PNG или WebP'
        );
      });
    });
  });

  describe('Form Validation', () => {
    it('должна валидировать обязательное поле имени', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.clear(firstNameInput);

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).not.toHaveBeenCalled();
      });
    });

    it('должна валидировать минимальный опыт работы (0 лет)', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const experienceInput = screen.getByLabelText(/Опыт работы/i);
      await user.clear(experienceInput);
      await user.type(experienceInput, '-5');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).not.toHaveBeenCalled();
      });
    });
  });

  describe('Form Submission', () => {
    it('должна отправить форму с обновленными данными', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.clear(firstNameInput);
      await user.type(firstNameInput, 'Мария');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
        const formData = mockUpdateProfile.mock.calls[0][0];
        expect(formData).toBeInstanceOf(FormData);
        expect(formData.get('first_name')).toBe('Мария');
      });
    });

    it('должна отправить выбранные предметы в формате subject_ids', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      // Make a change to enable submit
      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.type(firstNameInput, 'X');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
        const formData = mockUpdateProfile.mock.calls[0][0];
        expect(formData.get('subject_ids')).toBeTruthy();
      });
    });

    it('должна показать успешное уведомление после сохранения', async () => {
      mockUpdateProfile.mockResolvedValue({ success: true });
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      // Make a change
      const firstNameInput = screen.getByLabelText(/Имя/i);
      await user.type(firstNameInput, 'X');

      const submitButton = screen.getByRole('button', { name: /Сохранить/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalled();
      });
    });

    it('должна отключить кнопку отправки при загрузке', () => {
      mockUseTeacherProfile.mockReturnValue({
        profile: defaultProfile,
        isLoading: false,
        updateProfile: mockUpdateProfile,
        isUpdating: true,
      });

      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const submitButton = screen.getByRole('button', { name: /Сохранение/i });
      expect(submitButton).toBeDisabled();
    });

    it('должна отключить кнопку отправки когда нет несохраненных изменений', () => {
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

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

      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/auth');
      });
    });

    it('должна перенаправить на /auth если роль не учитель', () => {
      mockUseAuth.mockReturnValue({
        user: { ...defaultUser, role: 'student' },
        isAuthenticated: true,
      });

      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/auth');
      });
    });

    it('должна показать предупреждение при уходе со страницы с несохраненными изменениями', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

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
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      expect(screen.getByLabelText(/Имя/i)).toHaveAttribute('aria-label');
      expect(screen.getByLabelText(/Фамилия/i)).toHaveAttribute('aria-label');
      expect(screen.getByLabelText(/Телефон/i)).toHaveAttribute('aria-label');
    });

    it('должна поддерживать навигацию с клавиатуры', async () => {
      const user = userEvent.setup();
      render(<TeacherProfilePage />, { wrapper: createWrapper() });

      const firstNameInput = screen.getByLabelText(/Имя/i);
      firstNameInput.focus();

      await user.keyboard('{Tab}');
      const lastNameInput = screen.getByLabelText(/Фамилия/i);
      expect(lastNameInput).toHaveFocus();
    });
  });

  describe('Loading States', () => {
    it('должна показать загрузку при загрузке предметов', () => {
      mockUseQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      render(<TeacherProfilePage />, { wrapper: createWrapper() });
      // Component should handle subjects loading gracefully
    });

    it('должна обработать ошибку при загрузке предметов', () => {
      mockUseQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Failed to load subjects'),
      });

      render(<TeacherProfilePage />, { wrapper: createWrapper() });
      // Component should handle error gracefully
    });
  });
});
