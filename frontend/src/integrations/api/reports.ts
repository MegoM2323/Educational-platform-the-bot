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
