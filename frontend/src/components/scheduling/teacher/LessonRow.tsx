import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ExternalLink, Edit2, Trash2, Clock } from 'lucide-react';
import { Lesson } from '@/types/scheduling';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

interface LessonRowProps {
  lesson: Lesson;
  onEdit?: () => void;
  onDelete?: () => void;
  deletingId?: string | null;
}

export const LessonRow: React.FC<LessonRowProps> = ({
  lesson,
  onEdit,
  onDelete,
  deletingId = null,
}) => {
  // Проверяем, удаляется ли именно этот урок
  const isDeleting = deletingId === lesson.id;
  const formatDate = (date: string): string => {
    try {
      return format(new Date(date), 'EEE, d MMM', { locale: ru });
    } catch {
      return date;
    }
  };

  const formatTime = (time: string): string => {
    // time is "HH:MM:SS" format, return "HH:MM"
    return time.slice(0, 5);
  };

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
        <div className="flex-1 space-y-2">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <p className="font-semibold text-lg">{lesson.student_name}</p>
              <p className="text-sm text-muted-foreground">{lesson.subject_name}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span>
              {formatDate(lesson.date)} • {formatTime(lesson.start_time)} - {formatTime(lesson.end_time)}
            </span>
          </div>

          {lesson.description && (
            <p className="text-sm text-muted-foreground mt-2">{lesson.description}</p>
          )}

          <div className="flex flex-wrap gap-2 mt-3">
            {lesson.status && (
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  lesson.status === 'confirmed'
                    ? 'bg-blue-100 text-blue-800'
                    : lesson.status === 'pending'
                      ? 'bg-yellow-100 text-yellow-800'
                      : lesson.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                }`}
              >
                {lesson.status}
              </span>
            )}
          </div>
        </div>

        <div className="flex gap-2 flex-wrap sm:flex-nowrap">
          {lesson.telemost_link && (
            <Button type="button"
              size="sm"
              variant="outline"
              asChild
            >
              <a href={lesson.telemost_link} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Join</span>
              </a>
            </Button>
          )}
          {onEdit && (
            <Button type="button"
              size="sm"
              variant="outline"
              onClick={onEdit}
              disabled={isDeleting}
            >
              <Edit2 className="w-4 h-4" />
              <span className="hidden sm:inline ml-1">Edit</span>
            </Button>
          )}
          {onDelete && (
            <Button type="button"
              size="sm"
              variant="destructive"
              onClick={onDelete}
              disabled={isDeleting}
            >
              <Trash2 className="w-4 h-4" />
              <span className="hidden sm:inline ml-1">Delete</span>
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
};
