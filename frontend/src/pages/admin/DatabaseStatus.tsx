import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Pagination, PaginationContent, PaginationItem, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Download,
  Database,
  Play,
  Pause,
  Trash2,
  DownloadCloud,
  UploadCloud,
  AlertDialog,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { logger } from '@/utils/logger';
import { unifiedAPI as apiClient } from '@/integrations/api/unifiedClient';
import { toast } from 'sonner';

// Types for database monitoring
interface DatabaseStatus {
  database_type: string;
  database_version: string;
  database_size_mb: number;
  connection_pool_active: number;
  connection_pool_max: number;
  last_backup_timestamp: string | null;
  backup_status: 'pending' | 'in_progress' | 'completed' | 'failed';
  health_status: 'green' | 'yellow' | 'red';
  last_check_timestamp: string;
  alerts: Alert[];
}

interface Alert {
  id: string;
  severity: 'warning' | 'critical';
  message: string;
  component: string;
  timestamp: string;
}

interface TableStatistics {
  name: string;
  row_count: number;
  size_mb: number;
  last_vacuum: string | null;
  last_reindex: string | null;
  bloat_percentage: number;
  bloat_level: 'low' | 'medium' | 'high';
}

interface SlowQuery {
  id: string;
  query: string;
  count: number;
  avg_time_ms: number;
  max_time_ms: number;
  min_time_ms: number;
}

interface MaintenanceTask {
  name: string;
  last_run: string | null;
  estimated_duration_minutes: number;
  description: string;
}

interface Backup {
  id: string;
  filename: string;
  size_mb: number;
  created_date: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

interface Connection {
  pid: number;
  query: string;
  started_at: string;
  duration_seconds: number;
  user: string;
}

interface OperationResult {
  success: boolean;
  message: string;
  data?: {
    disk_freed_mb?: number;
    rows_processed?: number;
    duration_seconds?: number;
  };
}

/**
 * Database Status and Maintenance Page
 *
 * Features:
 * - Real-time database metrics and health status
 * - Table statistics with sorting and filtering
 * - Slow queries tracking
 * - Maintenance operations (vacuum, reindex, cleanup)
 * - Backup management (create, download, restore, delete)
 * - Connection and query monitoring with kill capability
 * - Auto-refresh with configurable interval
 * - Export to JSON/CSV
 */
export default function DatabaseStatus() {
  // State for main metrics
  const [dbStatus, setDbStatus] = useState<DatabaseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(10); // seconds

  // State for table statistics
  const [tableStats, setTableStats] = useState<TableStatistics[]>([]);
  const [filteredTableStats, setFilteredTableStats] = useState<TableStatistics[]>([]);
  const [tableFilter, setTableFilter] = useState<'all' | 'low' | 'medium' | 'high'>('all');
  const [tableSortBy, setTableSortBy] = useState<string>('name');
  const [tablePage, setTablePage] = useState(1);
  const [tableSortDesc, setTableSortDesc] = useState(false);

  // State for slow queries
  const [slowQueries, setSlowQueries] = useState<SlowQuery[]>([]);
  const [expandedQuery, setExpandedQuery] = useState<string | null>(null);

  // State for maintenance
  const [maintenanceTasks, setMaintenanceTasks] = useState<MaintenanceTask[]>([]);
  const [operationInProgress, setOperationInProgress] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [operationResult, setOperationResult] = useState<OperationResult | null>(null);

  // State for backups
  const [backups, setBackups] = useState<Backup[]>([]);
  const [backupPage, setBackupPage] = useState(1);

  // State for connections
  const [connections, setConnections] = useState<Connection[]>([]);

  // State for dialogs
  const [deleteBackupDialog, setDeleteBackupDialog] = useState(false);
  const [restoreBackupDialog, setRestoreBackupDialog] = useState(false);
  const [killQueryDialog, setKillQueryDialog] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState<Backup | null>(null);
  const [selectedConnection, setSelectedConnection] = useState<Connection | null>(null);

  // Load all data on mount
  useEffect(() => {
    loadAllData();
  }, []);

  // Auto-refresh interval
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadAllData();
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  // Filter and sort table statistics
  useEffect(() => {
    let filtered = tableStats;

    if (tableFilter !== 'all') {
      filtered = filtered.filter((t) => t.bloat_level === tableFilter);
    }

    filtered = filtered.sort((a, b) => {
      let aVal: any = (a as any)[tableSortBy];
      let bVal: any = (b as any)[tableSortBy];

      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = (bVal as string).toLowerCase();
      }

      const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return tableSortDesc ? -comparison : comparison;
    });

    setFilteredTableStats(filtered);
    setTablePage(1);
  }, [tableStats, tableFilter, tableSortBy, tableSortDesc]);

  const loadAllData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Load database status
      const statusResponse = await apiClient.request<DatabaseStatus>(
        '/admin/system/database/'
      );
      if (statusResponse.data) {
        setDbStatus(statusResponse.data);
        logger.info('[DatabaseStatus] Status loaded');
      }

      // Load table statistics
      const tablesResponse = await apiClient.request<{ tables: TableStatistics[] }>(
        '/admin/system/database/tables/'
      );
      if (tablesResponse.data?.tables) {
        setTableStats(tablesResponse.data.tables);
      }

      // Load slow queries
      const queriesResponse = await apiClient.request<{ queries: SlowQuery[] }>(
        '/admin/system/database/queries/'
      );
      if (queriesResponse.data?.queries) {
        setSlowQueries(queriesResponse.data.queries);
      }

      // Load backups
      const backupsResponse = await apiClient.request<{ backups: Backup[] }>(
        '/admin/system/database/backups/'
      );
      if (backupsResponse.data?.backups) {
        setBackups(backupsResponse.data.backups);
      }

      // Load connections
      const connectionsResponse = await apiClient.request<{ connections: Connection[] }>(
        '/admin/system/database/connections/'
      );
      if (connectionsResponse.data?.connections) {
        setConnections(connectionsResponse.data.connections);
      }

      // Load maintenance tasks
      const maintenanceResponse = await apiClient.request<{ tasks: MaintenanceTask[] }>(
        '/admin/system/database/maintenance/'
      );
      if (maintenanceResponse.data?.tasks) {
        setMaintenanceTasks(maintenanceResponse.data.tasks);
      }

      setLastRefresh(new Date());
    } catch (err) {
      logger.error('[DatabaseStatus] Failed to load data:', err);
      setError('Failed to load database information. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleMaintenanceOperation = async (operationName: string) => {
    try {
      setOperationInProgress(true);
      setOperationResult(null);

      const response = await apiClient.request<OperationResult>(
        '/admin/database/maintenance/',
        {
          method: 'POST',
          body: JSON.stringify({
            operation: operationName,
            dry_run: dryRun,
          }),
        }
      );

      if (response.data) {
        setOperationResult(response.data);
        toast.success(`${operationName} completed successfully`);

        if (!dryRun) {
          // Reload data after operation
          setTimeout(loadAllData, 1000);
        }
      }
    } catch (err) {
      logger.error('[DatabaseStatus] Operation failed:', err);
      toast.error(`Failed to execute ${operationName}`);
    } finally {
      setOperationInProgress(false);
    }
  };

  const handleCreateBackup = async () => {
    try {
      setOperationInProgress(true);

      const response = await apiClient.request<Backup>(
        '/admin/database/backup/',
        {
          method: 'POST',
        }
      );

      if (response.data) {
        toast.success('Backup created successfully');
        loadAllData();
      }
    } catch (err) {
      logger.error('[DatabaseStatus] Backup failed:', err);
      toast.error('Failed to create backup');
    } finally {
      setOperationInProgress(false);
    }
  };

  const handleDownloadBackup = async (backup: Backup) => {
    try {
      const response = await apiClient.request<Blob>(
        `/admin/database/backup/${backup.id}/download/`,
        {
          headers: {
            Accept: 'application/octet-stream',
          },
        }
      );

      if (response.data) {
        const url = window.URL.createObjectURL(response.data as any);
        const link = document.createElement('a');
        link.href = url;
        link.download = backup.filename;
        link.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      logger.error('[DatabaseStatus] Download failed:', err);
      toast.error('Failed to download backup');
    }
  };

  const handleDeleteBackup = async () => {
    if (!selectedBackup) return;

    try {
      await apiClient.request(`/admin/database/backup/${selectedBackup.id}/`, {
        method: 'DELETE',
      });

      toast.success('Backup deleted successfully');
      setDeleteBackupDialog(false);
      loadAllData();
    } catch (err) {
      logger.error('[DatabaseStatus] Delete failed:', err);
      toast.error('Failed to delete backup');
    }
  };

  const handleRestoreBackup = async () => {
    if (!selectedBackup) return;

    try {
      setOperationInProgress(true);

      await apiClient.request(`/admin/database/backup/${selectedBackup.id}/restore/`, {
        method: 'POST',
      });

      toast.success('Backup restored successfully');
      setRestoreBackupDialog(false);
      loadAllData();
    } catch (err) {
      logger.error('[DatabaseStatus] Restore failed:', err);
      toast.error('Failed to restore backup');
    } finally {
      setOperationInProgress(false);
    }
  };

  const handleKillQuery = async () => {
    if (!selectedConnection) return;

    try {
      await apiClient.request('/admin/database/kill-query/', {
        method: 'POST',
        body: JSON.stringify({ pid: selectedConnection.pid }),
      });

      toast.success('Query terminated successfully');
      setKillQueryDialog(false);
      loadAllData();
    } catch (err) {
      logger.error('[DatabaseStatus] Kill query failed:', err);
      toast.error('Failed to terminate query');
    }
  };

  const exportMetrics = () => {
    if (!dbStatus) return;

    const data = {
      timestamp: new Date().toISOString(),
      database: dbStatus,
      tables: tableStats,
      slowQueries: slowQueries,
      backups: backups,
      connections: connections,
    };

    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `database-status-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    window.URL.revokeObjectURL(url);

    toast.success('Database metrics exported');
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'green':
        return 'text-green-600 bg-green-50';
      case 'yellow':
        return 'text-yellow-600 bg-yellow-50';
      case 'red':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'green':
        return <CheckCircle className="h-4 w-4" />;
      case 'yellow':
        return <AlertTriangle className="h-4 w-4" />;
      case 'red':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Database className="h-4 w-4" />;
    }
  };

  const getBloatColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatSize = (mb: number) => {
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(2)} GB`;
    }
    return `${mb.toFixed(2)} MB`;
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const tableItemsPerPage = 20;
  const backupItemsPerPage = 10;
  const tablePaginatedItems = filteredTableStats.slice(
    (tablePage - 1) * tableItemsPerPage,
    tablePage * tableItemsPerPage
  );
  const backupPaginatedItems = backups.slice(
    (backupPage - 1) * backupItemsPerPage,
    backupPage * backupItemsPerPage
  );

  if (loading && !dbStatus) {
    return (
      <div className="container mx-auto p-4">
        <div className="flex items-center justify-center h-96">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">Loading database status...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Database Status</h1>
          <p className="text-muted-foreground mt-1">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={loadAllData}
            disabled={loading}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={() => setAutoRefresh(!autoRefresh)}
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            className="flex items-center gap-2"
          >
            {autoRefresh ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            {autoRefresh ? 'Pause' : 'Resume'}
          </Button>
          <Button
            onClick={exportMetrics}
            disabled={!dbStatus}
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Database Status Overview */}
      {dbStatus && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Database Overview
              </span>
              <div className={`flex items-center gap-2 px-3 py-1 rounded-lg ${getHealthColor(dbStatus.health_status)}`}>
                {getHealthIcon(dbStatus.health_status)}
                <span className="text-sm font-medium">
                  {dbStatus.health_status === 'green' ? 'Healthy' : dbStatus.health_status === 'yellow' ? 'Warning' : 'Critical'}
                </span>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">Database Type</p>
                <p className="text-lg font-semibold">{dbStatus.database_type}</p>
              </div>
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">Version</p>
                <p className="text-lg font-semibold">{dbStatus.database_version}</p>
              </div>
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">Database Size</p>
                <p className="text-lg font-semibold">{formatSize(dbStatus.database_size_mb)}</p>
              </div>
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">Connection Pool</p>
                <p className="text-lg font-semibold">
                  {dbStatus.connection_pool_active} / {dbStatus.connection_pool_max}
                </p>
              </div>
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">Last Backup</p>
                <p className="text-lg font-semibold">
                  {dbStatus.last_backup_timestamp ? formatDate(dbStatus.last_backup_timestamp) : 'Never'}
                </p>
              </div>
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">Backup Status</p>
                <Badge variant="outline" className="mt-1">
                  {dbStatus.backup_status}
                </Badge>
              </div>
            </div>

            {dbStatus.alerts.length > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-sm font-semibold">Alerts ({dbStatus.alerts.length})</p>
                <div className="space-y-2">
                  {dbStatus.alerts.slice(0, 5).map((alert) => (
                    <Alert key={alert.id} variant={alert.severity === 'critical' ? 'destructive' : 'default'}>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        <strong>{alert.component}</strong>: {alert.message}
                      </AlertDescription>
                    </Alert>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tabs for different sections */}
      <Tabs defaultValue="tables" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 lg:grid-cols-5">
          <TabsTrigger value="tables">Tables</TabsTrigger>
          <TabsTrigger value="queries">Slow Queries</TabsTrigger>
          <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
          <TabsTrigger value="backups">Backups</TabsTrigger>
          <TabsTrigger value="connections">Connections</TabsTrigger>
        </TabsList>

        {/* Tab 1: Table Statistics */}
        <TabsContent value="tables">
          <Card>
            <CardHeader>
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <CardTitle>Table Statistics</CardTitle>
                <div className="flex flex-wrap gap-2">
                  <select
                    value={tableFilter}
                    onChange={(e) => setTableFilter(e.target.value as any)}
                    className="px-2 py-1 border rounded text-sm"
                  >
                    <option value="all">All Tables</option>
                    <option value="low">Low Bloat</option>
                    <option value="medium">Medium Bloat</option>
                    <option value="high">High Bloat</option>
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="w-full border rounded-lg">
                <Table className="w-full">
                  <TableHeader>
                    <TableRow>
                      <TableHead
                        className="cursor-pointer"
                        onClick={() => {
                          setTableSortBy('name');
                          setTableSortDesc(tableSortBy === 'name' ? !tableSortDesc : false);
                        }}
                      >
                        Name {tableSortBy === 'name' && (tableSortDesc ? '↓' : '↑')}
                      </TableHead>
                      <TableHead
                        className="cursor-pointer text-right"
                        onClick={() => {
                          setTableSortBy('row_count');
                          setTableSortDesc(tableSortBy === 'row_count' ? !tableSortDesc : false);
                        }}
                      >
                        Rows {tableSortBy === 'row_count' && (tableSortDesc ? '↓' : '↑')}
                      </TableHead>
                      <TableHead
                        className="cursor-pointer text-right"
                        onClick={() => {
                          setTableSortBy('size_mb');
                          setTableSortDesc(tableSortBy === 'size_mb' ? !tableSortDesc : false);
                        }}
                      >
                        Size {tableSortBy === 'size_mb' && (tableSortDesc ? '↓' : '↑')}
                      </TableHead>
                      <TableHead className="text-right">Last Vacuum</TableHead>
                      <TableHead className="text-right">Last Reindex</TableHead>
                      <TableHead
                        className="cursor-pointer text-right"
                        onClick={() => {
                          setTableSortBy('bloat_percentage');
                          setTableSortDesc(tableSortBy === 'bloat_percentage' ? !tableSortDesc : false);
                        }}
                      >
                        Bloat {tableSortBy === 'bloat_percentage' && (tableSortDesc ? '↓' : '↑')}
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tablePaginatedItems.length > 0 ? (
                      tablePaginatedItems.map((table) => (
                        <TableRow key={table.name}>
                          <TableCell className="font-medium">{table.name}</TableCell>
                          <TableCell className="text-right">{table.row_count.toLocaleString()}</TableCell>
                          <TableCell className="text-right">{formatSize(table.size_mb)}</TableCell>
                          <TableCell className="text-right text-sm">
                            {table.last_vacuum ? formatDate(table.last_vacuum) : 'Never'}
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {table.last_reindex ? formatDate(table.last_reindex) : 'Never'}
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge className={getBloatColor(table.bloat_level)}>
                              {table.bloat_percentage.toFixed(1)}%
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-4 text-muted-foreground">
                          No tables found
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </ScrollArea>

              {filteredTableStats.length > tableItemsPerPage && (
                <div className="mt-4 flex justify-center">
                  <Pagination>
                    <PaginationContent>
                      {tablePage > 1 && (
                        <PaginationItem>
                          <PaginationPrevious
                            onClick={() => setTablePage((p) => Math.max(1, p - 1))}
                            className="cursor-pointer"
                          />
                        </PaginationItem>
                      )}
                      <PaginationItem>
                        <span className="text-sm">
                          Page {tablePage} of {Math.ceil(filteredTableStats.length / tableItemsPerPage)}
                        </span>
                      </PaginationItem>
                      {tablePage < Math.ceil(filteredTableStats.length / tableItemsPerPage) && (
                        <PaginationItem>
                          <PaginationNext
                            onClick={() => setTablePage((p) => p + 1)}
                            className="cursor-pointer"
                          />
                        </PaginationItem>
                      )}
                    </PaginationContent>
                  </Pagination>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Slow Queries */}
        <TabsContent value="queries">
          <Card>
            <CardHeader>
              <CardTitle>Slow Queries (Top 10)</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="w-full border rounded-lg">
                <div className="space-y-2">
                  {slowQueries.length > 0 ? (
                    slowQueries.map((query) => (
                      <div
                        key={query.id}
                        className="border rounded-lg p-3 space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <p className="text-sm font-mono bg-muted p-2 rounded truncate">
                              {query.query.substring(0, 80)}...
                            </p>
                            {expandedQuery === query.id && (
                              <p className="text-xs font-mono bg-muted p-2 rounded mt-2 break-all">
                                {query.query}
                              </p>
                            )}
                          </div>
                          <button
                            onClick={() => setExpandedQuery(expandedQuery === query.id ? null : query.id)}
                            className="ml-2 text-xs text-blue-600 hover:underline"
                          >
                            {expandedQuery === query.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </button>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                          <div>
                            <p className="text-muted-foreground">Count</p>
                            <p className="font-semibold">{query.count}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Avg (ms)</p>
                            <p className="font-semibold">{query.avg_time_ms.toFixed(2)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Max (ms)</p>
                            <p className="font-semibold">{query.max_time_ms.toFixed(2)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Min (ms)</p>
                            <p className="font-semibold">{query.min_time_ms.toFixed(2)}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-center py-4 text-muted-foreground">No slow queries detected</p>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Maintenance Operations */}
        <TabsContent value="maintenance">
          <Card>
            <CardHeader>
              <CardTitle>Database Maintenance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Dry-run option */}
              <div className="flex items-center gap-2 p-3 border rounded-lg bg-muted/30">
                <Checkbox
                  id="dryRun"
                  checked={dryRun}
                  onCheckedChange={(checked) => setDryRun(checked as boolean)}
                  disabled={operationInProgress}
                />
                <label htmlFor="dryRun" className="text-sm font-medium cursor-pointer">
                  Dry-run mode (preview changes without executing)
                </label>
              </div>

              {/* Operation result */}
              {operationResult && (
                <Alert variant={operationResult.success ? 'default' : 'destructive'}>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    {operationResult.message}
                    {operationResult.data && (
                      <div className="mt-2 text-sm space-y-1">
                        {operationResult.data.disk_freed_mb && (
                          <p>Disk freed: {formatSize(operationResult.data.disk_freed_mb)}</p>
                        )}
                        {operationResult.data.rows_processed && (
                          <p>Rows processed: {operationResult.data.rows_processed}</p>
                        )}
                        {operationResult.data.duration_seconds && (
                          <p>Duration: {operationResult.data.duration_seconds}s</p>
                        )}
                      </div>
                    )}
                  </AlertDescription>
                </Alert>
              )}

              {/* Operation progress */}
              {operationInProgress && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Operation in progress...</p>
                  <Progress value={66} className="w-full" />
                </div>
              )}

              {/* Maintenance operations grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {maintenanceTasks.map((task) => (
                  <div key={task.name} className="border rounded-lg p-4 space-y-3">
                    <div>
                      <h3 className="font-semibold">{task.name}</h3>
                      <p className="text-sm text-muted-foreground">{task.description}</p>
                    </div>
                    <div className="text-xs text-muted-foreground space-y-1">
                      <p>Last run: {task.last_run ? formatDate(task.last_run) : 'Never'}</p>
                      <p>Estimated duration: {task.estimated_duration_minutes} minutes</p>
                    </div>
                    <Button
                      onClick={() => handleMaintenanceOperation(task.name.toLowerCase().replace(/\s+/g, '_'))}
                      disabled={operationInProgress}
                      size="sm"
                      variant="outline"
                    >
                      Run {task.name}
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Backup Management */}
        <TabsContent value="backups">
          <Card>
            <CardHeader>
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <CardTitle>Backup Management</CardTitle>
                <Button
                  onClick={handleCreateBackup}
                  disabled={operationInProgress}
                  className="flex items-center gap-2"
                >
                  <DownloadCloud className="h-4 w-4" />
                  Create New Backup
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="w-full border rounded-lg">
                <Table className="w-full">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Filename</TableHead>
                      <TableHead className="text-right">Size</TableHead>
                      <TableHead className="text-right">Created Date</TableHead>
                      <TableHead className="text-right">Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {backupPaginatedItems.length > 0 ? (
                      backupPaginatedItems.map((backup) => (
                        <TableRow key={backup.id}>
                          <TableCell className="font-mono text-sm">{backup.filename}</TableCell>
                          <TableCell className="text-right">{formatSize(backup.size_mb)}</TableCell>
                          <TableCell className="text-right text-sm">
                            {formatDate(backup.created_date)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge variant="outline">{backup.status}</Badge>
                          </TableCell>
                          <TableCell className="text-right space-x-1">
                            <Button
                              onClick={() => handleDownloadBackup(backup)}
                              disabled={operationInProgress}
                              size="sm"
                              variant="ghost"
                              title="Download backup"
                            >
                              <DownloadCloud className="h-4 w-4" />
                            </Button>
                            <Button
                              onClick={() => {
                                setSelectedBackup(backup);
                                setRestoreBackupDialog(true);
                              }}
                              disabled={operationInProgress}
                              size="sm"
                              variant="ghost"
                              title="Restore backup"
                            >
                              <UploadCloud className="h-4 w-4" />
                            </Button>
                            <Button
                              onClick={() => {
                                setSelectedBackup(backup);
                                setDeleteBackupDialog(true);
                              }}
                              disabled={operationInProgress}
                              size="sm"
                              variant="ghost"
                              className="text-red-600"
                              title="Delete backup"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center py-4 text-muted-foreground">
                          No backups found
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </ScrollArea>

              {backups.length > backupItemsPerPage && (
                <div className="mt-4 flex justify-center">
                  <Pagination>
                    <PaginationContent>
                      {backupPage > 1 && (
                        <PaginationItem>
                          <PaginationPrevious
                            onClick={() => setBackupPage((p) => Math.max(1, p - 1))}
                            className="cursor-pointer"
                          />
                        </PaginationItem>
                      )}
                      <PaginationItem>
                        <span className="text-sm">
                          Page {backupPage} of {Math.ceil(backups.length / backupItemsPerPage)}
                        </span>
                      </PaginationItem>
                      {backupPage < Math.ceil(backups.length / backupItemsPerPage) && (
                        <PaginationItem>
                          <PaginationNext
                            onClick={() => setBackupPage((p) => p + 1)}
                            className="cursor-pointer"
                          />
                        </PaginationItem>
                      )}
                    </PaginationContent>
                  </Pagination>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 5: Connections & Queries */}
        <TabsContent value="connections">
          <Card>
            <CardHeader>
              <CardTitle>Long-Running Queries (> 30 seconds)</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="w-full border rounded-lg">
                <Table className="w-full">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Query</TableHead>
                      <TableHead className="text-right">Started</TableHead>
                      <TableHead className="text-right">Duration (s)</TableHead>
                      <TableHead className="text-right">User</TableHead>
                      <TableHead className="text-right">PID</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {connections.length > 0 ? (
                      connections.map((conn) => (
                        <TableRow key={conn.pid}>
                          <TableCell className="font-mono text-sm max-w-xs truncate">
                            {conn.query}
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {formatDate(conn.started_at)}
                          </TableCell>
                          <TableCell className="text-right">{conn.duration_seconds}</TableCell>
                          <TableCell className="text-right">{conn.user}</TableCell>
                          <TableCell className="text-right">{conn.pid}</TableCell>
                          <TableCell className="text-right">
                            <Button
                              onClick={() => {
                                setSelectedConnection(conn);
                                setKillQueryDialog(true);
                              }}
                              disabled={operationInProgress}
                              size="sm"
                              variant="ghost"
                              className="text-red-600"
                              title="Terminate query"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-4 text-muted-foreground">
                          No long-running queries
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Delete Backup Dialog */}
      <Dialog open={deleteBackupDialog} onOpenChange={setDeleteBackupDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Backup</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this backup? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {selectedBackup && (
            <div className="py-4">
              <p className="text-sm">
                <strong>Filename:</strong> {selectedBackup.filename}
              </p>
              <p className="text-sm mt-2">
                <strong>Size:</strong> {formatSize(selectedBackup.size_mb)}
              </p>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteBackupDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteBackup}
              disabled={operationInProgress}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Restore Backup Dialog */}
      <Dialog open={restoreBackupDialog} onOpenChange={setRestoreBackupDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Restore Backup</DialogTitle>
            <DialogDescription>
              WARNING: Restoring a backup will overwrite the current database. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {selectedBackup && (
            <div className="py-4 space-y-4">
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Data Loss Warning</AlertTitle>
                <AlertDescription>
                  All current data will be replaced with data from the backup. Any changes made since the backup was created will be lost.
                </AlertDescription>
              </Alert>
              <div className="p-3 border rounded-lg bg-muted/30">
                <p className="text-sm">
                  <strong>Filename:</strong> {selectedBackup.filename}
                </p>
                <p className="text-sm mt-2">
                  <strong>Created:</strong> {formatDate(selectedBackup.created_date)}
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreBackupDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRestoreBackup}
              disabled={operationInProgress}
            >
              Restore Backup
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Kill Query Dialog */}
      <Dialog open={killQueryDialog} onOpenChange={setKillQueryDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Terminate Query</DialogTitle>
            <DialogDescription>
              Are you sure you want to terminate this long-running query?
            </DialogDescription>
          </DialogHeader>
          {selectedConnection && (
            <div className="py-4 space-y-3">
              <div>
                <p className="text-sm text-muted-foreground">Query</p>
                <p className="text-sm font-mono bg-muted p-2 rounded break-all">
                  {selectedConnection.query}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Duration</p>
                  <p className="font-semibold">{selectedConnection.duration_seconds}s</p>
                </div>
                <div>
                  <p className="text-muted-foreground">PID</p>
                  <p className="font-semibold">{selectedConnection.pid}</p>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setKillQueryDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleKillQuery}
              disabled={operationInProgress}
            >
              Terminate Query
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
