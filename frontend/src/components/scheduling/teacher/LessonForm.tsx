import React, { useMemo } from 'react';
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
import { lessonSchema, type LessonFormData } from '@/schemas/lesson';
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
  onSubmit: (data: LessonFormData) => Promise<void>;
  isLoading?: boolean;
  initialData?: Partial<Lesson>;
  students: Student[];
  subjects: Subject[];
  onStudentSelect?: (studentId: string) => void;
}

export const LessonForm: React.FC<LessonFormProps> = ({
  onSubmit,
  isLoading = false,
  initialData,
  students,
  subjects,
  onStudentSelect,
}) => {
  const form = useForm<LessonFormData>({
    resolver: zodResolver(lessonSchema),
    defaultValues: initialData
      ? {
          student: initialData.student || '',
          subject: initialData.subject || '',
          date: initialData.date || '',
          start_time: initialData.start_time || '09:00',
          end_time: initialData.end_time || '10:00',
          description: initialData.description || '',
          telemost_link: initialData.telemost_link || '',
        }
      : {
          student: '',
          subject: '',
          date: '',
          start_time: '09:00',
          end_time: '10:00',
          description: '',
          telemost_link: '',
        },
  });

  const selectedStudentId = form.watch('student');

  // Get subjects for selected student
  const studentSubjects = useMemo(() => {
    const student = students.find((s) => s.id === selectedStudentId);
    if (!student) return subjects;
    return student.subjects || subjects;
  }, [selectedStudentId, students, subjects]);

  const handleSubmit = async (data: LessonFormData) => {
    try {
      await onSubmit(data);
      if (!initialData) {
        form.reset();
      }
    } catch (error) {
      // Error is handled by the caller
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Student selector */}
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
                    form.setValue('subject', '');
                  }}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a student" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {students.map((student) => (
                      <SelectItem key={student.id} value={student.id}>
                        {student.full_name || student.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Subject selector */}
          <FormField
            control={form.control}
            name="subject"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Subject</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a subject" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {studentSubjects.map((subject) => (
                      <SelectItem key={subject.id} value={subject.id}>
                        {subject.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
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
                  <Input type="time" {...field} />
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
                  <Input type="time" {...field} />
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
          {isLoading ? 'Creating...' : initialData ? 'Update Lesson' : 'Create Lesson'}
        </Button>
      </form>
    </Form>
  );
};
