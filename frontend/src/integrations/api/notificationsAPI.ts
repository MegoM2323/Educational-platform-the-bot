/**
 * Notifications API Integration
 * Handles all API calls related to notification analytics and management
 */

import { unifiedAPI } from './unifiedClient';

/**
 * Types for notification analytics
 */
export interface TimeMetricsItem {
  time: string;
  count: number;
  sent: number;
  opened: number;
}

export interface TypeMetrics {
  count: number;
  delivered: number;
  opened: number;
  delivery_rate: number;
  open_rate: number;
}

export interface ChannelMetrics {
  count: number;
  delivered: number;
  failed: number;
  delivery_rate: number;
}

export interface SummaryMetrics {
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_failed: number;
  avg_delivery_time: string;
  failures: number;
  error_reasons: string[];
}

export interface NotificationAnalyticsResponse {
  date_from: string;
  date_to: string;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  delivery_rate: number;
  open_rate: number;
  by_type: Record<string, TypeMetrics>;
  by_channel: Record<string, ChannelMetrics>;
  by_time: TimeMetricsItem[];
  summary: SummaryMetrics;
}

export interface ChannelPerformance {
  channel: string;
  count: number;
  delivered: number;
  failed: number;
  delivery_rate: number;
}

export interface ChannelPerformanceResponse {
  channels: ChannelPerformance[];
  best_channel: ChannelPerformance | null;
  worst_channel: ChannelPerformance | null;
}

export interface TopPerformingType {
  type: string;
  open_rate: number;
  count: number;
}

export interface TopTypesResponse {
  top_types: TopPerformingType[];
}

/**
 * Query parameters for analytics
 */
export interface AnalyticsQueryParams {
  date_from?: string; // YYYY-MM-DD format
  date_to?: string; // YYYY-MM-DD format
  type?: string; // Notification type filter
  channel?: string; // Channel filter (email, push, sms, in_app)
  granularity?: 'hour' | 'day' | 'week'; // Time grouping
  limit?: number; // Limit for top types
}

/**
 * Notifications API Service
 */
export const notificationsAPI = {
  /**
   * Get notification analytics metrics
   * GET /api/notifications/analytics/metrics/
   */
  getMetrics: async (params: AnalyticsQueryParams = {}) => {
    const queryParams = new URLSearchParams();

    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.type) queryParams.append('type', params.type);
    if (params.channel) queryParams.append('channel', params.channel);
    if (params.granularity) queryParams.append('granularity', params.granularity);

    const response = await unifiedAPI.get<NotificationAnalyticsResponse>(
      `/notifications/analytics/metrics/?${queryParams.toString()}`
    );
    return response;
  },

  /**
   * Get channel performance metrics
   * GET /api/notifications/analytics/performance/
   */
  getChannelPerformance: async (params: AnalyticsQueryParams = {}) => {
    const queryParams = new URLSearchParams();

    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);

    const response = await unifiedAPI.get<ChannelPerformanceResponse>(
      `/notifications/analytics/performance/?${queryParams.toString()}`
    );
    return response;
  },

  /**
   * Get top performing notification types
   * GET /api/notifications/analytics/top-types/
   */
  getTopTypes: async (params: AnalyticsQueryParams = {}) => {
    const queryParams = new URLSearchParams();

    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.limit) queryParams.append('limit', params.limit.toString());

    const response = await unifiedAPI.get<TopTypesResponse>(
      `/notifications/analytics/top-types/?${queryParams.toString()}`
    );
    return response;
  },
};

export type { AnalyticsQueryParams };
