import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form';
import { elementSchema, type ElementFormData } from '@/schemas/knowledge-graph';
import { ElementTypeFields } from './ElementTypeFields';
import { Loader2, CheckCircle2, X } from 'lucide-react';
import { toast } from '@/components/ui/use-toast';
import { ElementFileUpload } from './ElementFileUpload';

interface CreateElementFormProps {
  onSubmit: (data: ElementFormData) => Promise<void>;
  onCancel?: () => void;
  initialData?: Partial<ElementFormData>;
  isLoading?: boolean;
  createdElementId?: number | null;
}

export const CreateElementForm: React.FC<CreateElementFormProps> = ({
  onSubmit,
  onCancel,
  initialData,
  isLoading = false,
  createdElementId = null,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const form = useForm<ElementFormData>({
    resolver: zodResolver(elementSchema),
    defaultValues: initialData
      ? {
          type: initialData.type || 'text_problem',
          title: initialData.title || '',
          description: initialData.description || '',
          content: initialData.content || '',
          options: initialData.options || [],
          video_url: initialData.video_url || '',
          video_type: initialData.video_type,
          difficulty: initialData.difficulty || 5,
          estimated_time_minutes: initialData.estimated_time_minutes || 5,
          max_score: initialData.max_score || 100,
          tags: initialData.tags || [],
          is_public: initialData.is_public || false,
        }
      : {
          type: 'text_problem',
          title: '',
          description: '',
          content: '',
          options: [],
          video_url: '',
          difficulty: 5,
          estimated_time_minutes: 5,
          max_score: 100,
          tags: [],
          is_public: false,
        },
  });

  const selectedType = form.watch('type');

  const handleSubmit = async (data: ElementFormData) => {
    setIsSubmitting(true);
    setSubmitSuccess(false);

    try {
      await onSubmit(data);
      setSubmitSuccess(true);

      toast({
        title: 'Element created successfully',
        description: `"${data.title}" has been added to the element bank.`,
        variant: 'default',
      });

      // Reset form after successful submission
      form.reset({
        type: 'text_problem',
        title: '',
        description: '',
        content: '',
        options: [],
        video_url: '',
        difficulty: 5,
        estimated_time_minutes: 5,
        max_score: 100,
        tags: [],
        is_public: false,
      });

      // Hide success message after 3 seconds
      setTimeout(() => {
        setSubmitSuccess(false);
      }, 3000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create element';

      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    form.reset({
      type: 'text_problem',
      title: '',
      description: '',
      content: '',
      options: [],
      video_url: '',
      difficulty: 5,
      estimated_time_minutes: 5,
      max_score: 100,
      tags: [],
      is_public: false,
    });
    setSubmitSuccess(false);
  };

  const hasUnsavedChanges = form.formState.isDirty;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Element</CardTitle>
        <CardDescription>
          Add a new educational element to your content bank. Choose the type and fill in the details.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Success message */}
            {submitSuccess && (
              <div className="p-4 bg-green-50 border border-green-200 rounded-md flex items-center gap-2 text-green-800">
                <CheckCircle2 className="h-5 w-5" />
                <span className="font-medium">Element created successfully!</span>
              </div>
            )}

            {/* Element Type */}
            <FormField
              control={form.control}
              name="type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Element Type</FormLabel>
                  <Select
                    value={field.value}
                    onValueChange={(value) => {
                      field.onChange(value);
                      // Reset content and type-specific fields when type changes
                      form.setValue('content', '');
                      form.setValue('options', []);
                      form.setValue('video_url', '');
                    }}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select element type" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="text_problem">Text Problem</SelectItem>
                      <SelectItem value="quick_question">Quick Question</SelectItem>
                      <SelectItem value="theory">Theory</SelectItem>
                      <SelectItem value="video">Video</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    {selectedType === 'text_problem' && 'A problem requiring written solution'}
                    {selectedType === 'quick_question' && 'Multiple choice question with instant feedback'}
                    {selectedType === 'theory' && 'Theoretical material and explanations'}
                    {selectedType === 'video' && 'Video lecture or demonstration'}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Title */}
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input placeholder="Element title (3-200 characters)" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Description */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (Optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Brief description of this element..."
                      className="resize-none"
                      rows={2}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>Optional - helps organize your element bank</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Параметры элемента */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Difficulty */}
              <FormField
                control={form.control}
                name="difficulty"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Сложность (1-10)</FormLabel>
                    <Select
                      value={field.value?.toString()}
                      onValueChange={(value) => field.onChange(parseInt(value))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Выберите сложность" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((level) => (
                          <SelectItem key={level} value={level.toString()}>
                            {level === 1 && '1 - Очень легко'}
                            {level === 2 && '2 - Легко'}
                            {level === 3 && '3'}
                            {level === 4 && '4'}
                            {level === 5 && '5 - Средне'}
                            {level === 6 && '6'}
                            {level === 7 && '7'}
                            {level === 8 && '8 - Сложно'}
                            {level === 9 && '9'}
                            {level === 10 && '10 - Очень сложно'}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Estimated Time */}
              <FormField
                control={form.control}
                name="estimated_time_minutes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Время (минут)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        placeholder="5"
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Max Score */}
              <FormField
                control={form.control}
                name="max_score"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Максимальный балл</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        placeholder="100"
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value) || 0)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Публичность */}
            <FormField
              control={form.control}
              name="is_public"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel>Опубликовать элемент</FormLabel>
                    <FormDescription>
                      Сделать элемент доступным для других учителей
                    </FormDescription>
                  </div>
                </FormItem>
              )}
            />

            {/* Type-specific fields */}
            <div className="pt-4 border-t">
              <ElementTypeFields form={form} elementType={selectedType} />
            </div>

            {/* Form actions */}
            <div className="flex gap-3 pt-4">
              <Button
                type="submit"
                disabled={isSubmitting || isLoading}
                className="flex-1"
              >
                {isSubmitting || isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Element'
                )}
              </Button>

              {hasUnsavedChanges && (
                <Button type="button" onClick={handleReset} variant="outline">
                  <X className="h-4 w-4 mr-2" />
                  Clear
                </Button>
              )}

              {onCancel && (
                <Button type="button" onClick={onCancel} variant="ghost">
                  Cancel
                </Button>
              )}
            </div>

            {/* Unsaved changes warning */}
            {hasUnsavedChanges && !isSubmitting && (
              <p className="text-sm text-muted-foreground text-center">
                You have unsaved changes
              </p>
            )}
          </form>
        </Form>

        {/* File Upload Section - показываем после создания элемента */}
        {createdElementId && (
          <div className="mt-6 pt-6 border-t">
            <h3 className="text-lg font-semibold mb-4">Файлы элемента</h3>
            <ElementFileUpload
              elementId={createdElementId}
              disabled={isLoading || isSubmitting}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
};
