import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { unifiedAPI, User } from '@/integrations/api/unifiedClient';
import { adminAPI } from '@/integrations/api/adminAPI';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { EditUserDialog } from '@/components/admin/EditUserDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';
import { CreateParentDialog } from '@/components/admin/CreateParentDialog';
import { ParentStudentAssignment } from '@/components/admin/ParentStudentAssignment';
import { User as UserIcon, Key, Trash2, Plus, LogOut, RotateCcw, Link2, Search, ChevronLeft, ChevronRight } from 'lucide-react';

interface ParentItem {
  id: number;
  user: User;
  children_count?: number;
}

interface ParentManagementProps {
  embedded?: boolean;
}

export default function ParentManagement({ embedded = false }: ParentManagementProps) {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [parents, setParents] = useState<ParentItem[]>([]);
  const [filteredParents, setFilteredParents] = useState<ParentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLogoutLoading, setIsLogoutLoading] = useState(false);
  const [createDialog, setCreateDialog] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [editUserDialog, setEditUserDialog] = useState<{
    open: boolean;
    item: ParentItem | null;
  }>({ open: false, item: null });
  const [resetPasswordDialog, setResetPasswordDialog] = useState<{
    open: boolean;
    item: ParentItem | null;
  }>({ open: false, item: null });
  const [deleteUserDialog, setDeleteUserDialog] = useState<{
    open: boolean;
    item: ParentItem | null;
  }>({ open: false, item: null });
  const [reactivateDialog, setReactivateDialog] = useState<{
    open: boolean;
    item: ParentItem | null;
    isLoading: boolean;
  }>({ open: false, item: null, isLoading: false });
  const [assignmentDialog, setAssignmentDialog] = useState(false);

  const loadParents = async () => {
    setIsLoading(true);
    try {
      // Используем endpoint для получения списка родителей с children_count
      const response = await adminAPI.listParents();
      if (response.success && response.data) {
        const parentsList = response.data.results || [];
        setParents(parentsList);
        setFilteredParents(parentsList);
      } else {
        toast.error(response.error || 'Ошибка загрузки списка родителей');
      }
    } catch (e: any) {
      toast.error(e?.message || 'Ошибка загрузки списка');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadParents();
  }, []);

  // Filter parents by search term
  useEffect(() => {
    if (!searchTerm) {
      setFilteredParents(parents);
      setCurrentPage(1);
      return;
    }

    const lowercaseSearch = searchTerm.toLowerCase();
    const filtered = parents.filter((parent) => {
      const fullName = parent.user.full_name?.toLowerCase() || '';
      const email = parent.user.email?.toLowerCase() || '';
      return fullName.includes(lowercaseSearch) || email.includes(lowercaseSearch);
    });
    setFilteredParents(filtered);
    setCurrentPage(1);
  }, [searchTerm, parents]);

  const handleLogout = async () => {
    setIsLogoutLoading(true);
    try {
      await logout();
      toast.success('Вы вышли из системы');
      navigate('/auth');
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Ошибка при выходе');
    } finally {
      setIsLogoutLoading(false);
    }
  };

  const handleReactivate = async () => {
    if (!reactivateDialog.item) return;

    setReactivateDialog((prev) => ({ ...prev, isLoading: true }));
    try {
      const response = await adminAPI.reactivateUser(reactivateDialog.item.user.id);
      if (response.success) {
        toast.success('Родитель успешно активирован');
        setReactivateDialog({ open: false, item: null, isLoading: false });
        await loadParents();
      } else {
        toast.error(response.error || 'Ошибка при активации');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Неизвестная ошибка';
      toast.error(message);
    } finally {
      setReactivateDialog((prev) => ({ ...prev, isLoading: false }));
    }
  };

  // Pagination calculations
  const totalPages = Math.ceil(filteredParents.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedParents = filteredParents.slice(startIndex, endIndex);

  const cardContent = (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Управление родителями</CardTitle>
        <div className="flex gap-2">
          <Button onClick={() => setCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Создать родителя
          </Button>
          <Button
            variant="outline"
            onClick={() => setAssignmentDialog(true)}
          >
            <Link2 className="h-4 w-4 mr-2" />
            Назначить студентов
          </Button>
          {!embedded && (
            <Button
              variant="destructive"
              onClick={handleLogout}
              disabled={isLogoutLoading}
            >
              <LogOut className="h-4 w-4 mr-2" />
              {isLogoutLoading ? 'Выход...' : 'Выйти'}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Поиск и фильтры */}
        <div className="mb-6 space-y-4">
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <Label className="text-sm">Поиск</Label>
              <div className="flex gap-2 mt-2">
                <Input
                  placeholder="ФИО или email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1"
                />
                <Button variant="outline" size="icon">
                  <Search className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div>
              <Label className="text-sm">Показывать по</Label>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(parseInt(e.target.value));
                  setCurrentPage(1);
                }}
                className="w-[120px] mt-2 h-10 px-3 border border-input bg-background rounded-md text-sm"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
          </div>
        </div>

        {/* Таблица */}
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="py-2 pr-4">ФИО</th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Телефон</th>
                <th className="py-2 pr-4">Количество детей</th>
                <th className="py-2 pr-4">Дата регистрации</th>
                <th className="py-2 pr-4">Действия</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td className="py-4" colSpan={6}>
                    Загрузка...
                  </td>
                </tr>
              ) : paginatedParents.length === 0 ? (
                <tr>
                  <td className="py-4" colSpan={6}>
                    {searchTerm ? 'Родители не найдены по запросу' : 'Родители не найдены'}
                  </td>
                </tr>
              ) : (
                paginatedParents.map((parent) => (
                  <tr key={parent.id} className="border-b">
                    <td className="py-2 pr-4">{parent.user.full_name}</td>
                    <td className="py-2 pr-4">{parent.user.email}</td>
                    <td className="py-2 pr-4">{parent.user.phone || '-'}</td>
                    <td className="py-2 pr-4">{parent.children_count || 0}</td>
                    <td className="py-2 pr-4">
                      {new Date(parent.user.date_joined).toLocaleDateString('ru-RU')}
                    </td>
                    <td className="py-2 pr-4">
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setEditUserDialog({ open: true, item: parent })}
                          title="Редактировать пользователя"
                        >
                          <UserIcon className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setResetPasswordDialog({ open: true, item: parent })}
                          title="Сбросить пароль"
                        >
                          <Key className="h-4 w-4" />
                        </Button>
                        {!parent.user.is_active && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setReactivateDialog({ open: true, item: parent, isLoading: false })}
                            title="Активировать родителя"
                          >
                            <RotateCcw className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => setDeleteUserDialog({ open: true, item: parent })}
                          title="Удалить пользователя"
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

        {/* Пагинация */}
        {filteredParents.length > 0 && (
          <div className="flex items-center justify-between mt-6 pt-4 border-t">
            <div className="text-sm text-muted-foreground">
              Показано {startIndex + 1}-{Math.min(endIndex, filteredParents.length)} из {filteredParents.length} родителей
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="flex items-center gap-2">
                <span className="text-sm">
                  Страница {currentPage} из {totalPages || 1}
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage >= totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <>
      {embedded ? (
        cardContent
      ) : (
        <div className="container mx-auto p-4">
          {cardContent}
        </div>
      )}

      {/* Диалог создания родителя */}
      <CreateParentDialog
        open={createDialog}
        onOpenChange={setCreateDialog}
        onSuccess={() => {
          loadParents();
        }}
      />

      {/* Диалог назначения студентов родителям */}
      <ParentStudentAssignment
        open={assignmentDialog}
        onOpenChange={setAssignmentDialog}
        onSuccess={() => {
          loadParents();
        }}
      />

      {/* Диалог редактирования пользователя */}
      {editUserDialog.item && (
        <EditUserDialog
          user={editUserDialog.item.user}
          open={editUserDialog.open}
          onOpenChange={(open) => setEditUserDialog({ open, item: null })}
          onSuccess={() => {
            loadParents();
          }}
        />
      )}

      {/* Диалог сброса пароля */}
      {resetPasswordDialog.item && (
        <ResetPasswordDialog
          user={resetPasswordDialog.item.user}
          open={resetPasswordDialog.open}
          onOpenChange={(open) => setResetPasswordDialog({ open, item: null })}
        />
      )}

      {/* Диалог удаления пользователя */}
      {deleteUserDialog.item && (
        <DeleteUserDialog
          user={deleteUserDialog.item.user}
          open={deleteUserDialog.open}
          onOpenChange={(open) => setDeleteUserDialog({ open, item: null })}
          onSuccess={() => {
            loadParents();
          }}
        />
      )}

      {/* Диалог реактивации пользователя */}
      <Dialog
        open={reactivateDialog.open}
        onOpenChange={(open) => setReactivateDialog({ ...reactivateDialog, open })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Активировать родителя</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              Вы уверены, что хотите активировать родителя <strong>{reactivateDialog.item?.user.full_name}</strong>?
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setReactivateDialog({ open: false, item: null, isLoading: false })}
              disabled={reactivateDialog.isLoading}
            >
              Отменить
            </Button>
            <Button
              onClick={handleReactivate}
              disabled={reactivateDialog.isLoading}
            >
              {reactivateDialog.isLoading ? 'Активация...' : 'Активировать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
