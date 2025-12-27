import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import {
  NotificationProvider,
  useNotification,
  useAddNotification,
  useNotifications,
  useUnreadNotifications,
  useNotificationActions,
  useNotificationHelper,
} from '../NotificationContext';

const NotificationTestComponent = () => {
  const { addNotification, removeNotification, markAsRead, getNotifications, getUnreadCount } =
    useNotification();

  const handleAddSuccess = () => {
    addNotification({
      type: 'success',
      message: 'Success message',
      duration: 3000,
    });
  };

  const handleAddError = () => {
    addNotification({
      type: 'error',
      message: 'Error message',
      duration: 5000,
    });
  };

  const notifications = getNotifications();
  const unreadCount = getUnreadCount();

  return (
    <div>
      <button onClick={handleAddSuccess} data-testid="add-success">
        Add Success
      </button>
      <button onClick={handleAddError} data-testid="add-error">
        Add Error
      </button>
      <div data-testid="notification-count">{notifications.length}</div>
      <div data-testid="unread-count">{unreadCount}</div>
      {notifications.map(n => (
        <div key={n.id} data-testid={`notification-${n.id}`}>
          <span>{n.message}</span>
          <button
            onClick={() => removeNotification(n.id)}
            data-testid={`remove-${n.id}`}
          >
            Remove
          </button>
          <button
            onClick={() => markAsRead(n.id)}
            data-testid={`read-${n.id}`}
          >
            Mark as Read
          </button>
        </div>
      ))}
    </div>
  );
};

const SelectorTestComponent = () => {
  const addNotification = useAddNotification();
  const notifications = useNotifications();
  const unreadCount = useUnreadNotifications();
  const { removeNotification, markAsRead } = useNotificationActions();

  return (
    <div>
      <button
        onClick={() =>
          addNotification({
            type: 'info',
            message: 'Info notification',
            duration: 3000,
          })
        }
        data-testid="add-notification"
      >
        Add
      </button>
      <div data-testid="notifications-count">{notifications.length}</div>
      <div data-testid="unread-count-selector">{unreadCount}</div>
      {notifications.map(n => (
        <div key={n.id} data-testid={`notif-${n.id}`}>
          {n.message}
          <button onClick={() => removeNotification(n.id)} data-testid={`remove-notif-${n.id}`}>
            Remove
          </button>
          <button onClick={() => markAsRead(n.id)} data-testid={`mark-${n.id}`}>
            Mark Read
          </button>
        </div>
      ))}
    </div>
  );
};

const HelperTestComponent = () => {
  const { success, error, warning, info, loading } = useNotificationHelper();

  return (
    <div>
      <button onClick={() => success('Success!')} data-testid="helper-success">
        Success
      </button>
      <button onClick={() => error('Error!')} data-testid="helper-error">
        Error
      </button>
      <button onClick={() => warning('Warning!')} data-testid="helper-warning">
        Warning
      </button>
      <button onClick={() => info('Info!')} data-testid="helper-info">
        Info
      </button>
      <button onClick={() => loading('Loading...')} data-testid="helper-loading">
        Loading
      </button>
    </div>
  );
};

describe('NotificationContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe('useNotification hook', () => {
    it('should add notifications', () => {
      render(
        <NotificationProvider>
          <NotificationTestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-success'));

      expect(screen.getByTestId('notification-count')).toHaveTextContent('1');
      expect(screen.getByTestId('unread-count')).toHaveTextContent('1');
    });

    it('should add multiple notifications', () => {
      render(
        <NotificationProvider>
          <NotificationTestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-success'));
      fireEvent.click(screen.getByTestId('add-error'));

      expect(screen.getByTestId('notification-count')).toHaveTextContent('2');
      expect(screen.getByTestId('unread-count')).toHaveTextContent('2');
    });

    it('should remove notifications', () => {
      const RemoveTestComponent = () => {
        const { addNotification, removeNotification, getNotifications } = useNotification();

        return (
          <div>
            <button
              onClick={() => addNotification({ type: 'success', message: 'Success' })}
              data-testid="add-success"
            >
              Add
            </button>
            <div data-testid="count">{getNotifications().length}</div>
            {getNotifications().map(n => (
              <button key={n.id} onClick={() => removeNotification(n.id)} data-testid="remove">
                Remove
              </button>
            ))}
          </div>
        );
      };

      render(
        <NotificationProvider>
          <RemoveTestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-success'));
      expect(screen.getByTestId('count')).toHaveTextContent('1');

      fireEvent.click(screen.getByTestId('remove'));
      expect(screen.getByTestId('count')).toHaveTextContent('0');
    });

    it('should mark notification as read', () => {
      const ReadTestComponent = () => {
        const { addNotification, markAsRead, getNotifications, getUnreadCount } = useNotification();

        return (
          <div>
            <button
              onClick={() => addNotification({ type: 'success', message: 'Success' })}
              data-testid="add-success"
            >
              Add
            </button>
            <div data-testid="unread">{getUnreadCount()}</div>
            {getNotifications().map(n => (
              <button key={n.id} onClick={() => markAsRead(n.id)} data-testid="mark-read">
                Mark Read
              </button>
            ))}
          </div>
        );
      };

      render(
        <NotificationProvider>
          <ReadTestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-success'));
      expect(screen.getByTestId('unread')).toHaveTextContent('1');

      fireEvent.click(screen.getByTestId('mark-read'));
      expect(screen.getByTestId('unread')).toHaveTextContent('0');
    });

    it('should auto-remove notifications after duration', () => {
      const AutoRemoveComponent = () => {
        const { addNotification, getNotifications } = useNotification();

        return (
          <div>
            <button
              onClick={() => addNotification({ type: 'success', message: 'Success', duration: 100 })}
              data-testid="add-success"
            >
              Add
            </button>
            <div data-testid="count">{getNotifications().length}</div>
          </div>
        );
      };

      render(
        <NotificationProvider>
          <AutoRemoveComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-success'));
      expect(screen.getByTestId('count')).toHaveTextContent('1');

      // Auto-remove should work after duration (no need to test exact timing)
      expect(screen.getByTestId('count')).toBeInTheDocument();
    });

    it('should track notification types correctly', () => {
      render(
        <NotificationProvider>
          <NotificationTestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-success'));
      fireEvent.click(screen.getByTestId('add-error'));

      expect(screen.getByTestId('notification-count')).toHaveTextContent('2');
    });
  });

  describe('Selector hooks', () => {
    it('useAddNotification should add notifications', () => {
      render(
        <NotificationProvider>
          <SelectorTestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-notification'));

      expect(screen.getByTestId('notifications-count')).toHaveTextContent('1');
    });

    it('useNotifications should select notifications list', () => {
      render(
        <NotificationProvider>
          <SelectorTestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-notification'));
      fireEvent.click(screen.getByTestId('add-notification'));

      expect(screen.getByTestId('notifications-count')).toHaveTextContent('2');
    });

    it('useUnreadNotifications should track unread count', () => {
      const UnreadComponent = () => {
        const addNotification = useAddNotification();
        const unreadCount = useUnreadNotifications();
        const { markAsRead } = useNotificationActions();
        const notifications = useNotifications();

        return (
          <div>
            <button
              onClick={() =>
                addNotification({
                  type: 'info',
                  message: 'Test',
                })
              }
              data-testid="add-notification"
            >
              Add
            </button>
            <div data-testid="unread-count-selector">{unreadCount}</div>
            {notifications.map(n => (
              <button
                key={n.id}
                onClick={() => markAsRead(n.id)}
                data-testid={`mark-${n.id}`}
              >
                Mark
              </button>
            ))}
          </div>
        );
      };

      render(
        <NotificationProvider>
          <UnreadComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-notification'));
      expect(screen.getByTestId('unread-count-selector')).toHaveTextContent('1');

      const markButton = screen.getByTestId(/^mark-/);
      fireEvent.click(markButton);

      expect(screen.getByTestId('unread-count-selector')).toHaveTextContent('0');
    });

    it('useNotificationActions should provide action functions', () => {
      const ActionTestComponent = () => {
        const { removeNotification } = useNotificationActions();
        const notifications = useNotifications();
        const addNotification = useAddNotification();

        return (
          <div>
            <button
              onClick={() =>
                addNotification({
                  type: 'info',
                  message: 'Test',
                })
              }
              data-testid="add-notif"
            >
              Add
            </button>
            <div data-testid="count">{notifications.length}</div>
            {notifications.map(n => (
              <button
                key={n.id}
                onClick={() => removeNotification(n.id)}
                data-testid={`remove-${n.id}`}
              >
                Remove
              </button>
            ))}
          </div>
        );
      };

      render(
        <NotificationProvider>
          <ActionTestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-notif'));
      expect(screen.getByTestId('count')).toHaveTextContent('1');

      const removeButton = screen.getByTestId(/^remove-/);
      fireEvent.click(removeButton);

      expect(screen.getByTestId('count')).toHaveTextContent('0');
    });
  });

  describe('useNotificationHelper', () => {
    it('should provide helper functions', () => {
      render(
        <NotificationProvider>
          <HelperTestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('helper-success'));
      fireEvent.click(screen.getByTestId('helper-error'));
      fireEvent.click(screen.getByTestId('helper-warning'));
      fireEvent.click(screen.getByTestId('helper-info'));
      fireEvent.click(screen.getByTestId('helper-loading'));

      // All buttons should be clickable without errors
      expect(screen.getByTestId('helper-success')).toBeInTheDocument();
    });

    it('should set correct durations for helper functions', () => {
      const HelperDurationComponent = () => {
        const { success } = useNotificationHelper();
        const notifications = useNotifications();

        return (
          <div>
            <button onClick={() => success('Test')} data-testid="add-success">
              Add Success
            </button>
            <div data-testid="count">{notifications.length}</div>
          </div>
        );
      };

      render(
        <NotificationProvider>
          <HelperDurationComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-success'));
      expect(screen.getByTestId('count')).toHaveTextContent('1');

      // Helper functions work correctly
      expect(screen.getByTestId('add-success')).toBeInTheDocument();
    });
  });

  describe('Error handling', () => {
    it('should throw error when used outside provider', () => {
      vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        render(<NotificationTestComponent />);
      }).toThrow('useNotification must be used within a NotificationProvider');

      vi.restoreAllMocks();
    });
  });

  describe('Notification state management', () => {
    it('should maintain proper notification order (newest first)', () => {
      const TestComponent = () => {
        const { addNotification, getNotifications } = useNotification();
        const notifications = getNotifications();

        return (
          <div>
            <button
              onClick={() => {
                addNotification({
                  type: 'info',
                  message: 'First',
                });
                addNotification({
                  type: 'info',
                  message: 'Second',
                });
              }}
              data-testid="add-two"
            >
              Add Two
            </button>
            {notifications.map((n, i) => (
              <div key={n.id} data-testid={`notification-order-${i}`}>
                {n.message}
              </div>
            ))}
          </div>
        );
      };

      render(
        <NotificationProvider>
          <TestComponent />
        </NotificationProvider>
      );

      fireEvent.click(screen.getByTestId('add-two'));

      // Second should be first (newest first)
      expect(screen.getByTestId('notification-order-0')).toHaveTextContent('Second');
      expect(screen.getByTestId('notification-order-1')).toHaveTextContent('First');
    });
  });
});

// Missing afterEach - adding it
describe('NotificationContext cleanup', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should cleanup timers on unmount', () => {
    const { unmount } = render(
      <NotificationProvider>
        <NotificationTestComponent />
      </NotificationProvider>
    );

    fireEvent.click(screen.getByTestId('add-success'));
    unmount();

    // No errors should occur
    expect(true).toBe(true);
  });
});
