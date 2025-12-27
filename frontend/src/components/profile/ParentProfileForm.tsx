import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import { parentProfileSchema, type ParentProfile } from '@/types/profileSchemas';

interface ParentProfileFormProps {
  initialData?: Partial<ParentProfile>;
  onSubmit: (data: ParentProfile) => Promise<void>;
  isLoading?: boolean;
  autoSave?: boolean;
  onAutoSave?: (data: Partial<ParentProfile>) => Promise<void>;
}

export const ParentProfileForm = ({
  initialData,
  onSubmit,
  isLoading = false,
  autoSave = false,
  onAutoSave,
}: ParentProfileFormProps) => {
  const [hasChanges, setHasChanges] = useState(false);
  const [isAutoSaving, setIsAutoSaving] = useState(false);

  const form = useForm<ParentProfile>({
    resolver: zodResolver(parentProfileSchema),
    mode: 'onBlur',
    defaultValues: {
      first_name: initialData?.first_name || '',
      last_name: initialData?.last_name || '',
      phone: initialData?.phone || '',
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

  const handleSubmit = async (data: ParentProfile) => {
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
        <CardTitle>Профиль родителя</CardTitle>
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
                        aria-label="Имя родителя"
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
                        aria-label="Фамилия родителя"
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
              name="telegram"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor="telegram">Telegram</FormLabel>
                  <FormControl>
                    <Input
                      id="telegram"
                      placeholder="@username или username"
                      {...field}
                      aria-label="Telegram родителя"
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

export default ParentProfileForm;
