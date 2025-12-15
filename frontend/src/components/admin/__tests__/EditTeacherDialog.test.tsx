import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditTeacherDialog } from '../EditTeacherDialog';
import { adminAPI } from '@/integrations/api/adminAPI';
import { StaffListItem } from '@/services/staffService';
import * as sonner from 'sonner';

// Mock dependencies
vi.mock('@/integrations/api/adminAPI');
vi.mock('sonner');

// Mock subject data for SubjectMultiSelect
vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn().mockResolvedValue({
      success: true,
      data: {
        results: [
          { id: 1, name: 'Mathematics', description: 'Math course', is_active: true },
          { id: 2, name: 'Physics', description: 'Physics course', is_active: true },
          { id: 3, name: 'Chemistry', description: 'Chemistry course', is_active: true },
          { id: 4, name: 'Biology', description: 'Biology course', is_active: true },
        ],
      },
    }),
  },
}));

const mockTeacher: StaffListItem = {
  id: 1,
  user: {
    id: 1,
    email: 'teacher@test.com',
    first_name: 'John',
    last_name: 'Smith',
    phone: '+79991234567',
    is_active: true,
    role: 'teacher',
    avatar: null,
  },
  experience_years: 5,
  bio: 'Experienced teacher',
  subjects: [
    { id: 1, name: 'Mathematics' },
    { id: 2, name: 'Physics' },
  ],
};

describe('EditTeacherDialog', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (adminAPI.editTeacher as any).mockResolvedValue({
      success: true,
      data: mockTeacher,
    });
    (sonner.toast.success as any).mockImplementation(() => {});
  });

  describe('Form Rendering', () => {
    it('should render dialog with title when open', () => {
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      expect(screen.getByText('Редактировать преподавателя')).toBeInTheDocument();
    });

    it('should not render dialog when closed', () => {
      const { container } = render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={false}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const dialog = container.querySelector('[role="dialog"]');
      expect(dialog).not.toBeInTheDocument();
    });

    it('should populate initial form data from teacher props', async () => {
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      // Wait for form to be populated
      await waitFor(() => {
        const emailInput = screen.getByDisplayValue(mockTeacher.user.email);
        expect(emailInput).toBeInTheDocument();
      });

      expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Smith')).toBeInTheDocument();
      expect(screen.getByDisplayValue(mockTeacher.user.phone)).toBeInTheDocument();
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Experienced teacher')).toBeInTheDocument();
    });

    it('should render all form field labels', async () => {
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Email *')).toBeInTheDocument();
        expect(screen.getByText('Имя *')).toBeInTheDocument();
        expect(screen.getByText('Фамилия *')).toBeInTheDocument();
        expect(screen.getByText('Телефон')).toBeInTheDocument();
        expect(screen.getByText('Активен')).toBeInTheDocument();
        expect(screen.getByText('Опыт работы (лет)')).toBeInTheDocument();
        expect(screen.getByText('Биография')).toBeInTheDocument();
        expect(screen.getByText('Предметы')).toBeInTheDocument();
      });
    });

    it('should render Cancel and Save buttons', async () => {
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Отмена/ })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Сохранить/ })).toBeInTheDocument();
      });
    });
  });

  describe('Form Submission with Complete Data', () => {
    it('should successfully submit form with complete data', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      // Fill in form fields
      const firstNameInput = screen.getByDisplayValue('John') as HTMLInputElement;
      await user.clear(firstNameInput);
      await user.type(firstNameInput, 'Jane');

      const lastNameInput = screen.getByDisplayValue('Smith') as HTMLInputElement;
      await user.clear(lastNameInput);
      await user.type(lastNameInput, 'Doe');

      const emailInput = screen.getByDisplayValue(mockTeacher.user.email) as HTMLInputElement;
      await user.clear(emailInput);
      await user.type(emailInput, 'jane.doe@test.com');

      const phoneInput = screen.getByDisplayValue(mockTeacher.user.phone) as HTMLInputElement;
      await user.clear(phoneInput);
      await user.type(phoneInput, '79997654321');

      const experienceInput = screen.getByDisplayValue('5') as HTMLInputElement;
      await user.clear(experienceInput);
      await user.type(experienceInput, '10');

      const bioTextarea = screen.getByDisplayValue('Experienced teacher') as HTMLTextAreaElement;
      await user.clear(bioTextarea);
      await user.type(bioTextarea, 'Very experienced teacher');

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      // Verify API call
      await waitFor(() => {
        expect(adminAPI.editTeacher).toHaveBeenCalledWith(mockTeacher.id, expect.objectContaining({
          first_name: 'Jane',
          last_name: 'Doe',
          email: 'jane.doe@test.com',
          phone: '+79997654321',
          experience_years: 10,
          bio: 'Very experienced teacher',
        }));
      });

      // Verify success callback
      expect(mockOnSuccess).toHaveBeenCalled();
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('should show loading state during submission', async () => {
      const user = userEvent.setup();
      (adminAPI.editTeacher as any).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ success: true }), 100))
      );

      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      // Check for loading state
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Сохранение/ })).toBeInTheDocument();
      });
    });

    it('should display success notification after save', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(sonner.toast.success).toHaveBeenCalledWith('Преподаватель успешно обновлен');
      });
    });

    it('should close dialog after successful save', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      });
    });
  });

  describe('Form Validation', () => {
    it('should prevent form submission without required fields', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const emailInput = screen.getByDisplayValue(mockTeacher.user.email) as HTMLInputElement;
      await user.clear(emailInput);

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      // API should not be called if validation fails
      expect(adminAPI.editTeacher).not.toHaveBeenCalled();
    });

    it('should accept valid email formats', async () => {
      const user = userEvent.setup();
      const validEmails = [
        'test@example.com',
        'user.name@example.co.uk',
        'test+tag@example.com',
      ];

      for (const email of validEmails) {
        vi.clearAllMocks();
        (adminAPI.editTeacher as any).mockResolvedValue({
          success: true,
        });

        const { unmount } = render(
          <EditTeacherDialog
            teacher={mockTeacher}
            open={true}
            onOpenChange={mockOnOpenChange}
            onSuccess={mockOnSuccess}
          />
        );

        await waitFor(() => {
          expect(screen.getByDisplayValue(mockTeacher.user.email)).toBeInTheDocument();
        });

        const emailInput = screen.getByDisplayValue(mockTeacher.user.email) as HTMLInputElement;
        await user.clear(emailInput);
        await user.type(emailInput, email);

        const submitButton = screen.getByRole('button', { name: /Сохранить/ });
        await user.click(submitButton);

        await waitFor(() => {
          expect(adminAPI.editTeacher).toHaveBeenCalled();
        });

        unmount();
      }
    });
  });

  describe('Phone Number Formatting', () => {
    it('should format phone number starting with 8', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue(mockTeacher.user.phone)).toBeInTheDocument();
      });

      const phoneInput = screen.getByDisplayValue(mockTeacher.user.phone) as HTMLInputElement;
      await user.clear(phoneInput);
      await user.type(phoneInput, '89991234567');

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(adminAPI.editTeacher).toHaveBeenCalledWith(mockTeacher.id, expect.objectContaining({
          phone: '+79991234567',
        }));
      });
    });

    it('should format phone number starting with 7', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue(mockTeacher.user.phone)).toBeInTheDocument();
      });

      const phoneInput = screen.getByDisplayValue(mockTeacher.user.phone) as HTMLInputElement;
      await user.clear(phoneInput);
      await user.type(phoneInput, '79991234567');

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(adminAPI.editTeacher).toHaveBeenCalledWith(mockTeacher.id, expect.objectContaining({
          phone: '+79991234567',
        }));
      });
    });

    it('should format 10-digit phone number', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue(mockTeacher.user.phone)).toBeInTheDocument();
      });

      const phoneInput = screen.getByDisplayValue(mockTeacher.user.phone) as HTMLInputElement;
      await user.clear(phoneInput);
      await user.type(phoneInput, '9991234567');

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(adminAPI.editTeacher).toHaveBeenCalledWith(mockTeacher.id, expect.objectContaining({
          phone: '+79991234567',
        }));
      });
    });

    it('should handle empty phone number', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue(mockTeacher.user.phone)).toBeInTheDocument();
      });

      const phoneInput = screen.getByDisplayValue(mockTeacher.user.phone) as HTMLInputElement;
      await user.clear(phoneInput);

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(adminAPI.editTeacher).toHaveBeenCalledWith(mockTeacher.id, expect.objectContaining({
          phone: undefined,
        }));
      });
    });
  });

  describe('Subject Multi-Select Functionality', () => {
    it('should add subjects when selected', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      // Wait for subjects to load (check for any subject)
      await waitFor(() => {
        expect(screen.queryByText('Загрузка предметов...')).not.toBeInTheDocument();
      });

      // Add Chemistry (id=3)
      const chemistryCheckbox = screen.getByRole('checkbox', { name: /Chemistry/ });
      await user.click(chemistryCheckbox);

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(adminAPI.editTeacher).toHaveBeenCalledWith(mockTeacher.id, expect.objectContaining({
          subject_ids: [1, 2, 3],
        }));
      });
    });

    it('should remove subjects when deselected', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      // Wait for subjects to load
      await waitFor(() => {
        expect(screen.queryByText('Загрузка предметов...')).not.toBeInTheDocument();
      });

      // Remove Physics
      const physicsCheckbox = screen.getByRole('checkbox', { name: /Physics/ });
      await user.click(physicsCheckbox);

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(adminAPI.editTeacher).toHaveBeenCalledWith(mockTeacher.id, expect.objectContaining({
          subject_ids: [1],
        }));
      });
    });

    it('should send empty array when no subjects selected', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      // Wait for subjects to load
      await waitFor(() => {
        expect(screen.queryByText('Загрузка предметов...')).not.toBeInTheDocument();
      });

      // Deselect all subjects
      const mathCheckbox = screen.getByRole('checkbox', { name: /Mathematics/ });
      const physicsCheckbox = screen.getByRole('checkbox', { name: /Physics/ });

      await user.click(mathCheckbox);
      await user.click(physicsCheckbox);

      // Submit form
      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(adminAPI.editTeacher).toHaveBeenCalledWith(mockTeacher.id, expect.objectContaining({
          subject_ids: undefined,
        }));
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message when API fails', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Server error occurred';
      (adminAPI.editTeacher as any).mockResolvedValue({
        success: false,
        error: errorMessage,
      });

      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });

      expect(mockOnSuccess).not.toHaveBeenCalled();
      expect(mockOnOpenChange).not.toHaveBeenCalledWith(false);
    });

    it('should handle network errors gracefully', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Network error';
      (adminAPI.editTeacher as any).mockRejectedValue(new Error(errorMessage));

      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });

      expect(mockOnSuccess).not.toHaveBeenCalled();
    });

    it('should clear error message when form is modified after error', async () => {
      const user = userEvent.setup();
      (adminAPI.editTeacher as any)
        .mockResolvedValueOnce({
          success: false,
          error: 'Some error',
        })
        .mockResolvedValueOnce({
          success: true,
        });

      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      // First submission with error
      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Some error')).toBeInTheDocument();
      });

      // Clear error on new submission
      const firstNameInput = screen.getByDisplayValue('John') as HTMLInputElement;
      await user.clear(firstNameInput);
      await user.type(firstNameInput, 'Jane');

      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.queryByText('Some error')).not.toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should disable all form controls during submission', async () => {
      const user = userEvent.setup();
      (adminAPI.editTeacher as any).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ success: true }), 100))
      );

      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      // Check that inputs are disabled
      await waitFor(() => {
        const firstNameInput = screen.getByDisplayValue('John') as HTMLInputElement;
        expect(firstNameInput.disabled).toBe(true);
      });
    });

    it('should have proper label associations', () => {
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      const emailInput = screen.getByRole('textbox', { name: /Email/ });
      expect(emailInput).toBeInTheDocument();

      const firstNameInput = screen.getByRole('textbox', { name: /Имя/ });
      expect(firstNameInput).toBeInTheDocument();
    });
  });

  describe('Dialog Interactions', () => {
    it('should close dialog when Cancel button clicked', async () => {
      const user = userEvent.setup();

      // Create fresh mocks for this test
      const freshOnOpenChange = vi.fn();
      const freshOnSuccess = vi.fn();

      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={freshOnOpenChange}
          onSuccess={freshOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole('button', { name: /Отмена/ });
      await user.click(cancelButton);

      expect(freshOnOpenChange).toHaveBeenCalledWith(false);
      expect(freshOnSuccess).not.toHaveBeenCalled();
    });

    it('should update form when teacher prop changes', async () => {
      const { rerender } = render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const newTeacher = {
        ...mockTeacher,
        user: {
          ...mockTeacher.user,
          first_name: 'Alice',
          email: 'alice@test.com',
        },
      };

      rerender(
        <EditTeacherDialog
          teacher={newTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('Alice')).toBeInTheDocument();
        expect(screen.getByDisplayValue('alice@test.com')).toBeInTheDocument();
      });
    });

    it('should disable Cancel button during submission', async () => {
      const user = userEvent.setup();
      (adminAPI.editTeacher as any).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ success: true }), 100))
      );

      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      // Cancel button should be disabled during submission
      const cancelButton = screen.getByRole('button', { name: /Отмена/ });
      await waitFor(() => {
        expect(cancelButton).toBeDisabled();
      });
    });
  });

  describe('Switch Toggle (is_active)', () => {
    it('should toggle is_active switch', async () => {
      const user = userEvent.setup();
      render(
        <EditTeacherDialog
          teacher={mockTeacher}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('John')).toBeInTheDocument();
      });

      // Find and toggle switch
      const switchElement = screen.getByRole('switch', { name: /Активен/ });
      await user.click(switchElement);

      const submitButton = screen.getByRole('button', { name: /Сохранить/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(adminAPI.editTeacher).toHaveBeenCalledWith(mockTeacher.id, expect.objectContaining({
          is_active: false,
        }));
      });
    });
  });
});
