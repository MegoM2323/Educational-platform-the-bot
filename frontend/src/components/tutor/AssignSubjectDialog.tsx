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
  const [allTeachers, setAllTeachers] = useState<Teacher[]>([]);
  const [availableTeachers, setAvailableTeachers] = useState<Teacher[]>([]);
  const [subjectId, setSubjectId] = useState<string>('');
  const [teacherId, setTeacherId] = useState<string>('');
  const [loadingTeachers, setLoadingTeachers] = useState(false);

  const assignMutation = useAssignSubject(studentId);

  useEffect(() => {
    if (!open) return;
    const load = async () => {
      try {
        const [s, t] = await Promise.all([
          unifiedAPI.request<any>('/materials/subjects/'),
          unifiedAPI.request<any>('/accounts/users/?role=teacher'),
        ]);
        
        console.log('Subjects response:', s);
        console.log('Teachers response:', t);
        
        // API может вернуть либо массив, либо объект с data/results
        let subjectsData: Subject[] = [];
        let teachersData: Teacher[] = [];
        
        if (s.data) {
          if (Array.isArray(s.data)) {
            subjectsData = s.data;
          } else if (s.data.results && Array.isArray(s.data.results)) {
            subjectsData = s.data.results;
          } else if (s.data.subjects && Array.isArray(s.data.subjects)) {
            subjectsData = s.data.subjects;
          }
        }
        
        if (t.data) {
          if (Array.isArray(t.data)) {
            teachersData = t.data;
          } else if (t.data.results && Array.isArray(t.data.results)) {
            teachersData = t.data.results;
          } else if (t.data.users && Array.isArray(t.data.users)) {
            teachersData = t.data.users;
          }
        }
        
        console.log('Parsed subjects:', subjectsData);
        console.log('Parsed teachers:', teachersData);
        
        setSubjects(subjectsData);
        setAllTeachers(teachersData);
      } catch (error) {
        console.error('Error loading data:', error);
      }
    };
    load();
  }, [open]);

  // Загрузка преподавателей для выбранного предмета
  useEffect(() => {
    if (!subjectId || !open) {
      setAvailableTeachers([]);
      return;
    }
    
    const loadTeachers = async () => {
      try {
        setLoadingTeachers(true);
        const response = await unifiedAPI.request<any>(`/materials/subjects/${subjectId}/teachers/`);
        
        if (response.data) {
          const teachersData = Array.isArray(response.data) ? response.data : 
                             (response.data.results || response.data.teachers || []);
          setAvailableTeachers(teachersData);
        } else {
          // Если нет преподавателей для предмета, используем всех
          setAvailableTeachers(allTeachers);
        }
      } catch (error) {
        console.error('Error loading teachers for subject:', error);
        // Fallback: используем всех преподавателей
        setAvailableTeachers(allTeachers);
      } finally {
        setLoadingTeachers(false);
      }
    };
    
    loadTeachers();
  }, [subjectId, open, allTeachers]);

  const submit = async () => {
    if (!subjectId) return;
    
    // Если преподаватель не выбран, ищем преподавателя по предмету
    let selectedTeacherId = teacherId;
    if (!selectedTeacherId && subjectId) {
      // Ищем преподавателя для выбранного предмета
      const subject = subjects.find(s => String(s.id) === subjectId);
      if (subject) {
        // Логика поиска преподавателя по предмету
        // Можно улучшить, добавив связь преподаватель-предмет
        const teacher = availableTeachers[0];
        if (teacher) {
          selectedTeacherId = String(teacher.id);
        }
      }
    }
    
    const payload: any = { subject_id: Number(subjectId) };
    if (selectedTeacherId) payload.teacher_id = Number(selectedTeacherId);
    
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
                {Array.isArray(subjects) && subjects.map(s => (
                  <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Преподаватель</Label>
            <Select value={teacherId} onValueChange={setTeacherId} disabled={!subjectId}>
              <SelectTrigger aria-label="teacher-select">
                <SelectValue placeholder={subjectId ? "Выберите преподавателя" : "Сначала выберите предмет"} />
              </SelectTrigger>
              <SelectContent>
                {loadingTeachers && (
                  <SelectItem value="loading" disabled>Загрузка...</SelectItem>
                )}
                {!loadingTeachers && Array.isArray(availableTeachers) && availableTeachers.map(t => (
                  <SelectItem key={t.id} value={String(t.id)}>{t.full_name}</SelectItem>
                ))}
                {!loadingTeachers && availableTeachers.length === 0 && subjectId && (
                  <SelectItem value="none" disabled>Нет доступных преподавателей</SelectItem>
                )}
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
