// Reports React Query Hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  reportsAPI,
  StudentReport,
  CreateReportRequest,
  ReportTemplate,
} from '../integrations/api/reports';
import { toast } from 'sonner';

// Get teacher's reports
export const useTeacherReports = () => {
  return useQuery({
    queryKey: ['teacher-reports'],
    queryFn: () => reportsAPI.getTeacherReports(),
    staleTime: 60000, // 1 minute
    retry: 2,
  });
};

// Get parent's reports
export const useParentReports = (childId?: number) => {
  return useQuery({
    queryKey: ['parent-reports', childId],
    queryFn: () => reportsAPI.getParentReports(childId),
    enabled: !childId || !!childId,
    staleTime: 60000,
    retry: 2,
  });
};

// Get report by ID
export const useReport = (reportId: number) => {
  return useQuery({
    queryKey: ['report', reportId],
    queryFn: () => reportsAPI.getReport(reportId),
    enabled: !!reportId,
    staleTime: 60000,
    retry: 2,
  });
};

// Get report templates
export const useReportTemplates = () => {
  return useQuery({
    queryKey: ['report-templates'],
    queryFn: () => reportsAPI.getTemplates(),
    staleTime: 300000, // 5 minutes - templates don't change often
    retry: 2,
  });
};

// Create report
export const useCreateReport = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateReportRequest) =>
      reportsAPI.createReport(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher-reports'] });
      queryClient.invalidateQueries({ queryKey: ['parent-reports'] });
      queryClient.invalidateQueries({ queryKey: ['teacher-dashboard'] });
      toast.success('Отчет успешно создан и отправлен родителю');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка создания отчета: ${error.message}`);
    },
  });
};

// Update report
export const useUpdateReport = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ reportId, data }: { reportId: number; data: Partial<CreateReportRequest> }) =>
      reportsAPI.updateReport(reportId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher-reports'] });
      queryClient.invalidateQueries({ queryKey: ['parent-reports'] });
      queryClient.invalidateQueries({ queryKey: ['report'] });
      toast.success('Отчет успешно обновлен');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка обновления отчета: ${error.message}`);
    },
  });
};

// Delete report
export const useDeleteReport = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (reportId: number) =>
      reportsAPI.deleteReport(reportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher-reports'] });
      queryClient.invalidateQueries({ queryKey: ['parent-reports'] });
      toast.success('Отчет успешно удален');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка удаления отчета: ${error.message}`);
    },
  });
};
