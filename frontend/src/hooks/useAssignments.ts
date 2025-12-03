import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assignmentsAPI, Assignment, AssignmentSubmission, CreateAssignmentPayload, CreateSubmissionPayload, GradeSubmissionPayload } from '@/integrations/api/assignmentsAPI';
import { useToast } from '@/hooks/use-toast';

export const useAssignments = (filters?: Record<string, any>) => {
  return useQuery({
    queryKey: ['assignments', filters],
    queryFn: () => assignmentsAPI.getAssignments(filters),
    staleTime: 60000,
  });
};

export const useAssignment = (id: number) => {
  return useQuery({
    queryKey: ['assignment', id],
    queryFn: () => assignmentsAPI.getAssignment(id),
    enabled: !!id,
    staleTime: 60000,
  });
};

export const useCreateAssignment = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: CreateAssignmentPayload) => assignmentsAPI.createAssignment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      toast({
        title: 'Успешно',
        description: 'Задание создано',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error?.message || 'Не удалось создать задание',
        variant: 'destructive',
      });
    },
  });
};

export const useUpdateAssignment = (id: number) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: Partial<CreateAssignmentPayload>) => assignmentsAPI.updateAssignment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignment', id] });
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      toast({
        title: 'Успешно',
        description: 'Задание обновлено',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error?.message || 'Не удалось обновить задание',
        variant: 'destructive',
      });
    },
  });
};

export const useDeleteAssignment = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (id: number) => assignmentsAPI.deleteAssignment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      toast({
        title: 'Успешно',
        description: 'Задание удалено',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error?.message || 'Не удалось удалить задание',
        variant: 'destructive',
      });
    },
  });
};

export const useSubmissions = (filters?: Record<string, any>) => {
  return useQuery({
    queryKey: ['submissions', filters],
    queryFn: () => assignmentsAPI.getSubmissions(filters),
    staleTime: 60000,
  });
};

export const useSubmission = (id: number) => {
  return useQuery({
    queryKey: ['submission', id],
    queryFn: () => assignmentsAPI.getSubmission(id),
    enabled: !!id,
    staleTime: 60000,
  });
};

export const useSubmitAssignment = (assignmentId: number) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: CreateSubmissionPayload) => assignmentsAPI.submitAssignment(assignmentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      queryClient.invalidateQueries({ queryKey: ['assignment', assignmentId] });
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      toast({
        title: 'Успешно',
        description: 'Ответ отправлен',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error?.message || 'Не удалось отправить ответ',
        variant: 'destructive',
      });
    },
  });
};

export const useGradeSubmission = (submissionId: number) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: GradeSubmissionPayload) => assignmentsAPI.gradeSubmission(submissionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submission', submissionId] });
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      toast({
        title: 'Успешно',
        description: 'Оценка выставлена',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Ошибка',
        description: error?.message || 'Не удалось выставить оценку',
        variant: 'destructive',
      });
    },
  });
};

export const useAssignmentSubmissions = (assignmentId: number) => {
  return useQuery({
    queryKey: ['assignment-submissions', assignmentId],
    queryFn: () => assignmentsAPI.getAssignmentSubmissions(assignmentId),
    enabled: !!assignmentId,
    staleTime: 60000,
  });
};
