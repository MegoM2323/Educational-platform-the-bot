import { useEffect, useState, useCallback, useMemo } from 'react';
import { logger } from '@/utils/logger';
import { adminAPI } from '@/integrations/api/adminAPI';
import { User } from '@/integrations/api/unifiedClient';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { toast } from 'sonner';
import {
  Users,
  Plus,
  Search,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Edit2,
  Trash2,
  Eye,
  Lock,
  Unlock,
  Download,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { EditUserDialog } from '@/components/admin/EditUserDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';

/**
 * User Management Page
 * Comprehensive admin interface for managing all platform users
 *
 * Features:
 * - Advanced filtering by role, status, and date range
 * - Full-text search across email and name
 * - Bulk operations (activate, deactivate, suspend, reset password, delete, assign role)
 * - Sorting by any column
 * - Pagination with configurable page size
 * - User details modal
 * - Export to CSV
 */

interface UserFiltersType {
  search?: string;
  role?: string;
  status?: string;
  joined_date_from?: string;
  joined_date_to?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

interface BulkOperationResult {
  success_count: number;
  failed_count: number;
  failed_ids: number[];
  details: string;
}

export default function UserManagement() {
  // State
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Sorting
  const [sortBy, setSortBy] = useState<string>('date_joined');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Filters
  const [filters, setFilters] = useState({
    search: '',
    role: '',
    status: '',
    joined_date_from: '',
    joined_date_to: '',
  });

  // Selection and bulk operations
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isBulkOperating, setIsBulkOperating] = useState(false);
  const [bulkOperationType, setBulkOperationType] = useState<string | null>(null);
  const [bulkRoleTarget, setBulkRoleTarget] = useState('');

  // Dialogs
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showUserDetailsModal, setShowUserDetailsModal] = useState(false);
  const [editUserDialog, setEditUserDialog] = useState<{
    open: boolean;
    user: User | null;
  }>({ open: false, user: null });
  const [resetPasswordDialog, setResetPasswordDialog] = useState<{
    open: boolean;
    user: User | null;
  }>({ open: false, user: null });
  const [deleteUserDialog, setDeleteUserDialog] = useState<{
    open: boolean;
    user: User | null;
  }>({ open: false, user: null });
  const [bulkConfirmDialog, setBulkConfirmDialog] = useState<{
    open: boolean;
    operation: string;
  }>({ open: false, operation: '' });

  // Load users
  const loadUsers = useCallback(
    async (page: number = 1) => {
      setIsLoading(true);
      try {
        const filterParams: UserFiltersType = {};

        if (filters.search) filterParams.search = filters.search;
        if (filters.role) filterParams.role = filters.role;
        if (filters.status) filterParams.status = filters.status;
        if (filters.joined_date_from) filterParams.joined_date_from = filters.joined_date_from;
        if (filters.joined_date_to) filterParams.joined_date_to = filters.joined_date_to;

        const direction = sortDirection === 'desc' ? '-' : '';
        filterParams.ordering = `${direction}${sortBy}`;
        filterParams.page = page;
        filterParams.page_size = pageSize;

        const response = await adminAPI.getUsers(filterParams);
        if (response.success && response.data) {
          const data = response.data as any;
          setUsers(data.results || []);
          setTotalCount(data.count || 0);
          setCurrentPage(page);
        } else {
          toast.error(response.error || 'Ошибка загрузки списка пользователей');
          setUsers([]);
          setTotalCount(0);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Неизвестная ошибка';
        toast.error(message);
        setUsers([]);
        setTotalCount(0);
      } finally {
        setIsLoading(false);
      }
    },
    [filters, pageSize, sortBy, sortDirection]
  );

  useEffect(() => {
    loadUsers(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadUsers(currentPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, pageSize, sortBy, sortDirection]);

  // Pagination
  const totalPages = Math.ceil(totalCount / pageSize);

  // Selection handling
  const toggleSelectAll = () => {
    if (selectedIds.size === users.length && users.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(users.map(u => u.id)));
    }
  };

  const toggleSelectUser = (userId: number) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(userId)) {
      newSelected.delete(userId);
    } else {
      newSelected.add(userId);
    }
    setSelectedIds(newSelected);
  };

  // Sorting
  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortDirection('asc');
    }
  };

  const getSortIcon = (column: string) => {
    if (sortBy !== column) return null;
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  };

  // Bulk operations
  const handleBulkOperation = async (operation: string) => {
    if (selectedIds.size === 0) {
      toast.error('Выберите пользователей для операции');
      return;
    }

    setBulkOperationType(operation);
    setBulkConfirmDialog({ open: true, operation });
  };

  const executeBulkOperation = async () => {
    if (!bulkOperationType || selectedIds.size === 0) return;

    setIsBulkOperating(true);
    try {
      const userIds = Array.from(selectedIds);
      let result: BulkOperationResult | null = null;

      switch (bulkOperationType) {
        case 'activate':
          result = (await adminAPI.bulkActivateUsers(userIds)).data as BulkOperationResult;
          break;
        case 'deactivate':
          result = (await adminAPI.bulkDeactivateUsers(userIds)).data as BulkOperationResult;
          break;
        case 'suspend':
          result = (await adminAPI.bulkSuspendUsers(userIds)).data as BulkOperationResult;
          break;
        case 'reset_password':
          result = (await adminAPI.bulkResetPasswordUsers(userIds)).data as BulkOperationResult;
          break;
        case 'delete':
          result = (await adminAPI.bulkDeleteUsers(userIds)).data as BulkOperationResult;
          break;
        case 'assign_role':
          if (!bulkRoleTarget) {
            toast.error('Выберите роль');
            return;
          }
          result = (await adminAPI.bulkAssignRoleUsers(userIds, bulkRoleTarget)).data as BulkOperationResult;
          break;
      }

      if (result) {
        toast.success(
          `${result.success_count} пользователей обработано${
            result.failed_count > 0 ? `, ошибок: ${result.failed_count}` : ''
          }`
        );

        setBulkConfirmDialog({ open: false, operation: '' });
        setBulkOperationType(null);
        setBulkRoleTarget('');
        setSelectedIds(new Set());
        await loadUsers(1);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Ошибка при выполнении операции';
      toast.error(message);
    } finally {
      setIsBulkOperating(false);
    }
  };

  // CSV Export
  const exportToCSV = () => {
    const headers = ['ID', 'Email', 'ФИО', 'Роль', 'Статус', 'Дата регистрации', 'Последний вход'];
    const rows = users.map(user => [
      user.id,
      user.email,
      user.full_name,
      getRoleLabel(user.role),
      user.is_active ? 'Активен' : 'Неактивен',
      new Date(user.date_joined).toLocaleDateString('ru-RU'),
      user.last_login ? new Date(user.last_login).toLocaleDateString('ru-RU') : '-',
    ]);

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `users_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  // Filters
  const clearFilters = () => {
    setFilters({
      search: '',
      role: '',
      status: '',
      joined_date_from: '',
      joined_date_to: '',
    });
    setSortBy('date_joined');
    setSortDirection('desc');
    setCurrentPage(1);
  };

  // Helpers
  const getRoleLabel = (role: string) => {
    const labels: Record<string, string> = {
      student: 'Студент',
      teacher: 'Преподаватель',
      tutor: 'Тьютор',
      parent: 'Родитель',
      admin: 'Администратор',
    };
    return labels[role] || role;
  };

  const getStatusBadge = (user: User) => {
    if (!user.is_active) {
      return <Badge variant="secondary">Неактивен</Badge>;
    }
    return <Badge variant="default">Активен</Badge>;
  };

  const statusFilter = useMemo(() => {
    return [
      { value: 'active', label: 'Активные' },
      { value: 'inactive', label: 'Неактивные' },
      { value: 'suspended', label: 'Заблокированные' },
      { value: 'locked', label: 'Заморожены' },
    ];
  }, []);

  const roleFilter = useMemo(() => {
    return [
      { value: 'student', label: 'Студент' },
      { value: 'teacher', label: 'Преподаватель' },
      { value: 'tutor', label: 'Тьютор' },
      { value: 'parent', label: 'Родитель' },
      { value: 'admin', label: 'Администратор' },
    ];
  }, []);

  return (
    <div className="w-full h-full p-6 bg-background">
      <Card className="h-full flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between border-b">
          <div className="flex items-center gap-2">
            <Users className="h-6 w-6" />
            <CardTitle>Управление пользователями</CardTitle>
          </div>
          <Button onClick={exportToCSV} variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Экспорт CSV
          </Button>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col overflow-hidden pt-6">
          {/* Filters Section */}
          <div className="space-y-4 mb-6 pb-6 border-b">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Search */}
              <div>
                <Label className="text-sm">Поиск по Email/ФИО</Label>
                <div className="flex gap-2 mt-2">
                  <Input
                    placeholder="Email, ФИО..."
                    value={filters.search}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    className="flex-1"
                  />
                  <Button type="button" variant="outline" size="icon">
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Role Filter */}
              <div>
                <Label className="text-sm">Роль</Label>
                <select
                  value={filters.role}
                  onChange={(e) => {
                    setFilters({ ...filters, role: e.target.value });
                    setCurrentPage(1);
                  }}
                  className="w-full mt-2 h-10 px-3 border border-input bg-background rounded-md text-sm"
                >
                  <option value="">Все роли</option>
                  {roleFilter.map(role => (
                    <option key={role.value} value={role.value}>
                      {role.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Status Filter */}
              <div>
                <Label className="text-sm">Статус</Label>
                <select
                  value={filters.status}
                  onChange={(e) => {
                    setFilters({ ...filters, status: e.target.value });
                    setCurrentPage(1);
                  }}
                  className="w-full mt-2 h-10 px-3 border border-input bg-background rounded-md text-sm"
                >
                  <option value="">Все статусы</option>
                  {statusFilter.map(status => (
                    <option key={status.value} value={status.value}>
                      {status.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Page Size */}
              <div>
                <Label className="text-sm">Показывать по</Label>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(parseInt(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="w-full mt-2 h-10 px-3 border border-input bg-background rounded-md text-sm"
                >
                  <option value="25">25</option>
                  <option value="50">50</option>
                  <option value="100">100</option>
                </select>
              </div>
            </div>

            {/* Date Range Filter */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label className="text-sm">От (дата регистрации)</Label>
                <Input
                  type="date"
                  value={filters.joined_date_from}
                  onChange={(e) => {
                    setFilters({ ...filters, joined_date_from: e.target.value });
                    setCurrentPage(1);
                  }}
                  className="mt-2"
                />
              </div>

              <div>
                <Label className="text-sm">До (дата регистрации)</Label>
                <Input
                  type="date"
                  value={filters.joined_date_to}
                  onChange={(e) => {
                    setFilters({ ...filters, joined_date_to: e.target.value });
                    setCurrentPage(1);
                  }}
                  className="mt-2"
                />
              </div>

              <div className="flex items-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={clearFilters}
                  className="w-full"
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Сбросить фильтры
                </Button>
              </div>
            </div>
          </div>

          {/* Bulk Operations Bar */}
          {selectedIds.size > 0 && (
            <div className="mb-6 pb-6 border-b flex items-center justify-between bg-muted/50 p-4 rounded-lg">
              <div className="text-sm font-medium">
                Выбрано {selectedIds.size} пользователей
              </div>
              <div className="flex gap-2 flex-wrap">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleBulkOperation('activate')}
                  disabled={isBulkOperating}
                >
                  <CheckCircle2 className="h-4 w-4 mr-1" />
                  Активировать
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleBulkOperation('deactivate')}
                  disabled={isBulkOperating}
                >
                  <AlertCircle className="h-4 w-4 mr-1" />
                  Деактивировать
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleBulkOperation('suspend')}
                  disabled={isBulkOperating}
                >
                  <Lock className="h-4 w-4 mr-1" />
                  Заблокировать
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleBulkOperation('reset_password')}
                  disabled={isBulkOperating}
                >
                  <RotateCcw className="h-4 w-4 mr-1" />
                  Сбросить пароли
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleBulkOperation('delete')}
                  disabled={isBulkOperating}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Удалить
                </Button>
              </div>
            </div>
          )}

          {/* Table */}
          <div className="flex-1 overflow-auto">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-muted/50">
                  <tr className="border-b">
                    <th className="p-3 text-left w-10">
                      <input
                        type="checkbox"
                        checked={selectedIds.size === users.length && users.length > 0}
                        onChange={toggleSelectAll}
                        className="h-4 w-4"
                      />
                    </th>
                    <th
                      className="p-3 text-left cursor-pointer hover:bg-muted"
                      onClick={() => handleSort('id')}
                    >
                      ID{getSortIcon('id')}
                    </th>
                    <th
                      className="p-3 text-left cursor-pointer hover:bg-muted"
                      onClick={() => handleSort('email')}
                    >
                      Email{getSortIcon('email')}
                    </th>
                    <th
                      className="p-3 text-left cursor-pointer hover:bg-muted"
                      onClick={() => handleSort('full_name')}
                    >
                      ФИО{getSortIcon('full_name')}
                    </th>
                    <th
                      className="p-3 text-left cursor-pointer hover:bg-muted"
                      onClick={() => handleSort('role')}
                    >
                      Роль{getSortIcon('role')}
                    </th>
                    <th className="p-3 text-left">Статус</th>
                    <th
                      className="p-3 text-left cursor-pointer hover:bg-muted"
                      onClick={() => handleSort('date_joined')}
                    >
                      Дата регистрации{getSortIcon('date_joined')}
                    </th>
                    <th
                      className="p-3 text-left cursor-pointer hover:bg-muted"
                      onClick={() => handleSort('last_login')}
                    >
                      Последний вход{getSortIcon('last_login')}
                    </th>
                    <th className="p-3 text-left">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan={9} className="p-4 text-center text-muted-foreground">
                        Загрузка...
                      </td>
                    </tr>
                  ) : users.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="p-4 text-center text-muted-foreground">
                        Пользователи не найдены
                      </td>
                    </tr>
                  ) : (
                    users.map(user => (
                      <tr key={user.id} className="border-b hover:bg-muted/50">
                        <td className="p-3">
                          <input
                            type="checkbox"
                            checked={selectedIds.has(user.id)}
                            onChange={() => toggleSelectUser(user.id)}
                            className="h-4 w-4"
                          />
                        </td>
                        <td className="p-3">{user.id}</td>
                        <td className="p-3">{user.email}</td>
                        <td className="p-3">{user.full_name}</td>
                        <td className="p-3">
                          <Badge variant="outline">{getRoleLabel(user.role)}</Badge>
                        </td>
                        <td className="p-3">{getStatusBadge(user)}</td>
                        <td className="p-3">
                          {new Date(user.date_joined).toLocaleDateString('ru-RU')}
                        </td>
                        <td className="p-3">
                          {user.last_login
                            ? new Date(user.last_login).toLocaleDateString('ru-RU')
                            : '-'}
                        </td>
                        <td className="p-3">
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setSelectedUser(user);
                                setShowUserDetailsModal(true);
                              }}
                              title="Просмотр профиля"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                setEditUserDialog({ open: true, user })
                              }
                              title="Редактировать"
                            >
                              <Edit2 className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                setResetPasswordDialog({ open: true, user })
                              }
                              title="Сбросить пароль"
                            >
                              <RotateCcw className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() =>
                                setDeleteUserDialog({ open: true, user })
                              }
                              title="Удалить"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-6 pt-4 border-t">
            <div className="text-sm text-muted-foreground">
              Показано {users?.length || 0} из {totalCount} пользователей
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => loadUsers(currentPage - 1)}
                disabled={currentPage === 1 || isLoading}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="flex items-center gap-2">
                <span className="text-sm">
                  Страница {currentPage} из {totalPages || 1}
                </span>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => loadUsers(currentPage + 1)}
                disabled={currentPage >= totalPages || isLoading}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* User Details Modal */}
      {selectedUser && (
        <Dialog open={showUserDetailsModal} onOpenChange={setShowUserDetailsModal}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Профиль пользователя</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label className="text-xs font-semibold">Email</Label>
                <p className="text-sm">{selectedUser.email}</p>
              </div>
              <div>
                <Label className="text-xs font-semibold">ФИО</Label>
                <p className="text-sm">{selectedUser.full_name}</p>
              </div>
              <div>
                <Label className="text-xs font-semibold">Роль</Label>
                <p className="text-sm">{getRoleLabel(selectedUser.role)}</p>
              </div>
              <div>
                <Label className="text-xs font-semibold">Статус</Label>
                <p className="text-sm">
                  {getStatusBadge(selectedUser)}
                </p>
              </div>
              <div>
                <Label className="text-xs font-semibold">Дата регистрации</Label>
                <p className="text-sm">
                  {new Date(selectedUser.date_joined).toLocaleDateString('ru-RU')}
                </p>
              </div>
              <div>
                <Label className="text-xs font-semibold">Последний вход</Label>
                <p className="text-sm">
                  {selectedUser.last_login
                    ? new Date(selectedUser.last_login).toLocaleDateString('ru-RU')
                    : 'Нет данных'}
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowUserDetailsModal(false)}>
                Закрыть
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Edit User Dialog */}
      {editUserDialog.user && (
        <EditUserDialog
          user={editUserDialog.user}
          profile={{}}
          open={editUserDialog.open}
          onOpenChange={(open) => setEditUserDialog({ open, user: null })}
          onSuccess={() => {
            loadUsers(currentPage);
          }}
        />
      )}

      {/* Reset Password Dialog */}
      {resetPasswordDialog.user && (
        <ResetPasswordDialog
          user={resetPasswordDialog.user}
          open={resetPasswordDialog.open}
          onOpenChange={(open) => setResetPasswordDialog({ open, user: null })}
        />
      )}

      {/* Delete User Dialog */}
      {deleteUserDialog.user && (
        <DeleteUserDialog
          user={deleteUserDialog.user}
          open={deleteUserDialog.open}
          onOpenChange={(open) => setDeleteUserDialog({ open, user: null })}
          onSuccess={() => {
            loadUsers(currentPage);
          }}
        />
      )}

      {/* Bulk Operation Confirmation Dialog */}
      <AlertDialog
        open={bulkConfirmDialog.open}
        onOpenChange={(open) =>
          setBulkConfirmDialog({ ...bulkConfirmDialog, open })
        }
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Подтверждение массовой операции</AlertDialogTitle>
            <AlertDialogDescription>
              {bulkOperationType === 'activate' && (
                <>Вы уверены, что хотите активировать {selectedIds.size} пользователей?</>
              )}
              {bulkOperationType === 'deactivate' && (
                <>Вы уверены, что хотите деактивировать {selectedIds.size} пользователей?</>
              )}
              {bulkOperationType === 'suspend' && (
                <>Вы уверены, что хотите заблокировать {selectedIds.size} пользователей?</>
              )}
              {bulkOperationType === 'reset_password' && (
                <>Вы уверены, что хотите сбросить пароли для {selectedIds.size} пользователей?</>
              )}
              {bulkOperationType === 'delete' && (
                <>
                  Вы уверены, что хотите удалить {selectedIds.size} пользователей? Это действие
                  необратимо!
                </>
              )}
              {bulkOperationType === 'assign_role' && (
                <>
                  <div className="space-y-2">
                    <p>Вы уверены, что хотите назначить роль {selectedIds.size} пользователям?</p>
                    <select
                      value={bulkRoleTarget}
                      onChange={(e) => setBulkRoleTarget(e.target.value)}
                      className="w-full h-10 px-3 border border-input bg-background rounded-md text-sm"
                    >
                      <option value="">-- Выберите роль --</option>
                      {roleFilter.map(role => (
                        <option key={role.value} value={role.value}>
                          {role.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogAction
            onClick={executeBulkOperation}
            disabled={isBulkOperating || (bulkOperationType === 'assign_role' && !bulkRoleTarget)}
          >
            {isBulkOperating ? 'Обработка...' : 'Подтвердить'}
          </AlertDialogAction>
          <AlertDialogCancel disabled={isBulkOperating}>
            Отмена
          </AlertDialogCancel>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
