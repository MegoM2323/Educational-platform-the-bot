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

      const data = response.data;

      // Extract students and their subjects for scheduling
      if (data?.students) {
        // For each student, map subjects to include both student ID and subject info
        data.students = data.students.map((student: any) => ({
          ...student,
          id: String(student.id), // Ensure ID is string for form compatibility
          full_name: student.name,
          subjects: (student.subjects || []).map((s: any) => ({
            id: String(s.id),
            name: s.name
          }))
        }));
      }

      return data;
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
