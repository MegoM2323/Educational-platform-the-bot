import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '@/integrations/api/client';

/**
 * Analytics data returned from backend
 */
export interface AnalyticsData {
  assignment_id: number;
  assignment_title: string;
  max_score: number;
  statistics: {
    mean: number | null;
    median: number | null;
    mode: number | null;
    std_dev: number | null;
    min: number | null;
    max: number | null;
    q1: number | null;
    q2: number | null;
    q3: number | null;
    sample_size: number;
  };
  distribution: {
    buckets: {
      [key: string]: {
        label: string;
        count: number;
        percentage: number;
      };
    };
    total: number;
    pie_chart_data: Array<{
      label: string;
      value: number;
      percentage: number;
    }>;
  };
  submission_rate: {
    assigned_count: number;
    submitted_count: number;
    graded_count: number;
    late_count: number;
    submission_rate: number;
    grading_rate: number;
    late_rate: number;
  };
  comparison: {
    assignment_average: number | null;
    assignment_count: number;
    class_average: number | null;
    difference: number | null;
    performance: string;
  };
  generated_at: string;
}

/**
 * Question analysis data from backend
 */
export interface QuestionAnalysisData {
  assignment_id: number;
  total_questions: number;
  questions: Array<{
    question_id: number;
    question_text: string;
    question_type: string;
    points: number;
    total_answers: number;
    correct_answers: number;
    wrong_answers: number;
    correct_rate: number;
    wrong_rate: number;
    difficulty_score: number;
  }>;
  difficulty_ranking: Array<{
    question_id: number;
    question_text: string;
    difficulty_score: number;
  }>;
  average_difficulty: number;
  generated_at: string;
}

/**
 * Time analysis data from backend
 */
export interface TimeAnalysisData {
  assignment_id: number;
  submission_timing: {
    on_time_submissions: number;
    late_submissions: number;
    average_days_before_deadline: number | null;
    total_submissions: number;
  };
  grading_speed: {
    average_time_to_grade_hours: number | null;
    average_time_to_grade_days: number | null;
    fastest_grade_hours: number | null;
    slowest_grade_hours: number | null;
    total_graded: number;
  };
  late_submissions: {
    late_submission_count: number;
    late_submission_rate: number;
    average_days_late: number | null;
    most_days_late: number | null;
  };
  response_times: {
    first_grade_at: string | null;
    last_grade_at: string | null;
    grading_period_days: number | null;
    total_graded: number;
  };
  generated_at: string;
}

export interface UseAssignmentAnalyticsOptions {
  dateRange?: 'week' | 'month' | 'all';
  studentGroup?: 'all' | 'submitted' | 'not-submitted';
  enabled?: boolean;
}

export interface UseAssignmentAnalyticsResult {
  analytics: AnalyticsData | null;
  questions: QuestionAnalysisData | null;
  time: TimeAnalysisData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch and manage assignment analytics data
 *
 * Fetches grade distribution, question difficulty, submission timeline,
 * and class comparison data from the backend API.
 *
 * @param assignmentId - The ID of the assignment to analyze
 * @param options - Optional configuration for date range and filtering
 * @returns Object containing analytics data, loading state, and error handling
 *
 * @example
 * ```tsx
 * const { analytics, questions, time, loading, error } = useAssignmentAnalytics(123, {
 *   dateRange: 'month',
 *   studentGroup: 'all'
 * });
 *
 * if (loading) return <Spinner />;
 * if (error) return <ErrorAlert error={error} />;
 *
 * return <AssignmentAnalyticsDashboard data={analytics} />;
 * ```
 */
export const useAssignmentAnalytics = (
  assignmentId: number,
  options: UseAssignmentAnalyticsOptions = {}
): UseAssignmentAnalyticsResult => {
  const { dateRange = 'all', studentGroup = 'all', enabled = true } = options;

  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [questions, setQuestions] = useState<QuestionAnalysisData | null>(null);
  const [time, setTime] = useState<TimeAnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchAnalytics = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Fetch grade distribution analytics (T_ASSIGN_007)
      const analyticsResponse = await apiClient.get(
        `/assignments/assignments/${assignmentId}/analytics/`
      );

      // Fetch statistics by question (T_ASN_005)
      const questionsResponse = await apiClient.get(
        `/assignments/assignments/${assignmentId}/statistics/`
      );

      // Apply filters if provided
      const params = new URLSearchParams();
      if (dateRange !== 'all') params.append('date_range', dateRange);
      if (studentGroup !== 'all') params.append('student_group', studentGroup);

      const timeResponse = await apiClient.get(
        `/assignments/assignments/${assignmentId}/statistics/${
          params.toString() ? `?${params.toString()}` : ''
        }`
      );

      setAnalytics(analyticsResponse.data);
      setQuestions(questionsResponse.data);
      setTime(timeResponse.data);
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error('Failed to fetch analytics data')
      );
      setAnalytics(null);
      setQuestions(null);
      setTime(null);
    } finally {
      setLoading(false);
    }
  }, [assignmentId, dateRange, studentGroup, enabled]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return {
    analytics,
    questions,
    time,
    loading,
    error,
    refetch: fetchAnalytics,
  };
};

/**
 * Hook to fetch only grade distribution analytics
 *
 * Lighter-weight hook when only basic statistics are needed.
 *
 * @param assignmentId - The ID of the assignment
 * @returns Object with analytics data and loading state
 */
export const useAssignmentGradeAnalytics = (assignmentId: number) => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get(
          `/assignments/assignments/${assignmentId}/analytics/`
        );
        setData(response.data);
      } catch (err) {
        setError(
          err instanceof Error ? err : new Error('Failed to fetch analytics')
        );
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [assignmentId]);

  return { data, loading, error };
};

/**
 * Hook to fetch question difficulty analysis
 *
 * Focuses on per-question performance metrics.
 *
 * @param assignmentId - The ID of the assignment
 * @returns Object with question analysis data and loading state
 */
export const useAssignmentQuestionAnalytics = (assignmentId: number) => {
  const [data, setData] = useState<QuestionAnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get(
          `/assignments/assignments/${assignmentId}/statistics/`
        );
        setData(response.data);
      } catch (err) {
        setError(
          err instanceof Error ? err : new Error('Failed to fetch question analysis')
        );
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [assignmentId]);

  return { data, loading, error };
};

/**
 * Hook to fetch submission timeline analysis
 *
 * Focuses on submission timing and late submission metrics.
 *
 * @param assignmentId - The ID of the assignment
 * @returns Object with time analysis data and loading state
 */
export const useAssignmentTimeAnalytics = (assignmentId: number) => {
  const [data, setData] = useState<TimeAnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get(
          `/assignments/assignments/${assignmentId}/statistics/`
        );
        // Extract time-related data from full statistics response
        const { submission_timing, grading_speed, late_submissions, response_times } = response.data;
        setData({
          assignment_id: response.data.assignment_id,
          submission_timing,
          grading_speed,
          late_submissions,
          response_times,
          generated_at: response.data.generated_at,
        });
      } catch (err) {
        setError(
          err instanceof Error ? err : new Error('Failed to fetch time analysis')
        );
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [assignmentId]);

  return { data, loading, error };
};
