import { useState, useCallback } from 'react';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';

/**
 * Export job status types
 */
export type ExportStatus = 'queued' | 'processing' | 'completed' | 'failed';

/**
 * Export format types
 */
export type ExportFormat = 'json' | 'csv';

/**
 * Data export scope configuration
 */
export interface ExportScope {
  include_profile?: boolean;
  include_activity?: boolean;
  include_messages?: boolean;
  include_assignments?: boolean;
  include_payments?: boolean;
  include_notifications?: boolean;
}

/**
 * Export job response from API
 */
export interface ExportJob {
  job_id: string;
  status: ExportStatus;
  format: ExportFormat;
  file_path?: string;
  file_size?: number;
  created_at: string;
  expires_at: string;
  download_token?: string;
  error_message?: string;
}

/**
 * Custom hook for data export functionality
 *
 * Provides methods to:
 * - Initiate new data exports
 * - Check export status
 * - Download exports
 * - Delete exports
 * - Fetch export history
 *
 * @example
 * ```tsx
 * const { exports, initiateExport, checkStatus, downloadExport, deleteExport } = useDataExport();
 *
 * await initiateExport('json', { include_profile: true });
 * ```
 */
export const useDataExport = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Initiate a new data export
   */
  const initiateExport = useCallback(
    async (format: ExportFormat, scope?: ExportScope): Promise<ExportJob> => {
      try {
        setIsLoading(true);
        setError(null);

        logger.debug('[useDataExport] Initiating export with format:', format);

        const params = new URLSearchParams();
        params.set('format', format);

        const response = await unifiedAPI.fetch(
          `/accounts/data-export/?${params.toString()}`,
          'POST',
          scope ? { scope } : {}
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage =
            errorData.error ||
            errorData.detail ||
            `Failed to initiate export (${response.status})`;
          throw new Error(errorMessage);
        }

        const data = await response.json();
        const job = data.data || data;

        logger.debug('[useDataExport] Export job created:', job);
        return job;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to initiate export';
        setError(errorMessage);
        logger.error('[useDataExport] Error initiating export:', err);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Check the status of an export job
   */
  const checkStatus = useCallback(async (jobId: string): Promise<ExportJob> => {
    try {
      setError(null);

      logger.debug('[useDataExport] Checking status for job:', jobId);

      const response = await unifiedAPI.fetch(
        `/accounts/data-export/${jobId}/`,
        'GET'
      );

      if (!response.ok) {
        throw new Error(`Failed to check status (${response.status})`);
      }

      const data = await response.json();
      const job = data.data || data;

      logger.debug('[useDataExport] Job status:', job.status);
      return job;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to check export status';
      setError(errorMessage);
      logger.error('[useDataExport] Error checking status:', err);
      throw err;
    }
  }, []);

  /**
   * Fetch all exports for current user
   */
  const fetchExports = useCallback(async (): Promise<ExportJob[]> => {
    try {
      setIsLoading(true);
      setError(null);

      logger.debug('[useDataExport] Fetching export history...');

      const response = await unifiedAPI.fetch(
        '/accounts/data-export/',
        'GET'
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch exports (${response.status})`);
      }

      const data = await response.json();
      const exports = Array.isArray(data) ? data : data.results || data.data || [];

      logger.debug('[useDataExport] Fetched exports:', exports.length);
      return exports;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch export history';
      setError(errorMessage);
      logger.error('[useDataExport] Error fetching exports:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Download an export file
   */
  const downloadExport = useCallback(
    async (jobId: string, token: string, format: ExportFormat): Promise<void> => {
      try {
        setError(null);

        logger.debug('[useDataExport] Downloading export:', jobId);

        const params = new URLSearchParams();
        params.set('token', token);
        params.set('format', format);

        const fileExtension = format === 'json' ? 'json' : 'zip';
        const filename = `data-export-${new Date().toISOString().split('T')[0]}.${fileExtension}`;

        const authToken = localStorage.getItem('auth_token') || '';
        const response = await fetch(
          `/api/accounts/data-export/download/${token}/?${params.toString()}`,
          {
            method: 'GET',
            headers: {
              Authorization: authToken ? `Bearer ${authToken}` : '',
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Download failed (${response.status})`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        logger.debug('[useDataExport] Download completed');
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to download export';
        setError(errorMessage);
        logger.error('[useDataExport] Error downloading export:', err);
        throw err;
      }
    },
    []
  );

  /**
   * Delete an export
   */
  const deleteExport = useCallback(async (jobId: string): Promise<void> => {
    try {
      setError(null);

      logger.debug('[useDataExport] Deleting export:', jobId);

      const response = await unifiedAPI.fetch(
        `/accounts/data-export/${jobId}/`,
        'DELETE'
      );

      if (!response.ok) {
        throw new Error(`Failed to delete export (${response.status})`);
      }

      logger.debug('[useDataExport] Export deleted');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete export';
      setError(errorMessage);
      logger.error('[useDataExport] Error deleting export:', err);
      throw err;
    }
  }, []);

  return {
    isLoading,
    error,
    initiateExport,
    checkStatus,
    fetchExports,
    downloadExport,
    deleteExport,
  };
};

export default useDataExport;
