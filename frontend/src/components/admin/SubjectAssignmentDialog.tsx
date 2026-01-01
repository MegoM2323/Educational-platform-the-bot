import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

interface Subject {
  id: number;
  name: string;
  description?: string;
  color?: string;
}

interface Teacher {
  id: number;
  user: {
    id: number;
    full_name: string;
    email: string;
  };
}

interface SubjectAssignment {
  subject_id: number;
  teacher_id: number;
}

interface SubjectAssignmentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  studentId: number;
  studentName: string;
  onSuccess: () => void;
}

export const SubjectAssignmentDialog = ({
  open,
  onOpenChange,
  studentId,
  studentName,
  onSuccess,
}: SubjectAssignmentDialogProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [assignments, setAssignments] = useState<SubjectAssignment[]>([
    { subject_id: 0, teacher_id: 0 },
  ]);

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open]);

  const loadData = async () => {
    try {
      const [subjectsRes, teachersRes] = await Promise.all([
        unifiedAPI.request<{ success: boolean; count: number; results: Subject[] }>(
          '/materials/subjects/all/'
        ),
        unifiedAPI.request<Teacher[]>('/auth/staff/?role=teacher'),
      ]);

      if (subjectsRes.success && subjectsRes.data) {
        // Backend returns {success: true, count: 5, results: [...]}
        // or can return array directly, or nested structure
        const subjectsData = subjectsRes.data as any;
        let subjectsArray: Subject[] = [];
        if (Array.isArray(subjectsData)) {
          subjectsArray = subjectsData;
        } else if (subjectsData?.results && Array.isArray(subjectsData.results)) {
          subjectsArray = subjectsData.results;
        } else if (subjectsData?.data && Array.isArray(subjectsData.data)) {
          subjectsArray = subjectsData.data;
        } else if (subjectsData?.data?.results && Array.isArray(subjectsData.data.results)) {
          subjectsArray = subjectsData.data.results;
        }
        setSubjects(subjectsArray);
      }

      if (teachersRes.success && teachersRes.data) {
        // Backend returns {results: [...]} for /auth/staff/?role=teacher
        // or can return array directly, or nested structure
        const teachersData = teachersRes.data as any;
        let teachersArray: Teacher[] = [];
        if (Array.isArray(teachersData)) {
          teachersArray = teachersData;
        } else if (teachersData?.results && Array.isArray(teachersData.results)) {
          teachersArray = teachersData.results;
        } else if (teachersData?.data && Array.isArray(teachersData.data)) {
          teachersArray = teachersData.data;
        } else if (teachersData?.data?.results && Array.isArray(teachersData.data.results)) {
          teachersArray = teachersData.data.results;
        }
        setTeachers(teachersArray);
      }
    } catch (err) {
      logger.error('Error loading data:', err);
      toast.error('Ошибка загрузки данных');
    }
  };

  const addAssignment = () => {
    setAssignments([...assignments, { subject_id: 0, teacher_id: 0 }]);
  };

  const removeAssignment = (index: number) => {
    if (assignments.length === 1) {
      toast.error('Должно быть хотя бы одно назначение');
      return;
    }
    setAssignments(assignments.filter((_, i) => i !== index));
  };

  const updateAssignment = (index: number, field: 'subject_id' | 'teacher_id', value: number) => {
    const updated = [...assignments];
    updated[index][field] = value;
    setAssignments(updated);
  };

  const getAvailableTeachers = (subjectId: number): Teacher[] => {
    if (!subjectId) return teachers;
    // In a real implementation, filter teachers by subject
    // For now, return all teachers
    return teachers;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate all assignments
    for (let i = 0; i < assignments.length; i++) {
      const assignment = assignments[i];
      if (!assignment.subject_id || !assignment.teacher_id) {
        setError(`Назначение ${i + 1}: выберите предмет и преподавателя`);
        return;
      }
    }

    // Check for duplicate subjects
    const subjectIds = assignments.map((a) => a.subject_id);
    const uniqueSubjects = new Set(subjectIds);
    if (subjectIds.length !== uniqueSubjects.size) {
      setError('Нельзя назначать один предмет несколько раз');
      return;
    }

    setLoading(true);

    try {
      // Assign each subject-teacher pair
      const promises = assignments.map((assignment) =>
        unifiedAPI.request('/materials/tutor/students/assign-subject/', {
          method: 'POST',
          body: JSON.stringify({
            student_id: studentId,
            subject_id: assignment.subject_id,
            teacher_id: assignment.teacher_id,
          }),
        })
      );

      const results = await Promise.allSettled(promises);

      const failures = results.filter((r) => r.status === 'rejected');
      if (failures.length > 0) {
        setError(`Не удалось назначить ${failures.length} предмет(ов)`);
        toast.error(`Назначено ${results.length - failures.length} из ${results.length} предметов`);
      } else {
        toast.success(`Назначено ${assignments.length} предмет(ов) для ${studentName}`);
        onSuccess();
        onOpenChange(false);
      }
    } catch (err: any) {
      setError(err?.message || 'Произошла ошибка при назначении предметов');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Назначить предметы студенту: {studentName}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <p className="text-sm text-muted-foreground">
              Выберите предметы и преподавателей для назначения студенту
            </p>

            {assignments.map((assignment, index) => (
              <div key={index} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium">Назначение {index + 1}</h4>
                  {assignments.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeAssignment(index)}
                      disabled={loading}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`subject-${index}`}>Предмет *</Label>
                    <Select
                      value={assignment.subject_id.toString()}
                      onValueChange={(value) =>
                        updateAssignment(index, 'subject_id', parseInt(value))
                      }
                      disabled={loading}
                    >
                      <SelectTrigger id={`subject-${index}`}>
                        <SelectValue placeholder="Выберите предмет" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0" disabled>
                          Выберите предмет
                        </SelectItem>
                        {subjects.map((subject) => (
                          <SelectItem key={subject.id} value={subject.id.toString()}>
                            {subject.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`teacher-${index}`}>Преподаватель *</Label>
                    <Select
                      value={assignment.teacher_id.toString()}
                      onValueChange={(value) =>
                        updateAssignment(index, 'teacher_id', parseInt(value))
                      }
                      disabled={loading || !assignment.subject_id}
                    >
                      <SelectTrigger id={`teacher-${index}`}>
                        <SelectValue placeholder="Выберите преподавателя" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0" disabled>
                          Выберите преподавателя
                        </SelectItem>
                        {getAvailableTeachers(assignment.subject_id).map((teacher) => (
                          <SelectItem key={teacher.id} value={teacher.user.id.toString()}>
                            {teacher.user.full_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            ))}

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addAssignment}
              disabled={loading}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Добавить предмет
            </Button>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Отмена
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Назначение...' : 'Назначить предметы'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
