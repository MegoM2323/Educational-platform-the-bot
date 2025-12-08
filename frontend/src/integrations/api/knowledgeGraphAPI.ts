/**
 * Knowledge Graph API Client
 * Централизованный клиент для работы с API графов знаний
 */

import { unifiedAPI } from './unifiedClient';
import type {
  KnowledgeGraph,
  Lesson,
  Student,
  AddLessonToGraphRequest,
  UpdateLessonPositionRequest,
  BatchUpdateLessonsRequest,
  AddDependencyRequest,
} from '@/types/knowledgeGraph';

export const knowledgeGraphAPI = {
  // ============================================
  // Students Management
  // ============================================

  /**
   * Получить всех студентов преподавателя
   */
  getTeacherStudents: async (): Promise<Student[]> => {
    const response = await unifiedAPI.get<{ results: Student[] } | Student[]>(
      '/materials/dashboard/teacher/students/'
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    return Array.isArray(data) ? data : (data as { results: Student[] }).results;
  },

  // ============================================
  // Knowledge Graph CRUD
  // ============================================

  /**
   * Получить или создать граф для студента по предмету
   */
  getOrCreateGraph: async (studentId: number, subjectId: number): Promise<KnowledgeGraph> => {
    const response = await unifiedAPI.get<KnowledgeGraph>(
      `/knowledge-graph/students/${studentId}/subject/${subjectId}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as KnowledgeGraph;
  },

  /**
   * Получить уроки графа
   */
  getGraphLessons: async (graphId: number): Promise<KnowledgeGraph['lessons']> => {
    const response = await unifiedAPI.get<{ lessons: KnowledgeGraph['lessons'] }>(
      `/knowledge-graph/${graphId}/lessons/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return (response.data as { lessons: KnowledgeGraph['lessons'] }).lessons;
  },

  // ============================================
  // Lesson Management
  // ============================================

  /**
   * Получить все уроки (банк уроков)
   */
  getLessons: async (filters?: { subject?: number; created_by?: string }): Promise<Lesson[]> => {
    const response = await unifiedAPI.get<{ results: Lesson[] } | Lesson[]>(
      '/knowledge-graph/lessons/',
      { params: filters }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    return Array.isArray(data) ? data : (data as { results: Lesson[] }).results;
  },

  /**
   * Добавить урок в граф
   */
  addLessonToGraph: async (
    graphId: number,
    payload: AddLessonToGraphRequest
  ): Promise<KnowledgeGraph['lessons'][0]> => {
    const response = await unifiedAPI.post<KnowledgeGraph['lessons'][0]>(
      `/knowledge-graph/${graphId}/lessons/`,
      payload
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as KnowledgeGraph['lessons'][0];
  },

  /**
   * Удалить урок из графа
   */
  removeLessonFromGraph: async (graphId: number, graphLessonId: number): Promise<void> => {
    const response = await unifiedAPI.delete<void>(
      `/knowledge-graph/${graphId}/lessons/${graphLessonId}/remove/`
    );

    if (response.error) {
      throw new Error(response.error);
    }
  },

  /**
   * Обновить позицию урока
   */
  updateLessonPosition: async (
    graphId: number,
    graphLessonId: number,
    payload: UpdateLessonPositionRequest
  ): Promise<KnowledgeGraph['lessons'][0]> => {
    const response = await unifiedAPI.patch<KnowledgeGraph['lessons'][0]>(
      `/knowledge-graph/${graphId}/lessons/${graphLessonId}/`,
      payload
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as KnowledgeGraph['lessons'][0];
  },

  /**
   * Пакетное обновление позиций уроков
   */
  batchUpdateLessons: async (
    graphId: number,
    payload: BatchUpdateLessonsRequest
  ): Promise<KnowledgeGraph['lessons']> => {
    const response = await unifiedAPI.patch<{ lessons: KnowledgeGraph['lessons'] }>(
      `/knowledge-graph/${graphId}/lessons/batch/`,
      payload
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return (response.data as { lessons: KnowledgeGraph['lessons'] }).lessons;
  },

  // ============================================
  // Dependencies Management
  // ============================================

  /**
   * Получить зависимости урока
   */
  getLessonDependencies: async (
    graphId: number,
    lessonId: number
  ): Promise<KnowledgeGraph['dependencies']> => {
    const response = await unifiedAPI.get<{ dependencies: KnowledgeGraph['dependencies'] }>(
      `/knowledge-graph/${graphId}/lessons/${lessonId}/dependencies/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return (response.data as { dependencies: KnowledgeGraph['dependencies'] }).dependencies;
  },

  /**
   * Добавить зависимость (prerequisite)
   */
  addDependency: async (
    graphId: number,
    fromLessonId: number,
    payload: AddDependencyRequest
  ): Promise<KnowledgeGraph['dependencies'][0]> => {
    const response = await unifiedAPI.post<KnowledgeGraph['dependencies'][0]>(
      `/knowledge-graph/${graphId}/lessons/${fromLessonId}/dependencies/`,
      payload
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as KnowledgeGraph['dependencies'][0];
  },

  /**
   * Удалить зависимость
   */
  removeDependency: async (
    graphId: number,
    lessonId: number,
    dependencyId: number
  ): Promise<void> => {
    const response = await unifiedAPI.delete<void>(
      `/knowledge-graph/${graphId}/lessons/${lessonId}/dependencies/${dependencyId}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }
  },

  /**
   * Проверить, можно ли начать урок (проверка prerequisites)
   */
  checkPrerequisites: async (
    graphId: number,
    lessonId: number
  ): Promise<{ can_start: boolean; missing_prerequisites: number[] }> => {
    const response = await unifiedAPI.get<{ can_start: boolean; missing_prerequisites: number[] }>(
      `/knowledge-graph/${graphId}/lessons/${lessonId}/can-start/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as { can_start: boolean; missing_prerequisites: number[] };
  },

  // ============================================
  // Student View Methods (FIX T019)
  // ============================================

  /**
   * Получить список предметов студента (для выбора графа)
   * Endpoint: GET /api/student/subjects/
   */
  getStudentSubjects: async (): Promise<Array<{ id: number; name: string; color: string }>> => {
    const response = await unifiedAPI.get<{ results: Array<{ subject: { id: number; name: string; color: string } }> }>(
      '/student/subjects/'
    );

    if (response.error) {
      throw new Error(response.error);
    }

    // Преобразовать формат enrollments в массив subjects
    const enrollments = response.data?.results || [];
    return enrollments.map((e) => e.subject);
  },

  /**
   * Получить граф знаний для студента
   * Endpoint: GET /api/knowledge-graph/students/{studentId}/subject/{subjectId}/
   */
  getStudentGraph: async (studentId: number, subjectId: number): Promise<KnowledgeGraph> => {
    const response = await unifiedAPI.get<KnowledgeGraph>(
      `/knowledge-graph/students/${studentId}/subject/${subjectId}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as KnowledgeGraph;
  },

  /**
   * Получить прогресс по уроку для студента
   * Endpoint: GET /api/knowledge-graph/{graphId}/lessons/{lessonId}/progress/?student={studentId}
   */
  getLessonProgress: async (
    lessonId: number,
    studentId: number
  ): Promise<{
    status: string;
    completion_percent: number;
    total_score: number;
    max_possible_score: number;
  }> => {
    // Найти graph_lesson_id через список уроков графа
    // Примечание: это упрощенная реализация, может потребоваться корректировка
    const response = await unifiedAPI.get<{
      status: string;
      completion_percent: number;
      total_score: number;
      max_possible_score: number;
    }>(`/knowledge-graph/lessons/${lessonId}/progress/`, {
      params: { student: studentId },
    });

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data as {
      status: string;
      completion_percent: number;
      total_score: number;
      max_possible_score: number;
    };
  },
};
