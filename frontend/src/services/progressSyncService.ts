/**
 * Progress Synchronization Service (T702)
 * Auto-complete lessons, unlock dependencies, sync graph state
 */

import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { progressViewerAPI } from '@/integrations/api/progressViewerAPI';
import { queryClient } from '@/lib/queryClient';

// ============================================
// Types
// ============================================

export interface LessonCompletionResult {
  lesson_id: number;
  graph_lesson_id: number;
  status: 'completed';
  completion_percent: number;
  total_score: number;
  max_possible_score: number;
  time_spent_minutes: number;
  completed_at: string;
  unlocked_lessons: UnlockedLesson[];
}

export interface UnlockedLesson {
  graph_lesson_id: number;
  lesson_id: number;
  lesson_title: string;
}

export interface ProgressSyncResult {
  completed: boolean;
  unlocked_lessons: UnlockedLesson[];
  updated_graph_progress: GraphProgress;
  timestamp: string;
}

export interface GraphProgress {
  graph_id: number;
  completion_percentage: number;
  lessons_completed: number;
  lessons_total: number;
  total_score: number;
  max_possible_score: number;
  last_activity: string;
}

export interface CheckLessonCompletionResult {
  is_ready: boolean;
  completion_percent: number;
  completed_elements: number;
  total_elements: number;
  missing_elements: number;
}

// ============================================
// Progress Sync Service
// ============================================

export const progressSyncService = {
  /**
   * Проверить готовность урока к завершению
   */
  checkLessonCompletion: async (
    lessonId: number,
    graphLessonId: number,
    studentId: number
  ): Promise<CheckLessonCompletionResult> => {
    try {
      const response = await unifiedAPI.get<{
        success: boolean;
        data: {
          status: string;
          completion_percent: number;
          completed_elements: number;
          total_elements: number;
        };
      }>(`/knowledge-graph/lessons/${lessonId}/progress/${studentId}/?graph_lesson_id=${graphLessonId}`);

      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to check lesson completion');
      }

      const data = (response.data as any).data || response.data;
      const completionPercent = data.completion_percent || 0;
      const completedElements = data.completed_elements || 0;
      const totalElements = data.total_elements || 0;

      return {
        is_ready: completionPercent === 100,
        completion_percent: completionPercent,
        completed_elements: completedElements,
        total_elements: totalElements,
        missing_elements: totalElements - completedElements,
      };
    } catch (error) {
      console.error('[ProgressSync] Error checking lesson completion:', error);
      throw error;
    }
  },

  /**
   * Завершить урок если все элементы выполнены
   */
  completeLessonIfReady: async (
    graphId: number,
    lessonId: number,
    graphLessonId: number,
    studentId: number
  ): Promise<LessonCompletionResult | null> => {
    try {
      // Проверить готовность
      const check = await progressSyncService.checkLessonCompletion(lessonId, graphLessonId, studentId);

      if (!check.is_ready) {
        console.log(`[ProgressSync] Lesson ${lessonId} not ready: ${check.completion_percent}%`);
        return null;
      }

      // Завершить урок
      const response = await unifiedAPI.patch<{
        success: boolean;
        data: {
          id: number;
          status: string;
          completion_percent: number;
          total_score: number;
          max_possible_score: number;
          total_time_spent_seconds: number;
          completed_at: string;
        };
      }>(`/knowledge-graph/lessons/${lessonId}/progress/${studentId}/update/`, {
        graph_lesson_id: graphLessonId,
        status: 'completed',
      });

      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to complete lesson');
      }

      const data = (response.data as any).data || response.data;

      // Получить список разблокированных уроков
      const unlockedLessons = await progressSyncService.getUnlockedLessons(graphId, graphLessonId);

      return {
        lesson_id: lessonId,
        graph_lesson_id: graphLessonId,
        status: 'completed',
        completion_percent: data.completion_percent || 100,
        total_score: data.total_score || 0,
        max_possible_score: data.max_possible_score || 0,
        time_spent_minutes: Math.round((data.total_time_spent_seconds || 0) / 60),
        completed_at: data.completed_at || new Date().toISOString(),
        unlocked_lessons: unlockedLessons,
      };
    } catch (error) {
      console.error('[ProgressSync] Error completing lesson:', error);
      throw error;
    }
  },

  /**
   * Получить список разблокированных уроков после завершения текущего
   * Backend автоматически разблокирует при вызове check_unlock_next()
   */
  getUnlockedLessons: async (graphId: number, graphLessonId: number): Promise<UnlockedLesson[]> => {
    try {
      // Получить зависимости урока (outgoing = уроки которые зависят от данного)
      const response = await unifiedAPI.get<{
        success: boolean;
        data: {
          incoming: any[];
          outgoing: Array<{
            id: number;
            to_lesson: {
              id: number;
              lesson: {
                id: number;
                title: string;
              };
            };
          }>;
        };
      }>(`/knowledge-graph/${graphId}/lessons/${graphLessonId}/dependencies/`);

      if (response.error || !response.data) {
        console.warn('[ProgressSync] Could not fetch dependencies:', response.error);
        return [];
      }

      const data = (response.data as any).data || response.data;
      const outgoing = data.outgoing || [];

      // Преобразовать в UnlockedLesson
      return outgoing.map((dep: any) => ({
        graph_lesson_id: dep.to_lesson.id,
        lesson_id: dep.to_lesson.lesson.id,
        lesson_title: dep.to_lesson.lesson.title,
      }));
    } catch (error) {
      console.error('[ProgressSync] Error getting unlocked lessons:', error);
      return [];
    }
  },

  /**
   * Синхронизировать прогресс по графу (обновить все данные)
   */
  syncGraphProgress: async (graphId: number, studentId: number): Promise<GraphProgress> => {
    try {
      const response = await progressViewerAPI.getGraphProgress(graphId);

      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to sync graph progress');
      }

      const student = response.data.student;

      return {
        graph_id: graphId,
        completion_percentage: student.completion_percentage || 0,
        lessons_completed: student.lessons_completed || 0,
        lessons_total: student.lessons_total || 0,
        total_score: student.total_score || 0,
        max_possible_score: student.max_possible_score || 0,
        last_activity: student.last_activity || new Date().toISOString(),
      };
    } catch (error) {
      console.error('[ProgressSync] Error syncing graph progress:', error);
      throw error;
    }
  },

  /**
   * Инвалидировать кеш прогресса (вызвать после завершения урока)
   */
  invalidateProgressCache: (graphId?: number, studentId?: number, lessonId?: number) => {
    // Инвалидировать все связанные запросы
    if (graphId && studentId) {
      queryClient.invalidateQueries({ queryKey: ['graphProgress', graphId] });
      queryClient.invalidateQueries({ queryKey: ['studentProgress', graphId, studentId] });
    }

    if (lessonId && studentId) {
      queryClient.invalidateQueries({ queryKey: ['lessonProgress', lessonId, studentId] });
    }

    // Инвалидировать общий прогресс
    queryClient.invalidateQueries({ queryKey: ['progress'] });
  },

  /**
   * Полная синхронизация после завершения элемента
   */
  syncAfterElementCompletion: async (
    graphId: number,
    lessonId: number,
    graphLessonId: number,
    studentId: number
  ): Promise<ProgressSyncResult> => {
    try {
      // 1. Проверить завершен ли урок
      const completionResult = await progressSyncService.completeLessonIfReady(
        lessonId,
        graphLessonId,
        studentId
      );

      // 2. Синхронизировать прогресс графа
      const graphProgress = await progressSyncService.syncGraphProgress(graphId, studentId);

      // 3. Инвалидировать кеш
      progressSyncService.invalidateProgressCache(graphId, studentId, lessonId);

      return {
        completed: completionResult !== null,
        unlocked_lessons: completionResult?.unlocked_lessons || [],
        updated_graph_progress: graphProgress,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      console.error('[ProgressSync] Error in sync after element completion:', error);
      throw error;
    }
  },
};
