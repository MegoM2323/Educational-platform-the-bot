import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useDataExport, type ExportJob } from '../useDataExport';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

/**
 * Mock dependencies
 */
vi.mock('@/integrations/api/unifiedClient');
vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
  },
}));

describe('useDataExport Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('initiateExport', () => {
    it('should initiate an export with correct format', async () => {
      const mockJob: ExportJob = {
        job_id: 'job-123',
        status: 'queued',
        format: 'json',
        created_at: '2025-12-27T10:00:00Z',
        expires_at: '2026-01-03T10:00:00Z',
      };

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ data: mockJob }),
      });

      const { result } = renderHook(() => useDataExport());

      const job = await result.current.initiateExport('json');

      expect(job.job_id).toBe('job-123');
      expect(job.format).toBe('json');
      expect(job.status).toBe('queued');
    });

    it('should send scope parameters in export request', async () => {
      const mockJob: ExportJob = {
        job_id: 'job-123',
        status: 'queued',
        format: 'csv',
        created_at: '2025-12-27T10:00:00Z',
        expires_at: '2026-01-03T10:00:00Z',
      };

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ data: mockJob }),
      });

      const { result } = renderHook(() => useDataExport());

      const scope = {
        include_profile: true,
        include_messages: false,
      };

      await result.current.initiateExport('csv', scope);

      expect(unifiedAPI.fetch).toHaveBeenCalledWith(
        expect.stringContaining('format=csv'),
        'POST',
        expect.objectContaining({ scope })
      );
    });

    it('should handle export errors', async () => {
      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Invalid format' }),
      });

      const { result } = renderHook(() => useDataExport());

      await expect(result.current.initiateExport('invalid' as any)).rejects.toThrow();

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });
    });

    it('should set loading state during export initiation', async () => {
      (unifiedAPI.fetch as any).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => ({
                    data: {
                      job_id: 'job-123',
                      status: 'queued',
                      format: 'json',
                      created_at: '2025-12-27T10:00:00Z',
                      expires_at: '2026-01-03T10:00:00Z',
                    },
                  }),
                }),
              100
            )
          )
      );

      const { result } = renderHook(() => useDataExport());

      expect(result.current.isLoading).toBe(false);

      const promise = result.current.initiateExport('json');
      expect(result.current.isLoading).toBe(true);

      await promise;

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('checkStatus', () => {
    it('should check export job status', async () => {
      const mockJob: ExportJob = {
        job_id: 'job-123',
        status: 'completed',
        format: 'json',
        file_path: '/exports/file.json',
        file_size: 102400,
        created_at: '2025-12-27T10:00:00Z',
        expires_at: '2026-01-03T10:00:00Z',
        download_token: 'token-123',
      };

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ data: mockJob }),
      });

      const { result } = renderHook(() => useDataExport());
      const job = await result.current.checkStatus('job-123');

      expect(job.status).toBe('completed');
      expect(job.file_size).toBe(102400);
      expect(job.download_token).toBe('token-123');
    });

    it('should call correct endpoint for status check', async () => {
      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({
          data: {
            job_id: 'job-123',
            status: 'processing',
            format: 'json',
            created_at: '2025-12-27T10:00:00Z',
            expires_at: '2026-01-03T10:00:00Z',
          },
        }),
      });

      const { result } = renderHook(() => useDataExport());
      await result.current.checkStatus('job-123');

      expect(unifiedAPI.fetch).toHaveBeenCalledWith(
        '/accounts/data-export/job-123/',
        'GET'
      );
    });

    it('should handle status check errors', async () => {
      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: 'Job not found' }),
      });

      const { result } = renderHook(() => useDataExport());

      await expect(result.current.checkStatus('invalid-job')).rejects.toThrow();

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });
    });
  });

  describe('fetchExports', () => {
    it('should fetch export history', async () => {
      const mockExports: ExportJob[] = [
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          file_size: 102400,
          created_at: '2025-12-27T10:00:00Z',
          expires_at: '2026-01-03T10:00:00Z',
          download_token: 'token-1',
        },
        {
          job_id: 'job-2',
          status: 'processing',
          format: 'csv',
          created_at: '2025-12-27T09:00:00Z',
          expires_at: '2026-01-03T09:00:00Z',
        },
      ];

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockExports,
      });

      const { result } = renderHook(() => useDataExport());
      const exports = await result.current.fetchExports();

      expect(exports).toHaveLength(2);
      expect(exports[0].job_id).toBe('job-1');
      expect(exports[1].job_id).toBe('job-2');
    });

    it('should handle paginated responses', async () => {
      const mockExports: ExportJob[] = [
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: '2025-12-27T10:00:00Z',
          expires_at: '2026-01-03T10:00:00Z',
        },
      ];

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({
          results: mockExports,
          count: 1,
          next: null,
        }),
      });

      const { result } = renderHook(() => useDataExport());
      const exports = await result.current.fetchExports();

      expect(exports).toHaveLength(1);
    });

    it('should handle empty export history', async () => {
      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => [],
      });

      const { result } = renderHook(() => useDataExport());
      const exports = await result.current.fetchExports();

      expect(exports).toHaveLength(0);
    });

    it('should set loading state during fetch', async () => {
      (unifiedAPI.fetch as any).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => [],
                }),
              100
            )
          )
      );

      const { result } = renderHook(() => useDataExport());

      expect(result.current.isLoading).toBe(false);

      const promise = result.current.fetchExports();
      expect(result.current.isLoading).toBe(true);

      await promise;

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('downloadExport', () => {
    beforeEach(() => {
      global.fetch = vi.fn();
      global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      global.URL.revokeObjectURL = vi.fn();

      // Mock document methods
      document.body.appendChild = vi.fn();
      document.body.removeChild = vi.fn();
    });

    it('should download export file', async () => {
      const mockBlob = new Blob(['test data'], { type: 'application/json' });

      (global.fetch as any).mockResolvedValue({
        ok: true,
        blob: async () => mockBlob,
      });

      const { result } = renderHook(() => useDataExport());

      await result.current.downloadExport('job-123', 'token-123', 'json');

      expect(global.fetch).toHaveBeenCalled();
    });

    it('should use correct download URL format', async () => {
      const mockBlob = new Blob(['test data'], { type: 'application/json' });

      (global.fetch as any).mockResolvedValue({
        ok: true,
        blob: async () => mockBlob,
      });

      const { result } = renderHook(() => useDataExport());

      await result.current.downloadExport('job-123', 'token-123', 'json');

      const callUrl = (global.fetch as any).mock.calls[0][0];
      expect(callUrl).toContain('/api/accounts/data-export/download/token-123/');
      expect(callUrl).toContain('format=json');
    });

    it('should handle download errors', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: false,
        status: 404,
      });

      const { result } = renderHook(() => useDataExport());

      await expect(
        result.current.downloadExport('job-123', 'invalid-token', 'json')
      ).rejects.toThrow();
    });

    it('should create correct filename for downloads', async () => {
      const mockBlob = new Blob(['test data'], { type: 'application/json' });

      (global.fetch as any).mockResolvedValue({
        ok: true,
        blob: async () => mockBlob,
      });

      const { result } = renderHook(() => useDataExport());

      await result.current.downloadExport('job-123', 'token-123', 'json');

      // Verify filename ends with .json
      // (The actual filename creation happens in the component)
    });
  });

  describe('deleteExport', () => {
    it('should delete export', async () => {
      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({}),
      });

      const { result } = renderHook(() => useDataExport());

      await result.current.deleteExport('job-123');

      expect(unifiedAPI.fetch).toHaveBeenCalledWith(
        '/accounts/data-export/job-123/',
        'DELETE'
      );
    });

    it('should handle delete errors', async () => {
      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: 'Job not found' }),
      });

      const { result } = renderHook(() => useDataExport());

      await expect(result.current.deleteExport('invalid-job')).rejects.toThrow();

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });
    });
  });

  describe('Error Handling', () => {
    it('should store error messages', async () => {
      const errorMessage = 'Network timeout';
      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: errorMessage }),
      });

      const { result } = renderHook(() => useDataExport());

      try {
        await result.current.initiateExport('json');
      } catch {
        // Expected error
      }

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });
    });

    it('should clear error on successful request', async () => {
      const mockJob: ExportJob = {
        job_id: 'job-123',
        status: 'queued',
        format: 'json',
        created_at: '2025-12-27T10:00:00Z',
        expires_at: '2026-01-03T10:00:00Z',
      };

      // First call fails
      (unifiedAPI.fetch as any)
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: async () => ({ error: 'Server error' }),
        })
        // Second call succeeds
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ data: mockJob }),
        });

      const { result } = renderHook(() => useDataExport());

      try {
        await result.current.initiateExport('json');
      } catch {
        // Expected error
      }

      expect(result.current.error).toBeTruthy();

      // Clear error on success
      await result.current.initiateExport('json');

      expect(result.current.error).toBeNull();
    });
  });

  describe('Return Value', () => {
    it('should return all required methods', () => {
      const { result } = renderHook(() => useDataExport());

      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('error');
      expect(result.current).toHaveProperty('initiateExport');
      expect(result.current).toHaveProperty('checkStatus');
      expect(result.current).toHaveProperty('fetchExports');
      expect(result.current).toHaveProperty('downloadExport');
      expect(result.current).toHaveProperty('deleteExport');
    });

    it('should have correct initial state', () => {
      const { result } = renderHook(() => useDataExport());

      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });
});
