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
    const resp = await unifiedAPI.request<TutorStudent[]>('/tutor/students/');
    if (resp.error) throw new Error(resp.error);
    return resp.data!;
  },

  createStudent: async (data: CreateStudentRequest): Promise<CreateStudentResponse> => {
    const resp = await unifiedAPI.request<CreateStudentResponse>('/tutor/students/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (resp.error) throw new Error(resp.error);
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
