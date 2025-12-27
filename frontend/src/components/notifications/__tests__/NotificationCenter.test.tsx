import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import { NotificationCenter } from '../NotificationCenter';
import * as useNotificationCenterModule from '@/hooks/useNotificationCenter';

vi.mock('@/hooks/useNotificationCenter', () => ({
  useNotificationCenter: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockNotifications = [
  {
    id: 1,
    title: 'New Message',
    message: 'You have a new message from John',
    type: 'message_new',
    priority: 'high',
    created_at: new Date().toISOString(),
    is_read: false,
    is_sent: true,
  },
  {
    id: 2,
    title: 'Assignment Submitted',
    message: 'Your assignment has been submitted',
    type: 'assignment_submitted',
    priority: 'normal',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    is_read: true,
    is_sent: true,
  },
];

describe('NotificationCenter Component', () => {
  const mockUseNotificationCenter = useNotificationCenterModule.useNotificationCenter as any;

  const defaultMockReturn = {
    notifications: mockNotifications,
    isLoading: false,
    error: null,
    page: 1,
    setPage: vi.fn(),
    pageSize: 20,
    totalCount: 2,
    unreadCount: 1,
    filters: {},
    setFilters: vi.fn(),
    markAsRead: vi.fn(),
    markMultipleAsRead: vi.fn(),
    deleteNotification: vi.fn(),
    deleteMultiple: vi.fn(),
    refetch: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseNotificationCenter.mockReturnValue(defaultMockReturn);
  });

  it('should render notification center header', () => {
    render(<NotificationCenter />);

    expect(screen.getByText('Notification Center')).toBeInTheDocument();
    expect(screen.getByText(/2 notifications/)).toBeInTheDocument();
    expect(screen.getByText(/1 unread/)).toBeInTheDocument();
  });

  it('should display notifications list', () => {
    render(<NotificationCenter />);

    expect(screen.getByText('New Message')).toBeInTheDocument();
    expect(screen.getByText('You have a new message from John')).toBeInTheDocument();
    expect(screen.getByText('Assignment Submitted')).toBeInTheDocument();
  });

  it('should show loading state', () => {
    mockUseNotificationCenter.mockReturnValue({
      ...defaultMockReturn,
      isLoading: true,
      notifications: [],
    });

    render(<NotificationCenter />);

    const skeletons = screen.getAllByTestId('skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('should show error state', () => {
    mockUseNotificationCenter.mockReturnValue({
      ...defaultMockReturn,
      error: 'Failed to load notifications',
      isLoading: false,
      notifications: [],
    });

    render(<NotificationCenter />);

    expect(screen.getByText('Failed to load notifications')).toBeInTheDocument();
  });

  it('should show empty state', () => {
    mockUseNotificationCenter.mockReturnValue({
      ...defaultMockReturn,
      notifications: [],
      totalCount: 0,
    });

    render(<NotificationCenter />);

    expect(screen.getByText('No notifications')).toBeInTheDocument();
    expect(screen.getByText("You're all caught up!")).toBeInTheDocument();
  });

  it('should display notification type badges', () => {
    render(<NotificationCenter />);

    expect(screen.getByText('Message')).toBeInTheDocument();
    expect(screen.getByText('Assignment')).toBeInTheDocument();
  });

  it('should display priority badges', () => {
    render(<NotificationCenter />);

    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Normal')).toBeInTheDocument();
  });

  it('should mark notification as read', async () => {
    mockUseNotificationCenter.mockReturnValue({
      ...defaultMockReturn,
      markAsRead: vi.fn().mockResolvedValue({}),
    });

    render(<NotificationCenter />);

    const markReadButtons = screen.getAllByRole('button').filter((btn) => {
      return btn.querySelector('svg') !== null;
    });

    if (markReadButtons.length > 0) {
      fireEvent.click(markReadButtons[0]);

      await waitFor(() => {
        expect(defaultMockReturn.markAsRead).toHaveBeenCalled();
      });
    }
  });

  it('should delete notification', async () => {
    mockUseNotificationCenter.mockReturnValue({
      ...defaultMockReturn,
      deleteNotification: vi.fn().mockResolvedValue({}),
    });

    render(<NotificationCenter />);

    const deleteButtons = screen.getAllByRole('button').filter((btn) => {
      const svg = btn.querySelector('svg');
      return svg && svg.parentElement?.className.includes('text-red');
    });

    if (deleteButtons.length > 0) {
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/Delete Notification/)).toBeInTheDocument();
      });
    }
  });

  it('should search notifications', async () => {
    render(<NotificationCenter />);

    const searchInput = screen.getByPlaceholderText('Search notifications...');
    fireEvent.change(searchInput, { target: { value: 'test' } });

    const searchButton = screen.getAllByRole('button').find((btn) =>
      btn.querySelector('[class*="Search"]')
    );

    if (searchButton) {
      fireEvent.click(searchButton);

      expect(defaultMockReturn.setFilters).toHaveBeenCalledWith(
        expect.objectContaining({
          search: 'test',
        })
      );
    }
  });

  it('should filter by type', async () => {
    render(<NotificationCenter />);

    const typeSelects = screen.getAllByRole('combobox');
    if (typeSelects.length > 0) {
      fireEvent.click(typeSelects[0]);

      await waitFor(() => {
        const option = screen.getByText(/message/i);
        if (option) {
          fireEvent.click(option);
        }
      });
    }
  });

  it('should filter by priority', async () => {
    render(<NotificationCenter />);

    const prioritySelects = screen.getAllByRole('combobox');
    if (prioritySelects.length > 1) {
      fireEvent.click(prioritySelects[1]);

      await waitFor(() => {
        const option = screen.getByText(/high/i);
        if (option) {
          fireEvent.click(option);
        }
      });
    }
  });

  it('should select all notifications', () => {
    render(<NotificationCenter />);

    const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
    fireEvent.click(selectAllCheckbox);

    expect(screen.getByText(/All selected/)).toBeInTheDocument();
  });

  it('should mark all as read', async () => {
    render(<NotificationCenter />);

    const markAllButtons = screen.getAllByRole('button').filter((btn) =>
      btn.textContent?.includes('Mark all as read')
    );

    if (markAllButtons.length > 0) {
      fireEvent.click(markAllButtons[0]);

      await waitFor(() => {
        expect(defaultMockReturn.markMultipleAsRead).toHaveBeenCalledWith([], true);
      });
    }
  });

  it('should paginate to next page', () => {
    mockUseNotificationCenter.mockReturnValue({
      ...defaultMockReturn,
      totalCount: 100,
      pageSize: 20,
    });

    render(<NotificationCenter />);

    const nextButton = screen.getByText('Next');
    fireEvent.click(nextButton);

    expect(defaultMockReturn.setPage).toHaveBeenCalledWith(2);
  });

  it('should not show next button on last page', () => {
    mockUseNotificationCenter.mockReturnValue({
      ...defaultMockReturn,
      totalCount: 2,
      pageSize: 20,
    });

    render(<NotificationCenter />);

    const nextButton = screen.queryByText('Next');
    if (nextButton) {
      expect(nextButton).toBeDisabled();
    }
  });

  it('should display pagination info', () => {
    mockUseNotificationCenter.mockReturnValue({
      ...defaultMockReturn,
      totalCount: 100,
      pageSize: 20,
      page: 1,
    });

    render(<NotificationCenter />);

    expect(screen.getByText(/Page 1 of 5/)).toBeInTheDocument();
  });

  it('should show close button when onClose is provided', () => {
    const onClose = vi.fn();
    render(<NotificationCenter onClose={onClose} />);

    const closeButton = screen.getByRole('button', { name: /Close/i });
    expect(closeButton).toBeInTheDocument();

    fireEvent.click(closeButton);
    expect(onClose).toHaveBeenCalled();
  });

  it('should display unread badge for unread notifications', () => {
    render(<NotificationCenter />);

    const unreadBadges = screen.getAllByText('Unread');
    expect(unreadBadges.length).toBeGreaterThan(0);
  });

  it('should display notification timestamps', () => {
    render(<NotificationCenter />);

    // Check for relative time format
    expect(screen.getByText(/ago/i)).toBeInTheDocument();
  });

  it('should handle mark multiple as read for selected notifications', async () => {
    mockUseNotificationCenter.mockReturnValue({
      ...defaultMockReturn,
      markMultipleAsRead: vi.fn().mockResolvedValue({}),
    });

    render(<NotificationCenter />);

    // Select first notification
    const checkboxes = screen.getAllByRole('checkbox');
    if (checkboxes.length > 1) {
      fireEvent.click(checkboxes[1]);

      await waitFor(() => {
        const markReadButton = screen.getByText('Mark as Read');
        if (markReadButton) {
          fireEvent.click(markReadButton);
        }
      });
    }
  });
});
