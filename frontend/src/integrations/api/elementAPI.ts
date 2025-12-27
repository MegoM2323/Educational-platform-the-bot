/**
 * Element API Client
 * API для работы с элементами графа знаний
 */

import { unifiedAPI } from './unifiedClient';
import type { Element } from '@/types/knowledgeGraph';

export interface CreateElementPayload {
  title: string;
  description?: string;
  element_type: 'text_problem' | 'quick_question' | 'theory' | 'video';
  content: string;
  options?: Array<{ text: string; is_correct: boolean }>;
  video_url?: string;
  video_type?: 'youtube' | 'vimeo' | 'other';
  difficulty: number;
  estimated_time_minutes: number;
  max_score: number;
  tags?: string[];
  is_public: boolean;
}

export interface UpdateElementPayload {
  title?: string;
  description?: string;
  content?: string;
  options?: Array<{ text: string; is_correct: boolean }>;
  video_url?: string;
  video_type?: 'youtube' | 'vimeo' | 'other';
  difficulty?: number;
  estimated_time_minutes?: number;
  max_score?: number;
  tags?: string[];
  is_public?: boolean;
}

export const elementAPI = {
  /**
   * Получить список элементов с фильтрами
   * GET /api/knowledge-graph/elements/
   */
  getElements: async (filters?: {
    type?: string;
    created_by?: string;
    search?: string;
  }): Promise<Element[]> => {
    const response = await unifiedAPI.get<
      { success: boolean; data: Element[]; count?: number } | { results: Element[] } | Element[]
    >('/knowledge-graph/elements/', { params: filters });

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      return [];
    }

    // Backend возвращает { success: true, data: [...], count: N }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      const elements = (data as { success: boolean; data: Element[] }).data;
      return Array.isArray(elements) ? elements : [];
    }

    // Альтернативный формат { results: [...] }
    if ('results' in data) {
      const results = (data as { results: Element[] }).results;
      return Array.isArray(results) ? results : [];
    }

    // Прямой массив
    if (Array.isArray(data)) {
      return data;
    }

    return [];
  },

  /**
   * Создать новый элемент
   * POST /api/knowledge-graph/elements/
   */
  createElement: async (payload: CreateElementPayload): Promise<Element> => {
    // Преобразование payload для backend
    const backendPayload: any = {
      title: payload.title,
      description: payload.description || '',
      element_type: payload.element_type,
      difficulty: payload.difficulty,
      estimated_time_minutes: payload.estimated_time_minutes,
      max_score: payload.max_score,
      tags: payload.tags || [],
      is_public: payload.is_public,
    };

    // Формирование content JSON в зависимости от типа
    if (payload.element_type === 'text_problem') {
      backendPayload.content = {
        problem_text: payload.content,
        hints: [],
      };
    } else if (payload.element_type === 'quick_question') {
      const correctIndex = payload.options?.findIndex((opt) => opt.is_correct) ?? 0;
      backendPayload.content = {
        question: payload.content,
        choices: payload.options?.map((opt) => opt.text) || [],
        correct_answer: correctIndex,
      };
    } else if (payload.element_type === 'theory') {
      backendPayload.content = {
        text: payload.content,
      };
    } else if (payload.element_type === 'video') {
      backendPayload.content = {
        url: payload.video_url || '',
        platform: payload.video_type || 'youtube',
        description: payload.content || '',
      };
    }

    const response = await unifiedAPI.post<
      { success: boolean; data: Element } | Element
    >('/knowledge-graph/elements/', backendPayload);

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      throw new Error('Ошибка при создании элемента');
    }

    // Backend возвращает { success: true, data: Element }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: Element }).data;
    }

    return data as Element;
  },

  /**
   * Получить элемент по ID
   * GET /api/knowledge-graph/elements/{id}/
   */
  getElement: async (elementId: string): Promise<Element> => {
    const response = await unifiedAPI.get<
      { success: boolean; data: Element } | Element
    >(`/knowledge-graph/elements/${elementId}/`);

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      throw new Error('Элемент не найден');
    }

    // Backend возвращает { success: true, data: Element }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: Element }).data;
    }

    return data as Element;
  },

  /**
   * Обновить элемент
   * PATCH /api/knowledge-graph/elements/{id}/
   */
  updateElement: async (
    elementId: string,
    payload: UpdateElementPayload
  ): Promise<Element> => {
    const response = await unifiedAPI.patch<
      { success: boolean; data: Element } | Element
    >(`/knowledge-graph/elements/${elementId}/`, payload);

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      throw new Error('Ошибка при обновлении элемента');
    }

    // Backend возвращает { success: true, data: Element }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: Element }).data;
    }

    return data as Element;
  },

  /**
   * Удалить элемент
   * DELETE /api/knowledge-graph/elements/{id}/
   */
  deleteElement: async (elementId: string): Promise<void> => {
    const response = await unifiedAPI.delete<void>(
      `/knowledge-graph/elements/${elementId}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }
  },
};
