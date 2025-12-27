import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Clock, Star, TrendingUp, FileText, HelpCircle, BookOpen, Video as VideoIcon } from 'lucide-react';
import { TextProblem } from './element-types/TextProblem';
import { QuickQuestion } from './element-types/QuickQuestion';
import { Theory } from './element-types/Theory';
import { Video } from './element-types/Video';
import type { ElementCardProps } from '@/types/knowledgeGraph';

export const ElementCard: React.FC<ElementCardProps> = ({
  element,
  progress,
  onSubmit,
  onError,
  isLoading = false,
  readOnly = false,
}) => {
  // Обработка ошибок с передачей в onError callback
  const handleSubmit = async (answer: any) => {
    try {
      await onSubmit(answer);
    } catch (error) {
      if (onError) {
        onError(error as Error);
      }
      throw error;
    }
  };

  // Иконка в зависимости от типа элемента
  const getElementIcon = () => {
    switch (element.element_type) {
      case 'text_problem':
        return <FileText className="h-5 w-5" />;
      case 'quick_question':
        return <HelpCircle className="h-5 w-5" />;
      case 'theory':
        return <BookOpen className="h-5 w-5" />;
      case 'video':
        return <VideoIcon className="h-5 w-5" />;
      default:
        return <FileText className="h-5 w-5" />;
    }
  };

  // Цвет badge в зависимости от статуса
  const getStatusBadge = () => {
    if (!progress) {
      return <Badge variant="secondary">Не начато</Badge>;
    }

    switch (progress.status) {
      case 'not_started':
        return <Badge variant="secondary">Не начато</Badge>;
      case 'in_progress':
        return <Badge variant="default" className="bg-blue-500">В процессе</Badge>;
      case 'completed':
        return <Badge variant="default" className="bg-green-500">Выполнено</Badge>;
      case 'skipped':
        return <Badge variant="outline">Пропущено</Badge>;
      default:
        return <Badge variant="secondary">Неизвестно</Badge>;
    }
  };

  // Цвет сложности
  const getDifficultyColor = (difficulty: number): string => {
    if (difficulty <= 3) return 'text-green-600 dark:text-green-400';
    if (difficulty <= 7) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  // Рендеринг содержимого в зависимости от типа
  const renderContent = () => {
    switch (element.element_type) {
      case 'text_problem':
        return (
          <TextProblem
            element={element}
            progress={progress}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            readOnly={readOnly}
          />
        );
      case 'quick_question':
        return (
          <QuickQuestion
            element={element}
            progress={progress}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            readOnly={readOnly}
          />
        );
      case 'theory':
        return (
          <Theory
            element={element}
            progress={progress}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            readOnly={readOnly}
          />
        );
      case 'video':
        return (
          <Video
            element={element}
            progress={progress}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            readOnly={readOnly}
          />
        );
      default:
        return (
          <Alert variant="destructive">
            <AlertDescription>
              Неподдерживаемый тип элемента: {element.element_type}
            </AlertDescription>
          </Alert>
        );
    }
  };

  return (
    <Card className="w-full shadow-md hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 flex-1">
            <div className="mt-1 text-primary">{getElementIcon()}</div>
            <div className="flex-1 space-y-1">
              <CardTitle className="text-xl">{element.title}</CardTitle>
              <CardDescription className="text-sm">
                {element.description}
              </CardDescription>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            {getStatusBadge()}
            <Badge variant="outline">{element.element_type_display}</Badge>
          </div>
        </div>

        {/* Метаданные элемента */}
        <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Star className={`h-4 w-4 ${getDifficultyColor(element.difficulty)}`} />
            <span>Сложность: {element.difficulty}/10</span>
          </div>

          <div className="flex items-center gap-1.5">
            <Clock className="h-4 w-4" />
            <span>~{element.estimated_time_minutes} мин</span>
          </div>

          <div className="flex items-center gap-1.5">
            <TrendingUp className="h-4 w-4" />
            <span>Макс. балл: {element.max_score}</span>
          </div>

          {progress?.attempts && progress.attempts > 0 && (
            <Badge variant="secondary" className="text-xs">
              Попыток: {progress.attempts}
            </Badge>
          )}
        </div>

        {/* Теги */}
        {element.tags && element.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {element.tags.map((tag, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </CardHeader>

      <CardContent>
        {renderContent()}
      </CardContent>
    </Card>
  );
};

// Loading skeleton для ElementCard
export const ElementCardSkeleton: React.FC = () => {
  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 flex-1">
            <Skeleton className="h-5 w-5 rounded-md" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-full" />
            </div>
          </div>
          <Skeleton className="h-6 w-20" />
        </div>

        <div className="flex flex-wrap items-center gap-4 mt-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-28" />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <Skeleton className="h-32 w-full rounded-lg" />
        <Skeleton className="h-10 w-full" />
      </CardContent>
    </Card>
  );
};
