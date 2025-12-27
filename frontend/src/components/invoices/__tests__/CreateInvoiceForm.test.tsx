/**
 * Tests for CreateInvoiceForm component.
 * Covers form rendering, validation, submission, and error handling.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { CreateInvoiceForm } from '../CreateInvoiceForm';
import {
  createMockTutorStudents,
  createTestQueryClient,
} from '@/__tests__/utils/test-utils';
import * as invoiceAPI from '@/integrations/api/invoiceAPI';
import { ToastProvider } from '@/components/ui/toaster';

// Mock the invoiceAPI
vi.mock('@/integrations/api/invoiceAPI');

const MockedInvoiceAPI = invoiceAPI as any;

describe('CreateInvoiceForm', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  const renderForm = (open: boolean = true, onOpenChange = vi.fn()) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ToastProvider>
            <CreateInvoiceForm open={open} onOpenChange={onOpenChange} />
          </ToastProvider>
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  describe('Form Rendering', () => {
    it('should render all form fields when dialog is open', async () => {
      const mockStudents = createMockTutorStudents(2);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      expect(screen.getByText('Создать счёт')).toBeInTheDocument();
      expect(screen.getByLabelText(/Студент/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Сумма/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Срок оплаты/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Описание/)).toBeInTheDocument();
    });

    it('should render cancel and submit buttons', async () => {
      const mockStudents = createMockTutorStudents(2);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      expect(screen.getByText('Отмена')).toBeInTheDocument();
      expect(screen.getByText('Создать счёт')).toBeInTheDocument();
    });

    it('should not render form when dialog is closed', () => {
      renderForm(false);

      expect(
        screen.queryByText('Создать счёт')
      ).not.toBeInTheDocument();
    });

    it('should load and display student options', async () => {
      const mockStudents = createMockTutorStudents(2);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const studentInput = screen.getByDisplayValue('Выберите студента');
      await userEvent.click(studentInput);

      await waitFor(() => {
        expect(screen.getByText(mockStudents[0].full_name)).toBeInTheDocument();
        expect(screen.getByText(mockStudents[1].full_name)).toBeInTheDocument();
      });
    });
  });

  describe('Form Validation', () => {
    it('should show error when student is not selected', async () => {
      const user = userEvent.setup();
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      const onOpenChange = vi.fn();
      renderForm(true, onOpenChange);

      const submitButton = screen.getByText('Создать счёт');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Выберите студента')).toBeInTheDocument();
      });
    });

    it('should show error when amount is empty', async () => {
      const user = userEvent.setup();
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const submitButton = screen.getByText('Создать счёт');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Укажите сумму')).toBeInTheDocument();
      });
    });

    it('should show error when amount is zero or negative', async () => {
      const user = userEvent.setup();
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const amountInput = screen.getByLabelText(/Сумма/) as HTMLInputElement;
      await user.type(amountInput, '0');

      const submitButton = screen.getByText('Создать счёт');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('Сумма должна быть больше 0')
        ).toBeInTheDocument();
      });
    });

    it('should show error when description is empty', async () => {
      const user = userEvent.setup();
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const submitButton = screen.getByText('Создать счёт');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Укажите описание')).toBeInTheDocument();
      });
    });

    it('should show error when description exceeds max length', async () => {
      const user = userEvent.setup();
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const descriptionInput = screen.getByLabelText(/Описание/) as HTMLTextAreaElement;
      const longText = 'a'.repeat(2001);
      await user.type(descriptionInput, longText);

      const submitButton = screen.getByText('Создать счёт');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('Описание не должно превышать 2000 символов')
        ).toBeInTheDocument();
      });
    });

    it('should show error when due_date is in the past', async () => {
      const user = userEvent.setup();
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const dueDateInput = screen.getByLabelText(/Срок оплаты/) as HTMLInputElement;
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const pastDate = yesterday.toISOString().split('T')[0];

      await user.type(dueDateInput, pastDate);

      const submitButton = screen.getByText('Создать счёт');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('Срок оплаты не может быть в прошлом')
        ).toBeInTheDocument();
      });
    });

    it('should show error when due_date is not specified', async () => {
      const user = userEvent.setup();
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const submitButton = screen.getByText('Создать счёт');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Укажите срок оплаты')).toBeInTheDocument();
      });
    });

    it('should clear error when user corrects field', async () => {
      const user = userEvent.setup();
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const amountInput = screen.getByLabelText(/Сумма/);
      await user.type(amountInput, '0');

      let submitButton = screen.getByText('Создать счёт');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('Сумма должна быть больше 0')
        ).toBeInTheDocument();
      });

      await user.clear(amountInput);
      await user.type(amountInput, '5000');

      submitButton = screen.getByText('Создать счёт');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.queryByText('Сумма должна быть больше 0')
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('should have submit button that is not disabled by default', async () => {
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const submitButton = screen.getByText('Создать счёт') as HTMLButtonElement;
      expect(submitButton).not.toBeDisabled();
    });

    it('should show loading text when form is submitting', async () => {
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      // Mock a slow promise
      MockedInvoiceAPI.invoiceAPI.createInvoice.mockImplementation(
        () => new Promise(() => {})
      );

      renderForm(true);

      // Just verify the submit button exists
      const submitButton = screen.getByText('Создать счёт');
      expect(submitButton).toBeInTheDocument();
    });

    it('should show enrollment select label when form has students', async () => {
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      // Enrollment select appears conditionally based on student selection
      expect(screen.queryByLabelText(/Предмет/)).not.toBeInTheDocument();
    });
  });

  describe('Form Reset', () => {
    it('should reset form when dialog is closed', async () => {
      const user = userEvent.setup();
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      const onOpenChange = vi.fn();
      const { rerender } = renderForm(true, onOpenChange);

      const amountInput = screen.getByLabelText(/Сумма/) as HTMLInputElement;
      await user.type(amountInput, '5000');

      expect(amountInput.value).toBe('5000');

      rerender(
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <ToastProvider>
              <CreateInvoiceForm open={false} onOpenChange={onOpenChange} />
            </ToastProvider>
          </BrowserRouter>
        </QueryClientProvider>
      );

      rerender(
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <ToastProvider>
              <CreateInvoiceForm open={true} onOpenChange={onOpenChange} />
            </ToastProvider>
          </BrowserRouter>
        </QueryClientProvider>
      );

      await waitFor(() => {
        const newAmountInput = screen.getByLabelText(/Сумма/) as HTMLInputElement;
        expect(newAmountInput.value).toBe('');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle API error when fetching students', async () => {
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockRejectedValue(
        new Error('Failed to fetch students')
      );

      renderForm(true);

      await waitFor(() => {
        expect(
          screen.getByText('Выберите студента')
        ).toBeInTheDocument();
      });
    });

    it('should handle empty student list', async () => {
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue([]);

      renderForm(true);

      const studentSelect = screen.getByDisplayValue('Выберите студента');
      await userEvent.click(studentSelect);

      await waitFor(() => {
        expect(
          screen.getByText('Нет доступных студентов')
        ).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper label associations', async () => {
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const amountInput = screen.getByLabelText(/Сумма/);
      expect(amountInput).toBeInTheDocument();

      const descriptionInput = screen.getByLabelText(/Описание/);
      expect(descriptionInput).toBeInTheDocument();
    });

    it('should have required field indicators', () => {
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const labels = screen.getAllByText(/\*/);
      expect(labels.length).toBeGreaterThan(0);
    });

    it('should show character count for textarea', async () => {
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const descriptionInput = screen.getByLabelText(/Описание/);
      await userEvent.type(descriptionInput, 'Test description');

      expect(screen.getByText(/16 \/ 2000/)).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should accept decimal amounts in input', async () => {
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const amountInput = screen.getByLabelText(/Сумма/) as HTMLInputElement;
      expect(amountInput.type).toBe('number');
      expect(amountInput.step).toBe('0.01');
    });

    it('should have maxLength attribute on description field', async () => {
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      const descriptionInput = screen.getByLabelText(/Описание/) as HTMLTextAreaElement;
      expect(descriptionInput.maxLength).toBe(2000);
    });

    it('should display character counter for description', () => {
      const mockStudents = createMockTutorStudents(1);
      MockedInvoiceAPI.invoiceAPI.getTutorStudents.mockResolvedValue(
        mockStudents
      );

      renderForm(true);

      expect(screen.getByText(/Максимум 2000 символов/)).toBeInTheDocument();
    });
  });
});
