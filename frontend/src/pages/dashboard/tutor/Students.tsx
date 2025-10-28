import { useState } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { TutorSidebar } from '@/components/layout/TutorSidebar';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useTutorStudents, useCreateTutorStudent } from '@/hooks/useTutor';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import AssignSubjectDialog from '@/components/tutor/AssignSubjectDialog';

export default function TutorStudentsPage() {
  const { data: students, isLoading } = useTutorStudents();
  const createMutation = useCreateTutorStudent();

  const [open, setOpen] = useState(false);
  const [credsOpen, setCredsOpen] = useState(false);
  const [generatedCreds, setGeneratedCreds] = useState<{ student: { username: string; password: string }; parent: { username: string; password: string } } | null>(null);
  const [assignOpen, setAssignOpen] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    grade: '',
    goal: '',
    parent_first_name: '',
    parent_last_name: '',
    parent_email: '',
    parent_phone: '',
  });

  const submit = async () => {
    const res = await createMutation.mutateAsync(form);
    setGeneratedCreds(res.credentials);
    setOpen(false);
    setCredsOpen(true);
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TutorSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
            <Button onClick={() => setOpen(true)}>Создать ученика</Button>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <Card className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold">Мои ученики</h2>
                  <Badge variant="secondary">{students?.length || 0}</Badge>
                </div>
                {isLoading ? (
                  <div>Загрузка...</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {students?.map((s) => (
                      <Card key={s.id} className="p-4 space-y-3">
                        <div className="font-medium">{s.full_name || `${s.first_name || ''} ${s.last_name || ''}`}</div>
                        <div className="text-sm text-muted-foreground">Класс: {s.grade || '-'}</div>
                        <div className="text-sm text-muted-foreground">Цель: {s.goal || '-'}</div>
                        <div className="pt-2">
                          <Button variant="secondary" onClick={() => { setSelectedStudentId(s.id); setAssignOpen(true); }}>Назначить предмет</Button>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </main>
        </SidebarInset>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Создание ученика</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Имя</Label>
              <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </div>
            <div>
              <Label>Фамилия</Label>
              <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </div>
            <div>
              <Label>Класс</Label>
              <Input value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })} />
            </div>
            <div className="md:col-span-2">
              <Label>Цель</Label>
              <Input value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} />
            </div>
            <div>
              <Label>Имя родителя</Label>
              <Input value={form.parent_first_name} onChange={(e) => setForm({ ...form, parent_first_name: e.target.value })} />
            </div>
            <div>
              <Label>Фамилия родителя</Label>
              <Input value={form.parent_last_name} onChange={(e) => setForm({ ...form, parent_last_name: e.target.value })} />
            </div>
            <div>
              <Label>Email родителя</Label>
              <Input value={form.parent_email} onChange={(e) => setForm({ ...form, parent_email: e.target.value })} />
            </div>
            <div>
              <Label>Телефон родителя</Label>
              <Input value={form.parent_phone} onChange={(e) => setForm({ ...form, parent_phone: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Отмена</Button>
            <Button onClick={submit} disabled={createMutation.isPending}>Создать</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={credsOpen} onOpenChange={setCredsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Сгенерированные учетные данные</DialogTitle>
          </DialogHeader>
          {generatedCreds ? (
            <div className="space-y-3">
              <Card className="p-3">
                <div className="font-semibold mb-2">Ученик</div>
                <div className="text-sm">Логин: {generatedCreds.student.username}</div>
                <div className="text-sm">Пароль: {generatedCreds.student.password}</div>
              </Card>
              <Card className="p-3">
                <div className="font-semibold mb-2">Родитель</div>
                <div className="text-sm">Логин: {generatedCreds.parent.username}</div>
                <div className="text-sm">Пароль: {generatedCreds.parent.password}</div>
              </Card>
          ) : null}
          <DialogFooter>
            <Button onClick={() => setCredsOpen(false)}>Закрыть</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {selectedStudentId !== null && (
        <AssignSubjectDialog open={assignOpen} onOpenChange={setAssignOpen} studentId={selectedStudentId} />
      )}
    </SidebarProvider>
  );
}
