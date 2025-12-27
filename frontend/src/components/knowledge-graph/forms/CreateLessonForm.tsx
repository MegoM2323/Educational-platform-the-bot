import React, { useState, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form';
import { lessonSchema, type LessonFormData } from '@/schemas/knowledge-graph';
import { Loader2, CheckCircle2, X, Search, Plus, Trash2, GripVertical } from 'lucide-react';
import { toast } from '@/components/ui/use-toast';

interface Element {
  id: string;
  title: string;
  element_type: string;
  description: string;
  difficulty?: number;
  estimated_time_minutes?: number;
}

interface Subject {
  id: number;
  name: string;
}

interface CreateLessonFormProps {
  onSubmit: (data: LessonFormData) => Promise<void>;
  onCancel?: () => void;
  availableElements: Element[];
  availableSubjects: Subject[];
  isLoading?: boolean;
}

export const CreateLessonForm: React.FC<CreateLessonFormProps> = ({
  onSubmit,
  onCancel,
  availableElements,
  availableSubjects,
  isLoading = false,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedElementIds, setSelectedElementIds] = useState<string[]>([]);
  const [subjectFilter, setSubjectFilter] = useState<string>('all');

  const form = useForm<LessonFormData>({
    resolver: zodResolver(lessonSchema),
    defaultValues: {
      title: '',
      description: '',
      subject_id: availableSubjects.length > 0 ? availableSubjects[0].id : 0,
      difficulty: 'medium',
      element_ids: [],
      is_public: false,
    },
  });

  // Filter elements based on search and subject
  const filteredElements = useMemo(() => {
    // Применение фильтра по subject (если элементы имеют поле subject_id)
    // Примечание: в текущей модели Element нет subject, но можно фильтровать по другим критериям
    // Для простоты оставляем subject filter как placeholder для будущего расширения

    if (!searchQuery) return availableElements;

    const query = searchQuery.toLowerCase();
    return availableElements.filter(
      (el) =>
        el.title.toLowerCase().includes(query) ||
        el.description?.toLowerCase().includes(query) ||
        el.element_type.toLowerCase().includes(query)
    );
  }, [searchQuery, availableElements]);

  // Get selected elements in order
  const selectedElements = useMemo(() => {
    return selectedElementIds
      .map((id) => availableElements.find((el) => el.id === id))
      .filter((el): el is Element => el !== undefined);
  }, [selectedElementIds, availableElements]);

  // Calculate total estimated time
  const totalEstimatedTime = useMemo(() => {
    return selectedElements.reduce((total, el) => {
      return total + (el.estimated_time_minutes || 0);
    }, 0);
  }, [selectedElements]);

  const toggleElement = (elementId: string) => {
    setSelectedElementIds((prev) => {
      if (prev.includes(elementId)) {
        return prev.filter((id) => id !== elementId);
      } else {
        return [...prev, elementId];
      }
    });
  };

  const removeElement = (elementId: string) => {
    setSelectedElementIds((prev) => prev.filter((id) => id !== elementId));
  };

  const moveElement = (index: number, direction: 'up' | 'down') => {
    setSelectedElementIds((prev) => {
      const newOrder = [...prev];
      const targetIndex = direction === 'up' ? index - 1 : index + 1;

      if (targetIndex < 0 || targetIndex >= newOrder.length) return prev;

      [newOrder[index], newOrder[targetIndex]] = [newOrder[targetIndex], newOrder[index]];
      return newOrder;
    });
  };

  const handleSubmit = async (data: LessonFormData) => {
    setIsSubmitting(true);
    setSubmitSuccess(false);

    try {
      // Update element_ids from state
      const submitData = {
        ...data,
        element_ids: selectedElementIds,
      };

      await onSubmit(submitData);
      setSubmitSuccess(true);

      toast({
        title: 'Lesson created successfully',
        description: `"${data.title}" has been created with ${selectedElementIds.length} elements.`,
        variant: 'default',
      });

      // Reset form
      form.reset({
        title: '',
        description: '',
        subject_id: availableSubjects.length > 0 ? availableSubjects[0].id : 0,
        difficulty: 'medium',
        element_ids: [],
        is_public: false,
      });
      setSelectedElementIds([]);
      setSearchQuery('');
      setSubjectFilter('all');

      setTimeout(() => {
        setSubmitSuccess(false);
      }, 3000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create lesson';

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
      title: '',
      description: '',
      subject_id: availableSubjects.length > 0 ? availableSubjects[0].id : 0,
      difficulty: 'medium',
      element_ids: [],
      is_public: false,
    });
    setSelectedElementIds([]);
    setSearchQuery('');
    setSubjectFilter('all');
    setSubmitSuccess(false);
  };

  const hasUnsavedChanges = form.formState.isDirty || selectedElementIds.length > 0;

  const getElementTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      text_problem: 'Problem',
      quick_question: 'Question',
      theory: 'Theory',
      video: 'Video',
    };
    return labels[type] || type;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Lesson</CardTitle>
        <CardDescription>
          Build a lesson by selecting elements from your content bank and arranging them in order.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Success message */}
            {submitSuccess && (
              <div className="p-4 bg-green-50 border border-green-200 rounded-md flex items-center gap-2 text-green-800">
                <CheckCircle2 className="h-5 w-5" />
                <span className="font-medium">Lesson created successfully!</span>
              </div>
            )}

            {/* Title */}
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Lesson Title</FormLabel>
                  <FormControl>
                    <Input placeholder="Lesson title (3-200 characters)" {...field} />
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
                      placeholder="Brief description of lesson objectives..."
                      className="resize-none"
                      rows={2}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>What will students learn in this lesson?</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Subject */}
            <FormField
              control={form.control}
              name="subject_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Subject</FormLabel>
                  <Select
                    value={field.value?.toString()}
                    onValueChange={(value) => field.onChange(parseInt(value, 10))}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select subject" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {availableSubjects.map((subject) => (
                        <SelectItem key={subject.id} value={subject.id.toString()}>
                          {subject.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Difficulty */}
            <FormField
              control={form.control}
              name="difficulty"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Difficulty Level</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select difficulty" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="easy">Easy</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="hard">Hard</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Is Public */}
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
                    <FormLabel>
                      Make lesson public
                    </FormLabel>
                    <FormDescription>
                      Allow other teachers to use this lesson in their courses
                    </FormDescription>
                  </div>
                </FormItem>
              )}
            />

            {/* Element selection */}
            <div className="space-y-4 pt-4 border-t">
              <div>
                <h3 className="text-sm font-medium mb-2">Select Elements</h3>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search elements..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>

              <div className="border rounded-md max-h-64 overflow-y-auto">
                {filteredElements.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    {searchQuery ? 'No elements found matching your search' : 'No elements available'}
                  </div>
                ) : (
                  <div className="divide-y">
                    {filteredElements.map((element) => (
                      <div
                        key={element.id}
                        className="p-3 hover:bg-accent/50 cursor-pointer flex items-start gap-3"
                        onClick={() => toggleElement(element.id)}
                      >
                        <Checkbox
                          checked={selectedElementIds.includes(element.id)}
                          onCheckedChange={() => toggleElement(element.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm truncate">{element.title}</span>
                            <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary shrink-0">
                              {getElementTypeLabel(element.element_type)}
                            </span>
                          </div>
                          {element.description && (
                            <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{element.description}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Selected elements preview */}
            {selectedElements.length > 0 && (
              <div className="space-y-3 pt-4 border-t">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">
                    Selected Elements ({selectedElements.length})
                  </h3>
                  <p className="text-xs text-muted-foreground">Use arrows to reorder</p>
                </div>

                {/* Preview statistics */}
                <div className="grid grid-cols-2 gap-3 p-3 bg-muted/50 rounded-md">
                  <div>
                    <p className="text-xs text-muted-foreground">Total Elements</p>
                    <p className="text-lg font-semibold">{selectedElements.length}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Estimated Time</p>
                    <p className="text-lg font-semibold">
                      {totalEstimatedTime} min
                      {totalEstimatedTime >= 60 && (
                        <span className="text-sm font-normal text-muted-foreground ml-1">
                          (~{Math.floor(totalEstimatedTime / 60)}h {totalEstimatedTime % 60}m)
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  {selectedElements.map((element, index) => (
                    <div
                      key={element.id}
                      className="flex items-center gap-2 p-3 border rounded-md bg-card"
                    >
                      <div className="flex flex-col gap-1">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="h-4 w-4 p-0"
                          onClick={() => moveElement(index, 'up')}
                          disabled={index === 0}
                        >
                          ▲
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="h-4 w-4 p-0"
                          onClick={() => moveElement(index, 'down')}
                          disabled={index === selectedElements.length - 1}
                        >
                          ▼
                        </Button>
                      </div>
                      <GripVertical className="h-4 w-4 text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">#{index + 1}</span>
                          <span className="font-medium text-sm truncate">{element.title}</span>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary shrink-0">
                            {getElementTypeLabel(element.element_type)}
                          </span>
                        </div>
                        {element.estimated_time_minutes && (
                          <p className="text-xs text-muted-foreground mt-1">
                            ~{element.estimated_time_minutes} min
                          </p>
                        )}
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => removeElement(element.id)}
                        className="text-destructive hover:text-destructive shrink-0"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>

                {selectedElementIds.length < 1 && (
                  <p className="text-sm text-destructive">At least 1 element is required</p>
                )}
              </div>
            )}

            {/* Form actions */}
            <div className="flex gap-3 pt-4">
              <Button
                type="submit"
                disabled={isSubmitting || isLoading || selectedElementIds.length === 0}
                className="flex-1"
              >
                {isSubmitting || isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Lesson'
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

            {/* Validation messages */}
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
