import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { teacherProfileSchema, type TeacherProfile } from '@/types/profileSchemas';

interface TeacherProfileFormProps {
  initialData?: Partial<TeacherProfile>;
  onSubmit: (data: TeacherProfile) => Promise<void>;
  isLoading?: boolean;
  autoSave?: boolean;
  onAutoSave?: (data: Partial<TeacherProfile>) => Promise<void>;
}

export const TeacherProfileForm = ({
  initialData,
  onSubmit,
  isLoading = false,
  autoSave = false,
  onAutoSave,
}: TeacherProfileFormProps) => {
  const [hasChanges, setHasChanges] = useState(false);
  const [isAutoSaving, setIsAutoSaving] = useState(false);

  const form = useForm<TeacherProfile>({
    resolver: zodResolver(teacherProfileSchema),
    mode: 'onBlur',
    defaultValues: {
      first_name: initialData?.first_name || '',
      last_name: initialData?.last_name || '',
      phone: initialData?.phone || '',
      bio: initialData?.bio || '',
      subject: initialData?.subject || '',
      experience_years: initialData?.experience_years || undefined,
      telegram: initialData?.telegram || '',
    },
  });

  useEffect(() => {
    if (!autoSave || !onAutoSave) return;

    const subscription = form.watch(() => {
      setHasChanges(true);
    });

    return () => subscription.unsubscribe();
  }, [form, autoSave, onAutoSave]);

  const handleSubmit = async (data: TeacherProfile) => {
    try {
      await onSubmit(data);
      setHasChanges(false);
      toast.success('Профиль успешно сохранен');
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Ошибка при сохранении профиля';
      toast.error(message);
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Профиль учителя</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="first_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel htmlFor="first_name">Имя</FormLabel>
                    <FormControl>
                      <Input
                        id="first_name"
                        placeholder="Ваше имя"
                        {...field}
                        aria-label="Имя учителя"
                        disabled={isLoading}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="last_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel htmlFor="last_name">Фамилия</FormLabel>
                    <FormControl>
                      <Input
                        id="last_name"
                        placeholder="Ваша фамилия"
                        {...field}
                        aria-label="Фамилия учителя"
                        disabled={isLoading}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="phone"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor="phone">Телефон</FormLabel>
                  <FormControl>
                    <Input
                      id="phone"
                      placeholder="+7 (XXX) XXX-XX-XX"
                      type="tel"
                      {...field}
                      aria-label="Номер телефона"
                      aria-describedby="phone-hint"
                      disabled={isLoading}
                    />
                  </FormControl>
                  <p id="phone-hint" className="text-xs text-gray-500">
                    Формат: +7 (XXX) XXX-XX-XX или подобный
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="bio"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor="bio">Биография</FormLabel>
                  <FormControl>
                    <Textarea
                      id="bio"
                      placeholder="Расскажите о себе..."
                      {...field}
                      aria-label="Биография учителя"
                      disabled={isLoading}
                      className="resize-none"
                      rows={4}
                    />
                  </FormControl>
                  <p className="text-xs text-gray-500">
                    Максимум 1000 символов
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="subject"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor="subject">Предмет</FormLabel>
                  <FormControl>
                    <Input
                      id="subject"
                      placeholder="Ваш предмет"
                      {...field}
                      aria-label="Предмет учителя"
                      disabled={isLoading}
                    />
                  </FormControl>
                  <p className="text-xs text-gray-500">
                    Максимум 100 символов
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="experience_years"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor="experience_years">
                    Опыт работы (лет)
                  </FormLabel>
                  <FormControl>
                    <Input
                      id="experience_years"
                      placeholder="0"
                      type="number"
                      min="0"
                      max="80"
                      {...field}
                      value={field.value || ''}
                      onChange={(e) => {
                        const value = e.target.value
                          ? parseInt(e.target.value)
                          : undefined;
                        field.onChange(value);
                      }}
                      aria-label="Опыт работы учителя"
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="telegram"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor="telegram">Telegram</FormLabel>
                  <FormControl>
                    <Input
                      id="telegram"
                      placeholder="@username или username"
                      {...field}
                      aria-label="Telegram учителя"
                      aria-describedby="telegram-hint"
                      disabled={isLoading}
                    />
                  </FormControl>
                  <p id="telegram-hint" className="text-xs text-gray-500">
                    Без пробелов, 5-32 символа (букв, цифр, подчеркивание)
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex gap-2 pt-4">
              <Button type="submit"
                disabled={isLoading || isAutoSaving}
                aria-label="Сохранить профиль"
              >
                {isLoading || isAutoSaving
                  ? 'Сохранение...'
                  : 'Сохранить профиль'}
              </Button>

              {hasChanges && autoSave && (
                <div className="text-sm text-orange-600 flex items-center">
                  <span className="inline-block w-2 h-2 bg-orange-600 rounded-full mr-2" />
                  Есть несохраненные изменения
                </div>
              )}
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
};

export default TeacherProfileForm;
