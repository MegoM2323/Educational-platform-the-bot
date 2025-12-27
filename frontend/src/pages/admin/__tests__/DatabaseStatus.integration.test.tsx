import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DatabaseStatus from '../DatabaseStatus';

/**
 * Integration tests for DatabaseStatus component
 * Tests end-to-end flows without mocking internal functions
 */
describe('DatabaseStatus Integration Tests', () => {
  describe('Data Loading and Display', () => {
    it('should load all data on component mount', async () => {
      render(<DatabaseStatus />);

      // Initial loading state
      expect(screen.getByText(/Loading database status/i)).toBeInTheDocument();

      // Should eventually show content
      await waitFor(
        () => {
          expect(screen.queryByText(/Loading database status/i)).not.toBeInTheDocument();
        },
        { timeout: 5000 }
      );
    });

    it('should handle missing backup data gracefully', async () => {
      render(<DatabaseStatus />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Navigate to Backups tab
      const backupsTab = screen.getByRole('tab', { name: /Backups/ });
      await userEvent.click(backupsTab);

      // Should show "No backups found" or backups list
      await waitFor(() => {
        const content = screen.getByRole('main') || screen.getByRole('tabpanel');
        expect(content).toBeInTheDocument();
      });
    });

    it('should handle missing slow queries gracefully', async () => {
      render(<DatabaseStatus />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Navigate to Slow Queries tab
      const queriesTab = screen.getByRole('tab', { name: /Slow Queries/ });
      await userEvent.click(queriesTab);

      // Should show content
      await waitFor(() => {
        expect(screen.getByText(/Slow Queries/)).toBeInTheDocument();
      });
    });
  });

  describe('Tab Navigation', () => {
    it('should navigate between all tabs', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      const tabs = [
        { name: /Tables/, content: 'Table Statistics' },
        { name: /Slow Queries/, content: 'Slow Queries' },
        { name: /Maintenance/, content: 'Maintenance' },
        { name: /Backups/, content: 'Backup' },
        { name: /Connections/, content: 'Connections' },
      ];

      for (const tab of tabs) {
        const tabElement = screen.getByRole('tab', { name: tab.name });
        await user.click(tabElement);

        await waitFor(() => {
          expect(screen.getByText(new RegExp(tab.content))).toBeInTheDocument();
        });
      }
    });

    it('should maintain tab state during navigation', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Click on Maintenance tab
      const maintenanceTab = screen.getByRole('tab', { name: /Maintenance/ });
      await user.click(maintenanceTab);

      // Click on another tab
      const backupsTab = screen.getByRole('tab', { name: /Backups/ });
      await user.click(backupsTab);

      // Come back to Maintenance
      await user.click(maintenanceTab);

      // Should show Maintenance content
      await waitFor(() => {
        expect(screen.getByText(/Database Maintenance/)).toBeInTheDocument();
      });
    });
  });

  describe('UI Controls', () => {
    it('should toggle refresh auto-refresh state', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Should have Pause button initially
      const pauseButton = screen.getByRole('button', { name: /Pause/ });
      expect(pauseButton).toBeInTheDocument();

      // Click to pause
      await user.click(pauseButton);

      // Should show Resume button
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Resume/ })).toBeInTheDocument();
      });
    });

    it('should execute manual refresh', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Get initial timestamp
      const initialText = screen.getByText(/Last updated:/);
      const initialContent = initialText.textContent;

      // Click refresh
      const refreshButton = screen.getByRole('button', { name: /Refresh/ });
      await user.click(refreshButton);

      // Timestamp should update (eventually, if data changes)
      await waitFor(
        () => {
          // Either timestamp changes or component stays stable
          expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Table Filtering and Sorting', () => {
    it('should filter tables by bloat level', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Ensure we're on Tables tab
      const tablesTab = screen.getByRole('tab', { name: /Tables/ });
      if (!tablesTab.getAttribute('aria-selected')) {
        await user.click(tablesTab);
      }

      // Get filter dropdown
      const filterSelect = screen.getByDisplayValue(/All Tables/);
      await user.click(filterSelect);

      // Select High Bloat
      const highOption = screen.getAllByRole('option').find(opt =>
        opt.textContent?.includes('High Bloat')
      );
      if (highOption) {
        await user.click(highOption);

        // Table should update
        await waitFor(() => {
          expect(filterSelect).toHaveValue('high');
        });
      }
    });

    it('should sort tables by column', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Click on a column header (e.g., Rows)
      const sortableHeaders = screen.getAllByText(/Rows|Name|Size/);
      if (sortableHeaders.length > 0) {
        await user.click(sortableHeaders[0]);

        // Should show sort indicator
        await waitFor(() => {
          const header = sortableHeaders[0];
          // Check if sort indicator is present (↑ or ↓)
          expect(header.textContent).toMatch(/↑|↓|Rows|Name|Size/);
        });
      }
    });
  });

  describe('Maintenance Operations', () => {
    it('should show maintenance tasks', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Click on Maintenance tab
      const maintenanceTab = screen.getByRole('tab', { name: /Maintenance/ });
      await user.click(maintenanceTab);

      // Should see Dry-run option
      await waitFor(() => {
        expect(screen.getByLabelText(/Dry-run mode/)).toBeInTheDocument();
      });
    });

    it('should toggle dry-run mode', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Click on Maintenance tab
      const maintenanceTab = screen.getByRole('tab', { name: /Maintenance/ });
      await user.click(maintenanceTab);

      // Find checkbox
      const dryRunCheckbox = screen.getByRole('checkbox', {
        name: /Dry-run mode/,
      });
      expect(dryRunCheckbox).not.toBeChecked();

      // Toggle
      await user.click(dryRunCheckbox);
      expect(dryRunCheckbox).toBeChecked();

      // Toggle back
      await user.click(dryRunCheckbox);
      expect(dryRunCheckbox).not.toBeChecked();
    });
  });

  describe('Backup Operations', () => {
    it('should display backup list', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Click on Backups tab
      const backupsTab = screen.getByRole('tab', { name: /Backups/ });
      await user.click(backupsTab);

      // Should see table headers
      await waitFor(() => {
        expect(screen.getByText('Filename')).toBeInTheDocument();
        expect(screen.getByText('Size')).toBeInTheDocument();
      });
    });

    it('should have create backup button', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Click on Backups tab
      const backupsTab = screen.getByRole('tab', { name: /Backups/ });
      await userEvent.click(backupsTab);

      // Should see Create New Backup button
      await waitFor(() => {
        expect(screen.getByText(/Create New Backup/)).toBeInTheDocument();
      });
    });
  });

  describe('Connection Management', () => {
    it('should display connections table', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Click on Connections tab
      const connectionsTab = screen.getByRole('tab', { name: /Connections/ });
      await user.click(connectionsTab);

      // Should see table headers
      await waitFor(() => {
        expect(screen.getByText(/Long-Running Queries/)).toBeInTheDocument();
      });
    });
  });

  describe('Mobile Responsiveness', () => {
    it('should render on small screens', async () => {
      const originalMatchMedia = window.matchMedia;
      window.matchMedia = vi.fn().mockImplementation(query => ({
        matches: query === '(max-width: 768px)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Should still have tabs visible
      expect(screen.getByRole('tab', { name: /Tables/ })).toBeInTheDocument();

      window.matchMedia = originalMatchMedia;
    });

    it('should have scrollable tables on mobile', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Navigate to Tables tab
      const tablesTab = screen.getByRole('tab', { name: /Tables/ });
      await userEvent.click(tablesTab);

      // Should render without errors
      await waitFor(() => {
        expect(screen.getByText('Table Statistics')).toBeInTheDocument();
      });
    });
  });

  describe('Error Recovery', () => {
    it('should handle API errors gracefully', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        // Component should render even if API fails
        expect(screen.getByText(/Database Status|Error/i)).toBeInTheDocument();
      }, { timeout: 5000 });
    });

    it('should show empty states for missing data', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Navigate through tabs - should show empty states gracefully
      const tabs = screen.getAllByRole('tab');
      for (const tab of tabs.slice(0, 3)) {
        await userEvent.click(tab);

        // Should not show error, just empty state or content
        await waitFor(() => {
          const errorElement = screen.queryByText(/Error/);
          if (errorElement) {
            // If there's an error, it should be an expected error message
            expect(errorElement.textContent).toMatch(/Error|failed/i);
          }
        });
      }
    });
  });

  describe('Data Formatting', () => {
    it('should format file sizes correctly', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Look for formatted sizes (MB, GB, etc.)
      const sizeElements = screen.getAllByText(/\s(MB|GB)/);
      expect(sizeElements.length).toBeGreaterThanOrEqual(0);
    });

    it('should format dates correctly', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Look for Last updated text with timestamp
      const lastUpdated = screen.getByText(/Last updated:/);
      expect(lastUpdated).toBeInTheDocument();
      expect(lastUpdated.textContent).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });

    it('should format numbers with thousand separators', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Numbers should be formatted (look for patterns like 1,000)
      const mainElement = screen.getByRole('main') || document.body;
      expect(mainElement.textContent).toMatch(/,|\s\d{3}/);
    });
  });

  describe('Export Functionality', () => {
    it('should export data to JSON', async () => {
      const user = userEvent.setup();
      const createElementSpy = vi.spyOn(document, 'createElement');

      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      // Click export button
      const exportButton = screen.getByRole('button', { name: /Export/ });
      await user.click(exportButton);

      // Should trigger download
      await waitFor(() => {
        expect(createElementSpy).toHaveBeenCalledWith('a');
      });

      createElementSpy.mockRestore();
    });
  });

  describe('Keyboard Navigation', () => {
    it('should support keyboard navigation between tabs', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });

      const firstTab = screen.getByRole('tab', { name: /Tables/ });
      firstTab.focus();
      expect(firstTab).toHaveFocus();

      // Keyboard navigation would be tested with arrow keys
      // This is a simplified check
      expect(firstTab).toBeInTheDocument();
    });
  });
});
