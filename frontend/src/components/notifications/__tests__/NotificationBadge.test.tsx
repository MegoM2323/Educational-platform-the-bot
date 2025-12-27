import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { NotificationBadge } from '../NotificationBadge';
import * as useNotificationCenterModule from '@/hooks/useNotificationCenter';
import * as useAuthModule from '@/contexts/AuthContext';

// Mock hooks
vi.mock('@/hooks/useNotificationCenter');
vi.mock('@/contexts/AuthContext');
vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  },
}));

const mockUser = { id: 1, email: 'test@test.com', name: 'Test User' };

const mockNotifications = [
  {
    id: 1,
    title: 'New Assignment',
    message: 'You have a new assignment to submit',
    type: 'assignment_submitted',
    priority: 'normal' as const,
    created_at: new Date().toISOString(),
    is_read: false,
    is_sent: true,
  },
  {
    id: 2,
    title: 'Message from Teacher',
    message: 'Great work on the last assignment!',
    type: 'message_new',
    priority: 'normal' as const,
    created_at: new Date().toISOString(),
    is_read: false,
    is_sent: true,
  },
  {
    id: 3,
    title: 'Material Update',
    message: 'New learning material available',
    type: 'material_feedback',
    priority: 'high' as const,
    created_at: new Date().toISOString(),
    is_read: true,
    is_sent: true,
  },
];

const createMockHookReturn = (overrides = {}) => ({
  notifications: mockNotifications,
  isLoading: false,
  error: null,
  page: 1,
  setPage: vi.fn(),
  pageSize: 20,
  totalCount: 3,
  unreadCount: 2,
  filters: {},
  setFilters: vi.fn(),
  markAsRead: vi.fn(),
  markMultipleAsRead: vi.fn(),
  deleteNotification: vi.fn(),
  deleteMultiple: vi.fn(),
  refetch: vi.fn(),
  ...overrides,
});

describe('NotificationBadge Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock useAuth
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      user: mockUser,
      loading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      register: vi.fn(),
      updateProfile: vi.fn(),
    } as any);

    // Mock useNotificationCenter
    vi.mocked(useNotificationCenterModule.useNotificationCenter).mockReturnValue(
      createMockHookReturn() as any
    );

    // Mock WebSocket
    global.WebSocket = vi.fn(() => ({
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: vi.fn(),
      close: vi.fn(),
    })) as any;
  });

  describe('Rendering', () => {
    it('should not render when unreadCount is 0 and showZero is false', () => {
      vi.mocked(useNotificationCenterModule.useNotificationCenter).mockReturnValueOnce(
        createMockHookReturn({ unreadCount: 0, notifications: [] }) as any
      );

      const { container } = render(<NotificationBadge showZero={false} />);
      expect(container.firstChild).toBeNull();
    });

    it('should render badge with unread count', () => {
      render(<NotificationBadge />);
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('should render "99+" when count exceeds 99', () => {
      vi.mocked(useNotificationCenterModule.useNotificationCenter).mockReturnValueOnce(
        createMockHookReturn({ unreadCount: 150 }) as any
      );

      render(<NotificationBadge />);
      expect(screen.getByText('99+')).toBeInTheDocument();
    });

    it('should render when showZero is true and count is 0', () => {
      vi.mocked(useNotificationCenterModule.useNotificationCenter).mockReturnValueOnce(
        createMockHookReturn({ unreadCount: 0, notifications: [] }) as any
      );

      render(<NotificationBadge showZero={true} />);
      expect(screen.getByText('0')).toBeInTheDocument();
    });
  });

  describe('Variants', () => {
    it('should render icon variant correctly', () => {
      render(<NotificationBadge variant="icon" />);
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('should render compact variant correctly', () => {
      render(<NotificationBadge variant="compact" />);
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('should render default variant with label', () => {
      render(<NotificationBadge variant="default" />);
      expect(screen.getByText('Notifications')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  describe('Preview Popover', () => {
    it('should show preview on hover when showPreview is true', async () => {
      render(<NotificationBadge showPreview={true} />);

      const badgeContainer = screen.getByText('Notifications').parentElement;
      fireEvent.mouseEnter(badgeContainer!);

      await waitFor(() => {
        expect(screen.getByText('Latest Notifications')).toBeInTheDocument();
      });
    });

    it('should not show preview when showPreview is false', () => {
      render(<NotificationBadge showPreview={false} />);

      const badgeContainer = screen.getByText('Notifications').parentElement;
      fireEvent.mouseEnter(badgeContainer!);

      expect(screen.queryByText('Latest Notifications')).not.toBeInTheDocument();
    });

    it('should display preview notifications limited by previewCount', async () => {
      render(<NotificationBadge showPreview={true} previewCount={2} />);

      const badgeContainer = screen.getByText('Notifications').parentElement;
      fireEvent.mouseEnter(badgeContainer!);

      await waitFor(() => {
        expect(screen.getByText('New Assignment')).toBeInTheDocument();
        expect(screen.getByText('Message from Teacher')).toBeInTheDocument();
      });
    });

    it('should show unread badge in preview', async () => {
      render(<NotificationBadge showPreview={true} previewCount={3} />);

      const badgeContainer = screen.getByText('Notifications').parentElement;
      fireEvent.mouseEnter(badgeContainer!);

      await waitFor(() => {
        expect(screen.getByText('2 new')).toBeInTheDocument();
      });
    });

    it('should close preview on mouse leave', async () => {
      render(<NotificationBadge showPreview={true} />);

      const badgeContainer = screen.getByText('Notifications').parentElement;

      // Show preview
      fireEvent.mouseEnter(badgeContainer!);
      await waitFor(() => {
        expect(screen.getByText('Latest Notifications')).toBeInTheDocument();
      });

      // Hide preview
      fireEvent.mouseLeave(badgeContainer!);
      await waitFor(() => {
        expect(screen.queryByText('Latest Notifications')).not.toBeInTheDocument();
      });
    });

    it('should show notification type badges in preview', async () => {
      render(<NotificationBadge showPreview={true} />);

      const badgeContainer = screen.getByText('Notifications').parentElement;
      fireEvent.mouseEnter(badgeContainer!);

      await waitFor(() => {
        expect(screen.getByText(/assignment submitted/i)).toBeInTheDocument();
      });
    });
  });

  describe('Color Coding', () => {
    it('should apply correct color for low unread count', () => {
      vi.mocked(useNotificationCenterModule.useNotificationCenter).mockReturnValueOnce(
        createMockHookReturn({ unreadCount: 3 }) as any
      );

      render(<NotificationBadge />);
      const badge = screen.getByText('3');

      expect(badge.className).toContain('bg-blue-500');
    });

    it('should apply correct color for medium unread count', () => {
      vi.mocked(useNotificationCenterModule.useNotificationCenter).mockReturnValueOnce(
        createMockHookReturn({ unreadCount: 8 }) as any
      );

      render(<NotificationBadge />);
      const badge = screen.getByText('8');

      expect(badge.className).toContain('bg-yellow-500');
    });

    it('should apply correct color for high unread count', () => {
      vi.mocked(useNotificationCenterModule.useNotificationCenter).mockReturnValueOnce(
        createMockHookReturn({ unreadCount: 15 }) as any
      );

      render(<NotificationBadge />);
      const badge = screen.getByText('15');

      expect(badge.className).toContain('bg-red-500');
    });
  });

  describe('Props', () => {
    it('should accept custom className', () => {
      const { container } = render(<NotificationBadge className="custom-class" />);

      expect(container.querySelector('.custom-class')).toBeInTheDocument();
    });

    it('should respect previewCount prop', async () => {
      render(<NotificationBadge showPreview={true} previewCount={1} />);

      const badgeContainer = screen.getByText('Notifications').parentElement;
      fireEvent.mouseEnter(badgeContainer!);

      await waitFor(() => {
        const moreText = screen.queryByText(/more notification/i);
        expect(moreText).toBeInTheDocument();
      });
    });
  });

  describe('WebSocket Connection', () => {
    it('should establish WebSocket connection on mount', () => {
      render(<NotificationBadge />);

      expect(global.WebSocket).toHaveBeenCalled();
    });

    it('should use correct WebSocket URL', () => {
      render(<NotificationBadge />);

      expect(global.WebSocket).toHaveBeenCalledWith(expect.stringContaining('ws://'));
    });
  });

  describe('Responsive Sizing', () => {
    it('should have responsive classes', () => {
      const { container } = render(<NotificationBadge />);

      // Check for responsive container
      expect(container.querySelector('.relative')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper semantic structure', () => {
      render(<NotificationBadge />);

      expect(screen.getByText('Notifications')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  describe('Count Updates', () => {
    it('should display initial count correctly', () => {
      render(<NotificationBadge />);
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('should handle zero count display', () => {
      vi.mocked(useNotificationCenterModule.useNotificationCenter).mockReturnValueOnce(
        createMockHookReturn({ unreadCount: 0 }) as any
      );

      render(<NotificationBadge showZero={true} />);
      expect(screen.getByText('0')).toBeInTheDocument();
    });
  });
});
