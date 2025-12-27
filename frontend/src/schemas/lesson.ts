import { z } from 'zod';

export const lessonSchema = z
  .object({
    student: z.string().min(1, 'Student is required'),
    subject: z.string().min(1, 'Subject is required'),
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
