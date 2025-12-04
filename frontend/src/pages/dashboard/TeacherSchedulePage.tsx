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
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

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

  const handleCreateLesson = async (formData: LessonFormData) => {
    try {
      // Convert HH:MM to HH:MM:SS for backend compatibility
      const payload = {
        ...formData,
        start_time: formData.start_time.includes(':') && formData.start_time.split(':').length === 2
          ? formData.start_time + ':00'
          : formData.start_time,
        end_time: formData.end_time.includes(':') && formData.end_time.split(':').length === 2
          ? formData.end_time + ':00'
          : formData.end_time,
      };

      createLesson(payload);
      // Form will reset on success due to mutation onSuccess invalidating cache
      // Toast will be shown by the form's error handling
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

  const handleDeleteLesson = async (lessonId: string) => {
    try {
      deleteLesson(lessonId);
      toast({
        title: 'Success',
        description: 'Lesson deleted successfully',
        variant: 'default',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description:
          error instanceof Error ? error.message : 'Failed to delete lesson',
        variant: 'destructive',
      });
    }
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
                      onClick={() => setIsFormOpen(true)}
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
                  <Button
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
                        onEdit={() => setEditingId(lesson.id)}
                        onDelete={() => handleDeleteLesson(lesson.id)}
                        isDeleting={isDeleting}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default TeacherSchedulePage;