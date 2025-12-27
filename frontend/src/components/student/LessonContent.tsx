/**
 * LessonContent - обертка для отображения текущего элемента урока
 * Управляет навигацией между элементами и прогресс баром
 */

import React from 'react';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { ElementRenderer } from './ElementRenderer';

interface LessonContentProps {
  lessonTitle: string;
  currentElement: {
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
      status: 'not_started' | 'in_progress' | 'completed';
      score: number | null;
      answer: any | null;
    };
  };
  currentElementIndex: number;
  totalElements: number;
  progressPercent: number;
  onSubmit: (answer: any) => Promise<void>;
  onNext: () => void;
  onPrevious: () => void;
  onBackToGraph: () => void;
  isSubmitting: boolean;
  isLastElement: boolean;
}

export const LessonContent: React.FC<LessonContentProps> = ({
  lessonTitle,
  currentElement,
  currentElementIndex,
  totalElements,
  progressPercent,
  onSubmit,
  onNext,
  onPrevious,
  onBackToGraph,
  isSubmitting,
  isLastElement,
}) => {
  const canGoPrevious = currentElementIndex > 0;
  const canGoNext = currentElementIndex < totalElements - 1;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 p-6">
      {/* Заголовок с навигацией */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={onBackToGraph} className="gap-2">
          <ChevronLeft className="w-4 h-4" />
          Назад к графу
        </Button>
        <div className="flex-1 text-center">
          <h1 className="text-2xl font-bold">{lessonTitle}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Элемент {currentElementIndex + 1} / {totalElements}
          </p>
        </div>
        <div className="w-[120px]" /> {/* Spacer для выравнивания */}
      </div>

      {/* Прогресс бар */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm text-muted-foreground">
          <span>Прогресс</span>
          <span>{progressPercent}%</span>
        </div>
        <Progress value={progressPercent} className="h-2" />
      </div>

      {/* Текущий элемент */}
      <ElementRenderer
        element={currentElement.element}
        progress={currentElement.progress}
        onSubmit={onSubmit}
        onNext={onNext}
        isSubmitting={isSubmitting}
        isLastElement={isLastElement}
      />

      {/* Панель навигации снизу */}
      <div className="flex justify-between items-center pt-4 border-t">
        <Button
          variant="outline"
          onClick={onPrevious}
          disabled={!canGoPrevious}
          className="gap-2"
        >
          <ChevronLeft className="w-4 h-4" />
          Назад
        </Button>

        <div className="text-sm text-muted-foreground">
          {currentElement.progress?.status === 'completed' ? (
            <span className="text-green-600 font-medium">✓ Завершено</span>
          ) : currentElement.progress?.status === 'in_progress' ? (
            <span className="text-blue-600 font-medium">В процессе</span>
          ) : (
            <span className="text-gray-600">Не начато</span>
          )}
        </div>

        <Button
          variant="outline"
          onClick={onNext}
          disabled={!canGoNext}
          className="gap-2"
        >
          Дальше
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};
