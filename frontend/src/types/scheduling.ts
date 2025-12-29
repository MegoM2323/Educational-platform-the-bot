/**
 * Lesson entity представляет урок в системе расписания.
 *
 * Основные поля (teacher, student, subject) - это UUID ссылки на связанные сущности.
 * Дополнительные поля (teacher_id, subject_id) - также UUID для совместимости с API.
 * Опциональные поля (teacher_name, student_name, subject_name) - для отображения в UI.
 * Computed поля - рассчитываются на бэкенде и всегда присутствуют в ответах API.
 */
export interface Lesson {
  id: string;

  // Основные UUID ссылки на связанные сущности
  teacher: string;
  student: string;
  subject: string;

  // Дополнительные UUID поля для совместимости с API
  teacher_id: string;
  subject_id: string;

  // Временные параметры урока
  date: string; // ISO date (YYYY-MM-DD)
  start_time: string; // HH:MM:SS
  end_time: string; // HH:MM:SS

  // Дополнительная информация
  description: string;
  telemost_link: string;
  status: 'pending' | 'confirmed' | 'completed' | 'cancelled';

  // Метаданные
  created_at: string;
  updated_at: string;

  // Computed поля - рассчитываются бэкендом и всегда присутствуют
  is_upcoming: boolean;
  can_cancel: boolean;
  datetime_start: string; // ISO datetime для countdown
  datetime_end: string; // ISO datetime

  // Опциональные поля для отображения (не всегда возвращаются API)
  teacher_name?: string;
  student_name?: string;
  subject_name?: string;
}

/**
 * Payload для создания нового урока.
 * teacher берется из текущего пользователя автоматически на бэкенде.
 */
export interface LessonCreatePayload {
  student: string; // UUID студента
  subject: string; // UUID предмета
  date: string; // ISO date (YYYY-MM-DD)
  start_time: string; // HH:MM:SS
  end_time: string; // HH:MM:SS
  description?: string;
  telemost_link?: string;
}

/**
 * Payload для обновления существующего урока.
 * Все поля опциональны - обновляются только переданные.
 */
export interface LessonUpdatePayload {
  date?: string; // ISO date (YYYY-MM-DD)
  start_time?: string; // HH:MM:SS
  end_time?: string; // HH:MM:SS
  description?: string;
  telemost_link?: string;
  status?: 'pending' | 'confirmed' | 'completed' | 'cancelled';
}

/**
 * Фильтры для получения списка уроков.
 * Используются в query параметрах API запросов.
 */
export interface LessonFilters {
  date_from?: string; // ISO date (YYYY-MM-DD)
  date_to?: string; // ISO date (YYYY-MM-DD)
  subject?: string; // UUID предмета
  teacher?: string; // UUID преподавателя
  status?: string; // 'pending' | 'confirmed' | 'completed' | 'cancelled'
}

/**
 * AdminLesson - расширенная версия Lesson для админского интерфейса.
 * Всегда включает имена связанных сущностей для отображения.
 */
export interface AdminLesson extends Lesson {
  teacher_name: string;
  student_name: string;
  subject_name: string;
}

/**
 * Ответ API для получения расписания конкретного ребенка родителем.
 * Используется в ParentDashboard для отображения уроков одного студента.
 */
export interface ParentChildScheduleResponse {
  student: {
    id: string;
    name: string;
    email: string;
  };
  lessons: Lesson[];
  total_lessons: number;
}

/**
 * Ответ API для получения расписания всех детей родителя.
 * Используется в ParentDashboard для отображения уроков всех студентов сразу.
 */
export interface ParentAllSchedulesResponse {
  children: Array<{
    id: string;
    name: string;
    lessons: Lesson[];
  }>;
  total_children: number;
}
