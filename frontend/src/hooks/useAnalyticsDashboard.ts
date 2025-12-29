import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '@/integrations/api/client';

/**
 * Overall dashboard metrics and KPIs
 */
export interface DashboardMetrics {
  total_students: number;
  active_students: number;
  average_engagement: number;
  average_progress: number;
  total_assignments: number;
  completed_assignments: number;
  average_score: number;
  completion_rate: number;
}

/**
 * Learning progress data with trends
 */
export interface LearningProgress {
  period: string;
  student_count: number;
  average_progress: number;
  completion_rate: number;
  active_students: number;
}

/**
 * Engagement metrics over time
 */
export interface EngagementData {
  date: string;
  engagement_score: number;
  active_users: number;
  total_messages: number;
  assignments_submitted: number;
}

/**
 * Performance ranking data
 */
export interface StudentPerformance {
  student_id: number;
  student_name: string;
  average_score: number;
  progress: number;
  completion_rate: number;
  rank: number;
}

/**
 * Class/Section analytics
 */
export interface ClassAnalytics {
  class_id: number;
  class_name: string;
  total_students: number;
  average_score: number;
  average_progress: number;
  engagement_level: number;
}

/**
 * Complete dashboard data structure
 */
export interface AnalyticsDashboardData {
  metrics?: DashboardMetrics;
  learning_progress?: LearningProgress[];
  engagement_trend?: EngagementData[];
  top_performers?: StudentPerformance[];
  class_analytics?: ClassAnalytics[];
  date_range: {
    start_date: string;
    end_date: string;
  };
  generated_at: string;
}

/**
 * Hook options for filtering and date range
 */
export interface UseAnalyticsDashboardOptions {
  dateFrom?: string;
  dateTo?: string;
  classId?: number;
  studentId?: number;
  enabled?: boolean;
}

/**
 * Hook result interface
 */
export interface UseAnalyticsDashboardResult {
  data: AnalyticsDashboardData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  isRefetching: boolean;
}

/**
 * Hook to fetch comprehensive analytics dashboard data
 *
 * Fetches:
 * - Overall metrics (students, engagement, progress)
 * - Learning progress trends
 * - Engagement metrics over time
 * - Student performance rankings
 * - Class/section analytics
 *
 * @param options - Filter options and date range
 * @returns Object containing dashboard data, loading state, and refetch function
 *
 * @example
 * ```tsx
 * const { data, loading, error, refetch } = useAnalyticsDashboard({
 *   dateFrom: '2025-01-01',
 *   dateTo: '2025-01-31',
 *   classId: 5
 * });
 *
 * if (loading) return <LoadingSpinner />;
 * if (error) return <ErrorAlert error={error} />;
 *
 * return (
 *   <AnalyticsDashboard
 *     data={data}
 *     onRefresh={refetch}
 *   />
 * );
 * ```
 */
export const useAnalyticsDashboard = (
  options: UseAnalyticsDashboardOptions = {}
): UseAnalyticsDashboardResult => {
  const {
    dateFrom,
    dateTo,
    classId,
    studentId,
    enabled = true,
  } = options;

  const [data, setData] = useState<AnalyticsDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isRefetching, setIsRefetching] = useState(false);

  const fetchData = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    const isRefetch = !loading && !isRefetching;
    try {
      isRefetch ? setIsRefetching(true) : setLoading(true);
      setError(null);

      // Build query parameters
      const params = new URLSearchParams();
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);
      if (classId) params.append('class_id', classId.toString());
      if (studentId) params.append('student_id', studentId.toString());

      const endpoint = `/api/reports/analytics/dashboard/?${params.toString()}`;
      const response = await apiClient.get(endpoint);

      // Transform the API response to match the AnalyticsDashboardData interface
      // The API returns: { dashboard: {...}, summary: {...}, metadata: {...} }
      const apiResponse = response.data;
      const dashboard = apiResponse.dashboard || {};
      const summary = apiResponse.summary || {};
      const metadata = apiResponse.metadata || {};

      // Build metrics from summary
      const metrics: DashboardMetrics = {
        total_students: summary.total_students || 0,
        active_students: summary.active_students || 0,
        average_engagement: summary.avg_engagement || 0,
        average_progress: summary.avg_progress || 0,
        total_assignments: summary.total_assignments || 0,
        completed_assignments: dashboard.assignments?.completed || 0,
        average_score: summary.avg_grade || 0,
        completion_rate: summary.avg_completion_rate || 0,
      };

      // Build learning progress array (simplified for now)
      const learningProgress: LearningProgress[] = [{
        period: 'Last 30 days',
        student_count: metrics.active_students,
        average_progress: metrics.average_progress,
        completion_rate: metrics.completion_rate,
        active_students: metrics.active_students,
      }];

      // Build engagement trend (simplified)
      const engagementTrend: EngagementData[] = [{
        date: metadata.date_from || new Date().toISOString().split('T')[0],
        engagement_score: metrics.average_engagement,
        active_users: metrics.active_students,
        total_messages: 0,
        assignments_submitted: metrics.completed_assignments,
      }];

      // Build the complete dashboard data
      const dashboardData: AnalyticsDashboardData = {
        metrics,
        learning_progress: learningProgress,
        engagement_trend: engagementTrend,
        top_performers: [],
        class_analytics: [],
        date_range: {
          start_date: metadata.date_from || '',
          end_date: metadata.date_to || '',
        },
        generated_at: metadata.generated_at || new Date().toISOString(),
      };

      setData(dashboardData);
      setError(null);
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error('Failed to fetch analytics dashboard data');
      setError(error);
      setData(null);
    } finally {
      if (isRefetch) {
        setIsRefetching(false);
      } else {
        setLoading(false);
      }
    }
  }, [dateFrom, dateTo, classId, studentId, enabled]);

  useEffect(() => {
    fetchData();
  }, [dateFrom, dateTo, classId, studentId, enabled]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
    isRefetching,
  };
};

/**
 * Hook to fetch only learning progress data
 *
 * Lighter-weight hook for progress trend visualization.
 *
 * @param dateFrom - Start date for data range
 * @param dateTo - End date for data range
 * @returns Object with progress data and loading state
 */
export const useLearningProgress = (
  dateFrom?: string,
  dateTo?: string
) => {
  const [data, setData] = useState<LearningProgress[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);

        const response = await apiClient.get(
          `/api/reports/analytics/progress/?${params.toString()}`
        );
        setData(response.data.metadata ? response.data.weeks : []);
      } catch (err) {
        setError(
          err instanceof Error
            ? err
            : new Error('Failed to fetch learning progress')
        );
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [dateFrom, dateTo]);

  return { data, loading, error };
};

/**
 * Hook to fetch engagement metrics
 *
 * For engagement trend visualization.
 *
 * @param dateFrom - Start date for data range
 * @param dateTo - End date for data range
 * @returns Object with engagement data and loading state
 */
export const useEngagementMetrics = (
  dateFrom?: string,
  dateTo?: string
) => {
  const [data, setData] = useState<EngagementData[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);

        const response = await apiClient.get(
          `/api/reports/analytics/engagement/?${params.toString()}`
        );
        // Transform the engagement response data to match EngagementData interface
        const engagementRecords = response.data.data || [];
        setData(engagementRecords);
      } catch (err) {
        setError(
          err instanceof Error
            ? err
            : new Error('Failed to fetch engagement metrics')
        );
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [dateFrom, dateTo]);

  return { data, loading, error };
};

/**
 * Hook to fetch student performance rankings
 *
 * @param limit - Number of top performers to fetch (default: 10)
 * @param classId - Optional class filter
 * @returns Object with performance data and loading state
 */
export const useStudentPerformance = (
  limit: number = 10,
  classId?: number
) => {
  const [data, setData] = useState<StudentPerformance[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        params.append('limit', limit.toString());
        if (classId) params.append('class_id', classId.toString());

        const response = await apiClient.get(
          `/api/reports/analytics/students/?${params.toString()}`
        );
        // Transform student analytics records to StudentPerformance interface
        const studentRecords = response.data.data || [];
        const performers = studentRecords.map((record: any, idx: number) => ({
          student_id: record.student_id,
          student_name: record.name,
          average_score: record.avg_grade || 0,
          progress: record.progress_pct || 0,
          completion_rate: (record.submission_count / 30) * 100 || 0,
          rank: idx + 1,
        }));
        setData(performers);
      } catch (err) {
        setError(
          err instanceof Error
            ? err
            : new Error('Failed to fetch student performance')
        );
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [limit, classId]);

  return { data, loading, error };
};

/**
 * Hook to fetch class analytics
 *
 * @param classId - Optional specific class ID
 * @returns Object with class analytics data and loading state
 */
export const useClassAnalytics = (classId?: number) => {
  const [data, setData] = useState<ClassAnalytics[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (classId) params.append('class_id', classId.toString());

        const response = await apiClient.get(
          `/api/reports/analytics/dashboard/comparison/?${params.toString()}`
        );
        // Transform comparison response to ClassAnalytics interface
        const classesByClass = response.data.by_class || {};
        const classAnalytics = Object.entries(classesByClass).map(([className, stats]: any) => ({
          class_id: 0, // Not provided by API, would need separate lookup
          class_name: className,
          total_students: stats.students || 0,
          average_score: stats.avg_grade || 0,
          average_progress: 0,
          engagement_level: stats.engagement_level || 0,
        }));
        setData(classAnalytics);
      } catch (err) {
        setError(
          err instanceof Error
            ? err
            : new Error('Failed to fetch class analytics')
        );
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [classId]);

  return { data, loading, error };
};
