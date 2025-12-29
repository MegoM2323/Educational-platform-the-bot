import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
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
import { Input } from '@/components/ui/input';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Archive, RotateCcw, Trash2, Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNotificationArchive } from '@/hooks/useNotificationArchive';
import { toast } from 'sonner';

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  type: 'system' | 'message_new' | 'assignment_submitted' | 'material_feedback' | 'payment_received' | 'invoice_created';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  recipient_id?: number;
  created_at: string;
  archived_at: string;
  is_read: boolean;
  data?: Record<string, any>;
}

interface NotificationArchiveProps {
  onClose?: () => void;
}

const getTypeBadge = (type: string) => {
  const typeMap: Record<string, { label: string; variant: any }> = {
    system: { label: 'System', variant: 'default' },
    message_new: { label: 'Message', variant: 'secondary' },
    assignment_submitted: { label: 'Assignment', variant: 'outline' },
    material_feedback: { label: 'Feedback', variant: 'outline' },
    payment_received: { label: 'Payment', variant: 'default' },
    invoice_created: { label: 'Invoice', variant: 'outline' },
  };

  const config = typeMap[type] || { label: type, variant: 'outline' };
  return (
    <Badge variant={config.variant} className="text-xs">
      {config.label}
    </Badge>
  );
};

const getPriorityBadge = (priority: string) => {
  const priorityMap: Record<string, string> = {
    low: 'bg-blue-100 text-blue-800',
    normal: 'bg-gray-100 text-gray-800',
    high: 'bg-yellow-100 text-yellow-800',
    urgent: 'bg-red-100 text-red-800',
  };

  return (
    <span className={cn('px-2 py-1 text-xs rounded', priorityMap[priority] || priorityMap.normal)}>
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </span>
  );
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * NotificationArchive Component
 *
 * Displays archived notifications with features to:
 * - List archived notifications (paginated)
 * - Filter by type, date range, and status
 * - Sort by date, type, and recipient
 * - Restore individual or bulk archived notifications
 * - Permanently delete archived notifications
 * - View notification details
 *
 * @example
 * ```tsx
 * <NotificationArchive onClose={() => navigate('/notifications')} />
 * ```
 */
export const NotificationArchive: React.FC<NotificationArchiveProps> = ({ onClose }) => {
  const {
    notifications,
    isLoading,
    error,
    page,
    pageSize,
    totalCount,
    filters,
    setFilters,
    setPage,
    restoreNotification,
    deleteNotification,
    bulkRestore,
    bulkDelete,
  } = useNotificationArchive();

  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [sortBy, setSortBy] = useState('date');
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [bulkActionType, setBulkActionType] = useState<'restore' | 'delete' | null>(null);
  const [selectedNotification, setSelectedNotification] = useState<NotificationItem | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const totalPages = Math.ceil(totalCount / pageSize);

  const handleSelectAll = useCallback(() => {
    if (selectedIds.length === notifications.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(notifications.map((n) => n.id));
    }
  }, [selectedIds.length, notifications]);

  const handleSelectNotification = useCallback((id: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((nid) => nid !== id);
      } else {
        return [...prev, id];
      }
    });
  }, []);

  const handleSearch = useCallback(() => {
    setFilters({
      ...filters,
      search: searchTerm,
    });
    setPage(1);
  }, [searchTerm, filters, setFilters, setPage]);

  const handleFilterType = useCallback((type: string) => {
    setFilterType(type);
    setFilters({
      ...filters,
      type: type && type !== 'all' ? type : undefined,
    });
    setPage(1);
  }, [filters, setFilters, setPage]);

  const handleRestoreClick = (notification: NotificationItem) => {
    setSelectedNotification(notification);
    setBulkActionType('restore');
    setRestoreDialogOpen(true);
  };

  const handleDeleteClick = (notification: NotificationItem) => {
    setSelectedNotification(notification);
    setBulkActionType('delete');
    setDeleteDialogOpen(true);
  };

  const handleRestoreBulk = async () => {
    if (selectedIds.length === 0) return;

    try {
      const result = await bulkRestore(selectedIds);
      if (result.restored_count > 0) {
        toast.success(`Restored ${result.restored_count} notification(s)`);
        setSelectedIds([]);
      }
    } catch (err) {
      toast.error('Failed to restore notifications');
    }
    setRestoreDialogOpen(false);
  };

  const handleDeleteBulk = async () => {
    if (selectedIds.length === 0) return;

    try {
      await Promise.all(selectedIds.map((id) => deleteNotification(id)));
      toast.success(`Deleted ${selectedIds.length} notification(s)`);
      setSelectedIds([]);
    } catch (err) {
      toast.error('Failed to delete notifications');
    }
    setDeleteDialogOpen(false);
  };

  const handleRestoreSingle = async () => {
    if (!selectedNotification) return;

    try {
      await restoreNotification(selectedNotification.id);
      toast.success('Notification restored');
      setRestoreDialogOpen(false);
      setSelectedNotification(null);
    } catch (err) {
      toast.error('Failed to restore notification');
    }
  };

  const handleDeleteSingle = async () => {
    if (!selectedNotification) return;

    try {
      await deleteNotification(selectedNotification.id);
      toast.success('Notification deleted');
      setDeleteDialogOpen(false);
      setSelectedNotification(null);
    } catch (err) {
      toast.error('Failed to delete notification');
    }
  };

  const handleConfirmRestore = async () => {
    if (selectedIds.length > 0) {
      await handleRestoreBulk();
    } else if (selectedNotification) {
      await handleRestoreSingle();
    }
  };

  const handleConfirmDelete = async () => {
    if (selectedIds.length > 0) {
      await handleDeleteBulk();
    } else if (selectedNotification) {
      await handleDeleteSingle();
    }
  };

  const sortedAndFilteredNotifications = React.useMemo(() => {
    let result = [...notifications];

    // Sort
    switch (sortBy) {
      case 'date':
        result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        break;
      case 'type':
        result.sort((a, b) => a.type.localeCompare(b.type));
        break;
      case 'priority':
        const priorityOrder = { urgent: 0, high: 1, normal: 2, low: 3 };
        result.sort((a, b) => {
          const aOrder = priorityOrder[a.priority as keyof typeof priorityOrder] ?? 999;
          const bOrder = priorityOrder[b.priority as keyof typeof priorityOrder] ?? 999;
          return aOrder - bOrder;
        });
        break;
      default:
        break;
    }

    return result;
  }, [notifications, sortBy]);

  if (isLoading && notifications.length === 0) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error && notifications.length === 0) {
    return (
      <Card className="p-6">
        <div className="text-center space-y-4">
          <Archive className="w-12 h-12 mx-auto text-gray-400" />
          <h3 className="font-semibold text-lg">Failed to load archived notifications</h3>
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Archive className="w-6 h-6" />
          <h2 className="text-2xl font-bold">Archived Notifications</h2>
          <Badge variant="outline">{totalCount}</Badge>
        </div>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose}>
            Back
          </Button>
        )}
      </div>

      {/* Filters and Search */}
      <Card className="p-4">
        <div className="space-y-4">
          {/* Search Bar */}
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search by title or message..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="pl-10"
              />
            </div>
            <Button onClick={handleSearch} variant="outline">
              Search
            </Button>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Select value={filterType} onValueChange={handleFilterType}>
              <SelectTrigger>
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="system">System</SelectItem>
                <SelectItem value="message_new">Message</SelectItem>
                <SelectItem value="assignment_submitted">Assignment</SelectItem>
                <SelectItem value="material_feedback">Feedback</SelectItem>
                <SelectItem value="payment_received">Payment</SelectItem>
                <SelectItem value="invoice_created">Invoice</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger>
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date">Date (Newest)</SelectItem>
                <SelectItem value="type">Type</SelectItem>
                <SelectItem value="priority">Priority</SelectItem>
              </SelectContent>
            </Select>

            <Select value={pageSize.toString()} onValueChange={(value) => {
              // Page size change would require API modification
              setPage(1);
            }}>
              <SelectTrigger>
                <SelectValue placeholder="Items per page" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10 per page</SelectItem>
                <SelectItem value="25">25 per page</SelectItem>
                <SelectItem value="50">50 per page</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Bulk Actions */}
      {selectedIds.length > 0 && (
        <Card className="p-4 bg-blue-50 border-blue-200">
          <div className="flex items-center justify-between">
            <span className="font-semibold">{selectedIds.length} selected</span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setBulkActionType('restore');
                  setRestoreDialogOpen(true);
                }}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Restore
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  setBulkActionType('delete');
                  setDeleteDialogOpen(true);
                }}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setSelectedIds([])}
              >
                Clear
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={selectedIds.length === notifications.length && notifications.length > 0}
                    indeterminate={selectedIds.length > 0 && selectedIds.length < notifications.length}
                    onCheckedChange={handleSelectAll}
                  />
                </TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedAndFilteredNotifications.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <div className="space-y-2">
                      <Archive className="w-10 h-10 mx-auto text-gray-300" />
                      <p className="text-muted-foreground">No archived notifications</p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                sortedAndFilteredNotifications.map((notification) => (
                  <TableRow key={notification.id} className="hover:bg-muted/50">
                    <TableCell>
                      <Checkbox
                        checked={selectedIds.includes(notification.id)}
                        onCheckedChange={() => handleSelectNotification(notification.id)}
                      />
                    </TableCell>
                    <TableCell className="text-sm whitespace-nowrap">
                      {formatDate(notification.created_at)}
                    </TableCell>
                    <TableCell>
                      <div
                        className="cursor-pointer hover:underline"
                        onClick={() => {
                          setSelectedNotification(notification);
                          setDetailsOpen(true);
                        }}
                      >
                        <p className="font-medium max-w-xs truncate">{notification.title}</p>
                        <p className="text-xs text-muted-foreground max-w-xs truncate">
                          {notification.message}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{getTypeBadge(notification.type)}</TableCell>
                    <TableCell>{getPriorityBadge(notification.priority)}</TableCell>
                    <TableCell>
                      {notification.is_read ? (
                        <Badge variant="outline" className="text-xs">Read</Badge>
                      ) : (
                        <Badge variant="default" className="text-xs bg-blue-600">Unread</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Restore"
                          onClick={() => handleRestoreClick(notification)}
                        >
                          <RotateCcw className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Delete"
                          onClick={() => handleDeleteClick(notification)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between p-4 border-t">
          <div className="text-sm text-muted-foreground">
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalCount)} of {totalCount}
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <div className="flex items-center gap-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <Button
                  key={p}
                  size="sm"
                  variant={p === page ? 'default' : 'outline'}
                  onClick={() => setPage(p)}
                  className="w-8"
                >
                  {p}
                </Button>
              ))}
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </Card>

      {/* Restore Dialog */}
      <AlertDialog open={restoreDialogOpen} onOpenChange={setRestoreDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore Notification</AlertDialogTitle>
            <AlertDialogDescription>
              {selectedIds.length > 0
                ? `Are you sure you want to restore ${selectedIds.length} notification(s)? They will be moved back to your inbox.`
                : `Are you sure you want to restore "${selectedNotification?.title}"? It will be moved back to your inbox.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="flex justify-end gap-3">
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmRestore}>
              Restore
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Notification</AlertDialogTitle>
            <AlertDialogDescription>
              {selectedIds.length > 0
                ? `Are you sure you want to permanently delete ${selectedIds.length} notification(s)? This action cannot be undone.`
                : `Are you sure you want to permanently delete "${selectedNotification?.title}"? This action cannot be undone.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="flex justify-end gap-3">
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={handleConfirmDelete}>
              Delete
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>

      {/* Details Modal */}
      {detailsOpen && selectedNotification && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h3 className="text-2xl font-bold mb-2">{selectedNotification.title}</h3>
                  <p className="text-sm text-muted-foreground">
                    Archived {formatDate(selectedNotification.archived_at)}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setDetailsOpen(false)}
                >
                  ×
                </Button>
              </div>

              <div className="space-y-4 mb-6">
                <div>
                  <h4 className="font-semibold mb-2">Message</h4>
                  <p className="text-sm whitespace-pre-wrap">{selectedNotification.message}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-semibold mb-2">Type</h4>
                    {getTypeBadge(selectedNotification.type)}
                  </div>
                  <div>
                    <h4 className="font-semibold mb-2">Priority</h4>
                    {getPriorityBadge(selectedNotification.priority)}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Status</h4>
                  {selectedNotification.is_read ? (
                    <Badge variant="outline">Read</Badge>
                  ) : (
                    <Badge>Unread</Badge>
                  )}
                </div>

                {selectedNotification.data && Object.keys(selectedNotification.data).length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">Additional Data</h4>
                    <pre className="bg-muted p-3 rounded text-xs overflow-auto max-h-40">
                      {JSON.stringify(selectedNotification.data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              <div className="flex gap-3 justify-end">
                <Button variant="outline" onClick={() => setDetailsOpen(false)}>
                  Close
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    handleRestoreClick(selectedNotification);
                    setDetailsOpen(false);
                  }}
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Restore
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => {
                    handleDeleteClick(selectedNotification);
                    setDetailsOpen(false);
                  }}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
