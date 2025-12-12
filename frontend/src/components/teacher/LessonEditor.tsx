/**
 * LessonEditor Component (T023)
 * Редактор урока с выбором элементов и изменением порядка
 *
 * Функционал:
 * - Поля: название, описание, предмет
 * - Выбор элементов из банка
 * - Drag-drop для изменения порядка
 */
import React, { useState, useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useQuery } from '@tanstack/react-query';
import { contentCreatorService } from '@/services/contentCreatorService';
import { apiClient } from '@/integrations/api/client';
import { ElementSelector } from './ElementSelector';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2 } from 'lucide-react';

interface Subject {
  id: number;
  name: string;
}

interface LessonFormData {
  title: string;
  description: string;
  subject_id: number | null;
  element_ids: number[];
  is_public: boolean;
}

interface LessonEditorProps {
  lessonData: LessonFormData;
  onUpdate: (data: LessonFormData) => void;
}

export const LessonEditor: React.FC<LessonEditorProps> = ({ lessonData, onUpdate }) => {
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Загрузка списка предметов (для учителя)
  const { data: subjectsData, isLoading: isLoadingSubjects } = useQuery({
    queryKey: ['teacher', 'subjects'],
    queryFn: async () => {
      const response = await apiClient.get<{ subjects: Subject[] }>('/materials/teacher/subjects/');
      return response.data;
    },
  });

  const subjects = subjectsData?.subjects || [];

  // Загрузка всех элементов (созданных учителем)
  const { data: elementsData, isLoading: isLoadingElements } = useQuery({
    queryKey: ['content-creator', 'all-elements'],
    queryFn: () => contentCreatorService.getElements({ created_by: 'me' }),
    staleTime: 60000,
  });

  const availableElements = elementsData?.data || [];

  // Фильтрация элементов по поисковому запросу
  const filteredElements = useMemo(() => {
    if (!searchQuery) return availableElements;

    const query = searchQuery.toLowerCase();
    return availableElements.filter(
      (el) =>
        el.title.toLowerCase().includes(query) ||
        el.description?.toLowerCase().includes(query) ||
        el.element_type.toLowerCase().includes(query)
    );
  }, [searchQuery, availableElements]);

  // Получить выбранные элементы в правильном порядке
  const selectedElements = useMemo(() => {
    return lessonData.element_ids
      .map((id) => availableElements.find((el) => el.id === id))
      .filter((el): el is typeof availableElements[0] => el !== undefined);
  }, [lessonData.element_ids, availableElements]);

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpdate({ ...lessonData, title: e.target.value });
  };

  const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onUpdate({ ...lessonData, description: e.target.value });
  };

  const handleSubjectChange = (value: string) => {
    onUpdate({ ...lessonData, subject_id: Number(value) });
  };

  const handleElementsChange = (elementIds: number[]) => {
    onUpdate({ ...lessonData, element_ids: elementIds });
  };

  return (
    <div className="space-y-6">
      {/* Название урока */}
      <div className="space-y-2">
        <Label htmlFor="title">Название урока *</Label>
        <Input
          id="title"
          placeholder="Введите название урока (3-200 символов)"
          value={lessonData.title}
          onChange={handleTitleChange}
          maxLength={200}
        />
        <p className="text-xs text-muted-foreground">
          {lessonData.title.length}/200 символов
        </p>
      </div>

      {/* Описание */}
      <div className="space-y-2">
        <Label htmlFor="description">Описание (опционально)</Label>
        <Textarea
          id="description"
          placeholder="Краткое описание урока, цели и задачи..."
          value={lessonData.description}
          onChange={handleDescriptionChange}
          rows={3}
          maxLength={1000}
          className="resize-none"
        />
        <p className="text-xs text-muted-foreground">
          {lessonData.description.length}/1000 символов
        </p>
      </div>

      {/* Выбор предмета */}
      <div className="space-y-2">
        <Label htmlFor="subject">Предмет *</Label>
        {isLoadingSubjects ? (
          <div className="flex items-center gap-2 p-2 border rounded-md">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm text-muted-foreground">Загрузка предметов...</span>
          </div>
        ) : (
          <Select
            value={lessonData.subject_id?.toString() || ''}
            onValueChange={handleSubjectChange}
          >
            <SelectTrigger id="subject">
              <SelectValue placeholder="Выберите предмет" />
            </SelectTrigger>
            <SelectContent>
              {subjects.length === 0 ? (
                <div className="p-2 text-sm text-muted-foreground text-center">
                  Нет доступных предметов
                </div>
              ) : (
                subjects.map((subject) => (
                  <SelectItem key={subject.id} value={subject.id.toString()}>
                    {subject.name}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Выбор элементов */}
      <div className="space-y-2">
        <Label>Элементы урока *</Label>
        <p className="text-sm text-muted-foreground">
          Выберите элементы из банка контента и расставьте их в нужном порядке
        </p>
        {isLoadingElements ? (
          <div className="flex items-center justify-center p-8 border rounded-md">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Загрузка элементов...</p>
            </div>
          </div>
        ) : (
          <ElementSelector
            availableElements={filteredElements}
            selectedElements={selectedElements}
            selectedElementIds={lessonData.element_ids}
            onElementsChange={handleElementsChange}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
        )}
      </div>
    </div>
  );
};
