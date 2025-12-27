import { unifiedAPI as apiClient, ApiResponse } from './unifiedClient';

/**
 * Types for Database Status API
 */

export interface DatabaseStatus {
  database_type: string;
  database_version: string;
  database_size_mb: number;
  connection_pool_active: number;
  connection_pool_max: number;
  last_backup_timestamp: string | null;
  backup_status: 'pending' | 'in_progress' | 'completed' | 'failed';
  health_status: 'green' | 'yellow' | 'red';
  last_check_timestamp: string;
  alerts: DatabaseAlert[];
}

export interface DatabaseAlert {
  id: string;
  severity: 'warning' | 'critical';
  message: string;
  component: string;
  timestamp: string;
}

export interface TableStatistics {
  name: string;
  row_count: number;
  size_mb: number;
  last_vacuum: string | null;
  last_reindex: string | null;
  bloat_percentage: number;
  bloat_level: 'low' | 'medium' | 'high';
}

export interface SlowQuery {
  id: string;
  query: string;
  count: number;
  avg_time_ms: number;
  max_time_ms: number;
  min_time_ms: number;
}

export interface MaintenanceTask {
  name: string;
  last_run: string | null;
  estimated_duration_minutes: number;
  description: string;
}

export interface Backup {
  id: string;
  filename: string;
  size_mb: number;
  created_date: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export interface Connection {
  pid: number;
  query: string;
  started_at: string;
  duration_seconds: number;
  user: string;
}

export interface OperationResult {
  success: boolean;
  message: string;
  data?: {
    disk_freed_mb?: number;
    rows_processed?: number;
    duration_seconds?: number;
  };
}

export interface MaintenanceRequest {
  operation: string;
  dry_run: boolean;
}

export interface BackupOperationRequest {
  backup_id: string;
  action: 'restore' | 'download' | 'delete';
}

export interface KillQueryRequest {
  pid: number;
}

/**
 * Database Admin API Client
 * Provides endpoints for database monitoring and maintenance
 *
 * Endpoints:
 * - GET /api/admin/system/database/ - Get database status
 * - GET /api/admin/system/database/tables/ - Get table statistics
 * - GET /api/admin/system/database/queries/ - Get slow queries
 * - GET /api/admin/system/database/backups/ - Get backup list
 * - GET /api/admin/system/database/connections/ - Get long-running queries
 * - GET /api/admin/system/database/maintenance/ - Get maintenance tasks
 * - POST /api/admin/database/maintenance/ - Run maintenance operation
 * - POST /api/admin/database/backup/ - Create backup
 * - GET /api/admin/database/backup/{id}/download/ - Download backup
 * - POST /api/admin/database/backup/{id}/restore/ - Restore backup
 * - DELETE /api/admin/database/backup/{id}/ - Delete backup
 * - POST /api/admin/database/kill-query/ - Terminate long-running query
 */
export const databaseAPI = {
  /**
   * Get database status and overview
   */
  async getDatabaseStatus(): Promise<ApiResponse<DatabaseStatus>> {
    return apiClient.request<DatabaseStatus>('/admin/system/database/');
  },

  /**
   * Get table statistics
   */
  async getTableStatistics(): Promise<ApiResponse<{ tables: TableStatistics[] }>> {
    return apiClient.request<{ tables: TableStatistics[] }>(
      '/admin/system/database/tables/'
    );
  },

  /**
   * Get slow queries (top 10)
   */
  async getSlowQueries(): Promise<ApiResponse<{ queries: SlowQuery[] }>> {
    return apiClient.request<{ queries: SlowQuery[] }>(
      '/admin/system/database/queries/'
    );
  },

  /**
   * Get list of backups
   */
  async getBackups(): Promise<ApiResponse<{ backups: Backup[] }>> {
    return apiClient.request<{ backups: Backup[] }>(
      '/admin/system/database/backups/'
    );
  },

  /**
   * Get long-running queries (>30 seconds)
   */
  async getConnections(): Promise<ApiResponse<{ connections: Connection[] }>> {
    return apiClient.request<{ connections: Connection[] }>(
      '/admin/system/database/connections/'
    );
  },

  /**
   * Get available maintenance tasks
   */
  async getMaintenanceTasks(): Promise<ApiResponse<{ tasks: MaintenanceTask[] }>> {
    return apiClient.request<{ tasks: MaintenanceTask[] }>(
      '/admin/system/database/maintenance/'
    );
  },

  /**
   * Run a maintenance operation (vacuum, reindex, cleanup, etc.)
   */
  async runMaintenanceOperation(
    request: MaintenanceRequest
  ): Promise<ApiResponse<OperationResult>> {
    return apiClient.request<OperationResult>('/admin/database/maintenance/', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  /**
   * Create a new backup
   */
  async createBackup(): Promise<ApiResponse<Backup>> {
    return apiClient.request<Backup>('/admin/database/backup/', {
      method: 'POST',
    });
  },

  /**
   * Download a backup file
   */
  async downloadBackup(backupId: string): Promise<ApiResponse<Blob>> {
    return apiClient.request<Blob>(
      `/admin/database/backup/${backupId}/download/`,
      {
        headers: {
          Accept: 'application/octet-stream',
        },
      }
    );
  },

  /**
   * Restore a backup (WARNING: overwrites current database)
   */
  async restoreBackup(backupId: string): Promise<ApiResponse<OperationResult>> {
    return apiClient.request<OperationResult>(
      `/admin/database/backup/${backupId}/restore/`,
      {
        method: 'POST',
      }
    );
  },

  /**
   * Delete a backup
   */
  async deleteBackup(backupId: string): Promise<ApiResponse<void>> {
    return apiClient.request<void>(
      `/admin/database/backup/${backupId}/`,
      {
        method: 'DELETE',
      }
    );
  },

  /**
   * Terminate a long-running query
   */
  async killQuery(pid: number): Promise<ApiResponse<OperationResult>> {
    return apiClient.request<OperationResult>('/admin/database/kill-query/', {
      method: 'POST',
      body: JSON.stringify({ pid }),
    });
  },
};
