import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DatabaseStatus from '../DatabaseStatus';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

// Mock the API client
vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
  },
}));

// Mock the logger
vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('DatabaseStatus Component', () => {
  const mockDatabaseStatus = {
    database_type: 'PostgreSQL',
    database_version: '15.2',
    database_size_mb: 2048.5,
    connection_pool_active: 15,
    connection_pool_max: 20,
    last_backup_timestamp: '2025-12-27T10:00:00Z',
    backup_status: 'completed' as const,
    health_status: 'green' as const,
    last_check_timestamp: '2025-12-27T12:30:00Z',
    alerts: [
      {
        id: '1',
        severity: 'warning' as const,
        message: 'Table bloat detected',
        component: 'storage',
        timestamp: '2025-12-27T12:00:00Z',
      },
    ],
  };

  const mockTableStatistics = [
    {
      name: 'users',
      row_count: 1000,
      size_mb: 50.5,
      last_vacuum: '2025-12-27T10:00:00Z',
      last_reindex: '2025-12-27T09:00:00Z',
      bloat_percentage: 5.2,
      bloat_level: 'low' as const,
    },
    {
      name: 'messages',
      row_count: 5000,
      size_mb: 150.2,
      last_vacuum: '2025-12-27T08:00:00Z',
      last_reindex: null,
      bloat_percentage: 15.5,
      bloat_level: 'medium' as const,
    },
    {
      name: 'sessions',
      row_count: 100,
      size_mb: 5.3,
      last_vacuum: null,
      last_reindex: null,
      bloat_percentage: 45.2,
      bloat_level: 'high' as const,
    },
  ];

  const mockSlowQueries = [
    {
      id: '1',
      query: 'SELECT * FROM users WHERE created_at > NOW() - INTERVAL 7 days',
      count: 42,
      avg_time_ms: 234.5,
      max_time_ms: 1023.4,
      min_time_ms: 45.2,
    },
    {
      id: '2',
      query: 'SELECT * FROM messages WHERE user_id IN (...)',
      count: 128,
      avg_time_ms: 512.3,
      max_time_ms: 2043.1,
      min_time_ms: 125.5,
    },
  ];

  const mockBackups = [
    {
      id: '1',
      filename: 'backup_2025_12_27_120000.sql',
      size_mb: 512.5,
      created_date: '2025-12-27T12:00:00Z',
      status: 'completed' as const,
    },
    {
      id: '2',
      filename: 'backup_2025_12_26_120000.sql',
      size_mb: 510.2,
      created_date: '2025-12-26T12:00:00Z',
      status: 'completed' as const,
    },
  ];

  const mockConnections = [
    {
      pid: 1234,
      query: 'SELECT * FROM large_table WHERE id > 1000000',
      started_at: '2025-12-27T10:30:00Z',
      duration_seconds: 245,
      user: 'postgres',
    },
    {
      pid: 1235,
      query: 'UPDATE table SET column = value WHERE condition',
      started_at: '2025-12-27T11:00:00Z',
      duration_seconds: 125,
      user: 'app_user',
    },
  ];

  const mockMaintenanceTasks = [
    {
      name: 'Vacuum',
      last_run: '2025-12-27T10:00:00Z',
      estimated_duration_minutes: 5,
      description: 'Clean up dead tuples',
    },
    {
      name: 'Reindex',
      last_run: null,
      estimated_duration_minutes: 10,
      description: 'Rebuild database indexes',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock successful API responses
    (unifiedAPI.request as any).mockImplementation((endpoint: string) => {
      switch (endpoint) {
        case '/admin/system/database/':
          return Promise.resolve({ data: mockDatabaseStatus });
        case '/admin/system/database/tables/':
          return Promise.resolve({ data: { tables: mockTableStatistics } });
        case '/admin/system/database/queries/':
          return Promise.resolve({ data: { queries: mockSlowQueries } });
        case '/admin/system/database/backups/':
          return Promise.resolve({ data: { backups: mockBackups } });
        case '/admin/system/database/connections/':
          return Promise.resolve({ data: { connections: mockConnections } });
        case '/admin/system/database/maintenance/':
          return Promise.resolve({ data: { tasks: mockMaintenanceTasks } });
        default:
          return Promise.resolve({ data: null });
      }
    });
  });

  describe('Component Rendering', () => {
    it('should render the component with header', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Status')).toBeInTheDocument();
      });
    });

    it('should display loading state initially', () => {
      render(<DatabaseStatus />);
      expect(screen.getByText(/Loading database status/i)).toBeInTheDocument();
    });

    it('should load and display database status', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('PostgreSQL')).toBeInTheDocument();
        expect(screen.getByText('15.2')).toBeInTheDocument();
      });
    });

    it('should display all tabs', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Tables/ })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /Slow Queries/ })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /Maintenance/ })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /Backups/ })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /Connections/ })).toBeInTheDocument();
      });
    });

    it('should display database overview card', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Database Overview')).toBeInTheDocument();
        expect(screen.getByText('Database Type')).toBeInTheDocument();
        expect(screen.getByText('Version')).toBeInTheDocument();
      });
    });

    it('should display health status indicator', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('Healthy')).toBeInTheDocument();
      });
    });
  });

  describe('Table Statistics Tab', () => {
    it('should render table statistics', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('users')).toBeInTheDocument();
        expect(screen.getByText('messages')).toBeInTheDocument();
        expect(screen.getByText('sessions')).toBeInTheDocument();
      });
    });

    it('should display row count', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('1,000')).toBeInTheDocument();
        expect(screen.getByText('5,000')).toBeInTheDocument();
      });
    });

    it('should display bloat percentages with color coding', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('5.2%')).toBeInTheDocument();
        expect(screen.getByText('15.5%')).toBeInTheDocument();
        expect(screen.getByText('45.2%')).toBeInTheDocument();
      });
    });

    it('should filter tables by bloat level', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('users')).toBeInTheDocument();
      });

      // Switch to High Bloat filter
      const filter = screen.getByDisplayValue('All Tables');
      await user.click(filter);
      const option = screen.getByRole('option', { name: /High Bloat/ });
      await user.click(option);

      // Should only show high bloat tables
      await waitFor(() => {
        expect(screen.getByText('sessions')).toBeInTheDocument();
        expect(screen.queryByText('users')).not.toBeInTheDocument();
      });
    });

    it('should sort tables by column', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('users')).toBeInTheDocument();
      });

      // Click on Rows header to sort
      const rowsHeader = screen.getByText(/Rows/);
      fireEvent.click(rowsHeader);

      // Check that sort indicator appears
      await waitFor(() => {
        expect(rowsHeader.textContent).toMatch(/↑|↓/);
      });
    });

    it('should paginate table statistics', async () => {
      // Create a large number of tables to test pagination
      const largeMockTables = Array.from({ length: 25 }, (_, i) => ({
        ...mockTableStatistics[0],
        name: `table_${i}`,
      }));

      (unifiedAPI.request as any).mockImplementation((endpoint: string) => {
        if (endpoint === '/admin/system/database/tables/') {
          return Promise.resolve({ data: { tables: largeMockTables } });
        }
        return Promise.resolve({ data: null });
      });

      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText('table_0')).toBeInTheDocument();
      });

      // Check pagination exists
      expect(screen.getByText(/Page 1 of/)).toBeInTheDocument();
    });
  });

  describe('Slow Queries Tab', () => {
    it('should render slow queries', async () => {
      render(<DatabaseStatus />);

      // Click on Slow Queries tab
      const queriesTab = screen.getByRole('tab', { name: /Slow Queries/ });
      await userEvent.click(queriesTab);

      await waitFor(() => {
        expect(screen.getByText(/SELECT \* FROM users WHERE/)).toBeInTheDocument();
      });
    });

    it('should display query statistics', async () => {
      render(<DatabaseStatus />);

      const queriesTab = screen.getByRole('tab', { name: /Slow Queries/ });
      await userEvent.click(queriesTab);

      await waitFor(() => {
        expect(screen.getByText('Count')).toBeInTheDocument();
        expect(screen.getByText('Avg (ms)')).toBeInTheDocument();
        expect(screen.getByText('Max (ms)')).toBeInTheDocument();
      });
    });

    it('should expand query to show full text', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      const queriesTab = screen.getByRole('tab', { name: /Slow Queries/ });
      await user.click(queriesTab);

      await waitFor(() => {
        expect(screen.getByText(/SELECT \* FROM users WHERE/)).toBeInTheDocument();
      });

      // Find and click expand button
      const expandButtons = screen.getAllByRole('button').filter(btn =>
        btn.querySelector('svg')
      );
      if (expandButtons.length > 0) {
        await user.click(expandButtons[0]);
      }
    });
  });

  describe('Maintenance Operations Tab', () => {
    it('should render maintenance tasks', async () => {
      render(<DatabaseStatus />);

      const maintenanceTab = screen.getByRole('tab', { name: /Maintenance/ });
      await userEvent.click(maintenanceTab);

      await waitFor(() => {
        expect(screen.getByText('Vacuum')).toBeInTheDocument();
        expect(screen.getByText('Reindex')).toBeInTheDocument();
      });
    });

    it('should display dry-run checkbox', async () => {
      render(<DatabaseStatus />);

      const maintenanceTab = screen.getByRole('tab', { name: /Maintenance/ });
      await userEvent.click(maintenanceTab);

      await waitFor(() => {
        expect(screen.getByLabelText(/Dry-run mode/)).toBeInTheDocument();
      });
    });

    it('should execute maintenance operation', async () => {
      const user = userEvent.setup();
      (unifiedAPI.request as any).mockImplementation((endpoint: string, options?: any) => {
        if (endpoint === '/admin/database/maintenance/' && options?.method === 'POST') {
          return Promise.resolve({
            data: {
              success: true,
              message: 'Vacuum completed',
              data: { disk_freed_mb: 100, duration_seconds: 45 },
            },
          });
        }
        return Promise.resolve({ data: null });
      });

      render(<DatabaseStatus />);

      const maintenanceTab = screen.getByRole('tab', { name: /Maintenance/ });
      await user.click(maintenanceTab);

      await waitFor(() => {
        expect(screen.getByText('Vacuum')).toBeInTheDocument();
      });

      // Click Run Vacuum button
      const vacuumButton = screen.getByText(/Run Vacuum/);
      await user.click(vacuumButton);

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText(/Vacuum completed/)).toBeInTheDocument();
      });
    });

    it('should toggle dry-run mode', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      const maintenanceTab = screen.getByRole('tab', { name: /Maintenance/ });
      await user.click(maintenanceTab);

      await waitFor(() => {
        expect(screen.getByLabelText(/Dry-run mode/)).toBeInTheDocument();
      });

      const dryRunCheckbox = screen.getByRole('checkbox', { name: /Dry-run mode/ });
      expect(dryRunCheckbox).not.toBeChecked();

      await user.click(dryRunCheckbox);
      expect(dryRunCheckbox).toBeChecked();
    });
  });

  describe('Backup Management Tab', () => {
    it('should render backups', async () => {
      render(<DatabaseStatus />);

      const backupsTab = screen.getByRole('tab', { name: /Backups/ });
      await userEvent.click(backupsTab);

      await waitFor(() => {
        expect(screen.getByText('backup_2025_12_27_120000.sql')).toBeInTheDocument();
      });
    });

    it('should display backup information', async () => {
      render(<DatabaseStatus />);

      const backupsTab = screen.getByRole('tab', { name: /Backups/ });
      await userEvent.click(backupsTab);

      await waitFor(() => {
        expect(screen.getByText('Filename')).toBeInTheDocument();
        expect(screen.getByText('Size')).toBeInTheDocument();
        expect(screen.getByText('Created Date')).toBeInTheDocument();
      });
    });

    it('should create new backup', async () => {
      const user = userEvent.setup();
      (unifiedAPI.request as any).mockImplementation((endpoint: string, options?: any) => {
        if (endpoint === '/admin/database/backup/' && options?.method === 'POST') {
          return Promise.resolve({
            data: {
              id: '3',
              filename: 'backup_2025_12_27_130000.sql',
              size_mb: 515.2,
              created_date: '2025-12-27T13:00:00Z',
              status: 'completed',
            },
          });
        }
        return Promise.resolve({ data: null });
      });

      render(<DatabaseStatus />);

      const backupsTab = screen.getByRole('tab', { name: /Backups/ });
      await user.click(backupsTab);

      await waitFor(() => {
        expect(screen.getByText(/Create New Backup/)).toBeInTheDocument();
      });

      const createButton = screen.getByText(/Create New Backup/);
      await user.click(createButton);

      // Should reload data
      await waitFor(() => {
        expect(unifiedAPI.request).toHaveBeenCalledWith(
          '/admin/database/backup/',
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('should delete backup with confirmation', async () => {
      const user = userEvent.setup();
      (unifiedAPI.request as any).mockImplementation((endpoint: string, options?: any) => {
        if (endpoint === '/admin/database/backup/1/' && options?.method === 'DELETE') {
          return Promise.resolve({ data: null });
        }
        return Promise.resolve({ data: null });
      });

      render(<DatabaseStatus />);

      const backupsTab = screen.getByRole('tab', { name: /Backups/ });
      await user.click(backupsTab);

      await waitFor(() => {
        expect(screen.getByText('backup_2025_12_27_120000.sql')).toBeInTheDocument();
      });

      // Find and click delete button
      const deleteButtons = screen.getAllByRole('button').filter(btn =>
        btn.getAttribute('title')?.includes('Delete')
      );
      if (deleteButtons.length > 0) {
        await user.click(deleteButtons[0]);
      }

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByText(/Delete Backup/)).toBeInTheDocument();
      });
    });

    it('should paginate backups', async () => {
      // Create enough backups to require pagination
      const largeBackups = Array.from({ length: 15 }, (_, i) => ({
        ...mockBackups[0],
        id: `${i}`,
        filename: `backup_${i}.sql`,
      }));

      (unifiedAPI.request as any).mockImplementation((endpoint: string) => {
        if (endpoint === '/admin/system/database/backups/') {
          return Promise.resolve({ data: { backups: largeBackups } });
        }
        return Promise.resolve({ data: null });
      });

      render(<DatabaseStatus />);

      const backupsTab = screen.getByRole('tab', { name: /Backups/ });
      await userEvent.click(backupsTab);

      await waitFor(() => {
        expect(screen.getByText(/Page 1 of/)).toBeInTheDocument();
      });
    });
  });

  describe('Connections & Queries Tab', () => {
    it('should render long-running queries', async () => {
      render(<DatabaseStatus />);

      const connectionsTab = screen.getByRole('tab', { name: /Connections/ });
      await userEvent.click(connectionsTab);

      await waitFor(() => {
        expect(screen.getByText(/Long-Running Queries/)).toBeInTheDocument();
      });
    });

    it('should display connection details', async () => {
      render(<DatabaseStatus />);

      const connectionsTab = screen.getByRole('tab', { name: /Connections/ });
      await userEvent.click(connectionsTab);

      await waitFor(() => {
        expect(screen.getByText('User')).toBeInTheDocument();
        expect(screen.getByText('PID')).toBeInTheDocument();
      });
    });

    it('should kill query with confirmation', async () => {
      const user = userEvent.setup();
      (unifiedAPI.request as any).mockImplementation((endpoint: string, options?: any) => {
        if (endpoint === '/admin/database/kill-query/' && options?.method === 'POST') {
          return Promise.resolve({
            data: { success: true, message: 'Query terminated' },
          });
        }
        return Promise.resolve({ data: null });
      });

      render(<DatabaseStatus />);

      const connectionsTab = screen.getByRole('tab', { name: /Connections/ });
      await user.click(connectionsTab);

      await waitFor(() => {
        expect(screen.getByText(/Long-Running Queries/)).toBeInTheDocument();
      });

      // Find and click kill button
      const killButtons = screen.getAllByRole('button').filter(btn =>
        btn.getAttribute('title')?.includes('Terminate')
      );
      if (killButtons.length > 0) {
        await user.click(killButtons[0]);
      }

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByText(/Terminate Query/)).toBeInTheDocument();
      });
    });
  });

  describe('Refresh and Auto-refresh', () => {
    it('should have refresh button', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Refresh/ })).toBeInTheDocument();
      });
    });

    it('should have pause/resume button', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Pause/ })).toBeInTheDocument();
      });
    });

    it('should toggle auto-refresh', async () => {
      const user = userEvent.setup();
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Pause/ })).toBeInTheDocument();
      });

      const pauseButton = screen.getByRole('button', { name: /Pause/ });
      await user.click(pauseButton);

      // Should show Resume button
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Resume/ })).toBeInTheDocument();
      });
    });
  });

  describe('Export Functionality', () => {
    it('should have export button', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Export/ })).toBeInTheDocument();
      });
    });

    it('should export database metrics', async () => {
      const user = userEvent.setup();
      const createElementSpy = vi.spyOn(document, 'createElement');

      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Export/ })).toBeInTheDocument();
      });

      const exportButton = screen.getByRole('button', { name: /Export/ });
      await user.click(exportButton);

      // Should create a link element for download
      await waitFor(() => {
        expect(createElementSpy).toHaveBeenCalledWith('a');
      });

      createElementSpy.mockRestore();
    });
  });

  describe('Error Handling', () => {
    it('should display error message on failed load', async () => {
      (unifiedAPI.request as any).mockRejectedValue(new Error('Network error'));

      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load database information/)).toBeInTheDocument();
      });
    });

    it('should display alert for critical issues', async () => {
      const statusWithCritical = {
        ...mockDatabaseStatus,
        health_status: 'red' as const,
        alerts: [
          {
            id: '1',
            severity: 'critical' as const,
            message: 'Database connection pool exhausted',
            component: 'connections',
            timestamp: '2025-12-27T12:00:00Z',
          },
        ],
      };

      (unifiedAPI.request as any).mockImplementation((endpoint: string) => {
        if (endpoint === '/admin/system/database/') {
          return Promise.resolve({ data: statusWithCritical });
        }
        return Promise.resolve({ data: null });
      });

      render(<DatabaseStatus />);

      await waitFor(() => {
        expect(screen.getByText(/Database connection pool exhausted/)).toBeInTheDocument();
      });
    });
  });

  describe('Responsive Design', () => {
    it('should render on mobile viewport', () => {
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

      expect(screen.getByText('Database Status')).toBeInTheDocument();
    });

    it('should have responsive grid layout', async () => {
      render(<DatabaseStatus />);

      await waitFor(() => {
        const gridElements = screen.getAllByText(/Database Type|Version|Database Size/);
        expect(gridElements.length).toBeGreaterThan(0);
      });
    });
  });
});
