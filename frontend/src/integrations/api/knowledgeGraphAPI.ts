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
   * Всегда возвращает массив (пустой при отсутствии данных)
   * Бросает Error только при сетевых ошибках
   */
  getTeacherStudents: async (): Promise<Student[]> => {
    try {
      const response = await unifiedAPI.get<{ students: Student[] } | { results: Student[] } | Student[]>(
        '/materials/teacher/students/'
      );

      // Сетевая ошибка или ошибка авторизации - пробрасываем дальше
      if (response.error) {
        throw new Error(response.error);
      }

      const data = response.data;

      // Нет данных - возвращаем пустой массив
      if (!data) {
        return [];
      }

      // Backend возвращает { students: [...] }
      if (typeof data === 'object' && 'students' in data) {
        const students = (data as { students: Student[] }).students;
        return Array.isArray(students) ? students : [];
      }

      // Альтернативный формат { results: [...] }
      if (typeof data === 'object' && 'results' in data) {
        const results = (data as { results: Student[] }).results;
        return Array.isArray(results) ? results : [];
      }

      // Прямой массив
      if (Array.isArray(data)) {
        return data;
      }

      // Неизвестный формат - возвращаем пустой массив
      console.warn('[knowledgeGraphAPI] Unexpected response format for getTeacherStudents:', data);
      return [];
    } catch (error) {
      // Сетевая ошибка - пробрасываем с понятным сообщением
      if (error instanceof Error) {
        throw new Error(`Не удалось загрузить список студентов: ${error.message}`);
      }
      throw new Error('Не удалось загрузить список студентов: неизвестная ошибка');
    }
  },

  // ============================================
  // Knowledge Graph CRUD
  // ============================================

  /**
   * Получить или создать граф для студента по предмету
   * FIX T008: обработка обертки { success, data } от backend
   */
  getOrCreateGraph: async (studentId: number, subjectId: number): Promise<KnowledgeGraph> => {
    const response = await unifiedAPI.get<{ success: boolean; data: KnowledgeGraph; created?: boolean } | KnowledgeGraph>(
      `/knowledge-graph/students/${studentId}/subject/${subjectId}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      throw new Error('Граф не найден');
    }

    // Backend возвращает { success: true, data: KnowledgeGraph }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: KnowledgeGraph }).data;
    }

    // Или прямой объект KnowledgeGraph
    return data as KnowledgeGraph;
  },

  /**
   * Получить уроки графа
   * FIX T008: обработка обертки { success, data } от backend
   */
  getGraphLessons: async (graphId: number): Promise<KnowledgeGraph['lessons']> => {
    const response = await unifiedAPI.get<{ success: boolean; data: KnowledgeGraph['lessons']; count: number } | { lessons: KnowledgeGraph['lessons'] }>(
      `/knowledge-graph/${graphId}/lessons/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      return [];
    }

    // Backend возвращает { success: true, data: [...], count: N }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      const lessons = (data as { success: boolean; data: KnowledgeGraph['lessons'] }).data;
      return Array.isArray(lessons) ? lessons : [];
    }

    // Альтернативный формат { lessons: [...] }
    if ('lessons' in data) {
      const lessons = (data as { lessons: KnowledgeGraph['lessons'] }).lessons;
      return Array.isArray(lessons) ? lessons : [];
    }

    return [];
  },

  // ============================================
  // Lesson Management
  // ============================================

  /**
   * Получить все уроки (банк уроков)
   * FIX T008: обработка обертки { success, data } от backend
   */
  getLessons: async (filters?: { subject?: number; created_by?: string }): Promise<Lesson[]> => {
    const response = await unifiedAPI.get<{ success: boolean; data: Lesson[]; count?: number } | { results: Lesson[] } | Lesson[]>(
      '/knowledge-graph/lessons/',
      { params: filters }
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    // Защита от undefined/null - всегда возвращаем массив
    if (!data) {
      return [];
    }
    if (Array.isArray(data)) {
      return data;
    }
    // Обработка формата { success: true, data: [...] }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      const lessons = (data as { success: boolean; data: Lesson[] }).data;
      return Array.isArray(lessons) ? lessons : [];
    }
    // Обработка пагинированного формата {results: [...]}
    if ('results' in data) {
      return Array.isArray((data as { results: Lesson[] }).results) ? (data as { results: Lesson[] }).results : [];
    }
    return [];
  },

  /**
   * Добавить урок в граф
   * FIX T008: обработка обертки { success, data } от backend
   */
  addLessonToGraph: async (
    graphId: number,
    payload: AddLessonToGraphRequest
  ): Promise<KnowledgeGraph['lessons'][0]> => {
    const response = await unifiedAPI.post<{ success: boolean; data: KnowledgeGraph['lessons'][0] } | KnowledgeGraph['lessons'][0]>(
      `/knowledge-graph/${graphId}/lessons/`,
      payload
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      throw new Error('Ошибка при добавлении урока');
    }

    // Backend возвращает { success: true, data: GraphLesson }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: KnowledgeGraph['lessons'][0] }).data;
    }

    return data as KnowledgeGraph['lessons'][0];
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
   * FIX T008: обработка обертки { success, data } от backend
   */
  updateLessonPosition: async (
    graphId: number,
    graphLessonId: number,
    payload: UpdateLessonPositionRequest
  ): Promise<KnowledgeGraph['lessons'][0]> => {
    const response = await unifiedAPI.patch<{ success: boolean; data: KnowledgeGraph['lessons'][0] } | KnowledgeGraph['lessons'][0]>(
      `/knowledge-graph/${graphId}/lessons/${graphLessonId}/`,
      payload
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      throw new Error('Ошибка при обновлении позиции');
    }

    // Backend возвращает { success: true, data: GraphLesson }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: KnowledgeGraph['lessons'][0] }).data;
    }

    return data as KnowledgeGraph['lessons'][0];
  },

  /**
   * Пакетное обновление позиций уроков
   * FIX T008: Backend возвращает { success: true, message: ... }
   * Backend ожидает { lessons: [{ lesson_id, position_x, position_y }] }
   */
  batchUpdateLessons: async (
    graphId: number,
    payload: BatchUpdateLessonsRequest
  ): Promise<void> => {
    // Преобразование формата: frontend использует graph_lesson_id, backend ожидает lesson_id
    const backendPayload = {
      lessons: payload.lessons.map(item => ({
        lesson_id: item.graph_lesson_id,
        position_x: item.position_x,
        position_y: item.position_y,
      })),
    };

    const response = await unifiedAPI.patch<{ success: boolean; message: string }>(
      `/knowledge-graph/${graphId}/lessons/batch/`,
      backendPayload
    );

    if (response.error) {
      throw new Error(response.error);
    }

    // Backend возвращает { success: true, message: "Обновлено N уроков" }
    // Возвращаем void, успех определяется отсутствием ошибки
  },

  // ============================================
  // Dependencies Management
  // ============================================

  /**
   * Получить зависимости урока
   * FIX T008: Backend возвращает { success, data: { incoming, outgoing } }
   */
  getLessonDependencies: async (
    graphId: number,
    lessonId: number
  ): Promise<KnowledgeGraph['dependencies']> => {
    const response = await unifiedAPI.get<{ success: boolean; data: { incoming: KnowledgeGraph['dependencies']; outgoing: KnowledgeGraph['dependencies'] } }>(
      `/knowledge-graph/${graphId}/lessons/${lessonId}/dependencies/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data || !('data' in data)) {
      return [];
    }

    // Backend возвращает { success: true, data: { incoming: [...], outgoing: [...] } }
    const deps = (data as { success: boolean; data: { incoming: KnowledgeGraph['dependencies']; outgoing: KnowledgeGraph['dependencies'] } }).data;

    // Объединяем incoming и outgoing зависимости
    const allDeps = [
      ...(Array.isArray(deps.incoming) ? deps.incoming : []),
      ...(Array.isArray(deps.outgoing) ? deps.outgoing : []),
    ];

    return allDeps;
  },

  /**
   * Добавить зависимость (prerequisite)
   * FIX T008: Преобразование формата запроса и ответа
   * Frontend: { to_lesson_id, dependency_type, min_score_percent/strength }
   * Backend: { prerequisite_lesson_id, dependency_type, min_score_percent }
   */
  addDependency: async (
    graphId: number,
    toLessonId: number,
    payload: AddDependencyRequest
  ): Promise<KnowledgeGraph['dependencies'][0]> => {
    // Преобразование формата для backend
    // Backend endpoint: POST /api/knowledge-graph/{graph_id}/lessons/{lesson_id}/dependencies/
    // lesson_id - это to_lesson (урок который зависит от prerequisite)
    // prerequisite_lesson_id - это from_lesson (prerequisite урок)

    // Определить тип зависимости для backend
    let backendType = 'required';
    if (payload.dependency_type) {
      if (payload.dependency_type === 'prerequisite') {
        backendType = 'required';
      } else if (payload.dependency_type === 'related') {
        backendType = 'optional';
      } else if (['required', 'recommended', 'optional'].includes(payload.dependency_type)) {
        backendType = payload.dependency_type;
      }
    }

    // Определить min_score_percent
    let minScorePercent = 0;
    if (payload.min_score_percent !== undefined) {
      minScorePercent = payload.min_score_percent;
    } else if (payload.strength !== undefined) {
      // Deprecated: конвертация strength (1-10) в percent (0-100)
      minScorePercent = payload.strength * 10;
    }

    const backendPayload = {
      prerequisite_lesson_id: payload.to_lesson_id, // ID prerequisite GraphLesson
      dependency_type: backendType,
      min_score_percent: minScorePercent,
    };

    const response = await unifiedAPI.post<{ success: boolean; data: KnowledgeGraph['dependencies'][0] }>(
      `/knowledge-graph/${graphId}/lessons/${toLessonId}/dependencies/`,
      backendPayload
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      throw new Error('Ошибка при создании зависимости');
    }

    // Backend возвращает { success: true, data: Dependency }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: KnowledgeGraph['dependencies'][0] }).data;
    }

    return data as KnowledgeGraph['dependencies'][0];
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
   * FIX T008: обработка обертки { success, data } от backend
   */
  checkPrerequisites: async (
    graphId: number,
    lessonId: number
  ): Promise<{ can_start: boolean; missing_prerequisites: number[] }> => {
    const response = await unifiedAPI.get<{ success: boolean; data: { can_start: boolean; missing_prerequisites: number[] } }>(
      `/knowledge-graph/${graphId}/lessons/${lessonId}/can-start/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      return { can_start: false, missing_prerequisites: [] };
    }

    // Backend возвращает { success: true, data: { can_start, missing_prerequisites } }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: { can_start: boolean; missing_prerequisites: number[] } }).data;
    }

    return data as { can_start: boolean; missing_prerequisites: number[] };
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
   * FIX T008: обработка обертки { success, data } от backend
   */
  getStudentGraph: async (studentId: number, subjectId: number): Promise<KnowledgeGraph> => {
    const response = await unifiedAPI.get<{ success: boolean; data: KnowledgeGraph; created?: boolean } | KnowledgeGraph>(
      `/knowledge-graph/students/${studentId}/subject/${subjectId}/`
    );

    if (response.error) {
      throw new Error(response.error);
    }

    const data = response.data;
    if (!data) {
      throw new Error('Граф не найден');
    }

    // Backend возвращает { success: true, data: KnowledgeGraph }
    if (typeof data === 'object' && 'success' in data && 'data' in data) {
      return (data as { success: boolean; data: KnowledgeGraph }).data;
    }

    return data as KnowledgeGraph;
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

  // ============================================
  // Student Lesson Viewer Methods (T024)
  // ============================================

  /**
   * Получить урок со всеми элементами для студента
   * Endpoint: GET /api/knowledge-graph/student/lessons/{graph_lesson_id}/
   */
  getStudentLesson: async (graphLessonId: string) => {
    const response = await unifiedAPI.get<{
      success: boolean;
      data: {
        graph_lesson: {
          id: string;
          lesson: {
            id: string;
            title: string;
            description: string;
          };
          status: string;
          unlocked_at: string;
        };
        elements: Array<{
          id: string;
          order: number;
          element: {
            id: string;
            title: string;
            element_type: 'text_problem' | 'quick_question' | 'theory' | 'video';
            content: any;
            max_score: number;
            estimated_time_minutes: number;
          };
          progress?: {
            id: string;
            status: 'not_started' | 'in_progress' | 'completed';
            score: number | null;
            answer: any | null;
            started_at: string | null;
            completed_at: string | null;
          };
        }>;
        progress: {
          id: string;
          status: string;
          completion_percent: number;
          total_score: number;
          max_possible_score: number;
        };
        next_element_id: string | null;
      };
    }>(`/knowledge-graph/student/lessons/${graphLessonId}/`);

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data || !('data' in response.data)) {
      throw new Error('Урок не найден');
    }

    return response.data.data;
  },

  /**
   * Начать элемент (студент)
   * Endpoint: POST /api/knowledge-graph/student/elements/{element_id}/start/
   */
  startStudentElement: async (elementId: string) => {
    const response = await unifiedAPI.post<{
      success: boolean;
      data: {
        progress: {
          id: string;
          element_id: string;
          status: string;
          started_at: string;
        };
      };
    }>(`/knowledge-graph/student/elements/${elementId}/start/`, {});

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data;
  },

  /**
   * Отправить ответ на элемент (студент)
   * Endpoint: POST /api/knowledge-graph/student/elements/{element_id}/submit/
   */
  submitStudentAnswer: async (elementId: string, answer: any) => {
    const response = await unifiedAPI.post<{
      success: boolean;
      data: {
        progress: {
          id: string;
          status: string;
          score: number | null;
          answer: any;
        };
        score: number | null;
        is_correct?: boolean;
        next_element_id: string | null;
      };
    }>(`/knowledge-graph/student/elements/${elementId}/submit/`, { answer });

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data;
  },

  /**
   * Завершить урок (студент)
   * Endpoint: POST /api/knowledge-graph/student/lessons/{graph_lesson_id}/complete/
   */
  completeStudentLesson: async (graphLessonId: string) => {
    const response = await unifiedAPI.post<{
      success: boolean;
      data: {
        lesson_progress: {
          id: string;
          graph_lesson_id: string;
          status: string;
          score: number;
          max_score: number;
          percentage: number;
          completed_at: string;
        };
        unlocked_lessons: Array<{
          id: string;
          lesson: {
            id: string;
            title: string;
          };
          unlocked_at: string;
        }>;
      };
    }>(`/knowledge-graph/student/lessons/${graphLessonId}/complete/`, {});

    if (response.error) {
      throw new Error(response.error);
    }

    return response.data;
  },
};
