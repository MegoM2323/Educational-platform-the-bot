import { useEffect, useState } from 'react';
import { logger } from '@/utils/logger';
import { adminAPI } from '@/integrations/api/adminAPI';
import { User } from '@/integrations/api/unifiedClient';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { EditUserDialog } from '@/components/admin/EditUserDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';
import { CreateParentDialog } from '@/components/admin/CreateParentDialog';
import { ParentStudentAssignment } from '@/components/admin/ParentStudentAssignment';
import UserDetailModal from '@/components/admin/UserDetailModal';
import { User as UserIcon, Key, Trash2, Plus, Link2, Search, RotateCcw, Eye } from 'lucide-react';

interface ParentItem {
  id: number;
  user: User;
  children_count?: number;
}

interface ParentSectionProps {
  onUpdate?: () => void;
}

export default function ParentSection({ onUpdate }: ParentSectionProps) {
  const [parents, setParents] = useState<ParentItem[]>([]);
  const [filteredParents, setFilteredParents] = useState<ParentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [createDialog, setCreateDialog] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [assignmentDialog, setAssignmentDialog] = useState(false);

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
  const [detailModal, setDetailModal] = useState<{
    open: boolean;
    item: ParentItem | null;
  }>({ open: false, item: null });

  const loadParents = async () => {
    setIsLoading(true);
    try {
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

  // Фильтрация в реальном времени
  useEffect(() => {
    if (!searchTerm) {
      setFilteredParents(parents);
      return;
    }

    const lowercaseSearch = searchTerm.toLowerCase();
    const filtered = parents.filter((parent) => {
      const fullName = parent.user.full_name?.toLowerCase() || '';
      const email = parent.user.email?.toLowerCase() || '';
      return fullName.includes(lowercaseSearch) || email.includes(lowercaseSearch);
    });
    setFilteredParents(filtered);
  }, [searchTerm, parents]);

  const handleReactivate = async () => {
    if (!reactivateDialog.item) return;

    setReactivateDialog((prev) => ({ ...prev, isLoading: true }));
    try {
      const response = await adminAPI.reactivateUser(reactivateDialog.item.user.id);
      if (response.success) {
        toast.success('Родитель успешно активирован');
        setReactivateDialog({ open: false, item: null, isLoading: false });
        await loadParents();
        onUpdate?.();
      } else {
        toast.error(response.error || 'Ошибка при активации');
        setReactivateDialog((prev) => ({ ...prev, isLoading: false }));
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Неизвестная ошибка';
      toast.error(message);
      setReactivateDialog((prev) => ({ ...prev, isLoading: false }));
    }
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Родители</CardTitle>
          <div className="flex gap-2">
            <Button type="button" onClick={() => setCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Создать родителя
            </Button>
            <Button type="button" variant="outline" onClick={() => setAssignmentDialog(true)}>
              <Link2 className="h-4 w-4 mr-2" />
              Назначить студентов
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Поиск */}
          <div className="mb-6">
            <Label className="text-sm">Поиск</Label>
            <div className="flex gap-2 mt-2">
              <Input
                placeholder="ФИО или email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1"
              />
              <Button type="button" variant="outline" size="icon">
                <Search className="h-4 w-4" />
              </Button>
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
                  <th className="py-2 pr-4">Детей</th>
                  <th className="py-2 pr-4">Действия</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td className="py-4" colSpan={5}>
                      Загрузка...
                    </td>
                  </tr>
                ) : filteredParents.length === 0 ? (
                  <tr>
                    <td className="py-4" colSpan={5}>
                      {searchTerm ? 'Родители не найдены по запросу' : 'Родители не найдены'}
                    </td>
                  </tr>
                ) : (
                  filteredParents.map((parent) => (
                    <tr key={parent.id} className="border-b hover:bg-muted/50">
                      <td className="py-2 pr-4">{parent.user.full_name}</td>
                      <td className="py-2 pr-4">{parent.user.email}</td>
                      <td className="py-2 pr-4">{parent.user.phone || '-'}</td>
                      <td className="py-2 pr-4">{parent.children_count || 0}</td>
                      <td className="py-2 pr-4">
                        <div className="flex gap-1">
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setDetailModal({ open: true, item: parent })}
                            title="Просмотреть профиль"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setEditUserDialog({ open: true, item: parent })}
                            title="Редактировать пользователя"
                          >
                            <UserIcon className="h-4 w-4" />
                          </Button>
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setResetPasswordDialog({ open: true, item: parent })}
                            title="Сбросить пароль"
                          >
                            <Key className="h-4 w-4" />
                          </Button>
                          {!parent.user.is_active && (
                            <Button type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => setReactivateDialog({ open: true, item: parent, isLoading: false })}
                              title="Активировать родителя"
                            >
                              <RotateCcw className="h-4 w-4" />
                            </Button>
                          )}
                          <Button type="button"
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
        </CardContent>
      </Card>

      {/* Диалог создания родителя */}
      <CreateParentDialog
        open={createDialog}
        onOpenChange={setCreateDialog}
        onSuccess={() => {
          loadParents();
          onUpdate?.();
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
          onOpenChange={(open) => {
            if (!open) {
              setEditUserDialog((prev) => ({ ...prev, open: false }));
              setTimeout(() => setEditUserDialog({ open: false, item: null }), 300);
            } else {
              setEditUserDialog((prev) => ({ ...prev, open }));
            }
          }}
          onSuccess={() => {
            loadParents();
            onUpdate?.();
          }}
        />
      )}

      {/* Диалог сброса пароля */}
      {resetPasswordDialog.item && (
        <ResetPasswordDialog
          user={resetPasswordDialog.item.user}
          open={resetPasswordDialog.open}
          onOpenChange={(open) => {
            if (!open) {
              setResetPasswordDialog((prev) => ({ ...prev, open: false }));
              setTimeout(() => setResetPasswordDialog({ open: false, item: null }), 300);
            } else {
              setResetPasswordDialog((prev) => ({ ...prev, open }));
            }
          }}
        />
      )}

      {/* Диалог удаления пользователя */}
      {deleteUserDialog.item && (
        <DeleteUserDialog
          user={deleteUserDialog.item.user}
          open={deleteUserDialog.open}
          onOpenChange={(open) => {
            if (!open) {
              setDeleteUserDialog((prev) => ({ ...prev, open: false }));
              setTimeout(() => setDeleteUserDialog({ open: false, item: null }), 300);
            } else {
              setDeleteUserDialog((prev) => ({ ...prev, open }));
            }
          }}
          onSuccess={() => {
            loadParents();
            onUpdate?.();
          }}
        />
      )}

      {/* Модальное окно детального просмотра */}
      {detailModal.item && (
        <UserDetailModal
          open={detailModal.open}
          onOpenChange={(open) => {
            if (!open) {
              setDetailModal((prev) => ({ ...prev, open: false }));
              setTimeout(() => setDetailModal({ open: false, item: null }), 300);
            } else {
              setDetailModal((prev) => ({ ...prev, open }));
            }
          }}
          userId={detailModal.item.user.id}
          role="parent"
          onUpdate={() => {
            loadParents();
            onUpdate?.();
          }}
        />
      )}

      {/* Диалог реактивации пользователя */}
      <Dialog
        open={reactivateDialog.open}
        onOpenChange={(open) => {
          if (!open) {
            setReactivateDialog((prev) => ({ ...prev, open: false }));
            setTimeout(() => setReactivateDialog({ open: false, item: null, isLoading: false }), 300);
          } else {
            setReactivateDialog((prev) => ({ ...prev, open }));
          }
        }}
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
            <Button type="button"
              variant="outline"
              onClick={() => setReactivateDialog({ open: false, item: null, isLoading: false })}
              disabled={reactivateDialog.isLoading}
            >
              Отменить
            </Button>
            <Button type="button"
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
