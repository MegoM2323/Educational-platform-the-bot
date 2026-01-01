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
import { tutorProfileSchema, type TutorProfile } from '@/types/profileSchemas';

interface TutorProfileFormProps {
  initialData?: Partial<TutorProfile>;
  onSubmit: (data: TutorProfile) => Promise<void>;
  isLoading?: boolean;
  autoSave?: boolean;
  onAutoSave?: (data: Partial<TutorProfile>) => Promise<void>;
}

export const TutorProfileForm = ({
  initialData,
  onSubmit,
  isLoading = false,
  autoSave = false,
  onAutoSave,
}: TutorProfileFormProps) => {
  const [hasChanges, setHasChanges] = useState(false);
  const [isAutoSaving, setIsAutoSaving] = useState(false);

  const form = useForm<TutorProfile>({
    resolver: zodResolver(tutorProfileSchema),
    mode: 'onBlur',
    defaultValues: {
      first_name: initialData?.first_name || '',
      last_name: initialData?.last_name || '',
      phone: initialData?.phone || '',
      bio: initialData?.bio || '',
      specialization: initialData?.specialization || '',
      experience_years: initialData?.experience_years || undefined,
    },
  });

  useEffect(() => {
    if (!autoSave || !onAutoSave) return;

    const subscription = form.watch(() => {
      setHasChanges(true);
    });

    return () => subscription.unsubscribe();
  }, [form, autoSave, onAutoSave]);

  const handleSubmit = async (data: TutorProfile) => {
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
        <CardTitle>Профиль репетитора</CardTitle>
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
                        aria-label="Имя репетитора"
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
                        aria-label="Фамилия репетитора"
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
                      aria-label="Биография репетитора"
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
              name="specialization"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor="specialization">Специализация</FormLabel>
                  <FormControl>
                    <Input
                      id="specialization"
                      placeholder="Ваша специализация"
                      {...field}
                      aria-label="Специализация репетитора"
                      disabled={isLoading}
                    />
                  </FormControl>
                  <p className="text-xs text-gray-500">
                    Максимум 200 символов
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
                      aria-label="Опыт работы репетитора"
                      disabled={isLoading}
                    />
                  </FormControl>
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

export default TutorProfileForm;
