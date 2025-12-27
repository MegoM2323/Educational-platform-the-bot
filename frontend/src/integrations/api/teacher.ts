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
    if (!resp.data) {
      throw new Error('No data received from server');
    }
    return resp.data.pending ?? [];
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
    if (!resp.data) {
      throw new Error('No data received from server');
    }
    return resp.data.subjects ?? [];
  },
  getAllStudents: async (): Promise<any[]> => {
    const resp = await unifiedAPI.request<{students: any[]}>('/materials/teacher/all-students/');
    if (resp.error) throw new Error(resp.error);
    if (!resp.data) {
      throw new Error('No data received from server');
    }
    return resp.data.students ?? [];
  },
  assignSubjectToStudents: async (subjectId: number, studentIds: number[]): Promise<void> => {
    // TODO: Backend endpoint /materials/teacher/subjects/assign/ does not exist
    // This functionality should use the enrollment endpoint: POST /api/subjects/{subject_id}/enroll/
    // For bulk enrollment, need to iterate over studentIds or implement bulk enrollment endpoint
    // See: backend/materials/enrollment_views.py - enroll_subject()

    // Temporary implementation: enroll each student individually
    const errors: string[] = [];
    for (const studentId of studentIds) {
      try {
        const resp = await unifiedAPI.request(`/materials/subjects/${subjectId}/enroll/`, {
          method: 'POST',
          body: JSON.stringify({
            student_id: studentId,
            teacher_id: null // Will need to be provided by the caller
          }),
        });
        if (resp.error) {
          errors.push(`Student ${studentId}: ${resp.error}`);
        }
      } catch (error) {
        errors.push(`Student ${studentId}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }

    if (errors.length > 0) {
      throw new Error(`Failed to assign some students:\n${errors.join('\n')}`);
    }
  },
};
