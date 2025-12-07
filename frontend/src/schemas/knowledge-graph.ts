import { z } from 'zod';

// Element form schema
export const elementSchema = z.object({
  type: z.enum(['text_problem', 'quick_question', 'theory', 'video'], {
    required_error: 'Element type is required',
  }),
  title: z
    .string()
    .min(3, 'Title must be at least 3 characters')
    .max(200, 'Title must not exceed 200 characters'),
  description: z
    .string()
    .max(1000, 'Description must not exceed 1000 characters')
    .optional()
    .default(''),
  content: z.string().min(1, 'Content is required').max(10000, 'Content must not exceed 10000 characters'),
  options: z
    .array(
      z.object({
        text: z.string().min(1, 'Option text is required'),
        is_correct: z.boolean().default(false),
      })
    )
    .optional(),
  video_url: z
    .string()
    .url('Invalid URL format')
    .optional()
    .or(z.literal('')),
  video_type: z.enum(['youtube', 'vimeo', 'other']).optional(),
}).superRefine((data, ctx) => {
  // Validate quick_question has at least 2 options with at least 1 correct
  if (data.type === 'quick_question') {
    if (!data.options || data.options.length < 2) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Quick question must have at least 2 options',
        path: ['options'],
      });
    }
    if (data.options && !data.options.some(opt => opt.is_correct)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'At least one option must be marked as correct',
        path: ['options'],
      });
    }
    if (data.options && data.options.length > 10) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Maximum 10 options allowed',
        path: ['options'],
      });
    }
  }

  // Validate video type requires video_url
  if (data.type === 'video' && !data.video_url) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Video URL is required for video elements',
      path: ['video_url'],
    });
  }
});

export type ElementFormData = z.infer<typeof elementSchema>;

// Lesson form schema
export const lessonSchema = z.object({
  title: z
    .string()
    .min(3, 'Title must be at least 3 characters')
    .max(200, 'Title must not exceed 200 characters'),
  description: z
    .string()
    .max(1000, 'Description must not exceed 1000 characters')
    .optional()
    .default(''),
  difficulty: z.enum(['easy', 'medium', 'hard'], {
    required_error: 'Difficulty is required',
  }),
  element_ids: z
    .array(z.string())
    .min(1, 'At least one element is required')
    .max(50, 'Maximum 50 elements allowed'),
});

export type LessonFormData = z.infer<typeof lessonSchema>;
