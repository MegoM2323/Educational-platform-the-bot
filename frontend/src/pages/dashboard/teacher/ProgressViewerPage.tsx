import React, { useState, useEffect } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { ProgressViewerTab } from './ProgressViewerTab';
import { useTeacherDashboard } from '@/hooks/useTeacher';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

/**
 * Teacher Progress Viewer Page
 * Обертка для ProgressViewerTab с sidebar и выбором предмета
 */
const ProgressViewerPage: React.FC = () => {
  const { data: dashboardData, isLoading, error } = useTeacherDashboard();
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | null>(null);

  // Получаем список предметов преподавателя из дашборда
  const subjects = dashboardData?.profile?.subjects || [];

  // Автоматически выбираем первый предмет если есть
  useEffect(() => {
    if (subjects.length > 0 && !selectedSubjectId) {
      const firstSubject = subjects[0];
      if (typeof firstSubject === 'object' && firstSubject?.id) {
        setSelectedSubjectId(firstSubject.id);
      }
    }
  }, [subjects, selectedSubjectId]);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1">
              <h1 className="text-2xl font-bold">Прогресс учеников</h1>
            </div>
          </header>
          <main className="p-6">
            {isLoading && (
              <div className="space-y-4">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-64 w-full" />
              </div>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Ошибка загрузки данных преподавателя: {error.message}
                </AlertDescription>
              </Alert>
            )}

            {!isLoading && !error && subjects.length === 0 && (
              <Card className="p-6">
                <div className="text-center text-muted-foreground">
                  У вас нет назначенных предметов. Обратитесь к администратору.
                </div>
              </Card>
            )}

            {!isLoading && !error && subjects.length > 0 && (
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <label className="text-sm font-medium">Предмет:</label>
                  <Select
                    value={selectedSubjectId?.toString() || ''}
                    onValueChange={(value) => setSelectedSubjectId(Number(value))}
                  >
                    <SelectTrigger className="w-[300px]">
                      <SelectValue placeholder="Выберите предмет" />
                    </SelectTrigger>
                    <SelectContent>
                      {subjects.map((subject: any) => {
                        const subjectId = typeof subject === 'object' ? subject.id : null;
                        const subjectName = typeof subject === 'object' ? subject.name : subject;
                        if (!subjectId) return null;
                        return (
                          <SelectItem key={subjectId} value={subjectId.toString()}>
                            {subjectName}
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                </div>

                {selectedSubjectId && <ProgressViewerTab subjectId={selectedSubjectId} />}
              </div>
            )}
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default ProgressViewerPage;
