import React from 'react';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { BookOpen, Clock, Star, Lock, CheckCircle2, PlayCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Интерфейс урока (соответствует backend модели Lesson)
 */
export interface Lesson {
  id: number;
  title: string;
  description: string;
  subject: number;
  subject_name: string;
  is_public: boolean;
  total_duration_minutes: number;
  total_max_score: number;
  elements_count: number;
  created_by: {
    id: number;
    full_name: string;
  };
  created_at: string;
  updated_at: string;
}

/**
 * Интерфейс прогресса урока (соответствует backend модели LessonProgress)
 */
export interface LessonProgress {
  id: number;
  student: number;
  student_name: string;
  graph_lesson: number;
  lesson_title: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'failed';
  completed_elements: number;
  total_elements: number;
  completion_percent: number;
  total_score: number;
  max_possible_score: number;
  started_at?: string;
  completed_at?: string;
  last_activity: string;
  total_time_spent_seconds: number;
  created_at: string;
  updated_at: string;
}

/**
 * Пропсы компонента LessonCard
 */
export interface LessonCardProps {
  lesson: Lesson;
  progress?: LessonProgress;
  onClick?: () => void;
  onNavigate?: (lessonId: number) => void;
  isLocked?: boolean;
  showPreview?: boolean;
  className?: string;
}

/**
 * Получить метку сложности на основе максимального балла и времени
 */
const getDifficulty = (maxScore: number, durationMinutes: number): 'easy' | 'medium' | 'hard' => {
  // Логика определения сложности: комбинация баллов и времени
  const complexityScore = (maxScore / 100) + (durationMinutes / 30);

  if (complexityScore <= 2) return 'easy';
  if (complexityScore <= 4) return 'medium';
  return 'hard';
};

/**
 * Получить цвет для уровня сложности
 */
const getDifficultyColor = (difficulty: 'easy' | 'medium' | 'hard'): string => {
  switch (difficulty) {
    case 'easy':
      return 'text-green-600';
    case 'medium':
      return 'text-yellow-600';
    case 'hard':
      return 'text-red-600';
  }
};

/**
 * Получить текст для уровня сложности
 */
const getDifficultyText = (difficulty: 'easy' | 'medium' | 'hard'): string => {
  switch (difficulty) {
    case 'easy':
      return 'Легкий';
    case 'medium':
      return 'Средний';
    case 'hard':
      return 'Сложный';
  }
};

/**
 * Получить количество звезд для уровня сложности
 */
const getDifficultyStars = (difficulty: 'easy' | 'medium' | 'hard'): number => {
  switch (difficulty) {
    case 'easy':
      return 1;
    case 'medium':
      return 2;
    case 'hard':
      return 3;
  }
};

/**
 * Получить конфигурацию бэйджа статуса
 */
const getStatusBadge = (status: LessonProgress['status'], isLocked: boolean) => {
  if (isLocked) {
    return {
      label: 'Заблокирован',
      variant: 'destructive' as const,
      className: 'bg-red-100 text-red-800 border-red-200',
    };
  }

  switch (status) {
    case 'not_started':
      return {
        label: 'Не начат',
        variant: 'secondary' as const,
        className: 'bg-gray-100 text-gray-800 border-gray-200',
      };
    case 'in_progress':
      return {
        label: 'В процессе',
        variant: 'default' as const,
        className: 'bg-blue-100 text-blue-800 border-blue-200',
      };
    case 'completed':
      return {
        label: 'Завершен',
        variant: 'default' as const,
        className: 'bg-green-100 text-green-800 border-green-200',
      };
    case 'failed':
      return {
        label: 'Не пройден',
        variant: 'destructive' as const,
        className: 'bg-orange-100 text-orange-800 border-orange-200',
      };
    default:
      return {
        label: 'Не начат',
        variant: 'secondary' as const,
        className: 'bg-gray-100 text-gray-800 border-gray-200',
      };
  }
};

/**
 * Форматировать время в читаемый вид
 */
const formatDuration = (minutes: number): string => {
  if (minutes < 60) {
    return `${minutes} мин`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}ч ${mins}мин` : `${hours}ч`;
};

/**
 * Компонент карточки урока для системы графа знаний
 *
 * Отображает информацию об уроке с прогрессом студента
 */
export const LessonCard: React.FC<LessonCardProps> = ({
  lesson,
  progress,
  onClick,
  onNavigate,
  isLocked = false,
  showPreview = true,
  className = '',
}) => {
  const difficulty = getDifficulty(lesson.total_max_score, lesson.total_duration_minutes);
  const difficultyColor = getDifficultyColor(difficulty);
  const difficultyText = getDifficultyText(difficulty);
  const difficultyStars = getDifficultyStars(difficulty);

  const statusBadge = getStatusBadge(
    progress?.status || 'not_started',
    isLocked
  );

  const completionPercent = progress?.completion_percent || 0;
  const elementsCount = lesson.elements_count;
  const completedElements = progress?.completed_elements || 0;

  const handleClick = () => {
    if (isLocked) return;

    if (onClick) {
      onClick();
    } else if (onNavigate) {
      onNavigate(lesson.id);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <TooltipProvider>
      <Card
        className={cn(
          'group transition-all duration-200',
          isLocked
            ? 'opacity-60 cursor-not-allowed'
            : 'hover:shadow-lg hover:scale-[1.02] cursor-pointer',
          className
        )}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        tabIndex={isLocked ? -1 : 0}
        role="button"
        aria-label={`Урок: ${lesson.title}`}
        aria-disabled={isLocked}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center space-x-2">
              <div className={cn(
                'p-2 rounded-lg',
                isLocked ? 'bg-gray-100' : 'bg-primary/10'
              )}>
                {isLocked ? (
                  <Lock className="h-5 w-5 text-gray-500" />
                ) : progress?.status === 'completed' ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : progress?.status === 'in_progress' ? (
                  <PlayCircle className="h-5 w-5 text-blue-600" />
                ) : (
                  <BookOpen className="h-5 w-5 text-primary" />
                )}
              </div>
            </div>

            <Badge
              variant={statusBadge.variant}
              className={cn('text-xs', statusBadge.className)}
            >
              {statusBadge.label}
            </Badge>
          </div>

          <CardTitle className="text-lg leading-tight line-clamp-2 mb-2">
            {lesson.title}
          </CardTitle>

          {lesson.description && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {lesson.description}
            </p>
          )}
        </CardHeader>

        <CardContent className="pb-3 space-y-3">
          {/* Сложность */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Сложность:</span>
            <div className="flex items-center space-x-1">
              <span className={cn('text-sm font-medium', difficultyColor)}>
                {difficultyText}
              </span>
              <div className="flex space-x-0.5">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Star
                    key={i}
                    className={cn(
                      'h-3 w-3',
                      i < difficultyStars
                        ? `${difficultyColor} fill-current`
                        : 'text-gray-300'
                    )}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Информация об уроке */}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center space-x-1">
              <BookOpen className="h-3 w-3" />
              <span>{elementsCount} {elementsCount === 1 ? 'элемент' : 'элементов'}</span>
            </div>
            <div className="flex items-center space-x-1">
              <Clock className="h-3 w-3" />
              <span>{formatDuration(lesson.total_duration_minutes)}</span>
            </div>
          </div>

          {/* Прогресс */}
          {progress && !isLocked && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Прогресс:</span>
                <span className="font-medium">{completionPercent}%</span>
              </div>
              <Progress
                value={completionPercent}
                className={cn(
                  'h-2',
                  progress.status === 'completed' && 'bg-green-100'
                )}
              />
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>
                  {completedElements} из {elementsCount} завершено
                </span>
                {progress.total_score > 0 && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="cursor-help">
                        {progress.total_score} / {progress.max_possible_score} баллов
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Текущий балл / Максимальный балл</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            </div>
          )}

          {/* Превью элементов (опционально) */}
          {showPreview && !isLocked && elementsCount > 0 && (
            <div className="pt-2 border-t border-gray-100">
              <p className="text-xs text-muted-foreground">
                <span className="font-medium">Макс. балл:</span> {lesson.total_max_score}
              </p>
            </div>
          )}
        </CardContent>

        <CardFooter className="pt-0 pb-4">
          <div className="w-full flex items-center justify-between">
            {isLocked ? (
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <Lock className="h-4 w-4" />
                <span>Завершите предыдущие уроки</span>
              </div>
            ) : (
              <div className="text-sm text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                Нажмите для открытия →
              </div>
            )}

            {progress?.completed_at && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center space-x-1 text-xs text-green-600">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Завершено</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>
                    Завершено:{' '}
                    {new Date(progress.completed_at).toLocaleDateString('ru-RU', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })}
                  </p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        </CardFooter>
      </Card>
    </TooltipProvider>
  );
};
