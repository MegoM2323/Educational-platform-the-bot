import React, { useMemo } from 'react';
import { useTutorStudentSchedule } from '@/hooks/useTutorStudentSchedule';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Calendar, AlertCircle } from 'lucide-react';
import { LessonCard } from '@/components/scheduling/student/LessonCard';

interface TutorStudentScheduleProps {
  studentId: string;
}

export const TutorStudentSchedule: React.FC<TutorStudentScheduleProps> = ({ studentId }) => {
  const { lessons, isLoading, error } = useTutorStudentSchedule(studentId);

  const sortedLessons = useMemo(() => {
    return [...lessons].sort((a, b) => {
      const dateA = new Date(`${a.date}T${a.start_time}`).getTime();
      const dateB = new Date(`${b.date}T${b.start_time}`).getTime();
      return dateA - dateB;
    });
  }, [lessons]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <Card key={i} className="overflow-hidden">
            <CardContent className="p-6">
              <div className="space-y-3">
                <Skeleton className="h-6 w-1/2" />
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50 bg-destructive/5">
        <CardContent className="p-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
            <div>
              <p className="font-semibold text-destructive">Ошибка загрузки расписания</p>
              <p className="text-sm text-muted-foreground mt-1">
                {error instanceof Error ? error.message : 'Неизвестная ошибка'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (sortedLessons.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <Calendar className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-lg font-semibold mb-2">Нет запланированных занятий</h3>
          <p className="text-muted-foreground">
            Расписание пусто. Создайте первое занятие в расписании учителя.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {sortedLessons.map(lesson => (
        <LessonCard key={lesson.id} lesson={lesson} />
      ))}
    </div>
  );
};
