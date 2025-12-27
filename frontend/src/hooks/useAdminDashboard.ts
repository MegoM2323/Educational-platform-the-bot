/**
 * useAdminDashboard - Custom hook for admin dashboard data management
 *
 * Handles:
 * - Fetching system metrics
 * - Fetching user statistics
 * - Fetching activity logs
 * - Fetching system alerts
 * - Auto-refresh logic
 *
 * Usage:
 * const { stats, metrics, activity, alerts, loading, error, refresh } = useAdminDashboard();
 */

import { useState, useEffect, useCallback } from 'react';
import { adminAPI } from '@/integrations/api/adminAPI';
import { unifiedAPI as apiClient } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';

export interface QuickStat {
  title: string;
  value: number;
  trend?: number;
  icon: React.ReactNode;
  color: string;
}

export interface SystemMetrics {
  timestamp: string;
  cpu: {
    usage_percent: number;
    core_count: number;
    frequency_mhz: number | null;
    status: 'healthy' | 'warning' | 'critical' | 'error';
  };
  memory: {
    total_gb: number;
    available_gb: number;
    used_percent: number;
    swap_total_gb: number;
    swap_used_percent: number;
    status: 'healthy' | 'warning' | 'critical' | 'error';
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    used_percent: number;
    status: 'healthy' | 'warning' | 'critical' | 'error';
  };
  database: {
    response_time_ms: number;
    user_count: number;
    application_count: number;
    payment_count: number;
    status: 'healthy' | 'warning' | 'critical' | 'error';
  };
}

export interface MetricsHistory {
  timestamp: string;
  cpu: number;
  memory: number;
  disk: number;
  apiResponseTime: number;
}

export interface ActivityItem {
  id: number;
  timestamp: string;
  user?: {
    id: number;
    email: string;
    full_name: string;
  };
  action: string;
  resource?: string;
  status: 'success' | 'failed';
  details?: string;
}

export interface SystemAlert {
  id: string;
  severity: 'warning' | 'critical' | 'info';
  title: string;
  message: string;
  timestamp: string;
}

export interface UserStats {
  total_users: number;
  total_students: number;
  total_teachers: number;
  total_tutors: number;
  total_parents: number;
  active_today: number;
}

export interface AssignmentStats {
  total_assignments: number;
  this_week: number;
  last_week: number;
}

export interface DashboardState {
  stats: QuickStat[];
  metrics: SystemMetrics | null;
  metricsHistory: MetricsHistory[];
  activity: ActivityItem[];
  alerts: SystemAlert[];
  activeSessions: number;
  userStats: UserStats | null;
  assignmentStats: AssignmentStats | null;
  loading: boolean;
  error: string | null;
  lastRefresh: Date;
}

export const useAdminDashboard = (autoRefresh: boolean = true) => {
  const [state, setState] = useState<DashboardState>({
    stats: [],
    metrics: null,
    metricsHistory: [],
    activity: [],
    alerts: [],
    activeSessions: 0,
    userStats: null,
    assignmentStats: null,
    loading: true,
    error: null,
    lastRefresh: new Date(),
  });

  /**
   * Load user statistics
   */
  const loadUserStats = useCallback(async () => {
    try {
      const response = await adminAPI.getUserStats();
      if (response.data) {
        setState((prev) => ({
          ...prev,
          userStats: response.data as UserStats,
        }));
        logger.info('[useAdminDashboard] User stats loaded:', response.data);
      }
    } catch (err) {
      logger.error('[useAdminDashboard] Failed to load user stats:', err);
    }
  }, []);

  /**
   * Load assignment statistics
   */
  const loadAssignmentStats = useCallback(async () => {
    try {
      const response = await apiClient.request<AssignmentStats>('/assignments/stats/');
      if (response.data) {
        setState((prev) => ({
          ...prev,
          assignmentStats: response.data,
        }));
        logger.info('[useAdminDashboard] Assignment stats loaded:', response.data);
      }
    } catch (err) {
      logger.error('[useAdminDashboard] Failed to load assignment stats:', err);
    }
  }, []);

  /**
   * Load system metrics
   */
  const loadMetrics = useCallback(async () => {
    try {
      const response = await apiClient.request<SystemMetrics>('/core/metrics/');
      if (response.data) {
        setState((prev) => {
          // Add to history for charts
          const newHistory = [
            ...prev.metricsHistory.slice(-23),
            {
              timestamp: new Date().toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
              }),
              cpu: response.data.cpu.usage_percent,
              memory: response.data.memory.used_percent,
              disk: response.data.disk.used_percent,
              apiResponseTime: response.data.database.response_time_ms,
            },
          ];

          return {
            ...prev,
            metrics: response.data,
            metricsHistory: newHistory,
          };
        });
        logger.info('[useAdminDashboard] Metrics loaded:', response.data);
      }
    } catch (err) {
      logger.error('[useAdminDashboard] Failed to load metrics:', err);
    }
  }, []);

  /**
   * Load active sessions
   */
  const loadSessions = useCallback(async () => {
    try {
      const response = await apiClient.request<{ active_sessions: number }>(
        '/admin/system/sessions/'
      );
      if (response.data) {
        setState((prev) => ({
          ...prev,
          activeSessions: response.data.active_sessions,
        }));
      }
    } catch (err) {
      logger.error('[useAdminDashboard] Failed to load sessions:', err);
    }
  }, []);

  /**
   * Load activity feed
   */
  const loadActivity = useCallback(async () => {
    try {
      const response = await adminAPI.getAuditLogs({
        page_size: 20,
        ordering: '-timestamp',
      });

      if (response.data?.results) {
        setState((prev) => ({
          ...prev,
          activity: response.data.results.map((log: any) => ({
            id: log.id,
            timestamp: log.timestamp,
            user: log.user,
            action: log.action,
            resource: log.resource,
            status: log.status,
            details: log.details,
          })),
        }));
        logger.info('[useAdminDashboard] Activity loaded');
      }
    } catch (err) {
      logger.error('[useAdminDashboard] Failed to load activity:', err);
    }
  }, []);

  /**
   * Load system alerts
   */
  const loadAlerts = useCallback(async () => {
    try {
      const response = await apiClient.request<{ alerts: SystemAlert[] }>('/core/alerts/');
      if (response.data?.alerts) {
        setState((prev) => ({
          ...prev,
          alerts: response.data.alerts.slice(0, 5),
        }));
        logger.info('[useAdminDashboard] Alerts loaded:', response.data.alerts.length);
      }
    } catch (err) {
      logger.error('[useAdminDashboard] Failed to load alerts:', err);
    }
  }, []);

  /**
   * Refresh all data
   */
  const refresh = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      await Promise.all([
        loadUserStats(),
        loadAssignmentStats(),
        loadMetrics(),
        loadSessions(),
        loadActivity(),
        loadAlerts(),
      ]);

      setState((prev) => ({
        ...prev,
        loading: false,
        lastRefresh: new Date(),
      }));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load dashboard data';
      logger.error('[useAdminDashboard] Refresh failed:', err);
      setState((prev) => ({
        ...prev,
        error: errorMsg,
        loading: false,
      }));
    }
  }, [loadUserStats, loadAssignmentStats, loadMetrics, loadSessions, loadActivity, loadAlerts]);

  /**
   * Set up auto-refresh
   */
  useEffect(() => {
    // Initial load
    refresh();

    if (autoRefresh) {
      // Refresh metrics every 30 seconds
      const metricsInterval = setInterval(() => {
        loadMetrics();
        loadActivity();
      }, 30000);

      // Refresh health every 10 seconds
      const healthInterval = setInterval(() => {
        loadSessions();
      }, 10000);

      return () => {
        clearInterval(metricsInterval);
        clearInterval(healthInterval);
      };
    }
  }, [autoRefresh, refresh, loadMetrics, loadActivity, loadSessions]);

  return {
    ...state,
    refresh,
    loadMetrics,
    loadActivity,
    loadAlerts,
  };
};
