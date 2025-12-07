/**
 * Lesson Viewer Page
 * Displays lesson elements sequentially with navigation and progress tracking
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useLessonProgress } from '@/hooks/useLessonProgress';
import { ElementCard, ElementCardSkeleton } from '@/components/knowledge-graph/ElementCard';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import {
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  Lock,
  ArrowLeft,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import { logger } from '@/utils/logger';
import confetti from 'canvas-confetti';
import { useAuth } from '@/hooks/useAuth';

interface LessonViewerProps {
  lessonId?: string;
  studentId?: string;
  graphId?: string;
  onComplete?: () => void;
  onError?: (error: Error) => void;
}

export const LessonViewer: React.FC<LessonViewerProps> = ({
  lessonId: propLessonId,
  studentId: propStudentId,
  graphId: propGraphId,
  onComplete,
  onError,
}) => {
  const navigate = useNavigate();
  const params = useParams();
  const { user } = useAuth();

  // Получить параметры из props или URL params
  const lessonId = propLessonId || params.lessonId || '';
  const studentId = propStudentId || params.studentId || user?.id?.toString() || '';
  const graphId = propGraphId || params.graphId;

  const [currentElementIndex, setCurrentElementIndex] = useState<number>(0);
  const [hasSubmittedCurrent, setHasSubmittedCurrent] = useState<boolean>(false);

  // Использовать hook для работы с данными урока
  const {
    lesson,
    progress,
    elementsWithProgress,
    isLoading,
    error,
    isUnlocked,
    missingPrerequisites,
    submitAnswer,
    isSubmitting,
    completeLesson,
    isCompletingLesson,
    getCurrentElementIndex,
    allElementsCompleted,
    getProgressPercent,
  } = useLessonProgress({
    lessonId,
    studentId,
    graphId,
    onComplete,
  });

  // Установить начальный индекс элемента при загрузке
  useEffect(() => {
    if (!isLoading && elementsWithProgress.length > 0) {
      const initialIndex = getCurrentElementIndex();
      setCurrentElementIndex(initialIndex);
      logger.info('[LessonViewer] Initial element index:', initialIndex);
    }
  }, [isLoading, elementsWithProgress.length]);

  // Проверить завершение всех элементов
  useEffect(() => {
    if (allElementsCompleted() && progress?.status !== 'completed') {
      logger.info('[LessonViewer] All elements completed, triggering lesson completion');
      handleCompleteLesson();
    }
  }, [progress?.completed_elements_count]);

  // Обработка ошибок
  useEffect(() => {
    if (error && onError) {
      onError(error);
    }
  }, [error, onError]);

  // Показать confetti при завершении урока
  const triggerConfetti = () => {
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
    });
  };

  // Обработчик отправки ответа
  const handleSubmitAnswer = async (answer: any) => {
    if (!progress?.graph_lesson_id) {
      toast.error('Не удалось определить урок в графе');
      return;
    }

    const currentElement = elementsWithProgress[currentElementIndex];
    if (!currentElement) {
      toast.error('Элемент не найден');
      return;
    }

    logger.info('[LessonViewer] Submitting answer for element:', currentElement.id);

    try {
      await submitAnswer({
        elementId: currentElement.id,
        data: {
          answer,
          graph_lesson_id: progress.graph_lesson_id,
        },
      });

      setHasSubmittedCurrent(true);
    } catch (error) {
      logger.error('[LessonViewer] Submit answer error:', error);
      // Ошибка уже обработана в hook через toast
    }
  };

  // Навигация к следующему элементу
  const handleNext = () => {
    if (currentElementIndex < elementsWithProgress.length - 1) {
      setCurrentElementIndex((prev) => prev + 1);
      setHasSubmittedCurrent(false);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Навигация к предыдущему элементу
  const handlePrevious = () => {
    if (currentElementIndex > 0) {
      setCurrentElementIndex((prev) => prev - 1);
      setHasSubmittedCurrent(false);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Завершить урок
  const handleCompleteLesson = async () => {
    logger.info('[LessonViewer] Completing lesson');
    triggerConfetti();

    try {
      await completeLesson();
    } catch (error) {
      logger.error('[LessonViewer] Complete lesson error:', error);
    }
  };

  // Вернуться к графу
  const handleBackToGraph = () => {
    if (graphId) {
      navigate(`/dashboard/student/knowledge-graph/${graphId}`);
    } else {
      navigate('/dashboard/student');
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="space-y-6">
          <div className="h-8 w-64 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          <ElementCardSkeleton />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Alert variant="destructive">
          <AlertDescription>
            Ошибка загрузки урока: {error.message}
          </AlertDescription>
        </Alert>
        <Button onClick={handleBackToGraph} className="mt-4" variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Вернуться к графу
        </Button>
      </div>
    );
  }

  // Prerequisites not met
  if (!isUnlocked) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="flex items-center gap-4">
              <Lock className="h-12 w-12 text-yellow-600" />
              <div>
                <h2 className="text-2xl font-bold">Урок заблокирован</h2>
                <p className="text-muted-foreground">
                  Для доступа к этому уроку необходимо завершить предыдущие уроки
                </p>
              </div>
            </div>

            {missingPrerequisites.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-semibold">Требуется завершить:</h3>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                  {missingPrerequisites.map((prereq) => (
                    <li key={prereq.id}>{prereq.title}</li>
                  ))}
                </ul>
              </div>
            )}

            <Button onClick={handleBackToGraph} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Вернуться к графу
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // No lesson data
  if (!lesson || !elementsWithProgress.length) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Alert>
          <AlertDescription>Урок не содержит элементов</AlertDescription>
        </Alert>
        <Button onClick={handleBackToGraph} className="mt-4" variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Вернуться к графу
        </Button>
      </div>
    );
  }

  const currentElement = elementsWithProgress[currentElementIndex];
  const progressPercent = getProgressPercent();
  const isLastElement = currentElementIndex === elementsWithProgress.length - 1;
  const isFirstElement = currentElementIndex === 0;
  const currentElementCompleted =
    currentElement.progress?.status === 'completed' || hasSubmittedCurrent;

  // Lesson completed state
  if (progress?.status === 'completed' && allElementsCompleted()) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Card>
          <CardContent className="pt-6 space-y-6 text-center">
            <div className="flex flex-col items-center gap-4">
              <div className="h-20 w-20 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
                <CheckCircle className="h-12 w-12 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h2 className="text-3xl font-bold flex items-center justify-center gap-2">
                  Урок завершен! <Sparkles className="h-6 w-6 text-yellow-500" />
                </h2>
                <p className="text-muted-foreground mt-2">
                  Поздравляем! Вы успешно завершили урок "{lesson.title}"
                </p>
              </div>
            </div>

            {progress && (
              <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Завершено элементов:</span>
                  <span className="font-semibold">
                    {progress.completed_elements_count} / {progress.total_elements_count}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Набрано баллов:</span>
                  <span className="font-semibold">
                    {progress.total_score} / {progress.max_total_score}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Процент выполнения:</span>
                  <span className="font-semibold">{progress.score_percent}%</span>
                </div>
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button onClick={handleBackToGraph} size="lg">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Вернуться к графу
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Header with breadcrumb and progress */}
      <div className="space-y-4 mb-6">
        <Button
          onClick={handleBackToGraph}
          variant="ghost"
          size="sm"
          className="mb-2"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Вернуться к графу
        </Button>

        <div>
          <h1 className="text-3xl font-bold">{lesson.title}</h1>
          <p className="text-muted-foreground mt-2">{lesson.description}</p>
        </div>

        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>
              Элемент {currentElementIndex + 1} из {elementsWithProgress.length}
            </span>
            <span>{progressPercent}% завершено</span>
          </div>
          <Progress value={progressPercent} className="h-2" />
        </div>
      </div>

      {/* Current element card */}
      <div className="mb-6">
        <ElementCard
          element={currentElement}
          progress={currentElement.progress}
          onSubmit={handleSubmitAnswer}
          isLoading={isSubmitting}
          readOnly={false}
        />
      </div>

      {/* Navigation buttons */}
      <div className="flex justify-between items-center gap-4">
        <Button
          onClick={handlePrevious}
          variant="outline"
          disabled={isFirstElement}
          className="flex-1 sm:flex-initial"
        >
          <ChevronLeft className="h-4 w-4 mr-2" />
          Назад
        </Button>

        <div className="hidden sm:block text-sm text-muted-foreground">
          {currentElementCompleted && (
            <span className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-4 w-4" />
              Выполнено
            </span>
          )}
        </div>

        {!isLastElement ? (
          <Button
            onClick={handleNext}
            disabled={!currentElementCompleted}
            className="flex-1 sm:flex-initial"
          >
            Далее
            <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        ) : (
          <Button
            onClick={handleNext}
            disabled={!currentElementCompleted}
            className="flex-1 sm:flex-initial"
            variant="default"
          >
            {allElementsCompleted() ? 'Завершить урок' : 'Последний элемент'}
            <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        )}
      </div>

      {/* Mobile progress indicator */}
      <div className="sm:hidden mt-4 text-center text-sm text-muted-foreground">
        {currentElementCompleted && (
          <span className="flex items-center justify-center gap-2 text-green-600">
            <CheckCircle className="h-4 w-4" />
            Элемент выполнен
          </span>
        )}
      </div>
    </div>
  );
};
