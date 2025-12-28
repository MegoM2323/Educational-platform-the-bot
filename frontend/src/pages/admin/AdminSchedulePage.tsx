import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Clock, AlertCircle } from 'lucide-react';
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, isSameDay, addDays, startOfDay, endOfDay } from 'date-fns';
import { ru } from 'date-fns/locale';
import { useAdminSchedule } from '@/hooks/useAdminSchedule';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { LessonDetailModal } from '@/components/admin/LessonDetailModal';
import { useToast } from '@/hooks/use-toast';
import { AdminLesson } from '@/types/scheduling';

interface FilterOption {
  id: number;
  name: string;
}

type ViewMode = 'month' | 'week' | 'day';

export default function AdminSchedulePage() {
  const { toast } = useToast();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedTeacher, setSelectedTeacher] = useState<string>('all');
  const [selectedSubject, setSelectedSubject] = useState<string>('all');
  const [selectedStudent, setSelectedStudent] = useState<string>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('month');
  const [selectedLesson, setSelectedLesson] = useState<AdminLesson | null>(null);
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());

  // Вычисляем диапазон дат в зависимости от режима просмотра
  const getDateRange = () => {
    if (viewMode === 'month') {
      return {
        from: format(startOfMonth(currentDate), 'yyyy-MM-dd'),
        to: format(endOfMonth(currentDate), 'yyyy-MM-dd'),
      };
    } else if (viewMode === 'week') {
      const weekStart = startOfWeek(currentDate, { weekStartsOn: 1 });
      const weekEnd = endOfWeek(currentDate, { weekStartsOn: 1 });
      return {
        from: format(weekStart, 'yyyy-MM-dd'),
        to: format(weekEnd, 'yyyy-MM-dd'),
      };
    } else {
      // day mode
      return {
        from: format(currentDate, 'yyyy-MM-dd'),
        to: format(currentDate, 'yyyy-MM-dd'),
      };
    }
  };

  const dateRange = getDateRange();

  const { lessons, teachers, subjects, students, isLoading, error, filtersError, refetch } = useAdminSchedule({
    teacher_id: selectedTeacher !== 'all' ? selectedTeacher : undefined,
    subject_id: selectedSubject !== 'all' ? selectedSubject : undefined,
    student_id: selectedStudent !== 'all' ? selectedStudent : undefined,
    date_from: dateRange.from,
    date_to: dateRange.to,
  });

  // Показываем ошибку загрузки фильтров
  useEffect(() => {
    if (filtersError) {
      toast({
        variant: 'destructive',
        title: 'Ошибка загрузки фильтров',
        description: filtersError,
      });
    }
  }, [filtersError, toast]);

  // Получаем дни для отображения в зависимости от режима
  const getDaysToDisplay = () => {
    if (viewMode === 'month') {
      const start = startOfWeek(startOfMonth(currentDate), { weekStartsOn: 1 });
      const end = endOfWeek(endOfMonth(currentDate), { weekStartsOn: 1 });
      return eachDayOfInterval({ start, end });
    } else if (viewMode === 'week') {
      const start = startOfWeek(currentDate, { weekStartsOn: 1 });
      const end = endOfWeek(currentDate, { weekStartsOn: 1 });
      return eachDayOfInterval({ start, end });
    } else {
      // day mode
      return [currentDate];
    }
  };

  const days = getDaysToDisplay();

  // Группируем уроки по датам
  const lessonsByDate = lessons.reduce((acc: Record<string, AdminLesson[]>, lesson: AdminLesson) => {
    const dateKey = lesson.date;
    if (!acc[dateKey]) {
      acc[dateKey] = [];
    }
    acc[dateKey].push(lesson);
    return acc;
  }, {});

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

  const toggleDayExpanded = (dateKey: string) => {
    const newExpanded = new Set(expandedDays);
    if (newExpanded.has(dateKey)) {
      newExpanded.delete(dateKey);
    } else {
      newExpanded.add(dateKey);
    }
    setExpandedDays(newExpanded);
  };

  const getViewModeTitle = () => {
    if (viewMode === 'month') {
      return format(currentDate, 'LLLL yyyy', { locale: ru });
    } else if (viewMode === 'week') {
      const weekStart = startOfWeek(currentDate, { weekStartsOn: 1 });
      const weekEnd = endOfWeek(currentDate, { weekStartsOn: 1 });
      return `${format(weekStart, 'd MMM', { locale: ru })} - ${format(weekEnd, 'd MMM yyyy', { locale: ru })}`;
    } else {
      return format(currentDate, 'd MMMM yyyy', { locale: ru });
    }
  };

  if (error) {
    return (
      <div className="container mx-auto p-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-500 mb-4">
              <AlertCircle className="h-5 w-5" />
              <p>Ошибка загрузки расписания: {error}</p>
            </div>
            <Button type="button" onClick={() => refetch()}>
              Повторить
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Вычисляем статистику
  const todayDate = format(new Date(), 'yyyy-MM-dd');
  const todayLessons = lessonsByDate[todayDate] || [];
  const totalLessons = lessons.length;
  const pendingLessons = lessons.filter(l => l.status === 'pending').length;
  const completedLessons = lessons.filter(l => l.status === 'completed').length;
  const cancelledLessons = lessons.filter(l => l.status === 'cancelled').length;
  const confirmedLessons = lessons.filter(l => l.status === 'confirmed').length;

  return (
    <div className="container mx-auto p-4">
      {/* Карточки статистики */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">{totalLessons}</div>
              <div className="text-sm text-blue-700 mt-1">Всего занятий</div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-green-50 border-green-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">{todayLessons.length}</div>
              <div className="text-sm text-green-700 mt-1">Занятий сегодня</div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-yellow-50 border-yellow-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-yellow-600">{pendingLessons}</div>
              <div className="text-sm text-yellow-700 mt-1">Ожидают подтверждения</div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-purple-50 border-purple-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600">{confirmedLessons}</div>
              <div className="text-sm text-purple-700 mt-1">Подтверждено</div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-red-50 border-red-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-red-600">{cancelledLessons}</div>
              <div className="text-sm text-red-700 mt-1">Отменено</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5" />
              Расписание всех занятий
            </CardTitle>
            <div className="flex items-center gap-2 flex-wrap">
              <Select value={selectedTeacher} onValueChange={setSelectedTeacher}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Все преподаватели" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все преподаватели</SelectItem>
                  {teachers.map((teacher: FilterOption) => (
                    <SelectItem key={teacher.id} value={teacher.id.toString()}>
                      {teacher.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={selectedSubject} onValueChange={setSelectedSubject}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Все предметы" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все предметы</SelectItem>
                  {subjects.map((subject: FilterOption) => (
                    <SelectItem key={subject.id} value={subject.id.toString()}>
                      {subject.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={selectedStudent} onValueChange={setSelectedStudent}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Все студенты" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все студенты</SelectItem>
                  {students.map((student: FilterOption) => (
                    <SelectItem key={student.id} value={student.id.toString()}>
                      {student.name}
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
              <h2 className="text-xl font-semibold min-w-[250px] text-center">
                {getViewModeTitle()}
              </h2>
              <Button type="button" variant="outline" size="icon" onClick={navigateNext}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex gap-1">
              <Button
                type="button"
                variant={viewMode === 'month' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('month')}
              >
                Месяц
              </Button>
              <Button
                type="button"
                variant={viewMode === 'week' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('week')}
              >
                Неделя
              </Button>
              <Button
                type="button"
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
              {viewMode === 'day' ? (
                // Режим просмотра дня - показываем список уроков
                <div className="space-y-2">
                  {lessonsByDate[format(currentDate, 'yyyy-MM-dd')]?.length ? (
                    lessonsByDate[format(currentDate, 'yyyy-MM-dd')].map((lesson) => (
                      <Card
                        key={lesson.id}
                        className="p-3 cursor-pointer hover:shadow-md transition-shadow"
                        onClick={() => setSelectedLesson(lesson)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <Clock className="h-4 w-4 text-muted-foreground" />
                              <span className="font-medium">
                                {lesson.start_time.slice(0, 5)} - {lesson.end_time.slice(0, 5)}
                              </span>
                              <span className={cn('text-xs px-2 py-0.5 rounded', getStatusColor(lesson.status))}>
                                {lesson.status}
                              </span>
                            </div>
                            <p className="font-semibold">{lesson.subject_name}</p>
                            <p className="text-sm text-muted-foreground">
                              {lesson.teacher_name} → {lesson.student_name}
                            </p>
                          </div>
                        </div>
                      </Card>
                    ))
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <CalendarIcon className="h-12 w-12 mx-auto mb-2 opacity-50" />
                      <p>Нет занятий на выбранный день</p>
                    </div>
                  )}
                </div>
              ) : (
                // Режим месяца/недели - показываем сетку календаря
                <>
                  {/* Заголовки дней недели */}
                  <div className={cn('grid gap-2 mb-2', viewMode === 'week' ? 'grid-cols-7' : 'grid-cols-7')}>
                    {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((day) => (
                      <div key={day} className="text-center font-semibold text-sm">
                        {day}
                      </div>
                    ))}
                  </div>

                  {/* Дни календаря */}
                  <div className={cn('grid gap-2', viewMode === 'week' ? 'grid-cols-7' : 'grid-cols-7')}>
                    {days.map((day) => {
                      const dateKey = format(day, 'yyyy-MM-dd');
                      const dayLessons = lessonsByDate[dateKey] || [];
                      const isCurrentMonth = isSameMonth(day, currentDate);
                      const isToday = isSameDay(day, new Date());
                      const isExpanded = expandedDays.has(dateKey);
                      const visibleLessons = isExpanded ? dayLessons : dayLessons.slice(0, 3);

                      return (
                        <div
                          key={day.toString()}
                          className={cn(
                            'min-h-[100px] p-2 border rounded-lg',
                            !isCurrentMonth && 'bg-gray-50 opacity-50',
                            isToday && 'bg-blue-50 border-blue-300'
                          )}
                        >
                          <div className="font-semibold text-sm mb-1">{format(day, 'd')}</div>
                          <div className="space-y-1 text-xs">
                            {visibleLessons.map((lesson) => (
                              <div
                                key={lesson.id}
                                className={cn('p-1 rounded cursor-pointer hover:opacity-80', getStatusColor(lesson.status))}
                                onClick={() => setSelectedLesson(lesson)}
                              >
                                <div className="flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  <span>{lesson.start_time.slice(0, 5)}</span>
                                </div>
                                <div className="truncate font-medium">{lesson.subject_name}</div>
                                <div className="truncate text-[10px] opacity-75">
                                  {lesson.teacher_name} → {lesson.student_name}
                                </div>
                              </div>
                            ))}
                            {dayLessons.length > 3 && (
                              <button
                                type="button"
                                className="w-full text-center text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded py-1"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleDayExpanded(dateKey);
                                }}
                              >
                                {isExpanded ? 'Свернуть' : `+${dayLessons.length - 3} еще`}
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Пустое состояние */}
                  {lessons.length === 0 && !isLoading && (
                    <div className="text-center py-12 text-muted-foreground">
                      <CalendarIcon className="h-12 w-12 mx-auto mb-2 opacity-50" />
                      <p>Нет занятий на выбранный период</p>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Модальное окно деталей урока */}
      <LessonDetailModal lesson={selectedLesson} open={!!selectedLesson} onOpenChange={(open) => !open && setSelectedLesson(null)} />
    </div>
  );
}
