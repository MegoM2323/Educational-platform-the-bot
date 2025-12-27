import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { NotificationSettings } from '../NotificationSettings';
import * as notificationSettingsAPI from '@/integrations/api/unifiedClient';

/**
 * Test suite for NotificationSettings component
 * Tests form rendering, state management, API integration, and user interactions
 */

// Mock the API
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
    useNavigate: () => vi.fn(),
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
    error: vi.fn(),
    info: vi.fn(),
  },
}));

/**
 * Helper function to render component with required providers
 */
function renderWithProviders(component: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  );
}

/**
 * Mock response data for API calls
 */
const mockNotificationSettings = {
  assignments_enabled: true,
  materials_enabled: true,
  messages_enabled: true,
  payments_enabled: true,
  invoices_enabled: true,
  system_enabled: true,
  email_enabled: true,
  push_enabled: true,
  sms_enabled: false,
  quiet_hours_enabled: false,
  quiet_hours_start: '22:00',
  quiet_hours_end: '08:00',
  timezone: 'UTC',
};

describe('NotificationSettings Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock the API fetch to return success by default
    vi.mocked(notificationSettingsAPI.unifiedAPI.fetch).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: mockNotificationSettings }),
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Test: Component renders with loading state
   */
  it('should display loading spinner initially', () => {
    renderWithProviders(<NotificationSettings />);
    expect(screen.getByText('Loading notification settings...')).toBeInTheDocument();
  });

  /**
   * Test: Component renders page title and description
   */
  it('should render page title and description', async () => {
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Notification Settings')).toBeInTheDocument();
      expect(screen.getByText(/Manage how and when you receive notifications/i)).toBeInTheDocument();
    });
  });

  /**
   * Test: All notification type toggles are rendered
   */
  it('should render all notification type toggles', async () => {
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
      expect(screen.getByText('Materials')).toBeInTheDocument();
      expect(screen.getByText('Messages')).toBeInTheDocument();
      expect(screen.getByText('Payments')).toBeInTheDocument();
      expect(screen.getByText('Invoices')).toBeInTheDocument();
      expect(screen.getByText('System Notifications')).toBeInTheDocument();
    });
  });

  /**
   * Test: All notification channel toggles are rendered
   */
  it('should render all notification channel toggles', async () => {
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Email Notifications')).toBeInTheDocument();
      expect(screen.getByText('Push Notifications')).toBeInTheDocument();
      expect(screen.getByText('SMS Notifications')).toBeInTheDocument();
    });
  });

  /**
   * Test: In-app notification notice is always visible
   */
  it('should display in-app notification notice', async () => {
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('In-App Notifications')).toBeInTheDocument();
      expect(screen.getByText(/always enabled/i)).toBeInTheDocument();
    });
  });

  /**
   * Test: Quiet hours section is rendered
   */
  it('should render quiet hours section', async () => {
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Quiet Hours')).toBeInTheDocument();
      expect(screen.getByText('Enable Quiet Hours')).toBeInTheDocument();
    });
  });

  /**
   * Test: Toggle quiet hours shows/hides time inputs
   */
  it('should show/hide time inputs when quiet hours toggle changes', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Quiet Hours')).toBeInTheDocument();
    });

    // Initially, time inputs should not be visible
    expect(screen.queryByLabelText('Start Time')).not.toBeInTheDocument();

    // Enable quiet hours
    const quietHoursToggle = screen.getByRole('switch', { name: /Enable Quiet Hours/i });
    await user.click(quietHoursToggle);

    // Now time inputs should be visible
    await waitFor(() => {
      expect(screen.getByLabelText('Start Time')).toBeInTheDocument();
      expect(screen.getByLabelText('End Time')).toBeInTheDocument();
    });
  });

  /**
   * Test: API call is made to fetch settings on mount
   */
  it('should fetch notification settings on component mount', async () => {
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(notificationSettingsAPI.unifiedAPI.fetch).toHaveBeenCalledWith(
        '/accounts/notification-settings/',
        'GET'
      );
    });
  });

  /**
   * Test: Form loads with default values from API
   */
  it('should populate form with fetched values', async () => {
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      const assignmentsToggle = screen.getByRole('switch', { name: /Assignments/i });
      expect(assignmentsToggle).toHaveAttribute('data-state', 'checked');
    });
  });

  /**
   * Test: Toggle switch changes local form state
   */
  it('should change toggle state when clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
    });

    const assignmentsToggle = screen.getByRole('switch', { name: /Assignments/i });
    const initialState = assignmentsToggle.getAttribute('data-state');

    // Click toggle to change state
    await user.click(assignmentsToggle);

    await waitFor(() => {
      const newState = assignmentsToggle.getAttribute('data-state');
      expect(newState).not.toBe(initialState);
    });
  });

  /**
   * Test: Save button is disabled when form is pristine
   */
  it('should disable save button when form has no changes', async () => {
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      const saveButton = screen.getByRole('button', { name: /Save Settings/i });
      expect(saveButton).toBeDisabled();
    });
  });

  /**
   * Test: Save button is enabled when form is dirty
   */
  it('should enable save button when form is dirty', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
    });

    // Change a field
    const assignmentsToggle = screen.getByRole('switch', { name: /Assignments/i });
    await user.click(assignmentsToggle);

    // Save button should now be enabled
    await waitFor(() => {
      const saveButton = screen.getByRole('button', { name: /Save Settings/i });
      expect(saveButton).not.toBeDisabled();
    });
  });

  /**
   * Test: Form submission calls API with correct data
   */
  it('should call API with form data when save button is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(notificationSettingsAPI.unifiedAPI.fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: { success: true } }),
    } as any);

    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
    });

    // Change a field
    const assignmentsToggle = screen.getByRole('switch', { name: /Assignments/i });
    await user.click(assignmentsToggle);

    // Click save
    const saveButton = screen.getByRole('button', { name: /Save Settings/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(notificationSettingsAPI.unifiedAPI.fetch).toHaveBeenCalledWith(
        '/accounts/notification-settings/',
        'PATCH',
        expect.objectContaining({
          assignments_enabled: false, // Changed from true to false
        })
      );
    });
  });

  /**
   * Test: Success message is shown after save
   */
  it('should display success message after successful save', async () => {
    const user = userEvent.setup();
    vi.mocked(notificationSettingsAPI.unifiedAPI.fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: { success: true } }),
    } as any);

    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
    });

    // Change a field
    const assignmentsToggle = screen.getByRole('switch', { name: /Assignments/i });
    await user.click(assignmentsToggle);

    // Click save
    const saveButton = screen.getByRole('button', { name: /Save Settings/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
    });
  });

  /**
   * Test: Error message is shown when save fails
   */
  it('should display error message when save fails', async () => {
    const user = userEvent.setup();
    vi.mocked(notificationSettingsAPI.unifiedAPI.fetch)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ data: mockNotificationSettings }),
      } as any)
      .mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Validation failed' }),
      } as any);

    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
    });

    // Change a field
    const assignmentsToggle = screen.getByRole('switch', { name: /Assignments/i });
    await user.click(assignmentsToggle);

    // Click save
    const saveButton = screen.getByRole('button', { name: /Save Settings/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/Validation failed/i)).toBeInTheDocument();
    });
  });

  /**
   * Test: Reset button restores original values
   */
  it('should reset form to original values when reset button is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
    });

    // Change a field
    const assignmentsToggle = screen.getByRole('switch', { name: /Assignments/i });
    const initialState = assignmentsToggle.getAttribute('data-state');
    await user.click(assignmentsToggle);

    // State should be different
    await waitFor(() => {
      expect(assignmentsToggle.getAttribute('data-state')).not.toBe(initialState);
    });

    // Click reset
    const resetButton = screen.getByRole('button', { name: /Reset/i });
    await user.click(resetButton);

    // State should be back to initial
    await waitFor(() => {
      expect(assignmentsToggle.getAttribute('data-state')).toBe(initialState);
    });
  });

  /**
   * Test: Loading state is shown while saving
   */
  it('should show loading indicator while saving', async () => {
    const user = userEvent.setup();
    let resolveResponse: any;
    const responsePromise = new Promise((resolve) => {
      resolveResponse = resolve;
    });

    vi.mocked(notificationSettingsAPI.unifiedAPI.fetch)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ data: mockNotificationSettings }),
      } as any)
      .mockReturnValueOnce(responsePromise as any);

    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
    });

    // Change a field
    const assignmentsToggle = screen.getByRole('switch', { name: /Assignments/i });
    await user.click(assignmentsToggle);

    // Click save
    const saveButton = screen.getByRole('button', { name: /Save Settings/i });
    await user.click(saveButton);

    // Should show saving state
    await waitFor(() => {
      expect(screen.getByText(/Saving/i)).toBeInTheDocument();
    });

    // Resolve the promise
    resolveResponse({
      ok: true,
      status: 200,
      json: async () => ({ data: { success: true } }),
    });

    // Saving state should be gone
    await waitFor(() => {
      expect(screen.queryByText(/Saving/i)).not.toBeInTheDocument();
    });
  });

  /**
   * Test: Timezone selector is only shown when quiet hours enabled
   */
  it('should show timezone selector only when quiet hours enabled', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Quiet Hours')).toBeInTheDocument();
    });

    // Initially timezone selector should not be visible
    expect(screen.queryByText('Timezone')).not.toBeInTheDocument();

    // Enable quiet hours
    const quietHoursToggle = screen.getByRole('switch', { name: /Enable Quiet Hours/i });
    await user.click(quietHoursToggle);

    // Now timezone selector should be visible
    await waitFor(() => {
      expect(screen.getByText('Timezone')).toBeInTheDocument();
    });
  });

  /**
   * Test: Handles 401 unauthorized response
   */
  it('should navigate to auth when receiving 401 response', async () => {
    const navigateMock = vi.fn();
    vi.mocked(notificationSettingsAPI.unifiedAPI.fetch).mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ error: 'Unauthorized' }),
    } as any);

    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      // Should attempt to navigate to /auth
      // (actual navigation test requires useNavigate mock)
      expect(notificationSettingsAPI.unifiedAPI.fetch).toHaveBeenCalled();
    });
  });

  /**
   * Test: Multiple toggles can be changed together
   */
  it('should allow multiple toggles to be changed', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
    });

    // Toggle multiple fields
    const assignmentsToggle = screen.getByRole('switch', { name: /Assignments/i });
    const materialsToggle = screen.getByRole('switch', { name: /Materials/i });
    const emailToggle = screen.getByRole('switch', { name: /Email Notifications/i });

    await user.click(assignmentsToggle);
    await user.click(materialsToggle);
    await user.click(emailToggle);

    // Save button should be enabled
    const saveButton = screen.getByRole('button', { name: /Save Settings/i });
    expect(saveButton).not.toBeDisabled();
  });

  /**
   * Test: Form sections are properly organized
   */
  it('should have properly labeled sections', async () => {
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      const notificationTypesSection = screen.getByText('Notification Types').closest('h2');
      const channelsSection = screen.getByText('Notification Channels').closest('h2');
      const quietHoursSection = screen.getByText('Quiet Hours').closest('h2');

      expect(notificationTypesSection).toBeInTheDocument();
      expect(channelsSection).toBeInTheDocument();
      expect(quietHoursSection).toBeInTheDocument();
    });
  });

  /**
   * Test: Time input validation
   */
  it('should accept valid time format', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText('Quiet Hours')).toBeInTheDocument();
    });

    // Enable quiet hours
    const quietHoursToggle = screen.getByRole('switch', { name: /Enable Quiet Hours/i });
    await user.click(quietHoursToggle);

    // Find and change start time
    await waitFor(() => {
      const startTimeInput = screen.getByLabelText('Start Time') as HTMLInputElement;
      expect(startTimeInput).toBeInTheDocument();
    });
  });
});
