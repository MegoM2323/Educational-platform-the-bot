import { useEffect, useMemo, useState } from 'react';
import { staffService, CreateStaffPayload, StaffListItem } from '@/services/staffService';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { toast } from 'sonner';

export default function StaffManagement() {
  const [activeTab, setActiveTab] = useState<'teacher' | 'tutor'>('teacher');
  const [teachers, setTeachers] = useState<StaffListItem[]>([]);
  const [tutors, setTutors] = useState<StaffListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createdCredentials, setCreatedCredentials] = useState<{ login: string; password: string } | null>(null);
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

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>Управление преподавателями и тьюторами</CardTitle>
          <div className="flex gap-2">
            <Button onClick={() => openCreate('teacher')}>Создать преподавателя</Button>
            <Button variant="secondary" onClick={() => openCreate('tutor')}>Создать тьютора</Button>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
            <TabsList>
              <TabsTrigger value="teacher">Преподаватели</TabsTrigger>
              <TabsTrigger value="tutor">Тьюторы</TabsTrigger>
            </TabsList>
            <TabsContent value="teacher">
              <StaffTable items={teachers} isLoading={isLoading} type="teacher" />
            </TabsContent>
            <TabsContent value="tutor">
              <StaffTable items={tutors} isLoading={isLoading} type="tutor" />
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
    </div>
  );
}

function StaffTable({ items, isLoading, type }: { items: StaffListItem[]; isLoading: boolean; type: 'teacher' | 'tutor' }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2 pr-4">ФИО</th>
            <th className="py-2 pr-4">Email</th>
            <th className="py-2 pr-4">{type === 'teacher' ? 'Предмет' : 'Специализация'}</th>
            <th className="py-2 pr-4">Опыт</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr><td className="py-4" colSpan={4}>Загрузка...</td></tr>
          ) : items.length === 0 ? (
            <tr><td className="py-4" colSpan={4}>Пусто</td></tr>
          ) : (
            items.map((item) => (
              <tr key={item.id} className="border-b">
                <td className="py-2 pr-4">{item.user.full_name}</td>
                <td className="py-2 pr-4">{item.user.email}</td>
                <td className="py-2 pr-4">{type === 'teacher' ? item.subject : item.specialization}</td>
                <td className="py-2 pr-4">{item.experience_years ?? 0}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}


