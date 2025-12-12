/**
 * Content Creator Service
 * API client for managing elements and lessons
 */
import { apiClient } from '@/integrations/api/client';

export interface ElementListItem {
  id: number;
  title: string;
  element_type: 'text_problem' | 'quick_question' | 'theory' | 'video';
  description: string;
  created_at: string;
  is_public: boolean;
  created_by?: {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
  };
  difficulty?: number;
  estimated_time_minutes?: number;
}

export interface LessonListItem {
  id: number;
  title: string;
  description: string;
  total_duration_minutes: number;
  total_max_score: number;
  elements_count: number;
  created_at: string;
  is_public: boolean;
  created_by?: {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
  };
  subject?: {
    id: number;
    name: string;
  };
}

export interface ElementDetail extends ElementListItem {
  content: string;
  video_url?: string;
  max_score?: number;
  correct_answer?: string;
}

export interface LessonDetail extends LessonListItem {
  elements: Array<{
    id: number;
    element: ElementListItem;
    order: number;
    is_optional: boolean;
    custom_instructions?: string;
  }>;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  count: number;
  next?: string | null;
  previous?: string | null;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export const contentCreatorService = {
  // ============================================
  // Elements API
  // ============================================

  /**
   * Получить список элементов
   * @param params Параметры фильтрации
   */
  getElements: async (params?: {
    type?: string;
    created_by?: 'me' | string;
    search?: string;
    page?: number;
  }): Promise<PaginatedResponse<ElementListItem>> => {
    const queryParams = new URLSearchParams();

    if (params?.type) queryParams.append('type', params.type);
    if (params?.created_by) queryParams.append('created_by', params.created_by);
    if (params?.search) queryParams.append('search', params.search);
    if (params?.page) queryParams.append('page', params.page.toString());

    const response = await apiClient.get(
      `/knowledge-graph/elements/?${queryParams.toString()}`
    );

    return response.data;
  },

  /**
   * Получить детали элемента
   */
  getElement: async (id: number): Promise<ApiResponse<ElementDetail>> => {
    const response = await apiClient.get(`/knowledge-graph/elements/${id}/`);
    return response.data;
  },

  /**
   * Создать новый элемент
   */
  createElement: async (data: Partial<ElementDetail>): Promise<ApiResponse<ElementDetail>> => {
    const response = await apiClient.post('/knowledge-graph/elements/', data);
    return response.data;
  },

  /**
   * Обновить элемент
   */
  updateElement: async (id: number, data: Partial<ElementDetail>): Promise<ApiResponse<ElementDetail>> => {
    const response = await apiClient.patch(`/knowledge-graph/elements/${id}/`, data);
    return response.data;
  },

  /**
   * Удалить элемент
   */
  deleteElement: async (id: number): Promise<void> => {
    await apiClient.delete(`/knowledge-graph/elements/${id}/`);
  },

  /**
   * Копировать элемент (создать дубликат)
   */
  copyElement: async (id: number): Promise<ApiResponse<ElementDetail>> => {
    // Получить оригинал
    const original = await contentCreatorService.getElement(id);

    // Создать копию с "_copy" суффиксом
    const copy = {
      ...original.data,
      title: `${original.data.title}_copy`,
      is_public: false, // Копии приватные по умолчанию
    };

    // Удалить поля которые не нужны при создании
    delete (copy as any).id;
    delete (copy as any).created_at;
    delete (copy as any).created_by;

    return contentCreatorService.createElement(copy);
  },

  // ============================================
  // Lessons API
  // ============================================

  /**
   * Получить список уроков
   */
  getLessons: async (params?: {
    subject?: number;
    created_by?: 'me' | string;
    search?: string;
    page?: number;
  }): Promise<PaginatedResponse<LessonListItem>> => {
    const queryParams = new URLSearchParams();

    if (params?.subject) queryParams.append('subject', params.subject.toString());
    if (params?.created_by) queryParams.append('created_by', params.created_by);
    if (params?.search) queryParams.append('search', params.search);
    if (params?.page) queryParams.append('page', params.page.toString());

    const response = await apiClient.get(
      `/knowledge-graph/lessons/?${queryParams.toString()}`
    );

    return response.data;
  },

  /**
   * Получить детали урока
   */
  getLesson: async (id: number): Promise<ApiResponse<LessonDetail>> => {
    const response = await apiClient.get(`/knowledge-graph/lessons/${id}/`);
    return response.data;
  },

  /**
   * Создать новый урок
   */
  createLesson: async (data: Partial<LessonDetail> & { element_ids?: number[] }): Promise<ApiResponse<LessonDetail>> => {
    // Извлечь element_ids из payload (они не принимаются напрямую backend)
    const { element_ids, ...lessonData } = data;

    // Шаг 1: Создать урок
    const createResponse = await apiClient.post('/knowledge-graph/lessons/', lessonData);
    const createdLesson = createResponse.data.data;

    // Шаг 2: Добавить элементы в урок (если указаны)
    if (element_ids && element_ids.length > 0) {
      for (let i = 0; i < element_ids.length; i++) {
        await apiClient.post(`/knowledge-graph/lessons/${createdLesson.id}/elements/`, {
          element_id: element_ids[i],
          order: i + 1, // Порядок начинается с 1
          is_optional: false,
        });
      }

      // Шаг 3: Пересчитать totals (backend должен это делать автоматически)
      // Получить обновленный урок с элементами
      const updatedResponse = await apiClient.get(`/knowledge-graph/lessons/${createdLesson.id}/`);
      return updatedResponse.data;
    }

    return createResponse.data;
  },

  /**
   * Обновить урок
   */
  updateLesson: async (id: number, data: Partial<LessonDetail> & { element_ids?: number[] }): Promise<ApiResponse<LessonDetail>> => {
    // Извлечь element_ids из payload
    const { element_ids, ...lessonData } = data;

    // Шаг 1: Обновить основные поля урока
    await apiClient.patch(`/knowledge-graph/lessons/${id}/`, lessonData);

    // Шаг 2: Если указаны element_ids, обновить элементы урока
    if (element_ids !== undefined) {
      // Получить текущие элементы урока
      const currentLessonResponse = await apiClient.get(`/knowledge-graph/lessons/${id}/`);
      const currentElements = currentLessonResponse.data.data.elements_list || [];

      // Удалить элементы которые больше не нужны
      const currentElementIds = new Set(currentElements.map((el: any) => el.element.id));
      const newElementIds = new Set(element_ids);

      for (const current of currentElements) {
        if (!newElementIds.has(current.element.id)) {
          // Удалить элемент из урока
          await apiClient.delete(`/knowledge-graph/lessons/${id}/elements/${current.id}/`);
        }
      }

      // Добавить новые элементы и обновить порядок
      for (let i = 0; i < element_ids.length; i++) {
        const elementId = element_ids[i];
        const existingElement = currentElements.find((el: any) => el.element.id === elementId);

        if (existingElement) {
          // Обновить порядок существующего элемента
          await apiClient.patch(`/knowledge-graph/lessons/${id}/elements/${existingElement.id}/`, {
            order: i + 1,
          });
        } else {
          // Добавить новый элемент
          await apiClient.post(`/knowledge-graph/lessons/${id}/elements/`, {
            element_id: elementId,
            order: i + 1,
            is_optional: false,
          });
        }
      }
    }

    // Шаг 3: Получить обновленный урок
    const updatedResponse = await apiClient.get(`/knowledge-graph/lessons/${id}/`);
    return updatedResponse.data;
  },

  /**
   * Удалить урок
   */
  deleteLesson: async (id: number): Promise<void> => {
    await apiClient.delete(`/knowledge-graph/lessons/${id}/`);
  },

  /**
   * Копировать урок (создать дубликат)
   */
  copyLesson: async (id: number): Promise<ApiResponse<LessonDetail>> => {
    // Получить оригинал
    const original = await contentCreatorService.getLesson(id);

    // Создать копию с "_copy" суффиксом
    const copy = {
      ...original.data,
      title: `${original.data.title}_copy`,
      is_public: false,
    };

    // Удалить поля которые не нужны при создании
    delete (copy as any).id;
    delete (copy as any).created_at;
    delete (copy as any).created_by;
    delete (copy as any).elements; // Elements добавляются отдельно
    delete (copy as any).elements_count;
    delete (copy as any).total_duration_minutes;
    delete (copy as any).total_max_score;

    return contentCreatorService.createLesson(copy);
  },
};
