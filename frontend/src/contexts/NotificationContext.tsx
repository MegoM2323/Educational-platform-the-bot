// Notification Context для управления уведомлениями
import React, { createContext, useContext, useCallback, useMemo, ReactNode, useReducer } from 'react';
import { logger } from '@/utils/logger';

export type NotificationType = 'success' | 'error' | 'warning' | 'info' | 'loading';

interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  title?: string;
  description?: string;
  duration?: number;
  timestamp: number;
  read: boolean;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
}

type NotificationAction =
  | { type: 'ADD_NOTIFICATION'; payload: Notification }
  | { type: 'REMOVE_NOTIFICATION'; payload: string }
  | { type: 'CLEAR_NOTIFICATIONS' }
  | { type: 'MARK_AS_READ'; payload: string }
  | { type: 'MARK_ALL_AS_READ' }
  | { type: 'AUTO_REMOVE_NOTIFICATION'; payload: string };

interface NotificationContextType {
  state: NotificationState;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => string;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  getNotifications: () => Notification[];
  getUnreadCount: () => number;
}

const initialState: NotificationState = {
  notifications: [],
  unreadCount: 0,
};

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

function notificationReducer(state: NotificationState, action: NotificationAction): NotificationState {
  switch (action.type) {
    case 'ADD_NOTIFICATION': {
      const notifications = [action.payload, ...state.notifications];
      return {
        notifications,
        unreadCount: state.unreadCount + (action.payload.read ? 0 : 1),
      };
    }
    case 'REMOVE_NOTIFICATION': {
      const notification = state.notifications.find(n => n.id === action.payload);
      const notifications = state.notifications.filter(n => n.id !== action.payload);
      return {
        notifications,
        unreadCount: notification && !notification.read ? state.unreadCount - 1 : state.unreadCount,
      };
    }
    case 'CLEAR_NOTIFICATIONS':
      return { ...initialState };
    case 'MARK_AS_READ': {
      const notifications = state.notifications.map(n =>
        n.id === action.payload ? { ...n, read: true } : n
      );
      const notification = state.notifications.find(n => n.id === action.payload);
      return {
        notifications,
        unreadCount: notification && !notification.read ? state.unreadCount - 1 : state.unreadCount,
      };
    }
    case 'MARK_ALL_AS_READ':
      return {
        ...state,
        notifications: state.notifications.map(n => ({ ...n, read: true })),
        unreadCount: 0,
      };
    case 'AUTO_REMOVE_NOTIFICATION': {
      const notification = state.notifications.find(n => n.id === action.payload);
      const notifications = state.notifications.filter(n => n.id !== action.payload);
      return {
        notifications,
        unreadCount: notification && !notification.read ? state.unreadCount - 1 : state.unreadCount,
      };
    }
    default:
      return state;
  }
}

interface NotificationProviderProps {
  children: ReactNode;
  maxNotifications?: number;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({
  children,
  maxNotifications = 5,
}) => {
  const [state, dispatch] = useReducer(notificationReducer, initialState);

  const addNotification = useCallback(
    (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>): string => {
      const id = `notification-${Date.now()}-${Math.random()}`;
      const newNotification: Notification = {
        ...notification,
        id,
        timestamp: Date.now(),
        read: false,
      };

      dispatch({ type: 'ADD_NOTIFICATION', payload: newNotification });
      logger.debug('[NotificationContext] Notification added:', id);

      // Auto-remove notification after duration
      if (notification.duration && notification.duration > 0) {
        setTimeout(() => {
          dispatch({ type: 'AUTO_REMOVE_NOTIFICATION', payload: id });
        }, notification.duration);
      }

      return id;
    },
    []
  );

  const removeNotification = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_NOTIFICATION', payload: id });
    logger.debug('[NotificationContext] Notification removed:', id);
  }, []);

  const clearNotifications = useCallback(() => {
    dispatch({ type: 'CLEAR_NOTIFICATIONS' });
    logger.debug('[NotificationContext] All notifications cleared');
  }, []);

  const markAsRead = useCallback((id: string) => {
    dispatch({ type: 'MARK_AS_READ', payload: id });
    logger.debug('[NotificationContext] Notification marked as read:', id);
  }, []);

  const markAllAsRead = useCallback(() => {
    dispatch({ type: 'MARK_ALL_AS_READ' });
    logger.debug('[NotificationContext] All notifications marked as read');
  }, []);

  const getNotifications = useCallback(() => {
    return state.notifications;
  }, [state.notifications]);

  const getUnreadCount = useCallback(() => {
    return state.unreadCount;
  }, [state.unreadCount]);

  const value: NotificationContextType = useMemo(
    () => ({
      state,
      addNotification,
      removeNotification,
      clearNotifications,
      markAsRead,
      markAllAsRead,
      getNotifications,
      getUnreadCount,
    }),
    [state, addNotification, removeNotification, clearNotifications, markAsRead, markAllAsRead, getNotifications, getUnreadCount]
  );

  return (
    <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>
  );
};

export const useNotification = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};

// Selectors to prevent re-renders
export const useAddNotification = () => {
  const { addNotification } = useNotification();
  return useCallback(
    (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) =>
      addNotification(notification),
    [addNotification]
  );
};

export const useNotifications = () => {
  const { state, getNotifications } = useNotification();
  return useMemo(() => getNotifications(), [state.notifications]);
};

export const useUnreadNotifications = () => {
  const { state, getUnreadCount } = useNotification();
  return useMemo(() => getUnreadCount(), [state.unreadCount]);
};

export const useNotificationActions = () => {
  const { removeNotification, clearNotifications, markAsRead, markAllAsRead } = useNotification();
  return useMemo(
    () => ({
      removeNotification,
      clearNotifications,
      markAsRead,
      markAllAsRead,
    }),
    [removeNotification, clearNotifications, markAsRead, markAllAsRead]
  );
};

// Helper hooks for common notifications
export const useNotificationHelper = () => {
  const { addNotification } = useNotification();

  return useMemo(
    () => ({
      success: (message: string, title?: string) =>
        addNotification({ type: 'success', message, title, duration: 3000 }),
      error: (message: string, title?: string) =>
        addNotification({ type: 'error', message, title, duration: 5000 }),
      warning: (message: string, title?: string) =>
        addNotification({ type: 'warning', message, title, duration: 4000 }),
      info: (message: string, title?: string) =>
        addNotification({ type: 'info', message, title, duration: 3000 }),
      loading: (message: string, title?: string) =>
        addNotification({ type: 'loading', message, title }),
    }),
    [addNotification]
  );
};
