/**
 * Notification Analytics Dashboard
 * Displays notification delivery metrics, performance analytics, and insights
 */

import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  TooltipProps,
} from 'recharts';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  TrendingUp,
  TrendingDown,
  Send,
  CheckCircle,
  AlertCircle,
  Zap,
  BarChart3,
  Calendar,
  RefreshCw,
  Download,
  Filter,
} from 'lucide-react';
import { notificationsAPI, AnalyticsQueryParams } from '@/integrations/api/notificationsAPI';
import { logger } from '@/utils/logger';

/**
 * Color scheme for charts
 */
const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];
const CHANNEL_COLORS: Record<string, string> = {
  email: '#3b82f6',
  push: '#10b981',
  sms: '#f59e0b',
  in_app: '#8b5cf6',
};

/**
 * Custom tooltip for charts
 */
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
        <p className="text-sm font-semibold text-gray-900">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} style={{ color: entry.color }} className="text-sm">
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

/**
 * Metric card component
 */
interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  unit?: string;
  icon?: React.ReactNode;
}

const MetricCard = ({ title, value, change, unit, icon }: MetricCardProps) => (
  <Card>
    <CardHeader className="pb-2">
      <div className="flex items-center justify-between">
        <CardTitle className="text-sm font-medium text-gray-600">{title}</CardTitle>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
    </CardHeader>
    <CardContent>
      <div className="flex items-baseline justify-between">
        <div className="text-2xl font-bold text-gray-900">{value}</div>
        {change !== undefined && (
          <div className={`flex items-center text-xs font-semibold ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {change >= 0 ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
            {Math.abs(change)}%
          </div>
        )}
      </div>
      {unit && <p className="text-xs text-gray-500 mt-1">{unit}</p>}
    </CardContent>
  </Card>
);

/**
 * Filter bar component
 */
interface FilterBarProps {
  onFilterChange: (filters: AnalyticsQueryParams) => void;
  currentFilters: AnalyticsQueryParams;
}

const FilterBar = ({ onFilterChange, currentFilters }: FilterBarProps) => {
  const [filters, setFilters] = useState<AnalyticsQueryParams>(currentFilters);

  useEffect(() => {
    setFilters(currentFilters);
  }, [currentFilters]);

  const handleDateChange = (field: 'date_from' | 'date_to', value: string) => {
    const newFilters = { ...filters, [field]: value };
    setFilters(newFilters);
  };

  const handleChannelChange = (channel: string) => {
    const newFilters = { ...filters, channel: filters.channel === channel ? undefined : channel };
    setFilters(newFilters);
  };

  const handleApply = () => {
    onFilterChange(filters);
  };

  const handleReset = () => {
    const defaultFilters: AnalyticsQueryParams = {
      date_from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      date_to: new Date().toISOString().split('T')[0],
      granularity: 'day',
    };
    setFilters(defaultFilters);
    onFilterChange(defaultFilters);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center">
          <Filter className="w-4 h-4 mr-2" />
          Filters
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date From</label>
            <input
              type="date"
              value={filters.date_from || ''}
              onChange={(e) => handleDateChange('date_from', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date To</label>
            <input
              type="date"
              value={filters.date_to || ''}
              onChange={(e) => handleDateChange('date_to', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Granularity</label>
            <select
              value={filters.granularity || 'day'}
              onChange={(e) => setFilters({ ...filters, granularity: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="hour">Hourly</option>
              <option value="day">Daily</option>
              <option value="week">Weekly</option>
            </select>
          </div>

          <div className="flex items-end gap-2">
            <Button onClick={handleApply} className="flex-1" variant="default">
              Apply
            </Button>
            <Button onClick={handleReset} variant="outline" className="flex-1">
              Reset
            </Button>
          </div>
        </div>

        <div className="mt-4 flex gap-2">
          <p className="text-xs font-medium text-gray-600">Channels:</p>
          {['email', 'push', 'sms', 'in_app'].map((channel) => (
            <button
              key={channel}
              onClick={() => handleChannelChange(channel)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                filters.channel === channel
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {channel}
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

/**
 * Main NotificationAnalytics Component
 */
export const NotificationAnalytics = () => {
  const [filters, setFilters] = useState<AnalyticsQueryParams>({
    date_from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    date_to: new Date().toISOString().split('T')[0],
    granularity: 'day',
  });

  // Fetch analytics data
  const { data: analyticsData, isLoading: metricsLoading, error: metricsError, refetch: refetchMetrics } = useQuery({
    queryKey: ['notificationMetrics', filters],
    queryFn: () => notificationsAPI.getMetrics(filters),
    staleTime: 60 * 1000, // 1 minute
    retry: 2,
  });

  const { data: channelData, isLoading: channelLoading, error: channelError } = useQuery({
    queryKey: ['channelPerformance', filters.date_from, filters.date_to],
    queryFn: () => notificationsAPI.getChannelPerformance(filters),
    staleTime: 60 * 1000,
    retry: 2,
  });

  const { data: topTypesData, isLoading: topTypesLoading, error: topTypesError } = useQuery({
    queryKey: ['topNotificationTypes', filters.date_from, filters.date_to],
    queryFn: () => notificationsAPI.getTopTypes({ ...filters, limit: 5 }),
    staleTime: 60 * 1000,
    retry: 2,
  });

  const isLoading = metricsLoading || channelLoading || topTypesLoading;

  // Prepare chart data
  const timeSeriesData = useMemo(() => {
    if (!analyticsData) return [];
    return analyticsData.by_time || [];
  }, [analyticsData]);

  const channelChartData = useMemo(() => {
    if (!channelData?.channels) return [];
    return channelData.channels;
  }, [channelData]);

  const typeChartData = useMemo(() => {
    if (!topTypesData?.top_types) return [];
    return topTypesData.top_types.slice(0, 5);
  }, [topTypesData]);

  // Calculate summary statistics
  const stats = useMemo(() => {
    if (!analyticsData) return null;

    return {
      totalSent: analyticsData.total_sent,
      totalDelivered: analyticsData.total_delivered,
      totalOpened: analyticsData.total_opened,
      deliveryRate: analyticsData.delivery_rate,
      openRate: analyticsData.open_rate,
    };
  }, [analyticsData]);

  // Handle filter changes
  const handleFilterChange = (newFilters: AnalyticsQueryParams) => {
    setFilters(newFilters);
  };

  // Handle refresh
  const handleRefresh = () => {
    refetchMetrics();
  };

  // Render loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
          <p className="text-gray-600">Loading analytics data...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (metricsError || channelError || topTypesError) {
    const error = metricsError || channelError || topTypesError;
    logger.error('Analytics data fetch failed:', error);

    return (
      <div className="container mx-auto px-4 py-8">
        <Alert className="border-red-200 bg-red-50">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-700">
            Failed to load analytics data. Please try again or contact support.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Notification Analytics</h1>
          <p className="text-gray-600 mt-2">Monitor notification delivery, open rates, and channel performance</p>
        </div>
        <Button
          onClick={handleRefresh}
          variant="outline"
          size="sm"
          className="flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <FilterBar onFilterChange={handleFilterChange} currentFilters={filters} />

      {/* Key Metrics */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <MetricCard
            title="Total Sent"
            value={stats.totalSent.toLocaleString()}
            icon={<Send className="w-4 h-4" />}
          />
          <MetricCard
            title="Delivered"
            value={stats.totalDelivered.toLocaleString()}
            icon={<CheckCircle className="w-4 h-4" />}
          />
          <MetricCard
            title="Opened"
            value={stats.totalOpened.toLocaleString()}
            icon={<Zap className="w-4 h-4" />}
          />
          <MetricCard
            title="Delivery Rate"
            value={`${stats.deliveryRate.toFixed(1)}%`}
            unit="% of sent"
            icon={<BarChart3 className="w-4 h-4" />}
          />
          <MetricCard
            title="Open Rate"
            value={`${stats.openRate.toFixed(1)}%`}
            unit="% of sent"
            icon={<TrendingUp className="w-4 h-4" />}
          />
        </div>
      )}

      {/* Time Series Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Notification Metrics Over Time</CardTitle>
          <CardDescription>Daily notification counts and open rates</CardDescription>
        </CardHeader>
        <CardContent>
          {timeSeriesData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timeSeriesData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#6b7280' }}
                  style={{ fontSize: '12px' }}
                />
                <YAxis
                  tick={{ fill: '#6b7280' }}
                  style={{ fontSize: '12px' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke={COLORS[0]}
                  dot={false}
                  strokeWidth={2}
                  name="Sent"
                />
                <Line
                  type="monotone"
                  dataKey="sent"
                  stroke={COLORS[1]}
                  dot={false}
                  strokeWidth={2}
                  name="Processed"
                />
                <Line
                  type="monotone"
                  dataKey="opened"
                  stroke={COLORS[2]}
                  dot={false}
                  strokeWidth={2}
                  name="Opened"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-gray-500">
              No data available for selected period
            </div>
          )}
        </CardContent>
      </Card>

      {/* Channel Performance & Top Types */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Channel Performance */}
        <Card>
          <CardHeader>
            <CardTitle>Channel Performance</CardTitle>
            <CardDescription>Delivery rates by notification channel</CardDescription>
          </CardHeader>
          <CardContent>
            {channelChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={channelChartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="channel"
                    tick={{ fill: '#6b7280' }}
                    style={{ fontSize: '12px' }}
                  />
                  <YAxis
                    tick={{ fill: '#6b7280' }}
                    style={{ fontSize: '12px' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="count" fill={COLORS[0]} name="Sent" />
                  <Bar dataKey="delivered" fill={COLORS[2]} name="Delivered" />
                  <Bar dataKey="failed" fill={COLORS[1]} name="Failed" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500">
                No channel data available
              </div>
            )}

            {/* Channel Summary Table */}
            <div className="mt-6 space-y-2">
              {channelChartData.map((channel) => (
                <div key={channel.channel} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: CHANNEL_COLORS[channel.channel] || COLORS[0] }}
                    />
                    <span className="font-medium text-sm text-gray-700 capitalize">{channel.channel}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-600">
                      {channel.delivery_rate.toFixed(1)}% delivery rate
                    </span>
                    <span className="text-xs text-gray-500">
                      {channel.delivered}/{channel.count}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Performing Types */}
        <Card>
          <CardHeader>
            <CardTitle>Top Performing Notification Types</CardTitle>
            <CardDescription>Types with highest open rates</CardDescription>
          </CardHeader>
          <CardContent>
            {typeChartData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={typeChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, open_rate }) => `${name}: ${open_rate.toFixed(1)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="open_rate"
                    >
                      {typeChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value) => `${(value as number).toFixed(1)}%`}
                    />
                  </PieChart>
                </ResponsiveContainer>

                {/* Type Summary Table */}
                <div className="mt-6 space-y-2">
                  {typeChartData.map((type, index) => (
                    <div key={type.type} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        />
                        <span className="font-medium text-sm text-gray-700 capitalize">
                          {type.type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-600">
                          {type.open_rate.toFixed(1)}% open rate
                        </span>
                        <span className="text-xs text-gray-500">
                          {type.count} sent
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500">
                No type data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Detailed Summary */}
      {analyticsData?.summary && (
        <Card>
          <CardHeader>
            <CardTitle>Delivery Summary</CardTitle>
            <CardDescription>Detailed delivery statistics and error analysis</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-600">Average Delivery Time</p>
                <p className="text-2xl font-bold text-gray-900 mt-2">
                  {analyticsData.summary.avg_delivery_time}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Total Failed</p>
                <p className="text-2xl font-bold text-gray-900 mt-2">
                  {analyticsData.summary.total_failed}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Success Rate</p>
                <p className="text-2xl font-bold text-green-600 mt-2">
                  {((1 - analyticsData.summary.failures / (analyticsData.summary.failures + analyticsData.summary.total_sent)) * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Engagement Rate</p>
                <p className="text-2xl font-bold text-blue-600 mt-2">
                  {((analyticsData.summary.total_opened / analyticsData.summary.total_sent) * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            {analyticsData.summary.error_reasons.length > 0 && (
              <div className="mt-6 pt-6 border-t">
                <h4 className="font-medium text-gray-900 mb-3">Top Error Reasons</h4>
                <ul className="space-y-2">
                  {analyticsData.summary.error_reasons.map((error, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm">
                      <span className="text-red-600 font-bold">{index + 1}.</span>
                      <span className="text-gray-700">{error}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default NotificationAnalytics;
