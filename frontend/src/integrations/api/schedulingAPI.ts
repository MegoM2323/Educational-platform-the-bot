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
    // Конвертируем studentId в число для backend
    const numericStudentId = parseInt(studentId, 10);
    if (isNaN(numericStudentId)) {
      throw new Error(`Invalid studentId: ${studentId}. Expected a numeric value.`);
    }

    const response = await unifiedAPI.get<{
      student: { id: string; name: string; email: string };
      lessons: any[];
      total_lessons: number
    }>(
      `/scheduling/tutor/students/${numericStudentId}/schedule/`,
      { params: filters }
    );
    if (response.error) {
      throw new Error(response.error);
    }
    // Backend возвращает { student: {...}, lessons: [...], total_lessons: number }
    // Backend returns { student: {...}, lessons: [...], total_lessons: number }
    // Backend field names: teacher_name, subject_name (strings from LessonSerializer)
    // Frontend expects: teacher_name, subject_name
    const data = response.data;
    if (data && typeof data === 'object' && 'lessons' in data) {
      // Map backend field names to frontend expectations
      return data.lessons.map((lesson: any): Lesson => {
        return {
          id: lesson.id,
          teacher: lesson.teacher_id, // UUID
          student: studentId, // UUID
          subject: lesson.subject_id, // UUID
          teacher_id: lesson.teacher_id, // UUID (обязательное поле)
          subject_id: lesson.subject_id, // UUID (обязательное поле)
          teacher_name: lesson.teacher_name || '', // Backend returns full name as 'teacher_name'
          subject_name: lesson.subject_name || '', // Backend returns name as 'subject_name'
          date: lesson.date,
          start_time: lesson.start_time,
          end_time: lesson.end_time,
          status: lesson.status,
          description: lesson.description || '',
          telemost_link: lesson.telemost_link || '',
          created_at: lesson.created_at || new Date().toISOString(),
          updated_at: lesson.updated_at || new Date().toISOString(),
          // Computed fields (обязательные)
          is_upcoming: lesson.is_upcoming ?? false,
          can_cancel: lesson.can_cancel ?? false,
          datetime_start: lesson.datetime_start || `${lesson.date}T${lesson.start_time}`,
          datetime_end: lesson.datetime_end || `${lesson.date}T${lesson.end_time}`,
        };
      });
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
  },

  getParentChildSchedule: async (childId: string, filters?: Record<string, any>): Promise<{
    student: { id: string; name: string; email: string };
    lessons: Lesson[];
    total_lessons: number;
  }> => {
    // Конвертируем childId в число для backend
    const numericChildId = parseInt(childId, 10);
    if (isNaN(numericChildId)) {
      throw new Error(`Invalid childId: ${childId}. Expected a numeric value.`);
    }

    // Backend endpoint: GET /api/scheduling/parent/children/{child_id}/schedule/
    const response = await unifiedAPI.get<{
      student: { id: string; name: string; email: string };
      lessons: any[];
      total_lessons: number
    }>(
      `/scheduling/parent/children/${numericChildId}/schedule/`,
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
      return {
        student: data.student,
        lessons: data.lessons.map((lesson: any): Lesson => {
          return {
            id: lesson.id,
            teacher: lesson.teacher_id, // UUID
            student: childId, // UUID
            subject: lesson.subject_id, // UUID
            teacher_id: lesson.teacher_id, // UUID (обязательное поле)
            subject_id: lesson.subject_id, // UUID (обязательное поле)
            teacher_name: lesson.teacher_name || '', // Backend returns full name as 'teacher_name'
            subject_name: lesson.subject_name || '', // Backend returns name as 'subject_name'
            date: lesson.date,
            start_time: lesson.start_time,
            end_time: lesson.end_time,
            status: lesson.status,
            description: lesson.description || '',
            telemost_link: lesson.telemost_link || '',
            created_at: lesson.created_at || new Date().toISOString(),
            updated_at: lesson.updated_at || new Date().toISOString(),
            // Computed fields (обязательные)
            is_upcoming: lesson.is_upcoming ?? false,
            can_cancel: lesson.can_cancel ?? false,
            datetime_start: lesson.datetime_start || `${lesson.date}T${lesson.start_time}`,
            datetime_end: lesson.datetime_end || `${lesson.date}T${lesson.end_time}`,
          };
        }),
        total_lessons: data.total_lessons,
      };
    }
    return {
      student: { id: childId, name: '', email: '' },
      lessons: [],
      total_lessons: 0,
    };
  },

  getParentAllSchedules: async (): Promise<{ children: Array<{ id: string; name: string; lessons: Lesson[] }>; total_children: number }> => {
    const response = await unifiedAPI.get<{
      children: Array<{
        id: string;
        name: string;
        lessons: any[];
      }>;
      total_children: number;
    }>('/scheduling/parent/schedule/');
    if (response.error) {
      throw new Error(response.error);
    }
    // Backend возвращает { children: [{id, name, lessons: [...]}], total_children: number }
    // Map backend field names to frontend expectations
    const data = response.data;
    if (data && typeof data === 'object' && 'children' in data) {
      return {
        children: data.children.map((child: any) => ({
          id: child.id,
          name: child.name,
          lessons: child.lessons.map((lesson: any): Lesson => {
            return {
              id: lesson.id,
              teacher: lesson.teacher_id, // UUID
              student: child.id, // UUID
              subject: lesson.subject_id, // UUID
              teacher_id: lesson.teacher_id, // UUID (обязательное поле)
              subject_id: lesson.subject_id, // UUID (обязательное поле)
              teacher_name: lesson.teacher_name || '', // Backend returns full name as 'teacher_name'
              subject_name: lesson.subject_name || '', // Backend returns name as 'subject_name'
              date: lesson.date,
              start_time: lesson.start_time,
              end_time: lesson.end_time,
              status: lesson.status,
              description: lesson.description || '',
              telemost_link: lesson.telemost_link || '',
              created_at: lesson.created_at || new Date().toISOString(),
              updated_at: lesson.updated_at || new Date().toISOString(),
              // Computed fields (обязательные)
              is_upcoming: lesson.is_upcoming ?? false,
              can_cancel: lesson.can_cancel ?? false,
              datetime_start: lesson.datetime_start || `${lesson.date}T${lesson.start_time}`,
              datetime_end: lesson.datetime_end || `${lesson.date}T${lesson.end_time}`,
            };
          }),
        })),
        total_children: data.total_children,
      };
    }
    return { children: [], total_children: 0 };
  }
};
