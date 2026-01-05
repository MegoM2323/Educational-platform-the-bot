import { useEffect, useState, useCallback } from 'react';
import { logger } from '@/utils/logger';
import { staffService, StaffListItem } from '@/services/staffService';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { adminAPI } from '@/integrations/api/adminAPI';
import { EditTutorDialog } from '@/components/admin/EditTutorDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';
import UserDetailModal from '@/components/admin/UserDetailModal';
import { Edit, Key, Trash2, Plus, Search, RotateCcw, Eye } from 'lucide-react';

interface TutorSectionProps {
  onUpdate?: () => void;
}

export default function TutorSection({ onUpdate }: TutorSectionProps) {
  const [tutors, setTutors] = useState<StaffListItem[]>([]);
  const [filteredTutors, setFilteredTutors] = useState<StaffListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [createdCredentials, setCreatedCredentials] = useState<{ login: string; password: string } | null>(null);

  const [editTutorDialog, setEditTutorDialog] = useState<{
    open: boolean;
    tutor: StaffListItem | null;
  }>({ open: false, tutor: null });

  const [resetPasswordDialog, setResetPasswordDialog] = useState<{
    open: boolean;
    item: StaffListItem | null;
  }>({ open: false, item: null });

  const [deleteUserDialog, setDeleteUserDialog] = useState<{
    open: boolean;
    item: StaffListItem | null;
  }>({ open: false, item: null });

  const [reactivateDialog, setReactivateDialog] = useState<{
    open: boolean;
    item: StaffListItem | null;
    isLoading: boolean;
  }>({ open: false, item: null, isLoading: false });
  const [detailModal, setDetailModal] = useState<{
    open: boolean;
    item: StaffListItem | null;
  }>({ open: false, item: null });

  const [form, setForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    specialization: '',
    experience_years: 0,
    bio: '',
  });

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const tuts = await staffService.list('tutor');
      setTutors(tuts);
      setFilteredTutors(tuts);
    } catch (e: any) {
      toast.error(e?.message || 'Ошибка загрузки списка');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Фильтрация в реальном времени
  useEffect(() => {
    if (!searchTerm) {
      setFilteredTutors(tutors);
      return;
    }

    const lowercaseSearch = searchTerm.toLowerCase();
    const filtered = tutors.filter((tutor) => {
      const fullName = tutor.user.full_name?.toLowerCase() || '';
      const email = tutor.user.email?.toLowerCase() || '';
      const specialization = tutor.specialization?.toLowerCase() || '';
      return fullName.includes(lowercaseSearch) || email.includes(lowercaseSearch) || specialization.includes(lowercaseSearch);
    });
    setFilteredTutors(filtered);
  }, [searchTerm, tutors]);

  const openCreate = () => {
    setForm({
      email: '',
      first_name: '',
      last_name: '',
      specialization: '',
      experience_years: 0,
      bio: '',
    });
    setCreatedCredentials(null);
    setIsCreateOpen(true);
  };

  const submitCreate = async () => {
    try {
      // Валидация
      if (!form.email || !form.first_name || !form.last_name) {
        toast.error('Заполните email, имя и фамилию');
        return;
      }
      if (!form.specialization) {
        toast.error('Укажите специализацию');
        return;
      }

      const payload = {
        role: 'tutor' as const,
        email: form.email.trim().toLowerCase(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        experience_years: form.experience_years || undefined,
        bio: form.bio || undefined,
        specialization: form.specialization,
      };

      const res = await staffService.create(payload);
      logger.debug('[TutorSection] Tutor created:', res);
      setCreatedCredentials(res.credentials);
      setIsCreateOpen(false);
      toast.success('Тьютор создан');

      // Перезагрузка списка
      await load();
      onUpdate?.();
    } catch (e: any) {
      toast.error(e?.message || 'Не удалось создать тьютора');
      logger.error('Error creating tutor:', e);
    }
  };

  const handleReactivate = async () => {
    if (!reactivateDialog.item) return;

    setReactivateDialog((prev) => ({ ...prev, isLoading: true }));
    try {
      const response = await adminAPI.reactivateUser(reactivateDialog.item.user.id);
      if (response.success) {
        toast.success('Тьютор успешно активирован');
        setReactivateDialog({ open: false, item: null, isLoading: false });
        await load();
        onUpdate?.();
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

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Тьютеры</CardTitle>
          <Button type="button" onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" />
            Создать тьютера
          </Button>
        </CardHeader>
        <CardContent>
          {/* Поиск */}
          <div className="mb-6">
            <Label className="text-sm">Поиск</Label>
            <div className="flex gap-2 mt-2">
              <Input
                placeholder="ФИО, email, специализация..."
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
                  <th className="py-2 pr-4">Специализация</th>
                  <th className="py-2 pr-4">Опыт</th>
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
                ) : !filteredTutors || filteredTutors.length === 0 ? (
                  <tr>
                    <td className="py-4" colSpan={5}>
                      {searchTerm ? 'Тьютеры не найдены по запросу' : 'Тьютеры не найдены'}
                    </td>
                  </tr>
                ) : (
                  filteredTutors.map((item) => (
                    <tr key={item.id} className="border-b hover:bg-muted/50">
                      <td className="py-2 pr-4">{item.user.full_name}</td>
                      <td className="py-2 pr-4">{item.user.email}</td>
                      <td className="py-2 pr-4">{item.specialization || '-'}</td>
                      <td className="py-2 pr-4">{item.experience_years ?? 0}</td>
                      <td className="py-2 pr-4">
                        <div className="flex gap-1">
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setDetailModal({ open: true, item })}
                            title="Просмотреть профиль"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setEditTutorDialog({ open: true, tutor: item })}
                            title="Редактировать тьютора"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setResetPasswordDialog({ open: true, item })}
                            title="Сбросить пароль"
                          >
                            <Key className="h-4 w-4" />
                          </Button>
                          {!item.user.is_active && (
                            <Button type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => setReactivateDialog({ open: true, item, isLoading: false })}
                              title="Активировать тьютора"
                            >
                              <RotateCcw className="h-4 w-4" />
                            </Button>
                          )}
                          <Button type="button"
                            size="sm"
                            variant="destructive"
                            onClick={() => setDeleteUserDialog({ open: true, item })}
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

      {/* Диалог создания */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Создание тьютора</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            <div>
              <Label>Email</Label>
              <Input type="email" autoComplete="username" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Имя</Label>
                <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
              </div>
              <div>
                <Label>Фамилия</Label>
                <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
              </div>
            </div>
            <div>
              <Label>Специализация</Label>
              <Input value={form.specialization} onChange={(e) => setForm({ ...form, specialization: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Опыт (лет)</Label>
                <Input type="number" value={form.experience_years}
                  onChange={(e) => setForm({ ...form, experience_years: Number(e.target.value) })} />
              </div>
              <div>
                <Label>Био</Label>
                <Input value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" onClick={submitCreate}>Создать</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Диалог одноразовых данных */}
      <Dialog open={!!createdCredentials} onOpenChange={(open) => !open && setCreatedCredentials(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Учетные данные (показаны один раз)</DialogTitle>
          </DialogHeader>
          {createdCredentials && (
            <div className="space-y-2">
              <div className="flex justify-between"><span className="font-medium">Логин (email):</span> <span>{createdCredentials.login}</span></div>
              <div className="flex justify-between"><span className="font-medium">Пароль:</span> <span>{createdCredentials.password}</span></div>
              <p className="text-sm text-muted-foreground">Скопируйте эти данные и отправьте тьютору. После закрытия окна они больше не будут показаны.</p>
              <div className="flex gap-2">
                <Button type="button" onClick={() => navigator.clipboard.writeText(`${createdCredentials.login} ${createdCredentials.password}`)}>Скопировать</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Диалог редактирования тьютора */}
      {editTutorDialog.tutor && (
        <EditTutorDialog
          tutor={editTutorDialog.tutor}
          open={editTutorDialog.open}
          onOpenChange={(open) => {
            if (!open) {
              setEditTutorDialog((prev) => ({ ...prev, open: false }));
              setTimeout(() => setEditTutorDialog({ open: false, tutor: null }), 300);
            } else {
              setEditTutorDialog((prev) => ({ ...prev, open }));
            }
          }}
          onSuccess={() => {
            toast.success('Тьютор успешно обновлен');
            load();
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
            load();
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
          role="tutor"
          onUpdate={() => {
            load();
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
            <DialogTitle>Активировать тьютора</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              Вы уверены, что хотите активировать тьютора <strong>{reactivateDialog.item?.user.full_name}</strong>?
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
