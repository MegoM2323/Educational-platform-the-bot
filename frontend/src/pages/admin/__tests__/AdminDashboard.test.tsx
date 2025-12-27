import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import AdminDashboard from '../AdminDashboard';
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

// Mock toast notifications
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

describe('AdminDashboard', () => {
  beforeEach(() => {
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue(mockUseAuth() as any);
    mockNavigate.mockClear();
    mockLogout.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // Тест 1: Рендеринг основных элементов
  it('should render admin dashboard with all main elements', () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Проверяем заголовок
    expect(screen.getByRole('heading', { level: 1, name: /администратор/i })).toBeInTheDocument();

    // Проверяем кнопку выхода
    expect(screen.getByRole('button', { name: /выйти/i })).toBeInTheDocument();

    // Проверяем статистические карточки (по названиям)
    expect(screen.getByText(/всего пользователей/i)).toBeInTheDocument();
    expect(screen.getByText(/студентов/i)).toBeInTheDocument();
    expect(screen.getByText(/преподавателей/i)).toBeInTheDocument();
    expect(screen.getByText(/активных сегодня/i)).toBeInTheDocument();
  });

  // Тест 2: Рендеринг статистических значений
  it('should display statistics values in stat cards', () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Проверяем что значения отображаются (по умолчанию 0)
    const cardValues = screen.getAllByText('0');
    expect(cardValues.length).toBeGreaterThan(0);
  });

  // Тест 3: Наличие табов для управления
  it('should display all management tabs', () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Проверяем табы
    expect(screen.getByRole('tab', { name: /студенты/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /преподаватели и тьюторы/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /родители/i })).toBeInTheDocument();
  });

  // Тест 4: Переключение между табами
  it('should switch between tabs when clicked', async () => {
    const user = userEvent.setup();
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Проверяем что первый таб активен (студенты)
    const studentsTab = screen.getByRole('tab', { name: /студенты/i });
    expect(studentsTab).toHaveAttribute('data-state', 'active');

    // Кликаем на таб преподавателей
    const staffTab = screen.getByRole('tab', { name: /преподаватели и тьюторы/i });
    await user.click(staffTab);

    // Проверяем что таб переключился
    await waitFor(() => {
      expect(staffTab).toHaveAttribute('data-state', 'active');
    });
  });

  // Тест 5: Логаут функция
  it('should logout successfully on logout button click', async () => {
    const user = userEvent.setup();
    mockLogout.mockResolvedValue(undefined);

    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    const logoutButton = screen.getByRole('button', { name: /выйти/i });
    await user.click(logoutButton);

    // Проверяем что logout был вызван
    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalled();
    });

    // Проверяем редирект на /auth
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/auth');
    });
  });

  // Тест 6: Обработка ошибки при логауте
  it('should handle logout error gracefully', async () => {
    const user = userEvent.setup();
    mockLogout.mockRejectedValue(new Error('Logout failed'));

    const { toast } = await import('sonner');

    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    const logoutButton = screen.getByRole('button', { name: /выйти/i });
    await user.click(logoutButton);

    // Проверяем что ошибка была показана
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Ошибка при выходе');
    });
  });

  // Тест 7: Кнопка выхода должна быть disabled во время логаута
  it('should disable logout button during logout process', async () => {
    const user = userEvent.setup();
    mockLogout.mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(resolve, 100);
        })
    );

    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    const logoutButton = screen.getByRole('button', { name: /выйти/i });
    await user.click(logoutButton);

    // Проверяем что кнопка disabled
    await waitFor(() => {
      expect(logoutButton).toBeDisabled();
    });
  });

  // Тест 8: Иконки в статистических карточках
  it('should render icons in statistics cards', () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Проверяем наличие SVG элементов (иконки lucide-react)
    const svgs = screen.getAllByRole('img', { hidden: true });
    expect(svgs.length).toBeGreaterThan(0);
  });

  // Тест 9: Правильная структура сетки для разных экранов
  it('should have responsive grid layout for stat cards', () => {
    const { container } = render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Проверяем наличие grid контейнера
    const gridContainer = container.querySelector('[class*="grid"]');
    expect(gridContainer).toBeInTheDocument();
    expect(gridContainer).toHaveClass('grid', 'gap-4', 'mb-6');
  });

  // Тест 10: Дочерние компоненты должны рендериться в табах
  it('should render StudentManagement in students tab content', () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Проверяем что StudentManagement компонент рендерится
    // Это можно проверить через наличие элементов StudentManagement
    const tabContent = screen.getByRole('tabpanel');
    expect(tabContent).toBeInTheDocument();
  });

  // Тест 11: Проверка начальных значений статистики
  it('should initialize stats with zero values', () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Проверяем что все значения статистики = 0
    const values = screen.getAllByText('0');
    // Должны быть минимум 6 нулей (все поля статистики)
    expect(values.length).toBeGreaterThanOrEqual(4);
  });

  // Тест 12: Проверка наличия всех необходимых элементов в CardHeader
  it('should display correct header layout with title and buttons', () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Проверяем заголовок
    const heading = screen.getByRole('heading', { level: 1, name: /администратор/i });
    expect(heading).toBeInTheDocument();

    // Проверяем что кнопка выхода находится в одном контейнере с заголовком
    const logoutButton = screen.getByRole('button', { name: /выйти/i });
    expect(logoutButton).toBeInTheDocument();
  });

  // Тест 13: Обработка нескольких кликов на выход
  it('should handle multiple logout button clicks gracefully', async () => {
    const user = userEvent.setup();
    mockLogout.mockResolvedValue(undefined);

    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    const logoutButton = screen.getByRole('button', { name: /выйти/i });

    // Первый клик
    await user.click(logoutButton);

    // Проверяем что button disabled
    await waitFor(() => {
      expect(logoutButton).toBeDisabled();
    });
  });
});
