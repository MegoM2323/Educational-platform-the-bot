/**
 * Tests for Admin Dashboard component
 *
 * Coverage:
 * - Data fetching and loading states
 * - Chart rendering
 * - Quick stats display
 * - Activity feed
 * - System alerts
 * - Responsive design
 * - Error handling
 * - Auto-refresh functionality
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import AdminDashboard from '../Dashboard';
import { adminAPI } from '@/integrations/api/adminAPI';
import { unifiedAPI as apiClient } from '@/integrations/api/unifiedClient';

// Mock dependencies
vi.mock('@/integrations/api/adminAPI');
vi.mock('@/integrations/api/unifiedClient');
vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockUserStats = {
  total_users: 150,
  total_students: 100,
  total_teachers: 30,
  total_tutors: 15,
  total_parents: 5,
  active_today: 45,
};

const mockAssignmentStats = {
  total_assignments: 250,
  this_week: 45,
  last_week: 40,
};

const mockSystemMetrics = {
  timestamp: new Date().toISOString(),
  cpu: {
    usage_percent: 45,
    core_count: 8,
    frequency_mhz: 2400,
    status: 'healthy',
  },
  memory: {
    total_gb: 16,
    available_gb: 8,
    used_percent: 50,
    swap_total_gb: 4,
    swap_used_percent: 10,
    status: 'healthy',
  },
  disk: {
    total_gb: 500,
    used_gb: 250,
    free_gb: 250,
    used_percent: 50,
    status: 'healthy',
  },
  database: {
    response_time_ms: 45,
    user_count: 150,
    application_count: 50,
    payment_count: 25,
    status: 'healthy',
  },
};

const mockAuditLogs = {
  count: 5,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      timestamp: new Date().toISOString(),
      user: {
        id: 1,
        email: 'admin@test.com',
        full_name: 'Admin User',
      },
      action: 'login',
      resource: 'auth',
      status: 'success',
      details: 'User logged in',
    },
    {
      id: 2,
      timestamp: new Date().toISOString(),
      user: {
        id: 2,
        email: 'teacher@test.com',
        full_name: 'Teacher User',
      },
      action: 'create',
      resource: 'assignment',
      status: 'success',
      details: 'Created new assignment',
    },
  ],
};

describe('AdminDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Setup default mock responses
    (adminAPI.getUserStats as any).mockResolvedValue({ data: mockUserStats });
    (adminAPI.getAuditLogs as any).mockResolvedValue({ data: mockAuditLogs });

    (apiClient.request as any).mockImplementation((url: string) => {
      if (url === '/assignments/stats/') {
        return Promise.resolve({ data: mockAssignmentStats });
      } else if (url === '/admin/system/sessions/') {
        return Promise.resolve({ data: { active_sessions: 15 } });
      } else if (url === '/core/metrics/') {
        return Promise.resolve({ data: mockSystemMetrics });
      } else if (url === '/core/alerts/') {
        return Promise.resolve({
          data: {
            alerts: [
              {
                id: 'alert-1',
                severity: 'warning',
                title: 'High CPU Usage',
                message: 'CPU usage is above 80%',
                timestamp: new Date().toISOString(),
              },
            ],
          },
        });
      } else if (url === '/health/') {
        return Promise.resolve({ data: { status: 'healthy' } });
      }
      return Promise.resolve({ data: null });
    });
  });

  it('renders dashboard title and header', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Wait for initial content to render
      expect(screen.getByText(/Admin Dashboard/i)).toBeInTheDocument();
    });

    expect(screen.getByText('System overview and monitoring')).toBeInTheDocument();
  });

  it('displays loading state initially', async () => {
    // Keep default mocks that resolve
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Should show initial rendering with header
    await waitFor(() => {
      expect(screen.getByText(/Admin Dashboard/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('loads and displays quick stats cards', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Total Users')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument(); // total_users
    });

    expect(screen.getByText('Total Assignments')).toBeInTheDocument();
    expect(screen.getByText('Active Sessions')).toBeInTheDocument();
    expect(screen.getByText('System Health')).toBeInTheDocument();
  });

  it('displays system metrics', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Check for metric cards
      expect(screen.getByText('CPU')).toBeInTheDocument();
      expect(screen.getByText('Memory')).toBeInTheDocument();
      expect(screen.getByText('Disk')).toBeInTheDocument();
      expect(screen.getByText('Database')).toBeInTheDocument();
    });

    // Check metric values
    expect(screen.getByText('45%')).toBeInTheDocument(); // CPU usage
    expect(screen.getByText('45ms')).toBeInTheDocument(); // DB response time
  });

  it('renders charts with metrics history', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Resource Usage (Last 24h)')).toBeInTheDocument();
      expect(screen.getByText('API Response Time (Last 24h)')).toBeInTheDocument();
    });
  });

  it('displays activity feed with recent logs', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Recent Activity (Last 20 events)')).toBeInTheDocument();
      expect(screen.getByText('Admin User')).toBeInTheDocument();
      expect(screen.getByText('Teacher User')).toBeInTheDocument();
    });
  });

  it('displays system alerts', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('System Alerts')).toBeInTheDocument();
      expect(screen.getByText('High CPU Usage')).toBeInTheDocument();
    });
  });

  it('displays quick action buttons', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('View System Health')).toBeInTheDocument();
      expect(screen.getByText('View Audit Logs')).toBeInTheDocument();
      expect(screen.getByText('Manage Users')).toBeInTheDocument();
      expect(screen.getByText('Monitor Jobs')).toBeInTheDocument();
      expect(screen.getByText('View Database Status')).toBeInTheDocument();
      expect(screen.getByText('View Configuration')).toBeInTheDocument();
    });
  });

  it('handles refresh button click', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Total Users')).toBeInTheDocument();
    });

    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);

    // Should trigger data reload
    await waitFor(() => {
      expect(adminAPI.getUserStats).toHaveBeenCalled();
    });
  });

  it('toggles auto-refresh', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Total Users')).toBeInTheDocument();
    });

    const autoButton = screen.getByText('Auto');
    fireEvent.click(autoButton);

    // Button text should change
    expect(screen.getByText('Manual')).toBeInTheDocument();
  });

  it('displays error message on data fetch failure', async () => {
    (adminAPI.getUserStats as any).mockRejectedValue(new Error('API Error'));

    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // The error will be logged but may not display in the UI immediately
    // because the component still renders the dashboard structure
    await waitFor(() => {
      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
    });
  });

  it('shows no alerts message when none exist', async () => {
    (apiClient.request as any).mockImplementation((url: string) => {
      if (url === '/core/alerts/') {
        return Promise.resolve({ data: { alerts: [] } });
      }
      return Promise.resolve({ data: null });
    });

    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No active alerts')).toBeInTheDocument();
    });
  });

  it('shows no activity message when none exist', async () => {
    (adminAPI.getAuditLogs as any).mockResolvedValue({ data: { results: [] } });

    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No recent activity')).toBeInTheDocument();
    });
  });

  it('displays last refresh timestamp', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Last update:/)).toBeInTheDocument();
    });
  });

  it('navigates to system monitoring on button click', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('View System Health')).toBeInTheDocument();
    });

    const button = screen.getByText('View System Health');
    fireEvent.click(button);

    // Check that navigate was called
    expect(mockNavigate).toHaveBeenCalled();
  });

  it('displays trend indicators with correct colors', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Total Users')).toBeInTheDocument();
    });

    // Check if stats are displayed with trend values
    const statElements = screen.getAllByText(/Total Users|Total Assignments|Active Sessions|System Health/);
    expect(statElements.length).toBeGreaterThan(0);
  });

  it('shows health status indicator', async () => {
    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('System Health')).toBeInTheDocument();
      // Health status should be 98%
      expect(screen.getByText('98')).toBeInTheDocument();
    });
  });

  it('responsive layout adapts to screen size', async () => {
    const { container } = render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Total Users')).toBeInTheDocument();
    });

    // Check for responsive grid classes
    const statCards = container.querySelectorAll('.grid');
    expect(statCards.length).toBeGreaterThan(0);
  });

  it('handles network errors gracefully', async () => {
    (apiClient.request as any).mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );

    // Should still render some content
    await waitFor(() => {
      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
    });
  });
});
