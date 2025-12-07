import React from 'react';
import { UseFormReturn } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FormControl, FormField, FormItem, FormLabel, FormMessage, FormDescription } from '@/components/ui/form';
import { ElementFormData } from '@/schemas/knowledge-graph';
import { Plus, Trash2, CheckCircle2 } from 'lucide-react';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';

interface ElementTypeFieldsProps {
  form: UseFormReturn<ElementFormData>;
  elementType: 'text_problem' | 'quick_question' | 'theory' | 'video';
}

export const ElementTypeFields: React.FC<ElementTypeFieldsProps> = ({ form, elementType }) => {
  const options = form.watch('options') || [];

  const addOption = () => {
    const currentOptions = form.getValues('options') || [];
    form.setValue('options', [...currentOptions, { text: '', is_correct: false }]);
  };

  const removeOption = (index: number) => {
    const currentOptions = form.getValues('options') || [];
    form.setValue(
      'options',
      currentOptions.filter((_, i) => i !== index)
    );
  };

  const setCorrectOption = (index: number) => {
    const currentOptions = form.getValues('options') || [];
    form.setValue(
      'options',
      currentOptions.map((opt, i) => ({
        ...opt,
        is_correct: i === index,
      }))
    );
  };

  // Text problem - simple textarea
  if (elementType === 'text_problem') {
    return (
      <FormField
        control={form.control}
        name="content"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Problem Content</FormLabel>
            <FormControl>
              <Textarea
                placeholder="Enter the problem text, conditions, and questions..."
                className="resize-none min-h-[200px]"
                {...field}
              />
            </FormControl>
            <FormDescription>Describe the problem students need to solve</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />
    );
  }

  // Quick question - content + options with correct answer
  if (elementType === 'quick_question') {
    return (
      <div className="space-y-4">
        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Question</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Enter the question..."
                  className="resize-none"
                  rows={3}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <FormLabel>Answer Options</FormLabel>
            <Button type="button" onClick={addOption} size="sm" variant="outline">
              <Plus className="h-4 w-4 mr-1" />
              Add Option
            </Button>
          </div>

          {options.length === 0 && (
            <p className="text-sm text-muted-foreground">No options added yet. Add at least 2 options.</p>
          )}

          <RadioGroup
            value={options.findIndex((opt) => opt.is_correct).toString()}
            onValueChange={(value) => setCorrectOption(parseInt(value))}
          >
            {options.map((option, index) => (
              <div key={index} className="flex items-start gap-2 p-3 border rounded-md bg-card">
                <div className="flex items-center gap-2 pt-2">
                  <RadioGroupItem value={index.toString()} id={`option-${index}`} />
                </div>
                <div className="flex-1 space-y-2">
                  <Input
                    placeholder={`Option ${index + 1}`}
                    value={option.text}
                    onChange={(e) => {
                      const currentOptions = form.getValues('options') || [];
                      const newOptions = [...currentOptions];
                      newOptions[index] = { ...newOptions[index], text: e.target.value };
                      form.setValue('options', newOptions);
                    }}
                  />
                  {option.is_correct && (
                    <p className="text-xs text-green-600 flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Correct answer
                    </p>
                  )}
                </div>
                <Button
                  type="button"
                  onClick={() => removeOption(index)}
                  size="sm"
                  variant="ghost"
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </RadioGroup>
          {form.formState.errors.options && (
            <p className="text-sm font-medium text-destructive">{form.formState.errors.options.message}</p>
          )}
        </div>
      </div>
    );
  }

  // Theory - rich content
  if (elementType === 'theory') {
    return (
      <FormField
        control={form.control}
        name="content"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Theory Content</FormLabel>
            <FormControl>
              <Textarea
                placeholder="Enter theoretical material, explanations, formulas..."
                className="resize-none min-h-[300px] font-mono"
                {...field}
              />
            </FormControl>
            <FormDescription>Provide theoretical background and explanations</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />
    );
  }

  // Video - URL and type
  if (elementType === 'video') {
    return (
      <div className="space-y-4">
        <FormField
          control={form.control}
          name="video_url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Video URL</FormLabel>
              <FormControl>
                <Input placeholder="https://youtube.com/watch?v=..." type="url" {...field} />
              </FormControl>
              <FormDescription>Enter the full URL to the video</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="video_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Video Platform</FormLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select platform" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="youtube">YouTube</SelectItem>
                  <SelectItem value="vimeo">Vimeo</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Video Description</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Brief description of video content..."
                  className="resize-none"
                  rows={3}
                  {...field}
                />
              </FormControl>
              <FormDescription>Optional - what students will learn from this video</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>
    );
  }

  return null;
};
