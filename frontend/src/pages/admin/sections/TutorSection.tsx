import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Plus, Search, Edit, Key, Trash2 } from 'lucide-react';
import { staffService, StaffListItem } from '@/services/staffService';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { EditTutorDialog } from '@/components/admin/EditTutorDialog';
import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog';
import { DeleteUserDialog } from '@/components/admin/DeleteUserDialog';

interface TutorSectionProps {
  onUpdate?: () => void;
}

export default function TutorSection({ onUpdate }: TutorSectionProps) {
  const [tutors, setTutors] = useState<StaffListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createdCredentials, setCreatedCredentials] = useState<{ login: string; password: string } | null>(null);

  // Форма создания
  const [form, setForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    specialization: '',
    experience_years: 0,
    bio: '',
  });

  // Диалоги
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

  useEffect(() => {
    loadTutors();
  }, []);

  const loadTutors = async () => {
    setIsLoading(true);
    try {
      const data = await staffService.list('tutor');
      // Применяем фильтр по поисковому запросу
      if (searchTerm) {
        const filtered = data.filter(
          (t) =>
            t.user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            t.user.email.toLowerCase().includes(searchTerm.toLowerCase())
        );
        setTutors(filtered.slice(0, 5));
      } else {
        setTutors(data.slice(0, 5));
      }
    } catch (error) {
      toast.error('Ошибка загрузки тьюторов');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = () => {
    loadTutors();
  };

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
      if (!form.email || !form.first_name || !form.last_name || !form.specialization) {
        toast.error('Заполните все обязательные поля');
        return;
      }

      const res = await staffService.create({
        role: 'tutor',
        email: form.email.trim().toLowerCase(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        specialization: form.specialization,
        experience_years: form.experience_years || undefined,
        bio: form.bio || undefined,
      });

      setCreatedCredentials(res.credentials);
      setIsCreateOpen(false);
      toast.success('Тьютор создан');
      await loadTutors();
      onUpdate?.();
    } catch (error: any) {
      toast.error(error?.message || 'Не удалось создать тьютора');
    }
  };

  const handleSuccess = () => {
    loadTutors();
    onUpdate?.();
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Тьюторы</CardTitle>
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

          {/* Список тьюторов */}
          <div className="space-y-2">
            {isLoading ? (
              <div className="text-sm text-muted-foreground text-center py-4">Загрузка...</div>
            ) : tutors.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-4">
                Тьюторы не найдены
              </div>
            ) : (
              tutors.map((tutor) => (
                <div
                  key={tutor.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{tutor.user.full_name}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {tutor.user.email}
                    </div>
                    <div className="flex gap-1 mt-1">
                      {tutor.specialization && (
                        <Badge variant="outline" className="text-xs">
                          {tutor.specialization}
                        </Badge>
                      )}
                      {tutor.experience_years !== undefined && tutor.experience_years > 0 && (
                        <Badge variant="secondary" className="text-xs">
                          {tutor.experience_years} лет опыта
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1 ml-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditTutorDialog({ open: true, tutor })}
                      title="Редактировать"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setResetPasswordDialog({ open: true, item: tutor })}
                      title="Сбросить пароль"
                    >
                      <Key className="h-4 w-4" />
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setDeleteUserDialog({ open: true, item: tutor })}
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
            <DialogTitle>Создание тьютора</DialogTitle>
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
              <Label>Специализация</Label>
              <Input
                value={form.specialization}
                onChange={(e) => setForm({ ...form, specialization: e.target.value })}
              />
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
                Скопируйте эти данные и отправьте тьютору. После закрытия окна они больше не будут показаны.
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
      {editTutorDialog.tutor && (
        <EditTutorDialog
          tutor={editTutorDialog.tutor}
          open={editTutorDialog.open}
          onOpenChange={(open) => setEditTutorDialog({ open, tutor: null })}
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
