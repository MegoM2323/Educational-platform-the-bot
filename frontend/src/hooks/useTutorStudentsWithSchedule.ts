import { useQuery } from '@tanstack/react-query';
import { logger } from '@/utils/logger';
import { tutorAPI, TutorStudent } from '@/integrations/api/tutor';

/**
 * Тип для объединенных данных студента с расписанием
 */
export type TutorStudentWithSchedule = TutorStudent & {
  next_lesson: NonNullable<TutorStudent['next_lesson']> | null;
  lessons_count: number;
};

interface UseTutorStudentsWithScheduleFilters {
  refresh?: boolean;
}

/**
 * Hook для получения студентов тьютора с информацией о расписании
 * Объединяет данные из двух источников:
 * 1. /api/tutor/my-students/ - базовая информация о студентах (grade, goal, subjects)
 * 2. /api/scheduling/tutor/schedule/ - расписание (next_lesson, lessons_count)
 */
export const useTutorStudentsWithSchedule = (filters?: UseTutorStudentsWithScheduleFilters) => {
  return useQuery<TutorStudentWithSchedule[]>({
    queryKey: ['tutor', 'students', 'schedule', ...Object.values(filters || {})],
    queryFn: async () => {
      logger.debug('[useTutorStudentsWithSchedule] Fetching students and schedule...');

      try {
        // Получаем базовую информацию о студентах
        const basicStudents = await tutorAPI.listStudents();
        logger.debug('[useTutorStudentsWithSchedule] Basic students:', basicStudents.length);

        // Получаем расписание студентов (может быть undefined пока загружается)
        let scheduleStudents: TutorStudent[] = [];
        try {
          scheduleStudents = await tutorAPI.getStudentsSchedule();
          logger.debug('[useTutorStudentsWithSchedule] Schedule students:', scheduleStudents.length);
        } catch (error) {
          logger.warn('[useTutorStudentsWithSchedule] Failed to fetch schedule, using empty data:', error);
        }

        // Создаем Map для быстрого поиска расписания по ID студента
        const scheduleMap = new Map<number, TutorStudent>();
        if (scheduleStudents && Array.isArray(scheduleStudents)) {
          scheduleStudents.forEach(s => {
            if (s && s.id) {
              scheduleMap.set(s.id, s);
            }
          });
        }

        // Объединяем данные: базовая информация + расписание
        const mergedStudents: TutorStudentWithSchedule[] = basicStudents.map(student => {
          const scheduleData = scheduleMap.get(student.id);

          return {
            ...student,
            // Ensure proper type for next_lesson
            next_lesson: scheduleData?.next_lesson !== undefined ? scheduleData.next_lesson : null,
            // Ensure lessons_count is always a number
            lessons_count: typeof scheduleData?.lessons_count === 'number' ? scheduleData.lessons_count : 0,
          };
        });

        logger.debug('[useTutorStudentsWithSchedule] Merged students:', mergedStudents.length);
        return mergedStudents;
      } catch (error) {
        logger.error('[useTutorStudentsWithSchedule] Error fetching data:', error);
        throw error;
      }
    },
    staleTime: 30000, // 30 секунд
    gcTime: 60000, // 1 минута
    retry: 2,
    refetchOnWindowFocus: true,
    refetchOnMount: true,
  });
};
