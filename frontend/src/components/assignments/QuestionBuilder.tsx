import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// Validation schema
const questionFormSchema = z.object({
  question_text: z
    .string()
    .min(3, 'Вопрос должен содержать минимум 3 символа')
    .max(2000, 'Вопрос не должен превышать 2000 символов'),
  question_type: z.enum(['single_choice', 'multiple_choice', 'text', 'number']),
  points: z
    .number()
    .min(1, 'Баллы должны быть больше 0')
    .max(100, 'Баллы не должны превышать 100'),
  options: z.array(z.string()).optional(),
  correct_answer: z.any().optional(),
});

type QuestionFormValues = z.infer<typeof questionFormSchema>;

interface Question {
  id?: number;
  question_text: string;
  question_type: 'single_choice' | 'multiple_choice' | 'text' | 'number';
  points: number;
  order: number;
  options?: string[];
  correct_answer?: any;
}

interface QuestionBuilderProps {
  onAdd: (question: Question) => void;
  onCancel: () => void;
  initialQuestion?: Question;
}

export const QuestionBuilder: React.FC<QuestionBuilderProps> = ({
  onAdd,
  onCancel,
  initialQuestion,
}) => {
  const [options, setOptions] = useState<string[]>(initialQuestion?.options || ['', '']);
  const [correctAnswer, setCorrectAnswer] = useState<any>(
    initialQuestion?.correct_answer || ''
  );
  const [questionType, setQuestionType] = useState<string>(
    initialQuestion?.question_type || 'single_choice'
  );

  const form = useForm<QuestionFormValues>({
    resolver: zodResolver(questionFormSchema),
    defaultValues: {
      question_text: initialQuestion?.question_text || '',
      question_type: initialQuestion?.question_type || 'single_choice',
      points: initialQuestion?.points || 1,
      options: initialQuestion?.options || ['', ''],
      correct_answer: initialQuestion?.correct_answer || '',
    },
  });

  const onSubmit = (values: QuestionFormValues) => {
    // Validation for options
    if (['single_choice', 'multiple_choice'].includes(questionType)) {
      const filledOptions = options.filter((o) => o.trim());
      if (filledOptions.length < 2) {
        form.setError('options', {
          message: 'Должно быть минимум 2 варианта ответа',
        });
        return;
      }
    }

    const question: Question = {
      question_text: values.question_text,
      question_type: values.question_type,
      points: values.points,
      order: 0, // Will be set by parent
      options: ['single_choice', 'multiple_choice'].includes(questionType)
        ? options.filter((o) => o.trim())
        : undefined,
      correct_answer: correctAnswer,
    };

    onAdd(question);
    form.reset();
    setOptions(['', '']);
    setCorrectAnswer('');
  };

  const handleAddOption = () => {
    setOptions([...options, '']);
  };

  const handleRemoveOption = (index: number) => {
    if (options.length > 2) {
      const updated = options.filter((_, i) => i !== index);
      setOptions(updated);
    }
  };

  const handleOptionChange = (index: number, value: string) => {
    const updated = [...options];
    updated[index] = value;
    setOptions(updated);
  };

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Добавить вопрос</CardTitle>
        <CardDescription>
          Заполните информацию о новом вопросе для задания
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Question Text */}
            <FormField
              control={form.control}
              name="question_text"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Текст вопроса</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Сформулируйте вопрос..."
                      {...field}
                      maxLength={2000}
                      rows={3}
                    />
                  </FormControl>
                  <FormDescription>
                    {field.value?.length || 0}/2000 символов
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Question Type */}
            <FormField
              control={form.control}
              name="question_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Тип вопроса</FormLabel>
                  <Select
                    onValueChange={(value) => {
                      field.onChange(value);
                      setQuestionType(value);
                    }}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Выберите тип вопроса" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="single_choice">Один правильный ответ</SelectItem>
                      <SelectItem value="multiple_choice">
                        Несколько правильных ответов
                      </SelectItem>
                      <SelectItem value="text">Текстовый ответ</SelectItem>
                      <SelectItem value="number">Числовой ответ</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Points */}
            <FormField
              control={form.control}
              name="points"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Баллы</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      {...field}
                      onChange={(e) => field.onChange(parseInt(e.target.value))}
                      min={1}
                      max={100}
                    />
                  </FormControl>
                  <FormDescription>
                    Количество баллов за этот вопрос
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Options for choice questions */}
            {['single_choice', 'multiple_choice'].includes(questionType) && (
              <FormItem>
                <FormLabel>Варианты ответа</FormLabel>
                <div className="space-y-2">
                  {options.map((option, index) => (
                    <div key={index} className="flex gap-2">
                      <Input
                        placeholder={`Вариант ${index + 1}`}
                        value={option}
                        onChange={(e) => handleOptionChange(index, e.target.value)}
                        maxLength={500}
                      />
                      {options.length > 2 && (
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          onClick={() => handleRemoveOption(index)}
                        >
                          Удалить
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddOption}
                  className="mt-2"
                >
                  + Добавить вариант
                </Button>
                <FormMessage />
              </FormItem>
            )}

            {/* Correct Answer */}
            {questionType === 'single_choice' && (
              <FormItem>
                <FormLabel>Правильный ответ</FormLabel>
                <Select value={correctAnswer} onValueChange={setCorrectAnswer}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите правильный ответ" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {options
                      .filter((o) => o.trim())
                      .map((option, index) => (
                        <SelectItem key={index} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}

            {questionType === 'multiple_choice' && (
              <FormItem>
                <FormLabel>Правильные ответы</FormLabel>
                <FormDescription>
                  Удерживайте Ctrl для выбора нескольких вариантов
                </FormDescription>
                <FormControl>
                  <select
                    multiple
                    value={Array.isArray(correctAnswer) ? correctAnswer : []}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, (option) =>
                        option.value
                      );
                      setCorrectAnswer(selected);
                    }}
                    className="w-full p-2 border rounded-md"
                  >
                    {options
                      .filter((o) => o.trim())
                      .map((option, index) => (
                        <option key={index} value={option}>
                          {option}
                        </option>
                      ))}
                  </select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}

            {questionType === 'text' && (
              <FormItem>
                <FormLabel>Правильный ответ (пример)</FormLabel>
                <FormControl>
                  <Input
                    placeholder="Пример правильного ответа"
                    value={correctAnswer || ''}
                    onChange={(e) => setCorrectAnswer(e.target.value)}
                    maxLength={500}
                  />
                </FormControl>
                <FormDescription>
                  Для текстовых ответов это используется как пример/подсказка
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}

            {questionType === 'number' && (
              <FormItem>
                <FormLabel>Правильный ответ</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    placeholder="Числовое значение"
                    value={correctAnswer || ''}
                    onChange={(e) => setCorrectAnswer(parseFloat(e.target.value))}
                  />
                </FormControl>
                <FormDescription>
                  Числовое значение с допуском на 5%
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4 justify-end pt-4">
              <Button type="button" variant="outline" onClick={onCancel}>
                Отмена
              </Button>
              <Button type="submit">Добавить вопрос</Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
};

export default QuestionBuilder;
