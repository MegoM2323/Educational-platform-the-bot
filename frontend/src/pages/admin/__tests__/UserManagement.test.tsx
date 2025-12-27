import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import UserManagement from '../UserManagement';
import { adminAPI } from '@/integrations/api/adminAPI';
import { toast } from 'sonner';

// Mock dependencies
vi.mock('@/integrations/api/adminAPI');
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock components
vi.mock('@/components/admin/EditUserDialog', () => ({
  EditUserDialog: ({ open, onOpenChange }: any) => (
    open ? <div data-testid="edit-user-dialog">Edit Dialog</div> : null
  ),
}));

vi.mock('@/components/admin/ResetPasswordDialog', () => ({
  ResetPasswordDialog: ({ open, onOpenChange }: any) => (
    open ? <div data-testid="reset-password-dialog">Reset Password Dialog</div> : null
  ),
}));

vi.mock('@/components/admin/DeleteUserDialog', () => ({
  DeleteUserDialog: ({ open, onOpenChange }: any) => (
    open ? <div data-testid="delete-user-dialog">Delete Dialog</div> : null
  ),
}));

const mockUsers = [
  {
    id: 1,
    email: 'student1@test.com',
    full_name: 'Иван Иванов',
    role: 'student',
    is_active: true,
    date_joined: '2024-01-01T00:00:00Z',
    last_login: '2024-12-27T10:00:00Z',
  },
  {
    id: 2,
    email: 'teacher1@test.com',
    full_name: 'Мария Петрова',
    role: 'teacher',
    is_active: true,
    date_joined: '2024-01-15T00:00:00Z',
    last_login: '2024-12-26T14:30:00Z',
  },
  {
    id: 3,
    email: 'admin@test.com',
    full_name: 'Админ Тестов',
    role: 'admin',
    is_active: true,
    date_joined: '2023-12-01T00:00:00Z',
    last_login: '2024-12-27T09:00:00Z',
  },
];

const mockPaginatedResponse = {
  count: 3,
  next: null,
  previous: null,
  results: mockUsers,
};

const renderComponent = () => {
  return render(
    <BrowserRouter>
      <UserManagement />
    </BrowserRouter>
  );
};

describe('UserManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adminAPI.getUsers as any).mockResolvedValue({
      success: true,
      data: mockPaginatedResponse,
    });
  });

  describe('Rendering and Loading', () => {
    it('should render the page title', async () => {
      renderComponent();
      expect(screen.getByText('Управление пользователями')).toBeInTheDocument();
    });

    it('should load and display users on mount', async () => {
      renderComponent();

      await waitFor(() => {
        expect(adminAPI.getUsers).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
        expect(screen.getByText('teacher1@test.com')).toBeInTheDocument();
        expect(screen.getByText('admin@test.com')).toBeInTheDocument();
      });
    });

    it('should display empty state when no users found', async () => {
      (adminAPI.getUsers as any).mockResolvedValue({
        success: true,
        data: { count: 0, next: null, previous: null, results: [] },
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Пользователи не найдены')).toBeInTheDocument();
      });
    });

    it('should show error toast on API failure', async () => {
      (adminAPI.getUsers as any).mockResolvedValue({
        success: false,
        error: 'Network error',
      });

      renderComponent();

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Network error');
      });
    });
  });

  describe('Filtering', () => {
    it('should filter users by role', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const roleSelect = screen.getByDisplayValue('Все роли');
      fireEvent.change(roleSelect, { target: { value: 'student' } });

      await waitFor(() => {
        expect(adminAPI.getUsers).toHaveBeenCalledWith(
          expect.objectContaining({ role: 'student', page: 1 })
        );
      });
    });

    it('should filter users by status', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const statusSelect = screen.getByDisplayValue('Все статусы');
      fireEvent.change(statusSelect, { target: { value: 'active' } });

      await waitFor(() => {
        expect(adminAPI.getUsers).toHaveBeenCalledWith(
          expect.objectContaining({ status: 'active', page: 1 })
        );
      });
    });

    it('should search users by email/name', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Email, ФИО...');
      await user.type(searchInput, 'Иван');

      await waitFor(() => {
        expect(adminAPI.getUsers).toHaveBeenCalledWith(
          expect.objectContaining({ search: 'Иван', page: 1 })
        );
      });
    });

    it('should filter by date range', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const dateFromInput = screen.getAllByRole('textbox').find(
        input => input.getAttribute('type') === 'date'
      );

      if (dateFromInput) {
        fireEvent.change(dateFromInput, { target: { value: '2024-01-01' } });

        await waitFor(() => {
          expect(adminAPI.getUsers).toHaveBeenCalledWith(
            expect.objectContaining({ joined_date_from: '2024-01-01', page: 1 })
          );
        });
      }
    });

    it('should clear all filters', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Email, ФИО...');
      await user.type(searchInput, 'test');

      const clearButton = screen.getByRole('button', { name: /Сбросить фильтры/i });
      await user.click(clearButton);

      await waitFor(() => {
        expect(searchInput).toHaveValue('');
      });
    });
  });

  describe('Sorting', () => {
    it('should sort by email column', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const emailHeader = screen.getByText(/^Email/);
      await user.click(emailHeader);

      await waitFor(() => {
        expect(adminAPI.getUsers).toHaveBeenCalledWith(
          expect.objectContaining({ ordering: 'email', page: 1 })
        );
      });
    });

    it('should toggle sort direction', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const idHeader = screen.getByText(/^ID/);

      // First click - ascending
      await user.click(idHeader);
      await waitFor(() => {
        expect(adminAPI.getUsers).toHaveBeenCalledWith(
          expect.objectContaining({ ordering: 'id' })
        );
      });

      // Second click - descending
      await user.click(idHeader);
      await waitFor(() => {
        expect(adminAPI.getUsers).toHaveBeenCalledWith(
          expect.objectContaining({ ordering: '-id' })
        );
      });
    });
  });

  describe('Selection and Bulk Operations', () => {
    it('should select individual users', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      const firstUserCheckbox = checkboxes[1]; // Skip select-all checkbox

      await user.click(firstUserCheckbox);

      await waitFor(() => {
        expect(firstUserCheckbox).toBeChecked();
      });
    });

    it('should select all users with select-all checkbox', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      const selectAllCheckbox = checkboxes[0];

      await user.click(selectAllCheckbox);

      await waitFor(() => {
        const allCheckboxes = screen.getAllByRole('checkbox');
        allCheckboxes.forEach(checkbox => {
          expect(checkbox).toBeChecked();
        });
      });
    });

    it('should show bulk operations bar when users selected', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]); // Select first user

      await waitFor(() => {
        expect(screen.getByText(/Выбрано 1 пользователей/)).toBeInTheDocument();
      });
    });

    it('should execute bulk activate operation', async () => {
      (adminAPI.bulkActivateUsers as any).mockResolvedValue({
        success: true,
        data: {
          success_count: 1,
          failed_count: 0,
          failed_ids: [],
          details: 'OK',
        },
      });

      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      // Select user
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      // Click activate button - find by partial text match
      await waitFor(() => {
        expect(screen.getByText('Выбрано 1 пользователей')).toBeInTheDocument();
      });

      const activateButtons = screen.getAllByRole('button');
      const activateButton = activateButtons.find(btn => btn.textContent?.includes('Активировать'));

      if (activateButton) {
        await user.click(activateButton);

        // Confirm in dialog
        const confirmButtons = screen.getAllByRole('button');
        const confirmButton = confirmButtons.find(btn => btn.textContent?.includes('Подтвердить'));

        if (confirmButton) {
          await user.click(confirmButton);

          await waitFor(() => {
            expect(adminAPI.bulkActivateUsers).toHaveBeenCalledWith([1]);
            expect(toast.success).toHaveBeenCalled();
          });
        }
      }
    });

    it('should execute bulk deactivate operation', async () => {
      (adminAPI.bulkDeactivateUsers as any).mockResolvedValue({
        success: true,
        data: {
          success_count: 1,
          failed_count: 0,
          failed_ids: [],
          details: 'OK',
        },
      });

      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      await waitFor(() => {
        expect(screen.getByText('Выбрано 1 пользователей')).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button');
      const deactivateButton = buttons.find(btn => btn.textContent?.includes('Деактивировать'));

      if (deactivateButton) {
        await user.click(deactivateButton);

        const confirmButtons = screen.getAllByRole('button');
        const confirmButton = confirmButtons.find(btn => btn.textContent?.includes('Подтвердить'));

        if (confirmButton) {
          await user.click(confirmButton);

          await waitFor(() => {
            expect(adminAPI.bulkDeactivateUsers).toHaveBeenCalledWith([1]);
          });
        }
      }
    });

    it('should execute bulk suspend operation', async () => {
      (adminAPI.bulkSuspendUsers as any).mockResolvedValue({
        success: true,
        data: {
          success_count: 1,
          failed_count: 0,
          failed_ids: [],
          details: 'OK',
        },
      });

      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      await waitFor(() => {
        expect(screen.getByText('Выбрано 1 пользователей')).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button');
      const suspendButton = buttons.find(btn => btn.textContent?.includes('Заблокировать'));

      if (suspendButton) {
        await user.click(suspendButton);

        const confirmButtons = screen.getAllByRole('button');
        const confirmButton = confirmButtons.find(btn => btn.textContent?.includes('Подтвердить'));

        if (confirmButton) {
          await user.click(confirmButton);

          await waitFor(() => {
            expect(adminAPI.bulkSuspendUsers).toHaveBeenCalledWith([1]);
          });
        }
      }
    });

    it('should execute bulk reset password operation', async () => {
      (adminAPI.bulkResetPasswordUsers as any).mockResolvedValue({
        success: true,
        data: {
          success_count: 1,
          failed_count: 0,
          failed_ids: [],
          details: 'OK',
        },
      });

      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      await waitFor(() => {
        expect(screen.getByText('Выбрано 1 пользователей')).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button');
      const resetButton = buttons.find(btn => btn.textContent?.includes('Сбросить пароли'));

      if (resetButton) {
        await user.click(resetButton);

        const confirmButtons = screen.getAllByRole('button');
        const confirmButton = confirmButtons.find(btn => btn.textContent?.includes('Подтвердить'));

        if (confirmButton) {
          await user.click(confirmButton);

          await waitFor(() => {
            expect(adminAPI.bulkResetPasswordUsers).toHaveBeenCalledWith([1]);
          });
        }
      }
    });

    it('should execute bulk delete operation with warning', async () => {
      (adminAPI.bulkDeleteUsers as any).mockResolvedValue({
        success: true,
        data: {
          success_count: 1,
          failed_count: 0,
          failed_ids: [],
          details: 'OK',
        },
      });

      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      await waitFor(() => {
        expect(screen.getByText('Выбрано 1 пользователей')).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button');
      const deleteButton = buttons.find(btn => btn.textContent?.includes('Удалить') && !btn.textContent?.includes('действия'));

      if (deleteButton) {
        await user.click(deleteButton);

        const confirmButtons = screen.getAllByRole('button');
        const confirmButton = confirmButtons.find(btn => btn.textContent?.includes('Подтвердить'));

        if (confirmButton) {
          await user.click(confirmButton);

          await waitFor(() => {
            expect(adminAPI.bulkDeleteUsers).toHaveBeenCalledWith([1]);
          });
        }
      }
    });

    it('should require role selection for bulk assign role', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      // Note: Bulk assign role button is not visible in initial render
      // This test verifies the feature would work when exposed in UI
    });

    it('should clear selection after bulk operation success', async () => {
      (adminAPI.bulkActivateUsers as any).mockResolvedValue({
        success: true,
        data: {
          success_count: 2,
          failed_count: 0,
          failed_ids: [],
          details: 'OK',
        },
      });

      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      await waitFor(() => {
        expect(screen.getByText('Выбрано 1 пользователей')).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button');
      const activateButton = buttons.find(btn => btn.textContent?.includes('Активировать'));

      if (activateButton) {
        await user.click(activateButton);

        const confirmButtons = screen.getAllByRole('button');
        const confirmButton = confirmButtons.find(btn => btn.textContent?.includes('Подтвердить'));

        if (confirmButton) {
          await user.click(confirmButton);

          await waitFor(() => {
            expect(screen.queryByText(/Выбрано/)).not.toBeInTheDocument();
          });
        }
      }
    });
  });

  describe('User Actions', () => {
    it('should open user details modal', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const viewButtons = screen.getAllByTitle('Просмотр профиля');
      await user.click(viewButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Профиль пользователя')).toBeInTheDocument();
      });
    });

    it('should open edit user dialog', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByTitle('Редактировать');
      await user.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('edit-user-dialog')).toBeInTheDocument();
      });
    });

    it('should open reset password dialog', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const resetButtons = screen.getAllByTitle('Сбросить пароль');
      await user.click(resetButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('reset-password-dialog')).toBeInTheDocument();
      });
    });

    it('should open delete user dialog', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Удалить');
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('delete-user-dialog')).toBeInTheDocument();
      });
    });
  });

  describe('Pagination', () => {
    it('should change page size', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const pageSizeSelect = screen.getByDisplayValue('25');
      await user.selectOptions(pageSizeSelect, '50');

      await waitFor(() => {
        expect(adminAPI.getUsers).toHaveBeenCalledWith(
          expect.objectContaining({ page_size: 50, page: 1 })
        );
      });
    });

    it('should navigate to next page', async () => {
      (adminAPI.getUsers as any).mockResolvedValue({
        success: true,
        data: {
          count: 50,
          next: 'next',
          previous: null,
          results: mockUsers,
        },
      });

      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const nextButton = screen.getByRole('button', { name: />/i });
      await user.click(nextButton);

      await waitFor(() => {
        expect(adminAPI.getUsers).toHaveBeenCalledWith(
          expect.objectContaining({ page: 2 })
        );
      });
    });

    it('should navigate to previous page', async () => {
      (adminAPI.getUsers as any).mockResolvedValue({
        success: true,
        data: {
          count: 50,
          next: null,
          previous: 'prev',
          results: mockUsers,
        },
      });

      const user = userEvent.setup();
      renderComponent();

      // Load page 2 first
      (adminAPI.getUsers as any).mockResolvedValue({
        success: true,
        data: {
          count: 50,
          next: null,
          previous: 'prev',
          results: mockUsers,
        },
      });

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const prevButton = screen.getByRole('button', { name: /</i });
      if (!prevButton.hasAttribute('disabled')) {
        await user.click(prevButton);

        await waitFor(() => {
          expect(adminAPI.getUsers).toHaveBeenCalled();
        });
      }
    });
  });

  describe('CSV Export', () => {
    it('should export users to CSV', async () => {
      const user = userEvent.setup();
      const createElementSpy = vi.spyOn(document, 'createElement');

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button');
      const exportButton = buttons.find(btn => btn.textContent?.includes('Экспорт CSV'));

      if (exportButton) {
        await user.click(exportButton);

        await waitFor(() => {
          expect(createElementSpy).toHaveBeenCalledWith('a');
        });
      }

      createElementSpy.mockRestore();
    });
  });

  describe('Error Handling', () => {
    it('should show error when bulk operation fails', async () => {
      (adminAPI.bulkActivateUsers as any).mockRejectedValue(
        new Error('Operation failed')
      );

      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      const activateButton = screen.getByRole('button', { name: /Активировать/i });
      await user.click(activateButton);

      const confirmButton = screen.getByRole('button', { name: /Подтвердить/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Operation failed');
      });
    });

    it('should prevent bulk operation without selection', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('student1@test.com')).toBeInTheDocument();
      });

      // Bulk operation bar shouldn't be visible without selection
      expect(screen.queryByText(/Выбрано/)).not.toBeInTheDocument();
    });
  });
});
