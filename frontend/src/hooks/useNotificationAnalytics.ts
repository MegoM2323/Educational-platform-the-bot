/**
 * Custom Hook for Notification Analytics
 * Manages fetching and caching of notification analytics data
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import {
  notificationsAPI,
  NotificationAnalyticsResponse,
  ChannelPerformanceResponse,
  TopTypesResponse,
  AnalyticsQueryParams,
} from '@/integrations/api/notificationsAPI';
import { logger } from '@/utils/logger';

/**
 * Hook for fetching notification analytics metrics
 */
export const useNotificationMetrics = (
  filters: AnalyticsQueryParams
): UseQueryResult<NotificationAnalyticsResponse, Error> => {
  return useQuery({
    queryKey: ['notificationMetrics', filters],
    queryFn: async () => {
      try {
        const response = await notificationsAPI.getMetrics(filters);
        return response;
      } catch (error) {
        logger.error('Failed to fetch notification metrics:', error);
        throw error;
      }
    },
    staleTime: 60 * 1000, // 1 minute
    retry: 2,
    retryDelay: 1000,
  });
};

/**
 * Hook for fetching channel performance metrics
 */
export const useChannelPerformance = (
  filters: AnalyticsQueryParams
): UseQueryResult<ChannelPerformanceResponse, Error> => {
  return useQuery({
    queryKey: ['channelPerformance', filters.date_from, filters.date_to],
    queryFn: async () => {
      try {
        const response = await notificationsAPI.getChannelPerformance(filters);
        return response;
      } catch (error) {
        logger.error('Failed to fetch channel performance:', error);
        throw error;
      }
    },
    staleTime: 60 * 1000,
    retry: 2,
    retryDelay: 1000,
  });
};

/**
 * Hook for fetching top performing notification types
 */
export const useTopNotificationTypes = (
  filters: AnalyticsQueryParams
): UseQueryResult<TopTypesResponse, Error> => {
  return useQuery({
    queryKey: ['topNotificationTypes', filters.date_from, filters.date_to],
    queryFn: async () => {
      try {
        const response = await notificationsAPI.getTopTypes(filters);
        return response;
      } catch (error) {
        logger.error('Failed to fetch top notification types:', error);
        throw error;
      }
    },
    staleTime: 60 * 1000,
    retry: 2,
    retryDelay: 1000,
  });
};

/**
 * Combined hook for all analytics queries
 * Returns a single loading/error state and refetch function
 */
export const useAllNotificationAnalytics = (filters: AnalyticsQueryParams) => {
  const metrics = useNotificationMetrics(filters);
  const channelPerformance = useChannelPerformance(filters);
  const topTypes = useTopNotificationTypes(filters);

  return {
    metrics,
    channelPerformance,
    topTypes,
    isLoading: metrics.isLoading || channelPerformance.isLoading || topTypes.isLoading,
    isFetching: metrics.isFetching || channelPerformance.isFetching || topTypes.isFetching,
    error: metrics.error || channelPerformance.error || topTypes.error,
    refetch: async () => {
      await Promise.all([
        metrics.refetch(),
        channelPerformance.refetch(),
        topTypes.refetch(),
      ]);
    },
  };
};
