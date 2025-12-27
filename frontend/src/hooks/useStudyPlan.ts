import { useMutation, useQuery } from '@tanstack/react-query';
import { studyPlanAPI, StudyPlanParams, GenerationResponse } from '@/integrations/api/studyPlanAPI';

/**
 * Hook для генерации учебного плана
 */
export const useGenerateStudyPlan = () => {
  return useMutation<GenerationResponse, Error, StudyPlanParams>({
    mutationFn: (params: StudyPlanParams) => studyPlanAPI.generateStudyPlan(params),
  });
};

/**
 * Hook для получения статуса генерации
 * @param generationId - ID генерации
 * @param enabled - Включить автоматический запрос
 */
export const useGenerationStatus = (generationId: number | null, enabled: boolean = false) => {
  return useQuery({
    queryKey: ['study-plan-generation', generationId],
    queryFn: () => studyPlanAPI.getGenerationStatus(generationId!),
    enabled: enabled && generationId !== null,
    refetchInterval: (data) => {
      // Продолжаем polling если статус pending или processing
      if (data?.status === 'pending' || data?.status === 'processing') {
        return 3000; // Каждые 3 секунды
      }
      return false; // Остановить polling если completed или failed
    },
    refetchOnWindowFocus: false,
    staleTime: 0, // Всегда считать данные stale для корректного polling
  });
};

/**
 * Hook для получения списка всех генераций
 */
export const useStudyPlanGenerations = () => {
  return useQuery({
    queryKey: ['study-plan-generations'],
    queryFn: () => studyPlanAPI.listGenerations(),
    staleTime: 60000, // 1 минута
    refetchOnWindowFocus: true,
  });
};
