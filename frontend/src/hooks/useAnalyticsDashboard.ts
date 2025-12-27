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
  metrics: DashboardMetrics;
  learning_progress: LearningProgress[];
  engagement_trend: EngagementData[];
  top_performers: StudentPerformance[];
  class_analytics: ClassAnalytics[];
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

      const endpoint = `/reports/analytics-data/?${params.toString()}`;
      const response = await apiClient.get(endpoint);

      setData(response.data);
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
  }, [dateFrom, dateTo, classId, studentId, enabled, loading, isRefetching]);

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
          `/reports/analytics-data/learning-progress/?${params.toString()}`
        );
        setData(response.data.learning_progress);
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
          `/reports/analytics-data/engagement/?${params.toString()}`
        );
        setData(response.data.engagement_trend);
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
          `/reports/analytics-data/performance/?${params.toString()}`
        );
        setData(response.data.top_performers);
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
          `/reports/analytics-data/classes/?${params.toString()}`
        );
        setData(response.data.class_analytics);
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
