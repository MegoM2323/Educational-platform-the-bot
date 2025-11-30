import React, { useState, useMemo } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { Navigate } from "react-router-dom";
import { useStudentSchedule } from "@/hooks/useStudentSchedule";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Calendar, Filter } from "lucide-react";
import { LessonCard } from "@/components/scheduling/student/LessonCard";

const StudentSchedulePage: React.FC = () => {
  const { user } = useAuth();
  const { lessons, isLoading } = useStudentSchedule();

  const [activeTab, setActiveTab] = useState<'upcoming' | 'past'>('upcoming');
  const [selectedSubject, setSelectedSubject] = useState<string>('');
  const [selectedTeacher, setSelectedTeacher] = useState<string>('');

  if (user?.role !== 'student') {
    return <Navigate to="/dashboard" replace />;
  }

  const now = new Date();

  const filteredLessons = useMemo(() => {
    return lessons.filter(lesson => {
      const lessonDateTime = new Date(`${lesson.date}T${lesson.start_time}`);
      const isUpcoming = lessonDateTime > now;

      if (activeTab === 'upcoming' && !isUpcoming) return false;
      if (activeTab === 'past' && isUpcoming) return false;

      if (selectedSubject && lesson.subject_name !== selectedSubject) return false;
      if (selectedTeacher && lesson.teacher_name !== selectedTeacher) return false;

      return true;
    }).sort((a, b) => {
      const dateA = new Date(`${a.date}T${a.start_time}`);
      const dateB = new Date(`${b.date}T${b.start_time}`);
      return activeTab === 'upcoming' ? dateA.getTime() - dateB.getTime() : dateB.getTime() - dateA.getTime();
    });
  }, [lessons, activeTab, selectedSubject, selectedTeacher, now]);

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
                          <SelectItem value="">Все предметы</SelectItem>
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
                          <SelectItem value="">Все преподаватели</SelectItem>
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
                          <Button asChild>
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