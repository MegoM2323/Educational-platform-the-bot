import React, { useState } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { ContentCreatorTab } from './ContentCreatorTab';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { CreateElementForm } from '@/components/knowledge-graph/forms/CreateElementForm';
import { CreateLessonForm } from '@/components/knowledge-graph/forms/CreateLessonForm';
import { contentCreatorService } from '@/services/contentCreatorService';
import { useToast } from '@/hooks/use-toast';
import { useQueryClient, useQuery } from '@tanstack/react-query';

/**
 * Teacher Content Creator Page
 * Страница управления образовательным контентом с интегрированными формами создания
 */
const ContentCreatorPage: React.FC = () => {
  const [elementFormOpen, setElementFormOpen] = useState(false);
  const [lessonFormOpen, setLessonFormOpen] = useState(false);
  const [editingElementId, setEditingElementId] = useState<number | null>(null);
  const [editingLessonId, setEditingLessonId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch available elements for lesson creation
  const { data: elementsData } = useQuery({
    queryKey: ['content-creator', 'all-elements'],
    queryFn: () => contentCreatorService.getElements({ created_by: 'me' }),
    staleTime: 60000,
  });

  const availableElements = elementsData?.data || [];

  // Handlers for element operations
  const handleCreateElement = () => {
    setEditingElementId(null);
    setElementFormOpen(true);
  };

  const handleEditElement = (id: number) => {
    setEditingElementId(id);
    setElementFormOpen(true);
  };

  const handleElementFormClose = () => {
    setElementFormOpen(false);
    setEditingElementId(null);
  };

  const handleElementSubmit = async (data: any) => {
    setIsSubmitting(true);
    try {
      // Map form data to API format
      const apiData = {
        title: data.title,
        description: data.description || '',
        element_type: data.type, // Map 'type' to 'element_type'
        content: data.content || '',
        video_url: data.video_url || '',
        options: data.options || [],
        correct_answer: data.correct_answer || '',
        max_score: data.max_score || 0,
        difficulty: data.difficulty || 1,
        estimated_time_minutes: data.estimated_time_minutes || 5,
        is_public: false, // Default to private
      };

      if (editingElementId) {
        await contentCreatorService.updateElement(editingElementId, apiData);
        toast({
          title: 'Успех',
          description: 'Элемент успешно обновлен',
        });
      } else {
        await contentCreatorService.createElement(apiData);
        toast({
          title: 'Успех',
          description: 'Элемент успешно создан',
        });
      }

      // Refresh the elements list
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'elements'] });
      handleElementFormClose();
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: error instanceof Error ? error.message : 'Не удалось сохранить элемент',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handlers for lesson operations
  const handleCreateLesson = () => {
    setEditingLessonId(null);
    setLessonFormOpen(true);
  };

  const handleEditLesson = (id: number) => {
    setEditingLessonId(id);
    setLessonFormOpen(true);
  };

  const handleLessonFormClose = () => {
    setLessonFormOpen(false);
    setEditingLessonId(null);
  };

  const handleLessonSubmit = async (data: any) => {
    setIsSubmitting(true);
    try {
      if (editingLessonId) {
        await contentCreatorService.updateLesson(editingLessonId, data);
        toast({
          title: 'Успех',
          description: 'Урок успешно обновлен',
        });
      } else {
        await contentCreatorService.createLesson(data);
        toast({
          title: 'Успех',
          description: 'Урок успешно создан',
        });
      }

      // Refresh the lessons list
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'lessons'] });
      handleLessonFormClose();
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: error instanceof Error ? error.message : 'Не удалось сохранить урок',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1">
              <h1 className="text-2xl font-bold">Создание контента</h1>
            </div>
          </header>
          <main className="p-6">
            <ContentCreatorTab
              onCreateElement={handleCreateElement}
              onEditElement={handleEditElement}
              onCreateLesson={handleCreateLesson}
              onEditLesson={handleEditLesson}
            />

            {/* Element Form Dialog */}
            <Dialog open={elementFormOpen} onOpenChange={setElementFormOpen}>
              <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>
                    {editingElementId ? 'Редактировать элемент' : 'Создать элемент'}
                  </DialogTitle>
                </DialogHeader>
                <CreateElementForm
                  onSubmit={handleElementSubmit}
                  onCancel={handleElementFormClose}
                  isLoading={isSubmitting}
                />
              </DialogContent>
            </Dialog>

            {/* Lesson Form Dialog */}
            <Dialog open={lessonFormOpen} onOpenChange={setLessonFormOpen}>
              <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>
                    {editingLessonId ? 'Редактировать урок' : 'Создать урок'}
                  </DialogTitle>
                </DialogHeader>
                <CreateLessonForm
                  onSubmit={handleLessonSubmit}
                  onCancel={handleLessonFormClose}
                  availableElements={availableElements}
                  isLoading={isSubmitting}
                />
              </DialogContent>
            </Dialog>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default ContentCreatorPage;
