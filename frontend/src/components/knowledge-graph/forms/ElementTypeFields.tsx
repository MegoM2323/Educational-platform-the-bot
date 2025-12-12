import React, { useState } from 'react';
import { UseFormReturn } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FormControl, FormField, FormItem, FormLabel, FormMessage, FormDescription } from '@/components/ui/form';
import { ElementFormData } from '@/schemas/knowledge-graph';
import { Plus, Trash2, CheckCircle2, Eye, EyeOff } from 'lucide-react';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ElementTypeFieldsProps {
  form: UseFormReturn<ElementFormData>;
  elementType: 'text_problem' | 'quick_question' | 'theory' | 'video';
}

export const ElementTypeFields: React.FC<ElementTypeFieldsProps> = ({ form, elementType }) => {
  const [showPreview, setShowPreview] = useState(false);
  const options = form.watch('options') || [];
  const content = form.watch('content');
  const videoUrl = form.watch('video_url');

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

  // Рендер превью
  const renderPreview = () => {
    if (!showPreview) return null;

    return (
      <Card className="mt-4 bg-muted/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Предпросмотр</CardTitle>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShowPreview(false)}
            >
              <EyeOff className="h-4 w-4" />
            </Button>
          </div>
          <CardDescription>Как это будет выглядеть для студента</CardDescription>
        </CardHeader>
        <CardContent>
          {elementType === 'text_problem' && content && (
            <div className="prose prose-sm max-w-none">
              <div className="whitespace-pre-wrap text-foreground">{content}</div>
            </div>
          )}

          {elementType === 'quick_question' && (
            <div className="space-y-3">
              {content && <p className="font-medium">{content}</p>}
              {options.length > 0 && (
                <div className="space-y-2">
                  {options.map((opt, idx) => (
                    <div
                      key={idx}
                      className={`p-3 border rounded-lg ${
                        opt.is_correct ? 'bg-green-50 border-green-500' : 'bg-card'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{opt.text || `Вариант ${idx + 1}`}</span>
                        {opt.is_correct && (
                          <Badge variant="default" className="ml-2">Правильный</Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {elementType === 'theory' && content && (
            <div className="prose prose-sm max-w-none">
              <div className="whitespace-pre-wrap text-foreground">{content}</div>
            </div>
          )}

          {elementType === 'video' && videoUrl && (
            <div className="space-y-2">
              <div className="aspect-video bg-muted rounded-lg flex items-center justify-center">
                <p className="text-sm text-muted-foreground">Видео: {videoUrl}</p>
              </div>
              {content && <p className="text-sm text-muted-foreground">{content}</p>}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  // Text problem - задача с текстом
  if (elementType === 'text_problem') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">Текстовая задача</h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowPreview(!showPreview)}
          >
            {showPreview ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
            {showPreview ? 'Скрыть' : 'Предпросмотр'}
          </Button>
        </div>

        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Текст задачи *</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Введите условие задачи, вопросы для студента..."
                  className="resize-none min-h-[200px]"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Опишите задачу, которую студент должен решить. Можно использовать математические формулы.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {renderPreview()}
      </div>
    );
  }

  // Quick question - вопрос с вариантами ответа
  if (elementType === 'quick_question') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">Быстрый вопрос</h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowPreview(!showPreview)}
          >
            {showPreview ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
            {showPreview ? 'Скрыть' : 'Предпросмотр'}
          </Button>
        </div>

        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Вопрос *</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Введите вопрос для студента..."
                  className="resize-none"
                  rows={3}
                  {...field}
                />
              </FormControl>
              <FormDescription>Четкий вопрос с одним правильным ответом</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <FormLabel>Варианты ответа *</FormLabel>
            <Button type="button" onClick={addOption} size="sm" variant="outline">
              <Plus className="h-4 w-4 mr-1" />
              Добавить вариант
            </Button>
          </div>

          {options.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Добавьте минимум 2 варианта ответа
            </p>
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
                    placeholder={`Вариант ${index + 1}`}
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
                      Правильный ответ
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

        {renderPreview()}
      </div>
    );
  }

  // Theory - теоретический материал
  if (elementType === 'theory') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">Теоретический материал</h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowPreview(!showPreview)}
          >
            {showPreview ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
            {showPreview ? 'Скрыть' : 'Предпросмотр'}
          </Button>
        </div>

        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Содержание *</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Введите теоретический материал, объяснения, формулы..."
                  className="resize-none min-h-[300px] font-mono"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Теоретическая информация, примеры, формулы для изучения
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {renderPreview()}
      </div>
    );
  }

  // Video - видео материал
  if (elementType === 'video') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">Видео</h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowPreview(!showPreview)}
          >
            {showPreview ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
            {showPreview ? 'Скрыть' : 'Предпросмотр'}
          </Button>
        </div>

        <FormField
          control={form.control}
          name="video_url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>URL видео *</FormLabel>
              <FormControl>
                <Input
                  placeholder="https://youtube.com/watch?v=..."
                  type="url"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Введите полный URL видео (YouTube, Vimeo или другой платформы)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="video_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Платформа</FormLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите платформу" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="youtube">YouTube</SelectItem>
                  <SelectItem value="vimeo">Vimeo</SelectItem>
                  <SelectItem value="other">Другая</SelectItem>
                </SelectContent>
              </Select>
              <FormDescription>Выберите платформу для правильного отображения</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Описание (опционально)</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Краткое описание содержания видео..."
                  className="resize-none"
                  rows={3}
                  {...field}
                />
              </FormControl>
              <FormDescription>Что студенты узнают из этого видео</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {renderPreview()}
      </div>
    );
  }

  return null;
};
