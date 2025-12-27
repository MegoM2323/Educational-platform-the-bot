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
    const resp = await unifiedAPI.request<any>('/materials/student/');
    
    if (resp.error) throw new Error(resp.error);
    
    // Извлекаем предметы из materials_by_subject
    const materialsBySubject = resp.data?.materials_by_subject || {};
    
    const subjects: StudentSubject[] = Object.values(materialsBySubject).map((subjectData: any) => ({
      id: subjectData.subject_info.id,
      name: subjectData.subject_info.name,
      color: subjectData.subject_info.color,
      teacher: {
        id: subjectData.subject_info.teacher?.id || 0,
        full_name: subjectData.subject_info.teacher?.full_name || 'Не назначен'
      },
      enrollment_status: 'enrolled'
    }));
    
    return subjects;
  },

  getSubjectMaterials: async (subjectId: number): Promise<SubjectMaterial[]> => {
    const resp = await unifiedAPI.request<any>('/materials/student/');
    if (resp.error) throw new Error(resp.error);
    
    // Извлекаем материалы для конкретного предмета из materials_by_subject
    const materialsBySubject = resp.data?.materials_by_subject || {};
    const subjectData = Object.values(materialsBySubject).find((subj: any) => subj.subject_info.id === subjectId);
    
    if (!subjectData) {
      return [];
    }
    
    const materials: SubjectMaterial[] = subjectData.materials.map((material: any) => ({
      id: material.id,
      title: material.title,
      description: material.description,
      created_at: material.created_at,
      type: material.type,
      status: material.status,
      progress_percentage: material.progress_percentage || 0
    }));
    
    return materials;
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
