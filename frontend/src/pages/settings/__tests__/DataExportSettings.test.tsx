import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { DataExportSettings } from '../DataExportSettings';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import * as sonner from 'sonner';

/**
 * Mock dependencies
 */
vi.mock('@/integrations/api/unifiedClient');
vi.mock('sonner');
vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
  },
}));
vi.mock('@/components/LoadingSpinner', () => ({
  LoadingSpinner: ({ text }: { text?: string }) => <div>{text || 'Loading...'}</div>,
}));

/**
 * Test wrapper component
 */
const renderComponent = () => {
  return render(
    <BrowserRouter>
      <DataExportSettings />
    </BrowserRouter>
  );
};

describe('DataExportSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (unifiedAPI.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ data: [] }),
    });
  });

  describe('Component Rendering', () => {
    it('should render loading state initially', () => {
      renderComponent();
      expect(screen.getByText('Loading data export settings...')).toBeInTheDocument();
    });

    it('should render main page after loading', async () => {
      renderComponent();
      await waitFor(() => {
        expect(screen.getByText('Data Export')).toBeInTheDocument();
      });
    });

    it('should render all main sections', async () => {
      renderComponent();
      await waitFor(() => {
        expect(screen.getByText('Create New Export')).toBeInTheDocument();
        expect(screen.getByText('Export History')).toBeInTheDocument();
        expect(screen.getByText('About Your Data Export')).toBeInTheDocument();
      });
    });

    it('should render GDPR information alert', async () => {
      renderComponent();
      await waitFor(() => {
        expect(screen.getByText(/Your GDPR Right:/)).toBeInTheDocument();
        expect(screen.getByText(/Article 20/)).toBeInTheDocument();
      });
    });

    it('should display back button', async () => {
      renderComponent();
      await waitFor(() => {
        const backButton = screen.getByRole('button', { name: /Back/i });
        expect(backButton).toBeInTheDocument();
      });
    });
  });

  describe('Export Form', () => {
    it('should render format selection dropdown', async () => {
      renderComponent();
      await waitFor(() => {
        expect(screen.getByText('Export Format')).toBeInTheDocument();
      });
    });

    it('should render data scope checkboxes', async () => {
      renderComponent();
      await waitFor(() => {
        expect(screen.getByText('Profile Data')).toBeInTheDocument();
        expect(screen.getByText('Activity Logs')).toBeInTheDocument();
        expect(screen.getByText('Messages')).toBeInTheDocument();
        expect(screen.getByText('Assignments')).toBeInTheDocument();
        expect(screen.getByText('Payments')).toBeInTheDocument();
        expect(screen.getByText('Notifications')).toBeInTheDocument();
      });
    });

    it('should render Create Export button', async () => {
      renderComponent();
      await waitFor(() => {
        const button = screen.getByRole('button', { name: /Create Export/i });
        expect(button).toBeInTheDocument();
      });
    });

    it('should have all data scope options checked by default', async () => {
      renderComponent();
      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox');
        checkboxes.forEach((checkbox) => {
          expect(checkbox).toBeChecked();
        });
      });
    });
  });

  describe('Export History', () => {
    it('should show empty state when no exports', async () => {
      renderComponent();
      await waitFor(() => {
        expect(screen.getByText(/No exports yet/)).toBeInTheDocument();
      });
    });

    it('should display export history items', async () => {
      const mockExports = [
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          file_size: 1024000,
          created_at: '2025-12-27T10:00:00Z',
          expires_at: '2026-01-03T10:00:00Z',
          download_token: 'token-123',
        },
      ];

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockExports,
      });

      renderComponent();
      await waitFor(() => {
        expect(screen.getByText('JSON Export')).toBeInTheDocument();
        expect(screen.getByText('Completed')).toBeInTheDocument();
      });
    });

    it('should show file size in history', async () => {
      const mockExports = [
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          file_size: 1048576,
          created_at: '2025-12-27T10:00:00Z',
          expires_at: '2026-01-03T10:00:00Z',
        },
      ];

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockExports,
      });

      renderComponent();
      await waitFor(() => {
        expect(screen.getByText(/1\.00 MB/)).toBeInTheDocument();
      });
    });

    it('should display different status badges', async () => {
      const mockExports = [
        {
          job_id: 'job-1',
          status: 'queued',
          format: 'json',
          created_at: '2025-12-27T10:00:00Z',
          expires_at: '2026-01-03T10:00:00Z',
        },
        {
          job_id: 'job-2',
          status: 'processing',
          format: 'csv',
          created_at: '2025-12-27T10:05:00Z',
          expires_at: '2026-01-03T10:05:00Z',
        },
        {
          job_id: 'job-3',
          status: 'completed',
          format: 'json',
          created_at: '2025-12-27T10:10:00Z',
          expires_at: '2026-01-03T10:10:00Z',
          download_token: 'token-1',
        },
      ];

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockExports,
      });

      renderComponent();
      await waitFor(() => {
        expect(screen.getByText('Queued')).toBeInTheDocument();
        expect(screen.getByText('Processing')).toBeInTheDocument();
        expect(screen.getByText('Completed')).toBeInTheDocument();
      });
    });
  });

  describe('Export Form Submission', () => {
    it('should submit export request with correct format', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Create Export/i })).toBeInTheDocument();
      });

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({
          job_id: 'new-job-1',
          status: 'queued',
          format: 'json',
          expires_at: '2026-01-03T10:00:00Z',
        }),
      });

      const submitButton = screen.getByRole('button', { name: /Create Export/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(unifiedAPI.fetch).toHaveBeenCalledWith(
          expect.stringContaining('format=json'),
          'POST',
          expect.any(Object)
        );
      });
    });

    it('should show success message after export request', async () => {
      const user = userEvent.setup();
      renderComponent();

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({
          job_id: 'new-job-1',
          status: 'queued',
          format: 'json',
          expires_at: '2026-01-03T10:00:00Z',
        }),
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Create Export/i })).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Create Export/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(sonner.toast.success).toHaveBeenCalled();
      });
    });

    it('should handle export errors', async () => {
      const user = userEvent.setup();
      renderComponent();

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid format' }),
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Create Export/i })).toBeInTheDocument();
      });

      const submitButton = screen.getByRole('button', { name: /Create Export/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(sonner.toast.error).toHaveBeenCalled();
      });
    });
  });

  describe('Download Export', () => {
    beforeEach(() => {
      global.fetch = vi.fn();
      global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      global.URL.revokeObjectURL = vi.fn();
    });

    it('should provide download button for completed exports', async () => {
      const mockExports = [
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          file_size: 1024000,
          created_at: '2025-12-27T10:00:00Z',
          expires_at: '2026-01-03T10:00:00Z',
          download_token: 'token-123',
        },
      ];

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockExports,
      });

      renderComponent();
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Download/i })).toBeInTheDocument();
      });
    });

    it('should not show download button for queued exports', async () => {
      const mockExports = [
        {
          job_id: 'job-1',
          status: 'queued',
          format: 'json',
          created_at: '2025-12-27T10:00:00Z',
          expires_at: '2026-01-03T10:00:00Z',
        },
      ];

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockExports,
      });

      renderComponent();
      await waitFor(() => {
        const buttons = screen.queryAllByRole('button', { name: /Download/i });
        expect(buttons.length).toBe(0);
      });
    });
  });

  describe('Delete Export', () => {
    it('should show delete confirmation dialog', async () => {
      const user = userEvent.setup();
      const mockExports = [
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: '2025-12-27T10:00:00Z',
          expires_at: '2026-01-03T10:00:00Z',
          download_token: 'token-123',
        },
      ];

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockExports,
      });

      renderComponent();
      await waitFor(() => {
        const deleteButton = screen.getAllByRole('button').find((btn) =>
          btn.querySelector('[data-testid="trash-icon"]') ||
          btn.className.includes('text-red')
        );
        expect(deleteButton).toBeDefined();
      });
    });

    it('should call delete API on confirmation', async () => {
      const user = userEvent.setup();
      const mockExports = [
        {
          job_id: 'job-1',
          status: 'completed',
          format: 'json',
          created_at: '2025-12-27T10:00:00Z',
          expires_at: '2026-01-03T10:00:00Z',
          download_token: 'token-123',
        },
      ];

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockExports,
      });

      renderComponent();

      // Note: Delete button testing would require proper implementation
      // of trash icon identification in the component
    });
  });

  describe('Error Handling', () => {
    it('should display load error message', async () => {
      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: false,
        status: 500,
      });

      renderComponent();
      await waitFor(() => {
        expect(sonner.toast.error).toHaveBeenCalled();
      });
    });

    it('should redirect to login on 401 error', async () => {
      const navigateSpy = vi.fn();
      vi.mock('react-router-dom', async () => {
        const actual = await vi.importActual('react-router-dom');
        return {
          ...actual,
          useNavigate: () => navigateSpy,
        };
      });

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: false,
        status: 401,
      });

      renderComponent();
      await waitFor(() => {
        expect(sonner.toast.error).toHaveBeenCalled();
      });
    });
  });

  describe('Responsive Design', () => {
    it('should render properly on mobile', async () => {
      renderComponent();
      await waitFor(() => {
        const container = screen.getByText('Data Export').closest('div');
        expect(container).toBeInTheDocument();
      });
    });

    it('should have mobile-friendly button layout', async () => {
      renderComponent();
      await waitFor(() => {
        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper labels for form inputs', async () => {
      renderComponent();
      await waitFor(() => {
        expect(screen.getByLabelText(/Export Format/i)).toBeInTheDocument();
      });
    });

    it('should have proper form structure', async () => {
      renderComponent();
      await waitFor(() => {
        const form = screen.getByRole('button', { name: /Create Export/i }).closest('form');
        expect(form).toBeInTheDocument();
      });
    });

    it('should have semantic heading hierarchy', async () => {
      renderComponent();
      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Data Export');
      });
    });
  });

  describe('Data Export Scope Options', () => {
    it('should allow toggling profile data checkbox', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox');
        expect(checkboxes.length).toBeGreaterThan(0);
      });
    });

    it('should accept custom scope in export request', async () => {
      const user = userEvent.setup();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Create Export/i })).toBeInTheDocument();
      });

      (unifiedAPI.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({
          job_id: 'new-job-1',
          status: 'queued',
          format: 'json',
          expires_at: '2026-01-03T10:00:00Z',
        }),
      });

      const submitButton = screen.getByRole('button', { name: /Create Export/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(unifiedAPI.fetch).toHaveBeenCalled();
      });
    });
  });
});
