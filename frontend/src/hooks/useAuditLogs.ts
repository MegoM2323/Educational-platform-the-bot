import { useState, useCallback } from 'react';
import { logger } from '@/utils/logger';

/**
 * Audit log entry structure
 */
export interface AuditLogEntry {
  id: number;
  timestamp: string;
  user: {
    id: number;
    email: string;
    full_name: string;
  };
  action: 'create' | 'read' | 'update' | 'delete' | 'export' | 'login' | 'logout';
  resource: 'User' | 'Material' | 'Assignment' | 'ChatRoom' | 'Message' | 'Payment' | string;
  status: 'success' | 'failed';
  ip_address: string;
  user_agent?: string;
  duration_ms?: number;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  details?: string;
}

/**
 * Paginated response structure
 */
export interface PaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditLogEntry[];
}

/**
 * Filter options for audit logs
 */
export interface AuditLogFilters {
  user_id?: number;
  action?: string;
  resource?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}

/**
 * Hook for fetching and managing audit logs
 *
 * @param pageSize - Number of items per page (default: 50)
 * @returns Object with audit log state and methods
 */
export const useAuditLogs = (pageSize: number = 50) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  /**
   * Fetch audit logs with optional filters
   */
  const fetchLogs = useCallback(
    async (page: number = 1, filters?: AuditLogFilters) => {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        params.append('page', page.toString());
        params.append('page_size', pageSize.toString());
        params.append('ordering', '-timestamp');

        if (filters?.user_id) params.append('user_id', filters.user_id.toString());
        if (filters?.action) params.append('action', filters.action);
        if (filters?.resource) params.append('resource', filters.resource);
        if (filters?.status) params.append('status', filters.status);
        if (filters?.date_from) params.append('date_from', filters.date_from);
        if (filters?.date_to) params.append('date_to', filters.date_to);
        if (filters?.search) params.append('search', filters.search);

        const response = await fetch(`/api/admin/audit-logs/?${params.toString()}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`Failed to load audit logs: ${response.statusText}`);
        }

        const data: PaginatedResponse = await response.json();
        setLogs(data.results || []);
        setTotalCount(data.count || 0);
        setCurrentPage(page);

        logger.info('[useAuditLogs] Loaded logs:', {
          count: data.results?.length,
          total: data.count,
          page,
        });

        return data;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load audit logs';
        setError(errorMsg);
        logger.error('[useAuditLogs] Failed to fetch:', err);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [pageSize]
  );

  /**
   * Fetch a single audit log entry with full details
   */
  const fetchLogDetails = useCallback(async (logId: number) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/admin/audit-logs/${logId}/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to load log details: ${response.statusText}`);
      }

      const data: AuditLogEntry = await response.json();
      logger.info('[useAuditLogs] Loaded log details:', { id: logId });
      return data;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load log details';
      setError(errorMsg);
      logger.error('[useAuditLogs] Failed to fetch details:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Export audit logs to CSV
   */
  const exportToCSV = useCallback(async (filters?: AuditLogFilters) => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('page_size', '10000');

      if (filters?.user_id) params.append('user_id', filters.user_id.toString());
      if (filters?.action) params.append('action', filters.action);
      if (filters?.resource) params.append('resource', filters.resource);
      if (filters?.status) params.append('status', filters.status);
      if (filters?.date_from) params.append('date_from', filters.date_from);
      if (filters?.date_to) params.append('date_to', filters.date_to);
      params.append('format', 'csv');

      const response = await fetch(`/api/admin/audit-logs/?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Accept': 'text/csv',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to export audit logs');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      logger.info('[useAuditLogs] Exported to CSV');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Export failed';
      setError(errorMsg);
      logger.error('[useAuditLogs] Export failed:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Clear error message
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    logs,
    isLoading,
    error,
    totalCount,
    currentPage,
    pageSize,
    fetchLogs,
    fetchLogDetails,
    exportToCSV,
    clearError,
  };
};

/**
 * Hook for fetching users for audit log filters
 *
 * @returns Array of users
 */
export const useAuditLogUsers = () => {
  const [users, setUsers] = useState<
    Array<{ id: number; email: string; full_name: string }>
  >([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/users/?page_size=1000', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to load users');
      }

      const data = await response.json();
      setUsers(data.results || []);
      logger.info('[useAuditLogUsers] Loaded users:', { count: data.results?.length });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load users';
      setError(errorMsg);
      logger.error('[useAuditLogUsers] Failed to fetch:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    users,
    isLoading,
    error,
    fetchUsers,
  };
};
