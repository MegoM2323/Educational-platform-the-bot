import React from 'react';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Calendar, Clock, BookOpen, ExternalLink, MapPin } from "lucide-react";
import { Lesson } from '@/types/scheduling';
import { format } from "date-fns";
import { ru } from "date-fns/locale";

interface LessonCardProps {
  lesson: Lesson;
}

export const LessonCard: React.FC<LessonCardProps> = ({ lesson }) => {
  const lessonDateTime = new Date(`${lesson.date}T${lesson.start_time}`);
  const isUpcoming = lessonDateTime > new Date();

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

  // Безопасное получение инициалов преподавателя
  const getInitials = (name?: string): string => {
    if (!name) return 'T';
    const parts = name.trim().split(' ').filter(Boolean);
    if (parts.length === 0) return 'T';
    if (parts.length === 1) return parts[0][0].toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  return (
    <Card className={`border-l-4 overflow-hidden transition-shadow hover:shadow-md ${
      isUpcoming ? 'border-l-blue-500' : 'border-l-gray-400'
    }`}>
      <CardHeader className="pb-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="flex gap-3 flex-1 min-w-0">
            <Avatar className="w-10 h-10 flex-shrink-0">
              <AvatarFallback className="bg-blue-100 text-blue-900 text-xs font-bold">
                {getInitials(lesson.teacher_name)}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-base truncate">{lesson.subject_name || 'Занятие'}</h3>
              <p className="text-sm text-muted-foreground truncate">
                Преподаватель: {lesson.teacher_name || 'Не указан'}
              </p>
            </div>
          </div>
          <Badge variant="outline" className={`flex-shrink-0 ${statusColors[lesson.status] || statusColors.pending}`}>
            {statusLabels[lesson.status] || 'Неизвестно'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Date and Time */}
        <div className="grid sm:grid-cols-2 gap-3">
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            <span>{format(new Date(lesson.date), 'd MMMM yyyy', { locale: ru })}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            <span>{lesson.start_time.slice(0, 5)} - {lesson.end_time.slice(0, 5)}</span>
          </div>
        </div>

        {/* Description */}
        {lesson.description && (
          <div className="pt-2 border-t">
            <p className="text-sm text-muted-foreground">{lesson.description}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-2 pt-2">
          {lesson.telemost_link && (
            <Button type="button"
              asChild
              size="sm"
              className="flex-1"
            >
              <a href={lesson.telemost_link} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4 mr-2" />
                <span className="hidden xs:inline">Присоединиться к уроку</span>
                <span className="xs:hidden">К уроку</span>
              </a>
            </Button>
          )}
          {!lesson.telemost_link && (
            <div className="flex-1 flex items-center text-xs text-muted-foreground bg-muted rounded px-3 py-2">
              <MapPin className="w-4 h-4 mr-2 flex-shrink-0" />
              Место встречи не указано
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
