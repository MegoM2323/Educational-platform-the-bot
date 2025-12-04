import { unifiedAPI } from './unifiedClient';
import { Lesson, LessonCreatePayload, LessonUpdatePayload } from '@/types/scheduling';

export const schedulingAPI = {
  createLesson: async (payload: LessonCreatePayload): Promise<Lesson> => {
    const response = await unifiedAPI.post<Lesson>('/scheduling/lessons/', payload);
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data as Lesson;
  },

  getLessons: async (filters?: Record<string, any>): Promise<Lesson[]> => {
    const response = await unifiedAPI.get<{ results: Lesson[] } | Lesson[]>('/scheduling/lessons/', { params: filters });
    if (response.error) {
      throw new Error(response.error);
    }
    // Backend returns {results: [...]} with pagination
    const data = response.data;
    return Array.isArray(data) ? data : (data as { results: Lesson[] }).results;
  },

  getLesson: async (id: string): Promise<Lesson> => {
    const response = await unifiedAPI.get<Lesson>(`/scheduling/lessons/${id}/`);
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data as Lesson;
  },

  updateLesson: async (id: string, payload: LessonUpdatePayload): Promise<Lesson> => {
    const response = await unifiedAPI.patch<Lesson>(`/scheduling/lessons/${id}/`, payload);
    if (response.error) {
      throw new Error(response.error);
    }
    return response.data as Lesson;
  },

  deleteLesson: async (id: string): Promise<void> => {
    const response = await unifiedAPI.delete<void>(`/scheduling/lessons/${id}/`);
    if (response.error) {
      throw new Error(response.error);
    }
  },

  getMySchedule: async (filters?: Record<string, any>): Promise<Lesson[]> => {
    const response = await unifiedAPI.get<{ results: Lesson[] } | Lesson[]>('/scheduling/lessons/my-schedule/', { params: filters });
    if (response.error) {
      throw new Error(response.error);
    }
    // Backend returns {results: [...]} with pagination
    const data = response.data;
    return Array.isArray(data) ? data : (data as { results: Lesson[] }).results;
  },

  getStudentSchedule: async (studentId: string, filters?: Record<string, any>): Promise<Lesson[]> => {
    const response = await unifiedAPI.get<{ results: Lesson[] } | Lesson[]>(
      `/materials/dashboard/tutor/students/${studentId}/schedule/`,
      { params: filters }
    );
    if (response.error) {
      throw new Error(response.error);
    }
    // Backend returns array directly (not paginated)
    const data = response.data;
    return Array.isArray(data) ? data : (data as { results: Lesson[] }).results;
  },

  getUpcomingLessons: async (limit: number = 10): Promise<Lesson[]> => {
    const response = await unifiedAPI.get<{ results: Lesson[] } | Lesson[]>('/scheduling/lessons/upcoming/', { params: { limit } });
    if (response.error) {
      throw new Error(response.error);
    }
    // Backend returns {results: [...]} with pagination
    const data = response.data;
    return Array.isArray(data) ? data : (data as { results: Lesson[] }).results;
  }
};
