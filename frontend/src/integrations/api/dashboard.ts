// Dashboard API Service
import { unifiedAPI } from './unifiedClient';

export interface StudentDashboard {
  materials_count: number;
  completed_materials: number;
  progress_percentage: number;
  recent_materials: Array<{
    id: number;
    title: string;
    subject: string;
    assigned_date: string;
    completion_status: string;
  }>;
  upcoming_deadlines: Array<{
    id: number;
    title: string;
    deadline: string;
  }>;
}

export interface TeacherDashboard {
  total_students: number;
  total_materials: number;
  pending_reports: number;
  recent_activity: Array<{
    id: number;
    student_name: string;
    material_title: string;
    action: string;
    timestamp: string;
  }>;
}

export interface ParentDashboard {
  total_children: number;
  total_subjects: number;
  pending_payments: number;
  recent_reports: Array<{
    id: number;
    child_name: string;
    report_type: string;
    created_at: string;
  }>;
}

export interface StudentMaterial {
  id: number;
  title: string;
  description: string;
  subject: string;
  assigned_date: string;
  completion_status: string;
  progress_percentage: number;
  file_url?: string;
}

export interface TeacherMaterial {
  id: number;
  title: string;
  description: string;
  subject: string;
  created_at: string;
  assigned_students_count: number;
  file_url?: string;
}

export interface DistributeMaterialRequest {
  material_id: number;
  student_ids: number[];
  deadline?: string;
}

export interface ChildData {
  id: number;
  full_name: string;
  email: string;
  grade: string;
  subjects: Array<{
    id: number;
    name: string;
    teacher_name: string;
    enrollment_status: string;
    payment_status: string;
  }>;
}

// Student Dashboard API
export const studentDashboardAPI = {
  getDashboard: async (): Promise<StudentDashboard> => {
    const response = await unifiedAPI.getStudentDashboard();
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  getAssignedMaterials: async (): Promise<StudentMaterial[]> => {
    const response = await unifiedAPI.request<StudentMaterial[]>('/materials/materials/student/assigned/');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  updateMaterialProgress: async (materialId: number, progress: number): Promise<void> => {
    const response = await unifiedAPI.request(`/materials/materials/${materialId}/progress/`, {
      method: 'POST',
      body: JSON.stringify({ progress_percentage: progress }),
    });
    if (response.error) throw new Error(response.error);
  },

  getSubjects: async (): Promise<any[]> => {
    const response = await unifiedAPI.request<{ subjects: any[] }>('/materials/materials/student/subjects/');
    if (response.error) throw new Error(response.error);
    return response.data?.subjects || [];
  },
};

// Teacher Dashboard API
export const teacherDashboardAPI = {
  getDashboard: async (): Promise<TeacherDashboard> => {
    const response = await unifiedAPI.getTeacherDashboard();
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  getStudents: async (): Promise<any[]> => {
    const response = await unifiedAPI.request<any[]>('/materials/dashboard/teacher/students/');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  getMaterials: async (): Promise<TeacherMaterial[]> => {
    const response = await unifiedAPI.request<TeacherMaterial[]>('/materials/materials/teacher/');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  distributeMaterial: async (data: DistributeMaterialRequest): Promise<void> => {
    const response = await unifiedAPI.request('/materials/materials/teacher/distribute/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
  },

  getProgressOverview: async (): Promise<any> => {
    const response = await unifiedAPI.request('/materials/dashboard/teacher/progress/');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};

// Parent Dashboard API
export const parentDashboardAPI = {
  getDashboard: async (): Promise<ParentDashboard> => {
    const response = await unifiedAPI.getParentDashboard();
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  getChildren: async (): Promise<ChildData[]> => {
    const response = await unifiedAPI.request<ChildData[]>('/materials/dashboard/parent/children/');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  getChildSubjects: async (childId: number): Promise<any[]> => {
    const response = await unifiedAPI.request<any[]>(`/materials/dashboard/parent/children/${childId}/subjects/`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  getChildProgress: async (childId: number): Promise<any> => {
    const response = await unifiedAPI.request(`/materials/dashboard/parent/children/${childId}/progress/`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  initiatePayment: async (childId: number, enrollmentId: number, data: { amount: number; description?: string; create_subscription?: boolean }): Promise<any> => {
    const response = await unifiedAPI.request(`/materials/dashboard/parent/children/${childId}/payment/${enrollmentId}/`, {
      method: 'POST',
      body: JSON.stringify({
        amount: data.amount,
        description: data.description,
        create_subscription: data.create_subscription || false,
      }),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  cancelSubscription: async (childId: number, enrollmentId: number): Promise<any> => {
    const response = await unifiedAPI.request(`/materials/dashboard/parent/children/${childId}/subscription/${enrollmentId}/cancel/`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  getPaymentHistory: async (): Promise<any[]> => {
    const response = await unifiedAPI.request<any[]>('/materials/dashboard/parent/payments/');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  getPaymentStatus: async (childId: number): Promise<any> => {
    const response = await unifiedAPI.request(`/materials/dashboard/parent/children/${childId}/payments/`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },
};
