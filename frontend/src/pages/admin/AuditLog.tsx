import { useState, useEffect, useCallback, useMemo } from 'react';
import { logger } from '@/utils/logger';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Search,
  Clock,
  User,
  FileText,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

// Types for audit logs
interface AuditLogEntry {
  id: number;
  timestamp: string;
  user: {
    id: number;
    email: string;
    full_name: string;
  };
  action: 'create' | 'read' | 'update' | 'delete' | 'export' | 'login' | 'logout';
  resource: 'User' | 'Material' | 'Assignment' | 'ChatRoom' | 'Message' | 'Payment' | string;
  status: 'success' | 'failed';
  ip_address: string;
  user_agent?: string;
  duration_ms?: number;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  details?: string;
}

interface PaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditLogEntry[];
}

interface AuditLogFilters {
  user_id?: number;
  action?: string;
  resource?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}

/**
 * Audit Log Viewer Page
 *
 * Displays admin audit logs with filtering, sorting, pagination, and export capabilities.
 * Features:
 * - Table with timestamp, user, action, resource, status, IP address
 * - Filters: user dropdown, action type, resource type, date range, status
 * - Sorting: By timestamp (newest first default)
 * - Pagination: 50 rows per page
 * - Search: Full-text search in details
 * - Expandable rows for full details view
 * - CSV export functionality
 * - Real-time refresh (30-second auto-refresh)
 */
export default function AuditLog() {
  const navigate = useNavigate();
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [filters, setFilters] = useState<AuditLogFilters>({
    user_id: undefined,
    action: undefined,
    resource: undefined,
    status: undefined,
    date_from: undefined,
    date_to: undefined,
    search: '',
  });

  // UI state
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [users, setUsers] = useState<Array<{ id: number; email: string; full_name: string }>>([]);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);

  // Load audit logs
  const loadAuditLogs = useCallback(async (page = 1) => {
    setIsLoading(true);
    setError(null);
    try {
      // Build query parameters
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('page_size', pageSize.toString());
      params.append('ordering', `-timestamp`);

      if (filters.user_id) params.append('user_id', filters.user_id.toString());
      if (filters.action) params.append('action', filters.action);
      if (filters.resource) params.append('resource', filters.resource);
      if (filters.status) params.append('status', filters.status);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);
      if (filters.search) params.append('search', filters.search);

      const response = await fetch(`/api/admin/audit-logs/?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to load audit logs: ${response.statusText}`);
      }

      const data: PaginatedResponse = await response.json();
      setAuditLogs(data.results || []);
      setTotalCount(data.count || 0);
      setCurrentPage(page);
      logger.info('[AuditLog] Loaded logs:', { count: data.results?.length || 0 });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load audit logs';
      setError(errorMsg);
      logger.error('[AuditLog] Load failed:', err);
      toast.error(errorMsg);
    } finally {
      setIsLoading(false);
    }
  }, [filters, pageSize]);

  // Load users for dropdown
  const loadUsers = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/users/?page_size=1000', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to load users');
      }

      const data = await response.json();
      setUsers(data.results || []);
    } catch (err) {
      logger.error('[AuditLog] Failed to load users:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadAuditLogs(1);
    loadUsers();
  }, []);

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefreshEnabled) return;

    const interval = setInterval(() => {
      loadAuditLogs(currentPage);
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [autoRefreshEnabled, currentPage, loadAuditLogs]);

  // Handle filter changes
  const handleFilterChange = (key: keyof AuditLogFilters, value: any) => {
    setFilters((prev) => ({
      ...prev,
      [key]: (value && value !== 'all') ? value : undefined,
    }));
    setCurrentPage(1);
  };

  // Clear all filters
  const handleClearFilters = () => {
    setFilters({
      user_id: undefined,
      action: undefined,
      resource: undefined,
      status: undefined,
      date_from: undefined,
      date_to: undefined,
      search: '',
    });
    setCurrentPage(1);
  };

  // Toggle row expansion
  const toggleRowExpansion = (id: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  // Open details modal
  const openDetailsModal = (log: AuditLogEntry) => {
    setSelectedLog(log);
    setShowDetailsModal(true);
  };

  // Export to CSV
  const handleExportCSV = async () => {
    setIsExporting(true);
    try {
      // Build query parameters for export
      const params = new URLSearchParams();
      params.append('page_size', '10000'); // Get up to 10k records

      if (filters.user_id) params.append('user_id', filters.user_id.toString());
      if (filters.action) params.append('action', filters.action);
      if (filters.resource) params.append('resource', filters.resource);
      if (filters.status) params.append('status', filters.status);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);
      params.append('format', 'csv');

      const response = await fetch(`/api/admin/audit-logs/?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Accept': 'text/csv',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to export data');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Audit logs exported successfully');
      logger.info('[AuditLog] Exported to CSV');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Export failed';
      logger.error('[AuditLog] Export failed:', err);
      toast.error(errorMsg);
    } finally {
      setIsExporting(false);
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string): string => {
    return new Date(timestamp).toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // Get action badge color
  const getActionColor = (action: string): string => {
    const colors: Record<string, string> = {
      create: 'bg-green-100 text-green-800',
      read: 'bg-blue-100 text-blue-800',
      update: 'bg-yellow-100 text-yellow-800',
      delete: 'bg-red-100 text-red-800',
      export: 'bg-purple-100 text-purple-800',
      login: 'bg-cyan-100 text-cyan-800',
      logout: 'bg-gray-100 text-gray-800',
    };
    return colors[action] || 'bg-gray-100 text-gray-800';
  };

  // Get status badge
  const getStatusBadge = (status: string) => {
    if (status === 'success') {
      return <Badge className="bg-green-600">Success</Badge>;
    }
    return <Badge variant="destructive">Failed</Badge>;
  };

  // Pagination calculations
  const totalPages = Math.ceil(totalCount / pageSize);
  const startIndex = (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, totalCount);

  // Check if there are active filters
  const hasActiveFilters = useMemo(() => {
    return Object.values(filters).some((v) => v !== undefined && v !== '');
  }, [filters]);

  if (!auditLogs && isLoading) {
    return (
      <div className="container mx-auto p-4">
        <Card>
          <CardContent className="flex items-center justify-center py-10">
            <div className="flex flex-col items-center gap-2">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              <p className="text-muted-foreground">Loading audit logs...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Audit Logs</h1>
          <p className="text-muted-foreground mt-1">View system audit trail and admin actions</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadAuditLogs(currentPage)}
            disabled={isLoading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            disabled={isExporting || auditLogs.length === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Filter Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* User Filter */}
            <div className="space-y-2">
              <Label>User</Label>
              <Select
                value={filters.user_id?.toString() || 'all'}
                onValueChange={(value) =>
                  handleFilterChange('user_id', value !== 'all' && value ? parseInt(value) : undefined)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="All users" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All users</SelectItem>
                  {users.map((user) => (
                    <SelectItem key={user.id} value={user.id.toString()}>
                      {user.full_name || user.email}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Action Filter */}
            <div className="space-y-2">
              <Label>Action</Label>
              <Select
                value={filters.action || 'all'}
                onValueChange={(value) => handleFilterChange('action', value || undefined)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All actions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All actions</SelectItem>
                  <SelectItem value="create">Create</SelectItem>
                  <SelectItem value="read">Read</SelectItem>
                  <SelectItem value="update">Update</SelectItem>
                  <SelectItem value="delete">Delete</SelectItem>
                  <SelectItem value="export">Export</SelectItem>
                  <SelectItem value="login">Login</SelectItem>
                  <SelectItem value="logout">Logout</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Resource Filter */}
            <div className="space-y-2">
              <Label>Resource</Label>
              <Select
                value={filters.resource || 'all'}
                onValueChange={(value) => handleFilterChange('resource', value || undefined)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All resources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All resources</SelectItem>
                  <SelectItem value="User">User</SelectItem>
                  <SelectItem value="Material">Material</SelectItem>
                  <SelectItem value="Assignment">Assignment</SelectItem>
                  <SelectItem value="ChatRoom">ChatRoom</SelectItem>
                  <SelectItem value="Message">Message</SelectItem>
                  <SelectItem value="Payment">Payment</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Status Filter */}
            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={filters.status || 'all'}
                onValueChange={(value) => handleFilterChange('status', value || undefined)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Date From */}
            <div className="space-y-2">
              <Label>Date From</Label>
              <Input
                type="date"
                value={filters.date_from || ''}
                onChange={(e) => handleFilterChange('date_from', e.target.value || undefined)}
              />
            </div>

            {/* Date To */}
            <div className="space-y-2">
              <Label>Date To</Label>
              <Input
                type="date"
                value={filters.date_to || ''}
                onChange={(e) => handleFilterChange('date_to', e.target.value || undefined)}
              />
            </div>
          </div>

          {/* Search and Actions */}
          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <Label>Search Details</Label>
              <Input
                placeholder="Search in details..."
                value={filters.search || ''}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                className="mt-2"
              />
            </div>
            {hasActiveFilters && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearFilters}
              >
                Clear Filters
              </Button>
            )}
          </div>

          {/* Auto-refresh toggle */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="autoRefresh"
              checked={autoRefreshEnabled}
              onChange={(e) => setAutoRefreshEnabled(e.target.checked)}
              className="h-4 w-4"
            />
            <Label htmlFor="autoRefresh" className="cursor-pointer">
              Auto-refresh every 30 seconds
            </Label>
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-600">{error}</p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => loadAuditLogs(currentPage)}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Results Info */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {totalCount === 0
            ? 'No audit logs found'
            : `Showing ${startIndex} to ${endIndex} of ${totalCount} results`}
        </span>
      </div>

      {/* Table */}
      {auditLogs.length > 0 ? (
        <Card>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8"></TableHead>
                  <TableHead className="w-32">Timestamp</TableHead>
                  <TableHead className="w-40">User</TableHead>
                  <TableHead className="w-24">Action</TableHead>
                  <TableHead className="w-24">Resource</TableHead>
                  <TableHead className="w-20">Status</TableHead>
                  <TableHead className="w-32">IP Address</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.map((log) => (
                  <Collapsible key={log.id} asChild>
                    <>
                      <TableRow>
                        <TableCell>
                          <CollapsibleTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                            >
                              {expandedRows.has(log.id) ? (
                                <ChevronUp className="h-4 w-4" />
                              ) : (
                                <ChevronDown className="h-4 w-4" />
                              )}
                            </Button>
                          </CollapsibleTrigger>
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {formatTimestamp(log.timestamp)}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            <span className="font-medium">{log.user.full_name}</span>
                            <span className="text-xs text-muted-foreground">{log.user.email}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getActionColor(log.action)}>
                            {log.action}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{log.resource}</Badge>
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(log.status)}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          <Tooltip title="Click for more details">
                            <span className="cursor-help text-blue-600">
                              {log.ip_address}
                            </span>
                          </Tooltip>
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <p className="truncate text-sm text-muted-foreground">
                            {log.details || '-'}
                          </p>
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell colSpan={8} className="p-0">
                          <CollapsibleContent asChild>
                            <div className="bg-muted/50 p-4">
                              <DetailsPanel log={log} onOpenModal={() => openDetailsModal(log)} />
                            </div>
                          </CollapsibleContent>
                        </TableCell>
                      </TableRow>
                    </>
                  </Collapsible>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mb-3" />
            <p className="text-lg font-medium text-muted-foreground">No audit logs found</p>
            {hasActiveFilters && (
              <Button
                variant="link"
                onClick={handleClearFilters}
                className="mt-2"
              >
                Clear filters and try again
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadAuditLogs(currentPage - 1)}
              disabled={currentPage === 1 || isLoading}
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadAuditLogs(currentPage + 1)}
              disabled={currentPage === totalPages || isLoading}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        </div>
      )}

      {/* Details Modal */}
      <DetailsModal
        log={selectedLog}
        open={showDetailsModal}
        onOpenChange={setShowDetailsModal}
      />
    </div>
  );
}

/**
 * Details Panel for expanded rows
 */
interface DetailsPanelProps {
  log: AuditLogEntry;
  onOpenModal: () => void;
}

function DetailsPanel({ log, onOpenModal }: DetailsPanelProps) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">IP Address</p>
          <p className="font-mono text-sm">{log.ip_address}</p>
        </div>
        {log.duration_ms !== undefined && (
          <div>
            <p className="text-sm font-medium text-muted-foreground">Duration</p>
            <p className="font-mono text-sm">{log.duration_ms}ms</p>
          </div>
        )}
      </div>

      {log.user_agent && (
        <div>
          <p className="text-sm font-medium text-muted-foreground">User Agent</p>
          <p className="text-xs text-muted-foreground break-words">{log.user_agent}</p>
        </div>
      )}

      {(log.old_values || log.new_values) && (
        <div>
          <Button variant="link" size="sm" onClick={onOpenModal} className="p-0">
            View full details (JSON) →
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * Details Modal for full JSON view
 */
interface DetailsModalProps {
  log: AuditLogEntry | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function DetailsModal({ log, open, onOpenChange }: DetailsModalProps) {
  if (!log) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Audit Log Details</DialogTitle>
          <DialogDescription>
            Full details for {log.action} action on {log.resource}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Timestamp</p>
              <p className="text-sm">{new Date(log.timestamp).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">User</p>
              <p className="text-sm">{log.user.full_name} ({log.user.email})</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Action</p>
              <p className="text-sm">{log.action}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Resource</p>
              <p className="text-sm">{log.resource}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Status</p>
              <p className="text-sm">{log.status}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">IP Address</p>
              <p className="text-sm font-mono">{log.ip_address}</p>
            </div>
          </div>

          {/* User Agent */}
          {log.user_agent && (
            <div>
              <p className="text-sm font-medium text-muted-foreground">User Agent</p>
              <p className="text-xs text-muted-foreground break-words">{log.user_agent}</p>
            </div>
          )}

          {/* Duration */}
          {log.duration_ms !== undefined && (
            <div>
              <p className="text-sm font-medium text-muted-foreground">Duration</p>
              <p className="text-sm font-mono">{log.duration_ms}ms</p>
            </div>
          )}

          {/* Old Values */}
          {log.old_values && Object.keys(log.old_values).length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Old Values</p>
              <pre className="bg-muted p-3 rounded text-xs overflow-x-auto">
                {JSON.stringify(log.old_values, null, 2)}
              </pre>
            </div>
          )}

          {/* New Values */}
          {log.new_values && Object.keys(log.new_values).length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">New Values</p>
              <pre className="bg-muted p-3 rounded text-xs overflow-x-auto">
                {JSON.stringify(log.new_values, null, 2)}
              </pre>
            </div>
          )}

          {/* Details */}
          {log.details && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Details</p>
              <p className="text-sm text-muted-foreground">{log.details}</p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Simple Tooltip component
 */
interface TooltipProps {
  title: string;
  children: React.ReactNode;
}

function Tooltip({ title, children }: TooltipProps) {
  const [showTooltip, setShowTooltip] = React.useState(false);

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {children}
      </div>
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs text-white bg-black rounded whitespace-nowrap z-10">
          {title}
        </div>
      )}
    </div>
  );
}
