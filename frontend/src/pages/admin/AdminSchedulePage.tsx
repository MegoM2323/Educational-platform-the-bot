import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Calendar as CalendarIcon, Filter, ChevronLeft, ChevronRight, Clock, User, BookOpen } from 'lucide-react';
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, isSameDay, parseISO } from 'date-fns';
import { ru } from 'date-fns/locale';
import { useAdminSchedule } from '@/hooks/useAdminSchedule';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface Lesson {
  id: string;
  date: string;
  start_time: string;
  end_time: string;
  teacher: number;
  teacher_name: string;
  student: number;
  student_name: string;
  subject: number;
  subject_name: string;
  status: 'pending' | 'confirmed' | 'completed' | 'cancelled';
  description?: string;
  telemost_link?: string;
}

export default function AdminSchedulePage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedTeacher, setSelectedTeacher] = useState<string>('all');
  const [selectedSubject, setSelectedSubject] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'month' | 'week' | 'day'>('month');

  const { lessons, teachers, subjects, isLoading, error, refetch } = useAdminSchedule({
    teacher_id: selectedTeacher !== 'all' ? selectedTeacher : undefined,
    subject_id: selectedSubject !== 'all' ? selectedSubject : undefined,
    date_from: format(startOfMonth(currentDate), 'yyyy-MM-dd'),
    date_to: format(endOfMonth(currentDate), 'yyyy-MM-dd'),
  });

  // Получаем дни для отображения в календаре
  const getDaysToDisplay = () => {
    const start = startOfWeek(startOfMonth(currentDate), { weekStartsOn: 1 });
    const end = endOfWeek(endOfMonth(currentDate), { weekStartsOn: 1 });
    return eachDayOfInterval({ start, end });
  };

  const days = getDaysToDisplay();

  // Группируем уроки по датам
  const lessonsByDate = lessons?.reduce((acc: Record<string, Lesson[]>, lesson: Lesson) => {
    const dateKey = lesson.date;
    if (!acc[dateKey]) {
      acc[dateKey] = [];
    }
    acc[dateKey].push(lesson);
    return acc;
  }, {}) || {};

  const navigatePrev = () => {
    const newDate = new Date(currentDate);
    if (viewMode === 'month') {
      newDate.setMonth(newDate.getMonth() - 1);
    } else if (viewMode === 'week') {
      newDate.setDate(newDate.getDate() - 7);
    } else {
      newDate.setDate(newDate.getDate() - 1);
    }
    setCurrentDate(newDate);
  };

  const navigateNext = () => {
    const newDate = new Date(currentDate);
    if (viewMode === 'month') {
      newDate.setMonth(newDate.getMonth() + 1);
    } else if (viewMode === 'week') {
      newDate.setDate(newDate.getDate() + 7);
    } else {
      newDate.setDate(newDate.getDate() + 1);
    }
    setCurrentDate(newDate);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'confirmed':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-blue-100 text-blue-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (error) {
    return (
      <div className="container mx-auto p-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-500">Ошибка загрузки расписания: {error}</p>
            <Button type="button" onClick={() => refetch()} className="mt-4">
              Повторить
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5" />
              Расписание всех занятий
            </CardTitle>
            <div className="flex items-center gap-2">
              <Select value={selectedTeacher} onValueChange={setSelectedTeacher}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Все преподаватели" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все преподаватели</SelectItem>
                  {teachers?.map((teacher: any) => (
                    <SelectItem key={teacher.id} value={teacher.id.toString()}>
                      {teacher.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={selectedSubject} onValueChange={setSelectedSubject}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Все предметы" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все предметы</SelectItem>
                  {subjects?.map((subject: any) => (
                    <SelectItem key={subject.id} value={subject.id.toString()}>
                      {subject.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {/* Навигация по календарю */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Button type="button" variant="outline" size="icon" onClick={navigatePrev}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <h2 className="text-xl font-semibold">
                {format(currentDate, 'LLLL yyyy', { locale: ru })}
              </h2>
              <Button type="button" variant="outline" size="icon" onClick={navigateNext}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex gap-1">
              <Button type="button"
                variant={viewMode === 'month' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('month')}
              >
                Месяц
              </Button>
              <Button type="button"
                variant={viewMode === 'week' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('week')}
              >
                Неделя
              </Button>
              <Button type="button"
                variant={viewMode === 'day' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('day')}
              >
                День
              </Button>
            </div>
          </div>

          {/* Календарь */}
          {isLoading ? (
            <div className="grid grid-cols-7 gap-2">
              {[...Array(35)].map((_, i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
          ) : (
            <>
              {/* Заголовки дней недели */}
              <div className="grid grid-cols-7 gap-2 mb-2">
                {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((day) => (
                  <div key={day} className="text-center font-semibold text-sm">
                    {day}
                  </div>
                ))}
              </div>

              {/* Дни календаря */}
              <div className="grid grid-cols-7 gap-2">
                {days.map((day) => {
                  const dateKey = format(day, 'yyyy-MM-dd');
                  const dayLessons = lessonsByDate[dateKey] || [];
                  const isCurrentMonth = isSameMonth(day, currentDate);
                  const isToday = isSameDay(day, new Date());

                  return (
                    <div
                      key={day.toString()}
                      className={cn(
                        "min-h-[100px] p-2 border rounded-lg",
                        !isCurrentMonth && "bg-gray-50 opacity-50",
                        isToday && "bg-blue-50 border-blue-300"
                      )}
                    >
                      <div className="font-semibold text-sm mb-1">
                        {format(day, 'd')}
                      </div>
                      <div className="space-y-1 text-xs">
                        {dayLessons.slice(0, 3).map((lesson) => (
                          <div
                            key={lesson.id}
                            className={cn(
                              "p-1 rounded",
                              getStatusColor(lesson.status)
                            )}
                          >
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              <span>{lesson.start_time.slice(0, 5)}</span>
                            </div>
                            <div className="truncate font-medium">
                              {lesson.subject_name}
                            </div>
                            <div className="truncate text-[10px] opacity-75">
                              {lesson.teacher_name} → {lesson.student_name}
                            </div>
                          </div>
                        ))}
                        {dayLessons.length > 3 && (
                          <div className="text-center text-gray-500">
                            +{dayLessons.length - 3} еще
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}