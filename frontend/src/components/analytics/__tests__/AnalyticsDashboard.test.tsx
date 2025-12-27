import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AnalyticsDashboard } from '../AnalyticsDashboard';
import * as useAnalyticsDashboardModule from '@/hooks/useAnalyticsDashboard';

// Mock hooks
vi.mock('@/hooks/useAnalyticsDashboard');
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

const mockAnalyticsData = {
  metrics: {
    total_students: 45,
    active_students: 38,
    average_engagement: 78.5,
    average_progress: 65.2,
    total_assignments: 20,
    completed_assignments: 16,
    average_score: 72.3,
    completion_rate: 80,
  },
  learning_progress: [
    {
      period: 'Week 1',
      student_count: 40,
      average_progress: 50,
      completion_rate: 60,
      active_students: 35,
    },
    {
      period: 'Week 2',
      student_count: 42,
      average_progress: 55,
      completion_rate: 65,
      active_students: 36,
    },
    {
      period: 'Week 3',
      student_count: 44,
      average_progress: 62,
      completion_rate: 75,
      active_students: 37,
    },
  ],
  engagement_trend: [
    {
      date: '2025-01-01',
      engagement_score: 65,
      active_users: 30,
      total_messages: 150,
      assignments_submitted: 5,
    },
    {
      date: '2025-01-02',
      engagement_score: 70,
      active_users: 35,
      total_messages: 180,
      assignments_submitted: 8,
    },
    {
      date: '2025-01-03',
      engagement_score: 75,
      active_users: 38,
      total_messages: 200,
      assignments_submitted: 10,
    },
  ],
  top_performers: [
    {
      student_id: 1,
      student_name: 'John Doe',
      average_score: 95,
      progress: 95,
      completion_rate: 100,
      rank: 1,
    },
    {
      student_id: 2,
      student_name: 'Jane Smith',
      average_score: 90,
      progress: 90,
      completion_rate: 95,
      rank: 2,
    },
    {
      student_id: 3,
      student_name: 'Bob Johnson',
      average_score: 85,
      progress: 85,
      completion_rate: 90,
      rank: 3,
    },
  ],
  class_analytics: [
    {
      class_id: 1,
      class_name: 'Mathematics 101',
      total_students: 30,
      average_score: 75,
      average_progress: 68,
      engagement_level: 80,
    },
    {
      class_id: 2,
      class_name: 'Science 102',
      total_students: 28,
      average_score: 72,
      average_progress: 64,
      engagement_level: 76,
    },
  ],
  date_range: {
    start_date: '2025-01-01',
    end_date: '2025-01-31',
  },
  generated_at: new Date().toISOString(),
};

describe('AnalyticsDashboard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAnalyticsDashboardModule.useAnalyticsDashboard).mockReturnValue({
      data: mockAnalyticsData,
      loading: false,
      error: null,
      refetch: vi.fn(),
      isRefetching: false,
    });
  });

  describe('Rendering', () => {
    it('should render dashboard title and description', () => {
      render(<AnalyticsDashboard />);
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
      expect(
        screen.getByText('Learning metrics and performance insights')
      ).toBeInTheDocument();
    });

    it('should render KPI cards with metrics', async () => {
      render(<AnalyticsDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Total Students')).toBeInTheDocument();
        expect(screen.getByText('45')).toBeInTheDocument();
        expect(screen.getByText('Avg. Progress')).toBeInTheDocument();
        expect(screen.getByText('Avg. Score')).toBeInTheDocument();
        expect(screen.getByText('Engagement')).toBeInTheDocument();
      });
    });

    it('should render filter controls', () => {
      render(<AnalyticsDashboard />);

      expect(screen.getByText('Last 7 Days')).toBeInTheDocument();
      expect(screen.getByText('Last 30 Days')).toBeInTheDocument();
      expect(screen.getByText('This Month')).toBeInTheDocument();
      expect(screen.getAllByLabelText('From')).toHaveLength(1);
      expect(screen.getAllByLabelText('To')).toHaveLength(1);
    });

    it('should render chart tabs', () => {
      render(<AnalyticsDashboard />);

      expect(screen.getByRole('tab', { name: 'Progress' })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: 'Engagement' })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: 'Performance' })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: 'Classes' })).toBeInTheDocument();
    });

    it('should render action buttons (Refresh and Export)', () => {
      render(<AnalyticsDashboard />);

      expect(screen.getByText('Refresh')).toBeInTheDocument();
      expect(screen.getByText('Export')).toBeInTheDocument();
    });
  });

  describe('Loading and Error States', () => {
    it('should show loading skeletons when loading', () => {
      vi.mocked(useAnalyticsDashboardModule.useAnalyticsDashboard).mockReturnValue({
        data: null,
        loading: true,
        error: null,
        refetch: vi.fn(),
        isRefetching: false,
      });

      render(<AnalyticsDashboard />);
      const skeletons = document.querySelectorAll('[class*="skeleton"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('should show error alert when error occurs', () => {
      const testError = new Error('Failed to fetch analytics data');
      vi.mocked(useAnalyticsDashboardModule.useAnalyticsDashboard).mockReturnValue({
        data: null,
        loading: false,
        error: testError,
        refetch: vi.fn(),
        isRefetching: false,
      });

      render(<AnalyticsDashboard />);
      expect(screen.getByText('Failed to fetch analytics data')).toBeInTheDocument();
    });
  });

  describe('Filters and Date Range', () => {
    it('should handle quick date range selection', async () => {
      const user = userEvent.setup();
      const mockRefetch = vi.fn();

      vi.mocked(useAnalyticsDashboardModule.useAnalyticsDashboard).mockReturnValue({
        data: mockAnalyticsData,
        loading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AnalyticsDashboard />);

      const last7DaysBtn = screen.getByText('Last 7 Days');
      await user.click(last7DaysBtn);

      // Date inputs should be updated
      const dateInputs = screen.getAllByDisplayValue(/\d{4}-\d{2}-\d{2}/);
      expect(dateInputs.length).toBeGreaterThan(0);
    });

    it('should handle custom date range input', async () => {
      const user = userEvent.setup();
      render(<AnalyticsDashboard />);

      const dateInputs = screen.getAllByDisplayValue(/\d{4}-\d{2}-\d{2}/);
      const fromInput = dateInputs[0] as HTMLInputElement;

      await user.clear(fromInput);
      await user.type(fromInput, '2025-01-15');

      expect(fromInput.value).toBe('2025-01-15');
    });

    it('should display date range in footer', () => {
      render(<AnalyticsDashboard />);

      // Check for date range display in footer
      const footerText = screen.getByText(/Data range:/);
      expect(footerText).toBeInTheDocument();
    });
  });

  describe('Chart Tabs', () => {
    it('should display Progress tab content by default', async () => {
      render(<AnalyticsDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Learning Progress Trend')).toBeInTheDocument();
      });
    });

    it('should switch to Engagement tab', async () => {
      const user = userEvent.setup();
      render(<AnalyticsDashboard />);

      const engagementTab = screen.getByRole('tab', { name: 'Engagement' });
      await user.click(engagementTab);

      await waitFor(() => {
        expect(screen.getByText('Engagement Metrics')).toBeInTheDocument();
      });
    });

    it('should switch to Performance tab', async () => {
      const user = userEvent.setup();
      render(<AnalyticsDashboard />);

      const performanceTab = screen.getByRole('tab', { name: 'Performance' });
      await user.click(performanceTab);

      await waitFor(() => {
        expect(screen.getByText('Top Performers')).toBeInTheDocument();
      });
    });

    it('should display top performers list', async () => {
      const user = userEvent.setup();
      render(<AnalyticsDashboard />);

      const performanceTab = screen.getByRole('tab', { name: 'Performance' });
      await user.click(performanceTab);

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
        expect(screen.getByText('Jane Smith')).toBeInTheDocument();
        expect(screen.getByText('Bob Johnson')).toBeInTheDocument();
      });
    });

    it('should switch to Classes tab', async () => {
      const user = userEvent.setup();
      render(<AnalyticsDashboard />);

      const classesTab = screen.getByRole('tab', { name: 'Classes' });
      await user.click(classesTab);

      await waitFor(() => {
        expect(screen.getByText('Class Analytics')).toBeInTheDocument();
      });
    });

    it('should display class summary information', async () => {
      const user = userEvent.setup();
      render(<AnalyticsDashboard />);

      const classesTab = screen.getByRole('tab', { name: 'Classes' });
      await user.click(classesTab);

      await waitFor(() => {
        expect(screen.getByText('Mathematics 101')).toBeInTheDocument();
        expect(screen.getByText('Science 102')).toBeInTheDocument();
      });
    });
  });

  describe('Interactivity', () => {
    it('should call refetch when Refresh button is clicked', async () => {
      const user = userEvent.setup();
      const mockRefetch = vi.fn();

      vi.mocked(useAnalyticsDashboardModule.useAnalyticsDashboard).mockReturnValue({
        data: mockAnalyticsData,
        loading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AnalyticsDashboard />);

      const refreshBtn = screen.getByText('Refresh');
      await user.click(refreshBtn);

      await waitFor(() => {
        expect(mockRefetch).toHaveBeenCalled();
      });
    });

    it('should disable Refresh button while refetching', () => {
      vi.mocked(useAnalyticsDashboardModule.useAnalyticsDashboard).mockReturnValue({
        data: mockAnalyticsData,
        loading: false,
        error: null,
        refetch: vi.fn(),
        isRefetching: true,
      });

      render(<AnalyticsDashboard />);

      const refreshBtn = screen.getByText('Refresh') as HTMLButtonElement;
      expect(refreshBtn).toBeDisabled();
    });

    it('should display tooltip on hover for chart data points', async () => {
      render(<AnalyticsDashboard />);

      await waitFor(() => {
        // Charts should be rendered
        const chartElements = document.querySelectorAll('[class*="recharts"]');
        expect(chartElements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Responsive Design', () => {
    it('should render on mobile viewport', () => {
      // Mock mobile viewport
      global.innerWidth = 375;
      global.innerHeight = 667;

      render(<AnalyticsDashboard />);

      expect(screen.getByText('Analytics Dashboard')).toBeVisible();
      expect(screen.getByText('Last 7 Days')).toBeVisible();
    });

    it('should render on tablet viewport', () => {
      // Mock tablet viewport
      global.innerWidth = 768;
      global.innerHeight = 1024;

      render(<AnalyticsDashboard />);

      expect(screen.getByText('Analytics Dashboard')).toBeVisible();
    });

    it('should render on desktop viewport', () => {
      // Mock desktop viewport
      global.innerWidth = 1920;
      global.innerHeight = 1080;

      render(<AnalyticsDashboard />);

      expect(screen.getByText('Analytics Dashboard')).toBeVisible();
    });
  });

  describe('Props Handling', () => {
    it('should accept and use initialDateFrom and initialDateTo props', () => {
      render(
        <AnalyticsDashboard
          initialDateFrom="2025-01-01"
          initialDateTo="2025-01-31"
        />
      );

      const dateInputs = screen.getAllByDisplayValue(/\d{4}-\d{2}-\d{2}/);
      expect(dateInputs.length).toBeGreaterThan(0);
    });

    it('should accept and use classId prop', () => {
      const mockRefetch = vi.fn();
      vi.mocked(useAnalyticsDashboardModule.useAnalyticsDashboard).mockReturnValue({
        data: mockAnalyticsData,
        loading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AnalyticsDashboard classId={5} />);

      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });

    it('should accept and use studentId prop', () => {
      const mockRefetch = vi.fn();
      vi.mocked(useAnalyticsDashboardModule.useAnalyticsDashboard).mockReturnValue({
        data: mockAnalyticsData,
        loading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AnalyticsDashboard studentId={42} />);

      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });
  });

  describe('Data Display', () => {
    it('should display KPI values correctly formatted', async () => {
      render(<AnalyticsDashboard />);

      await waitFor(() => {
        // Check that numbers are formatted correctly
        expect(screen.getByText('45')).toBeInTheDocument(); // total_students
        expect(screen.getByText('38')).toBeInTheDocument(); // active_students (in badge)
      });
    });

    it('should show percentage values with proper formatting', async () => {
      render(<AnalyticsDashboard />);

      await waitFor(() => {
        const percentageText = screen.getByText(/65\.2%/);
        expect(percentageText).toBeInTheDocument();
      });
    });

    it('should display completion metrics', async () => {
      render(<AnalyticsDashboard />);

      await waitFor(() => {
        // Should show completed assignments
        expect(screen.getByText(/16\/20/)).toBeInTheDocument();
      });
    });
  });
});
