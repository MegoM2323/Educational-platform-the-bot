/**
 * API client for Teacher Progress Viewer (Knowledge Graph System - T605)
 */
import { unifiedAPI } from './unifiedClient';

export interface StudentBasic {
  id: number;
  name: string;
  email: string;
}

export interface StudentProgressOverview {
  student_id: number;
  student_name: string;
  student_email: string;
  completion_percentage: number;
  lessons_completed: number;
  lessons_total: number;
  total_score: number;
  max_possible_score: number;
  last_activity: string | null;
}

export interface LessonProgressDetail {
  lesson_id: number;
  lesson_title: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'failed';
  completion_percent: number;
  completed_elements: number;
  total_elements: number;
  total_score: number;
  max_possible_score: number;
  started_at: string | null;
  completed_at: string | null;
  total_time_spent_seconds: number;
}

export interface ElementProgressDetail {
  element_id: number;
  element_type: 'text_problem' | 'quick_question' | 'theory' | 'video';
  element_title: string;
  student_answer: {
    text?: string;
    choice?: number;
    viewed?: boolean;
    watched_until?: number;
  } | null;
  score: number | null;
  max_score: number;
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped';
  completed_at: string | null;
  attempts: number;
  correct_answer?: number; // Для quick_question
  choices?: string[]; // Для quick_question
}

export interface GraphProgressResponse {
  success: boolean;
  data: {
    graph_id: number;
    subject_name: string;
    student: StudentProgressOverview;
  };
  error?: string;
}

export interface StudentDetailedProgressResponse {
  success: boolean;
  data: {
    student_id: number;
    student_name: string;
    lessons: LessonProgressDetail[];
  };
  error?: string;
}

export interface LessonDetailResponse {
  success: boolean;
  data: {
    lesson_id: number;
    lesson_title: string;
    elements: ElementProgressDetail[];
  };
  error?: string;
}

export const progressViewerAPI = {
  /**
   * Получить список студентов преподавателя
   */
  getTeacherStudents: async (): Promise<StudentBasic[]> => {
    const response = await unifiedAPI.get<{ results: StudentBasic[] } | StudentBasic[]>(
      '/materials/teacher/all-students/'
    );
    if (response.error) {
      throw new Error(response.error);
    }
    const data = response.data;
    return Array.isArray(data) ? data : (data as { results: StudentBasic[] }).results;
  },

  /**
   * Получить обзор прогресса по графу
   * GET /api/knowledge-graph/{graph_id}/progress/
   */
  getGraphProgress: async (graphId: number): Promise<GraphProgressResponse> => {
    const response = await unifiedAPI.get<GraphProgressResponse>(
      `/knowledge-graph/${graphId}/progress/`
    );
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data as GraphProgressResponse;
  },

  /**
   * Получить детальный прогресс студента по всем урокам в графе
   * GET /api/knowledge-graph/{graph_id}/students/{student_id}/progress/
   */
  getStudentDetailedProgress: async (
    graphId: number,
    studentId: number
  ): Promise<StudentDetailedProgressResponse> => {
    const response = await unifiedAPI.get<StudentDetailedProgressResponse>(
      `/knowledge-graph/${graphId}/students/${studentId}/progress/`
    );
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data as StudentDetailedProgressResponse;
  },

  /**
   * Получить детали урока с ответами студента на элементы
   * GET /api/knowledge-graph/{graph_id}/students/{student_id}/lesson/{lesson_id}/
   */
  getLessonDetail: async (
    graphId: number,
    studentId: number,
    lessonId: number
  ): Promise<LessonDetailResponse> => {
    const response = await unifiedAPI.get<LessonDetailResponse>(
      `/knowledge-graph/${graphId}/students/${studentId}/lesson/${lessonId}/`
    );
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data as LessonDetailResponse;
  },

  /**
   * Экспорт прогресса в CSV
   * GET /api/knowledge-graph/{graph_id}/export/?format=csv
   */
  exportProgress: async (graphId: number): Promise<Blob> => {
    const response = await fetch(`/api/knowledge-graph/${graphId}/export/?format=csv`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${unifiedAPI.getToken()}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Export failed' }));
      throw new Error(errorData.error || 'Failed to export progress');
    }

    return await response.blob();
  },

  /**
   * Получить граф для студента и предмета (для получения graph_id)
   * GET /api/knowledge-graph/students/{student_id}/subject/{subject_id}/
   */
  getOrCreateGraph: async (
    studentId: number,
    subjectId: number
  ): Promise<{ id: number; student: number; subject: number }> => {
    const response = await unifiedAPI.get<{
      success: boolean;
      data: { id: number; student: number; subject: number };
    }>(`/knowledge-graph/students/${studentId}/subject/${subjectId}/`);
    if (response.error) {
      throw new Error(response.error);
    }
    // Backend wraps response in {success, data} structure
    const wrappedResponse = response.data as {
      success: boolean;
      data: { id: number; student: number; subject: number };
    };
    return wrappedResponse.data;
  },
};
