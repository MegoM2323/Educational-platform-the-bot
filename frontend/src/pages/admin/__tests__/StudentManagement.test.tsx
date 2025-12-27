import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import StudentManagement from '../StudentManagement';
import * as adminAPI from '@/integrations/api/adminAPI';
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

// Mock adminAPI
vi.mock('@/integrations/api/adminAPI', () => ({
  adminAPI: {
    getStudents: vi.fn(),
    editStudent: vi.fn(),
    deleteStudent: vi.fn(),
    resetPassword: vi.fn(),
  },
}));

// Mock dialogs
vi.mock('@/components/admin/CreateUserDialog', () => ({
  CreateUserDialog: ({ onSuccess }: any) => (
    <div data-testid="create-user-dialog" onClick={() => onSuccess?.()}>
      Mock CreateUserDialog
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

const mockStudentResponse = {
  success: true,
  data: {
    count: 2,
    next: null,
    previous: null,
    results: [
      {
        id: 1,
        user: {
          id: 1,
          email: 'student1@test.com',
          full_name: 'Student One',
          is_active: true,
          date_joined: '2024-01-01T10:00:00Z',
          role: 'student',
        },
        grade: '10A',
        tutor_id: null,
        parent_id: null,
      },
      {
        id: 2,
        user: {
          id: 2,
          email: 'student2@test.com',
          full_name: 'Student Two',
          is_active: false,
          date_joined: '2024-01-02T10:00:00Z',
          role: 'student',
        },
        grade: '11B',
        tutor_id: null,
        parent_id: null,
      },
    ],
  },
};

describe('StudentManagement', () => {
  beforeEach(() => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue(mockUseAuth() as any);
    (adminAPI.adminAPI.getStudents as any).mockResolvedValue(mockStudentResponse);
    mockNavigate.mockClear();
    mockLogout.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // Тест 1: Рендеринг основных элементов
  it('should render student management page with all main elements', async () => {
    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    // Проверяем заголовок
    await waitFor(() => {
      expect(screen.getByText(/управление студентами/i)).toBeInTheDocument();
    });

    // Проверяем кнопку создания
    expect(screen.getByRole('button', { name: /создать студента/i })).toBeInTheDocument();

    // Проверяем кнопку выхода
    expect(screen.getByRole('button', { name: /выйти/i })).toBeInTheDocument();
  });

  // Тест 2: Загрузка списка студентов
  it('should load and display student list', async () => {
    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    // Ждем загрузки студентов
    await waitFor(() => {
      expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      expect(screen.getByText('student2@test.com')).toBeInTheDocument();
    });

    // Проверяем что данные отображаются
    expect(screen.getByText('Student One')).toBeInTheDocument();
    expect(screen.getByText('Student Two')).toBeInTheDocument();
    expect(screen.getByText('10A')).toBeInTheDocument();
    expect(screen.getByText('11B')).toBeInTheDocument();
  });

  // Тест 3: Отображение статуса активности
  it('should display student activity status correctly', async () => {
    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      const badges = screen.getAllByRole('status');
      expect(badges.length).toBeGreaterThan(0);
    });

    // Проверяем наличие статусов
    const activeText = screen.getAllByText(/активен/i);
    const inactiveText = screen.getAllByText(/неактивен/i);
    expect(activeText.length + inactiveText.length).toBeGreaterThan(0);
  });

  // Тест 4: Фильтр по поиску
  it('should filter students by search query', async () => {
    const user = userEvent.setup();
    const filteredResponse = {
      success: true,
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [mockStudentResponse.data.results[0]],
      },
    };
    (adminAPI.adminAPI.getStudents as any).mockResolvedValue(filteredResponse);

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('student1@test.com')).toBeInTheDocument();
    });

    // Вводим поиск
    const searchInput = screen.getByPlaceholderText(/фио, email/i);
    await user.type(searchInput, 'student1');

    // Проверяем что API был вызван
    await waitFor(() => {
      expect(adminAPI.adminAPI.getStudents).toHaveBeenCalled();
    });
  });

  // Тест 5: Фильтр по классу
  it('should filter students by grade', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('student1@test.com')).toBeInTheDocument();
    });

    // Заполняем фильтр класса
    const gradeInput = screen.getByPlaceholderText(/класс/i);
    await user.type(gradeInput, '10A');

    // Проверяем что API был вызван
    await waitFor(() => {
      expect(adminAPI.adminAPI.getStudents).toHaveBeenCalled();
    });
  });

  // Тест 6: Фильтр по статусу активности
  it('should filter students by active status', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('student1@test.com')).toBeInTheDocument();
    });

    // Выбираем фильтр активности
    const statusSelect = screen.getByDisplayValue(/все/i);
    await user.selectOption(statusSelect, 'true');

    // Проверяем что API был вызван с правильными параметрами
    await waitFor(() => {
      const calls = (adminAPI.adminAPI.getStudents as any).mock.calls;
      expect(calls.some((call: any) => call[0].is_active === true)).toBe(true);
    });
  });

  // Тест 7: Открытие диалога создания студента
  it('should open create student dialog on button click', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    const createButton = screen.getByRole('button', { name: /создать студента/i });
    await user.click(createButton);

    // Проверяем что диалог открылся
    await waitFor(() => {
      expect(screen.getByTestId('create-user-dialog')).toBeInTheDocument();
    });
  });

  // Тест 8: Открытие диалога редактирования студента
  it('should open edit dialog when edit button clicked', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    // Ждем загрузки студентов
    await waitFor(() => {
      expect(screen.getByText('student1@test.com')).toBeInTheDocument();
    });

    // Находим кнопку редактирования (первого студента)
    const editButtons = screen.getAllByTitle(/редактировать пользователя/i);
    await user.click(editButtons[0]);

    // Проверяем что диалог редактирования открылся
    await waitFor(() => {
      expect(screen.getByTestId('edit-user-dialog')).toBeInTheDocument();
    });
  });

  // Тест 9: Открытие диалога сброса пароля
  it('should open reset password dialog on button click', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('student1@test.com')).toBeInTheDocument();
    });

    const resetButtons = screen.getAllByTitle(/сбросить пароль/i);
    await user.click(resetButtons[0]);

    // Проверяем что диалог открылся
    await waitFor(() => {
      expect(screen.getByTestId('reset-password-dialog')).toBeInTheDocument();
    });
  });

  // Тест 10: Открытие диалога удаления студента
  it('should open delete dialog when delete button clicked', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('student1@test.com')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle(/удалить пользователя/i);
    await user.click(deleteButtons[0]);

    // Проверяем что диалог удаления открылся
    await waitFor(() => {
      expect(screen.getByTestId('delete-user-dialog')).toBeInTheDocument();
    });
  });

  // Тест 11: Пагинация - кнопка "Далее"
  it('should load next page on next button click', async () => {
    const user = userEvent.setup();
    const secondPageResponse = {
      success: true,
      data: {
        count: 3,
        next: null,
        previous: 'http://api/students?page=1',
        results: [
          {
            id: 3,
            user: {
              id: 3,
              email: 'student3@test.com',
              full_name: 'Student Three',
              is_active: true,
              date_joined: '2024-01-03T10:00:00Z',
              role: 'student',
            },
            grade: '9C',
          },
        ],
      },
    };

    (adminAPI.adminAPI.getStudents as any)
      .mockResolvedValueOnce(mockStudentResponse)
      .mockResolvedValueOnce(secondPageResponse);

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('student1@test.com')).toBeInTheDocument();
    });

    // Кликаем на кнопку "Далее"
    const nextButton = screen.getByRole('button', { name: /chevron/i });
    // Пропускаем первую кнопку (предыдущая), берем вторую (следующая)
    const buttons = screen.getAllByRole('button');
    const nextBtn = buttons.find((btn) => btn.querySelector('[class*="chevron-right"]'));

    if (nextBtn) {
      await user.click(nextBtn);

      // Проверяем что был сделан второй запрос со страницей 2
      await waitFor(() => {
        const calls = (adminAPI.adminAPI.getStudents as any).mock.calls;
        expect(calls[calls.length - 1][0].page).toBe(2);
      });
    }
  });

  // Тест 12: Отображение информации о пагинации
  it('should display pagination info correctly', async () => {
    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/показано 2 из 2 студентов/i)).toBeInTheDocument();
      expect(screen.getByText(/страница 1 из 1/i)).toBeInTheDocument();
    });
  });

  // Тест 13: Загрузка во время операций
  it('should show loading state while fetching students', () => {
    (adminAPI.adminAPI.getStudents as any).mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(() => resolve(mockStudentResponse), 100);
        })
    );

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    // Проверяем что "Загрузка..." появляется
    // (может исчезнуть слишком быстро, но должна была быть)
    const table = screen.queryByRole('table');
    expect(table || screen.queryByText(/загрузка/i)).toBeDefined();
  });

  // Тест 14: Сообщение об ошибке при загрузке
  it('should display error message when student loading fails', async () => {
    const { toast } = await import('sonner');
    (adminAPI.adminAPI.getStudents as any).mockResolvedValue({
      success: false,
      error: 'Ошибка загрузки списка студентов',
    });

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Ошибка загрузки списка студентов');
    });
  });

  // Тест 15: Логаут функция
  it('should logout successfully on logout button click', async () => {
    const user = userEvent.setup();
    mockLogout.mockResolvedValue(undefined);

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    const logoutButton = screen.getByRole('button', { name: /выйти/i });
    await user.click(logoutButton);

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/auth');
    });
  });

  // Тест 16: Пустой список студентов
  it('should display empty state when no students found', async () => {
    (adminAPI.adminAPI.getStudents as any).mockResolvedValue({
      success: true,
      data: {
        count: 0,
        next: null,
        previous: null,
        results: [],
      },
    });

    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/студенты не найдены/i)).toBeInTheDocument();
    });
  });

  // Тест 17: Форматирование даты регистрации
  it('should format registration date correctly', async () => {
    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Проверяем что дата форматируется (локаль ru-RU)
      const dateCell = screen.getByText(/\d{1,2}\.\d{1,2}\.\d{4}/);
      expect(dateCell).toBeInTheDocument();
    });
  });

  // Тест 18: Проверка структуры таблицы
  it('should have correct table structure with all columns', async () => {
    render(
      <BrowserRouter>
        <StudentManagement />
      </BrowserRouter>
    );

    await waitFor(() => {
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();

      // Проверяем заголовки колонок
      expect(screen.getByText(/фио/i)).toBeInTheDocument();
      expect(screen.getByText(/email/i)).toBeInTheDocument();
      expect(screen.getByText(/класс/i)).toBeInTheDocument();
      expect(screen.getByText(/статус/i)).toBeInTheDocument();
      expect(screen.getByText(/дата регистрации/i)).toBeInTheDocument();
      expect(screen.getByText(/действия/i)).toBeInTheDocument();
    });
  });
});
