/**
 * Lesson Delete Confirmation Dialog with Cascade Details
 * Показывает подробности каскадного удаления перед подтверждением
 */

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2, Trash2, Users, Link as LinkIcon } from 'lucide-react';

interface LessonDeleteConfirmDialogProps {
  /** Открыт ли диалог */
  open: boolean;
  /** Callback при изменении состояния открытия */
  onOpenChange: (open: boolean) => void;
  /** ID урока для удаления */
  lessonId: number;
  /** Название урока */
  lessonName: string;
  /** Количество затронутых зависимостей (рассчитывается из graph.dependencies) */
  affectedDependencies: number;
  /** Количество затронутых студентов (передается из родителя) */
  affectedStudents?: number;
  /** Callback при подтверждении удаления */
  onConfirm: () => Promise<void>;
  /** Callback при отмене */
  onCancel?: () => void;
}

export const LessonDeleteConfirmDialog: React.FC<LessonDeleteConfirmDialogProps> = ({
  open,
  onOpenChange,
  lessonId,
  lessonName,
  affectedDependencies,
  affectedStudents = 0,
  onConfirm,
  onCancel,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setIsDeleting(true);
    setError(null);

    try {
      await onConfirm();
      // Успех - диалог закроется через onOpenChange из родителя
      onOpenChange(false);
    } catch (err) {
      // Показать ошибку в диалоге
      const errorMessage = err instanceof Error ? err.message : 'Неизвестная ошибка при удалении урока';
      setError(errorMessage);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancel = () => {
    if (isDeleting) return; // Нельзя отменить во время удаления

    setError(null);
    onCancel?.();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Trash2 className="h-5 w-5 text-destructive" />
            Удалить урок из графа?
          </DialogTitle>
          <DialogDescription>
            Это действие приведет к удалению урока и всех связанных данных
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Основное предупреждение */}
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>ВНИМАНИЕ:</strong> Вы собираетесь удалить урок <strong>"{lessonName}"</strong> из графа знаний.
            </AlertDescription>
          </Alert>

          {/* Детали каскадного удаления */}
          <div className="space-y-3 text-sm">
            <p className="font-medium text-muted-foreground">Что будет удалено:</p>

            <div className="space-y-2 pl-4">
              {/* Зависимости */}
              {affectedDependencies > 0 && (
                <div className="flex items-center gap-2">
                  <LinkIcon className="h-4 w-4 text-orange-500" />
                  <span>
                    <strong>{affectedDependencies}</strong> {affectedDependencies === 1 ? 'зависимость' : affectedDependencies > 4 ? 'зависимостей' : 'зависимости'}
                  </span>
                </div>
              )}

              {/* Затронутые студенты */}
              {affectedStudents > 0 && (
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-blue-500" />
                  <span>
                    Прогресс <strong>{affectedStudents}</strong> {affectedStudents === 1 ? 'студента' : affectedStudents > 4 ? 'студентов' : 'студентов'} будет очищен
                  </span>
                </div>
              )}

              {/* Если нет зависимостей и студентов */}
              {affectedDependencies === 0 && affectedStudents === 0 && (
                <p className="text-muted-foreground italic">
                  Урок не имеет зависимостей и не используется студентами
                </p>
              )}
            </div>

            {/* Дополнительное предупреждение */}
            <Alert className="mt-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                Это действие будет сохранено только после нажатия кнопки <strong>"Сохранить"</strong> в редакторе графа.
              </AlertDescription>
            </Alert>
          </div>

          {/* Отображение ошибки */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={isDeleting}
          >
            Отмена
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleConfirm}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Удаление...
              </>
            ) : (
              <>
                <Trash2 className="h-4 w-4 mr-2" />
                Удалить
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
