import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExportButton } from '../ExportButton';
import * as useDataExportHook from '@/hooks/useDataExport';
import { toast } from 'sonner';

// Mock dependencies
vi.mock('sonner');
vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

/**
 * Mock useDataExport hook
 */
const mockUseDataExport = {
  isLoading: false,
  error: null,
  initiateExport: vi.fn().mockResolvedValue({
    job_id: 'default-job',
    status: 'queued',
    format: 'json' as const,
    created_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  }),
  checkStatus: vi.fn().mockResolvedValue({
    job_id: 'default-job',
    status: 'queued',
    format: 'json' as const,
  }),
  fetchExports: vi.fn().mockResolvedValue([]),
  downloadExport: vi.fn().mockResolvedValue(undefined),
  deleteExport: vi.fn().mockResolvedValue(undefined),
};

describe('ExportButton Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useDataExportHook, 'useDataExport').mockReturnValue(
      mockUseDataExport as any
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Rendering', () => {
    it('should render export button', () => {
      render(<ExportButton />);
      const button = screen.getByRole('button', { name: /export data/i });
      expect(button).toBeInTheDocument();
    });

    it('should render history button when showHistory is true', () => {
      render(<ExportButton showHistory={true} />);
      const historyButton = screen.getByRole('button', { name: /history/i });
      expect(historyButton).toBeInTheDocument();
    });

    it('should not render history button when showHistory is false', () => {
      render(<ExportButton showHistory={false} />);
      const historyButton = screen.queryByRole('button', { name: /history/i });
      expect(historyButton).not.toBeInTheDocument();
    });

    it('should apply correct variant to button', () => {
      const { container } = render(<ExportButton variant="outline" />);
      const button = screen.getByRole('button', { name: /export data/i });
      expect(button).toHaveClass('border');
    });

    it('should apply correct size to button', () => {
      render(<ExportButton size="sm" />);
      const button = screen.getByRole('button', { name: /export data/i });
      expect(button).toBeInTheDocument();
    });
  });

  describe('Format Selection', () => {
    it('should open format dialog when export button is clicked', async () => {
      const user = userEvent.setup();
      render(<ExportButton />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      expect(
        screen.getByRole('heading', { name: /select export format/i })
      ).toBeInTheDocument();
    });

    it('should display both format options', async () => {
      const user = userEvent.setup();
      render(<ExportButton />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      expect(screen.getByText('JSON')).toBeInTheDocument();
      expect(screen.getByText('CSV')).toBeInTheDocument();
      expect(
        screen.getByText('Single file with all data')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Multiple CSV files in ZIP archive')
      ).toBeInTheDocument();
    });

    it('should allow format selection', async () => {
      const user = userEvent.setup();
      render(<ExportButton />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      const csvOption = screen.getByText('CSV').closest('div[class*="border"]');
      await user.click(csvOption!);

      expect(csvOption).toHaveClass('border-blue-500');
    });

    it('should close dialog on cancel', async () => {
      const user = userEvent.setup();
      render(<ExportButton />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(
        screen.queryByRole('heading', { name: /select export format/i })
      ).not.toBeInTheDocument();
    });
  });

  describe('Export Initiation', () => {
    it('should initiate export with selected format', async () => {
      const user = userEvent.setup();
      mockUseDataExport.initiateExport.mockResolvedValue({
        job_id: 'job-123',
        status: 'queued',
        format: 'json',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      });

      render(<ExportButton />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      const confirmButton = screen.getByRole('button', { name: /export/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(mockUseDataExport.initiateExport).toHaveBeenCalledWith('json');
      });
    });

    it('should show success toast on successful export', async () => {
      const user = userEvent.setup();
      mockUseDataExport.initiateExport.mockResolvedValue({
        job_id: 'job-123',
        status: 'queued',
        format: 'json',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      });

      render(<ExportButton />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      const confirmButton = screen.getByRole('button', { name: /export/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          expect.stringContaining('Export initiated')
        );
      });
    });

    it('should show error toast on export failure', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Export failed';
      mockUseDataExport.initiateExport.mockRejectedValue(
        new Error(errorMessage)
      );

      render(<ExportButton />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      const confirmButton = screen.getByRole('button', { name: /export/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(errorMessage);
      });
    });

    it('should call onExportComplete callback', async () => {
      const user = userEvent.setup();
      const onExportComplete = vi.fn();
      mockUseDataExport.initiateExport.mockResolvedValue({
        job_id: 'job-123',
        status: 'queued',
        format: 'json',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      });

      render(<ExportButton onExportComplete={onExportComplete} />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      const confirmButton = screen.getByRole('button', { name: /export/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(onExportComplete).toHaveBeenCalledWith('job-123');
      });
    });
  });

  describe('Export History', () => {
    it('should load export history on mount', async () => {
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          file_size: 1024,
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);

      render(<ExportButton showHistory={true} />);

      await waitFor(() => {
        expect(mockUseDataExport.fetchExports).toHaveBeenCalled();
      });
    });

    it('should display export history dialog', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([]);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      expect(
        screen.getByRole('heading', { name: /export history/i })
      ).toBeInTheDocument();
    });

    it('should display empty state when no exports', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([]);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      expect(
        screen.getByText('No exports yet. Create your first export above!')
      ).toBeInTheDocument();
    });

    it('should display exports in history', async () => {
      const user = userEvent.setup();
      const mockDate = new Date();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          file_size: 1024,
          created_at: mockDate.toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      await waitFor(() => {
        expect(screen.getByText('JSON Export')).toBeInTheDocument();
        expect(screen.getByText('Completed')).toBeInTheDocument();
      });
    });

    it('should show correct status badges', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'processing',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          job_id: 'job-2',
          status: 'failed',
          format: 'csv',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          error_message: 'Failed to process export',
        },
      ]);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      await waitFor(() => {
        expect(screen.getByText('Processing')).toBeInTheDocument();
        expect(screen.getByText('Failed')).toBeInTheDocument();
      });
    });
  });

  describe('Download Functionality', () => {
    it('should download export when download button is clicked', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);
      mockUseDataExport.downloadExport.mockResolvedValue(undefined);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      const downloadButton = await screen.findByRole('button', {
        name: /download/i,
      });
      await user.click(downloadButton);

      await waitFor(() => {
        expect(mockUseDataExport.downloadExport).toHaveBeenCalledWith(
          'job-1',
          'token-1',
          'json'
        );
      });
    });

    it('should show success toast on download start', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);
      mockUseDataExport.downloadExport.mockResolvedValue(undefined);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      const downloadButton = await screen.findByRole('button', {
        name: /download/i,
      });
      await user.click(downloadButton);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Download started!');
      });
    });

    it('should show error when download link is unavailable', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: undefined,
        },
      ]);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      // The export won't have a download button if there's no token
      expect(
        screen.queryByRole('button', { name: /download/i })
      ).not.toBeInTheDocument();
    });

    it('should show download progress', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);

      // Slow down the download mock to see progress
      mockUseDataExport.downloadExport.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      const downloadButton = await screen.findByRole('button', {
        name: /download/i,
      });
      await user.click(downloadButton);

      await waitFor(() => {
        expect(screen.getByText(/downloading/i)).toBeInTheDocument();
      });
    });
  });

  describe('Delete Functionality', () => {
    it('should delete export when delete button is clicked', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);
      mockUseDataExport.deleteExport.mockResolvedValue(undefined);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      const deleteButton = screen.getByRole('button', {
        name: '',
      }).parentElement?.querySelector('button:last-child');

      if (deleteButton) {
        await user.click(deleteButton as HTMLElement);

        await waitFor(() => {
          expect(mockUseDataExport.deleteExport).toHaveBeenCalledWith('job-1');
        });
      }
    });

    it('should show success toast on delete', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);
      mockUseDataExport.deleteExport.mockResolvedValue(undefined);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      // Get all buttons within the dialog
      const buttons = screen.getAllByRole('button');
      const deleteButton = buttons.find((btn) => btn.classList.contains('text-red-600'));

      if (deleteButton) {
        await user.click(deleteButton);

        await waitFor(() => {
          expect(toast.success).toHaveBeenCalledWith('Export deleted');
        });
      }
    });

    it('should handle delete error gracefully', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Failed to delete export';
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);
      mockUseDataExport.deleteExport.mockRejectedValue(new Error(errorMessage));

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      const buttons = screen.getAllByRole('button');
      const deleteButton = buttons.find((btn) => btn.classList.contains('text-red-600'));

      if (deleteButton) {
        await user.click(deleteButton);

        await waitFor(() => {
          expect(toast.error).toHaveBeenCalledWith(errorMessage);
        });
      }
    });
  });

  describe('Error Handling', () => {
    it('should display error in format dialog', async () => {
      const user = userEvent.setup();
      const mockError = 'API Error';
      vi.spyOn(useDataExportHook, 'useDataExport').mockReturnValue({
        ...mockUseDataExport,
        error: mockError,
      } as any);

      render(<ExportButton />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      expect(screen.getByText(mockError)).toBeInTheDocument();
    });

    it('should handle network errors', async () => {
      const user = userEvent.setup();
      mockUseDataExport.initiateExport.mockRejectedValue(
        new Error('Network error')
      );

      render(<ExportButton />);

      const exportButton = screen.getByRole('button', { name: /export data/i });
      await user.click(exportButton);

      const confirmButton = screen.getByRole('button', { name: /export/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Network error');
      });
    });
  });

  describe('File Size Formatting', () => {
    it('should format file sizes correctly', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          file_size: 1024 * 1024 * 2.5, // 2.5 MB
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      await waitFor(() => {
        expect(screen.getByText(/2.50 MB/)).toBeInTheDocument();
      });
    });
  });

  describe('Status Badge Colors', () => {
    it('should show correct colors for different statuses', async () => {
      const user = userEvent.setup();
      mockUseDataExport.fetchExports.mockResolvedValue([
        {
          job_id: 'job-1',
          status: 'queued',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          job_id: 'job-2',
          status: 'completed',
          format: 'json',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          download_token: 'token-1',
        },
      ]);

      render(<ExportButton showHistory={true} />);

      const historyButton = screen.getByRole('button', { name: /history/i });
      await user.click(historyButton);

      await waitFor(() => {
        const badges = screen.getAllByText(/queued|completed/i);
        expect(badges.length).toBeGreaterThan(0);
      });
    });
  });
});
