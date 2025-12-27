import { useEffect, useState, useCallback } from 'react';
import { logger } from '@/utils/logger';
import { staffService, StaffListItem } from '@/services/staffService';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { adminAPI } from '@/integrations/api/adminAPI';
import { EditTeacherDialog } from '@/components/admin/EditTeacherDialog';
import { EditTeacherSubjectsDialog } from '@/components/admin/EditTeacherSubjectsDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';
import UserDetailModal from '@/components/admin/UserDetailModal';
import { Edit, BookOpen, Key, Trash2, Plus, Search, RotateCcw, Eye } from 'lucide-react';

interface TeacherSectionProps {
  onUpdate?: () => void;
}

export default function TeacherSection({ onUpdate }: TeacherSectionProps) {
  const [teachers, setTeachers] = useState<StaffListItem[]>([]);
  const [filteredTeachers, setFilteredTeachers] = useState<StaffListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [createdCredentials, setCreatedCredentials] = useState<{ login: string; password: string } | null>(null);

  const [editTeacherDialog, setEditTeacherDialog] = useState<{
    open: boolean;
    teacher: StaffListItem | null;
  }>({ open: false, teacher: null });

  const [editSubjectsDialog, setEditSubjectsDialog] = useState<{
    open: boolean;
    teacher: StaffListItem | null;
  }>({ open: false, teacher: null });

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
    subject: '',
    experience_years: 0,
    bio: '',
  });

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const tchs = await staffService.list('teacher');
      setTeachers(tchs);
      setFilteredTeachers(tchs);
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
      setFilteredTeachers(teachers);
      return;
    }

    const lowercaseSearch = searchTerm.toLowerCase();
    const filtered = teachers.filter((teacher) => {
      const fullName = teacher.user.full_name?.toLowerCase() || '';
      const email = teacher.user.email?.toLowerCase() || '';
      const subjects = teacher.subjects?.map(s => s.name.toLowerCase()).join(' ') || '';
      return fullName.includes(lowercaseSearch) || email.includes(lowercaseSearch) || subjects.includes(lowercaseSearch);
    });
    setFilteredTeachers(filtered);
  }, [searchTerm, teachers]);

  const openCreate = () => {
    setForm({
      email: '',
      first_name: '',
      last_name: '',
      subject: '',
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
      if (!form.subject) {
        toast.error('Укажите предмет');
        return;
      }

      const payload = {
        role: 'teacher' as const,
        email: form.email.trim().toLowerCase(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        experience_years: form.experience_years || undefined,
        bio: form.bio || undefined,
        subject: form.subject,
      };

      const res = await staffService.create(payload);
      logger.debug('[TeacherSection] Teacher created:', res);
      setCreatedCredentials(res.credentials);
      setIsCreateOpen(false);
      toast.success('Преподаватель создан');

      // Перезагрузка списка
      await load();
      onUpdate?.();
    } catch (e: any) {
      toast.error(e?.message || 'Не удалось создать преподавателя');
      logger.error('Error creating teacher:', e);
    }
  };

  const handleReactivate = async () => {
    if (!reactivateDialog.item) return;

    setReactivateDialog((prev) => ({ ...prev, isLoading: true }));
    try {
      const response = await adminAPI.reactivateUser(reactivateDialog.item.user.id);
      if (response.success) {
        toast.success('Преподаватель успешно активирован');
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
          <CardTitle>Преподаватели</CardTitle>
          <Button type="button" onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" />
            Создать преподавателя
          </Button>
        </CardHeader>
        <CardContent>
          {/* Поиск */}
          <div className="mb-6">
            <Label className="text-sm">Поиск</Label>
            <div className="flex gap-2 mt-2">
              <Input
                placeholder="ФИО, email, предметы..."
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
                  <th className="py-2 pr-4">Предметы</th>
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
                ) : !filteredTeachers || filteredTeachers.length === 0 ? (
                  <tr>
                    <td className="py-4" colSpan={5}>
                      {searchTerm ? 'Преподаватели не найдены по запросу' : 'Преподаватели не найдены'}
                    </td>
                  </tr>
                ) : (
                  filteredTeachers.map((item) => (
                    <tr key={item.id} className="border-b hover:bg-muted/50">
                      <td className="py-2 pr-4">{item.user.full_name}</td>
                      <td className="py-2 pr-4">{item.user.email}</td>
                      <td className="py-2 pr-4">
                        {item.subjects && item.subjects.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {item.subjects.slice(0, 3).map((subject) => (
                              <Badge key={subject.id} variant="secondary">
                                {subject.name}
                              </Badge>
                            ))}
                            {item.subjects.length > 3 && (
                              <Badge variant="outline">
                                +{item.subjects.length - 3} ещё
                              </Badge>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted-foreground text-xs">
                            Не назначены
                          </span>
                        )}
                      </td>
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
                            onClick={() => setEditSubjectsDialog({ open: true, teacher: item })}
                            title="Редактировать предметы"
                          >
                            <BookOpen className="h-4 w-4" />
                          </Button>
                          <Button type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setEditTeacherDialog({ open: true, teacher: item })}
                            title="Редактировать преподавателя"
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
                              title="Активировать преподавателя"
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
            <DialogTitle>Создание преподавателя</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            <div>
              <Label>Email</Label>
              <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
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
              <Label>Предмет</Label>
              <Input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
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
              <p className="text-sm text-muted-foreground">Скопируйте эти данные и отправьте преподавателю. После закрытия окна они больше не будут показаны.</p>
              <div className="flex gap-2">
                <Button type="button" onClick={() => navigator.clipboard.writeText(`${createdCredentials.login} ${createdCredentials.password}`)}>Скопировать</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Диалог редактирования преподавателя */}
      {editTeacherDialog.teacher && (
        <EditTeacherDialog
          teacher={editTeacherDialog.teacher}
          open={editTeacherDialog.open}
          onOpenChange={(open) => setEditTeacherDialog({ open, teacher: null })}
          onSuccess={() => {
            toast.success('Преподаватель успешно обновлен');
            load();
            onUpdate?.();
          }}
        />
      )}

      {/* Диалог редактирования предметов */}
      {editSubjectsDialog.teacher && (
        <EditTeacherSubjectsDialog
          teacher={editSubjectsDialog.teacher}
          open={editSubjectsDialog.open}
          onOpenChange={(open) => setEditSubjectsDialog({ open, teacher: null })}
          onSuccess={() => {
            toast.success('Предметы обновлены');
            load();
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
            load();
            onUpdate?.();
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
            <DialogTitle>Активировать преподавателя</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              Вы уверены, что хотите активировать преподавателя <strong>{reactivateDialog.item?.user.full_name}</strong>?
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

      {/* Модальное окно детального просмотра */}
      {detailModal.item && (
        <UserDetailModal
          open={detailModal.open}
          onOpenChange={(open) => setDetailModal({ open, item: null })}
          userId={detailModal.item.user.id}
          role="teacher"
          onUpdate={() => {
            load();
            onUpdate?.();
          }}
        />
      )}
    </>
  );
}
