// Reports API Service
import { unifiedAPI } from './unifiedClient';

export interface StudentReport {
  id: number;
  student_name: string;
  report_type: string;
  title: string;
  content: string;
  academic_performance: number;
  behavior: string;
  attendance: number;
  recommendations: string;
  created_at: string;
  parent_notified: boolean;
  parent_notification_date?: string;
}

export interface CreateReportRequest {
  student_id: number;
  report_type: string;
  title: string;
  content: string;
  academic_performance?: number;
  behavior?: string;
  attendance?: number;
  recommendations?: string;
}

export interface ReportTemplate {
  id: number;
  name: string;
  report_type: string;
  template_content: string;
  created_at: string;
}

// Reports API
export const reportsAPI = {
  // Create report (Teacher)
  createReport: async (data: CreateReportRequest): Promise<StudentReport> => {
    const response = await unifiedAPI.request<StudentReport>('/materials/reports/teacher/create/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Get teacher's reports
  getTeacherReports: async (): Promise<StudentReport[]> => {
    const response = await unifiedAPI.request<StudentReport[]>('/materials/reports/teacher/');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Get parent's reports
  getParentReports: async (childId?: number): Promise<StudentReport[]> => {
    const url = childId 
      ? `/materials/dashboard/parent/reports/${childId}/`
      : '/materials/dashboard/parent/reports/';
    const response = await unifiedAPI.request<StudentReport[]>(url);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Get report by ID
  getReport: async (reportId: number): Promise<StudentReport> => {
    const response = await unifiedAPI.request<StudentReport>(`/reports/reports/${reportId}/`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Get report templates
  getTemplates: async (): Promise<ReportTemplate[]> => {
    const response = await unifiedAPI.request<ReportTemplate[]>('/reports/templates/');
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Update report
  updateReport: async (reportId: number, data: Partial<CreateReportRequest>): Promise<StudentReport> => {
    const response = await unifiedAPI.request<StudentReport>(`/reports/reports/${reportId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Delete report
  deleteReport: async (reportId: number): Promise<void> => {
    const response = await unifiedAPI.request(`/reports/reports/${reportId}/`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },
};

// Еженедельные отчеты тьютора родителю
export interface TutorWeeklyReport {
  id: number;
  tutor: number;
  tutor_name: string;
  student: number;
  student_name: string;
  parent: number | null;
  parent_name: string;
  week_start: string;
  week_end: string;
  title: string;
  summary: string;
  academic_progress?: string;
  behavior_notes?: string;
  achievements?: string;
  concerns?: string;
  recommendations?: string;
  attendance_days: number;
  total_days: number;
  attendance_percentage: number;
  progress_percentage: number;
  status: 'draft' | 'sent' | 'read' | 'archived';
  attachment?: string;
  created_at: string;
  updated_at: string;
  sent_at?: string;
  read_at?: string;
}

export interface CreateTutorWeeklyReportRequest {
  student: number;
  week_start: string;
  week_end: string;
  title?: string;
  summary: string;
  academic_progress?: string;
  behavior_notes?: string;
  achievements?: string;
  concerns?: string;
  recommendations?: string;
  attendance_days?: number;
  total_days?: number;
  progress_percentage?: number;
  attachment?: File;
}

export interface TutorStudent {
  id: number;
  name: string;
  username: string;
  grade: string;
  parent_id: number | null;
  parent_name: string | null;
}

// Еженедельные отчеты преподавателя тьютору
export interface TeacherWeeklyReport {
  id: number;
  teacher: number;
  teacher_name: string;
  student: number;
  student_name: string;
  tutor: number | null;
  tutor_name: string;
  subject: number;
  subject_name: string;
  subject_color: string;
  week_start: string;
  week_end: string;
  title: string;
  summary: string;
  academic_progress?: string;
  performance_notes?: string;
  achievements?: string;
  concerns?: string;
  recommendations?: string;
  assignments_completed: number;
  assignments_total: number;
  completion_percentage: number;
  average_score?: number;
  attendance_percentage: number;
  status: 'draft' | 'sent' | 'read' | 'archived';
  attachment?: string;
  created_at: string;
  updated_at: string;
  sent_at?: string;
  read_at?: string;
}

export interface CreateTeacherWeeklyReportRequest {
  student: number;
  subject: number;
  week_start: string;
  week_end: string;
  title?: string;
  summary: string;
  academic_progress?: string;
  performance_notes?: string;
  achievements?: string;
  concerns?: string;
  recommendations?: string;
  assignments_completed?: number;
  assignments_total?: number;
  average_score?: number;
  attendance_percentage?: number;
  attachment?: File;
}

export interface TeacherStudent {
  id: number;
  name: string;
  username: string;
  grade: string;
  tutor_id: number | null;
  tutor_name: string | null;
  subjects: Array<{
    id: number;
    name: string;
    color: string;
  }>;
}

// API для еженедельных отчетов тьютора
export const tutorWeeklyReportsAPI = {
  // Получить все отчеты тьютора
  getReports: async (): Promise<TutorWeeklyReport[]> => {
    console.log('[API] Fetching tutor weekly reports...');
    const response = await unifiedAPI.request<TutorWeeklyReport[]>('/reports/tutor-weekly-reports/');
    console.log('[API] Tutor weekly reports response:', response);
    if (response.error) {
      console.error('[API] Tutor weekly reports error:', response.error);
      throw new Error(response.error);
    }
    const data = response.data || [];
    console.log('[API] Tutor weekly reports data:', data, 'length:', data.length);
    return data;
  },

  // Получить отчет по ID
  getReport: async (reportId: number): Promise<TutorWeeklyReport> => {
    const response = await unifiedAPI.request<TutorWeeklyReport>(`/reports/tutor-weekly-reports/${reportId}/`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Создать отчет
  createReport: async (data: CreateTutorWeeklyReportRequest): Promise<TutorWeeklyReport> => {
    // Очищаем кэш перед созданием отчета
    const { cacheService } = await import('../../services/cacheService');
    cacheService.delete('/reports/tutor-weekly-reports/');
    cacheService.delete('/reports/tutor-weekly-reports/available_students/');
    
    // Если есть файл, используем FormData, иначе JSON
    const hasFile = data.attachment && data.attachment instanceof File;
    
    if (hasFile) {
      const formData = new FormData();
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (key === 'attachment' && value instanceof File) {
            formData.append(key, value);
          } else {
            formData.append(key, String(value));
          }
        }
      });

      const response = await unifiedAPI.request<TutorWeeklyReport>('/reports/tutor-weekly-reports/', {
        method: 'POST',
        body: formData,
      });
      if (!response.success || response.error) {
        throw new Error(response.error || 'Ошибка при создании отчета');
      }
      if (!response.data) {
        throw new Error('Отчет не был создан');
      }
      // Очищаем кэш после успешного создания
      cacheService.delete('/reports/tutor-weekly-reports/');
      return response.data;
    } else {
      // Отправляем как JSON без файла
      const jsonData = { ...data };
      delete jsonData.attachment;
      
      const response = await unifiedAPI.request<TutorWeeklyReport>('/reports/tutor-weekly-reports/', {
        method: 'POST',
        body: JSON.stringify(jsonData),
      });
      if (!response.success || response.error) {
        throw new Error(response.error || 'Ошибка при создании отчета');
      }
      if (!response.data) {
        throw new Error('Отчет не был создан');
      }
      // Очищаем кэш после успешного создания
      cacheService.delete('/reports/tutor-weekly-reports/');
      return response.data;
    }
  },

  // Обновить отчет
  updateReport: async (reportId: number, data: Partial<CreateTutorWeeklyReportRequest>): Promise<TutorWeeklyReport> => {
    const hasFile = data.attachment && data.attachment instanceof File;
    
    if (hasFile) {
      const formData = new FormData();
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (key === 'attachment' && value instanceof File) {
            formData.append(key, value);
          } else {
            formData.append(key, String(value));
          }
        }
      });

      const response = await unifiedAPI.request<TutorWeeklyReport>(`/reports/tutor-weekly-reports/${reportId}/`, {
        method: 'PATCH',
        body: formData,
      });
      if (response.error) throw new Error(response.error);
      return response.data!;
    } else {
      const jsonData = { ...data };
      delete jsonData.attachment;
      
      const response = await unifiedAPI.request<TutorWeeklyReport>(`/reports/tutor-weekly-reports/${reportId}/`, {
        method: 'PATCH',
        body: JSON.stringify(jsonData),
      });
      if (response.error) throw new Error(response.error);
      return response.data!;
    }
  },

  // Удалить отчет
  deleteReport: async (reportId: number): Promise<void> => {
    const response = await unifiedAPI.request(`/reports/tutor-weekly-reports/${reportId}/`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  // Отправить отчет
  sendReport: async (reportId: number): Promise<void> => {
    // Очищаем кэш перед отправкой отчета
    const { cacheService } = await import('../../services/cacheService');
    cacheService.delete('/reports/tutor-weekly-reports/');
    
    const response = await unifiedAPI.request(`/reports/tutor-weekly-reports/${reportId}/send/`, {
      method: 'POST',
    });
    if (!response.success || response.error) {
      throw new Error(response.error || 'Ошибка при отправке отчета');
    }
    // Очищаем кэш после успешной отправки
    cacheService.delete('/reports/tutor-weekly-reports/');
  },

  // Отметить как прочитанный
  markAsRead: async (reportId: number): Promise<void> => {
    const response = await unifiedAPI.request(`/reports/tutor-weekly-reports/${reportId}/mark_read/`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
  },

  // Получить список доступных студентов
  getAvailableStudents: async (): Promise<TutorStudent[]> => {
    console.log('[API] Fetching tutor available students...');
    const response = await unifiedAPI.request<{ students: TutorStudent[] }>('/reports/tutor-weekly-reports/available_students/');
    console.log('[API] Tutor available students response:', response);
    if (response.error) {
      console.error('[API] Tutor available students error:', response.error);
      throw new Error(response.error);
    }
    const data = response.data?.students || [];
    console.log('[API] Tutor available students data:', data, 'length:', data.length);
    return data;
  },
};

// API для еженедельных отчетов преподавателя
export const teacherWeeklyReportsAPI = {
  // Получить все отчеты преподавателя
  getReports: async (): Promise<TeacherWeeklyReport[]> => {
    console.log('[API] Fetching teacher weekly reports...');
    const response = await unifiedAPI.request<TeacherWeeklyReport[]>('/reports/teacher-weekly-reports/');
    console.log('[API] Teacher weekly reports response:', response);
    if (response.error) {
      console.error('[API] Teacher weekly reports error:', response.error);
      throw new Error(response.error);
    }
    const data = response.data || [];
    console.log('[API] Teacher weekly reports data:', data, 'length:', data.length);
    return data;
  },

  // Получить отчет по ID
  getReport: async (reportId: number): Promise<TeacherWeeklyReport> => {
    const response = await unifiedAPI.request<TeacherWeeklyReport>(`/reports/teacher-weekly-reports/${reportId}/`);
    if (response.error) throw new Error(response.error);
    return response.data!;
  },

  // Создать отчет
  createReport: async (data: CreateTeacherWeeklyReportRequest): Promise<TeacherWeeklyReport> => {
    // Очищаем кэш перед созданием отчета
    const { cacheService } = await import('../../services/cacheService');
    cacheService.delete('/reports/teacher-weekly-reports/');
    cacheService.delete('/reports/teacher-weekly-reports/available_students/');
    
    const hasFile = data.attachment && data.attachment instanceof File;
    
    if (hasFile) {
      const formData = new FormData();
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (key === 'attachment' && value instanceof File) {
            formData.append(key, value);
          } else {
            formData.append(key, String(value));
          }
        }
      });

      const response = await unifiedAPI.request<TeacherWeeklyReport>('/reports/teacher-weekly-reports/', {
        method: 'POST',
        body: formData,
      });
      if (!response.success || response.error) {
        throw new Error(response.error || 'Ошибка при создании отчета');
      }
      if (!response.data) {
        throw new Error('Отчет не был создан');
      }
      // Очищаем кэш после успешного создания
      cacheService.delete('/reports/teacher-weekly-reports/');
      return response.data;
    } else {
      const jsonData = { ...data };
      delete jsonData.attachment;
      
      const response = await unifiedAPI.request<TeacherWeeklyReport>('/reports/teacher-weekly-reports/', {
        method: 'POST',
        body: JSON.stringify(jsonData),
      });
      if (!response.success || response.error) {
        throw new Error(response.error || 'Ошибка при создании отчета');
      }
      if (!response.data) {
        throw new Error('Отчет не был создан');
      }
      // Очищаем кэш после успешного создания
      cacheService.delete('/reports/teacher-weekly-reports/');
      return response.data;
    }
  },

  // Обновить отчет
  updateReport: async (reportId: number, data: Partial<CreateTeacherWeeklyReportRequest>): Promise<TeacherWeeklyReport> => {
    const hasFile = data.attachment && data.attachment instanceof File;
    
    if (hasFile) {
      const formData = new FormData();
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (key === 'attachment' && value instanceof File) {
            formData.append(key, value);
          } else {
            formData.append(key, String(value));
          }
        }
      });

      const response = await unifiedAPI.request<TeacherWeeklyReport>(`/reports/teacher-weekly-reports/${reportId}/`, {
        method: 'PATCH',
        body: formData,
      });
      if (response.error) throw new Error(response.error);
      return response.data!;
    } else {
      const jsonData = { ...data };
      delete jsonData.attachment;
      
      const response = await unifiedAPI.request<TeacherWeeklyReport>(`/reports/teacher-weekly-reports/${reportId}/`, {
        method: 'PATCH',
        body: JSON.stringify(jsonData),
      });
      if (response.error) throw new Error(response.error);
      return response.data!;
    }
  },

  // Удалить отчет
  deleteReport: async (reportId: number): Promise<void> => {
    const response = await unifiedAPI.request(`/reports/teacher-weekly-reports/${reportId}/`, {
      method: 'DELETE',
    });
    if (response.error) throw new Error(response.error);
  },

  // Отправить отчет
  sendReport: async (reportId: number): Promise<void> => {
    // Очищаем кэш перед отправкой отчета
    const { cacheService } = await import('../../services/cacheService');
    cacheService.delete('/reports/teacher-weekly-reports/');
    
    const response = await unifiedAPI.request(`/reports/teacher-weekly-reports/${reportId}/send/`, {
      method: 'POST',
    });
    if (!response.success || response.error) {
      throw new Error(response.error || 'Ошибка при отправке отчета');
    }
    // Очищаем кэш после успешной отправки
    cacheService.delete('/reports/teacher-weekly-reports/');
  },

  // Отметить как прочитанный
  markAsRead: async (reportId: number): Promise<void> => {
    const response = await unifiedAPI.request(`/reports/teacher-weekly-reports/${reportId}/mark_read/`, {
      method: 'POST',
    });
    if (response.error) throw new Error(response.error);
  },

  // Получить список доступных студентов
  getAvailableStudents: async (): Promise<TeacherStudent[]> => {
    console.log('[API] Fetching teacher available students...');
    const response = await unifiedAPI.request<{ students: TeacherStudent[] }>('/reports/teacher-weekly-reports/available_students/');
    console.log('[API] Teacher available students response:', response);
    if (response.error) {
      console.error('[API] Teacher available students error:', response.error);
      throw new Error(response.error);
    }
    const data = response.data?.students || [];
    console.log('[API] Teacher available students data:', data, 'length:', data.length);
    return data;
  },

  // Получить отчеты по студенту (для тьютора)
  getReportsByStudent: async (studentId: number): Promise<TeacherWeeklyReport[]> => {
    const response = await unifiedAPI.request<TeacherWeeklyReport[]>(`/reports/teacher-weekly-reports/by_student/?student_id=${studentId}`);
    if (response.error) throw new Error(response.error);
    return response.data || [];
  },
};
