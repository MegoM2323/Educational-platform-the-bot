import { z } from 'zod';

const phoneRegex = /^[+]?[\d\s\-()]+$/;

export const baseProfileSchema = z.object({
  first_name: z.string().min(1, 'Имя обязательно').max(150, 'Имя не должно превышать 150 символов'),
  last_name: z
    .string()
    .min(1, 'Фамилия обязательна')
    .max(150, 'Фамилия не должна превышать 150 символов'),
  phone: z
    .string()
    .refine((val) => !val || phoneRegex.test(val), 'Некорректный формат телефона')
    .optional()
    .or(z.literal('')),
});

export const studentProfileSchema = baseProfileSchema.extend({
  grade: z
    .string()
    .refine((val) => !val || /^\d{1,2}$/.test(val), 'Класс должен быть числом от 1 до 12')
    .optional()
    .or(z.literal('')),
  goal: z.string().max(1000, 'Цель не должна превышать 1000 символов').optional().or(z.literal('')),
});

export const teacherProfileSchema = baseProfileSchema.extend({
  bio: z
    .string()
    .max(1000, 'Биография не должна превышать 1000 символов')
    .optional()
    .or(z.literal('')),
  subject: z
    .string()
    .max(100, 'Предмет не должен превышать 100 символов')
    .optional()
    .or(z.literal('')),
  experience_years: z
    .number()
    .int('Опыт должен быть целым числом')
    .min(0, 'Опыт не может быть отрицательным')
    .max(80, 'Опыт не может превышать 80 лет')
    .optional(),
});

export const tutorProfileSchema = baseProfileSchema.extend({
  bio: z
    .string()
    .max(1000, 'Биография не должна превышать 1000 символов')
    .optional()
    .or(z.literal('')),
  specialization: z
    .string()
    .max(200, 'Специализация не должна превышать 200 символов')
    .optional()
    .or(z.literal('')),
  experience_years: z
    .number()
    .int('Опыт должен быть целым числом')
    .min(0, 'Опыт не может быть отрицательным')
    .max(80, 'Опыт не может превышать 80 лет')
    .optional(),
});

export const parentProfileSchema = baseProfileSchema.extend({});

export type StudentProfile = z.infer<typeof studentProfileSchema>;
export type TeacherProfile = z.infer<typeof teacherProfileSchema>;
export type TutorProfile = z.infer<typeof tutorProfileSchema>;
export type ParentProfile = z.infer<typeof parentProfileSchema>;
