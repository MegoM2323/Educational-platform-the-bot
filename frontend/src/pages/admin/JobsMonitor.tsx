import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Download,
  Activity,
  Zap,
  Trash2,
  RotateCcw,
  Wifi,
  WifiOff,
  ChevronDown,
  Loader,
} from 'lucide-react';
import { logger } from '@/utils/logger';
import { unifiedAPI as apiClient } from '@/integrations/api/unifiedClient';
import { WebSocketService } from '@/services/websocketService';

// Types for Celery monitoring
interface Worker {
  name: string;
  status: 'online' | 'offline';
  heartbeat: string;
  active_tasks: number;
  memory_usage_mb: number;
  cpu_usage_percent: number;
}

interface Queue {
  name: string;
  length: number;
  retention_policy: string;
}

interface ActiveTask {
  id: string;
  name: string;
  worker: string;
  started_at: string;
  duration_seconds: number;
  status: 'active' | 'pending';
  progress: number;
  args?: string;
  kwargs?: string;
}

interface CompletedTask {
  id: string;
  name: string;
  worker: string;
  duration_seconds: number;
  timestamp: string;
  status: 'success' | 'failed';
  error_message?: string;
}

interface TaskStatistics {
  total_completed: number;
  total_failed: number;
  total_pending: number;
  total_active: number;
  success_rate_percent: number;
  avg_duration_seconds: number;
  error_rate_percent: number;
}

interface WebSocketTaskUpdate {
  type: 'task_update' | 'worker_update' | 'stats_update' | 'error';
  data?: ActiveTask | Worker | TaskStatistics;
  error?: string;
}

/**
 * JobsMonitor Component
 * Monitors Celery background jobs, workers, and queues in real-time
 * Features: WebSocket updates, task statistics, worker status, queue management
 */
export default function JobsMonitor() {
  // State
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [queues, setQueues] = useState<Queue[]>([]);
  const [activeTasks, setActiveTasks] = useState<ActiveTask[]>([]);
  const [completedTasks, setCompletedTasks] = useState<CompletedTask[]>([]);
  const [failedTasks, setFailedTasks] = useState<CompletedTask[]>([]);
  const [statistics, setStatistics] = useState<TaskStatistics | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'duration' | 'started'>('started');
  const [refreshInterval, setRefreshInterval] = useState(2000);

  // WebSocket service ref
  const wsRef = useRef<WebSocketService | null>(null);

  // Initialize WebSocket connection
  useEffect(() => {
    const initializeWebSocket = async () => {
      try {
        setLoading(true);
        // First load initial data
        await loadInitialData();

        // Then connect to WebSocket
        const wsUrl = getWebSocketUrl();
        wsRef.current = new WebSocketService({
          url: wsUrl,
          reconnectInterval: 5000,
          maxReconnectAttempts: 10,
        });

        // Subscribe to task updates
        const taskSubscriptionId = wsRef.current.subscribe('tasks', handleTaskUpdate);
        const workerSubscriptionId = wsRef.current.subscribe('workers', handleWorkerUpdate);
        const statsSubscriptionId = wsRef.current.subscribe('stats', handleStatsUpdate);

        // Connect to WebSocket
        await wsRef.current.connect();
        setConnectionStatus('connected');

        return () => {
          if (wsRef.current) {
            wsRef.current.unsubscribe(taskSubscriptionId);
            wsRef.current.unsubscribe(workerSubscriptionId);
            wsRef.current.unsubscribe(statsSubscriptionId);
            wsRef.current.disconnect();
          }
        };
      } catch (err) {
        logger.error('[JobsMonitor] Failed to initialize WebSocket:', err);
        setConnectionStatus('disconnected');
        setError('Failed to connect to real-time updates');
        // Fall back to polling
        setupPolling();
      }
    };

    initializeWebSocket();
  }, []);

  // Setup polling fallback
  const setupPolling = useCallback(() => {
    const interval = setInterval(async () => {
      try {
        await loadInitialData();
      } catch (err) {
        logger.error('[JobsMonitor] Polling error:', err);
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  // WebSocket handlers
  const handleTaskUpdate = (data: any) => {
    try {
      const task = data as ActiveTask;
      setActiveTasks((prev) =>
        prev
          .map((t) => (t.id === task.id ? { ...t, ...task } : t))
          .filter((t) => t.status !== 'success' && t.status !== 'failed')
      );
    } catch (err) {
      logger.error('[JobsMonitor] Error handling task update:', err);
    }
  };

  const handleWorkerUpdate = (data: any) => {
    try {
      const worker = data as Worker;
      setWorkers((prev) =>
        prev.map((w) => (w.name === worker.name ? { ...w, ...worker } : w))
      );
    } catch (err) {
      logger.error('[JobsMonitor] Error handling worker update:', err);
    }
  };

  const handleStatsUpdate = (data: any) => {
    try {
      const stats = data as TaskStatistics;
      setStatistics(stats);
    } catch (err) {
      logger.error('[JobsMonitor] Error handling stats update:', err);
    }
  };

  // Load initial data from API
  const loadInitialData = async () => {
    try {
      setError(null);
      const response = await apiClient.request<{
        workers: Worker[];
        queues: Queue[];
        active_tasks: ActiveTask[];
        completed_tasks: CompletedTask[];
        failed_tasks: CompletedTask[];
        statistics: TaskStatistics;
      }>('/admin/system/tasks/', {
        method: 'GET',
      });

      if (response.data) {
        setWorkers(response.data.workers || []);
        setQueues(response.data.queues || []);
        setActiveTasks(response.data.active_tasks || []);
        setCompletedTasks(response.data.completed_tasks || []);
        setFailedTasks(response.data.failed_tasks || []);
        setStatistics(response.data.statistics || null);
      }
    } catch (err) {
      logger.error('[JobsMonitor] Failed to load initial data:', err);
      setError('Failed to load monitoring data');
    } finally {
      setLoading(false);
    }
  };

  // Kill task action
  const handleKillTask = async (taskId: string) => {
    if (!window.confirm('Are you sure you want to kill this task?')) return;

    try {
      await apiClient.request(`/admin/tasks/${taskId}/kill/`, {
        method: 'POST',
      });
      setActiveTasks((prev) => prev.filter((t) => t.id !== taskId));
      logger.info('[JobsMonitor] Task killed:', taskId);
    } catch (err) {
      logger.error('[JobsMonitor] Failed to kill task:', err);
      setError('Failed to kill task');
    }
  };

  // Retry failed task
  const handleRetryTask = async (taskId: string) => {
    try {
      await apiClient.request(`/admin/tasks/${taskId}/retry/`, {
        method: 'POST',
      });
      setFailedTasks((prev) => prev.filter((t) => t.id !== taskId));
      logger.info('[JobsMonitor] Task retried:', taskId);
    } catch (err) {
      logger.error('[JobsMonitor] Failed to retry task:', err);
      setError('Failed to retry task');
    }
  };

  // Purge queue
  const handlePurgeQueue = async (queueName: string) => {
    if (!window.confirm(`Are you sure you want to purge the "${queueName}" queue?`)) return;

    try {
      await apiClient.request(`/admin/queues/${queueName}/purge/`, {
        method: 'POST',
      });
      setQueues((prev) =>
        prev.map((q) => (q.name === queueName ? { ...q, length: 0 } : q))
      );
      logger.info('[JobsMonitor] Queue purged:', queueName);
    } catch (err) {
      logger.error('[JobsMonitor] Failed to purge queue:', err);
      setError('Failed to purge queue');
    }
  };

  // Refresh data
  const handleRefresh = async () => {
    await loadInitialData();
  };

  // Download logs
  const handleDownloadLogs = async () => {
    try {
      const response = await apiClient.request('/admin/system/tasks/logs/', {
        method: 'GET',
      });

      if (response.data) {
        const blob = new Blob([JSON.stringify(response.data, null, 2)], {
          type: 'application/json',
        });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `celery-logs-${new Date().toISOString()}.json`;
        link.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      logger.error('[JobsMonitor] Failed to download logs:', err);
      setError('Failed to download logs');
    }
  };

  // Sort active tasks
  const sortedActiveTasks = [...activeTasks].sort((a, b) => {
    if (sortBy === 'duration') {
      return b.duration_seconds - a.duration_seconds;
    }
    return new Date(b.started_at).getTime() - new Date(a.started_at).getTime();
  });

  // Helper function
  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const token = localStorage.getItem('auth_token');
    return `${protocol}//${host}/ws/admin/tasks/?token=${token}`;
  };

  // Status badge color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
      case 'success':
      case 'active':
        return 'text-green-600 bg-green-100';
      case 'offline':
      case 'failed':
        return 'text-red-600 bg-red-100';
      case 'pending':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
      case 'success':
        return <CheckCircle className="h-4 w-4" />;
      case 'offline':
      case 'failed':
        return <AlertCircle className="h-4 w-4" />;
      case 'pending':
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Background Jobs Monitor</h1>
          <p className="text-gray-600 mt-1">Monitor Celery tasks, workers, and queues</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            className="flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadLogs}
            className="flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Download Logs
          </Button>
        </div>
      </div>

      {/* Connection Status */}
      <div className="flex items-center gap-2">
        {connectionStatus === 'connected' ? (
          <>
            <Wifi className="h-4 w-4 text-green-600" />
            <span className="text-sm text-green-600">Real-time connection active</span>
          </>
        ) : (
          <>
            <WifiOff className="h-4 w-4 text-red-600" />
            <span className="text-sm text-red-600">Real-time connection offline (polling)</span>
          </>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Worker Status Grid */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Worker Status</h2>
        {workers.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-gray-500">
              No workers found
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workers.map((worker) => (
              <Card key={worker.name} className="overflow-hidden">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{worker.name}</CardTitle>
                    <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(worker.status)}`}>
                      {getStatusIcon(worker.status)}
                      {worker.status}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Active Tasks:</span>
                    <span className="font-semibold">{worker.active_tasks}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Memory:</span>
                    <span className="font-semibold">{worker.memory_usage_mb}MB</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">CPU:</span>
                    <span className="font-semibold">{worker.cpu_usage_percent.toFixed(1)}%</span>
                  </div>
                  <div className="text-xs text-gray-500 pt-2 border-t">
                    Last heartbeat: {new Date(worker.heartbeat).toLocaleTimeString()}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Queue Status */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Queue Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {queues.length === 0 ? (
            <Card className="md:col-span-3">
              <CardContent className="py-8 text-center text-gray-500">
                No queues found
              </CardContent>
            </Card>
          ) : (
            queues.map((queue) => (
              <Card key={queue.name}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">{queue.name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <div className="text-2xl font-bold text-blue-600">{queue.length}</div>
                    <p className="text-sm text-gray-600">Tasks in queue</p>
                  </div>
                  <div className="text-xs text-gray-500 py-2 border-t">
                    {queue.retention_policy}
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="w-full"
                    onClick={() => handlePurgeQueue(queue.name)}
                  >
                    <Trash2 className="h-3 w-3 mr-2" />
                    Purge
                  </Button>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Statistics */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Completed</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_completed}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Failed</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{statistics.total_failed}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Pending</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{statistics.total_pending}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Success Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {statistics.success_rate_percent.toFixed(1)}%
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Active Tasks and History Tabs */}
      <Tabs defaultValue="active" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="active">
            Active Tasks ({activeTasks.length})
          </TabsTrigger>
          <TabsTrigger value="completed">
            Completed ({completedTasks.length})
          </TabsTrigger>
          <TabsTrigger value="failed">
            Failed ({failedTasks.length})
          </TabsTrigger>
        </TabsList>

        {/* Active Tasks Tab */}
        <TabsContent value="active" className="space-y-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex gap-2">
              <Button
                variant={sortBy === 'started' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSortBy('started')}
              >
                Sort by Started
              </Button>
              <Button
                variant={sortBy === 'duration' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSortBy('duration')}
              >
                Sort by Duration
              </Button>
            </div>
          </div>

          {sortedActiveTasks.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-gray-500">
                No active tasks
              </CardContent>
            </Card>
          ) : (
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Task Name</TableHead>
                    <TableHead>Worker</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Progress</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedActiveTasks.map((task) => (
                    <TableRow key={task.id}>
                      <TableCell>
                        <button
                          onClick={() =>
                            setExpandedTask(expandedTask === task.id ? null : task.id)
                          }
                          className="flex items-center gap-2 hover:text-blue-600"
                        >
                          <ChevronDown
                            className={`h-4 w-4 transition-transform ${
                              expandedTask === task.id ? 'rotate-180' : ''
                            }`}
                          />
                          {task.name}
                        </button>
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">{task.worker}</TableCell>
                      <TableCell className="text-sm">
                        {new Date(task.started_at).toLocaleTimeString()}
                      </TableCell>
                      <TableCell className="text-sm">{task.duration_seconds.toFixed(1)}s</TableCell>
                      <TableCell>
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600">{task.progress}%</span>
                      </TableCell>
                      <TableCell>
                        <div
                          className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                            task.status
                          )}`}
                        >
                          {getStatusIcon(task.status)}
                          {task.status}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleKillTask(task.id)}
                          className="flex items-center gap-1"
                        >
                          <AlertTriangle className="h-3 w-3" />
                          Kill
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>

        {/* Completed Tasks Tab */}
        <TabsContent value="completed" className="space-y-4">
          {completedTasks.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-gray-500">
                No completed tasks
              </CardContent>
            </Card>
          ) : (
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Task Name</TableHead>
                    <TableHead>Worker</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Completed</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {completedTasks.map((task) => (
                    <TableRow key={task.id}>
                      <TableCell>{task.name}</TableCell>
                      <TableCell className="text-sm text-gray-600">{task.worker}</TableCell>
                      <TableCell className="text-sm">{task.duration_seconds.toFixed(1)}s</TableCell>
                      <TableCell className="text-sm">
                        {new Date(task.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <div
                          className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                            task.status
                          )}`}
                        >
                          {getStatusIcon(task.status)}
                          {task.status}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>

        {/* Failed Tasks Tab */}
        <TabsContent value="failed" className="space-y-4">
          {failedTasks.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-gray-500">
                No failed tasks
              </CardContent>
            </Card>
          ) : (
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Task Name</TableHead>
                    <TableHead>Worker</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Failed</TableHead>
                    <TableHead>Error</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {failedTasks.map((task) => (
                    <TableRow key={task.id}>
                      <TableCell>{task.name}</TableCell>
                      <TableCell className="text-sm text-gray-600">{task.worker}</TableCell>
                      <TableCell className="text-sm">{task.duration_seconds.toFixed(1)}s</TableCell>
                      <TableCell className="text-sm">
                        {new Date(task.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm text-red-600 max-w-xs truncate">
                        {task.error_message || 'Unknown error'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRetryTask(task.id)}
                          className="flex items-center gap-1"
                        >
                          <RotateCcw className="h-3 w-3" />
                          Retry
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
