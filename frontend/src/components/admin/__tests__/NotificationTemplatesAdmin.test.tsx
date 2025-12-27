/**
 * Tests for NotificationTemplatesAdmin component
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NotificationTemplatesAdmin } from '../NotificationTemplatesAdmin';
import * as notificationTemplatesAPI from '@/integrations/api/notificationTemplatesAPI';

// Mock the API
vi.mock('@/integrations/api/notificationTemplatesAPI');

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('NotificationTemplatesAdmin', () => {
  const mockTemplates = [
    {
      id: 1,
      name: 'New Assignment',
      description: 'Notification when new assignment is created',
      type: 'assignment_new' as const,
      type_display: 'Новое задание',
      title_template: 'Новое задание: {{title}}',
      message_template: 'У вас новое задание {{title}} по предмету {{subject}}',
      is_active: true,
      created_at: '2025-12-27T10:00:00Z',
      updated_at: '2025-12-27T10:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(notificationTemplatesAPI.notificationTemplatesAPI.getTemplates).mockResolvedValue({
      success: true,
      data: {
        count: 1,
        next: null,
        previous: null,
        results: mockTemplates,
      },
    });
  });

  it('renders the component with header', async () => {
    render(<NotificationTemplatesAdmin />);
    expect(screen.getByText('Шаблоны уведомлений')).toBeInTheDocument();
    expect(screen.getByText('Управление шаблонами для отправки уведомлений')).toBeInTheDocument();
  });

  it('loads and displays templates on mount', async () => {
    render(<NotificationTemplatesAdmin />);

    await waitFor(() => {
      expect(screen.getByText('New Assignment')).toBeInTheDocument();
    });
  });

  it('displays create button', () => {
    render(<NotificationTemplatesAdmin />);
    const createButton = screen.getByRole('button', { name: /новый шаблон/i });
    expect(createButton).toBeInTheDocument();
  });

  it('shows filters for type and status', () => {
    render(<NotificationTemplatesAdmin />);
    expect(screen.getByDisplayValue('Все типы')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Все')).toBeInTheDocument();
  });

  it('displays templates in table format', async () => {
    render(<NotificationTemplatesAdmin />);

    await waitFor(() => {
      expect(screen.getByText('New Assignment')).toBeInTheDocument();
      expect(screen.getByText('Новое задание')).toBeInTheDocument();
    });
  });

  it('shows pagination info when templates exist', async () => {
    render(<NotificationTemplatesAdmin />);

    await waitFor(() => {
      expect(screen.getByText(/Всего: 1 шаблонов/)).toBeInTheDocument();
    });
  });

  it('handles empty state when no templates found', async () => {
    vi.mocked(notificationTemplatesAPI.notificationTemplatesAPI.getTemplates).mockResolvedValue({
      success: true,
      data: {
        count: 0,
        next: null,
        previous: null,
        results: [],
      },
    });

    render(<NotificationTemplatesAdmin />);

    await waitFor(() => {
      expect(screen.getByText('Шаблоны не найдены')).toBeInTheDocument();
    });
  });

  it('displays error message on load failure', async () => {
    vi.mocked(notificationTemplatesAPI.notificationTemplatesAPI.getTemplates).mockResolvedValue({
      success: false,
      error: 'Failed to load templates',
    });

    render(<NotificationTemplatesAdmin />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load templates')).toBeInTheDocument();
    });
  });

  it('provides action buttons for each template', async () => {
    render(<NotificationTemplatesAdmin />);

    await waitFor(() => {
      const editButtons = screen.getAllByTitle('Редактировать');
      const copyButtons = screen.getAllByTitle('Скопировать');
      const deleteButtons = screen.getAllByTitle('Удалить');

      expect(editButtons.length).toBeGreaterThan(0);
      expect(copyButtons.length).toBeGreaterThan(0);
      expect(deleteButtons.length).toBeGreaterThan(0);
    });
  });
});
