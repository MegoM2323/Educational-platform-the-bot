import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
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

interface CreateElementFormProps {
  onSubmit: (data: ElementFormData) => Promise<void>;
  onCancel?: () => void;
  initialData?: Partial<ElementFormData>;
  isLoading?: boolean;
}

export const CreateElementForm: React.FC<CreateElementFormProps> = ({
  onSubmit,
  onCancel,
  initialData,
  isLoading = false,
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
        }
      : {
          type: 'text_problem',
          title: '',
          description: '',
          content: '',
          options: [],
          video_url: '',
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
      </CardContent>
    </Card>
  );
};
