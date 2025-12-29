import React, { useMemo, useState } from 'react';
import { useTutorStudentSchedule } from '@/hooks/useTutorStudentSchedule';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Calendar, AlertCircle, Filter } from 'lucide-react';
import { LessonCard } from '@/components/scheduling/student/LessonCard';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface TutorStudentScheduleProps {
  studentId: string | null; // Может быть null, если студент не выбран
}

// Компонент для отображения фильтров (избегаем дублирования)
interface FiltersProps {
  statusFilter: string;
  subjectFilter: string;
  subjects: string[];
  lessonCount: number;
  onStatusChange: (value: string) => void;
  onSubjectChange: (value: string) => void;
}

const Filters: React.FC<FiltersProps> = ({
  statusFilter,
  subjectFilter,
  subjects,
  lessonCount,
  onStatusChange,
  onSubjectChange,
}) => (
  <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
    <div className="flex items-center gap-2">
      <Filter className="w-4 h-4 text-muted-foreground" />
      <span className="text-sm font-medium">Фильтры:</span>
    </div>
    <Select value={statusFilter} onValueChange={onStatusChange}>
      <SelectTrigger className="w-[180px]">
        <SelectValue placeholder="Статус" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">Все статусы</SelectItem>
        <SelectItem value="pending">Ожидание</SelectItem>
        <SelectItem value="confirmed">Подтверждено</SelectItem>
        <SelectItem value="completed">Завершено</SelectItem>
        <SelectItem value="cancelled">Отменено</SelectItem>
      </SelectContent>
    </Select>
    {subjects.length > 0 && (
      <Select value={subjectFilter} onValueChange={onSubjectChange}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Предмет" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все предметы</SelectItem>
          {subjects.map(subject => (
            <SelectItem key={subject} value={subject}>{subject}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    )}
    <Badge variant="secondary">{lessonCount} уроков</Badge>
  </div>
);

export const TutorStudentSchedule: React.FC<TutorStudentScheduleProps> = ({ studentId }) => {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [subjectFilter, setSubjectFilter] = useState<string>('all');

  // Безопасная функция парсинга даты и времени
  const parseDateTime = (date?: string, time?: string): number => {
    if (!date || !time) return 0;
    const dt = new Date(`${date}T${time}`);
    return isNaN(dt.getTime()) ? 0 : dt.getTime();
  };

  // Ранний возврат, если студент не выбран
  if (studentId === null) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <Calendar className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-lg font-semibold mb-2">Студент не выбран</h3>
          <p className="text-muted-foreground">
            Выберите студента для просмотра расписания
          </p>
        </CardContent>
      </Card>
    );
  }

  const { lessons, isLoading, error } = useTutorStudentSchedule(studentId);

  // Получаем уникальные предметы из уроков
  const subjects = useMemo(() => {
    const uniqueSubjects = new Map<string, string>();
    lessons.forEach(lesson => {
      if (lesson.subject_name) {
        uniqueSubjects.set(lesson.subject_name, lesson.subject_name);
      }
    });
    return Array.from(uniqueSubjects.values());
  }, [lessons]);

  const filteredLessons = useMemo(() => {
    return lessons.filter(lesson => {
      // Фильтр по статусу
      if (statusFilter !== 'all' && lesson.status !== statusFilter) {
        return false;
      }
      // Фильтр по предмету
      if (subjectFilter !== 'all' && lesson.subject_name !== subjectFilter) {
        return false;
      }
      return true;
    });
  }, [lessons, statusFilter, subjectFilter]);

  // Сортировка уроков с безопасным парсингом дат
  const sortedLessons = useMemo(() => {
    return [...filteredLessons].sort((a, b) => {
      const dateA = parseDateTime(a.date, a.start_time);
      const dateB = parseDateTime(b.date, b.start_time);
      return dateA - dateB;
    });
  }, [filteredLessons]);

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

  // Если нет уроков после фильтрации
  if (sortedLessons.length === 0 && (statusFilter !== 'all' || subjectFilter !== 'all')) {
    return (
      <div className="space-y-4">
        <Filters
          statusFilter={statusFilter}
          subjectFilter={subjectFilter}
          subjects={subjects}
          lessonCount={sortedLessons.length}
          onStatusChange={setStatusFilter}
          onSubjectChange={setSubjectFilter}
        />
        <Card>
          <CardContent className="p-12 text-center">
            <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <h3 className="text-lg font-semibold mb-2">Нет уроков по выбранным фильтрам</h3>
            <p className="text-muted-foreground">
              Попробуйте изменить фильтры
            </p>
          </CardContent>
        </Card>
      </div>
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
      <Filters
        statusFilter={statusFilter}
        subjectFilter={subjectFilter}
        subjects={subjects}
        lessonCount={sortedLessons.length}
        onStatusChange={setStatusFilter}
        onSubjectChange={setSubjectFilter}
      />

      {/* Список уроков */}
      {sortedLessons.map(lesson => (
        <LessonCard key={lesson.id} lesson={lesson} />
      ))}
    </div>
  );
};
