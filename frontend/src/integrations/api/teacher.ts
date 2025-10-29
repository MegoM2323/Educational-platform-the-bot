import { unifiedAPI } from './unifiedClient';

export interface PendingSubmission {
  id: number;
  material_id: number;
  material_title: string;
  student_id: number;
  student_name: string;
  submitted_at: string;
  submission_text?: string;
  submission_file?: string;
  status: 'pending' | 'reviewed' | 'needs_changes';
}

export interface ProvideFeedbackRequest {
  feedback_text: string;
  grade?: number;
}

export const teacherAPI = {
  getPendingSubmissions: async (): Promise<PendingSubmission[]> => {
    const resp = await unifiedAPI.request<{pending: PendingSubmission[]}>('/materials/teacher/submissions/pending/');
    if (resp.error) throw new Error(resp.error);
    return resp.data!.pending;
  },
  provideFeedback: async (submissionId: number, data: ProvideFeedbackRequest): Promise<void> => {
    const resp = await unifiedAPI.request(`/materials/teacher/submissions/${submissionId}/feedback/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (resp.error) throw new Error(resp.error);
  },
  updateSubmissionStatus: async (submissionId: number, status: 'pending' | 'reviewed' | 'needs_changes'): Promise<void> => {
    const resp = await unifiedAPI.request(`/materials/teacher/submissions/${submissionId}/status/`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
    if (resp.error) throw new Error(resp.error);
  },
  getSubjects: async (): Promise<any[]> => {
    const resp = await unifiedAPI.request<{subjects: any[]}>('/materials/teacher/subjects/');
    if (resp.error) throw new Error(resp.error);
    return resp.data!.subjects;
  },
  getAllStudents: async (): Promise<any[]> => {
    const resp = await unifiedAPI.request<{students: any[]}>('/materials/teacher/all-students/');
    if (resp.error) throw new Error(resp.error);
    return resp.data!.students;
  },
  assignSubjectToStudents: async (subjectId: number, studentIds: number[]): Promise<void> => {
    const resp = await unifiedAPI.request('/materials/teacher/subjects/assign/', {
      method: 'POST',
      body: JSON.stringify({ subject_id: subjectId, student_ids: studentIds }),
    });
    if (resp.error) throw new Error(resp.error);
  },
};
