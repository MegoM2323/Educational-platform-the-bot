/**
 * LessonViewer with Progress Synchronization (T702)
 * Пример интеграции progressSyncService и notificationService
 */

import React, { useState, useEffect } from 'react';
import { useProgressSync } from '@/hooks/useProgressSync';
import { notificationService } from '@/services/notificationService';
import { LessonCompletionModal, type LessonCompletionStats } from './LessonCompletionModal';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

interface LessonViewerWithSyncProps {
  graphId: number;
  lessonId: number;
  graphLessonId: number;
  studentId: number;
  lessonTitle: string;
  elements: any[]; // Элементы урока
  onReturnToGraph: () => void;
  onNavigateToNextLesson?: () => void;
}

export const LessonViewerWithSync: React.FC<LessonViewerWithSyncProps> = ({
  graphId,
  lessonId,
  graphLessonId,
  studentId,
  lessonTitle,
  elements,
  onReturnToGraph,
  onNavigateToNextLesson,
}) => {
  // Состояние
  const [completedElements, setCompletedElements] = useState<Set<number>>(new Set());
  const [showCompletionModal, setShowCompletionModal] = useState(false);
  const [completionStats, setCompletionStats] = useState<LessonCompletionStats | null>(null);
  const [currentElementIndex, setCurrentElementIndex] = useState(0);

  // Hook для синхронизации прогресса
  const {
    completeLesson,
    syncProgress,
    checkCompletion,
    isLoading,
    unlockedLessons,
    lastSyncResult,
  } = useProgressSync({
    graphId,
    lessonId,
    graphLessonId,
    studentId,
    onLessonComplete: (result) => {
      // Урок завершен - показать модальное окно
      setCompletionStats({
        lessonTitle,
        completionPercent: result.completion_percent,
        timeSpentMinutes: result.time_spent_minutes,
        score: result.total_score,
        maxScore: result.max_possible_score,
        completedLessons: 0, // Будет обновлено из lastSyncResult
        totalLessons: 0,
        unlockedLessonsCount: result.unlocked_lessons.length,
      });
      setShowCompletionModal(true);
    },
    onUnlock: (lessonIds) => {
      console.log('Unlocked lessons:', lessonIds);
    },
    onError: (error) => {
      console.error('Progress sync error:', error);
    },
  });

  // Обработчик завершения элемента
  const handleElementComplete = async (elementId: number, answer: any, score?: number) => {
    try {
      // 1. Сохранить ответ на элемент (API call)
      // await saveElementProgress(elementId, answer);

      // 2. Отметить элемент как завершенный
      setCompletedElements((prev) => new Set(prev).add(elementId));

      // 3. Показать уведомление
      notificationService.elementCompleted(
        `Элемент ${elementId}`,
        score,
        100 // max score
      );

      // 4. Синхронизировать прогресс
      const syncResult = await syncProgress();

      // 5. Проверить завершение урока
      if (syncResult.completed) {
        // Урок автоматически завершен, модальное окно откроется через onLessonComplete
        console.log('Lesson completed automatically!');
      } else {
        // Урок еще не завершен - показать прогресс
        const completionPercent = Math.round(
          (completedElements.size / elements.length) * 100
        );
        if (completionPercent >= 80 && completionPercent < 100) {
          notificationService.lessonProgress(completionPercent);
        }
      }

      // 6. Перейти к следующему элементу
      if (currentElementIndex < elements.length - 1) {
        setCurrentElementIndex(currentElementIndex + 1);
      }
    } catch (error) {
      console.error('Error completing element:', error);
      notificationService.progressSaveError(() => handleElementComplete(elementId, answer, score));
    }
  };

  // Ручное завершение урока (если студент нажал кнопку "Завершить")
  const handleManualComplete = async () => {
    try {
      const result = await completeLesson();
      if (!result) {
        notificationService.warning(
          'Урок еще не завершен',
          'Завершите все элементы урока'
        );
      }
    } catch (error) {
      console.error('Error completing lesson manually:', error);
    }
  };

  // Проверка завершения при загрузке
  useEffect(() => {
    const checkIfComplete = async () => {
      const isComplete = await checkCompletion();
      if (isComplete) {
        // Урок уже завершен - показать уведомление
        notificationService.lessonAlreadyCompleted(lessonTitle);
      }
    };
    checkIfComplete();
  }, []);

  // Вычислить процент завершения
  const completionPercent =
    elements.length > 0 ? Math.round((completedElements.size / elements.length) * 100) : 0;

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Заголовок */}
      <Card>
        <CardHeader>
          <CardTitle>{lessonTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Прогресс-бар */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Прогресс</span>
              <span className="font-medium">{completionPercent}%</span>
            </div>
            <Progress value={completionPercent} className="h-2" />
            <div className="text-xs text-gray-500">
              Завершено {completedElements.size} из {elements.length} элементов
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Текущий элемент */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            Элемент {currentElementIndex + 1} из {elements.length}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Здесь рендерится компонент элемента (ElementCard) */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <p>Element content goes here...</p>
            <Button
              onClick={() =>
                handleElementComplete(
                  elements[currentElementIndex]?.id,
                  { answer: 'example' },
                  100
                )
              }
              disabled={isLoading}
            >
              {isLoading ? 'Сохранение...' : 'Отправить ответ'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Навигация */}
      <div className="flex justify-between">
        <Button variant="outline" onClick={onReturnToGraph}>
          Вернуться к графу
        </Button>

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setCurrentElementIndex(Math.max(0, currentElementIndex - 1))}
            disabled={currentElementIndex === 0}
          >
            Назад
          </Button>
          <Button
            onClick={() =>
              setCurrentElementIndex(Math.min(elements.length - 1, currentElementIndex + 1))
            }
            disabled={currentElementIndex === elements.length - 1}
          >
            Далее
          </Button>
        </div>

        {completionPercent === 100 && (
          <Button onClick={handleManualComplete} disabled={isLoading}>
            Завершить урок
          </Button>
        )}
      </div>

      {/* Информация о разблокированных уроках */}
      {unlockedLessons.length > 0 && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <p className="text-center text-blue-900">
              {unlockedLessons.length} новых урока доступно для изучения!
            </p>
          </CardContent>
        </Card>
      )}

      {/* Модальное окно завершения урока */}
      {completionStats && (
        <LessonCompletionModal
          open={showCompletionModal}
          onOpenChange={setShowCompletionModal}
          stats={completionStats}
          onReturnToGraph={onReturnToGraph}
          onNextLesson={onNavigateToNextLesson}
          hasNextLesson={!!onNavigateToNextLesson}
        />
      )}
    </div>
  );
};
