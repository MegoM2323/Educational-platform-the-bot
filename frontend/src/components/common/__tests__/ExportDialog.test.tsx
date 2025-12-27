import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { ExportDialog, ExportParams } from '../ExportDialog';

/**
 * ExportDialog Component Tests
 *
 * Comprehensive test suite for the ExportDialog component
 * Tests rendering, user interactions, and data export functionality
 */
describe('ExportDialog', () => {
  const mockOnExport = vi.fn<[ExportParams], Promise<void>>(async () => {});
  const mockOnOpenChange = vi.fn<[boolean], void>();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render when open prop is true', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          title="Test Export"
          description="Test description"
        />
      );

      expect(screen.getByText('Test Export')).toBeInTheDocument();
      expect(screen.getByText('Test description')).toBeInTheDocument();
    });

    it('should display file name input field', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      expect(screen.getByPlaceholderText(/export_/)).toBeInTheDocument();
    });

    it('should show default file name with current date', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      const today = new Date().toISOString().split('T')[0];
      const input = screen.getByPlaceholderText(/export_/) as HTMLInputElement;
      expect(input.value).toContain(today);
    });

    it('should display formatting options label', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          includeFormatOptions={true}
        />
      );

      expect(screen.getByText(/Include Formatting/)).toBeInTheDocument();
    });
  });

  describe('Format Selection', () => {
    it('should display CSV format option by default', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          supportedFormats={['csv', 'excel', 'pdf']}
        />
      );

      expect(screen.getByText(/CSV/i)).toBeInTheDocument();
    });

    it('should display Excel format option when supported', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          supportedFormats={['excel']}
        />
      );

      expect(screen.getByText(/Excel/i)).toBeInTheDocument();
    });

    it('should display PDF format option when supported', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          supportedFormats={['pdf']}
        />
      );

      expect(screen.getByText(/PDF/i)).toBeInTheDocument();
    });

    it('should only display supported formats', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          supportedFormats={['csv']}
        />
      );

      expect(screen.getByText(/CSV/i)).toBeInTheDocument();
      expect(screen.queryByText(/Excel/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/PDF/i)).not.toBeInTheDocument();
    });
  });

  describe('File Naming', () => {
    it('should update file name when input changes', async () => {
      const user = userEvent.setup();
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      const input = screen.getByPlaceholderText(/export_/) as HTMLInputElement;
      await user.clear(input);
      await user.type(input, 'my_export_file');

      expect(input.value).toBe('my_export_file');
    });

    it('should preview file extension based on format', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          defaultFormat="csv"
        />
      );

      expect(screen.getByText(/.csv/)).toBeInTheDocument();
    });
  });

  describe('Scope Selection', () => {
    it('should display current view scope option', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          supportedScopes={['current']}
        />
      );

      expect(screen.getByText(/Current View/i)).toBeInTheDocument();
    });

    it('should display all data scope option', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          supportedScopes={['all']}
        />
      );

      expect(screen.getByText(/All Data/i)).toBeInTheDocument();
    });

    it('should only show supported scopes', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          supportedScopes={['current']}
        />
      );

      expect(screen.getByText(/Current View/i)).toBeInTheDocument();
      expect(screen.queryByText(/All Data/i)).not.toBeInTheDocument();
    });
  });

  describe('Export Functionality', () => {
    it('should call onExport with correct default parameters', async () => {
      const user = userEvent.setup();
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          defaultFormat="csv"
          defaultScope="all"
        />
      );

      const buttons = screen.getAllByRole('button');
      const exportButton = buttons.find((btn) => btn.textContent?.includes('Export'));
      if (exportButton) {
        await user.click(exportButton);
      }

      await waitFor(() => {
        expect(mockOnExport).toHaveBeenCalledWith(
          expect.objectContaining({
            format: 'csv',
            scope: 'all',
            fileName: expect.any(String),
            includeFormatting: expect.any(Boolean),
          })
        );
      });
    });

    it('should disable export button when file name is empty', async () => {
      const user = userEvent.setup();
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      const input = screen.getByPlaceholderText(/export_/) as HTMLInputElement;
      await user.clear(input);

      const buttons = screen.getAllByRole('button');
      const exportButton = buttons.find((btn) => btn.textContent?.includes('Export'));

      // Button should be disabled when file name is empty
      expect(exportButton).toBeDisabled();
    });

    it('should show processing state during export', async () => {
      const user = userEvent.setup();
      mockOnExport.mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(resolve, 100);
          })
      );

      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      const buttons = screen.getAllByRole('button');
      const exportButton = buttons.find((btn) => btn.textContent?.includes('Export'));
      if (exportButton) {
        await user.click(exportButton);
      }

      await waitFor(() => {
        expect(screen.getByText(/Exporting/i)).toBeInTheDocument();
      });
    });

    it('should handle export errors gracefully', async () => {
      const user = userEvent.setup();
      const error = new Error('Network error');
      mockOnExport.mockRejectedValueOnce(error);

      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      const buttons = screen.getAllByRole('button');
      const exportButton = buttons.find((btn) => btn.textContent?.includes('Export'));
      if (exportButton) {
        await user.click(exportButton);
      }

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });
    });
  });

  describe('Scheduling', () => {
    it('should show scheduling section when enabled', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          includeScheduling={true}
        />
      );

      expect(screen.getByText(/Schedule Export/)).toBeInTheDocument();
    });

    it('should hide scheduling section when disabled', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          includeScheduling={false}
        />
      );

      expect(screen.queryByText(/Schedule Export/)).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper form labels', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      expect(screen.getByLabelText(/Export Format/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Data Scope/)).toBeInTheDocument();
      expect(screen.getByLabelText(/File Name/)).toBeInTheDocument();
    });

    it('should have semantic button labels', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons.some((btn) => btn.textContent?.includes('Cancel'))).toBe(true);
      expect(buttons.some((btn) => btn.textContent?.includes('Export'))).toBe(true);
    });
  });

  describe('Dialog Controls', () => {
    it('should be callable to close dialog', () => {
      const { rerender } = render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      // Simulate closing
      rerender(
        <ExportDialog
          isOpen={false}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
        />
      );

      // Dialog should not render content when closed
      expect(screen.queryByText(/File Name/)).not.toBeInTheDocument();
    });

    it('should support custom title and description', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          title="Custom Title"
          description="Custom description text"
        />
      );

      expect(screen.getByText('Custom Title')).toBeInTheDocument();
      expect(screen.getByText('Custom description text')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('should show loading indicator when isLoading is true', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          isLoading={true}
        />
      );

      expect(screen.getByText(/Processing export/)).toBeInTheDocument();
    });

    it('should disable form inputs when loading', () => {
      render(
        <ExportDialog
          isOpen={true}
          onOpenChange={mockOnOpenChange}
          onExport={mockOnExport}
          isLoading={true}
        />
      );

      const input = screen.getByPlaceholderText(/export_/) as HTMLInputElement;
      expect(input).toBeDisabled();
    });
  });
});
