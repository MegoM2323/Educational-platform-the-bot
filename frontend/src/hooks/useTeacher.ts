import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { teacherAPI, PendingSubmission, ProvideFeedbackRequest } from '@/integrations/api/teacher';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

export const useTeacherDashboard = () => {
  return useQuery({
    queryKey: ['teacher-dashboard'],
    queryFn: async () => {
      const response = await unifiedAPI.getTeacherDashboard();
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data;
    },
    staleTime: 60000, // 1 minute
    refetchOnWindowFocus: true,
    refetchOnMount: true,
  });
};

export const usePendingSubmissions = () => {
  return useQuery<PendingSubmission[]>({
    queryKey: ['teacher-pending-submissions'],
    queryFn: () => teacherAPI.getPendingSubmissions(),
    staleTime: 30000,
  });
};

export const useProvideFeedback = () => {
  const qc = useQueryClient();
  return useMutation<void, Error, { submissionId: number; data: ProvideFeedbackRequest }>({
    mutationFn: ({ submissionId, data }) => teacherAPI.provideFeedback(submissionId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teacher-pending-submissions'] });
    },
  });
};

export const useUpdateSubmissionStatus = () => {
  const qc = useQueryClient();
  return useMutation<void, Error, { submissionId: number; status: 'pending' | 'reviewed' | 'needs_changes' }>({
    mutationFn: ({ submissionId, status }) => teacherAPI.updateSubmissionStatus(submissionId, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teacher-pending-submissions'] });
    },
  });
};
