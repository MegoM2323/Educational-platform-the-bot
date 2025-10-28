import { unifiedAPI } from './unifiedClient';

export interface StudentSubject {
  id: number;
  name: string;
  color?: string;
  teacher: { id: number; full_name: string };
  enrollment_status?: string;
}

export interface SubjectMaterial {
  id: number;
  title: string;
  description?: string;
  created_at: string;
  type?: string;
  status?: string;
  progress_percentage?: number;
}

export interface SubmissionResponse {
  id: number;
  status: string;
  submitted_at: string;
}

export interface FeedbackItem {
  id: number;
  submission_id: number;
  teacher_id: number;
  feedback_text: string;
  grade?: number;
  created_at: string;
}

export const studentAPI = {
  getSubjects: async (): Promise<StudentSubject[]> => {
    const resp = await unifiedAPI.request<StudentSubject[]>('/student/subjects/');
    if (resp.error) throw new Error(resp.error);
    return resp.data!;
  },

  getSubjectMaterials: async (subjectId: number): Promise<SubjectMaterial[]> => {
    const resp = await unifiedAPI.request<SubjectMaterial[]>(`/student/subjects/${subjectId}/materials/`);
    if (resp.error) throw new Error(resp.error);
    return resp.data!;
  },

  submitHomework: async (materialId: number, data: FormData): Promise<SubmissionResponse> => {
    const resp = await unifiedAPI.request<SubmissionResponse>(`/student/materials/${materialId}/submissions/`, {
      method: 'POST',
      body: data,
      headers: {},
    });
    if (resp.error) throw new Error(resp.error);
    return resp.data!;
  },

  getFeedback: async (submissionId: number): Promise<FeedbackItem> => {
    const resp = await unifiedAPI.request<FeedbackItem>(`/student/submissions/${submissionId}/feedback/`);
    if (resp.error) throw new Error(resp.error);
    return resp.data!;
  },

  getSubmissions: async (): Promise<SubmissionResponse[]> => {
    const resp = await unifiedAPI.request<SubmissionResponse[]>(`/student/submissions/`);
    if (resp.error) throw new Error(resp.error);
    return resp.data!;
  },
};
