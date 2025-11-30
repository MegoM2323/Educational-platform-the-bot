export interface Lesson {
  id: string;
  teacher: string; // UUID
  student: string; // UUID
  subject: string; // UUID
  date: string; // ISO date
  start_time: string; // HH:MM:SS
  end_time: string; // HH:MM:SS
  description: string;
  telemost_link: string;
  status: 'pending' | 'confirmed' | 'completed' | 'cancelled';
  created_at: string;
  updated_at: string;
  // Computed fields from API
  teacher_name?: string;
  student_name?: string;
  subject_name?: string;
  is_upcoming?: boolean;
  can_cancel?: boolean;
  datetime_start?: string; // ISO datetime for countdown
  datetime_end?: string; // ISO datetime
}

export interface LessonCreatePayload {
  student: string;
  subject: string;
  date: string;
  start_time: string;
  end_time: string;
  description?: string;
  telemost_link?: string;
}

export interface LessonUpdatePayload {
  description?: string;
  telemost_link?: string;
  start_time?: string;
  end_time?: string;
  date?: string;
}

export interface LessonFilters {
  date_from?: string;
  date_to?: string;
  subject?: string;
  teacher?: string;
  status?: string;
}
