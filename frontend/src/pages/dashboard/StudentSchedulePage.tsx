import React, { useState, useMemo } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { useStudentSchedule } from "@/hooks/useStudentSchedule";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Calendar, Filter } from "lucide-react";
import { LessonCard } from "@/components/scheduling/student/LessonCard";

/**
 * Безопасный парсинг даты и времени с обработкой ошибок
 * Возвращает null для невалидных дат вместо падения приложения
 */
const parseDateTime = (date: string, time: string): Date | null => {
  try {
    const dt = new Date(`${date}T${time}`);
    return isNaN(dt.getTime()) ? null : dt;
  } catch {
    return null;
  }
};

const StudentSchedulePage: React.FC = () => {
  const { lessons, isLoading, error } = useStudentSchedule();

  const [activeTab, setActiveTab] = useState<'upcoming' | 'past'>('upcoming');
  const [selectedSubject, setSelectedSubject] = useState<string>('all');
  const [selectedTeacher, setSelectedTeacher] = useState<string>('all');

  const filteredLessons = useMemo(() => {
    // Создаём актуальную метку времени внутри useMemo для правильной фильтрации
    // Округляем до минуты для оптимизации пересчётов (изменяется раз в минуту)
    const now = new Date();
    now.setSeconds(0, 0);
    const nowTimestamp = now.getTime();

    return lessons.filter(lesson => {
      // Безопасный парсинг даты с обработкой невалидных значений
      const lessonDateTime = parseDateTime(lesson.date, lesson.start_time);

      // Пропускаем уроки с невалидными датами
      if (!lessonDateTime) {
        console.warn(`Invalid date/time for lesson ${lesson.id}: ${lesson.date} ${lesson.start_time}`);
        return false;
      }

      // Фильтрация по времени: предстоящие vs прошедшие
      const isUpcoming = lessonDateTime.getTime() > nowTimestamp;

      if (activeTab === 'upcoming' && !isUpcoming) return false;
      if (activeTab === 'past' && isUpcoming) return false;

      // Фильтрация по предмету
      if (selectedSubject && selectedSubject !== 'all' && lesson.subject_name !== selectedSubject) return false;

      // Фильтрация по преподавателю
      if (selectedTeacher && selectedTeacher !== 'all' && lesson.teacher_name !== selectedTeacher) return false;

      return true;
    }).sort((a, b) => {
      // Сортировка с безопасным парсингом дат
      const dateA = parseDateTime(a.date, a.start_time);
      const dateB = parseDateTime(b.date, b.start_time);

      // Невалидные даты в конец списка
      if (!dateA) return 1;
      if (!dateB) return -1;

      // Предстоящие: от раннего к позднему, Прошедшие: от позднего к раннему
      return activeTab === 'upcoming'
        ? dateA.getTime() - dateB.getTime()
        : dateB.getTime() - dateA.getTime();
    });
  }, [lessons, activeTab, selectedSubject, selectedTeacher]);

  const uniqueSubjects = useMemo(() => {
    return [...new Set(lessons.map(l => l.subject_name).filter(Boolean))].sort();
  }, [lessons]);

  const uniqueTeachers = useMemo(() => {
    return [...new Set(lessons.map(l => l.teacher_name).filter(Boolean))].sort();
  }, [lessons]);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <StudentSidebar />
        <SidebarInset className="flex-1">
          <header className="sticky top-0 z-10 flex h-16 items-center border-b bg-background px-6">
            <SidebarTrigger />
            <h1 className="ml-4 text-xl font-semibold flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Мое расписание
            </h1>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              {/* Filters */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Filter className="w-5 h-5" />
                    <CardTitle className="text-lg">Фильтры</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Предмет</label>
                      <Select value={selectedSubject} onValueChange={setSelectedSubject}>
                        <SelectTrigger>
                          <SelectValue placeholder="Все предметы" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Все предметы</SelectItem>
                          {uniqueSubjects.map(subject => (
                            <SelectItem key={subject} value={subject}>{subject}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Преподаватель</label>
                      <Select value={selectedTeacher} onValueChange={setSelectedTeacher}>
                        <SelectTrigger>
                          <SelectValue placeholder="Все преподаватели" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Все преподаватели</SelectItem>
                          {uniqueTeachers.map(teacher => (
                            <SelectItem key={teacher} value={teacher}>{teacher}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Tabs */}
              <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'upcoming' | 'past')}>
                <TabsList className="grid w-full sm:w-auto grid-cols-2">
                  <TabsTrigger value="upcoming">Предстоящие</TabsTrigger>
                  <TabsTrigger value="past">Прошедшие</TabsTrigger>
                </TabsList>

                <TabsContent value={activeTab} className="space-y-4 mt-6">
                  {isLoading ? (
                    <div className="space-y-4">
                      <p className="text-sm text-muted-foreground mb-4">Загрузка расписания...</p>
                      {[...Array(3)].map((_, i) => (
                        <Card key={`lesson-skeleton-${i}`} className="overflow-hidden">
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
                  ) : error ? (
                    <Card className="border-destructive">
                      <CardContent className="p-12 text-center">
                        <div className="mx-auto mb-4 w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
                          <Calendar className="w-6 h-6 text-destructive" />
                        </div>
                        <h3 className="text-lg font-semibold mb-2 text-destructive">
                          Ошибка загрузки расписания
                        </h3>
                        <p className="text-muted-foreground mb-6">
                          {error instanceof Error ? error.message : 'Не удалось загрузить расписание. Попробуйте обновить страницу.'}
                        </p>
                        <Button type="button"
                          onClick={() => window.location.reload()}
                          variant="outline"
                        >
                          Обновить страницу
                        </Button>
                      </CardContent>
                    </Card>
                  ) : filteredLessons.length === 0 ? (
                    <Card>
                      <CardContent className="p-12 text-center">
                        <Calendar className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                        <h3 className="text-lg font-semibold mb-2">
                          {activeTab === 'upcoming' ? 'Нет предстоящих занятий' : 'Нет прошедших занятий'}
                        </h3>
                        <p className="text-muted-foreground mb-6">
                          {activeTab === 'upcoming'
                            ? 'Обратитесь к преподавателю для планирования занятий'
                            : 'Ещё нет завершённых занятий'}
                        </p>
                        {activeTab === 'upcoming' && (
                          <Button type="button" asChild>
                            <a href="/dashboard/student/materials">Смотреть материалы</a>
                          </Button>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="space-y-4">
                      {filteredLessons.map(lesson => (
                        <LessonCard key={lesson.id} lesson={lesson} />
                      ))}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default StudentSchedulePage;