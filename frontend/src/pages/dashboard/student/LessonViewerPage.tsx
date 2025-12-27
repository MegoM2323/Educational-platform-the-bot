/**
 * LessonViewerPage - страница для прохождения урока студентом
 * Интерактивный плеер уроков с элементами разных типов
 *
 * Route: /dashboard/student/lesson/:lessonId
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { knowledgeGraphAPI } from '@/integrations/api/knowledgeGraphAPI';
import { LessonContent } from '@/components/student/LessonContent';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, Trophy, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

interface LessonElement {
  id: string;
  order: number;
  element: {
    id: string;
    title: string;
    element_type: 'text_problem' | 'quick_question' | 'theory' | 'video';
    content: any;
    max_score: number;
    estimated_time_minutes: number;
  };
  progress?: {
    id: string;
    status: 'not_started' | 'in_progress' | 'completed';
    score: number | null;
    answer: any | null;
    started_at: string | null;
    completed_at: string | null;
  };
}

const LessonViewerPage: React.FC = () => {
  const { lessonId } = useParams<{ lessonId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [currentElementIndex, setCurrentElementIndex] = useState(0);
  const [isCompleting, setIsCompleting] = useState(false);

  // Загрузка урока с элементами
  const {
    data: lessonData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['student-lesson', lessonId],
    queryFn: () => knowledgeGraphAPI.getStudentLesson(lessonId!),
    enabled: !!lessonId,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    staleTime: 60000,
  });

  // Автоматически найти первый незавершенный элемент
  useEffect(() => {
    if (lessonData?.elements) {
      const firstIncomplete = lessonData.elements.findIndex(
        (el: LessonElement) => el.progress?.status !== 'completed'
      );
      if (firstIncomplete !== -1) {
        setCurrentElementIndex(firstIncomplete);
      }
    }
  }, [lessonData]);

  const currentElement = lessonData?.elements?.[currentElementIndex];
  const totalElements = lessonData?.elements?.length || 0;
  const isLastElement = currentElementIndex >= totalElements - 1;

  // Мутация: отправить ответ на элемент
  const submitAnswerMutation = useMutation({
    mutationFn: async (answer: any) => {
      if (!currentElement) throw new Error('Элемент не найден');

      // Сначала начинаем элемент если еще не начат
      if (currentElement.progress?.status === 'not_started' || !currentElement.progress) {
        await knowledgeGraphAPI.startStudentElement(currentElement.element.id);
      }

      // Отправляем ответ
      const result = await knowledgeGraphAPI.submitStudentAnswer(
        currentElement.element.id,
        answer
      );

      return result;
    },
    onSuccess: (data) => {
      // Показать результат
      if (data?.data?.is_correct !== undefined) {
        if (data.data.is_correct) {
          toast.success('Правильно! Молодец!');
        } else {
          toast.error('Неверно. Попробуйте еще раз.');
        }
      } else {
        toast.success('Ответ принят!');
      }

      // Обновить урок
      queryClient.invalidateQueries({ queryKey: ['student-lesson', lessonId] });

      // Автоматически перейти к следующему если не последний и ответ правильный
      if (!isLastElement && data?.data?.is_correct !== false) {
        setTimeout(() => {
          setCurrentElementIndex((prev) => prev + 1);
        }, 1500);
      }
    },
    onError: (error: any) => {
      toast.error(error.message || 'Ошибка отправки ответа');
    },
  });

  // Мутация: завершить урок
  const completeLessonMutation = useMutation({
    mutationFn: () => knowledgeGraphAPI.completeStudentLesson(lessonId!),
    onSuccess: (data) => {
      setIsCompleting(true);
      toast.success('🎉 Урок завершен! Поздравляем!');

      // Обновить граф и урок
      queryClient.invalidateQueries({ queryKey: ['student-lesson', lessonId] });
      queryClient.invalidateQueries({ queryKey: ['student-graph'] });
      queryClient.invalidateQueries({ queryKey: ['forum', 'chats'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Ошибка завершения урока');
    },
  });

  // Навигация
  const goToNext = useCallback(() => {
    if (currentElementIndex < totalElements - 1) {
      setCurrentElementIndex((prev) => prev + 1);
    }
  }, [currentElementIndex, totalElements]);

  const goToPrevious = useCallback(() => {
    if (currentElementIndex > 0) {
      setCurrentElementIndex((prev) => prev - 1);
    }
  }, [currentElementIndex]);

  const handleBackToGraph = useCallback(() => {
    navigate('/dashboard/student/knowledge-graph');
  }, [navigate]);

  const handleSubmitAnswer = useCallback(
    async (answer: any) => {
      await submitAnswerMutation.mutateAsync(answer);
    },
    [submitAnswerMutation]
  );

  const handleCompleteLesson = useCallback(() => {
    completeLessonMutation.mutate();
  }, [completeLessonMutation]);

  // Прогресс
  const completedCount =
    lessonData?.elements?.filter((el: LessonElement) => el.progress?.status === 'completed')
      .length || 0;
  const progressPercent =
    totalElements > 0 ? Math.round((completedCount / totalElements) * 100) : 0;

  // Проверка: все элементы завершены?
  const allCompleted = completedCount === totalElements && totalElements > 0;

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen p-6">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Ошибка загрузки урока</AlertTitle>
          <AlertDescription>{(error as Error).message}</AlertDescription>
          <Button variant="outline" onClick={handleBackToGraph} className="mt-4">
            Назад к графу
          </Button>
        </Alert>
      </div>
    );
  }

  // Нет данных
  if (!lessonData || !currentElement) {
    return (
      <div className="flex items-center justify-center min-h-screen p-6">
        <Alert className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Урок не найден</AlertTitle>
          <AlertDescription>
            Не удалось загрузить урок. Возможно, он был удален.
          </AlertDescription>
          <Button variant="outline" onClick={handleBackToGraph} className="mt-4">
            Назад к графу
          </Button>
        </Alert>
      </div>
    );
  }

  // Экран завершения урока
  if (isCompleting || allCompleted) {
    const totalScore = lessonData.progress?.total_score || 0;
    const maxScore = lessonData.progress?.max_possible_score || 0;
    const scorePercent = maxScore > 0 ? Math.round((totalScore / maxScore) * 100) : 0;

    return (
      <div className="flex items-center justify-center min-h-screen p-6">
        <Card className="max-w-lg w-full">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <Trophy className="w-16 h-16 text-yellow-500" />
            </div>
            <CardTitle className="text-3xl">🎉 Урок завершен!</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-xl font-semibold">{lessonData.graph_lesson.lesson.title}</h2>
              <p className="text-muted-foreground">
                {lessonData.graph_lesson.lesson.description}
              </p>
            </div>

            <div className="space-y-4 border-t pt-4">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Процент правильных ответов:</span>
                <span className="font-bold text-lg">{scorePercent}%</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Набрано баллов:</span>
                <span className="font-bold text-lg">
                  {totalScore} / {maxScore}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Элементов завершено:</span>
                <span className="font-bold text-lg">
                  {completedCount} / {totalElements}
                </span>
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <Button onClick={handleBackToGraph} className="flex-1 gap-2">
                Назад к графу
                <ArrowRight className="w-4 h-4" />
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsCompleting(false);
                  setCurrentElementIndex(0);
                  queryClient.invalidateQueries({ queryKey: ['student-lesson', lessonId] });
                }}
                className="flex-1"
              >
                Повторить урок
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Основной экран прохождения урока
  return (
    <div className="min-h-screen bg-background">
      <LessonContent
        lessonTitle={lessonData.graph_lesson.lesson.title}
        currentElement={currentElement}
        currentElementIndex={currentElementIndex}
        totalElements={totalElements}
        progressPercent={progressPercent}
        onSubmit={handleSubmitAnswer}
        onNext={isLastElement && allCompleted ? handleCompleteLesson : goToNext}
        onPrevious={goToPrevious}
        onBackToGraph={handleBackToGraph}
        isSubmitting={submitAnswerMutation.isPending || completeLessonMutation.isPending}
        isLastElement={isLastElement}
      />
    </div>
  );
};

export default LessonViewerPage;
