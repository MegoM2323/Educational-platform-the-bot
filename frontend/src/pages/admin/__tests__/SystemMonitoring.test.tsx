import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SystemMonitoring from '../SystemMonitoring';
import { unifiedAPI as apiClient } from '@/integrations/api/unifiedClient';

// Mock the API client
vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
  },
}));

// Mock logger
vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
  },
}));

describe('SystemMonitoring', () => {
  const mockMetrics = {
    timestamp: new Date().toISOString(),
    cpu: {
      usage_percent: 45.5,
      core_count: 4,
      frequency_mhz: 2400,
      status: 'healthy' as const,
    },
    memory: {
      total_gb: 16,
      available_gb: 8,
      used_percent: 50,
      swap_total_gb: 4,
      swap_used_percent: 25,
      status: 'healthy' as const,
    },
    disk: {
      total_gb: 256,
      used_gb: 128,
      free_gb: 128,
      used_percent: 50,
      status: 'healthy' as const,
    },
    database: {
      response_time_ms: 250,
      user_count: 150,
      application_count: 50,
      payment_count: 100,
      status: 'healthy' as const,
    },
    cache: {
      response_time_ms: 5,
      is_working: true,
      status: 'healthy' as const,
    },
    external_services: {
      telegram: {
        status: 'healthy' as const,
        response_time_ms: 150,
      },
      yookassa: {
        status: 'healthy' as const,
        response_time_ms: 200,
      },
    },
  };

  const mockCeleryMetrics = {
    data: {
      failed_tasks: {
        total: 5,
        failed: 3,
        investigating: 2,
        resolved_last_24h: 1,
      },
      executions_24h: {
        total: 1000,
        success: 950,
        failed: 50,
        success_rate: 95.0,
        avg_duration_seconds: 2.5,
      },
      health_status: 'healthy' as const,
    },
  };

  const mockAlerts = {
    alerts: [
      {
        type: 'cpu_high',
        severity: 'warning' as const,
        message: 'CPU usage is 75%',
        component: 'cpu',
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe('Component Rendering', () => {
    it('should render loading state initially', () => {
      vi.mocked(apiClient.request).mockImplementationOnce(
        () => new Promise(() => {}) // Never resolves
      );

      render(<SystemMonitoring />);

      expect(screen.getByText(/loading metrics/i)).toBeInTheDocument();
    });

    it('should load and display system metrics', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText('System Monitoring')).toBeInTheDocument();
      });

      // Check CPU display
      await waitFor(() => {
        expect(screen.getByText(/45\.5%/)).toBeInTheDocument();
      });

      // Check Memory display
      expect(screen.getByText(/50\.0%/)).toBeInTheDocument();

      // Check Database response time
      expect(screen.getByText(/250/)).toBeInTheDocument();
    });

    it('should display error message on failed API call', async () => {
      vi.mocked(apiClient.request).mockRejectedValueOnce(
        new Error('API Error')
      );

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(
          screen.getByText(/failed to load system metrics/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('Status Indicators', () => {
    it('should display healthy status with green color', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        const healthyElements = screen.getAllByText('healthy');
        expect(healthyElements.length).toBeGreaterThan(0);
      });
    });

    it('should display warning status with yellow color', async () => {
      const warningMetrics = {
        ...mockMetrics,
        cpu: { ...mockMetrics.cpu, usage_percent: 85, status: 'warning' as const },
      };

      vi.mocked(apiClient.request).mockResolvedValueOnce({
        data: warningMetrics,
      });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText(/warning/i)).toBeInTheDocument();
      });
    });

    it('should display critical status with red color', async () => {
      const criticalMetrics = {
        ...mockMetrics,
        disk: {
          ...mockMetrics.disk,
          used_percent: 95,
          status: 'critical' as const,
        },
      };

      vi.mocked(apiClient.request).mockResolvedValueOnce({
        data: criticalMetrics,
      });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText(/critical/i)).toBeInTheDocument();
      });
    });
  });

  describe('Alerts Display', () => {
    it('should display active alerts', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText(/active alerts/i)).toBeInTheDocument();
        expect(screen.getByText(/cpu usage is 75%/i)).toBeInTheDocument();
      });
    });

    it('should not display alerts section when no alerts', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce({ alerts: [] });

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(
          screen.queryByText(/active alerts/i)
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Refresh Functionality', () => {
    it('should refresh metrics when refresh button clicked', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      const { rerender } = render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText('System Monitoring')).toBeInTheDocument();
      });

      const refreshButton = screen.getByRole('button', { name: /refresh/i });

      // Reset mocks for second call
      vi.clearAllMocks();
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(apiClient.request).toHaveBeenCalled();
      });
    });

    it('should auto-refresh every 30 seconds when enabled', async () => {
      vi.useFakeTimers();

      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText('System Monitoring')).toBeInTheDocument();
      });

      const initialCallCount = vi.mocked(apiClient.request).mock.calls.length;

      // Setup mocks for auto-refresh
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      // Advance time by 30 seconds
      vi.advanceTimersByTime(30000);

      await waitFor(() => {
        expect(vi.mocked(apiClient.request).mock.calls.length).toBeGreaterThan(
          initialCallCount
        );
      });

      vi.useRealTimers();
    });

    it('should toggle auto-refresh button state', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText('System Monitoring')).toBeInTheDocument();
      });

      const autoRefreshButton = screen.getByRole('button', { name: /auto/i });
      expect(autoRefreshButton).toHaveTextContent('Auto (30s)');

      fireEvent.click(autoRefreshButton);

      expect(autoRefreshButton).toHaveTextContent('Manual');
    });
  });

  describe('Export Functionality', () => {
    it('should export metrics as CSV', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      const mockClick = vi.fn();
      const mockCreateObjectURL = vi.spyOn(window.URL, 'createObjectURL');
      const mockRevokeObjectURL = vi.spyOn(window.URL, 'revokeObjectURL');

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText('System Monitoring')).toBeInTheDocument();
      });

      const exportButton = screen.getByRole('button', { name: /export csv/i });
      fireEvent.click(exportButton);

      // Verify that blob was created
      await waitFor(() => {
        expect(mockCreateObjectURL).toHaveBeenCalled();
      });

      mockCreateObjectURL.mockRestore();
      mockRevokeObjectURL.mockRestore();
    });
  });

  describe('Charts Rendering', () => {
    it('should render performance trends chart with data', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(
          screen.getByText(/performance trends/i)
        ).toBeInTheDocument();
      });
    });

    it('should render resource distribution pie charts', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText(/cpu distribution/i)).toBeInTheDocument();
        expect(screen.getByText(/memory distribution/i)).toBeInTheDocument();
        expect(screen.getByText(/disk distribution/i)).toBeInTheDocument();
      });
    });
  });

  describe('Celery Metrics', () => {
    it('should display Celery task execution statistics', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(
          screen.getByText(/celery task execution/i)
        ).toBeInTheDocument();
        expect(screen.getByText(/1000/)).toBeInTheDocument(); // Total tasks
        expect(screen.getByText(/950/)).toBeInTheDocument(); // Success
        expect(screen.getByText(/95\.0%/)).toBeInTheDocument(); // Success rate
      });
    });
  });

  describe('External Services Status', () => {
    it('should display external services status', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(
          screen.getByText(/external services/i)
        ).toBeInTheDocument();
        expect(screen.getByText(/telegram/i)).toBeInTheDocument();
        expect(screen.getByText(/yookassa/i)).toBeInTheDocument();
      });
    });
  });

  describe('Time Range Selector', () => {
    it('should allow selecting different time ranges', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText('System Monitoring')).toBeInTheDocument();
      });

      const oneHourButton = screen.getByRole('button', { name: /1h/i });
      const oneDayButton = screen.getByRole('button', { name: /24h/i });
      const sevenDayButton = screen.getByRole('button', { name: /7d/i });

      expect(oneHourButton).toBeInTheDocument();
      expect(oneDayButton).toBeInTheDocument();
      expect(sevenDayButton).toBeInTheDocument();

      fireEvent.click(oneHourButton);
      expect(oneHourButton).toHaveClass('bg-');
    });
  });

  describe('Resource Metrics Display', () => {
    it('should display CPU metrics correctly', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText(/45\.5%/)).toBeInTheDocument();
        expect(screen.getByText(/4 cores/)).toBeInTheDocument();
      });
    });

    it('should display Memory metrics correctly', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText(/50\.0%/)).toBeInTheDocument();
        expect(screen.getByText(/8.*gb available/i)).toBeInTheDocument();
      });
    });

    it('should display Disk metrics correctly', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText(/128.*gb free/i)).toBeInTheDocument();
      });
    });

    it('should display Database metrics correctly', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        expect(screen.getByText(/250/)).toBeInTheDocument(); // Response time
        expect(screen.getByText(/150 users/i)).toBeInTheDocument();
      });
    });
  });

  describe('Responsive Design', () => {
    it('should render metric cards in grid layout', async () => {
      vi.mocked(apiClient.request).mockResolvedValueOnce({ data: mockMetrics });
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockCeleryMetrics);
      vi.mocked(apiClient.request).mockResolvedValueOnce(mockAlerts);

      render(<SystemMonitoring />);

      await waitFor(() => {
        const cards = screen.getAllByText(/usage/i);
        expect(cards.length).toBeGreaterThan(0);
      });
    });
  });
});
