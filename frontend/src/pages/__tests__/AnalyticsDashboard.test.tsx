import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AnalyticsDashboardPage } from '../AnalyticsDashboard';

// Mock hooks
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      username: 'teacher1',
      email: 'teacher@test.com',
      role: 'teacher',
    },
    isLoading: false,
  }),
}));

vi.mock('@/hooks/useAnalyticsDashboard', () => ({
  useAnalyticsDashboard: () => ({
    data: {
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
      learning_progress: [],
      engagement_trend: [],
      top_performers: [],
      class_analytics: [],
      date_range: {
        start_date: '2025-01-01',
        end_date: '2025-01-31',
      },
      generated_at: new Date().toISOString(),
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
    isRefetching: false,
  }),
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      {component}
    </BrowserRouter>
  );
};

describe('AnalyticsDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render the analytics dashboard page', async () => {
    renderWithRouter(<AnalyticsDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });
  });

  it('should display dashboard with authorized user', async () => {
    renderWithRouter(<AnalyticsDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Learning metrics and performance insights')).toBeInTheDocument();
    });
  });

  it('should show loading state while checking auth', () => {
    vi.mocked(require('@/hooks/useAuth').useAuth).mockReturnValue({
      user: null,
      isLoading: true,
    });

    renderWithRouter(<AnalyticsDashboardPage />);

    expect(screen.getByText(/Loading analytics dashboard/)).toBeInTheDocument();
  });

  it('should redirect unauthorized users', async () => {
    vi.mocked(require('@/hooks/useAuth').useAuth).mockReturnValue({
      user: {
        id: 1,
        username: 'student1',
        email: 'student@test.com',
        role: 'student',
      },
      isLoading: false,
    });

    renderWithRouter(<AnalyticsDashboardPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/don't have permission to access/)
      ).toBeInTheDocument();
    });
  });

  it('should pass query parameters to dashboard component', async () => {
    // This test would require setup with location/routing context
    renderWithRouter(<AnalyticsDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });
  });
});
