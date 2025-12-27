/**
 * Lesson Completion Modal (T702)
 * Показывает результаты завершения урока с анимацией
 */

import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Clock, Trophy, ArrowRight } from 'lucide-react';
import Confetti from 'react-confetti';
import { useWindowSize } from '@/hooks/useWindowSize';

export interface LessonCompletionStats {
  lessonTitle: string;
  completionPercent: number;
  timeSpentMinutes: number;
  score: number;
  maxScore: number;
  completedLessons: number;
  totalLessons: number;
  unlockedLessonsCount: number;
}

export interface LessonCompletionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  stats: LessonCompletionStats;
  onReturnToGraph: () => void;
  onNextLesson?: () => void; // Если есть доступный следующий урок
  hasNextLesson?: boolean;
}

export const LessonCompletionModal: React.FC<LessonCompletionModalProps> = ({
  open,
  onOpenChange,
  stats,
  onReturnToGraph,
  onNextLesson,
  hasNextLesson = false,
}) => {
  const { width, height } = useWindowSize();
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => {
    if (open) {
      setShowConfetti(true);
      // Остановить конфетти через 5 секунд
      const timer = setTimeout(() => {
        setShowConfetti(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const scorePercent = stats.maxScore > 0 ? Math.round((stats.score / stats.maxScore) * 100) : 100;

  return (
    <>
      {showConfetti && (
        <Confetti
          width={width}
          height={height}
          recycle={false}
          numberOfPieces={300}
          gravity={0.3}
        />
      )}

      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center justify-center mb-4">
              <div className="rounded-full bg-green-100 p-3 animate-bounce">
                <CheckCircle2 className="h-12 w-12 text-green-600" />
              </div>
            </div>
            <DialogTitle className="text-center text-2xl">Урок завершен!</DialogTitle>
            <DialogDescription className="text-center text-lg font-medium">
              {stats.lessonTitle}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Статистика */}
            <div className="space-y-3">
              {/* Процент выполнения */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span className="font-medium">Выполнено</span>
                </div>
                <span className="text-lg font-bold text-green-600">
                  {stats.completionPercent}%
                </span>
              </div>

              {/* Время */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-blue-600" />
                  <span className="font-medium">Затрачено времени</span>
                </div>
                <span className="text-lg font-bold text-blue-600">
                  {stats.timeSpentMinutes} мин
                </span>
              </div>

              {/* Баллы */}
              {stats.maxScore > 0 && (
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Trophy className="h-5 w-5 text-yellow-600" />
                    <span className="font-medium">Баллы</span>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-yellow-600">
                      {stats.score}/{stats.maxScore}
                    </div>
                    <div className="text-xs text-gray-500">{scorePercent}%</div>
                  </div>
                </div>
              )}
            </div>

            {/* Общий прогресс */}
            <div className="border-t pt-4">
              <div className="text-center">
                <p className="text-sm text-gray-600 mb-2">Общий прогресс по курсу</p>
                <p className="text-2xl font-bold text-indigo-600">
                  {stats.completedLessons}/{stats.totalLessons} уроков
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {Math.round((stats.completedLessons / stats.totalLessons) * 100)}% завершено
                </p>
              </div>
            </div>

            {/* Разблокированные уроки */}
            {stats.unlockedLessonsCount > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                <p className="text-sm font-medium text-blue-900">
                  {stats.unlockedLessonsCount}{' '}
                  {stats.unlockedLessonsCount === 1
                    ? 'новый урок разблокирован'
                    : 'новых урока разблокировано'}
                  !
                </p>
              </div>
            )}
          </div>

          <DialogFooter className="flex flex-col sm:flex-row gap-2">
            <Button variant="outline" onClick={onReturnToGraph} className="flex-1">
              Вернуться к графу
            </Button>
            {hasNextLesson && onNextLesson && (
              <Button onClick={onNextLesson} className="flex-1">
                Следующий урок
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
