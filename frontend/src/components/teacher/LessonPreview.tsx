/**
 * LessonPreview Component (T023)
 * Превью урока - как будет выглядеть для студента
 *
 * Функционал:
 * - Показать список элементов в порядке прохождения
 * - Отобразить базовую информацию об уроке
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { contentCreatorService } from '@/services/contentCreatorService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Clock, Award, BookOpen, CheckCircle2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface LessonPreviewProps {
  title: string;
  description: string;
  elementIds: number[];
}

export const LessonPreview: React.FC<LessonPreviewProps> = ({
  title,
  description,
  elementIds,
}) => {
  // Загрузка данных об элементах
  const { data: elementsData, isLoading } = useQuery({
    queryKey: ['content-creator', 'all-elements'],
    queryFn: () => contentCreatorService.getElements({ created_by: 'me' }),
    staleTime: 60000,
  });

  const availableElements = elementsData?.data || [];

  // Получить выбранные элементы в правильном порядке
  const selectedElements = elementIds
    .map((id) => availableElements.find((el) => el.id === id))
    .filter((el): el is typeof availableElements[0] => el !== undefined);

  // Вычислить общую статистику
  const totalTime = selectedElements.reduce(
    (sum, el) => sum + (el.estimated_time_minutes || 0),
    0
  );
  const totalScore = selectedElements.reduce(
    (sum, el) => sum + (el.max_score || 0),
    0
  );

  const getElementTypeLabel = (type: string): string => {
    const labels: Record<string, string> = {
      text_problem: 'Задача',
      quick_question: 'Вопрос',
      theory: 'Теория',
      video: 'Видео',
    };
    return labels[type] || type;
  };

  const getElementTypeIcon = (type: string): string => {
    const icons: Record<string, string> = {
      text_problem: '📝',
      quick_question: '❓',
      theory: '📚',
      video: '🎥',
    };
    return icons[type] || '📄';
  };

  const getElementTypeBadgeColor = (type: string): string => {
    const colors: Record<string, string> = {
      text_problem: 'bg-blue-100 text-blue-800',
      quick_question: 'bg-green-100 text-green-800',
      theory: 'bg-purple-100 text-purple-800',
      video: 'bg-orange-100 text-orange-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Загрузка превью...</p>
        </div>
      </div>
    );
  }

  if (!title && elementIds.length === 0) {
    return (
      <Alert>
        <AlertDescription>
          Заполните название урока и выберите хотя бы один элемент для предпросмотра
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Заголовок урока */}
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">
            {title || 'Без названия'}
          </CardTitle>
          {description && (
            <CardDescription className="text-base mt-2">
              {description}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-primary" />
              <div>
                <p className="text-sm text-muted-foreground">Элементов</p>
                <p className="text-lg font-semibold">{selectedElements.length}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-primary" />
              <div>
                <p className="text-sm text-muted-foreground">Время</p>
                <p className="text-lg font-semibold">{totalTime} мин</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Award className="h-5 w-5 text-primary" />
              <div>
                <p className="text-sm text-muted-foreground">Макс. баллы</p>
                <p className="text-lg font-semibold">{totalScore}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Список элементов */}
      {selectedElements.length === 0 ? (
        <Alert>
          <AlertDescription>
            Добавьте элементы в урок для предпросмотра
          </AlertDescription>
        </Alert>
      ) : (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Содержание урока</h3>
          <div className="space-y-2">
            {selectedElements.map((element, index) => (
              <Card key={element.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    {/* Номер шага */}
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground font-semibold text-sm shrink-0">
                      {index + 1}
                    </div>

                    {/* Информация об элементе */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xl">{getElementTypeIcon(element.element_type)}</span>
                        <h4 className="font-medium text-base">{element.title}</h4>
                        <Badge
                          className={`text-xs ${getElementTypeBadgeColor(
                            element.element_type
                          )}`}
                          variant="secondary"
                        >
                          {getElementTypeLabel(element.element_type)}
                        </Badge>
                      </div>

                      {element.description && (
                        <p className="text-sm text-muted-foreground mb-2">
                          {element.description}
                        </p>
                      )}

                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        {element.estimated_time_minutes && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            <span>{element.estimated_time_minutes} мин</span>
                          </div>
                        )}
                        {element.max_score && (
                          <div className="flex items-center gap-1">
                            <Award className="h-3 w-3" />
                            <span>до {element.max_score} баллов</span>
                          </div>
                        )}
                        {element.difficulty && (
                          <div className="flex items-center gap-1">
                            <span>Сложность: {element.difficulty}/10</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Статус (placeholder для студента) */}
                    <div className="shrink-0">
                      <div className="w-6 h-6 rounded-full border-2 border-muted flex items-center justify-center">
                        <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Примечание */}
      <Alert>
        <AlertDescription className="text-sm">
          <strong>Примечание:</strong> Это превью показывает, как урок будет выглядеть для студента.
          Фактический прогресс и результаты будут отображаться после начала урока.
        </AlertDescription>
      </Alert>
    </div>
  );
};
