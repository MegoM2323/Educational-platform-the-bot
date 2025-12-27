import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { logger } from '@/utils/logger';
import { tutorAPI, CreateStudentRequest, AssignSubjectRequest, TutorStudent, CreateStudentResponse } from '@/integrations/api/tutor';
import { useToast } from '@/hooks/use-toast';
import { cacheService } from '@/services/cacheService';

export const useTutorStudents = () => {
  return useQuery<TutorStudent[]>({
    queryKey: ['tutor-students'],
    queryFn: async () => {
      logger.debug('[useTutorStudents] Fetching students list...');
      const result = await tutorAPI.listStudents();
      logger.debug('[useTutorStudents] Fetched', result.length, 'students');
      // Логируем предметы для каждого студента
      result.forEach(s => {
        const subjectsCount = s.subjects?.length || 0;
        logger.debug(`[useTutorStudents] Student ${s.id} (${s.full_name}) has ${subjectsCount} subjects`);
        if (subjectsCount > 0) {
          s.subjects?.forEach(subj => {
            logger.debug(`  - ${subj.name} (teacher: ${subj.teacher_name}, enrollment_id: ${subj.enrollment_id})`);
          });
        }
      });
      return result;
    },
    staleTime: 0, // Данные сразу считаются устаревшими
    gcTime: 0, // Не кешируем данные - всегда загружаем свежие
    retry: 2,
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    refetchOnReconnect: true,
    refetchInterval: false, // Не обновляем автоматически по таймеру
  });
};

export const useCreateTutorStudent = () => {
  const qc = useQueryClient();
  const { toast } = useToast();
  
  return useMutation<CreateStudentResponse, Error, CreateStudentRequest>({
    mutationFn: async (data) => {
      logger.debug('[useCreateTutorStudent] Creating student with data:', data);
      const result = await tutorAPI.createStudent(data);
      logger.debug('[useCreateTutorStudent] Student created successfully:', result);
      return result;
    },
    onSuccess: async (data) => {
      logger.debug('[useCreateTutorStudent] onSuccess called, invalidating and refetching...');
      
      // Очищаем кеш в cacheService для списка студентов
      cacheService.delete('/tutor/students/');
      
      // Инвалидируем кеш React Query
      qc.invalidateQueries({ 
        queryKey: ['tutor-students']
      });
      
      // Принудительно перезагружаем данные
      await qc.refetchQueries({ 
        queryKey: ['tutor-students'],
        type: 'active'
      });
      
      logger.debug('[useCreateTutorStudent] Data refreshed successfully');
      
      toast({
        title: "Успешно",
        description: "Ученик и родитель успешно созданы",
      });
    },
    onError: (error: any) => {
      logger.error('[useCreateTutorStudent] Error:', error);
      const errorMessage = error?.message || 'Не удалось создать ученика';
      toast({
        title: "Ошибка",
        description: errorMessage,
        variant: "destructive"
      });
    },
  });
};

export const useAssignSubject = (studentId: number) => {
  const qc = useQueryClient();
  const { toast } = useToast();
  
  return useMutation<void, Error, AssignSubjectRequest>({
    mutationFn: async (data) => {
      logger.debug('[useAssignSubject] Starting mutation for student:', studentId, 'data:', data);
      await tutorAPI.assignSubject(studentId, data);
      logger.debug('[useAssignSubject] Mutation completed successfully');
    },
    onSuccess: async () => {
      logger.debug('[useAssignSubject] onSuccess called, invalidating cache...');
      
      // Очищаем кеш в cacheService для списка студентов
      cacheService.delete('/tutor/students/');
      
      // Помечаем кеш как устаревший
      qc.invalidateQueries({ 
        queryKey: ['tutor-students']
      });
      
      qc.invalidateQueries({ 
        queryKey: ['tutor-student', studentId]
      });
      
      // Принудительно перезагружаем данные
      await qc.refetchQueries({ 
        queryKey: ['tutor-students'],
        type: 'active'
      });
      
      logger.debug('[useAssignSubject] Cache invalidated and data refreshed');
      
      toast({
        title: "Успешно",
        description: "Предмет успешно назначен ученику",
      });
    },
    onError: (error: any) => {
      const errorMessage = error?.message || error?.response?.data?.detail || 'Не удалось назначить предмет';
      logger.error('[useAssignSubject] Error:', errorMessage);
      toast({
        title: "Ошибка",
        description: errorMessage,
        variant: "destructive",
      });
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
