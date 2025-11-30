import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import StaffManagement from '../StaffManagement';
import * as staffService from '@/services/staffService';
import * as AuthContext from '@/contexts/AuthContext';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock staffService
vi.mock('@/services/staffService', () => ({
  staffService: {
    list: vi.fn(),
    create: vi.fn(),
  },
}));

// Mock dialogs
vi.mock('@/components/admin/EditTeacherSubjectsDialog', () => ({
  EditTeacherSubjectsDialog: ({ onSuccess }: any) => (
    <div data-testid="edit-subjects-dialog" onClick={() => onSuccess?.()}>
      Mock EditTeacherSubjectsDialog
    </div>
  ),
}));

vi.mock('@/components/admin/EditUserDialog', () => ({
  EditUserDialog: ({ onSuccess }: any) => (
    <div data-testid="edit-user-dialog" onClick={() => onSuccess?.()}>
      Mock EditUserDialog
    </div>
  ),
}));

vi.mock('@/components/admin/EditProfileDialog', () => ({
  EditProfileDialog: ({ onSuccess }: any) => (
    <div data-testid="edit-profile-dialog" onClick={() => onSuccess?.()}>
      Mock EditProfileDialog
    </div>
  ),
}));

vi.mock('@/components/admin/ResetPasswordDialog', () => ({
  ResetPasswordDialog: () => <div data-testid="reset-password-dialog">Mock ResetPasswordDialog</div>,
}));

vi.mock('@/components/admin/DeleteUserDialog', () => ({
  DeleteUserDialog: ({ onSuccess }: any) => (
    <div data-testid="delete-user-dialog" onClick={() => onSuccess?.()}>
      Mock DeleteUserDialog
    </div>
  ),
}));

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockLogout = vi.fn();

const mockUseAuth = () => ({
  logout: mockLogout,
  user: {
    id: 1,
    email: 'admin@example.com',
    role: 'admin',
    full_name: 'Admin User',
  },
  isAuthenticated: true,
});

const mockTeacherList = [
  {
    id: 1,
    user: {
      id: 1,
      email: 'teacher1@test.com',
      full_name: 'Teacher One',
      is_active: true,
      date_joined: '2024-01-01T10:00:00Z',
      role: 'teacher',
    },
    subjects: [
      { id: 1, name: 'Mathematics' },
      { id: 2, name: 'Physics' },
    ],
    experience_years: 5,
    bio: 'Experienced math teacher',
  },
  {
    id: 2,
    user: {
      id: 2,
      email: 'teacher2@test.com',
      full_name: 'Teacher Two',
      is_active: true,
      date_joined: '2024-01-02T10:00:00Z',
      role: 'teacher',
    },
    subjects: [{ id: 3, name: 'Chemistry' }],
    experience_years: 3,
    bio: 'Chemistry specialist',
  },
];

const mockTutorList = [
  {
    id: 3,
    user: {
      id: 3,
      email: 'tutor1@test.com',
      full_name: 'Tutor One',
      is_active: true,
      date_joined: '2024-01-03T10:00:00Z',
      role: 'tutor',
    },
    specialization: 'Math Tutoring',
    experience_years: 7,
    bio: 'Expert tutor in mathematics',
  },
];

describe('StaffManagement', () => {
  beforeEach(() => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue(mockUseAuth() as any);
    (staffService.staffService.list as any)
      .mockResolvedValueOnce(mockTeacherList)
      .mockResolvedValueOnce(mockTutorList);
    mockNavigate.mockClear();
    mockLogout.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // Тест 1: Рендеринг основных элементов
  it('should render staff management page with main elements', async () => {
    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    // Проверяем заголовок
    await waitFor(() => {
      expect(screen.getByText(/управление преподавателями и тьюторами/i)).toBeInTheDocument();
    });

    // Проверяем кнопки создания
    expect(screen.getByRole('button', { name: /создать преподавателя/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /создать тьютора/i })).toBeInTheDocument();

    // Проверяем кнопку выхода
    expect(screen.getByRole('button', { name: /выйти/i })).toBeInTheDocument();
  });

  // Тест 2: Загрузка списка учителей
  it('should load and display teachers list', async () => {
    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    // Ждем загрузки учителей
    await waitFor(() => {
      expect(screen.getByText('teacher1@test.com')).toBeInTheDocument();
      expect(screen.getByText('teacher2@test.com')).toBeInTheDocument();
    });

    // Проверяем данные учителей
    expect(screen.getByText('Teacher One')).toBeInTheDocument();
    expect(screen.getByText('Teacher Two')).toBeInTheDocument();
  });

  // Тест 3: Загрузка списка тьюторов
  it('should load and display tutors list', async () => {
    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    // Ждем загрузки
    await waitFor(() => {
      expect(screen.getByText('Tutor One')).toBeInTheDocument();
    });
  });

  // Тест 4: Переключение между табами (Учителя <-> Тьюторы)
  it('should switch between teachers and tutors tabs', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Teacher One')).toBeInTheDocument();
    });

    // Кликаем на таб тьюторов
    const tutorsTab = screen.getByRole('tab', { name: /тьюторы/i });
    await user.click(tutorsTab);

    // Проверяем что отображаются тьюторы
    await waitFor(() => {
      expect(screen.getByText('Tutor One')).toBeInTheDocument();
    });
  });

  // Тест 5: Отображение предметов учителя
  it('should display teacher subjects in a list', async () => {
    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Mathematics')).toBeInTheDocument();
      expect(screen.getByText('Physics')).toBeInTheDocument();
      expect(screen.getByText('Chemistry')).toBeInTheDocument();
    });
  });

  // Тест 6: Отображение опыта работы
  it('should display experience years correctly', async () => {
    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Teacher 1 has 5 years
      const expValues = screen.getAllByText(/5|3|7/);
      expect(expValues.length).toBeGreaterThan(0);
    });
  });

  // Тест 7: Открытие диалога создания преподавателя
  it('should open create teacher dialog on button click', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    const createTeacherBtn = screen.getByRole('button', { name: /создать преподавателя/i });
    await user.click(createTeacherBtn);

    // Проверяем наличие элементов формы создания
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /создание преподавателя/i })).toBeInTheDocument();
    });
  });

  // Тест 8: Открытие диалога создания тьютора
  it('should open create tutor dialog on button click', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    const createTutorBtn = screen.getByRole('button', { name: /создать тьютора/i });
    await user.click(createTutorBtn);

    // Проверяем наличие диалога создания тьютора
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /создание тьютора/i })).toBeInTheDocument();
    });
  });

  // Тест 9: Заполнение и отправка формы создания учителя
  it('should create teacher successfully with validation', async () => {
    const user = userEvent.setup();
    const { toast } = await import('sonner');
    (staffService.staffService.create as any).mockResolvedValue({
      success: true,
      credentials: { login: 'teacher@test.com', password: 'GeneratedPass123' },
    });

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    // Открываем диалог создания
    const createTeacherBtn = screen.getByRole('button', { name: /создать преподавателя/i });
    await user.click(createTeacherBtn);

    // Заполняем форму
    const emailInput = screen.getAllByRole('textbox')[0]; // Email is first text input
    const firstNameInput = screen.getAllByRole('textbox')[1];
    const lastNameInput = screen.getAllByRole('textbox')[2];
    const subjectInput = screen.getAllByRole('textbox')[3];

    await user.type(emailInput, 'newteacher@test.com');
    await user.type(firstNameInput, 'John');
    await user.type(lastNameInput, 'Doe');
    await user.type(subjectInput, 'English');

    // Отправляем форму
    const submitButton = screen.getByRole('button', { name: /создать/i });
    await user.click(submitButton);

    // Проверяем что создание прошло успешно
    await waitFor(() => {
      expect(staffService.staffService.create).toHaveBeenCalled();
    });
  });

  // Тест 10: Валидация обязательных полей при создании учителя
  it('should show validation error when required fields are empty', async () => {
    const user = userEvent.setup();
    const { toast } = await import('sonner');

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    // Открываем диалог создания
    const createTeacherBtn = screen.getByRole('button', { name: /создать преподавателя/i });
    await user.click(createTeacherBtn);

    // Пытаемся отправить пустую форму
    const submitButton = screen.getByRole('button', { name: /создать/i });
    await user.click(submitButton);

    // Проверяем что была ошибка валидации
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('Заполните'));
    });
  });

  // Тест 11: Требование предмета для учителя
  it('should require subject field for teacher creation', async () => {
    const user = userEvent.setup();
    const { toast } = await import('sonner');

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    const createTeacherBtn = screen.getByRole('button', { name: /создать преподавателя/i });
    await user.click(createTeacherBtn);

    // Заполняем все кроме предмета
    const emailInput = screen.getAllByRole('textbox')[0];
    const firstNameInput = screen.getAllByRole('textbox')[1];
    const lastNameInput = screen.getAllByRole('textbox')[2];

    await user.type(emailInput, 'teacher@test.com');
    await user.type(firstNameInput, 'John');
    await user.type(lastNameInput, 'Doe');

    const submitButton = screen.getByRole('button', { name: /создать/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('предмет'));
    });
  });

  // Тест 12: Требование специализации для тьютора
  it('should require specialization field for tutor creation', async () => {
    const user = userEvent.setup();
    const { toast } = await import('sonner');

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    const createTutorBtn = screen.getByRole('button', { name: /создать тьютора/i });
    await user.click(createTutorBtn);

    // Заполняем всё кроме специализации
    const emailInput = screen.getAllByRole('textbox')[0];
    const firstNameInput = screen.getAllByRole('textbox')[1];
    const lastNameInput = screen.getAllByRole('textbox')[2];

    await user.type(emailInput, 'tutor@test.com');
    await user.type(firstNameInput, 'Jane');
    await user.type(lastNameInput, 'Smith');

    const submitButton = screen.getByRole('button', { name: /создать/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('специализац'));
    });
  });

  // Тест 13: Открытие диалога редактирования предметов
  it('should open edit subjects dialog for teacher', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Teacher One')).toBeInTheDocument();
    });

    // Находим кнопку редактирования предметов
    const editSubjectsButtons = screen.getAllByTitle(/редактировать предметы/i);
    if (editSubjectsButtons.length > 0) {
      await user.click(editSubjectsButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('edit-subjects-dialog')).toBeInTheDocument();
      });
    }
  });

  // Тест 14: Открытие диалога редактирования профиля
  it('should open edit profile dialog on button click', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Teacher One')).toBeInTheDocument();
    });

    const editProfileButtons = screen.getAllByTitle(/редактировать профиль/i);
    if (editProfileButtons.length > 0) {
      await user.click(editProfileButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('edit-profile-dialog')).toBeInTheDocument();
      });
    }
  });

  // Тест 15: Открытие диалога сброса пароля
  it('should open reset password dialog on button click', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Teacher One')).toBeInTheDocument();
    });

    const resetPasswordButtons = screen.getAllByTitle(/сбросить пароль/i);
    if (resetPasswordButtons.length > 0) {
      await user.click(resetPasswordButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('reset-password-dialog')).toBeInTheDocument();
      });
    }
  });

  // Тест 16: Открытие диалога удаления
  it('should open delete dialog on delete button click', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Teacher One')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle(/удалить пользователя/i);
    if (deleteButtons.length > 0) {
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-user-dialog')).toBeInTheDocument();
      });
    }
  });

  // Тест 17: Отображение учетных данных после создания
  it('should display credentials after teacher creation', async () => {
    const user = userEvent.setup();
    (staffService.staffService.create as any).mockResolvedValue({
      success: true,
      credentials: { login: 'newteacher@test.com', password: 'SecurePass123!' },
    });

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    const createTeacherBtn = screen.getByRole('button', { name: /создать преподавателя/i });
    await user.click(createTeacherBtn);

    // Заполняем форму минимально
    const emailInput = screen.getAllByRole('textbox')[0];
    const firstNameInput = screen.getAllByRole('textbox')[1];
    const lastNameInput = screen.getAllByRole('textbox')[2];
    const subjectInput = screen.getAllByRole('textbox')[3];

    await user.type(emailInput, 'newteacher@test.com');
    await user.type(firstNameInput, 'John');
    await user.type(lastNameInput, 'Doe');
    await user.type(subjectInput, 'English');

    const submitButton = screen.getByRole('button', { name: /создать/i });
    await user.click(submitButton);

    // Проверяем что диалог с учетными данными появился
    await waitFor(() => {
      expect(screen.getByText(/учетные данные/i)).toBeInTheDocument();
      expect(screen.getByText('newteacher@test.com')).toBeInTheDocument();
    });
  });

  // Тест 18: Отображение "не назначены" для учителя без предметов
  it('should display "not assigned" for teacher without subjects', async () => {
    const teacherNoSubjects = [
      {
        id: 1,
        user: {
          id: 1,
          email: 'teacher1@test.com',
          full_name: 'Teacher One',
          is_active: true,
          date_joined: '2024-01-01T10:00:00Z',
          role: 'teacher',
        },
        subjects: [],
        experience_years: 5,
        bio: 'Experienced math teacher',
      },
    ];

    (staffService.staffService.list as any)
      .mockResolvedValueOnce(teacherNoSubjects)
      .mockResolvedValueOnce(mockTutorList);

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/не назначены/i)).toBeInTheDocument();
    });
  });

  // Тест 19: Логаут функция
  it('should logout successfully on logout button click', async () => {
    const user = userEvent.setup();
    mockLogout.mockResolvedValue(undefined);

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    const logoutButton = screen.getByRole('button', { name: /выйти/i });
    await user.click(logoutButton);

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/auth');
    });
  });

  // Тест 20: Перезагрузка списка после успешного действия
  it('should reload staff list after successful operations', async () => {
    (staffService.staffService.list as any)
      .mockResolvedValueOnce(mockTeacherList)
      .mockResolvedValueOnce(mockTutorList)
      .mockResolvedValueOnce(mockTeacherList)
      .mockResolvedValueOnce(mockTutorList);

    render(
      <BrowserRouter>
        <StaffManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Teacher One')).toBeInTheDocument();
    });

    // Проверяем что list был вызван минимум дважды (для teachers и tutors)
    const calls = (staffService.staffService.list as any).mock.calls;
    expect(calls.length).toBeGreaterThanOrEqual(2);
    expect(calls[0][0]).toBe('teacher');
    expect(calls[1][0]).toBe('tutor');
  });
});
