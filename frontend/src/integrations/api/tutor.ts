// Tutor API Service
import { unifiedAPI } from './unifiedClient';

/**
 * TutorStudent интерфейс
 *
 * ВАЖНО: goal - ПРИВАТНОЕ поле (студент не видит, тьютор видит)
 * Backend автоматически фильтрует это поле в зависимости от прав.
 */
export interface TutorStudent {
  id: number; // student profile or user id depending on backend
  user_id?: number;
  full_name: string;
  first_name?: string;
  last_name?: string;
  grade?: string;
  goal?: string; // ПРИВАТНОЕ: студент не видит, тьютор видит
  parent_name?: string;
  created_at?: string;
  subjects?: Array<{
    id: number;
    name: string;
    teacher_name: string;
    enrollment_id: number;
  }>;
}

export interface CreateStudentRequest {
  first_name: string;
  last_name: string;
  grade: string;
  goal?: string;
  parent_first_name: string;
  parent_last_name: string;
  parent_email: string;
  parent_phone: string;
}

export interface CreateStudentResponse {
  student: TutorStudent;
  parent: { id: number; full_name: string };
  credentials: {
    student: { username: string; password: string };
    parent: { username: string; password: string };
  };
}

export interface AssignSubjectRequest {
  subject_id?: number;
  subject_name?: string;
  teacher_id?: number;
}

export const tutorAPI = {
  listStudents: async (): Promise<TutorStudent[]> => {
    console.log('[tutorAPI.listStudents] Starting request');
    
    const token = unifiedAPI.getToken();
    console.log('[tutorAPI.listStudents] Current token:', token ? 'EXISTS' : 'MISSING');
    
    if (!token) {
      console.error('[tutorAPI.listStudents] No token available!');
      throw new Error('Authentication required. Please login again.');
    }
    
    const resp = await unifiedAPI.request<any>('/tutor/students/');
    
    console.log('[tutorAPI.listStudents] Response status:', resp.success);
    console.log('[tutorAPI.listStudents] Response data:', resp.data);
    
    if (resp.error) {
      console.error('[tutorAPI.listStudents] Error:', resp.error);
      throw new Error(resp.error);
    }
    
    // Backend может вернуть данные в формате {success: true, data: [...]} или просто массив
    if (resp.data) {
      if (Array.isArray(resp.data)) {
        return resp.data;
      } else if (resp.data.data && Array.isArray(resp.data.data)) {
        return resp.data.data;
      } else if (Array.isArray(resp.data.results)) {
        return resp.data.results;
      }
    }
    
    return [];
  },

  createStudent: async (data: CreateStudentRequest): Promise<CreateStudentResponse> => {
    console.log('[tutorAPI.createStudent] Starting request with data:', data);
    
    // Проверяем токен перед запросом
    const token = unifiedAPI.getToken();
    console.log('[tutorAPI.createStudent] Current token:', token ? 'EXISTS' : 'MISSING');
    
    if (!token) {
      console.error('[tutorAPI.createStudent] No token available!');
      throw new Error('HTTP 403: Forbidden - Authentication required');
    }
    
    const resp = await unifiedAPI.request<CreateStudentResponse>('/tutor/students/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    
    console.log('[tutorAPI.createStudent] Response success:', resp.success);
    console.log('[tutorAPI.createStudent] Response error:', resp.error);
    console.log('[tutorAPI.createStudent] Full response:', JSON.stringify(resp, null, 2));
    
    if (resp.error) {
      console.error('[tutorAPI.createStudent] Error:', resp.error);
      // Если ошибка содержит 403 или Forbidden, сохраняем это в сообщении
      if (resp.error.includes('403') || resp.error.includes('Forbidden')) {
        throw new Error('HTTP 403: Forbidden');
      }
      throw new Error(resp.error);
    }
    
    return resp.data!;
  },

  getStudent: async (id: number): Promise<TutorStudent> => {
    const resp = await unifiedAPI.request<TutorStudent>(`/tutor/students/${id}/`);
    if (resp.error) throw new Error(resp.error);
    return resp.data!;
  },

  assignSubject: async (studentId: number, data: AssignSubjectRequest): Promise<void> => {
    try {
      console.log('[tutorAPI.assignSubject] Starting request:', { studentId, data });
      const resp = await unifiedAPI.request(`/tutor/students/${studentId}/subjects/`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      
      console.log('[tutorAPI.assignSubject] Response:', {
        success: resp.success,
        error: resp.error,
        data: resp.data,
        hasData: !!resp.data,
        status: resp.status
      });
      
      if (!resp.success || resp.error) {
        // Пытаемся извлечь детальное сообщение об ошибке
        const errorMessage = resp.error || resp.data?.detail || 'Не удалось назначить предмет';
        console.error('[tutorAPI.assignSubject] Error:', errorMessage);
        throw new Error(errorMessage);
      }
      
      // Если запрос успешен, даже если данных нет в ответе, считаем что предмет назначен
      console.log('[tutorAPI.assignSubject] Subject assigned successfully, status:', resp.status || 'OK');
      
      // Возвращаем void, так как данные будут загружены через отдельный запрос
      return;
    } catch (error: any) {
      console.error('[tutorAPI.assignSubject] Exception:', error);
      // Если это уже Error с сообщением, пробрасываем дальше
      if (error instanceof Error) {
        throw error;
      }
      // Иначе создаем новый Error
      throw new Error(error?.message || 'Не удалось назначить предмет');
    }
  },

  removeSubject: async (studentId: number, subjectId: number): Promise<void> => {
    const resp = await unifiedAPI.request(`/tutor/students/${studentId}/subjects/${subjectId}/`, {
      method: 'DELETE',
    });
    if (resp.error) throw new Error(resp.error);
  },
};
