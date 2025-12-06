import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { SubjectMultiSelect, Subject } from './SubjectMultiSelect';
import { StaffListItem, staffService } from '@/services/staffService';
import { Loader2, AlertCircle } from 'lucide-react';

interface EditTeacherSubjectsDialogProps {
  teacher: StaffListItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export const EditTeacherSubjectsDialog = ({
  teacher,
  open,
  onOpenChange,
  onSuccess,
}: EditTeacherSubjectsDialogProps) => {
  const [selectedSubjects, setSelectedSubjects] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Инициализация выбранных предметов при открытии диалога
  useEffect(() => {
    if (open && teacher.subjects) {
      setSelectedSubjects(teacher.subjects.map(s => s.id));
      setError(null);
    }
  }, [open, teacher]);

  const handleSave = async () => {
    try {
      setLoading(true);
      setError(null);

      // Валидация: проверяем, что выбран хотя бы один предмет
      if (selectedSubjects.length === 0) {
        setError('Выберите хотя бы один предмет');
        return;
      }

      await staffService.updateTeacherSubjects(teacher.id, selectedSubjects);

      // Успешное сохранение
      onSuccess();
      onOpenChange(false);
    } catch (err: any) {
      logger.error('Error updating teacher subjects:', err);
      setError(err.message || 'Ошибка сохранения предметов');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setError(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Редактировать предметы преподавателя</DialogTitle>
          <DialogDescription>
            {teacher.user.first_name} {teacher.user.last_name} ({teacher.user.email})
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <SubjectMultiSelect
            value={selectedSubjects}
            onChange={setSelectedSubjects}
            disabled={loading}
          />
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={loading}
          >
            Отмена
          </Button>
          <Button
            onClick={handleSave}
            disabled={loading || selectedSubjects.length === 0}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Сохранение...
              </>
            ) : (
              'Сохранить'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
