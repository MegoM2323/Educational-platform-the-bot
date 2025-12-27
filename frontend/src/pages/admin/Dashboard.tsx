/**
 * Admin Dashboard - Main system overview and monitoring page
 *
 * Features:
 * - Quick stats cards (users, assignments, sessions, health)
 * - System metrics charts (CPU, memory, disk, API response time)
 * - Real-time activity feed (logins, failed auth, admin actions)
 * - System alerts with priority levels
 * - Quick action buttons for navigation
 * - Auto-refresh with manual refresh option
 * - Responsive grid layout
 *
 * Depends on: T_ADM_002 (System Monitoring Dashboard)
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Users,
  BookOpen,
  Activity,
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  MoreVertical,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Zap,
  HardDrive,
  Server,
  BarChart3,
  Shield,
  Database,
  LogOut,
  Lock,
  Eye,
} from 'lucide-react';
import { logger } from '@/utils/logger';
import { adminAPI } from '@/integrations/api/adminAPI';
import { unifiedAPI as apiClient } from '@/integrations/api/unifiedClient';

/**
 * System Metrics Interfaces
 */
interface CPUMetrics {
  usage_percent: number;
  core_count: number;
  frequency_mhz: number | null;
  status: 'healthy' | 'warning' | 'critical' | 'error';
}

interface MemoryMetrics {
  total_gb: number;
  available_gb: number;
  used_percent: number;
  swap_total_gb: number;
  swap_used_percent: number;
  status: 'healthy' | 'warning' | 'critical' | 'error';
}

interface DiskMetrics {
  total_gb: number;
  used_gb: number;
  free_gb: number;
  used_percent: number;
  status: 'healthy' | 'warning' | 'critical' | 'error';
}

interface DatabaseMetrics {
  response_time_ms: number;
  user_count: number;
  application_count: number;
  payment_count: number;
  status: 'healthy' | 'warning' | 'critical' | 'error';
}

interface SystemMetrics {
  timestamp: string;
  cpu: CPUMetrics;
  memory: MemoryMetrics;
  disk: DiskMetrics;
  database: DatabaseMetrics;
}

interface QuickStat {
  title: string;
  value: number;
  trend?: number; // percentage change
  icon: React.ReactNode;
  color: string;
}

interface ActivityItem {
  id: number;
  timestamp: string;
  user?: {
    id: number;
    email: string;
    full_name: string;
  };
  action: string;
  resource?: string;
  status: 'success' | 'failed';
  details?: string;
}

interface SystemAlert {
  id: string;
  severity: 'warning' | 'critical' | 'info';
  title: string;
  message: string;
  timestamp: string;
}

interface MetricsHistory {
  timestamp: string;
  cpu: number;
  memory: number;
  disk: number;
  apiResponseTime: number;
}

/**
 * Main Admin Dashboard Component
 */
export default function AdminDashboard() {
  const navigate = useNavigate();

  // State
  const [quickStats, setQuickStats] = useState<QuickStat[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<MetricsHistory[]>([]);
  const [activityFeed, setActivityFeed] = useState<ActivityItem[]>([]);
  const [systemAlerts, setSystemAlerts] = useState<SystemAlert[]>([]);
  const [activeSessions, setActiveSessions] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Load data on mount and set up auto-refresh
  useEffect(() => {
    loadAllData();

    if (autoRefresh) {
      // Refresh metrics every 30 seconds
      const metricsInterval = setInterval(() => {
        loadMetrics();
        loadActivity();
      }, 30000);

      // Refresh health every 10 seconds
      const healthInterval = setInterval(() => {
        loadHealth();
      }, 10000);

      return () => {
        clearInterval(metricsInterval);
        clearInterval(healthInterval);
      };
    }
  }, [autoRefresh]);

  /**
   * Load all dashboard data
   */
  const loadAllData = async () => {
    try {
      setLoading(true);
      setError(null);

      await Promise.all([
        loadStats(),
        loadMetrics(),
        loadHealth(),
        loadActivity(),
        loadAlerts(),
      ]);

      setLastRefresh(new Date());
    } catch (err) {
      logger.error('[AdminDashboard] Failed to load data:', err);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Load quick stats (users, assignments, sessions)
   */
  const loadStats = async () => {
    try {
      // Get user stats
      const userStatsResponse = await adminAPI.getUserStats();
      if (userStatsResponse.data) {
        const data = userStatsResponse.data;

        // Get assignment stats
        const assignmentStatsResponse = await apiClient.request<{
          total_assignments: number;
          this_week: number;
          last_week: number;
        }>('/assignments/stats/');

        const assignStats = assignmentStatsResponse.data || {
          total_assignments: 0,
          this_week: 0,
          last_week: 0,
        };

        // Get sessions
        const sessionsResponse = await apiClient.request<{
          active_sessions: number;
        }>('/admin/system/sessions/');

        const sessionCount = sessionsResponse.data?.active_sessions || 0;
        setActiveSessions(sessionCount);

        // Calculate trends (simplified - in real app would compare with previous period)
        const usersTrend = data.total_users > 0 ? 5 : 0;
        const assignmentsTrend =
          assignStats.this_week > 0
            ? Math.round(
                ((assignStats.this_week - assignStats.last_week) / (assignStats.last_week || 1)) *
                  100
              )
            : 0;

        setQuickStats([
          {
            title: 'Total Users',
            value: data.total_users,
            trend: usersTrend,
            icon: <Users className="h-5 w-5" />,
            color: 'bg-blue-100 text-blue-700',
          },
          {
            title: 'Total Assignments',
            value: assignStats.total_assignments,
            trend: assignmentsTrend,
            icon: <BookOpen className="h-5 w-5" />,
            color: 'bg-green-100 text-green-700',
          },
          {
            title: 'Active Sessions',
            value: sessionCount,
            trend: 0,
            icon: <Activity className="h-5 w-5" />,
            color: 'bg-purple-100 text-purple-700',
          },
          {
            title: 'System Health',
            value: 98, // Percentage
            trend: 0,
            icon:
              systemMetrics?.cpu.status === 'healthy' ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
              ),
            color: 'bg-orange-100 text-orange-700',
          },
        ]);
      }
    } catch (err) {
      logger.error('[AdminDashboard] Failed to load stats:', err);
    }
  };

  /**
   * Load system metrics
   */
  const loadMetrics = async () => {
    try {
      const response = await apiClient.request<SystemMetrics>('/core/metrics/');
      if (response.data) {
        setSystemMetrics(response.data);
        logger.info('[AdminDashboard] Metrics loaded:', response.data);

        // Add to history
        setMetricsHistory((prev) => {
          const newHistory = [
            ...prev.slice(-23), // Keep last 24 data points
            {
              timestamp: new Date().toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
              }),
              cpu: response.data.cpu.usage_percent,
              memory: response.data.memory.used_percent,
              disk: response.data.disk.used_percent,
              apiResponseTime: response.data.database.response_time_ms,
            },
          ];
          return newHistory;
        });
      }
    } catch (err) {
      logger.error('[AdminDashboard] Failed to load metrics:', err);
    }
  };

  /**
   * Load health status
   */
  const loadHealth = async () => {
    try {
      const response = await apiClient.request<{ status: string }>('/health/');
      if (response.data?.status === 'healthy') {
        logger.info('[AdminDashboard] System is healthy');
      }
    } catch (err) {
      logger.error('[AdminDashboard] Health check failed:', err);
    }
  };

  /**
   * Load activity feed
   */
  const loadActivity = async () => {
    try {
      // Get login/logout activities
      const auditLogsResponse = await adminAPI.getAuditLogs({
        page_size: 20,
        ordering: '-timestamp',
      });

      if (auditLogsResponse.data?.results) {
        setActivityFeed(
          auditLogsResponse.data.results.map((log: any) => ({
            id: log.id,
            timestamp: log.timestamp,
            user: log.user,
            action: log.action,
            resource: log.resource,
            status: log.status,
            details: log.details,
          }))
        );
      }
    } catch (err) {
      logger.error('[AdminDashboard] Failed to load activity feed:', err);
    }
  };

  /**
   * Load system alerts
   */
  const loadAlerts = async () => {
    try {
      const response = await apiClient.request<{ alerts: SystemAlert[] }>('/core/alerts/');
      if (response.data?.alerts) {
        setSystemAlerts(response.data.alerts.slice(0, 5)); // Show top 5 alerts
      }
    } catch (err) {
      logger.error('[AdminDashboard] Failed to load alerts:', err);
    }
  };

  /**
   * Get status color based on metric status
   */
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-50';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50';
      case 'critical':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  /**
   * Get trend icon
   */
  const getTrendIcon = (trend?: number) => {
    if (!trend) return <Minus className="h-4 w-4 text-gray-400" />;
    return trend > 0 ? (
      <ArrowUpRight className="h-4 w-4 text-red-500" />
    ) : (
      <ArrowDownRight className="h-4 w-4 text-green-500" />
    );
  };

  /**
   * Get action icon
   */
  const getActionIcon = (action: string) => {
    switch (action) {
      case 'login':
        return <Activity className="h-4 w-4" />;
      case 'logout':
        return <LogOut className="h-4 w-4" />;
      case 'create':
      case 'update':
      case 'delete':
        return <Eye className="h-4 w-4" />;
      case 'export':
        return <BarChart3 className="h-4 w-4" />;
      default:
        return <Shield className="h-4 w-4" />;
    }
  };

  // Render loading state
  if (loading && quickStats.length === 0) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-12 bg-gray-200 rounded w-1/3" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground mt-1">System overview and monitoring</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadAllData()}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Auto' : 'Manual'}
          </Button>
          <span className="text-xs text-muted-foreground">
            Last update: {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Quick Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {quickStats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">{stat.value}</div>
                  {stat.trend !== undefined && (
                    <div className="flex items-center gap-1 mt-2">
                      {getTrendIcon(stat.trend)}
                      <span
                        className={`text-xs ${
                          stat.trend > 0 ? 'text-red-600' : 'text-green-600'
                        }`}
                      >
                        {Math.abs(stat.trend)}%
                      </span>
                    </div>
                  )}
                </div>
                <div className={`p-3 rounded-lg ${stat.color}`}>{stat.icon}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* System Metrics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU & Memory Chart */}
        {metricsHistory.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Resource Usage (Last 24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={metricsHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="cpu"
                    stroke="#ef4444"
                    name="CPU %"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="memory"
                    stroke="#f59e0b"
                    name="Memory %"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="disk"
                    stroke="#8b5cf6"
                    name="Disk %"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* API Response Time Chart */}
        {metricsHistory.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                API Response Time (Last 24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={metricsHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="apiResponseTime" fill="#3b82f6" name="Response Time (ms)" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Current System Metrics */}
      {systemMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* CPU Metrics */}
          <Card className={getStatusColor(systemMetrics.cpu.status)}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Zap className="h-4 w-4" />
                CPU
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{systemMetrics.cpu.usage_percent}%</div>
              <p className="text-xs mt-2">Cores: {systemMetrics.cpu.core_count}</p>
            </CardContent>
          </Card>

          {/* Memory Metrics */}
          <Card className={getStatusColor(systemMetrics.memory.status)}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Memory</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{systemMetrics.memory.used_percent}%</div>
              <p className="text-xs mt-2">
                {systemMetrics.memory.available_gb.toFixed(1)} GB available
              </p>
            </CardContent>
          </Card>

          {/* Disk Metrics */}
          <Card className={getStatusColor(systemMetrics.disk.status)}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <HardDrive className="h-4 w-4" />
                Disk
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{systemMetrics.disk.used_percent}%</div>
              <p className="text-xs mt-2">{systemMetrics.disk.free_gb.toFixed(1)} GB free</p>
            </CardContent>
          </Card>

          {/* Database Metrics */}
          <Card className={getStatusColor(systemMetrics.database.status)}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Database className="h-4 w-4" />
                Database
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{systemMetrics.database.response_time_ms}ms</div>
              <p className="text-xs mt-2">{systemMetrics.database.user_count} users</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Activity Feed & Alerts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity Feed */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Activity (Last 20 events)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {activityFeed.length > 0 ? (
                activityFeed.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start gap-3 p-2 rounded hover:bg-gray-50 border-l-2 border-gray-200"
                  >
                    <div className="mt-1">{getActionIcon(item.action)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm truncate">
                          {item.user?.full_name || 'System'}
                        </span>
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            item.status === 'success'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {item.status}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">
                        {item.action} {item.resource}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(item.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No recent activity</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* System Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              System Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {systemAlerts.length > 0 ? (
                systemAlerts.map((alert) => (
                  <Alert
                    key={alert.id}
                    variant={alert.severity === 'critical' ? 'destructive' : 'default'}
                  >
                    {alert.severity === 'critical' ? (
                      <AlertTriangle className="h-4 w-4" />
                    ) : (
                      <AlertCircle className="h-4 w-4" />
                    )}
                    <div>
                      <AlertTitle className="text-sm">{alert.title}</AlertTitle>
                      <AlertDescription className="text-xs mt-1">
                        {alert.message}
                      </AlertDescription>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(alert.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </Alert>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No active alerts</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <Button
              variant="outline"
              className="justify-start"
              onClick={() => navigate('/admin/system-monitoring')}
            >
              <Server className="h-4 w-4 mr-2" />
              View System Health
            </Button>
            <Button
              variant="outline"
              className="justify-start"
              onClick={() => navigate('/admin/audit')}
            >
              <BarChart3 className="h-4 w-4 mr-2" />
              View Audit Logs
            </Button>
            <Button
              variant="outline"
              className="justify-start"
              onClick={() => navigate('/admin/account-management')}
            >
              <Users className="h-4 w-4 mr-2" />
              Manage Users
            </Button>
            <Button
              variant="outline"
              className="justify-start"
              onClick={() => navigate('/admin/jobs')}
            >
              <Activity className="h-4 w-4 mr-2" />
              Monitor Jobs
            </Button>
            <Button
              variant="outline"
              className="justify-start"
              onClick={() => navigate('/admin/system-monitoring')}
            >
              <Database className="h-4 w-4 mr-2" />
              View Database Status
            </Button>
            <Button
              variant="outline"
              className="justify-start"
              onClick={() => navigate('/admin/schedule')}
            >
              <Clock className="h-4 w-4 mr-2" />
              View Configuration
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
