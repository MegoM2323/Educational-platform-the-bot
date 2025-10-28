import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tutorAPI, CreateStudentRequest, AssignSubjectRequest, TutorStudent, CreateStudentResponse } from '@/integrations/api/tutor';

export const useTutorStudents = () => {
  return useQuery<TutorStudent[]>({
    queryKey: ['tutor-students'],
    queryFn: () => tutorAPI.listStudents(),
    staleTime: 60000,
    retry: 2,
  });
};

export const useCreateTutorStudent = () => {
  const qc = useQueryClient();
  return useMutation<CreateStudentResponse, Error, CreateStudentRequest>({
    mutationFn: (data) => tutorAPI.createStudent(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tutor-students'] });
    },
  });
};

export const useAssignSubject = (studentId: number) => {
  const qc = useQueryClient();
  return useMutation<void, Error, AssignSubjectRequest>({
    mutationFn: (data) => tutorAPI.assignSubject(studentId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tutor-students'] });
      qc.invalidateQueries({ queryKey: ['tutor-student', studentId] });
    },
  });
};

export const useTutorStudent = (studentId: number) => {
  return useQuery<TutorStudent>({
    queryKey: ['tutor-student', studentId],
    queryFn: () => tutorAPI.getStudent(studentId),
    enabled: !!studentId,
    staleTime: 30000,
  });
};
