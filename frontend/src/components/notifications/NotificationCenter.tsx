import React, { useState, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import {
  Trash2,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Mail,
  AlertCircle,
  CheckCircle2,
  MessageSquare,
  FileText,
  DollarSign,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNotificationCenter, type Notification } from '@/hooks/useNotificationCenter';
import { toast } from 'sonner';

interface NotificationCenterProps {
  onClose?: () => void;
}

const getTypeIcon = (type: string) => {
  const iconMap: Record<string, React.ReactNode> = {
    system: <AlertCircle className="w-4 h-4" />,
    message_new: <Mail className="w-4 h-4" />,
    assignment_submitted: <FileText className="w-4 h-4" />,
    material_feedback: <MessageSquare className="w-4 h-4" />,
    payment_received: <DollarSign className="w-4 h-4" />,
    invoice_created: <FileText className="w-4 h-4" />,
  };

  return iconMap[type] || <AlertCircle className="w-4 h-4" />;
};

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

const getPriorityColor = (priority: string) => {
  const priorityMap: Record<string, string> = {
    low: 'bg-blue-100 text-blue-800',
    normal: 'bg-gray-100 text-gray-800',
    high: 'bg-yellow-100 text-yellow-800',
    urgent: 'bg-red-100 text-red-800',
  };

  return priorityMap[priority] || priorityMap.normal;
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) {
    return 'Just now';
  } else if (diffMins < 60) {
    return `${diffMins}m ago`;
  } else if (diffHours < 24) {
    return `${diffHours}h ago`;
  } else if (diffDays < 7) {
    return `${diffDays}d ago`;
  } else {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
};

/**
 * NotificationCenter Component
 *
 * Main notification management interface displaying:
 * - List of active notifications
 * - Filtering by type and priority
 * - Search functionality
 * - Mark as read/unread
 * - Delete notifications
 * - Infinite scroll pagination
 * - Real-time WebSocket updates
 *
 * @example
 * ```tsx
 * <NotificationCenter onClose={() => navigate('/dashboard')} />
 * ```
 */
export const NotificationCenter: React.FC<NotificationCenterProps> = ({ onClose }) => {
  const {
    notifications,
    isLoading,
    error,
    page,
    setPage,
    pageSize,
    totalCount,
    unreadCount,
    filters,
    setFilters,
    markAsRead,
    markMultipleAsRead,
    deleteNotification,
    deleteMultiple,
  } = useNotificationCenter();

  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [filterReadStatus, setFilterReadStatus] = useState<string>('all');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const totalPages = Math.ceil(totalCount / pageSize);
  const hasMore = page < totalPages;

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
      search: searchTerm || undefined,
    });
    setPage(1);
  }, [searchTerm, filters, setFilters, setPage]);

  const handleFilterType = useCallback(
    (type: string) => {
      setFilterType(type);
      setFilters({
        ...filters,
        type: type && type !== 'all' ? type : undefined,
      });
      setPage(1);
    },
    [filters, setFilters, setPage]
  );

  const handleFilterPriority = useCallback(
    (priority: string) => {
      setFilterPriority(priority);
      setFilters({
        ...filters,
        priority: priority && priority !== 'all' ? priority : undefined,
      });
      setPage(1);
    },
    [filters, setFilters, setPage]
  );

  const handleFilterReadStatus = useCallback(
    (status: string) => {
      setFilterReadStatus(status);
      if (status === 'all' || status === '') {
        const newFilters = { ...filters };
        delete newFilters.is_read;
        setFilters(newFilters);
      } else {
        setFilters({
          ...filters,
          is_read: status === 'unread',
        });
      }
      setPage(1);
    },
    [filters, setFilters, setPage]
  );

  const handleDeleteClick = (notification: Notification) => {
    setSelectedNotification(notification);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (selectedIds.length > 0) {
      await handleDeleteBulk();
    } else if (selectedNotification) {
      await handleDeleteSingle();
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

  const handleDeleteBulk = async () => {
    if (selectedIds.length === 0) return;

    try {
      await deleteMultiple(selectedIds);
      toast.success(`Deleted ${selectedIds.length} notification(s)`);
      setSelectedIds([]);
    } catch (err) {
      toast.error('Failed to delete notifications');
    }
    setDeleteDialogOpen(false);
  };

  const handleMarkAsRead = async (notificationId: number) => {
    try {
      await markAsRead(notificationId);
      toast.success('Marked as read');
    } catch (err) {
      toast.error('Failed to mark as read');
    }
  };

  const handleMarkMultipleAsRead = async () => {
    if (selectedIds.length === 0) return;

    try {
      await markMultipleAsRead(selectedIds);
      toast.success(`Marked ${selectedIds.length} notification(s) as read`);
      setSelectedIds([]);
    } catch (err) {
      toast.error('Failed to mark notifications as read');
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await markMultipleAsRead([], true);
      toast.success('All notifications marked as read');
    } catch (err) {
      toast.error('Failed to mark all as read');
    }
  };

  const notificationTypes = useMemo(
    () => ['system', 'message_new', 'assignment_submitted', 'material_feedback', 'payment_received', 'invoice_created'],
    []
  );

  const priorityOptions = useMemo(() => ['low', 'normal', 'high', 'urgent'], []);

  return (
    <div className="w-full max-w-6xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Notification Center</h1>
          <p className="text-sm text-gray-600 mt-1">
            {totalCount} notification{totalCount !== 1 ? 's' : ''} ({unreadCount} unread)
          </p>
        </div>
        {onClose && (
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        )}
      </div>

      {/* Action Bar */}
      {selectedIds.length > 0 && (
        <Card className="p-4 bg-blue-50 border-blue-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-blue-900">
              {selectedIds.length} notification{selectedIds.length !== 1 ? 's' : ''} selected
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={handleMarkMultipleAsRead}>
                Mark as Read
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => setDeleteDialogOpen(true)}
              >
                Delete
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Filters */}
      <Card className="p-4 space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">Search</label>
          <div className="flex gap-2">
            <Input
              placeholder="Search notifications..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1"
            />
            <Button onClick={handleSearch} variant="outline">
              <Search className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Filter by Type */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Type</label>
            <Select value={filterType} onValueChange={handleFilterType}>
              <SelectTrigger>
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                {notificationTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type.replace(/_/g, ' ')}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Filter by Priority */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Priority</label>
            <Select value={filterPriority} onValueChange={handleFilterPriority}>
              <SelectTrigger>
                <SelectValue placeholder="All priorities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All priorities</SelectItem>
                {priorityOptions.map((priority) => (
                  <SelectItem key={priority} value={priority}>
                    {priority.charAt(0).toUpperCase() + priority.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Filter by Read Status */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Status</label>
            <Select value={filterReadStatus} onValueChange={handleFilterReadStatus}>
              <SelectTrigger>
                <SelectValue placeholder="All notifications" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All notifications</SelectItem>
                <SelectItem value="unread">Unread only</SelectItem>
                <SelectItem value="read">Read only</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Mark all as read button */}
        {unreadCount > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleMarkAllAsRead}
            className="w-full"
          >
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Mark all as read
          </Button>
        )}
      </Card>

      {/* Notifications List */}
      <div className="space-y-3">
        {isLoading && notifications.length === 0 ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <Card key={i} className="p-4">
                <Skeleton className="h-6 w-full mb-2" />
                <Skeleton className="h-4 w-3/4" />
              </Card>
            ))}
          </div>
        ) : error ? (
          <Card className="p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <p className="text-gray-700 font-medium">Failed to load notifications</p>
            <p className="text-gray-600 text-sm">{error}</p>
          </Card>
        ) : notifications.length === 0 ? (
          <Card className="p-8 text-center">
            <Mail className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-700 font-medium">No notifications</p>
            <p className="text-gray-600 text-sm">You're all caught up!</p>
          </Card>
        ) : (
          <>
            {/* Select all checkbox */}
            <div className="flex items-center gap-2 px-2 py-1">
              <Checkbox
                checked={selectedIds.length === notifications.length && notifications.length > 0}
                onCheckedChange={handleSelectAll}
              />
              <span className="text-xs text-gray-600">
                {selectedIds.length === notifications.length && notifications.length > 0
                  ? 'All selected'
                  : 'Select all'}
              </span>
            </div>

            {/* Notification cards */}
            {notifications.map((notification) => (
              <Card
                key={notification.id}
                className={cn(
                  'p-4 cursor-pointer transition-all hover:shadow-md',
                  !notification.is_read && 'bg-blue-50 border-blue-200',
                  selectedIds.includes(notification.id) && 'ring-2 ring-blue-500'
                )}
              >
                <div className="flex gap-4 items-start">
                  {/* Checkbox */}
                  <Checkbox
                    checked={selectedIds.includes(notification.id)}
                    onCheckedChange={() => handleSelectNotification(notification.id)}
                    className="mt-1"
                  />

                  {/* Icon */}
                  <div className="text-gray-600 mt-1">{getTypeIcon(notification.type)}</div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <h3 className="font-semibold text-gray-900 break-words">
                          {notification.title}
                        </h3>
                        <p className="text-sm text-gray-700 break-words mt-1">
                          {notification.message}
                        </p>
                      </div>
                    </div>

                    {/* Metadata */}
                    <div className="flex items-center justify-between mt-3">
                      <div className="flex flex-wrap gap-2">
                        {getTypeBadge(notification.type)}
                        <span
                          className={cn(
                            'px-2 py-1 text-xs rounded',
                            getPriorityColor(notification.priority)
                          )}
                        >
                          {notification.priority.charAt(0).toUpperCase() +
                            notification.priority.slice(1)}
                        </span>
                        {!notification.is_read && (
                          <Badge variant="default" className="text-xs">
                            Unread
                          </Badge>
                        )}
                      </div>

                      <div className="flex items-center gap-2 ml-2">
                        <span className="text-xs text-gray-600 whitespace-nowrap">
                          {formatDate(notification.created_at)}
                        </span>

                        {/* Action buttons */}
                        <div className="flex gap-1">
                          {!notification.is_read && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleMarkAsRead(notification.id)}
                              title="Mark as read"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                          )}

                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDeleteClick(notification)}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => setPage(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="w-4 h-4 mr-2" />
            Previous
          </Button>

          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>

          <Button
            variant="outline"
            onClick={() => setPage(page + 1)}
            disabled={!hasMore}
          >
            Next
            <ChevronRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      )}

      {/* Delete Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Notification{selectedIds.length > 1 ? 's' : ''}</AlertDialogTitle>
            <AlertDialogDescription>
              {selectedIds.length > 0
                ? `Are you sure you want to delete ${selectedIds.length} notification${selectedIds.length !== 1 ? 's' : ''}? This action cannot be undone.`
                : selectedNotification
                ? 'Are you sure you want to delete this notification? This action cannot be undone.'
                : ''}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="flex gap-3 justify-end">
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
