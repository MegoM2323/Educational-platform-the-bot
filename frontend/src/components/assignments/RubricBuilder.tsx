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
import { Badge } from '@/components/ui/badge';

// Validation schema
const rubricCriterionSchema = z.object({
  name: z
    .string()
    .min(3, 'Название должно содержать минимум 3 символа')
    .max(200, 'Название не должно превышать 200 символов'),
  description: z
    .string()
    .min(5, 'Описание должно содержать минимум 5 символов')
    .max(1000, 'Описание не должно превышать 1000 символов'),
  max_points: z
    .number()
    .min(1, 'Максимум баллов должен быть больше 0')
    .max(100, 'Максимум баллов не должен превышать 100'),
});

type RubricCriterionValues = z.infer<typeof rubricCriterionSchema>;

interface PointScale {
  label: string;
  points: number;
}

interface RubricCriterion {
  id?: number;
  name: string;
  description: string;
  max_points: number;
  point_scales: Record<string, number>;
}

interface RubricBuilderProps {
  onAdd: (criterion: RubricCriterion) => void;
  onCancel: () => void;
}

export const RubricBuilder: React.FC<RubricBuilderProps> = ({
  onAdd,
  onCancel,
}) => {
  const [pointScales, setPointScales] = useState<PointScale[]>([
    { label: 'Отлично', points: 5 },
    { label: 'Хорошо', points: 4 },
    { label: 'Удовлетворительно', points: 3 },
  ]);

  const form = useForm<RubricCriterionValues>({
    resolver: zodResolver(rubricCriterionSchema),
    defaultValues: {
      name: '',
      description: '',
      max_points: 5,
    },
  });

  const onSubmit = (values: RubricCriterionValues) => {
    // Validate point scales
    if (pointScales.length === 0) {
      form.setError('max_points', {
        message: 'Должна быть минимум одна шкала оценки',
      });
      return;
    }

    const criterion: RubricCriterion = {
      name: values.name,
      description: values.description,
      max_points: values.max_points,
      point_scales: pointScales.reduce(
        (acc, scale) => {
          acc[scale.label] = scale.points;
          return acc;
        },
        {} as Record<string, number>
      ),
    };

    onAdd(criterion);
    form.reset();
    setPointScales([
      { label: 'Отлично', points: 5 },
      { label: 'Хорошо', points: 4 },
      { label: 'Удовлетворительно', points: 3 },
    ]);
  };

  const handleAddScale = () => {
    setPointScales([...pointScales, { label: '', points: 0 }]);
  };

  const handleRemoveScale = (index: number) => {
    if (pointScales.length > 1) {
      const updated = pointScales.filter((_, i) => i !== index);
      setPointScales(updated);
    }
  };

  const handleScaleChange = (
    index: number,
    field: 'label' | 'points',
    value: string | number
  ) => {
    const updated = [...pointScales];
    if (field === 'label') {
      updated[index].label = value as string;
    } else {
      updated[index].points = parseInt(value as string) || 0;
    }
    setPointScales(updated);
  };

  const handlePresetTemplate = (template: string) => {
    switch (template) {
      case 'binary':
        setPointScales([
          { label: 'Да', points: 1 },
          { label: 'Нет', points: 0 },
        ]);
        break;
      case 'proficiency':
        setPointScales([
          { label: 'Мастер', points: 4 },
          { label: 'Развитие', points: 3 },
          { label: 'Начинающий', points: 2 },
          { label: 'Не приступал', points: 0 },
        ]);
        break;
      case 'standard':
        setPointScales([
          { label: 'Отлично', points: 5 },
          { label: 'Хорошо', points: 4 },
          { label: 'Удовлетворительно', points: 3 },
          { label: 'Неудовлетворительно', points: 1 },
        ]);
        break;
      case 'percentage':
        setPointScales([
          { label: '100%', points: 5 },
          { label: '80-99%', points: 4 },
          { label: '60-79%', points: 3 },
          { label: '40-59%', points: 2 },
          { label: 'Менее 40%', points: 0 },
        ]);
        break;
    }
  };

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Добавить критерий оценки</CardTitle>
        <CardDescription>
          Определите критерий и шкалу баллов для оценки работы студентов
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Name */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Название критерия</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Например: Содержание, Оформление, Грамматика"
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
                  <FormLabel>Описание критерия</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Подробное описание критерия оценки..."
                      {...field}
                      maxLength={1000}
                      rows={3}
                    />
                  </FormControl>
                  <FormDescription>
                    {field.value?.length || 0}/1000 символов
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Max Points */}
            <FormField
              control={form.control}
              name="max_points"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Максимум баллов</FormLabel>
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
                    Максимальное количество баллов для этого критерия
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Preset Templates */}
            <FormItem>
              <FormLabel>Шаблоны шкалы баллов</FormLabel>
              <FormDescription>
                Выберите предустановленный шаблон или создайте собственный
              </FormDescription>
              <div className="flex flex-wrap gap-2 mt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handlePresetTemplate('standard')}
                >
                  Стандартная (1-5)
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handlePresetTemplate('binary')}
                >
                  Да/Нет
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handlePresetTemplate('proficiency')}
                >
                  Уровни компетенции
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handlePresetTemplate('percentage')}
                >
                  По процентам
                </Button>
              </div>
            </FormItem>

            {/* Point Scales */}
            <FormItem>
              <FormLabel>Шкала баллов</FormLabel>
              <div className="space-y-3 mt-2">
                {pointScales.map((scale, index) => (
                  <div key={index} className="flex gap-2 items-end">
                    <div className="flex-1">
                      <Input
                        placeholder="Описание уровня (например: Отлично)"
                        value={scale.label}
                        onChange={(e) => handleScaleChange(index, 'label', e.target.value)}
                        maxLength={100}
                      />
                    </div>
                    <div className="w-24">
                      <Input
                        type="number"
                        placeholder="Баллы"
                        value={scale.points}
                        onChange={(e) => handleScaleChange(index, 'points', e.target.value)}
                        min={0}
                        max={100}
                      />
                    </div>
                    {pointScales.length > 1 && (
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => handleRemoveScale(index)}
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
                onClick={handleAddScale}
                className="mt-2"
              >
                + Добавить уровень
              </Button>
            </FormItem>

            {/* Preview */}
            {pointScales.length > 0 && (
              <FormItem>
                <FormLabel>Предпросмотр</FormLabel>
                <div className="flex flex-wrap gap-2 mt-2">
                  {pointScales
                    .filter((s) => s.label.trim())
                    .sort((a, b) => b.points - a.points)
                    .map((scale, index) => (
                      <Badge key={index} variant="secondary">
                        {scale.label}: {scale.points} баллов
                      </Badge>
                    ))}
                </div>
              </FormItem>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4 justify-end pt-4">
              <Button type="button" variant="outline" onClick={onCancel}>
                Отмена
              </Button>
              <Button type="submit">Добавить критерий</Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
};

export default RubricBuilder;
