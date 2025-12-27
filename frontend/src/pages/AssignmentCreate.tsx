import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
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
import { Spinner } from '@/components/ui/spinner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { assignmentsAPI, CreateAssignmentPayload, Assignment } from '@/integrations/api/assignmentsAPI';
import { QuestionBuilder } from '@/components/assignments/QuestionBuilder';
import { RubricBuilder } from '@/components/assignments/RubricBuilder';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// Validation schema
const assignmentFormSchema = z.object({
  title: z
    .string()
    .min(3, 'Название должно содержать минимум 3 символа')
    .max(200, 'Название не должно превышать 200 символов'),
  description: z
    .string()
    .min(10, 'Описание должно содержать минимум 10 символов')
    .max(5000, 'Описание не должно превышать 5000 символов'),
  instructions: z
    .string()
    .min(5, 'Инструкции должны содержать минимум 5 символов')
    .max(5000, 'Инструкции не должны превышать 5000 символов'),
  type: z.enum(['homework', 'test', 'project', 'essay', 'practical']),
  max_score: z
    .number()
    .min(1, 'Максимальный балл должен быть больше 0')
    .max(500, 'Максимальный балл не должен превышать 500'),
  time_limit: z.number().optional().nullable(),
  attempts_limit: z
    .number()
    .min(1, 'Минимум 1 попытка')
    .max(10, 'Максимум 10 попыток'),
  start_date: z
    .string()
    .refine((date) => new Date(date) > new Date(), 'Дата начала должна быть в будущем'),
  due_date: z
    .string()
    .refine((date) => new Date(date) > new Date(), 'Дата сдачи должна быть в будущем'),
  tags: z.string().optional(),
  difficulty_level: z
    .number()
    .min(1, 'Уровень сложности от 1 до 5')
    .max(5, 'Уровень сложности от 1 до 5'),
  assigned_to: z.array(z.number()).optional(),
}).refine((data) => new Date(data.due_date) > new Date(data.start_date), {
  message: 'Дата сдачи должна быть позже даты начала',
  path: ['due_date'],
});

type AssignmentFormValues = z.infer<typeof assignmentFormSchema>;

interface Question {
  id?: number;
  question_text: string;
  question_type: 'single_choice' | 'multiple_choice' | 'text' | 'number';
  points: number;
  order: number;
  options?: string[];
  correct_answer?: any;
}

interface RubricCriterion {
  id?: number;
  name: string;
  description: string;
  max_points: number;
  point_scales: Record<string, number>;
}

interface AssignmentFormProps {
  assignmentId?: number;
  onSuccess?: (assignment: Assignment) => void;
}

export const AssignmentCreate: React.FC<AssignmentFormProps> = ({
  assignmentId,
  onSuccess,
}) => {
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();
  const effectiveId = assignmentId || (id ? parseInt(id) : undefined);

  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [rubricCriteria, setRubricCriteria] = useState<RubricCriterion[]>([]);
  const [showQuestionForm, setShowQuestionForm] = useState(false);
  const [showRubricForm, setShowRubricForm] = useState(false);

  const form = useForm<AssignmentFormValues>({
    resolver: zodResolver(assignmentFormSchema),
    defaultValues: {
      title: '',
      description: '',
      instructions: '',
      type: 'homework',
      max_score: 100,
      attempts_limit: 3,
      start_date: new Date().toISOString().split('T')[0],
      due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      tags: '',
      difficulty_level: 3,
      assigned_to: [],
    },
  });

  // Load existing assignment if editing
  useEffect(() => {
    if (effectiveId) {
      loadAssignment(effectiveId);
    }
  }, [effectiveId]);

  const loadAssignment = async (id: number) => {
    try {
      setIsLoadingData(true);
      const assignment = await assignmentsAPI.getAssignment(id);
      const qs = await assignmentsAPI.getQuestions(id);

      form.reset({
        title: assignment.title,
        description: assignment.description,
        instructions: assignment.instructions,
        type: assignment.type as any,
        max_score: assignment.max_score,
        time_limit: assignment.time_limit,
        attempts_limit: assignment.attempts_limit,
        start_date: assignment.start_date.split('T')[0],
        due_date: assignment.due_date.split('T')[0],
        tags: assignment.tags || '',
        difficulty_level: assignment.difficulty_level,
        assigned_to: assignment.assigned_to,
      });

      setQuestions(qs.map((q: any) => ({
        id: q.id,
        question_text: q.question_text,
        question_type: q.question_type,
        points: q.points,
        order: q.order,
        options: q.options,
        correct_answer: q.correct_answer,
      })));
    } catch (error) {
      console.error('Failed to load assignment:', error);
      toast.error('Не удалось загрузить задание');
    } finally {
      setIsLoadingData(false);
    }
  };

  const onSubmit = async (values: AssignmentFormValues) => {
    try {
      setIsLoading(true);

      const payload: CreateAssignmentPayload = {
        ...values,
        assigned_to: values.assigned_to || [],
      };

      let assignment: Assignment;
      if (effectiveId) {
        assignment = await assignmentsAPI.updateAssignment(effectiveId, payload);
        toast.success('Задание обновлено');
      } else {
        assignment = await assignmentsAPI.createAssignment(payload);
        toast.success('Задание создано');
      }

      // Handle questions
      if (questions.length > 0) {
        // Questions would be saved separately via API
        // This requires additional API endpoint implementation
      }

      if (onSuccess) {
        onSuccess(assignment);
      } else {
        navigate(`/assignments/${assignment.id}`);
      }
    } catch (error: any) {
      console.error('Failed to save assignment:', error);
      const message = error.response?.data?.detail || 'Ошибка при сохранении задания';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddQuestion = (question: Question) => {
    const newQuestion = {
      ...question,
      order: questions.length,
    };
    setQuestions([...questions, newQuestion]);
    setShowQuestionForm(false);
  };

  const handleUpdateQuestion = (index: number, question: Question) => {
    const updated = [...questions];
    updated[index] = question;
    setQuestions(updated);
  };

  const handleDeleteQuestion = (index: number) => {
    setQuestions(questions.filter((_, i) => i !== index));
  };

  const handleReorderQuestions = (fromIndex: number, toIndex: number) => {
    const updated = [...questions];
    const [moved] = updated.splice(fromIndex, 1);
    updated.splice(toIndex, 0, moved);
    // Update order field
    updated.forEach((q, idx) => {
      q.order = idx;
    });
    setQuestions(updated);
  };

  const handleAddRubricCriterion = (criterion: RubricCriterion) => {
    setRubricCriteria([...rubricCriteria, criterion]);
    setShowRubricForm(false);
  };

  const handleDeleteRubricCriterion = (index: number) => {
    setRubricCriteria(rubricCriteria.filter((_, i) => i !== index));
  };

  if (isLoadingData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <Card>
        <CardHeader>
          <CardTitle>
            {effectiveId ? 'Редактирование задания' : 'Создание задания'}
          </CardTitle>
          <CardDescription>
            Заполните форму для создания нового задания для студентов
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="general">Общие</TabsTrigger>
              <TabsTrigger value="questions">Вопросы</TabsTrigger>
              <TabsTrigger value="rubric">Рубрика</TabsTrigger>
              <TabsTrigger value="settings">Параметры</TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-6 mt-6">
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                  {/* Title */}
                  <FormField
                    control={form.control}
                    name="title"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Название задания</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Например: Контрольная работа №1"
                            {...field}
                            maxLength={200}
                          />
                        </FormControl>
                        <FormDescription>
                          {field.value?.length || 0}/200 символов
                        </FormDescription>
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
                        <FormLabel>Описание</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Подробное описание задания..."
                            {...field}
                            maxLength={5000}
                            rows={4}
                          />
                        </FormControl>
                        <FormDescription>
                          {field.value?.length || 0}/5000 символов
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Instructions */}
                  <FormField
                    control={form.control}
                    name="instructions"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Инструкции</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Пошаговые инструкции для выполнения..."
                            {...field}
                            maxLength={5000}
                            rows={4}
                          />
                        </FormControl>
                        <FormDescription>
                          {field.value?.length || 0}/5000 символов
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Type */}
                  <FormField
                    control={form.control}
                    name="type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Тип задания</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Выберите тип" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="homework">Домашнее задание</SelectItem>
                            <SelectItem value="test">Тест</SelectItem>
                            <SelectItem value="project">Проект</SelectItem>
                            <SelectItem value="essay">Эссе</SelectItem>
                            <SelectItem value="practical">Практическая работа</SelectItem>
                          </SelectContent>
                        </Select>
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
                            {...field}
                            onChange={(e) => field.onChange(parseInt(e.target.value))}
                            min={1}
                            max={500}
                          />
                        </FormControl>
                        <FormDescription>
                          Максимальное количество баллов за выполнение задания
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Difficulty Level */}
                  <FormField
                    control={form.control}
                    name="difficulty_level"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Уровень сложности</FormLabel>
                        <Select onValueChange={(value) => field.onChange(parseInt(value))} defaultValue={String(field.value)}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Выберите уровень" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="1">1 - Очень легко</SelectItem>
                            <SelectItem value="2">2 - Легко</SelectItem>
                            <SelectItem value="3">3 - Средне</SelectItem>
                            <SelectItem value="4">4 - Сложно</SelectItem>
                            <SelectItem value="5">5 - Очень сложно</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Tags */}
                  <FormField
                    control={form.control}
                    name="tags"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Теги (опционально)</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Разделены запятыми, например: математика, анализ"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex gap-4 justify-end pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => navigate(-1)}
                    >
                      Отмена
                    </Button>
                    <Button type="submit" disabled={isLoading}>
                      {isLoading ? (
                        <>
                          <Spinner className="mr-2 h-4 w-4" />
                          Сохранение...
                        </>
                      ) : (
                        'Сохранить'
                      )}
                    </Button>
                  </div>
                </form>
              </Form>
            </TabsContent>

            <TabsContent value="questions" className="space-y-6 mt-6">
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold">Вопросы ({questions.length})</h3>
                  <Button
                    onClick={() => setShowQuestionForm(!showQuestionForm)}
                    size="sm"
                  >
                    {showQuestionForm ? 'Отмена' : 'Добавить вопрос'}
                  </Button>
                </div>

                {showQuestionForm && (
                  <QuestionBuilder
                    onAdd={handleAddQuestion}
                    onCancel={() => setShowQuestionForm(false)}
                  />
                )}

                <QuestionList
                  questions={questions}
                  onUpdate={handleUpdateQuestion}
                  onDelete={handleDeleteQuestion}
                  onReorder={handleReorderQuestions}
                />
              </div>
            </TabsContent>

            <TabsContent value="rubric" className="space-y-6 mt-6">
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold">Критерии оценки</h3>
                  <Button
                    onClick={() => setShowRubricForm(!showRubricForm)}
                    size="sm"
                  >
                    {showRubricForm ? 'Отмена' : 'Добавить критерий'}
                  </Button>
                </div>

                {showRubricForm && (
                  <RubricBuilder
                    onAdd={handleAddRubricCriterion}
                    onCancel={() => setShowRubricForm(false)}
                  />
                )}

                <RubricList
                  criteria={rubricCriteria}
                  onDelete={handleDeleteRubricCriterion}
                />
              </div>
            </TabsContent>

            <TabsContent value="settings" className="space-y-6 mt-6">
              <Form {...form}>
                <form className="space-y-6">
                  {/* Start Date */}
                  <FormField
                    control={form.control}
                    name="start_date"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Дата начала</FormLabel>
                        <FormControl>
                          <Input
                            type="date"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Студенты смогут начать решение с этой даты
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Due Date */}
                  <FormField
                    control={form.control}
                    name="due_date"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Дата сдачи</FormLabel>
                        <FormControl>
                          <Input
                            type="date"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Срок выполнения задания (должна быть в будущем)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Time Limit */}
                  <FormField
                    control={form.control}
                    name="time_limit"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Время на выполнение (минут)</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            placeholder="Оставьте пусто для неограниченного времени"
                            {...field}
                            value={field.value || ''}
                            onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : null)}
                            min={5}
                            max={480}
                          />
                        </FormControl>
                        <FormDescription>
                          Максимальное время на решение задания
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Attempts Limit */}
                  <FormField
                    control={form.control}
                    name="attempts_limit"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Количество попыток</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            {...field}
                            onChange={(e) => field.onChange(parseInt(e.target.value))}
                            min={1}
                            max={10}
                          />
                        </FormControl>
                        <FormDescription>
                          Количество раз, когда студент может отправить решение
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </form>
              </Form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

/**
 * Question list component with drag-to-reorder support
 */
interface QuestionListProps {
  questions: Question[];
  onUpdate: (index: number, question: Question) => void;
  onDelete: (index: number) => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
}

const QuestionList: React.FC<QuestionListProps> = ({
  questions,
  onUpdate,
  onDelete,
  onReorder,
}) => {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (index: number) => {
    if (draggedIndex !== null && draggedIndex !== index) {
      onReorder(draggedIndex, index);
    }
    setDraggedIndex(null);
  };

  if (questions.length === 0) {
    return (
      <Card className="p-6 text-center text-gray-500">
        <p>Вопросы еще не добавлены</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {questions.map((question, index) => (
        <Card
          key={index}
          draggable
          onDragStart={() => handleDragStart(index)}
          onDragOver={handleDragOver}
          onDrop={() => handleDrop(index)}
          className={`p-4 cursor-move transition-opacity ${
            draggedIndex === index ? 'opacity-50' : 'opacity-100'
          }`}
        >
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <p className="font-semibold">
                Вопрос {index + 1}: {question.question_text}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                Тип: {getQuestionTypeLabel(question.question_type)} | Баллы: {question.points}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  // TODO: Open edit dialog
                }}
              >
                Изменить
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => onDelete(index)}
              >
                Удалить
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};

interface RubricListProps {
  criteria: RubricCriterion[];
  onDelete: (index: number) => void;
}

const RubricList: React.FC<RubricListProps> = ({ criteria, onDelete }) => {
  if (criteria.length === 0) {
    return (
      <Card className="p-6 text-center text-gray-500">
        <p>Критерии оценки еще не добавлены</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {criteria.map((criterion, index) => (
        <Card key={index} className="p-4">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <p className="font-semibold">{criterion.name}</p>
              <p className="text-sm text-gray-600 mt-1">
                {criterion.description}
              </p>
              <p className="text-sm text-gray-600 mt-2">
                Макс. баллов: {criterion.max_points}
              </p>
            </div>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => onDelete(index)}
            >
              Удалить
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
};

function getQuestionTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    single_choice: 'Один ответ',
    multiple_choice: 'Несколько ответов',
    text: 'Текст',
    number: 'Число',
  };
  return labels[type] || type;
}

export default AssignmentCreate;
