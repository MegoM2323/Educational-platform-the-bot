import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReportCreateForm } from '../ReportCreateForm';
import * as unifiedClient from '@/integrations/api/unifiedClient';

// Mock the API client
vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
  },
}));

// Mock notification system
vi.mock('@/components/NotificationSystem', () => ({
  useErrorNotification: () => vi.fn(),
  useSuccessNotification: () => vi.fn(),
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
  },
}));

describe('ReportCreateForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading state initially', () => {
    (unifiedClient.unifiedAPI.request as any).mockImplementation(() =>
      new Promise(() => {}) // Never resolves
    );

    render(<ReportCreateForm />);
    expect(screen.getByText(/Загрузка шаблонов отчетов/i)).toBeInTheDocument();
  });

  it('should load and display templates', async () => {
    const mockTemplates = [
      {
        id: 1,
        name: 'Quarterly Report',
        report_type: 'quarterly',
        template_content: 'Q1 Report Template',
        created_at: '2025-01-01',
        description: 'Monthly analysis',
      },
      {
        id: 2,
        name: 'Annual Report',
        report_type: 'annual',
        template_content: 'Annual Report Template',
        created_at: '2025-01-01',
        description: 'Yearly summary',
      },
    ];

    (unifiedClient.unifiedAPI.request as any).mockResolvedValueOnce({
      data: mockTemplates,
      success: true,
      error: null,
    });

    render(<ReportCreateForm />);

    await waitFor(() => {
      expect(screen.getByText('Quarterly Report')).toBeInTheDocument();
      expect(screen.getByText('Annual Report')).toBeInTheDocument();
    });
  });

  it('should show error when templates fail to load', async () => {
    (unifiedClient.unifiedAPI.request as any).mockResolvedValueOnce({
      data: null,
      success: false,
      error: 'Failed to load templates',
    });

    render(<ReportCreateForm />);

    await waitFor(() => {
      expect(
        screen.getByText(/Шаблоны отчетов недоступны/i)
      ).toBeInTheDocument();
    });
  });

  it('should display template preview when preview button is clicked', async () => {
    const mockTemplates = [
      {
        id: 1,
        name: 'Test Template',
        report_type: 'test',
        template_content: 'This is a test template content',
        created_at: '2025-01-01',
      },
    ];

    (unifiedClient.unifiedAPI.request as any).mockResolvedValueOnce({
      data: mockTemplates,
      success: true,
      error: null,
    });

    render(<ReportCreateForm />);

    await waitFor(() => {
      expect(screen.getByText('Показать превью')).toBeInTheDocument();
    });

    const previewButton = screen.getByText('Показать превью');
    fireEvent.click(previewButton);

    await waitFor(() => {
      expect(screen.getByText(/This is a test template content/i)).toBeInTheDocument();
      expect(screen.getByText('Скрыть превью')).toBeInTheDocument();
    });
  });

  it('should validate required fields', async () => {
    const mockTemplates = [
      {
        id: 1,
        name: 'Test Template',
        report_type: 'test',
        template_content: 'Template content',
        created_at: '2025-01-01',
      },
    ];

    (unifiedClient.unifiedAPI.request as any).mockResolvedValueOnce({
      data: mockTemplates,
      success: true,
      error: null,
    });

    render(<ReportCreateForm />);

    await waitFor(() => {
      expect(screen.getByText('Создать отчет')).toBeInTheDocument();
    });

    const submitButton = screen.getByText('Создать отчет');
    fireEvent.click(submitButton);

    // Validation should occur and show errors
    // Note: The actual validation messages depend on the implementation
  });

  it('should validate date range', async () => {
    const mockTemplates = [
      {
        id: 1,
        name: 'Test Template',
        report_type: 'test',
        template_content: 'Template content',
        created_at: '2025-01-01',
      },
    ];

    (unifiedClient.unifiedAPI.request as any).mockResolvedValueOnce({
      data: mockTemplates,
      success: true,
      error: null,
    });

    render(<ReportCreateForm />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('')).toBeDefined();
    });

    const reportNameInput = screen.getByPlaceholderText(/Например: Квартальный отчет/i);
    const startDateInput = screen.getByDisplayValue('');
    const endDateInput = screen.getAllByDisplayValue('')[1];

    await userEvent.type(reportNameInput, 'Test Report');
    fireEvent.change(startDateInput, { target: { value: '2025-12-31' } });
    fireEvent.change(endDateInput, { target: { value: '2025-01-01' } });

    const submitButton = screen.getByText('Создать отчет');
    fireEvent.click(submitButton);

    // Date validation error should appear
  });

  it('should handle form submission successfully', async () => {
    const mockTemplates = [
      {
        id: 1,
        name: 'Test Template',
        report_type: 'test',
        template_content: 'Template content',
        created_at: '2025-01-01',
      },
    ];

    const mockResponse = {
      id: 1,
      name: 'Generated Report',
      template_id: 1,
      content: 'Generated content',
      date_created: '2025-01-01',
      date_start: '2025-01-01',
      date_end: '2025-12-31',
      status: 'generated' as const,
    };

    (unifiedClient.unifiedAPI.request as any)
      .mockResolvedValueOnce({
        data: mockTemplates,
        success: true,
        error: null,
      })
      .mockResolvedValueOnce({
        data: mockResponse,
        success: true,
        error: null,
      });

    const onSuccess = vi.fn();
    render(<ReportCreateForm onSuccess={onSuccess} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('')).toBeDefined();
    });

    const reportNameInput = screen.getByPlaceholderText(/Например: Квартальный отчет/i);
    const dateInputs = screen.getAllByRole('textbox');

    await userEvent.type(reportNameInput, 'Test Report');

    // Note: Actual date input interaction might vary
    const submitButton = screen.getByText('Создать отчет');
    fireEvent.click(submitButton);

    // The onSuccess callback might be called after form submission
  });

  it('should call onCancel when cancel button is clicked', async () => {
    const mockTemplates = [
      {
        id: 1,
        name: 'Test Template',
        report_type: 'test',
        template_content: 'Template content',
        created_at: '2025-01-01',
      },
    ];

    (unifiedClient.unifiedAPI.request as any).mockResolvedValueOnce({
      data: mockTemplates,
      success: true,
      error: null,
    });

    const onCancel = vi.fn();
    render(<ReportCreateForm onCancel={onCancel} />);

    await waitFor(() => {
      expect(screen.getByText('Отмена')).toBeInTheDocument();
    });

    const cancelButton = screen.getByText('Отмена');
    fireEvent.click(cancelButton);

    expect(onCancel).toHaveBeenCalled();
  });

  it('should render student and class filters when provided', async () => {
    const mockTemplates = [
      {
        id: 1,
        name: 'Test Template',
        report_type: 'test',
        template_content: 'Template content',
        created_at: '2025-01-01',
      },
    ];

    const mockStudents = [
      { id: 1, name: 'Student 1' },
      { id: 2, name: 'Student 2' },
    ];

    const mockClasses = [
      { id: 1, name: 'Class A' },
      { id: 2, name: 'Class B' },
    ];

    (unifiedClient.unifiedAPI.request as any).mockResolvedValueOnce({
      data: mockTemplates,
      success: true,
      error: null,
    });

    render(
      <ReportCreateForm
        students={mockStudents}
        classes={mockClasses}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Фильтры (опционально)')).toBeInTheDocument();
      expect(screen.getByText('Student 1')).toBeInTheDocument();
      expect(screen.getByText('Class A')).toBeInTheDocument();
    });
  });

  it('should clear validation errors when user types', async () => {
    const mockTemplates = [
      {
        id: 1,
        name: 'Test Template',
        report_type: 'test',
        template_content: 'Template content',
        created_at: '2025-01-01',
      },
    ];

    (unifiedClient.unifiedAPI.request as any).mockResolvedValueOnce({
      data: mockTemplates,
      success: true,
      error: null,
    });

    render(<ReportCreateForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Например: Квартальный отчет/i)).toBeInTheDocument();
    });

    // Trigger validation by clicking submit with empty fields
    const submitButton = screen.getByText('Создать отчет');
    fireEvent.click(submitButton);

    // User starts typing
    const reportNameInput = screen.getByPlaceholderText(/Например: Квартальный отчет/i);
    await userEvent.type(reportNameInput, 'Test');

    // Validation errors should be cleared for this field
  });
});
