/**
 * ElementSelector Component (T023)
 * Выбор и упорядочивание элементов для урока
 *
 * Функционал:
 * - Слева: банк всех элементов с поиском
 * - Справа: выбранные элементы с drag-drop для изменения порядка
 */
import React from 'react';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Search, Trash2, GripVertical, ChevronUp, ChevronDown } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface Element {
  id: number;
  title: string;
  element_type: 'text_problem' | 'quick_question' | 'theory' | 'video';
  description: string;
  difficulty?: number;
  estimated_time_minutes?: number;
}

interface ElementSelectorProps {
  availableElements: Element[];
  selectedElements: Element[];
  selectedElementIds: number[];
  onElementsChange: (elementIds: number[]) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export const ElementSelector: React.FC<ElementSelectorProps> = ({
  availableElements,
  selectedElements,
  selectedElementIds,
  onElementsChange,
  searchQuery,
  onSearchChange,
}) => {
  const toggleElement = (elementId: number) => {
    if (selectedElementIds.includes(elementId)) {
      // Удалить из выбранных
      onElementsChange(selectedElementIds.filter((id) => id !== elementId));
    } else {
      // Добавить в конец
      onElementsChange([...selectedElementIds, elementId]);
    }
  };

  const removeElement = (elementId: number) => {
    onElementsChange(selectedElementIds.filter((id) => id !== elementId));
  };

  const moveElement = (index: number, direction: 'up' | 'down') => {
    const newOrder = [...selectedElementIds];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;

    if (targetIndex < 0 || targetIndex >= newOrder.length) return;

    // Swap элементы
    [newOrder[index], newOrder[targetIndex]] = [newOrder[targetIndex], newOrder[index]];
    onElementsChange(newOrder);
  };

  const getElementTypeLabel = (type: string): string => {
    const labels: Record<string, string> = {
      text_problem: 'Задача',
      quick_question: 'Вопрос',
      theory: 'Теория',
      video: 'Видео',
    };
    return labels[type] || type;
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

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Левая панель: Банк элементов */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Банк элементов</h3>
          <span className="text-xs text-muted-foreground">
            {availableElements.length} элементов
          </span>
        </div>

        {/* Поиск */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Поиск элементов..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Список доступных элементов */}
        <div className="border rounded-md max-h-96 overflow-y-auto">
          {availableElements.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              {searchQuery ? 'Элементы не найдены' : 'Нет доступных элементов'}
            </div>
          ) : (
            <div className="divide-y">
              {availableElements.map((element) => {
                const isSelected = selectedElementIds.includes(element.id);

                return (
                  <div
                    key={element.id}
                    className={`p-3 hover:bg-accent/50 cursor-pointer transition-colors ${
                      isSelected ? 'bg-accent/30' : ''
                    }`}
                    onClick={() => toggleElement(element.id)}
                  >
                    <div className="flex items-start gap-3">
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => toggleElement(element.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm truncate">{element.title}</span>
                          <Badge
                            className={`text-xs shrink-0 ${getElementTypeBadgeColor(
                              element.element_type
                            )}`}
                            variant="secondary"
                          >
                            {getElementTypeLabel(element.element_type)}
                          </Badge>
                        </div>
                        {element.description && (
                          <p className="text-xs text-muted-foreground line-clamp-2 mb-1">
                            {element.description}
                          </p>
                        )}
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          {element.difficulty && (
                            <span>Сложность: {element.difficulty}/10</span>
                          )}
                          {element.estimated_time_minutes && (
                            <span>{element.estimated_time_minutes} мин</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Правая панель: Выбранные элементы */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Выбранные элементы</h3>
          <span className="text-xs text-muted-foreground">
            {selectedElements.length} выбрано
          </span>
        </div>

        {selectedElements.length === 0 ? (
          <div className="border rounded-md p-8 text-center">
            <p className="text-sm text-muted-foreground">
              Выберите элементы из банка слева
            </p>
          </div>
        ) : (
          <div className="space-y-2 border rounded-md p-3 max-h-96 overflow-y-auto">
            {selectedElements.map((element, index) => (
              <div
                key={element.id}
                className="flex items-center gap-2 p-3 border rounded-md bg-card hover:bg-accent/50 transition-colors"
              >
                {/* Кнопки перемещения */}
                <div className="flex flex-col gap-0.5">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-5 w-5 p-0"
                    onClick={() => moveElement(index, 'up')}
                    disabled={index === 0}
                  >
                    <ChevronUp className="h-3 w-3" />
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-5 w-5 p-0"
                    onClick={() => moveElement(index, 'down')}
                    disabled={index === selectedElements.length - 1}
                  >
                    <ChevronDown className="h-3 w-3" />
                  </Button>
                </div>

                <GripVertical className="h-4 w-4 text-muted-foreground shrink-0" />

                {/* Информация об элементе */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-muted-foreground shrink-0">
                      #{index + 1}
                    </span>
                    <span className="font-medium text-sm truncate">{element.title}</span>
                    <Badge
                      className={`text-xs shrink-0 ${getElementTypeBadgeColor(
                        element.element_type
                      )}`}
                      variant="secondary"
                    >
                      {getElementTypeLabel(element.element_type)}
                    </Badge>
                  </div>
                  {element.estimated_time_minutes && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {element.estimated_time_minutes} мин
                    </p>
                  )}
                </div>

                {/* Кнопка удаления */}
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => removeElement(element.id)}
                  className="text-destructive hover:text-destructive hover:bg-destructive/10 shrink-0"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}

        {/* Статистика */}
        {selectedElements.length > 0 && (
          <div className="border rounded-md p-3 bg-muted/50">
            <h4 className="text-xs font-medium mb-2">Статистика урока</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">Всего элементов:</span>
                <span className="ml-2 font-medium">{selectedElements.length}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Примерное время:</span>
                <span className="ml-2 font-medium">
                  {selectedElements.reduce(
                    (sum, el) => sum + (el.estimated_time_minutes || 0),
                    0
                  )}{' '}
                  мин
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
