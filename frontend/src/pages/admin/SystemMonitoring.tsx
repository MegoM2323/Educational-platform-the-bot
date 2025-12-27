import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Download,
  Activity,
  Database,
  HardDrive,
  Zap,
  MessageSquare,
  Clock,
} from 'lucide-react';
import { logger } from '@/utils/logger';
import { unifiedAPI as apiClient } from '@/integrations/api/unifiedClient';

/**
 * Types for system monitoring metrics
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

interface CacheMetrics {
  response_time_ms: number;
  is_working: boolean;
  status: 'healthy' | 'error';
}

interface ExternalServiceStatus {
  status: 'healthy' | 'error' | 'disabled' | 'warning';
  response_time_ms?: number;
  message?: string;
}

interface SystemMetrics {
  timestamp: string;
  cpu: CPUMetrics;
  memory: MemoryMetrics;
  disk: DiskMetrics;
  database: DatabaseMetrics;
  cache: CacheMetrics;
  external_services?: {
    telegram?: ExternalServiceStatus;
    yookassa?: ExternalServiceStatus;
    supabase?: ExternalServiceStatus;
  };
}

interface CeleryMetrics {
  failed_tasks: {
    total: number;
    failed: number;
    investigating: number;
    resolved_last_24h: number;
  };
  executions_24h: {
    total: number;
    success: number;
    failed: number;
    success_rate: number;
    avg_duration_seconds: number;
  };
  health_status: 'healthy' | 'warning' | 'critical';
}

interface HistoryMetrics {
  timestamp: Date;
  cpu: number;
  memory: number;
  disk: number;
}

interface SystemAlert {
  type: string;
  severity: 'warning' | 'critical';
  message: string;
  component: string;
}

export default function SystemMonitoring() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [celeryMetrics, setCeleryMetrics] = useState<CeleryMetrics | null>(null);
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [history, setHistory] = useState<HistoryMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d'>('24h');

  // Load metrics on mount and set up auto-refresh
  useEffect(() => {
    loadMetrics();

    if (autoRefresh) {
      const interval = setInterval(loadMetrics, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load system metrics
      const metricsResponse = await apiClient.request<SystemMetrics>('/core/metrics/');
      if (metricsResponse.data) {
        setMetrics(metricsResponse.data);
        logger.info('[SystemMonitoring] Metrics loaded:', metricsResponse.data);

        // Add to history for charts
        setHistory((prev) => [
          ...prev.slice(-23), // Keep last 24 data points
          {
            timestamp: new Date(),
            cpu: metricsResponse.data.cpu.usage_percent,
            memory: metricsResponse.data.memory.used_percent,
            disk: metricsResponse.data.disk.used_percent,
          },
        ]);
      }

      // Load Celery metrics
      const celeryResponse = await apiClient.request<{ data: CeleryMetrics }>(
        '/core/monitoring/celery/'
      );
      if (celeryResponse.data?.data) {
        setCeleryMetrics(celeryResponse.data.data);
      }

      // Load alerts
      const alertsResponse = await apiClient.request<{ alerts: SystemAlert[] }>(
        '/core/alerts/'
      );
      if (alertsResponse.data?.alerts) {
        setAlerts(alertsResponse.data.alerts);
      }

      setLastRefresh(new Date());
    } catch (err) {
      logger.error('[SystemMonitoring] Failed to load metrics:', err);
      setError('Failed to load system metrics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const exportMetrics = () => {
    if (!metrics || !celeryMetrics) {
      logger.warn('[SystemMonitoring] No metrics to export');
      return;
    }

    const csvContent = [
      ['System Metrics Export', new Date().toISOString()],
      [''],
      ['CPU Usage %', metrics.cpu.usage_percent.toString()],
      ['Memory Usage %', metrics.memory.used_percent.toString()],
      ['Disk Usage %', metrics.disk.used_percent.toString()],
      ['Database Response Time (ms)', metrics.database.response_time_ms.toString()],
      ['Cache Status', metrics.cache.status],
      [''],
      ['Celery Tasks (24h)'],
      ['Total', celeryMetrics.executions_24h.total.toString()],
      ['Success', celeryMetrics.executions_24h.success.toString()],
      ['Failed', celeryMetrics.executions_24h.failed.toString()],
      ['Success Rate %', celeryMetrics.executions_24h.success_rate.toString()],
    ]
      .map((row) => row.join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `system-metrics-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4" />;
      case 'critical':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const chartData = history.map((item, index) => ({
    name: `${index}`,
    cpu: parseFloat(item.cpu.toFixed(1)),
    memory: parseFloat(item.memory.toFixed(1)),
    disk: parseFloat(item.disk.toFixed(1)),
  }));

  if (loading && !metrics) {
    return (
      <div className="container mx-auto p-4">
        <div className="flex items-center justify-center h-96">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">Loading metrics...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">System Monitoring</h1>
          <p className="text-muted-foreground mt-1">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={loadMetrics}
            disabled={loading}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={exportMetrics}
            disabled={!metrics}
            variant="outline"
            className="flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
          <Button
            onClick={() => setAutoRefresh(!autoRefresh)}
            variant={autoRefresh ? 'default' : 'outline'}
            className="flex items-center gap-2"
          >
            <Clock className="h-4 w-4" />
            {autoRefresh ? 'Auto (30s)' : 'Manual'}
          </Button>
        </div>
      </div>

      {/* Time Range Selector */}
      <div className="flex gap-2">
        {(['1h', '24h', '7d'] as const).map((range) => (
          <Button
            key={range}
            onClick={() => setTimeRange(range)}
            variant={timeRange === range ? 'default' : 'outline'}
            size="sm"
          >
            {range}
          </Button>
        ))}
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Active Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Active Alerts ({alerts.length})
          </h2>
          {alerts.map((alert, index) => (
            <Alert
              key={index}
              variant={alert.severity === 'critical' ? 'destructive' : 'default'}
            >
              {alert.severity === 'critical' ? (
                <AlertCircle className="h-4 w-4" />
              ) : (
                <AlertTriangle className="h-4 w-4" />
              )}
              <AlertTitle>{alert.component}</AlertTitle>
              <AlertDescription>{alert.message}</AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* System Health Status Cards */}
      {metrics && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* CPU Status */}
            <Card className={getStatusColor(metrics.cpu.status)}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  CPU Usage
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-2xl font-bold">
                    {metrics.cpu.usage_percent.toFixed(1)}%
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    {getStatusIcon(metrics.cpu.status)}
                    <span className="capitalize">{metrics.cpu.status}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {metrics.cpu.core_count} cores
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Memory Status */}
            <Card className={getStatusColor(metrics.memory.status)}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Memory Usage
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-2xl font-bold">
                    {metrics.memory.used_percent.toFixed(1)}%
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    {getStatusIcon(metrics.memory.status)}
                    <span className="capitalize">{metrics.memory.status}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {metrics.memory.available_gb.toFixed(1)}GB available
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Disk Status */}
            <Card className={getStatusColor(metrics.disk.status)}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <HardDrive className="h-4 w-4" />
                  Disk Usage
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-2xl font-bold">
                    {metrics.disk.used_percent.toFixed(1)}%
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    {getStatusIcon(metrics.disk.status)}
                    <span className="capitalize">{metrics.disk.status}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {metrics.disk.free_gb.toFixed(1)}GB free
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Database Status */}
            <Card className={getStatusColor(metrics.database.status)}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Database
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-2xl font-bold">
                    {metrics.database.response_time_ms.toFixed(0)}ms
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    {getStatusIcon(metrics.database.status)}
                    <span className="capitalize">{metrics.database.status}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {metrics.database.user_count} users
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Cache Status */}
            <Card className={getStatusColor(metrics.cache.status)}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Cache
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-2xl font-bold">
                    {metrics.cache.response_time_ms.toFixed(0)}ms
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    {getStatusIcon(metrics.cache.status)}
                    <span className="capitalize">
                      {metrics.cache.is_working ? 'Working' : 'Down'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Performance Metrics Chart */}
          {chartData.length > 1 && (
            <Card>
              <CardHeader>
                <CardTitle>Performance Trends (Last 24 Hours)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip formatter={(value) => `${(value as number).toFixed(1)}%`} />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="cpu"
                      stroke="#ef4444"
                      dot={false}
                      name="CPU %"
                    />
                    <Line
                      type="monotone"
                      dataKey="memory"
                      stroke="#f59e0b"
                      dot={false}
                      name="Memory %"
                    />
                    <Line
                      type="monotone"
                      dataKey="disk"
                      stroke="#3b82f6"
                      dot={false}
                      name="Disk %"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Resource Distribution Charts */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* CPU Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>CPU Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Used', value: metrics.cpu.usage_percent },
                        {
                          name: 'Available',
                          value: Math.max(0, 100 - metrics.cpu.usage_percent),
                        },
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      dataKey="value"
                    >
                      <Cell fill="#ef4444" />
                      <Cell fill="#e5e7eb" />
                    </Pie>
                    <Tooltip formatter={(value) => `${(value as number).toFixed(1)}%`} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Memory Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Memory Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Used', value: metrics.memory.used_percent },
                        {
                          name: 'Available',
                          value: Math.max(0, 100 - metrics.memory.used_percent),
                        },
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      dataKey="value"
                    >
                      <Cell fill="#f59e0b" />
                      <Cell fill="#e5e7eb" />
                    </Pie>
                    <Tooltip formatter={(value) => `${(value as number).toFixed(1)}%`} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Disk Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Disk Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Used', value: metrics.disk.used_percent },
                        {
                          name: 'Free',
                          value: Math.max(0, 100 - metrics.disk.used_percent),
                        },
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      dataKey="value"
                    >
                      <Cell fill="#3b82f6" />
                      <Cell fill="#e5e7eb" />
                    </Pie>
                    <Tooltip formatter={(value) => `${(value as number).toFixed(1)}%`} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {/* Celery Monitoring */}
      {celeryMetrics && (
        <Card>
          <CardHeader>
            <CardTitle>Celery Task Execution (24h)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">Total Tasks</div>
                <div className="text-2xl font-bold">{celeryMetrics.executions_24h.total}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Success</div>
                <div className="text-2xl font-bold text-green-600">
                  {celeryMetrics.executions_24h.success}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Failed</div>
                <div className="text-2xl font-bold text-red-600">
                  {celeryMetrics.executions_24h.failed}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Success Rate</div>
                <div className="text-2xl font-bold">
                  {celeryMetrics.executions_24h.success_rate.toFixed(1)}%
                </div>
              </div>
            </div>
            <div className="mt-4 p-4 bg-muted rounded">
              <div className="text-sm text-muted-foreground">Avg Duration</div>
              <div className="text-lg font-semibold">
                {celeryMetrics.executions_24h.avg_duration_seconds.toFixed(2)}s
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* External Services Status */}
      {metrics?.external_services && (
        <Card>
          <CardHeader>
            <CardTitle>External Services</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(metrics.external_services).map(([service, status]) => (
                <div
                  key={service}
                  className="flex items-center justify-between p-3 bg-muted rounded"
                >
                  <span className="capitalize font-medium">{service}</span>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(status.status)}
                    <span className="capitalize text-sm">{status.status}</span>
                    {status.response_time_ms && (
                      <span className="text-xs text-muted-foreground">
                        ({status.response_time_ms.toFixed(0)}ms)
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
