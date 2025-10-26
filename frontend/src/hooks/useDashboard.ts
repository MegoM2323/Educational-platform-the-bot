// Dashboard React Query Hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  studentDashboardAPI,
  teacherDashboardAPI,
  parentDashboardAPI,
  StudentDashboard,
  TeacherDashboard,
  ParentDashboard,
  StudentMaterial,
  TeacherMaterial,
  ChildData,
  DistributeMaterialRequest,
} from '../integrations/api/dashboard';
import { toast } from 'sonner';

// Student Dashboard Hooks
export const useStudentDashboard = () => {
  return useQuery({
    queryKey: ['student-dashboard'],
    queryFn: () => studentDashboardAPI.getDashboard(),
    staleTime: 30000, // 30 seconds
    retry: 2,
  });
};

export const useStudentMaterials = () => {
  return useQuery({
    queryKey: ['student-materials'],
    queryFn: () => studentDashboardAPI.getAssignedMaterials(),
    staleTime: 60000, // 1 minute
    retry: 2,
  });
};

export const useUpdateMaterialProgress = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ materialId, progress }: { materialId: number; progress: number }) =>
      studentDashboardAPI.updateMaterialProgress(materialId, progress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['student-materials'] });
      queryClient.invalidateQueries({ queryKey: ['student-dashboard'] });
      toast.success('Прогресс обновлен');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка обновления прогресса: ${error.message}`);
    },
  });
};

// Teacher Dashboard Hooks
export const useTeacherDashboard = () => {
  return useQuery({
    queryKey: ['teacher-dashboard'],
    queryFn: () => teacherDashboardAPI.getDashboard(),
    staleTime: 30000,
    retry: 2,
  });
};

export const useTeacherStudents = () => {
  return useQuery({
    queryKey: ['teacher-students'],
    queryFn: () => teacherDashboardAPI.getStudents(),
    staleTime: 60000,
    retry: 2,
  });
};

export const useTeacherMaterials = () => {
  return useQuery({
    queryKey: ['teacher-materials'],
    queryFn: () => teacherDashboardAPI.getMaterials(),
    staleTime: 60000,
    retry: 2,
  });
};

export const useDistributeMaterial = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: DistributeMaterialRequest) =>
      teacherDashboardAPI.distributeMaterial(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher-materials'] });
      queryClient.invalidateQueries({ queryKey: ['teacher-dashboard'] });
      toast.success('Материал успешно распространен');
    },
    onError: (error: Error) => {
      toast.error(`Ошибка распространения материала: ${error.message}`);
    },
  });
};

export const useTeacherProgressOverview = () => {
  return useQuery({
    queryKey: ['teacher-progress-overview'],
    queryFn: () => teacherDashboardAPI.getProgressOverview(),
    staleTime: 60000,
    retry: 2,
  });
};

// Parent Dashboard Hooks
export const useParentDashboard = () => {
  return useQuery({
    queryKey: ['parent-dashboard'],
    queryFn: () => parentDashboardAPI.getDashboard(),
    staleTime: 30000,
    retry: 2,
  });
};

export const useParentChildren = () => {
  return useQuery({
    queryKey: ['parent-children'],
    queryFn: () => parentDashboardAPI.getChildren(),
    staleTime: 60000,
    retry: 2,
  });
};

export const useChildSubjects = (childId: number) => {
  return useQuery({
    queryKey: ['child-subjects', childId],
    queryFn: () => parentDashboardAPI.getChildSubjects(childId),
    enabled: !!childId,
    staleTime: 60000,
    retry: 2,
  });
};

export const useChildProgress = (childId: number) => {
  return useQuery({
    queryKey: ['child-progress', childId],
    queryFn: () => parentDashboardAPI.getChildProgress(childId),
    enabled: !!childId,
    staleTime: 60000,
    retry: 2,
  });
};

export const useInitiatePayment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ childId, subjectId }: { childId: number; subjectId: number }) =>
      parentDashboardAPI.initiatePayment(childId, subjectId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['parent-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['parent-children'] });
      toast.success('Переадресация на страницу оплаты');
      // Redirect to payment URL if provided
      if (data?.confirmation_url) {
        window.location.href = data.confirmation_url;
      }
    },
    onError: (error: Error) => {
      toast.error(`Ошибка инициации оплаты: ${error.message}`);
    },
  });
};

export const usePaymentStatus = (childId: number) => {
  return useQuery({
    queryKey: ['payment-status', childId],
    queryFn: () => parentDashboardAPI.getPaymentStatus(childId),
    enabled: !!childId,
    staleTime: 30000,
    retry: 2,
  });
};
