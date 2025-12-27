import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Plus, Search, Edit, BookOpen, Key, Trash2 } from 'lucide-react';
import { staffService, StaffListItem } from '@/services/staffService';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { EditTeacherDialog } from '@/components/admin/EditTeacherDialog';
import { EditTeacherSubjectsDialog } from '@/components/admin/EditTeacherSubjectsDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';

interface TeacherSectionProps {
  onUpdate?: () => void;
}

export default function TeacherSection({ onUpdate }: TeacherSectionProps) {
  const [teachers, setTeachers] = useState<StaffListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createdCredentials, setCreatedCredentials] = useState<{ login: string; password: string } | null>(null);

  // Форма создания
  const [form, setForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    subject: '',
    experience_years: 0,
    bio: '',
  });

  // Диалоги
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

  useEffect(() => {
    loadTeachers();
  }, []);

  const loadTeachers = async () => {
    setIsLoading(true);
    try {
      const data = await staffService.list('teacher');
      // Применяем фильтр по поисковому запросу
      if (searchTerm) {
        const filtered = data.filter(
          (t) =>
            t.user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            t.user.email.toLowerCase().includes(searchTerm.toLowerCase())
        );
        setTeachers(filtered.slice(0, 5));
      } else {
        setTeachers(data.slice(0, 5));
      }
    } catch (error) {
      toast.error('Ошибка загрузки преподавателей');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = () => {
    loadTeachers();
  };

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
      if (!form.email || !form.first_name || !form.last_name || !form.subject) {
        toast.error('Заполните все обязательные поля');
        return;
      }

      const res = await staffService.create({
        role: 'teacher',
        email: form.email.trim().toLowerCase(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        subject: form.subject,
        experience_years: form.experience_years || undefined,
        bio: form.bio || undefined,
      });

      setCreatedCredentials(res.credentials);
      setIsCreateOpen(false);
      toast.success('Преподаватель создан');
      await loadTeachers();
      onUpdate?.();
    } catch (error: any) {
      toast.error(error?.message || 'Не удалось создать преподавателя');
    }
  };

  const handleSuccess = () => {
    loadTeachers();
    onUpdate?.();
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Преподаватели</CardTitle>
            <Button type="button" size="sm" onClick={openCreate}>
              <Plus className="h-4 w-4 mr-1" />
              Создать
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Поиск */}
          <div className="flex gap-2">
            <Input
              placeholder="Поиск по ФИО, email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1"
            />
            <Button type="button" variant="outline" size="icon" onClick={handleSearch}>
              <Search className="h-4 w-4" />
            </Button>
          </div>

          {/* Список преподавателей */}
          <div className="space-y-2">
            {isLoading ? (
              <div className="text-sm text-muted-foreground text-center py-4">Загрузка...</div>
            ) : teachers.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-4">
                Преподаватели не найдены
              </div>
            ) : (
              teachers.map((teacher) => (
                <div
                  key={teacher.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{teacher.user.full_name}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {teacher.user.email}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {teacher.subjects && teacher.subjects.length > 0 ? (
                        teacher.subjects.slice(0, 2).map((subject) => (
                          <Badge key={subject.id} variant="outline" className="text-xs">
                            {subject.name}
                          </Badge>
                        ))
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          Нет предметов
                        </Badge>
                      )}
                      {teacher.subjects && teacher.subjects.length > 2 && (
                        <Badge variant="outline" className="text-xs">
                          +{teacher.subjects.length - 2}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1 ml-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditTeacherDialog({ open: true, teacher })}
                      title="Редактировать"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditSubjectsDialog({ open: true, teacher })}
                      title="Предметы"
                    >
                      <BookOpen className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setResetPasswordDialog({ open: true, item: teacher })}
                      title="Сбросить пароль"
                    >
                      <Key className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setDeleteUserDialog({ open: true, item: teacher })}
                      title="Удалить"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))
            )}
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
                <Input
                  type="number"
                  value={form.experience_years}
                  onChange={(e) => setForm({ ...form, experience_years: Number(e.target.value) })}
                />
              </div>
              <div>
                <Label>Био</Label>
                <Input value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Отмена
            </Button>
            <Button type="button" onClick={submitCreate}>Создать</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Диалог с учетными данными */}
      <Dialog open={!!createdCredentials} onOpenChange={(open) => !open && setCreatedCredentials(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Учетные данные (показаны один раз)</DialogTitle>
          </DialogHeader>
          {createdCredentials && (
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="font-medium">Логин (email):</span> <span>{createdCredentials.login}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Пароль:</span> <span>{createdCredentials.password}</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Скопируйте эти данные и отправьте преподавателю. После закрытия окна они больше не будут показаны.
              </p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  onClick={() =>
                    navigator.clipboard.writeText(`${createdCredentials.login} ${createdCredentials.password}`)
                  }
                >
                  Скопировать
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Диалоги редактирования */}
      {editTeacherDialog.teacher && (
        <EditTeacherDialog
          teacher={editTeacherDialog.teacher}
          open={editTeacherDialog.open}
          onOpenChange={(open) => setEditTeacherDialog({ open, teacher: null })}
          onSuccess={handleSuccess}
        />
      )}

      {editSubjectsDialog.teacher && (
        <EditTeacherSubjectsDialog
          teacher={editSubjectsDialog.teacher}
          open={editSubjectsDialog.open}
          onOpenChange={(open) => setEditSubjectsDialog({ open, teacher: null })}
          onSuccess={handleSuccess}
        />
      )}

      {resetPasswordDialog.item && (
        <ResetPasswordDialog
          user={resetPasswordDialog.item.user}
          open={resetPasswordDialog.open}
          onOpenChange={(open) => setResetPasswordDialog({ open, item: null })}
        />
      )}

      {deleteUserDialog.item && (
        <DeleteUserDialog
          user={deleteUserDialog.item.user}
          open={deleteUserDialog.open}
          onOpenChange={(open) => setDeleteUserDialog({ open, item: null })}
          onSuccess={handleSuccess}
        />
      )}
    </>
  );
}
