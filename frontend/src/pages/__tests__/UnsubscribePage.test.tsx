import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { UnsubscribePage } from '../UnsubscribePage';
import * as unifiedClientModule from '@/integrations/api/unifiedClient';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock the unified API client
vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    fetch: vi.fn(),
  },
}));

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useSearchParams: () => [new URLSearchParams('token=test-token-123'), vi.fn()],
  };
});

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

const mockUnifiedAPI = unifiedClientModule.unifiedAPI as any;

const renderUnsubscribePage = () => {
  return render(
    <BrowserRouter>
      <UnsubscribePage />
    </BrowserRouter>
  );
};

describe('UnsubscribePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render the unsubscribe form with token present', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      expect(screen.getByText('Manage Notification Subscriptions')).toBeInTheDocument();
    });
  });

  it('should display all notification channels', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      expect(screen.getByText('Email Notifications')).toBeInTheDocument();
      expect(screen.getByText('Push Notifications')).toBeInTheDocument();
      expect(screen.getByText('SMS Notifications')).toBeInTheDocument();
    });
  });

  it('should display all notification types', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
      expect(screen.getByText('Learning Materials')).toBeInTheDocument();
      expect(screen.getByText('Messages')).toBeInTheDocument();
      expect(screen.getByText('Payments')).toBeInTheDocument();
      expect(screen.getByText('Invoices')).toBeInTheDocument();
      expect(screen.getByText('System Notifications')).toBeInTheDocument();
    });
  });

  it('should allow selecting notification channels', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      const emailCheckbox = screen.getByRole('checkbox', { name: /email notifications/i });
      fireEvent.click(emailCheckbox);
      expect(emailCheckbox).toBeChecked();
    });
  });

  it('should allow selecting notification types', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      const assignmentsCheckbox = screen.getByRole('checkbox', { name: /assignments/i });
      fireEvent.click(assignmentsCheckbox);
      expect(assignmentsCheckbox).toBeChecked();
    });
  });

  it('should allow unsubscribing from all notifications', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      const unsubscribeAllCheckbox = screen.getByRole('checkbox', {
        name: /unsubscribe from all notifications/i,
      });
      fireEvent.click(unsubscribeAllCheckbox);
      expect(unsubscribeAllCheckbox).toBeChecked();
    });
  });

  it('should disable individual selections when unsubscribe all is checked', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      const unsubscribeAllCheckbox = screen.getByRole('checkbox', {
        name: /unsubscribe from all notifications/i,
      });
      fireEvent.click(unsubscribeAllCheckbox);

      // Check that notification channels section is hidden (would verify visibility)
      expect(screen.queryByText('Notification Channels')).not.toBeInTheDocument();
    });
  });

  it('should submit unsubscribe request with selected channels', async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({
        success: true,
        message: 'Successfully unsubscribed',
        disabled_types: ['email'],
        user_email: 'test@example.com',
      }),
    };

    mockUnifiedAPI.fetch.mockResolvedValueOnce(mockResponse);

    renderUnsubscribePage();

    await waitFor(() => {
      const emailCheckbox = screen.getByRole('checkbox', { name: /email notifications/i });
      fireEvent.click(emailCheckbox);
    });

    const submitButton = screen.getByRole('button', { name: /confirm unsubscribe/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockUnifiedAPI.fetch).toHaveBeenCalledWith(
        '/notifications/unsubscribe/',
        'POST',
        expect.objectContaining({
          token: 'test-token-123',
        })
      );
    });
  });

  it('should submit unsubscribe request for all notifications', async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({
        success: true,
        message: 'Successfully unsubscribed from all',
        disabled_types: ['all'],
        user_email: 'test@example.com',
      }),
    };

    mockUnifiedAPI.fetch.mockResolvedValueOnce(mockResponse);

    renderUnsubscribePage();

    await waitFor(() => {
      const unsubscribeAllCheckbox = screen.getByRole('checkbox', {
        name: /unsubscribe from all notifications/i,
      });
      fireEvent.click(unsubscribeAllCheckbox);
    });

    const submitButton = screen.getByRole('button', { name: /confirm unsubscribe/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockUnifiedAPI.fetch).toHaveBeenCalledWith(
        '/notifications/unsubscribe/',
        'POST',
        expect.objectContaining({
          token: 'test-token-123',
          unsubscribe_from: ['all'],
        })
      );
    });
  });

  it('should display success message after successful unsubscribe', async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({
        success: true,
        message: 'Successfully unsubscribed',
        disabled_types: ['assignments'],
        user_email: 'test@example.com',
      }),
    };

    mockUnifiedAPI.fetch.mockResolvedValueOnce(mockResponse);

    renderUnsubscribePage();

    await waitFor(() => {
      const assignmentsCheckbox = screen.getByRole('checkbox', { name: /assignments/i });
      fireEvent.click(assignmentsCheckbox);
    });

    const submitButton = screen.getByRole('button', { name: /confirm unsubscribe/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Successfully Unsubscribed')).toBeInTheDocument();
      expect(screen.getByText(/Your notification preferences have been updated/i)).toBeInTheDocument();
    });
  });

  it('should display error message on failed unsubscribe', async () => {
    const mockResponse = {
      ok: false,
      status: 400,
      json: async () => ({
        error: 'Invalid token',
      }),
    };

    mockUnifiedAPI.fetch.mockResolvedValueOnce(mockResponse);

    renderUnsubscribePage();

    await waitFor(() => {
      const assignmentsCheckbox = screen.getByRole('checkbox', { name: /assignments/i });
      fireEvent.click(assignmentsCheckbox);
    });

    const submitButton = screen.getByRole('button', { name: /confirm unsubscribe/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid token/i)).toBeInTheDocument();
    });
  });

  it('should show error when no options selected', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      const submitButton = screen.getByRole('button', { name: /confirm unsubscribe/i });
      // Button should be disabled initially
      expect(submitButton).toBeDisabled();
    });
  });

  it('should enable submit button when channel selected', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      const emailCheckbox = screen.getByRole('checkbox', { name: /email notifications/i });
      fireEvent.click(emailCheckbox);
    });

    const submitButton = screen.getByRole('button', { name: /confirm unsubscribe/i });
    expect(submitButton).not.toBeDisabled();
  });

  it('should enable submit button when notification type selected', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      const assignmentsCheckbox = screen.getByRole('checkbox', { name: /assignments/i });
      fireEvent.click(assignmentsCheckbox);
    });

    const submitButton = screen.getByRole('button', { name: /confirm unsubscribe/i });
    expect(submitButton).not.toBeDisabled();
  });

  it('should display user email in success state', async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({
        success: true,
        message: 'Successfully unsubscribed',
        disabled_types: ['assignments'],
        user_email: 'john.doe@example.com',
      }),
    };

    mockUnifiedAPI.fetch.mockResolvedValueOnce(mockResponse);

    renderUnsubscribePage();

    await waitFor(() => {
      const assignmentsCheckbox = screen.getByRole('checkbox', { name: /assignments/i });
      fireEvent.click(assignmentsCheckbox);
    });

    const submitButton = screen.getByRole('button', { name: /confirm unsubscribe/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('john.doe@example.com')).toBeInTheDocument();
    });
  });

  it('should have responsive layout for mobile', async () => {
    renderUnsubscribePage();

    await waitFor(() => {
      const form = screen.getByRole('button', { name: /confirm unsubscribe/i }).closest('form');
      expect(form).toBeInTheDocument();

      // Check that grid layout classes are present for responsive design
      const typeSection = screen.getByText('Notification Types').parentElement;
      expect(typeSection?.className).toMatch(/grid/);
    });
  });
});
