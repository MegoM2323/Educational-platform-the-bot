import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { studentAPI, StudentSubject, SubjectMaterial, SubmissionResponse, FeedbackItem } from '@/integrations/api/student';

export const useStudentSubjects = () => {
  return useQuery<StudentSubject[]>({
    queryKey: ['student-subjects'],
    queryFn: () => studentAPI.getSubjects(),
    staleTime: 60000,
  });
};

export const useSubjectMaterials = (subjectId?: number) => {
  return useQuery<SubjectMaterial[]>({
    queryKey: ['student-subject-materials', subjectId],
    queryFn: () => studentAPI.getSubjectMaterials(subjectId!),
    enabled: !!subjectId,
    staleTime: 30000,
  });
};

export const useSubmitHomework = (materialId: number) => {
  const qc = useQueryClient();
  return useMutation<SubmissionResponse, Error, FormData>({
    mutationFn: (formData) => studentAPI.submitHomework(materialId, formData),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['student-submissions'] });
    },
  });
};

export const useStudentSubmissions = () => {
  return useQuery<SubmissionResponse[]>({
    queryKey: ['student-submissions'],
    queryFn: () => studentAPI.getSubmissions(),
    staleTime: 30000,
  });
};

export const useSubmissionFeedback = (submissionId?: number) => {
  return useQuery<FeedbackItem>({
    queryKey: ['submission-feedback', submissionId],
    queryFn: () => studentAPI.getFeedback(submissionId!),
    enabled: !!submissionId,
    staleTime: 30000,
  });
};
