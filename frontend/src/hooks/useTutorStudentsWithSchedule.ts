import { useQuery } from '@tanstack/react-query';
import { logger } from '@/utils/logger';
import { tutorAPI, TutorStudent } from '@/integrations/api/tutor';

/**
 * Hook для получения студентов тьютора с информацией о расписании
 * Объединяет данные из двух источников:
 * 1. /api/tutor/my-students/ - базовая информация о студентах (grade, goal, subjects)
 * 2. /api/scheduling/tutor/schedule/ - расписание (next_lesson, lessons_count)
 */
export const useTutorStudentsWithSchedule = () => {
  return useQuery<TutorStudent[]>({
    queryKey: ['tutor-students-with-schedule'],
    queryFn: async () => {
      logger.debug('[useTutorStudentsWithSchedule] Fetching students and schedule...');

      // Получаем базовую информацию о студентах
      const basicStudents = await tutorAPI.listStudents();
      logger.debug('[useTutorStudentsWithSchedule] Basic students:', basicStudents.length);

      // Получаем расписание студентов
      const scheduleStudents = await tutorAPI.getStudentsSchedule();
      logger.debug('[useTutorStudentsWithSchedule] Schedule students:', scheduleStudents.length);

      // Создаем Map для быстрого поиска расписания по ID студента
      const scheduleMap = new Map<number, TutorStudent>();
      scheduleStudents.forEach(s => {
        scheduleMap.set(s.id, s);
      });

      // Объединяем данные: базовая информация + расписание
      const mergedStudents = basicStudents.map(student => {
        const scheduleData = scheduleMap.get(student.id);
        return {
          ...student,
          next_lesson: scheduleData?.next_lesson || null,
          lessons_count: scheduleData?.lessons_count || 0,
        };
      });

      logger.debug('[useTutorStudentsWithSchedule] Merged students:', mergedStudents.length);
      return mergedStudents;
    },
    staleTime: 30000, // 30 секунд
    gcTime: 60000, // 1 минута
    retry: 2,
    refetchOnWindowFocus: true,
    refetchOnMount: true,
  });
};
