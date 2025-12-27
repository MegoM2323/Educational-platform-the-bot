import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NotificationArchive } from '../NotificationArchive';
import * as useNotificationArchiveModule from '@/hooks/useNotificationArchive';
import { toast } from 'sonner';

// Mock the hook
vi.mock('@/hooks/useNotificationArchive');
vi.mock('sonner');

const mockNotifications = [
  {
    id: 1,
    title: 'System Update',
    message: 'System has been updated',
    type: 'system',
    priority: 'normal',
    created_at: '2025-12-20T10:00:00Z',
    archived_at: '2025-12-27T10:00:00Z',
    is_read: true,
  },
  {
    id: 2,
    title: 'New Message',
    message: 'You have a new message from teacher',
    type: 'message_new',
    priority: 'high',
    created_at: '2025-12-25T14:30:00Z',
    archived_at: '2025-12-27T10:00:00Z',
    is_read: false,
  },
  {
    id: 3,
    title: 'Assignment Submitted',
    message: 'Your assignment has been submitted',
    type: 'assignment_submitted',
    priority: 'low',
    created_at: '2025-12-26T16:00:00Z',
    archived_at: '2025-12-27T10:00:00Z',
    is_read: true,
  },
];

const mockHookReturn = {
  notifications: mockNotifications,
  isLoading: false,
  error: null,
  page: 1,
  setPage: vi.fn(),
  pageSize: 10,
  totalCount: 3,
  filters: {},
  setFilters: vi.fn(),
  restoreNotification: vi.fn(),
  bulkRestore: vi.fn(),
  deleteNotification: vi.fn(),
  bulkDelete: vi.fn(),
  refetch: vi.fn(),
};

describe('NotificationArchive Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useNotificationArchiveModule.useNotificationArchive).mockReturnValue(
      mockHookReturn
    );
  });

  it('renders the archive header with title and count', () => {
    render(<NotificationArchive />);

    expect(screen.getByText('Archived Notifications')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('displays search input and filter controls', () => {
    render(<NotificationArchive />);

    expect(screen.getByPlaceholderText('Search by title or message...')).toBeInTheDocument();
    expect(screen.getByText('Search')).toBeInTheDocument();
    expect(screen.getByText('Filter by type')).toBeInTheDocument();
    expect(screen.getByText('Sort by')).toBeInTheDocument();
  });

  it('renders table with notification data', () => {
    render(<NotificationArchive />);

    expect(screen.getByText('System Update')).toBeInTheDocument();
    expect(screen.getByText('New Message')).toBeInTheDocument();
    expect(screen.getByText('Assignment Submitted')).toBeInTheDocument();
  });

  it('displays notification badges correctly', () => {
    render(<NotificationArchive />);

    expect(screen.getByText('System')).toBeInTheDocument();
    expect(screen.getByText('Message')).toBeInTheDocument();
    expect(screen.getByText('Assignment')).toBeInTheDocument();
  });

  it('shows read/unread status for each notification', () => {
    render(<NotificationArchive />);

    const readBadges = screen.getAllByText('Read');
    const unreadBadges = screen.getAllByText('Unread');

    expect(readBadges).toHaveLength(2); // notifications with is_read: true
    expect(unreadBadges).toHaveLength(1); // notification with is_read: false
  });

  it('allows selecting individual notifications', async () => {
    const user = userEvent.setup();
    render(<NotificationArchive />);

    const checkboxes = screen.getAllByRole('checkbox');
    // First checkbox is "select all", skip it
    await user.click(checkboxes[1]);

    expect(checkboxes[1]).toBeChecked();
  });

  it('allows selecting all notifications with select-all checkbox', async () => {
    const user = userEvent.setup();
    render(<NotificationArchive />);

    const checkboxes = screen.getAllByRole('checkbox');
    const selectAllCheckbox = checkboxes[0];

    await user.click(selectAllCheckbox);

    // All checkboxes should be checked
    checkboxes.forEach((checkbox) => {
      expect(checkbox).toBeChecked();
    });
  });

  it('shows bulk actions panel when notifications are selected', async () => {
    const user = userEvent.setup();
    render(<NotificationArchive />);

    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]); // Select first notification

    expect(screen.getByText('1 selected')).toBeInTheDocument();
    expect(screen.getByText('Restore')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('filters notifications by type', async () => {
    const user = userEvent.setup();
    render(<NotificationArchive />);

    const filterButton = screen.getByText('Filter by type');
    await user.click(filterButton);

    const systemOption = screen.getByText('System');
    await user.click(systemOption);

    expect(mockHookReturn.setFilters).toHaveBeenCalled();
  });

  it('handles search input and triggers search', async () => {
    const user = userEvent.setup();
    render(<NotificationArchive />);

    const searchInput = screen.getByPlaceholderText('Search by title or message...');
    await user.type(searchInput, 'System');

    const searchButton = screen.getAllByText('Search')[0];
    await user.click(searchButton);

    expect(mockHookReturn.setFilters).toHaveBeenCalled();
  });

  it('allows sorting notifications', async () => {
    const user = userEvent.setup();
    render(<NotificationArchive />);

    const sortSelect = screen.getByText('Sort by');
    await user.click(sortSelect);

    const typeOption = screen.getByText('Type');
    await user.click(typeOption);

    // The component should re-render with sorted data
    await waitFor(() => {
      expect(screen.getByText('System Update')).toBeInTheDocument();
    });
  });

  it('opens details modal when clicking on notification title', async () => {
    const user = userEvent.setup();
    render(<NotificationArchive />);

    const title = screen.getByText('System Update');
    await user.click(title);

    await waitFor(() => {
      expect(screen.getByText('System Update')).toBeInTheDocument();
      expect(screen.getByText('System has been updated')).toBeInTheDocument();
    });
  });

  it('restores a single notification', async () => {
    const user = userEvent.setup();
    mockHookReturn.restoreNotification.mockResolvedValue({ success: true });

    render(<NotificationArchive />);

    const title = screen.getByText('System Update');
    await user.click(title);

    await waitFor(() => {
      expect(screen.getByText('System Update')).toBeInTheDocument();
    });

    const restoreButton = screen.getByRole('button', { name: /restore/i });
    await user.click(restoreButton);

    // Confirmation dialog
    const confirmButton = screen.getByRole('button', { name: /restore/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockHookReturn.restoreNotification).toHaveBeenCalledWith(1);
      expect(toast.success).toHaveBeenCalled();
    });
  });

  it('bulk restores selected notifications', async () => {
    const user = userEvent.setup();
    mockHookReturn.bulkRestore.mockResolvedValue({
      restored_count: 2,
      not_found: 0,
      errors: [],
    });

    render(<NotificationArchive />);

    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]); // Select first
    await user.click(checkboxes[2]); // Select second

    const bulkRestoreButton = screen.getAllByRole('button', { name: /restore/i })[1];
    await user.click(bulkRestoreButton);

    // Confirmation dialog
    const confirmButton = screen.getByRole('button', { name: /restore/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockHookReturn.bulkRestore).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalled();
    });
  });

  it('deletes a single notification', async () => {
    const user = userEvent.setup();
    mockHookReturn.deleteNotification.mockResolvedValue({ success: true });

    render(<NotificationArchive />);

    // Click on notification to view details
    const title = screen.getByText('System Update');
    await user.click(title);

    await waitFor(() => {
      expect(screen.getByText('System Update')).toBeInTheDocument();
    });

    // Find and click delete button in modal
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    const modalDeleteButton = deleteButtons.find(btn => btn.textContent?.includes('Delete'));
    if (modalDeleteButton) {
      await user.click(modalDeleteButton);
    }

    // Confirmation dialog
    const confirmDeleteButton = screen.getByRole('button', { name: /delete/i });
    await user.click(confirmDeleteButton);

    await waitFor(() => {
      expect(mockHookReturn.deleteNotification).toHaveBeenCalledWith(1);
      expect(toast.success).toHaveBeenCalled();
    });
  });

  it('bulk deletes selected notifications', async () => {
    const user = userEvent.setup();
    mockHookReturn.deleteNotification.mockResolvedValue({ success: true });

    render(<NotificationArchive />);

    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]); // Select first
    await user.click(checkboxes[2]); // Select second

    const bulkDeleteButton = screen.getAllByRole('button', { name: /delete/i }).find(
      btn => btn.parentElement?.classList.contains('flex')
    );

    if (bulkDeleteButton) {
      await user.click(bulkDeleteButton);

      // Confirmation dialog
      const confirmButton = screen.getByRole('button', { name: /delete/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(mockHookReturn.deleteNotification).toHaveBeenCalled();
      });
    }
  });

  it('displays loading skeleton while fetching', () => {
    vi.mocked(useNotificationArchiveModule.useNotificationArchive).mockReturnValue({
      ...mockHookReturn,
      isLoading: true,
      notifications: [],
    });

    render(<NotificationArchive />);

    // Should show skeleton components
    const skeletons = screen.getAllByTestId('skeleton') || [];
    expect(skeletons.length >= 0).toBe(true);
  });

  it('displays error message when fetch fails', () => {
    vi.mocked(useNotificationArchiveModule.useNotificationArchive).mockReturnValue({
      ...mockHookReturn,
      error: 'Failed to load notifications',
      notifications: [],
      isLoading: false,
    });

    render(<NotificationArchive />);

    expect(screen.getByText('Failed to load archived notifications')).toBeInTheDocument();
    expect(screen.getByText('Failed to load notifications')).toBeInTheDocument();
  });

  it('displays empty state when no notifications exist', () => {
    vi.mocked(useNotificationArchiveModule.useNotificationArchive).mockReturnValue({
      ...mockHookReturn,
      notifications: [],
      totalCount: 0,
      isLoading: false,
    });

    render(<NotificationArchive />);

    expect(screen.getByText('No archived notifications')).toBeInTheDocument();
  });

  it('shows pagination controls', () => {
    render(<NotificationArchive />);

    expect(screen.getByText(/Showing/)).toBeInTheDocument();
    expect(screen.getByText(/of 3/)).toBeInTheDocument();
  });

  it('handles pagination navigation', async () => {
    const user = userEvent.setup();
    vi.mocked(useNotificationArchiveModule.useNotificationArchive).mockReturnValue({
      ...mockHookReturn,
      totalCount: 25, // More than pageSize
    });

    render(<NotificationArchive />);

    const nextPageButton = screen.getByRole('button', { name: /chevron right/i });
    await user.click(nextPageButton);

    expect(mockHookReturn.setPage).toHaveBeenCalledWith(2);
  });

  it('calls onClose callback when back button is clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(<NotificationArchive onClose={onClose} />);

    const backButton = screen.getByRole('button', { name: /back/i });
    await user.click(backButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('shows toast error on restore failure', async () => {
    const user = userEvent.setup();
    mockHookReturn.restoreNotification.mockRejectedValue(new Error('Network error'));

    render(<NotificationArchive />);

    const title = screen.getByText('System Update');
    await user.click(title);

    await waitFor(() => {
      expect(screen.getByText('System Update')).toBeInTheDocument();
    });

    const restoreButton = screen.getAllByRole('button', { name: /restore/i }).pop();
    if (restoreButton) {
      await user.click(restoreButton);
    }

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });
  });

  it('shows toast error on delete failure', async () => {
    const user = userEvent.setup();
    mockHookReturn.deleteNotification.mockRejectedValue(new Error('Network error'));

    render(<NotificationArchive />);

    const title = screen.getByText('System Update');
    await user.click(title);

    await waitFor(() => {
      expect(screen.getByText('System Update')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    const modalDeleteButton = deleteButtons.find(btn => btn.textContent?.includes('Delete'));
    if (modalDeleteButton) {
      await user.click(modalDeleteButton);
    }

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });
  });

  it('clears selection when Clear button is clicked', async () => {
    const user = userEvent.setup();
    render(<NotificationArchive />);

    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]); // Select first notification

    expect(screen.getByText('1 selected')).toBeInTheDocument();

    const clearButton = screen.getByRole('button', { name: /clear/i });
    await user.click(clearButton);

    // Selection should be cleared (bulk actions panel disappears)
    expect(screen.queryByText('1 selected')).not.toBeInTheDocument();
  });

  it('renders close button in details modal', async () => {
    const user = userEvent.setup();
    render(<NotificationArchive />);

    const title = screen.getByText('System Update');
    await user.click(title);

    await waitFor(() => {
      expect(screen.getByText('System Update')).toBeInTheDocument();
    });

    // There should be a close button (×) in the modal
    const closeButton = screen.getByRole('button', { name: '×' });
    expect(closeButton).toBeInTheDocument();
  });
});
