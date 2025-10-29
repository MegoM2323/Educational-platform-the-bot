// Tutor API Service
import { unifiedAPI } from './unifiedClient';

export interface TutorStudent {
  id: number; // student profile or user id depending on backend
  user_id?: number;
  full_name: string;
  first_name?: string;
  last_name?: string;
  grade?: string;
  goal?: string;
  parent_name?: string;
  created_at?: string;
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
  subject_id: number;
  teacher_id: number;
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
    
    const resp = await unifiedAPI.request<TutorStudent[]>('/tutor/students/');
    
    console.log('[tutorAPI.listStudents] Response status:', resp.success);
    
    if (resp.error) {
      console.error('[tutorAPI.listStudents] Error:', resp.error);
      throw new Error(resp.error);
    }
    
    return resp.data!;
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
    const resp = await unifiedAPI.request(`/tutor/students/${studentId}/subjects/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (resp.error) throw new Error(resp.error);
  },

  removeSubject: async (studentId: number, subjectId: number): Promise<void> => {
    const resp = await unifiedAPI.request(`/tutor/students/${studentId}/subjects/${subjectId}/`, {
      method: 'DELETE',
    });
    if (resp.error) throw new Error(resp.error);
  },
};
