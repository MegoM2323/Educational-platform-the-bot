import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAssignSubject } from '@/hooks/useTutor';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

interface Subject { id: number; name: string; }
interface Teacher { id: number; full_name: string; }

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  studentId: number;
}

export default function AssignSubjectDialog({ open, onOpenChange, studentId }: Props) {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [subjectId, setSubjectId] = useState<string>('');
  const [teacherId, setTeacherId] = useState<string>('');

  const assignMutation = useAssignSubject(studentId);

  useEffect(() => {
    if (!open) return;
    const load = async () => {
      const [s, t] = await Promise.all([
        unifiedAPI.request<Subject[]>('/materials/subjects/'),
        unifiedAPI.request<Teacher[]>('/accounts/users/?role=teacher'),
      ]);
      if (s.data) setSubjects(s.data);
      if (t.data) setTeachers(t.data);
    };
    load();
  }, [open]);

  const submit = async () => {
    if (!subjectId) return;
    const payload: any = { subject_id: Number(subjectId) };
    if (teacherId) payload.teacher_id = Number(teacherId);
    await assignMutation.mutateAsync(payload);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Назначить предмет</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label>Предмет</Label>
            <Select value={subjectId} onValueChange={setSubjectId}>
              <SelectTrigger aria-label="subject-select">
                <SelectValue placeholder="Выберите предмет" />
              </SelectTrigger>
              <SelectContent>
                {subjects.map(s => (
                  <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Преподаватель</Label>
            <Select value={teacherId} onValueChange={setTeacherId}>
              <SelectTrigger aria-label="teacher-select">
                <SelectValue placeholder="Выберите преподавателя" />
              </SelectTrigger>
              <SelectContent>
                {teachers.map(t => (
                  <SelectItem key={t.id} value={String(t.id)}>{t.full_name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Отмена</Button>
          <Button onClick={submit} disabled={assignMutation.isPending || !subjectId}>Назначить</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
