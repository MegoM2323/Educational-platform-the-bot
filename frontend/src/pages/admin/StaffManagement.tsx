import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { staffService, CreateStaffPayload, StaffListItem } from '@/services/staffService';
import { adminAPI } from '@/integrations/api/adminAPI';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { EditTeacherSubjectsDialog } from '@/components/admin/EditTeacherSubjectsDialog';
import { EditTeacherDialog } from '@/components/admin/EditTeacherDialog';
import { EditTutorDialog } from '@/components/admin/EditTutorDialog';
import { EditUserDialog } from '@/components/admin/EditUserDialog';
import { EditProfileDialog } from '@/components/admin/EditProfileDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';
import { Edit, BookOpen, Key, Trash2, User, LogOut, RotateCcw } from 'lucide-react';
import StudentManagement from './StudentManagement';
import ParentManagement from './ParentManagement';

export default function StaffManagement() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [activeTab, setActiveTab] = useState<'teacher' | 'tutor' | 'student' | 'parent'>('teacher');
  const [teachers, setTeachers] = useState<StaffListItem[]>([]);
  const [tutors, setTutors] = useState<StaffListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isLogoutLoading, setIsLogoutLoading] = useState(false);
  const [createdCredentials, setCreatedCredentials] = useState<{ login: string; password: string } | null>(null);
  const [editSubjectsDialog, setEditSubjectsDialog] = useState<{
    open: boolean;
    teacher: StaffListItem | null;
  }>({ open: false, teacher: null });
  const [editTeacherDialog, setEditTeacherDialog] = useState<{
    open: boolean;
    teacher: StaffListItem | null;
  }>({ open: false, teacher: null });
  const [editTutorDialog, setEditTutorDialog] = useState<{
    open: boolean;
    tutor: StaffListItem | null;
  }>({ open: false, tutor: null });
  const [editUserDialog, setEditUserDialog] = useState<{
    open: boolean;
    item: StaffListItem | null;
  }>({ open: false, item: null });
  const [editProfileDialog, setEditProfileDialog] = useState<{
    open: boolean;
    item: StaffListItem | null;
  }>({ open: false, item: null });
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
  const [form, setForm] = useState<CreateStaffPayload>({
    role: 'teacher',
    email: '',
    first_name: '',
    last_name: '',
    subject: '',
    specialization: '',
    experience_years: 0,
    bio: '',
  });

  const listToShow = useMemo(() => (activeTab === 'teacher' ? teachers : tutors), [activeTab, teachers, tutors]);

  const load = async () => {
    setIsLoading(true);
    try {
      const [tchs, tuts] = await Promise.all([staffService.list('teacher'), staffService.list('tutor')]);
      setTeachers(tchs);
      setTutors(tuts);
    } catch (e: any) {
      toast.error(e?.message || 'Ошибка загрузки списка');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openCreate = (role: 'teacher' | 'tutor') => {
    setForm({
      role,
      email: '',
      first_name: '',
      last_name: '',
      subject: '',
      specialization: '',
      experience_years: 0,
      bio: '',
    });
    setCreatedCredentials(null);
    setIsCreateOpen(true);
  };

  const submitCreate = async () => {
    try {
      // валидация
      if (!form.email || !form.first_name || !form.last_name) {
        toast.error('Заполните email, имя и фамилию');
        return;
      }
      if (form.role === 'teacher' && !form.subject) {
        toast.error('Укажите предмет');
        return;
      }
      if (form.role === 'tutor' && !form.specialization) {
        toast.error('Укажите специализацию');
        return;
      }
      const payload: CreateStaffPayload = {
        role: form.role,
        email: form.email.trim().toLowerCase(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        experience_years: form.experience_years || undefined,
        bio: form.bio || undefined,
        subject: form.role === 'teacher' ? form.subject : undefined,
        specialization: form.role === 'tutor' ? form.specialization : undefined,
      };
      const res = await staffService.create(payload);
      console.log('[StaffManagement] User created:', res);
      setCreatedCredentials(res.credentials);
      setIsCreateOpen(false);
      toast.success('Пользователь создан');

      // Загружаем список сразу после создания без задержек
      // База данных уже обновлена на момент получения ответа
      await load();
    } catch (e: any) {
      toast.error(e?.message || 'Не удалось создать пользователя');
      console.error('Error creating staff:', e);
    }
  };

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
        toast.success('Пользователь успешно активирован');
        setReactivateDialog({ open: false, item: null, isLoading: false });
        await load();
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
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>Управление пользователями</CardTitle>
          <div className="flex gap-2">
            {(activeTab === 'teacher' || activeTab === 'tutor') && (
              <>
                <Button onClick={() => openCreate('teacher')}>Создать преподавателя</Button>
                <Button variant="secondary" onClick={() => openCreate('tutor')}>Создать тьютора</Button>
              </>
            )}
            <Button
              variant="destructive"
              onClick={handleLogout}
              disabled={isLogoutLoading}
              className="ml-2"
            >
              <LogOut className="h-4 w-4 mr-2" />
              {isLogoutLoading ? 'Выход...' : 'Выйти'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
            <TabsList>
              <TabsTrigger value="teacher">Преподаватели</TabsTrigger>
              <TabsTrigger value="tutor">Тьюторы</TabsTrigger>
              <TabsTrigger value="student">Студенты</TabsTrigger>
              <TabsTrigger value="parent">Родители</TabsTrigger>
            </TabsList>
            <TabsContent value="teacher">
              <StaffTable
                items={teachers}
                isLoading={isLoading}
                type="teacher"
                onEditSubjects={(teacher) => setEditSubjectsDialog({ open: true, teacher })}
                onEdit={(item) => setEditTeacherDialog({ open: true, teacher: item })}
                onResetPassword={(item) => setResetPasswordDialog({ open: true, item })}
                onDeleteUser={(item) => setDeleteUserDialog({ open: true, item })}
                onReactivate={(item) => setReactivateDialog({ open: true, item, isLoading: false })}
              />
            </TabsContent>
            <TabsContent value="tutor">
              <StaffTable
                items={tutors}
                isLoading={isLoading}
                type="tutor"
                onEdit={(item) => setEditTutorDialog({ open: true, tutor: item })}
                onResetPassword={(item) => setResetPasswordDialog({ open: true, item })}
                onDeleteUser={(item) => setDeleteUserDialog({ open: true, item })}
                onReactivate={(item) => setReactivateDialog({ open: true, item, isLoading: false })}
              />
            </TabsContent>
            <TabsContent value="student" className="mt-6">
              <StudentManagement embedded={true} />
            </TabsContent>
            <TabsContent value="parent" className="mt-6">
              <ParentManagement embedded={true} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Диалог создания */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{form.role === 'teacher' ? 'Создание преподавателя' : 'Создание тьютора'}</DialogTitle>
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
            {form.role === 'teacher' ? (
              <div>
                <Label>Предмет</Label>
                <Input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
              </div>
            ) : (
              <div>
                <Label>Специализация</Label>
                <Input value={form.specialization} onChange={(e) => setForm({ ...form, specialization: e.target.value })} />
              </div>
            )}
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
            <Button onClick={submitCreate}>Создать</Button>
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
              <p className="text-sm text-muted-foreground">Скопируйте эти данные и отправьте преподавателю/тьютору. После закрытия окна они больше не будут показаны.</p>
              <div className="flex gap-2">
                <Button onClick={() => navigator.clipboard.writeText(`${createdCredentials.login} ${createdCredentials.password}`)}>Скопировать</Button>
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
          }}
        />
      )}

      {/* Диалог редактирования тьютора */}
      {editTutorDialog.tutor && (
        <EditTutorDialog
          tutor={editTutorDialog.tutor}
          open={editTutorDialog.open}
          onOpenChange={(open) => setEditTutorDialog({ open, tutor: null })}
          onSuccess={() => {
            toast.success('Тьютор успешно обновлен');
            load();
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
            load(); // Перезагрузить список преподавателей
          }}
        />
      )}

      {/* Диалог редактирования пользователя */}
      {editUserDialog.item && (
        <EditUserDialog
          user={editUserDialog.item.user}
          profile={editUserDialog.item}
          open={editUserDialog.open}
          onOpenChange={(open) => setEditUserDialog({ open, item: null })}
          onSuccess={() => {
            load(); // Перезагрузить список
          }}
        />
      )}

      {/* Диалог редактирования профиля */}
      {editProfileDialog.item && (
        <EditProfileDialog
          user={editProfileDialog.item.user}
          profile={editProfileDialog.item}
          open={editProfileDialog.open}
          onOpenChange={(open) => setEditProfileDialog({ open, item: null })}
          onSuccess={() => {
            load(); // Перезагрузить список
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
            load(); // Перезагрузить список
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
            <DialogTitle>Активировать пользователя</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              Вы уверены, что хотите активировать пользователя <strong>{reactivateDialog.item?.user.full_name}</strong>?
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
    </div>
  );
}

function StaffTable({
  items,
  isLoading,
  type,
  onEditSubjects,
  onEdit,
  onResetPassword,
  onDeleteUser,
  onReactivate,
}: {
  items: StaffListItem[];
  isLoading: boolean;
  type: 'teacher' | 'tutor';
  onEditSubjects?: (teacher: StaffListItem) => void;
  onEdit?: (item: StaffListItem) => void;
  onResetPassword?: (item: StaffListItem) => void;
  onDeleteUser?: (item: StaffListItem) => void;
  onReactivate?: (item: StaffListItem) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2 pr-4">ФИО</th>
            <th className="py-2 pr-4">Email</th>
            {type === 'teacher' ? (
              <th className="py-2 pr-4">Предметы</th>
            ) : (
              <th className="py-2 pr-4">Специализация</th>
            )}
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
          ) : !items || items.length === 0 ? (
            <tr>
              <td className="py-4" colSpan={5}>
                Пусто
              </td>
            </tr>
          ) : (
            items.map((item) => (
              <tr key={item.id} className="border-b">
                <td className="py-2 pr-4">{item.user.full_name}</td>
                <td className="py-2 pr-4">{item.user.email}</td>
                {type === 'teacher' ? (
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
                ) : (
                  <td className="py-2 pr-4">{item.specialization}</td>
                )}
                <td className="py-2 pr-4">{item.experience_years ?? 0}</td>
                <td className="py-2 pr-4">
                  <div className="flex gap-1">
                    {type === 'teacher' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onEditSubjects?.(item)}
                        title="Редактировать предметы"
                      >
                        <BookOpen className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onEdit?.(item)}
                      title={type === 'teacher' ? 'Редактировать преподавателя' : 'Редактировать тьютора'}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onResetPassword?.(item)}
                      title="Сбросить пароль"
                    >
                      <Key className="h-4 w-4" />
                    </Button>
                    {!item.user.is_active && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onReactivate?.(item)}
                        title="Активировать пользователя"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => onDeleteUser?.(item)}
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
  );
}


