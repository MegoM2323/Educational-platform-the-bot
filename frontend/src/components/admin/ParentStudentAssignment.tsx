import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { adminAPI, Parent } from '@/integrations/api/adminAPI';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import { toast } from 'sonner';

interface StudentOption {
  id: number;
  name: string;
  grade?: string;
  currentParent?: string;
}

interface ParentStudentAssignmentProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export const ParentStudentAssignment = ({ open, onOpenChange, onSuccess }: ParentStudentAssignmentProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [parents, setParents] = useState<Parent[]>([]);
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [selectedParentId, setSelectedParentId] = useState<string>('');
  const [selectedStudentIds, setSelectedStudentIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [parentsResponse, studentsResponse] = await Promise.all([
        adminAPI.listParents(),
        adminAPI.getStudents(),
      ]);

      if (parentsResponse.success && parentsResponse.data) {
        setParents(parentsResponse.data.results || []);
      }

      if (studentsResponse.success && studentsResponse.data) {
        const studentsList = studentsResponse.data?.results?.map((s) => ({
          id: s.id,
          name: s.user.full_name,
          grade: s.grade,
          currentParent: s.parent_id ? `ID: ${s.parent_id}` : 'Не назначен',
        })) || [];
        setStudents(studentsList);
      }
    } catch (err) {
      logger.error('Error loading data:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  };

  const handleParentChange = (parentId: string) => {
    setSelectedParentId(parentId);
    setSelectedStudentIds(new Set());
    setError(null);
    setSuccess(false);
  };

  const handleStudentToggle = (studentId: number) => {
    const newSelectedIds = new Set(selectedStudentIds);
    if (newSelectedIds.has(studentId)) {
      newSelectedIds.delete(studentId);
    } else {
      newSelectedIds.add(studentId);
    }
    setSelectedStudentIds(newSelectedIds);
  };

  const handleSelectAll = () => {
    if (selectedStudentIds.size === students.length) {
      setSelectedStudentIds(new Set());
    } else {
      setSelectedStudentIds(new Set(students.map((s) => s.id)));
    }
  };

  const handleSubmit = async () => {
    if (!selectedParentId) {
      setError('Выберите родителя');
      return;
    }

    if (selectedStudentIds.size === 0) {
      setError('Выберите хотя бы одного студента');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const parentId = parseInt(selectedParentId);
      const studentIds = Array.from(selectedStudentIds);

      const response = await adminAPI.assignParentToStudents(parentId, studentIds);

      if (response.success) {
        setSuccess(true);
        toast.success(response.data?.message || 'Студенты успешно назначены родителю');
        setTimeout(() => {
          onSuccess();
          handleClose();
        }, 1500);
      } else {
        setError(response.error || 'Не удалось назначить студентов');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Произошла ошибка';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setSelectedParentId('');
    setSelectedStudentIds(new Set());
    setError(null);
    setSuccess(false);
    onOpenChange(false);
  };

  const selectedParent = parents.find((p) => p.id === parseInt(selectedParentId));

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Назначить студентов родителю</DialogTitle>
        </DialogHeader>

        {success ? (
          <div className="space-y-4 py-4">
            <Alert className="bg-green-50 border-green-200">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                Студенты успешно назначены родителю!
              </AlertDescription>
            </Alert>
          </div>
        ) : (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="parent">Выберите родителя *</Label>
              <Select value={selectedParentId} onValueChange={handleParentChange} disabled={loading}>
                <SelectTrigger id="parent">
                  <SelectValue placeholder="Выберите родителя" />
                </SelectTrigger>
                <SelectContent>
                  {parents.map((parent) => (
                    <SelectItem key={parent.id} value={parent.id.toString()}>
                      {parent.user.full_name}
                      {parent.children_count ? ` (${parent.children_count} детей)` : ' (нет детей)'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedParent && (
              <div className="bg-muted p-3 rounded-md">
                <p className="text-sm">
                  <strong>{selectedParent.user.full_name}</strong> – Email: {selectedParent.user.email}
                </p>
              </div>
            )}

            {selectedParentId && (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Label>Студенты для назначения:</Label>
                  <Button type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleSelectAll}
                    disabled={loading || students.length === 0}
                  >
                    {selectedStudentIds.size === students.length ? 'Убрать все' : 'Выбрать все'}
                  </Button>
                </div>

                <div className="border rounded-md p-3 max-h-[400px] overflow-y-auto space-y-2">
                  {students.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">Студентов не найдено</p>
                  ) : (
                    students.map((student) => (
                      <div key={student.id} className="flex items-center space-x-3 p-2 hover:bg-muted rounded">
                        <Checkbox
                          id={`student-${student.id}`}
                          checked={selectedStudentIds.has(student.id)}
                          onCheckedChange={() => handleStudentToggle(student.id)}
                          disabled={loading}
                        />
                        <label
                          htmlFor={`student-${student.id}`}
                          className="flex-1 cursor-pointer text-sm flex items-center space-x-2"
                        >
                          <span className="font-medium">{student.name}</span>
                          {student.grade && <span className="text-muted-foreground">({student.grade} класс)</span>}
                        </label>
                        <span className="text-xs text-muted-foreground">{student.currentParent}</span>
                      </div>
                    ))
                  )}
                </div>

                <div className="text-sm text-muted-foreground">
                  Выбрано: {selectedStudentIds.size} из {students.length}
                </div>
              </div>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {!success && (
          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={loading}>
              Отмена
            </Button>
            <Button type="button"
              onClick={handleSubmit}
              disabled={loading || !selectedParentId || selectedStudentIds.size === 0}
            >
              {loading ? 'Назначение...' : 'Назначить'}
            </Button>
          </DialogFooter>
        )}

        {success && (
          <DialogFooter>
            <Button type="button" onClick={handleClose}>Закрыть</Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
};
