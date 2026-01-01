import React, { useMemo, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card } from '@/components/ui/card';
import { Calendar } from 'lucide-react';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { lessonSchema, lessonUpdateSchema, type LessonFormData, type LessonUpdateFormData } from '@/schemas/lesson';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { format } from 'date-fns';
import { Lesson } from '@/types/scheduling';

interface Teacher {
  id: string;
  name: string;
}

interface Subject {
  id: string;
  name: string;
}

interface Student {
  id: string;
  name: string;
  full_name?: string;
  subjects?: Array<{
    id: string;
    name: string;
  }>;
}

interface LessonFormProps {
  onSubmit: (data: LessonFormData | LessonUpdateFormData) => Promise<void>;
  onSuccess?: () => void; // Callback after successful submission
  isLoading?: boolean;
  initialData?: Partial<Lesson>;
  students: Student[];
  subjects: Subject[];
  onStudentSelect?: (studentId: string) => void;
  isEditMode?: boolean; // NEW: determines which schema to use
}

export const LessonForm: React.FC<LessonFormProps> = ({
  onSubmit,
  onSuccess,
  isLoading = false,
  initialData,
  students,
  subjects,
  onStudentSelect,
  isEditMode = false, // Default to create mode
}) => {
  // Use different schema based on mode
  const schema = isEditMode ? lessonUpdateSchema : lessonSchema;

  // Extract ID from student/subject - handle both string IDs and objects with id property
  const extractId = (value: any): string => {
    if (typeof value === 'object' && value?.id) {
      return String(value.id);
    }
    return String(value || '');
  };

  const form = useForm<LessonFormData | LessonUpdateFormData>({
    resolver: zodResolver(schema),
    defaultValues: initialData
      ? isEditMode
        ? {
            // Edit mode: NO student and subject in form data
            date: initialData.date || '',
            start_time: initialData.start_time || '09:00',
            end_time: initialData.end_time || '10:00',
            description: initialData.description || '',
            telemost_link: initialData.telemost_link || '',
          }
        : {
            // Create mode: include student and subject
            student: extractId(initialData.student),
            subject: extractId(initialData.subject),
            date: initialData.date || '',
            start_time: initialData.start_time || '09:00',
            end_time: initialData.end_time || '10:00',
            description: initialData.description || '',
            telemost_link: initialData.telemost_link || '',
          }
      : {
          // New lesson: include student and subject
          student: '',
          subject: '',
          date: '',
          start_time: '09:00',
          end_time: '10:00',
          description: '',
          telemost_link: '',
        },
  });

  // Получаем ID выбранного студента с проверкой на undefined
  const selectedStudentId = !isEditMode
    ? form.watch('student' as any)
    : (initialData?.student ? extractId(initialData.student) : '');

  // Reset form when initialData changes (for edit mode)
  useEffect(() => {
    if (initialData) {
      form.reset(
        isEditMode
          ? {
              // Edit mode: NO student and subject
              date: initialData.date || '',
              start_time: initialData.start_time || '09:00',
              end_time: initialData.end_time || '10:00',
              description: initialData.description || '',
              telemost_link: initialData.telemost_link || '',
            }
          : {
              // Create mode: include student and subject
              student: extractId(initialData.student),
              subject: extractId(initialData.subject),
              date: initialData.date || '',
              start_time: initialData.start_time || '09:00',
              end_time: initialData.end_time || '10:00',
              description: initialData.description || '',
              telemost_link: initialData.telemost_link || '',
            }
      );
    }
  }, [initialData, isEditMode, form]);

  // Get subjects for selected student - fallback when no student selected
  const studentSubjects = useMemo(() => {
    // Если студент не выбран или не найден, возвращаем все предметы
    if (!selectedStudentId) return subjects;

    const student = students.find((s) => s.id === selectedStudentId);
    if (!student) return subjects;

    // Возвращаем предметы студента или все предметы, если у студента их нет
    return student.subjects && student.subjects.length > 0 ? student.subjects : subjects;
  }, [selectedStudentId, students, subjects]);

  const handleSubmit = async (data: LessonFormData | LessonUpdateFormData) => {
    // Валидация: проверяем, что студент выбран (только для режима создания)
    if (!isEditMode && !data.student) {
      form.setError('student' as any, {
        type: 'manual',
        message: 'Please select a student',
      });
      return;
    }

    try {
      await onSubmit(data);
      // Сбрасываем форму после успешного создания
      if (!isEditMode) {
        form.reset();
      }
      // Вызываем callback после успешного сабмита
      onSuccess?.();
    } catch (error) {
      // Error is handled by the caller
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Student display/selector */}
          {isEditMode ? (
            // Edit mode: readonly text display
            <div className="space-y-2">
              <FormLabel>Student</FormLabel>
              <div className="flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-sm">
                {(() => {
                  const studentId = extractId(initialData?.student);
                  const student = students.find((s) => s.id === studentId);
                  return student?.full_name || student?.name || 'Unknown';
                })()}
              </div>
              <FormDescription className="text-xs text-muted-foreground">
                Student cannot be changed when editing
              </FormDescription>
            </div>
          ) : (
            // Create mode: editable select
            <FormField
              control={form.control}
              name="student"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Student</FormLabel>
                  <Select
                    value={field.value}
                    onValueChange={(value) => {
                      field.onChange(value);
                      onStudentSelect?.(value);
                      // Reset subject when student changes
                      form.setValue('subject' as any, '');
                    }}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a student" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {students.map((student) => (
                        <SelectItem key={student.id} value={String(student.id)}>
                          {student.full_name || student.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          )}

          {/* Subject display/selector */}
          {isEditMode ? (
            // Edit mode: readonly text display
            <div className="space-y-2">
              <FormLabel>Subject</FormLabel>
              <div className="flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-sm">
                {(() => {
                  const subjectId = extractId(initialData?.subject);
                  const subject = subjects.find((s) => s.id === subjectId);
                  return subject?.name || 'Unknown';
                })()}
              </div>
              <FormDescription className="text-xs text-muted-foreground">
                Subject cannot be changed when editing
              </FormDescription>
            </div>
          ) : (
            // Create mode: editable select
            <FormField
              control={form.control}
              name="subject"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Subject</FormLabel>
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a subject" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {studentSubjects.map((subject) => (
                        <SelectItem key={subject.id} value={String(subject.id)}>
                          {subject.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          )}
        </div>

        {/* Date picker */}
        <FormField
          control={form.control}
          name="date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Date</FormLabel>
              <Popover>
                <PopoverTrigger asChild>
                  <Button type="button"
                    variant="outline"
                    className="w-full justify-start text-left font-normal"
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    {field.value
                      ? format(new Date(field.value), 'MMM dd, yyyy')
                      : 'Pick a date'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <CalendarComponent
                    mode="single"
                    selected={field.value ? new Date(field.value) : undefined}
                    onSelect={(date) => {
                      if (date) {
                        // Используем date-fns для корректного форматирования без смещения timezone
                        field.onChange(format(date, 'yyyy-MM-dd'));
                      }
                    }}
                    disabled={(date) => {
                      const today = new Date();
                      today.setHours(0, 0, 0, 0);
                      return date < today;
                    }}
                  />
                </PopoverContent>
              </Popover>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Time fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField
            control={form.control}
            name="start_time"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Start Time</FormLabel>
                <FormControl>
                  <Input
                    type="time"
                    value={field.value || ''}
                    onChange={field.onChange}
                    onBlur={field.onBlur}
                    name={field.name}
                    ref={field.ref}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="end_time"
            render={({ field }) => (
              <FormItem>
                <FormLabel>End Time</FormLabel>
                <FormControl>
                  <Input
                    type="time"
                    value={field.value || ''}
                    onChange={field.onChange}
                    onBlur={field.onBlur}
                    name={field.name}
                    ref={field.ref}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Description */}
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Lesson topic, materials to prepare, etc."
                  className="resize-none"
                  rows={3}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Telemost link */}
        <FormField
          control={form.control}
          name="telemost_link"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Telemost Link</FormLabel>
              <FormControl>
                <Input
                  placeholder="https://telemost.yandex.ru/j/..."
                  type="url"
                  {...field}
                />
              </FormControl>
              <FormDescription>Optional - link to online lesson</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading
            ? (initialData ? 'Saving...' : 'Creating...')
            : (initialData ? 'Update Lesson' : 'Create Lesson')
          }
        </Button>
      </form>
    </Form>
  );
};
