import React, { useState } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { TeacherSidebar } from '@/components/layout/TeacherSidebar';
import { useAuth } from '@/contexts/AuthContext';
import { Navigate } from 'react-router-dom';
import { useTeacherDashboard } from '@/hooks/useTeacher';
import { useTeacherLessons } from '@/hooks/useTeacherLessons';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader, Plus, AlertCircle } from 'lucide-react';
import { LessonForm } from '@/components/scheduling/teacher/LessonForm';
import { LessonRow } from '@/components/scheduling/teacher/LessonRow';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { LessonFormData } from '@/schemas/lesson';

const TeacherSchedulePage: React.FC = () => {
  const { user } = useAuth();
  const { data: dashboardData, isLoading: dashboardLoading } = useTeacherDashboard();
  const { toast } = useToast();
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [lessonToEdit, setLessonToEdit] = useState<any | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const {
    lessons,
    isLoading: lessonsLoading,
    error: lessonsError,
    createLesson,
    updateLesson,
    deleteLesson,
    isCreating,
    isUpdating,
    isDeleting,
  } = useTeacherLessons();

  // Redirect if not a teacher
  if (user?.role !== 'teacher') {
    return <Navigate to="/dashboard" replace />;
  }

  const students = dashboardData?.students || [];

  // Extract all unique subjects from students' subject enrollments
  const subjectsMap = new Map<string, any>();
  students.forEach((student) => {
    if (student.subjects) {
      student.subjects.forEach((subject) => {
        if (!subjectsMap.has(String(subject.id))) {
          subjectsMap.set(String(subject.id), subject);
        }
      });
    }
  });
  const subjects = Array.from(subjectsMap.values());

  // Утилита для конвертации времени HH:MM в HH:MM:SS
  const formatTime = (time: string): string => {
    const parts = time.split(':');
    return parts.length === 2 ? `${time}:00` : time;
  };

  const handleCreateLesson = async (formData: LessonFormData) => {
    try {
      // Конвертируем HH:MM в HH:MM:SS для бэкенда
      const payload = {
        ...formData,
        start_time: formatTime(formData.start_time),
        end_time: formatTime(formData.end_time),
      };

      // Используем async/await для корректной обработки мутации
      await createLesson(payload);

      // Закрываем форму только после успешного создания
      setIsFormOpen(false);
    } catch (error) {
      toast({
        title: 'Error',
        description:
          error instanceof Error ? error.message : 'Failed to create lesson',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteLesson = (lessonId: string) => {
    // Устанавливаем ID удаляемого урока для отображения loading state
    setDeletingId(lessonId);
    // Мутация обрабатывает success/error тосты и инвалидацию запросов
    deleteLesson(lessonId, {
      onSettled: () => {
        // Сбрасываем deletingId после завершения операции (успех или ошибка)
        setDeletingId(null);
      }
    });
  };

  const handleEditLesson = (lesson: any) => {
    // Convert HH:MM:SS to HH:MM for form compatibility
    // Convert student/subject IDs to strings for form compatibility
    // Handle cases where student/subject might be objects with id property
    const studentId = typeof lesson.student === 'object'
      ? String(lesson.student?.id || lesson.student)
      : String(lesson.student);
    const subjectId = typeof lesson.subject === 'object'
      ? String(lesson.subject?.id || lesson.subject)
      : String(lesson.subject);

    const lessonData = {
      id: lesson.id,
      student: studentId,
      subject: subjectId,
      date: lesson.date,
      start_time: lesson.start_time.substring(0, 5), // HH:MM:SS -> HH:MM
      end_time: lesson.end_time.substring(0, 5), // HH:MM:SS -> HH:MM
      description: lesson.description || '',
      telemost_link: lesson.telemost_link || '',
      status: lesson.status,
      teacher: lesson.teacher,
      created_at: lesson.created_at,
      updated_at: lesson.updated_at,
    };
    setEditingId(lesson.id);
    setLessonToEdit(lessonData);
  };

  const handleUpdateLesson = async (formData: LessonFormData) => {
    if (!editingId) return;

    try {
      // Конвертируем HH:MM в HH:MM:SS для бэкенда
      // НЕ отправляем student и subject - они read-only при обновлении
      const payload = {
        date: formData.date,
        start_time: formatTime(formData.start_time),
        end_time: formatTime(formData.end_time),
        description: formData.description || '',
        telemost_link: formData.telemost_link || '',
      };

      // Используем async/await для корректной обработки мутации
      await updateLesson({ id: editingId, payload });

      // Очищаем состояние диалога только после успешного обновления
      setEditingId(null);
      setLessonToEdit(null);
    } catch (error) {
      toast({
        title: 'Error',
        description:
          error instanceof Error ? error.message : 'Failed to update lesson',
        variant: 'destructive',
      });
    }
  };

  const handleOpenForm = () => {
    setIsFormOpen(true);
  };

  const sortedLessons = [...lessons].sort((a, b) => {
    return new Date(a.date).getTime() - new Date(b.date).getTime();
  });

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <TeacherSidebar />
        <SidebarInset className="flex-1">
          <div className="flex h-14 items-center border-b px-6">
            <SidebarTrigger />
            <h1 className="ml-4 text-xl font-semibold">My Schedule</h1>
          </div>
          <div className="space-y-6 p-6">
            {/* Create lesson card */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Create Lesson</CardTitle>
                  {!isFormOpen && (
                    <Button
                      type="button"
                      onClick={handleOpenForm}
                      size="sm"
                      variant="outline"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Add Lesson
                    </Button>
                  )}
                </div>
              </CardHeader>
              {isFormOpen && (
                <CardContent className="space-y-4">
                  <LessonForm
                    onSubmit={handleCreateLesson}
                    isLoading={isCreating}
                    students={students}
                    subjects={subjects}
                  />
                  <Button type="button"
                    variant="ghost"
                    onClick={() => setIsFormOpen(false)}
                    className="w-full"
                  >
                    Cancel
                  </Button>
                </CardContent>
              )}
            </Card>

            {/* Lessons list */}
            <Card>
              <CardHeader>
                <CardTitle>My Lessons</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {lessonsLoading && (
                  <div className="flex items-center justify-center py-8">
                    <Loader className="w-5 h-5 animate-spin text-muted-foreground" />
                  </div>
                )}

                {lessonsError && (
                  <div className="flex items-center gap-2 p-4 rounded-lg bg-red-50 text-red-700">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <span className="text-sm">
                      Failed to load lessons. Please try again.
                    </span>
                  </div>
                )}

                {!lessonsLoading && sortedLessons.length === 0 && (
                  <p className="text-center py-8 text-muted-foreground">
                    No lessons created yet. Click "Add Lesson" to create your first lesson.
                  </p>
                )}

                {!lessonsLoading && sortedLessons.length > 0 && (
                  <div className="space-y-3">
                    {sortedLessons.map((lesson) => (
                      <LessonRow
                        key={lesson.id}
                        lesson={lesson}
                        onEdit={() => handleEditLesson(lesson)}
                        onDelete={() => handleDeleteLesson(lesson.id)}
                        deletingId={deletingId}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Edit lesson dialog */}
          {editingId && lessonToEdit && (
            <Dialog
              open={editingId !== null}
              onOpenChange={(open) => {
                if (!open) {
                  setEditingId(null);
                  setLessonToEdit(null);
                }
              }}
            >
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Edit Lesson</DialogTitle>
                </DialogHeader>
                <LessonForm
                  onSubmit={handleUpdateLesson}
                  initialData={lessonToEdit}
                  isLoading={isUpdating}
                  students={students}
                  subjects={subjects}
                  isEditMode={true} // IMPORTANT: use update schema
                />
              </DialogContent>
            </Dialog>
          )}
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default TeacherSchedulePage;