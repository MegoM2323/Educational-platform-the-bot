import { apiClient } from './client';

export interface Assignment {
  id: number;
  title: string;
  description: string;
  instructions: string;
  type: 'homework' | 'test' | 'project' | 'essay' | 'practical';
  status: 'draft' | 'published' | 'closed';
  max_score: number;
  time_limit?: number;
  attempts_limit: number;
  start_date: string;
  due_date: string;
  tags: string;
  difficulty_level: number;
  author: {
    id: number;
    email: string;
    full_name: string;
  };
  assigned_to: number[];
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
}

export interface AssignmentSubmission {
  id: number;
  assignment: number;
  assignment_title?: string;
  student: {
    id: number;
    email: string;
    full_name: string;
  };
  content: string;
  file?: string;
  status: 'submitted' | 'graded' | 'returned';
  score?: number;
  max_score?: number;
  percentage?: number;
  feedback: string;
  submitted_at: string;
  graded_at?: string;
  updated_at: string;
}

export interface AssignmentQuestion {
  id: number;
  assignment: number;
  question_text: string;
  question_type: 'single_choice' | 'multiple_choice' | 'text' | 'number';
  points: number;
  order: number;
  options: string[];
  correct_answer: any;
}

export interface AssignmentAnswer {
  id: number;
  submission: number;
  question: number;
  answer_text: string;
  answer_choice: string[];
  is_correct: boolean;
  points_earned: number;
}

export interface CreateAssignmentPayload {
  title: string;
  description: string;
  instructions: string;
  type?: string;
  max_score?: number;
  time_limit?: number;
  attempts_limit?: number;
  start_date: string;
  due_date: string;
  tags?: string;
  difficulty_level?: number;
  assigned_to?: number[];
}

export interface CreateSubmissionPayload {
  content: string;
  file?: File;
}

export interface GradeSubmissionPayload {
  score: number;
  feedback?: string;
  status?: 'graded' | 'returned';
}

export const assignmentsAPI = {
  // Assignments
  getAssignments: async (filters?: Record<string, any>): Promise<Assignment[]> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    const url = `/assignments/assignments/${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await apiClient.get(url);
    return response.data;
  },

  getAssignment: async (id: number): Promise<Assignment> => {
    const response = await apiClient.get(`/assignments/assignments/${id}/`);
    return response.data;
  },

  createAssignment: async (data: CreateAssignmentPayload): Promise<Assignment> => {
    const response = await apiClient.post('/assignments/assignments/', data);
    return response.data;
  },

  updateAssignment: async (id: number, data: Partial<CreateAssignmentPayload>): Promise<Assignment> => {
    const response = await apiClient.patch(`/assignments/assignments/${id}/`, data);
    return response.data;
  },

  deleteAssignment: async (id: number): Promise<void> => {
    await apiClient.delete(`/assignments/assignments/${id}/`);
  },

  assignToStudents: async (id: number, studentIds: number[]): Promise<void> => {
    await apiClient.post(`/assignments/assignments/${id}/assign/`, {
      student_ids: studentIds
    });
  },

  getAssignmentSubmissions: async (assignmentId: number): Promise<AssignmentSubmission[]> => {
    const response = await apiClient.get(`/assignments/assignments/${assignmentId}/submissions/`);
    return response.data;
  },

  submitAssignment: async (assignmentId: number, data: CreateSubmissionPayload): Promise<AssignmentSubmission> => {
    const formData = new FormData();
    formData.append('content', data.content);
    if (data.file) {
      formData.append('file', data.file);
    }

    const response = await apiClient.post(
      `/assignments/assignments/${assignmentId}/submit/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  // Submissions
  getSubmissions: async (filters?: Record<string, any>): Promise<AssignmentSubmission[]> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    const url = `/assignments/submissions/${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await apiClient.get(url);
    return response.data;
  },

  getSubmission: async (id: number): Promise<AssignmentSubmission> => {
    const response = await apiClient.get(`/assignments/submissions/${id}/`);
    return response.data;
  },

  gradeSubmission: async (id: number, data: GradeSubmissionPayload): Promise<AssignmentSubmission> => {
    const response = await apiClient.post(`/assignments/submissions/${id}/grade/`, data);
    return response.data;
  },

  // Questions
  getQuestions: async (assignmentId: number): Promise<AssignmentQuestion[]> => {
    const response = await apiClient.get(`/assignments/questions/?assignment=${assignmentId}`);
    return response.data;
  },

  // Answers
  getAnswers: async (submissionId: number): Promise<AssignmentAnswer[]> => {
    const response = await apiClient.get(`/assignments/submissions/${submissionId}/answers/`);
    return response.data;
  },

  // Analytics (T_ASSIGN_007, T_ASN_005)
  getAssignmentAnalytics: async (assignmentId: number): Promise<any> => {
    const response = await apiClient.get(`/assignments/assignments/${assignmentId}/analytics/`);
    return response.data;
  },

  getAssignmentStatistics: async (
    assignmentId: number,
    filters?: Record<string, any>
  ): Promise<any> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    const url = `/assignments/assignments/${assignmentId}/statistics/${
      params.toString() ? `?${params.toString()}` : ''
    }`;
    const response = await apiClient.get(url);
    return response.data;
  },
};
