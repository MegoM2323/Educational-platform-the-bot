/**
 * Teacher Lesson Creator Page (T023)
 * Страница создания и редактирования уроков из элементов
 *
 * Функционал:
 * - Создание урока с выбором элементов
 * - Drag-drop для изменения порядка элементов
 * - Выбор предмета
 * - Сохранение как черновик или публикация
 * - Превью урока для студента
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { LessonEditor } from '@/components/teacher/LessonEditor';
import { LessonPreview } from '@/components/teacher/LessonPreview';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { contentCreatorService } from '@/services/contentCreatorService';
import { Loader2, ArrowLeft } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface LessonFormData {
  title: string;
  description: string;
  subject_id: number | null;
  element_ids: number[];
  is_public: boolean;
}

const LessonCreatorPage: React.FC = () => {
  const { lessonId } = useParams<{ lessonId?: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [lessonData, setLessonData] = useState<LessonFormData>({
    title: '',
    description: '',
    subject_id: null,
    element_ids: [],
    is_public: false,
  });
  const [activeTab, setActiveTab] = useState<'editor' | 'preview'>('editor');

  // Загрузка существующего урока при редактировании
  useEffect(() => {
    if (lessonId) {
      loadLesson(Number(lessonId));
    }
  }, [lessonId]);

  const loadLesson = async (id: number) => {
    setIsLoading(true);
    try {
      const response = await contentCreatorService.getLesson(id);
      const lesson = response.data;

      setLessonData({
        title: lesson.title,
        description: lesson.description,
        subject_id: lesson.subject?.id || null,
        element_ids: lesson.elements?.map(el => el.element.id) || [],
        is_public: lesson.is_public,
      });

      toast({
        title: 'Урок загружен',
        description: `Загружен урок: ${lesson.title}`,
      });
    } catch (error) {
      toast({
        title: 'Ошибка загрузки',
        description: error instanceof Error ? error.message : 'Не удалось загрузить урок',
        variant: 'destructive',
      });
      navigate('/dashboard/teacher/content-creator');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async (isDraft: boolean) => {
    // Валидация
    if (!lessonData.title.trim()) {
      toast({
        title: 'Ошибка валидации',
        description: 'Название урока обязательно',
        variant: 'destructive',
      });
      return;
    }

    if (!lessonData.subject_id) {
      toast({
        title: 'Ошибка валидации',
        description: 'Выберите предмет',
        variant: 'destructive',
      });
      return;
    }

    if (lessonData.element_ids.length === 0) {
      toast({
        title: 'Ошибка валидации',
        description: 'Добавьте хотя бы один элемент',
        variant: 'destructive',
      });
      return;
    }

    setIsSaving(true);
    try {
      const payload = {
        title: lessonData.title,
        description: lessonData.description,
        subject: lessonData.subject_id,
        element_ids: lessonData.element_ids,
        is_public: !isDraft, // Черновик = is_public: false, Публикация = is_public: true
      };

      let response;
      if (lessonId) {
        response = await contentCreatorService.updateLesson(Number(lessonId), payload);
      } else {
        response = await contentCreatorService.createLesson(payload);
      }

      toast({
        title: 'Успех',
        description: isDraft
          ? 'Урок сохранён как черновик'
          : 'Урок опубликован',
      });

      // Перенаправление на страницу Content Creator
      navigate('/dashboard/teacher/content-creator');
    } catch (error) {
      toast({
        title: 'Ошибка сохранения',
        description: error instanceof Error ? error.message : 'Не удалось сохранить урок',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    navigate('/dashboard/teacher/content-creator');
  };

  if (isLoading) {
    return (
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <TeacherSidebar />
          <SidebarInset>
            <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
              <SidebarTrigger />
              <h1 className="text-2xl font-bold">Создание урока</h1>
            </header>
            <main className="p-6 flex items-center justify-center">
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-muted-foreground">Загрузка урока...</p>
              </div>
            </main>
          </SidebarInset>
        </div>
      </SidebarProvider>
    );
  }

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleCancel}
              className="mr-2"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Назад
            </Button>
            <div className="flex-1">
              <h1 className="text-2xl font-bold">
                {lessonId ? 'Редактирование урока' : 'Создание урока'}
              </h1>
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleSave(true)}
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Сохранение...
                  </>
                ) : (
                  'Сохранить черновик'
                )}
              </Button>
              <Button
                type="button"
                onClick={() => handleSave(false)}
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Сохранение...
                  </>
                ) : (
                  'Опубликовать'
                )}
              </Button>
            </div>
          </header>
          <main className="p-6">
            <Card>
              <CardHeader>
                <CardTitle>
                  {lessonId ? 'Редактирование урока' : 'Создание урока'}
                </CardTitle>
                <CardDescription>
                  Создайте урок, выбрав элементы из банка контента и расставив их в нужном порядке
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'editor' | 'preview')}>
                  <TabsList className="grid w-full grid-cols-2 mb-6">
                    <TabsTrigger value="editor">Редактор</TabsTrigger>
                    <TabsTrigger value="preview">Превью</TabsTrigger>
                  </TabsList>

                  <TabsContent value="editor" className="space-y-6">
                    <LessonEditor
                      lessonData={lessonData}
                      onUpdate={setLessonData}
                    />
                  </TabsContent>

                  <TabsContent value="preview">
                    <LessonPreview
                      title={lessonData.title}
                      description={lessonData.description}
                      elementIds={lessonData.element_ids}
                    />
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default LessonCreatorPage;
