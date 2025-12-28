import { z } from 'zod';

// Preprocess function to convert number/string to string
const toStringPreprocess = (val: unknown) => {
  if (val === null || val === undefined || val === '') return '';
  return String(val);
};

// Base fields shared by both create and update schemas
const baseLessonFields = {
  date: z.string().min(1, 'Date is required'),
  start_time: z.string().min(1, 'Start time is required'),
  end_time: z.string().min(1, 'End time is required'),
  description: z.string().optional().default(''),
  telemost_link: z
    .string()
    .optional()
    .default('')
    .refine(
      (val) => !val || /^https?:\/\/.+/.test(val),
      'Invalid URL format'
    ),
};

// Schema for CREATING lesson (includes student and subject)
export const lessonSchema = z
  .object({
    // Accept both string and number for student (UUID from backend)
    student: z.preprocess(toStringPreprocess, z.string().min(1, 'Student is required')),
    // Accept both string and number for subject (Integer ID from backend)
    subject: z.preprocess(toStringPreprocess, z.string().min(1, 'Subject is required')),
    ...baseLessonFields,
  })
  .refine(
    (data) => {
      if (!data.start_time || !data.end_time) return true;
      return data.start_time < data.end_time;
    },
    {
      message: 'Start time must be before end time',
      path: ['end_time'],
    }
  )
  .refine(
    (data) => {
      if (!data.date) return true;
      const selectedDate = new Date(data.date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return selectedDate >= today;
    },
    {
      message: 'Date cannot be in the past',
      path: ['date'],
    }
  );

// Schema for UPDATING lesson (NO student and subject - they are read-only)
// Student and subject fields will be disabled in the form, not validated
export const lessonUpdateSchema = z
  .object({
    // Student and subject - completely bypass validation (disabled in form)
    student: z.any().optional(),
    subject: z.any().optional(),
    ...baseLessonFields,
  })
  .refine(
    (data) => {
      if (!data.start_time || !data.end_time) return true;
      return data.start_time < data.end_time;
    },
    {
      message: 'Start time must be before end time',
      path: ['end_time'],
    }
  )
  .refine(
    (data) => {
      if (!data.date) return true;
      const selectedDate = new Date(data.date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return selectedDate >= today;
    },
    {
      message: 'Date cannot be in the past',
      path: ['date'],
    }
  );

export type LessonFormData = z.infer<typeof lessonSchema>;
export type LessonUpdateFormData = z.infer<typeof lessonUpdateSchema>;
