import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, Clock, User, BookOpen, ExternalLink, FileText } from 'lucide-react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { AdminLesson } from '@/types/scheduling';

interface LessonDetailModalProps {
  lesson: AdminLesson | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
};

const statusLabels: Record<string, string> = {
  pending: 'Ожидание подтверждения',
  confirmed: 'Подтверждено',
  completed: 'Завершено',
  cancelled: 'Отменено',
};

export const LessonDetailModal: React.FC<LessonDetailModalProps> = ({
  lesson,
  open,
  onOpenChange,
}) => {
  if (!lesson) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <DialogTitle className="text-2xl">{lesson.subject_name}</DialogTitle>
              <DialogDescription className="mt-1">
                Детали занятия
              </DialogDescription>
            </div>
            <Badge className={statusColors[lesson.status] || statusColors.pending}>
              {statusLabels[lesson.status] || 'Неизвестно'}
            </Badge>
          </div>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* Дата и время */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <Calendar className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">Дата</p>
                <p className="text-base font-semibold">
                  {format(new Date(lesson.date), 'd MMMM yyyy', { locale: ru })}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <Clock className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-muted-foreground">Время</p>
                <p className="text-base font-semibold">
                  {lesson.start_time.slice(0, 5)} - {lesson.end_time.slice(0, 5)}
                </p>
              </div>
            </div>
          </div>

          {/* Участники */}
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <User className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Преподаватель</p>
                <p className="text-base font-semibold">{lesson.teacher_name}</p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <User className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Студент</p>
                <p className="text-base font-semibold">{lesson.student_name}</p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <BookOpen className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground">Предмет</p>
                <p className="text-base font-semibold">{lesson.subject_name}</p>
              </div>
            </div>
          </div>

          {/* Описание */}
          {lesson.description && (
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <FileText className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-muted-foreground mb-1">Описание</p>
                <p className="text-sm">{lesson.description}</p>
              </div>
            </div>
          )}

          {/* Ссылка на Telemost */}
          {lesson.telemost_link && (
            <div className="pt-2">
              <Button type="button" asChild className="w-full">
                <a href={lesson.telemost_link} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Присоединиться к уроку
                </a>
              </Button>
            </div>
          )}

          {/* Метаданные */}
          {(lesson.created_at || lesson.updated_at) && (
            <div className="pt-4 border-t text-xs text-muted-foreground space-y-1">
              {lesson.created_at && (
                <p>
                  Создано: {format(new Date(lesson.created_at), 'd MMMM yyyy, HH:mm', { locale: ru })}
                </p>
              )}
              {lesson.updated_at && lesson.updated_at !== lesson.created_at && (
                <p>
                  Обновлено: {format(new Date(lesson.updated_at), 'd MMMM yyyy, HH:mm', { locale: ru })}
                </p>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
