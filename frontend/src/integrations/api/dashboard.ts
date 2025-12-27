// Dashboard API Service
import { unifiedAPI } from './unifiedClient';
import { cacheInvalidationManager } from '@/services/cacheInvalidationManager';

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
  teacher_info?: {
    id: number;
    name: string;
    role: string;
    avatar?: string;
  };
  students: Array<{
    id: number;
    name: string;
    profile?: {
      grade: string;
      progress_percentage: number;
    };
    subjects?: Array<{
      id: number;
      name: string;
      color: string;
      enrollment_id: number;
      enrolled_at: string;
    }>;
  }>;
  materials: Array<{
    id: number;
    title: string;
    description: string;
    subject: {
      id: number;
      name: string;
      color: string;
    };
    status: 'active' | 'draft';
    assigned_count: number;
    created_at: string;
    file_url?: string;
  }>;
  progress_overview: {
    total_students: number;
    total_materials: number;
    total_assignments: number;
    completed_assignments: number;
  };
  reports: Array<{
    id: number;
    title: string;
    student_name: string;
    subject: string;
    created_at: string;
    status: 'draft' | 'sent';
  }>;
  general_chat?: {
    id: number;
    name: string;
  };
  profile?: {
    experience: number;
    subjects?: Array<string | { id: number; name: string }>;
    avatar_url?: string;
  };
}

export interface ParentDashboard {
  parent: {
    id: number;
    name: string;
    email: string;
  };
  children: Array<{
    id: number;
    name: string;
    grade: string;
    goal: string;
    tutor_name: string;
    progress_percentage: number;
    progress: number;
    avatar?: string;
    subjects: Array<{
      id: number;
      enrollment_id: number;
      name: string;
      teacher_name: string;
      teacher_id: number;
      payment_status: string;
      next_payment_date?: string | null;
      has_subscription: boolean;
      subscription_status?: string | null;
      expires_at?: string | null;
      amount?: string;
    }>;
    payments: Array<any>;
  }>;
  reports: Array<{
    id: number;
    child_name: string;
    report_type: string;
    created_at: string;
  }>;
  statistics: {
    total_children: number;
    average_progress: number;
    completed_payments: number;
    pending_payments: number;
    overdue_payments: number;
  };
  total_children: number;
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
  name: string;
  full_name: string;
  email: string;
  grade: string;
  goal?: string;
  subjects: Array<{
    id: number;
    enrollment_id: number;
    name: string;
    teacher_name: string;
    teacher_id: number;
    enrollment_status: string;
    payment_status: string;
    next_payment_date?: string | null;
    has_subscription: boolean;
    subscription_status?: string | null;
    expires_at?: string | null;
  }>;
}

// Student Dashboard API
export const studentDashboardAPI = {
  getDashboard: async (): Promise<StudentDashboard> => {
    const response = await unifiedAPI.getStudentDashboard();
    if (response.error) throw new Error(response.error);
    // Safe fallback: если data отсутствует, выбросить ошибку (критические данные)
    if (!response.data) {
      throw new Error('Не удалось загрузить данные дашборда');
    }
    return response.data;
  },

  getAssignedMaterials: async (): Promise<StudentMaterial[]> => {
    const response = await unifiedAPI.request<StudentMaterial[]>('/materials/student/assigned/');
    if (response.error) throw new Error(response.error);
    // Safe fallback: возвращаем пустой массив если данные отсутствуют
    return response.data ?? [];
  },

  updateMaterialProgress: async (materialId: number, progress: number): Promise<void> => {
    const response = await unifiedAPI.request(`/materials/${materialId}/progress/`, {
      method: 'POST',
      body: JSON.stringify({ progress_percentage: progress }),
    });
    if (response.error) throw new Error(response.error);

    // Invalidate student-related caches after progress update
    await cacheInvalidationManager.invalidateEndpoint('/materials/student/');
  },

  getSubjects: async (): Promise<any[]> => {
    const response = await unifiedAPI.request<{ subjects: any[] }>('/materials/student/subjects/');
    if (response.error) throw new Error(response.error);
    return response.data?.subjects || [];
  },
};

// Teacher Dashboard API
export const teacherDashboardAPI = {
  getDashboard: async (): Promise<TeacherDashboard> => {
    const response = await unifiedAPI.getTeacherDashboard();
    if (response.error) throw new Error(response.error);
    // Safe fallback: если data отсутствует, выбросить ошибку (критические данные)
    if (!response.data) {
      throw new Error('Не удалось загрузить данные дашборда');
    }
    return response.data;
  },

  getStudents: async (): Promise<any[]> => {
    const response = await unifiedAPI.request<any[]>('/dashboard/teacher/students/');
    if (response.error) throw new Error(response.error);
    // Safe fallback: возвращаем пустой массив если данные отсутствуют
    return response.data ?? [];
  },

  getMaterials: async (): Promise<TeacherMaterial[]> => {
    const response = await unifiedAPI.request<TeacherMaterial[]>('/materials/teacher/');
    if (response.error) throw new Error(response.error);
    // Safe fallback: возвращаем пустой массив если данные отсутствуют
    return response.data ?? [];
  },

  distributeMaterial: async (data: DistributeMaterialRequest): Promise<void> => {
    const response = await unifiedAPI.request('/materials/teacher/distribute/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);

    // Invalidate teacher dashboard after distributing materials
    await cacheInvalidationManager.invalidateEndpoint('/dashboard/teacher/');
  },

  getProgressOverview: async (): Promise<any> => {
    const response = await unifiedAPI.request('/dashboard/teacher/progress/');
    if (response.error) throw new Error(response.error);
    // Safe fallback: возвращаем пустой объект если данные отсутствуют
    return response.data ?? {};
  },
};

// Parent Dashboard API
export const parentDashboardAPI = {
  getDashboard: async (): Promise<ParentDashboard> => {
    const response = await unifiedAPI.getParentDashboard();
    if (response.error) throw new Error(response.error);
    // Safe fallback: если data отсутствует, выбросить ошибку (критические данные)
    if (!response.data) {
      throw new Error('Не удалось загрузить данные дашборда');
    }
    return response.data;
  },

  getChildren: async (): Promise<ChildData[]> => {
    const response = await unifiedAPI.request<ChildData[]>('/dashboard/parent/children/');
    if (response.error) throw new Error(response.error);
    // Safe fallback: возвращаем пустой массив если данные отсутствуют
    return response.data ?? [];
  },

  getChildSubjects: async (childId: number): Promise<any[]> => {
    const response = await unifiedAPI.request<any[]>(`/dashboard/parent/children/${childId}/subjects/`);
    if (response.error) throw new Error(response.error);
    // Safe fallback: возвращаем пустой массив если данные отсутствуют
    return response.data ?? [];
  },

  getChildProgress: async (childId: number): Promise<any> => {
    const response = await unifiedAPI.request(`/dashboard/parent/children/${childId}/progress/`);
    if (response.error) throw new Error(response.error);
    // Safe fallback: возвращаем пустой объект если данные отсутствуют
    return response.data ?? {};
  },

  initiatePayment: async (childId: number, enrollmentId: number, data: { amount?: number; description?: string; create_subscription?: boolean }): Promise<any> => {
    const requestBody: any = {
      description: data.description,
      create_subscription: data.create_subscription || false,
    };
    // amount передаем только если указан явно, иначе бэкенд определит из настроек
    if (data.amount !== undefined) {
      requestBody.amount = data.amount;
    }
    const response = await unifiedAPI.request(`/dashboard/parent/children/${childId}/payment/${enrollmentId}/`, {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
    if (response.error) throw new Error(response.error);

    // Invalidate parent children and payment caches after payment initiation
    await cacheInvalidationManager.invalidateEndpoint(`/dashboard/parent/children/`);

    // Safe fallback: если data отсутствует, выбросить ошибку (критические данные для оплаты)
    if (!response.data) {
      throw new Error('Не удалось инициировать оплату');
    }
    return response.data;
  },

  cancelSubscription: async (childId: number, enrollmentId: number): Promise<any> => {
    const response = await unifiedAPI.request(`/dashboard/parent/children/${childId}/subscription/${enrollmentId}/cancel/`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);

    // Invalidate parent children and subscription caches after cancellation
    await cacheInvalidationManager.invalidateEndpoint(`/dashboard/parent/children/`);

    // Safe fallback: если data отсутствует, выбросить ошибку (критические данные)
    if (!response.data) {
      throw new Error('Не удалось отменить подписку');
    }
    return response.data;
  },

  getPaymentHistory: async (): Promise<any[]> => {
    const response = await unifiedAPI.request<any[]>('/dashboard/parent/payments/');
    if (response.error) throw new Error(response.error);
    // Safe fallback: возвращаем пустой массив если данные отсутствуют
    return response.data ?? [];
  },

  getPaymentStatus: async (childId: number): Promise<any> => {
    const response = await unifiedAPI.request(`/dashboard/parent/children/${childId}/payments/`);
    if (response.error) throw new Error(response.error);
    // Safe fallback: возвращаем пустой объект если данные отсутствуют
    return response.data ?? {};
  },
};
