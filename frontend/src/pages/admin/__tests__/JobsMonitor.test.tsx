import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import JobsMonitor from '../JobsMonitor';
import * as unifiedClientModule from '@/integrations/api/unifiedClient';

// Mock modules
vi.mock('@/integrations/api/unifiedClient');
vi.mock('@/services/websocketService');
vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

// Mock data
const mockWorkers = [
  {
    name: 'celery@worker1',
    status: 'online' as const,
    heartbeat: new Date().toISOString(),
    active_tasks: 3,
    memory_usage_mb: 256,
    cpu_usage_percent: 45.5,
  },
  {
    name: 'celery@worker2',
    status: 'offline' as const,
    heartbeat: new Date(Date.now() - 60000).toISOString(),
    active_tasks: 0,
    memory_usage_mb: 128,
    cpu_usage_percent: 0,
  },
];

const mockQueues = [
  { name: 'default', length: 15, retention_policy: 'FIFO' },
  { name: 'priority', length: 3, retention_policy: 'Priority-based' },
  { name: 'scheduled', length: 5, retention_policy: 'Time-based' },
];

const mockActiveTasks = [
  {
    id: 'task-1',
    name: 'send_email',
    worker: 'celery@worker1',
    started_at: new Date(Date.now() - 30000).toISOString(),
    duration_seconds: 30,
    status: 'active' as const,
    progress: 75,
    args: '["user@example.com"]',
    kwargs: '{}',
  },
  {
    id: 'task-2',
    name: 'process_video',
    worker: 'celery@worker1',
    started_at: new Date(Date.now() - 60000).toISOString(),
    duration_seconds: 60,
    status: 'active' as const,
    progress: 45,
  },
];

const mockCompletedTasks = [
  {
    id: 'completed-1',
    name: 'send_sms',
    worker: 'celery@worker1',
    duration_seconds: 2.5,
    timestamp: new Date(Date.now() - 300000).toISOString(),
    status: 'success' as const,
  },
];

const mockFailedTasks = [
  {
    id: 'failed-1',
    name: 'send_notification',
    worker: 'celery@worker2',
    duration_seconds: 5,
    timestamp: new Date(Date.now() - 120000).toISOString(),
    status: 'failed' as const,
    error_message: 'Connection timeout to external service',
  },
];

const mockStatistics = {
  total_completed: 1250,
  total_failed: 12,
  total_pending: 23,
  total_active: 5,
  success_rate_percent: 98.5,
  avg_duration_seconds: 15.3,
  error_rate_percent: 1.5,
};

describe('JobsMonitor', () => {
  let mockApiClient: any;

  beforeEach(() => {
    // Setup API mock
    mockApiClient = {
      request: vi.fn(),
    };
    vi.spyOn(unifiedClientModule, 'unifiedAPI', 'get').mockReturnValue(mockApiClient);

    // Mock localStorage
    Storage.prototype.getItem = vi.fn((key: string) => {
      if (key === 'auth_token') return 'mock-token';
      return null;
    });

    // Default API response
    mockApiClient.request.mockResolvedValue({
      data: {
        workers: mockWorkers,
        queues: mockQueues,
        active_tasks: mockActiveTasks,
        completed_tasks: mockCompletedTasks,
        failed_tasks: mockFailedTasks,
        statistics: mockStatistics,
      },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render the page title and description', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('Background Jobs Monitor')).toBeInTheDocument();
        expect(screen.getByText('Monitor Celery tasks, workers, and queues')).toBeInTheDocument();
      });
    });

    it('should display worker status grid', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('celery@worker1')).toBeInTheDocument();
        expect(screen.getByText('celery@worker2')).toBeInTheDocument();
      });
    });

    it('should display worker metrics', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getAllByText(/Active Tasks:/)).toHaveLength(2);
        expect(screen.getAllByText(/Memory:/)).toHaveLength(2);
        expect(screen.getAllByText(/CPU:/)).toHaveLength(2);
      });
    });

    it('should display queue status cards', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('default')).toBeInTheDocument();
        expect(screen.getByText('priority')).toBeInTheDocument();
        expect(screen.getByText('scheduled')).toBeInTheDocument();
      });
    });

    it('should display task statistics', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('Completed')).toBeInTheDocument();
        expect(screen.getByText('Failed')).toBeInTheDocument();
        expect(screen.getByText('Pending')).toBeInTheDocument();
        expect(screen.getByText('Success Rate')).toBeInTheDocument();
      });
    });

    it('should display active tasks table with correct columns', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('Task Name')).toBeInTheDocument();
        expect(screen.getByText('Worker')).toBeInTheDocument();
        expect(screen.getByText('Started')).toBeInTheDocument();
        expect(screen.getByText('Duration')).toBeInTheDocument();
        expect(screen.getByText('Progress')).toBeInTheDocument();
        expect(screen.getByText('Status')).toBeInTheDocument();
      });
    });

    it('should display active tasks in table', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('send_email')).toBeInTheDocument();
        expect(screen.getByText('process_video')).toBeInTheDocument();
      });
    });

    it('should display completed tasks tab', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText(/Completed \(1\)/)).toBeInTheDocument();
      });
    });

    it('should display failed tasks tab', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText(/Failed \(1\)/)).toBeInTheDocument();
      });
    });
  });

  describe('User Interactions', () => {
    it('should kill a task when button is clicked and confirmed', async () => {
      mockApiClient.request.mockResolvedValue({ data: { success: true } });
      window.confirm = vi.fn().mockReturnValue(true);

      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('send_email')).toBeInTheDocument();
      });

      const killButtons = screen.getAllByText('Kill');
      fireEvent.click(killButtons[0]);

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalledWith(
          'Are you sure you want to kill this task?'
        );
        expect(mockApiClient.request).toHaveBeenCalledWith(
          '/admin/tasks/task-1/kill/',
          expect.any(Object)
        );
      });
    });

    it('should not kill a task if not confirmed', async () => {
      window.confirm = vi.fn().mockReturnValue(false);

      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('send_email')).toBeInTheDocument();
      });

      const killButtons = screen.getAllByText('Kill');
      fireEvent.click(killButtons[0]);

      expect(mockApiClient.request).not.toHaveBeenCalledWith(
        expect.stringContaining('/kill/'),
        expect.any(Object)
      );
    });

    it('should purge a queue when button is clicked and confirmed', async () => {
      mockApiClient.request.mockResolvedValue({ data: { success: true } });
      window.confirm = vi.fn().mockReturnValue(true);

      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getAllByText('Purge')).toHaveLength(3);
      });

      const purgeButtons = screen.getAllByText('Purge');
      fireEvent.click(purgeButtons[0]);

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalledWith(
          expect.stringContaining('purge the')
        );
        expect(mockApiClient.request).toHaveBeenCalledWith(
          '/admin/queues/default/purge/',
          expect.any(Object)
        );
      });
    });

    it('should refresh data when refresh button is clicked', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('Background Jobs Monitor')).toBeInTheDocument();
      });

      const refreshButton = screen.getByText('Refresh');
      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(mockApiClient.request).toHaveBeenCalledWith(
          '/admin/system/tasks/',
          expect.any(Object)
        );
      });
    });

    it('should sort active tasks by started time', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('send_email')).toBeInTheDocument();
      });

      const sortByStartedButton = screen.getByText('Sort by Started');
      fireEvent.click(sortByStartedButton);

      // After sorting, tasks should still be visible
      await waitFor(() => {
        expect(screen.getByText('send_email')).toBeInTheDocument();
        expect(screen.getByText('process_video')).toBeInTheDocument();
      });
    });

    it('should sort active tasks by duration', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('send_email')).toBeInTheDocument();
      });

      const sortByDurationButton = screen.getByText('Sort by Duration');
      fireEvent.click(sortByDurationButton);

      // After sorting, tasks should still be visible
      await waitFor(() => {
        expect(screen.getByText('send_email')).toBeInTheDocument();
        expect(screen.getByText('process_video')).toBeInTheDocument();
      });
    });

    it('should switch to completed tasks tab', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('Completed (1)')).toBeInTheDocument();
      });

      const completedTab = screen.getByText('Completed (1)');
      fireEvent.click(completedTab);

      await waitFor(() => {
        expect(screen.getByText('send_sms')).toBeInTheDocument();
      });
    });

    it('should switch to failed tasks tab', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('Failed (1)')).toBeInTheDocument();
      });

      const failedTab = screen.getByText('Failed (1)');
      fireEvent.click(failedTab);

      await waitFor(() => {
        expect(screen.getByText('send_notification')).toBeInTheDocument();
      });
    });

    it('should retry a failed task', async () => {
      mockApiClient.request.mockResolvedValue({ data: { success: true } });

      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('Failed (1)')).toBeInTheDocument();
      });

      const failedTab = screen.getByText('Failed (1)');
      fireEvent.click(failedTab);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(mockApiClient.request).toHaveBeenCalledWith(
          '/admin/tasks/failed-1/retry/',
          expect.any(Object)
        );
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error alert if API request fails', async () => {
      mockApiClient.request.mockRejectedValue(new Error('Network error'));

      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load monitoring data/)).toBeInTheDocument();
      });
    });

    it('should display error when killing task fails', async () => {
      mockApiClient.request.mockRejectedValueOnce(new Error('Kill failed'));
      window.confirm = vi.fn().mockReturnValue(true);

      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('send_email')).toBeInTheDocument();
      });

      const killButtons = screen.getAllByText('Kill');
      fireEvent.click(killButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/Failed to kill task/)).toBeInTheDocument();
      });
    });

    it('should handle empty workers list', async () => {
      mockApiClient.request.mockResolvedValue({
        data: {
          workers: [],
          queues: mockQueues,
          active_tasks: mockActiveTasks,
          completed_tasks: mockCompletedTasks,
          failed_tasks: mockFailedTasks,
          statistics: mockStatistics,
        },
      });

      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('No workers found')).toBeInTheDocument();
      });
    });

    it('should handle empty queues list', async () => {
      mockApiClient.request.mockResolvedValue({
        data: {
          workers: mockWorkers,
          queues: [],
          active_tasks: mockActiveTasks,
          completed_tasks: mockCompletedTasks,
          failed_tasks: mockFailedTasks,
          statistics: mockStatistics,
        },
      });

      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('No queues found')).toBeInTheDocument();
      });
    });

    it('should handle empty active tasks list', async () => {
      mockApiClient.request.mockResolvedValue({
        data: {
          workers: mockWorkers,
          queues: mockQueues,
          active_tasks: [],
          completed_tasks: mockCompletedTasks,
          failed_tasks: mockFailedTasks,
          statistics: mockStatistics,
        },
      });

      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('No active tasks')).toBeInTheDocument();
      });
    });

    it('should handle null statistics', async () => {
      mockApiClient.request.mockResolvedValue({
        data: {
          workers: mockWorkers,
          queues: mockQueues,
          active_tasks: mockActiveTasks,
          completed_tasks: mockCompletedTasks,
          failed_tasks: mockFailedTasks,
          statistics: null,
        },
      });

      render(<JobsMonitor />);

      await waitFor(() => {
        // Should render without statistics section
        expect(screen.getByText('celery@worker1')).toBeInTheDocument();
      });
    });
  });

  describe('Data Loading', () => {
    it('should load data on component mount', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(mockApiClient.request).toHaveBeenCalledWith(
          '/admin/system/tasks/',
          expect.any(Object)
        );
      });
    });

    it('should update counts in tabs', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText(/Active Tasks \(2\)/)).toBeInTheDocument();
        expect(screen.getByText(/Completed \(1\)/)).toBeInTheDocument();
        expect(screen.getByText(/Failed \(1\)/)).toBeInTheDocument();
      });
    });
  });

  describe('Performance Indicators', () => {
    it('should show worker memory usage', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('256MB')).toBeInTheDocument();
        expect(screen.getByText('128MB')).toBeInTheDocument();
      });
    });

    it('should show worker CPU usage', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        expect(screen.getByText('45.5%')).toBeInTheDocument();
      });
    });

    it('should display active tasks with all details', async () => {
      render(<JobsMonitor />);

      await waitFor(() => {
        // Check that active tasks are rendered with worker info
        expect(screen.getByText('celery@worker1')).toBeInTheDocument();
        expect(screen.getAllByText('celery@worker1').length).toBeGreaterThan(1);
      });
    });
  });
});
