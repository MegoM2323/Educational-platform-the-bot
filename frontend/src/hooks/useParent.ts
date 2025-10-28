import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { parentDashboardAPI, type ChildData } from '@/integrations/api/dashboard';

export const useParentChildren = () => {
  return useQuery<ChildData[]>({
    queryKey: ['parent-children'],
    queryFn: () => parentDashboardAPI.getChildren(),
    staleTime: 60000,
  });
};

export const useChildSubjects = (childId?: number) => {
  return useQuery<any[]>({
    queryKey: ['parent-child-subjects', childId],
    queryFn: () => parentDashboardAPI.getChildSubjects(childId!),
    enabled: !!childId,
    staleTime: 60000,
  });
};

export const useInitiatePayment = (childId: number, subjectId: number) => {
  const qc = useQueryClient();
  return useMutation<any, Error, void>({
    mutationFn: () => parentDashboardAPI.initiatePayment(childId, subjectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['parent-children'] });
      qc.invalidateQueries({ queryKey: ['parent-child-subjects', childId] });
    },
  });
};

export const useChildProgress = (childId?: number) => {
  return useQuery<any>({
    queryKey: ['parent-child-progress', childId],
    queryFn: () => parentDashboardAPI.getChildProgress(childId!),
    enabled: !!childId,
    staleTime: 60000,
  });
};
