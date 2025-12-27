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
    const response = await unifiedAPI.get<{
      student: { id: string; name: string; email: string };
      lessons: any[];
      total_lessons: number
    }>(
      `/scheduling/tutor/students/${studentId}/schedule/`,
      { params: filters }
    );
    if (response.error) {
      throw new Error(response.error);
    }
    // Backend возвращает { student: {...}, lessons: [...], total_lessons: number }
    // Backend field names: teacher, subject (strings)
    // Frontend expects: teacher_name, subject_name
    const data = response.data;
    if (data && typeof data === 'object' && 'lessons' in data) {
      // Map backend field names to frontend expectations
      return data.lessons.map((lesson: any) => ({
        id: lesson.id,
        teacher: lesson.teacher_id, // UUID
        student: studentId, // UUID
        subject: lesson.subject_id, // UUID
        teacher_name: lesson.teacher, // Backend returns full name as 'teacher'
        subject_name: lesson.subject, // Backend returns name as 'subject'
        date: lesson.date,
        start_time: lesson.start_time,
        end_time: lesson.end_time,
        status: lesson.status,
        description: lesson.description || '',
        telemost_link: lesson.telemost_link || '',
        created_at: lesson.created_at || new Date().toISOString(),
        updated_at: lesson.updated_at || new Date().toISOString(),
      }));
    }
    return [];
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
