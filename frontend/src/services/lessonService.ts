/**
 * Lesson Service - API client for lesson viewer
 * Handles all lesson-related API calls for student lesson viewing
 */

import { unifiedAPI } from '@/integrations/api/unifiedClient';
import type { ApiResponse } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';

// Types
export interface LessonElement {
  id: string;
  title: string;
  description: string;
  element_type: 'text_problem' | 'quick_question' | 'theory' | 'video';
  element_type_display: string;
  content: any;
  difficulty: number;
  estimated_time_minutes: number;
  max_score: number;
  tags: string[];
  order: number;
}

export interface Lesson {
  id: string;
  title: string;
  description: string;
  subject: {
    id: number;
    name: string;
  };
  total_duration_minutes: number;
  total_max_score: number;
  elements: LessonElement[];
  created_at: string;
}

export interface ElementProgress {
  id: string;
  element: {
    id: string;
    title: string;
  };
  answer: any;
  score: number | null;
  max_score: number;
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped';
  started_at: string | null;
  completed_at: string | null;
  attempts: number;
}

export interface LessonProgress {
  id: string;
  lesson: {
    id: string;
    title: string;
  };
  graph_lesson_id: string;
  status: 'not_started' | 'in_progress' | 'completed';
  started_at: string | null;
  completed_at: string | null;
  completed_elements_count: number;
  total_elements_count: number;
  total_score: number;
  max_total_score: number;
  score_percent: number;
  element_progress: ElementProgress[];
}

export interface PrerequisiteCheck {
  can_start: boolean;
  missing_prerequisites: Array<{
    id: string;
    title: string;
  }>;
  message?: string;
}

export interface SubmitAnswerRequest {
  answer: any;
  graph_lesson_id: string;
}

export interface SubmitAnswerResponse {
  id: string;
  score: number;
  max_score: number;
  status: string;
  message?: string;
}

class LessonService {
  /**
   * Получить урок со всеми элементами
   */
  async getLesson(lessonId: string): Promise<Lesson> {
    logger.info('[LessonService] Fetching lesson:', lessonId);

    const response: ApiResponse<Lesson> = await unifiedAPI.get(
      `/knowledge-graph/lessons/${lessonId}/`
    );

    if (!response.success || !response.data) {
      const error = response.error || 'Failed to fetch lesson';
      logger.error('[LessonService] Get lesson failed:', error);
      throw new Error(error);
    }

    logger.info('[LessonService] Lesson fetched successfully:', response.data.title);
    return response.data;
  }

  /**
   * Получить прогресс студента по уроку
   */
  async getLessonProgress(lessonId: string, studentId: string): Promise<LessonProgress> {
    logger.info('[LessonService] Fetching lesson progress:', { lessonId, studentId });

    const response: ApiResponse<LessonProgress> = await unifiedAPI.get(
      `/knowledge-graph/lessons/${lessonId}/progress/${studentId}/`
    );

    if (!response.success || !response.data) {
      const error = response.error || 'Failed to fetch lesson progress';
      logger.error('[LessonService] Get lesson progress failed:', error);
      throw new Error(error);
    }

    logger.info('[LessonService] Lesson progress fetched:', {
      status: response.data.status,
      completed: response.data.completed_elements_count,
      total: response.data.total_elements_count
    });

    return response.data;
  }

  /**
   * Отправить ответ на элемент
   */
  async submitElementAnswer(
    elementId: string,
    data: SubmitAnswerRequest
  ): Promise<SubmitAnswerResponse> {
    logger.info('[LessonService] Submitting answer for element:', elementId);

    const response: ApiResponse<SubmitAnswerResponse> = await unifiedAPI.post(
      `/knowledge-graph/elements/${elementId}/progress/`,
      data
    );

    if (!response.success || !response.data) {
      const error = response.error || 'Failed to submit answer';
      logger.error('[LessonService] Submit answer failed:', error);
      throw new Error(error);
    }

    logger.info('[LessonService] Answer submitted successfully:', {
      score: response.data.score,
      status: response.data.status
    });

    return response.data;
  }

  /**
   * Обновить статус урока (пометить как завершенный)
   */
  async completeLessonStatus(lessonId: string, studentId: string): Promise<void> {
    logger.info('[LessonService] Marking lesson as complete:', { lessonId, studentId });

    const response: ApiResponse<void> = await unifiedAPI.patch(
      `/knowledge-graph/lessons/${lessonId}/progress/${studentId}/update/`,
      { status: 'completed' }
    );

    if (!response.success) {
      const error = response.error || 'Failed to complete lesson';
      logger.error('[LessonService] Complete lesson failed:', error);
      throw new Error(error);
    }

    logger.info('[LessonService] Lesson marked as complete');
  }

  /**
   * Проверить, может ли студент начать урок (проверка пререквизитов)
   */
  async checkPrerequisites(
    graphId: string,
    lessonId: string
  ): Promise<PrerequisiteCheck> {
    logger.info('[LessonService] Checking prerequisites:', { graphId, lessonId });

    const response: ApiResponse<PrerequisiteCheck> = await unifiedAPI.get(
      `/knowledge-graph/${graphId}/lessons/${lessonId}/can-start/`
    );

    if (!response.success || !response.data) {
      const error = response.error || 'Failed to check prerequisites';
      logger.error('[LessonService] Check prerequisites failed:', error);
      throw new Error(error);
    }

    logger.info('[LessonService] Prerequisites checked:', {
      canStart: response.data.can_start,
      missing: response.data.missing_prerequisites.length
    });

    return response.data;
  }

  /**
   * Получить прогресс по конкретному элементу
   */
  async getElementProgress(
    elementId: string,
    studentId: string
  ): Promise<ElementProgress> {
    logger.info('[LessonService] Fetching element progress:', { elementId, studentId });

    const response: ApiResponse<ElementProgress> = await unifiedAPI.get(
      `/knowledge-graph/elements/${elementId}/progress/${studentId}/`
    );

    if (!response.success || !response.data) {
      const error = response.error || 'Failed to fetch element progress';
      logger.error('[LessonService] Get element progress failed:', error);
      throw new Error(error);
    }

    return response.data;
  }
}

// Export singleton instance
export const lessonService = new LessonService();
