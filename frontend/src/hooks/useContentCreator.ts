/**
 * Custom hook for Content Creator functionality
 * Manages elements and lessons data fetching and actions
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useToast } from '@/hooks/use-toast';
import {
  contentCreatorService,
  ElementListItem,
  LessonListItem,
  ElementDetail,
  LessonDetail,
} from '@/services/contentCreatorService';

export interface ContentFilters {
  visibility: 'mine' | 'all';
  type?: string;
  search?: string;
  page: number;
}

export const useContentCreator = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Фильтры для элементов
  const [elementFilters, setElementFilters] = useState<ContentFilters>({
    visibility: 'mine',
    type: undefined,
    search: '',
    page: 1,
  });

  // Фильтры для уроков
  const [lessonFilters, setLessonFilters] = useState<ContentFilters>({
    visibility: 'mine',
    search: '',
    page: 1,
  });

  // Выбранные элементы для bulk операций
  const [selectedElements, setSelectedElements] = useState<Set<number>>(new Set());
  const [selectedLessons, setSelectedLessons] = useState<Set<number>>(new Set());

  // ============================================
  // Elements Queries
  // ============================================

  const {
    data: elementsData,
    isLoading: elementsLoading,
    error: elementsError,
    refetch: refetchElements,
  } = useQuery({
    queryKey: ['content-creator', 'elements', elementFilters],
    queryFn: () =>
      contentCreatorService.getElements({
        created_by: elementFilters.visibility === 'mine' ? 'me' : undefined,
        type: elementFilters.type,
        search: elementFilters.search || undefined,
        page: elementFilters.page,
      }),
    staleTime: 60000, // 1 минута
  });

  // ============================================
  // Lessons Queries
  // ============================================

  const {
    data: lessonsData,
    isLoading: lessonsLoading,
    error: lessonsError,
    refetch: refetchLessons,
  } = useQuery({
    queryKey: ['content-creator', 'lessons', lessonFilters],
    queryFn: () =>
      contentCreatorService.getLessons({
        created_by: lessonFilters.visibility === 'mine' ? 'me' : undefined,
        search: lessonFilters.search || undefined,
        page: lessonFilters.page,
      }),
    staleTime: 60000,
  });

  // ============================================
  // Element Mutations
  // ============================================

  const createElementMutation = useMutation({
    mutationFn: (data: Partial<ElementDetail>) => contentCreatorService.createElement(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'elements'] });
      toast({
        title: 'Успех',
        description: 'Элемент успешно создан',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.error || 'Не удалось создать элемент',
        variant: 'destructive',
      });
    },
  });

  const updateElementMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ElementDetail> }) =>
      contentCreatorService.updateElement(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'elements'] });
      toast({
        title: 'Успех',
        description: 'Элемент успешно обновлен',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.error || 'Не удалось обновить элемент',
        variant: 'destructive',
      });
    },
  });

  const deleteElementMutation = useMutation({
    mutationFn: (id: number) => contentCreatorService.deleteElement(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'elements'] });
      toast({
        title: 'Успех',
        description: 'Элемент успешно удален',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.error || 'Не удалось удалить элемент',
        variant: 'destructive',
      });
    },
  });

  const copyElementMutation = useMutation({
    mutationFn: (id: number) => contentCreatorService.copyElement(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'elements'] });
      toast({
        title: 'Успех',
        description: 'Элемент успешно скопирован',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.error || 'Не удалось скопировать элемент',
        variant: 'destructive',
      });
    },
  });

  // ============================================
  // Lesson Mutations
  // ============================================

  const createLessonMutation = useMutation({
    mutationFn: (data: Partial<LessonDetail>) => contentCreatorService.createLesson(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'lessons'] });
      toast({
        title: 'Успех',
        description: 'Урок успешно создан',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.error || 'Не удалось создать урок',
        variant: 'destructive',
      });
    },
  });

  const updateLessonMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<LessonDetail> }) =>
      contentCreatorService.updateLesson(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'lessons'] });
      toast({
        title: 'Успех',
        description: 'Урок успешно обновлен',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.error || 'Не удалось обновить урок',
        variant: 'destructive',
      });
    },
  });

  const deleteLessonMutation = useMutation({
    mutationFn: (id: number) => contentCreatorService.deleteLesson(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'lessons'] });
      toast({
        title: 'Успех',
        description: 'Урок успешно удален',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.error || 'Не удалось удалить урок',
        variant: 'destructive',
      });
    },
  });

  const copyLessonMutation = useMutation({
    mutationFn: (id: number) => contentCreatorService.copyLesson(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-creator', 'lessons'] });
      toast({
        title: 'Успех',
        description: 'Урок успешно скопирован',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error.response?.data?.error || 'Не удалось скопировать урок',
        variant: 'destructive',
      });
    },
  });

  // ============================================
  // Helper Functions
  // ============================================

  const toggleElementSelection = (id: number) => {
    setSelectedElements((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const toggleLessonSelection = (id: number) => {
    setSelectedLessons((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const clearElementSelection = () => setSelectedElements(new Set());
  const clearLessonSelection = () => setSelectedLessons(new Set());

  const bulkDeleteElements = async () => {
    const promises = Array.from(selectedElements).map((id) =>
      deleteElementMutation.mutateAsync(id)
    );
    await Promise.all(promises);
    clearElementSelection();
  };

  const bulkDeleteLessons = async () => {
    const promises = Array.from(selectedLessons).map((id) =>
      deleteLessonMutation.mutateAsync(id)
    );
    await Promise.all(promises);
    clearLessonSelection();
  };

  return {
    // Elements data
    elements: elementsData?.data ?? [],
    elementsCount: elementsData?.count ?? 0,
    elementsLoading,
    elementsError,
    refetchElements,

    // Lessons data
    lessons: lessonsData?.data ?? [],
    lessonsCount: lessonsData?.count ?? 0,
    lessonsLoading,
    lessonsError,
    refetchLessons,

    // Filters
    elementFilters,
    setElementFilters,
    lessonFilters,
    setLessonFilters,

    // Selection
    selectedElements,
    selectedLessons,
    toggleElementSelection,
    toggleLessonSelection,
    clearElementSelection,
    clearLessonSelection,

    // Actions
    createElement: createElementMutation.mutate,
    updateElement: updateElementMutation.mutate,
    deleteElement: deleteElementMutation.mutate,
    copyElement: copyElementMutation.mutate,

    createLesson: createLessonMutation.mutate,
    updateLesson: updateLessonMutation.mutate,
    deleteLesson: deleteLessonMutation.mutate,
    copyLesson: copyLessonMutation.mutate,

    bulkDeleteElements,
    bulkDeleteLessons,

    // Loading states
    isCreating: createElementMutation.isPending || createLessonMutation.isPending,
    isUpdating: updateElementMutation.isPending || updateLessonMutation.isPending,
    isDeleting: deleteElementMutation.isPending || deleteLessonMutation.isPending,
  };
};
