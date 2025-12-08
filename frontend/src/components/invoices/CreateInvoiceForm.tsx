import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useCreateInvoice } from '@/hooks/useInvoicesList';
import { invoiceAPI, TutorStudent } from '@/integrations/api/invoiceAPI';
import { Loader2 } from 'lucide-react';
import { logger } from '@/utils/logger';
import { format } from 'date-fns';

interface CreateInvoiceFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface FormData {
  student_id: string;
  amount: string;
  description: string;
  due_date: string;
  enrollment_id: string;
}

interface FormErrors {
  student_id?: string;
  amount?: string;
  description?: string;
  due_date?: string;
}

export const CreateInvoiceForm = ({ open, onOpenChange }: CreateInvoiceFormProps) => {
  const createMutation = useCreateInvoice();

  const [formData, setFormData] = useState<FormData>({
    student_id: '',
    amount: '',
    description: '',
    due_date: '',
    enrollment_id: '',
  });

  const [errors, setErrors] = useState<FormErrors>({});

  // Загрузка списка студентов
  const { data: students, isLoading: isLoadingStudents } = useQuery({
    queryKey: ['tutor-students-for-invoice'],
    queryFn: async () => {
      logger.debug('[CreateInvoiceForm] Fetching students...');
      const result = await invoiceAPI.getTutorStudents();
      logger.debug('[CreateInvoiceForm] Fetched students:', result);
      return result;
    },
    enabled: open,
  });

  // Найти выбранного студента
  const selectedStudent = students?.find((s) => s.id === parseInt(formData.student_id));

  // Сброс формы при закрытии
  useEffect(() => {
    if (!open) {
      setFormData({
        student_id: '',
        amount: '',
        description: '',
        due_date: '',
        enrollment_id: '',
      });
      setErrors({});
    }
  }, [open]);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.student_id) {
      newErrors.student_id = 'Выберите студента';
    }

    if (!formData.amount) {
      newErrors.amount = 'Укажите сумму';
    } else {
      const amount = parseFloat(formData.amount);
      if (isNaN(amount) || amount <= 0) {
        newErrors.amount = 'Сумма должна быть больше 0';
      }
    }

    if (!formData.description || formData.description.trim().length === 0) {
      newErrors.description = 'Укажите описание';
    } else if (formData.description.length > 2000) {
      newErrors.description = 'Описание не должно превышать 2000 символов';
    }

    if (!formData.due_date) {
      newErrors.due_date = 'Укажите срок оплаты';
    } else {
      const dueDate = new Date(formData.due_date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (dueDate < today) {
        newErrors.due_date = 'Срок оплаты не может быть в прошлом';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      await createMutation.mutateAsync({
        student_id: parseInt(formData.student_id),
        amount: formData.amount,
        description: formData.description.trim(),
        due_date: formData.due_date,
        enrollment_id: formData.enrollment_id ? parseInt(formData.enrollment_id) : undefined,
      });

      onOpenChange(false);
    } catch (error) {
      // Ошибка обрабатывается в хуке
      logger.error('[CreateInvoiceForm] Submit error:', error);
    }
  };

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Очистка ошибки для поля
    if (errors[field as keyof FormErrors]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field as keyof FormErrors];
        return newErrors;
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Создать счёт</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Выбор студента */}
          <div>
            <Label htmlFor="student">Студент *</Label>
            <Select
              value={formData.student_id}
              onValueChange={(value) => {
                handleInputChange('student_id', value);
                // Сброс выбранного предмета при смене студента
                handleInputChange('enrollment_id', '');
              }}
            >
              <SelectTrigger
                id="student"
                className={errors.student_id ? 'border-red-500' : ''}
              >
                <SelectValue placeholder="Выберите студента" />
              </SelectTrigger>
              <SelectContent>
                {isLoadingStudents ? (
                  <div className="p-2 text-center text-sm text-muted-foreground">
                    Загрузка...
                  </div>
                ) : students && students.length > 0 ? (
                  students.map((student) => (
                    <SelectItem key={student.id} value={String(student.id)}>
                      {student.full_name}
                    </SelectItem>
                  ))
                ) : (
                  <div className="p-2 text-center text-sm text-muted-foreground">
                    Нет доступных студентов
                  </div>
                )}
              </SelectContent>
            </Select>
            {errors.student_id && (
              <p className="text-sm text-red-500 mt-1">{errors.student_id}</p>
            )}
          </div>

          {/* Выбор предмета (опционально) */}
          {selectedStudent && selectedStudent.enrollments.length > 0 && (
            <div>
              <Label htmlFor="enrollment">Предмет (опционально)</Label>
              <Select
                value={formData.enrollment_id}
                onValueChange={(value) => handleInputChange('enrollment_id', value)}
              >
                <SelectTrigger id="enrollment">
                  <SelectValue placeholder="Выберите предмет (если применимо)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Не указывать предмет</SelectItem>
                  {selectedStudent.enrollments.map((enrollment) => (
                    <SelectItem key={enrollment.id} value={String(enrollment.id)}>
                      {enrollment.subject.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Сумма */}
          <div>
            <Label htmlFor="amount">Сумма (руб) *</Label>
            <Input
              id="amount"
              type="number"
              step="0.01"
              min="0"
              placeholder="5000.00"
              value={formData.amount}
              onChange={(e) => handleInputChange('amount', e.target.value)}
              className={errors.amount ? 'border-red-500' : ''}
            />
            {errors.amount && (
              <p className="text-sm text-red-500 mt-1">{errors.amount}</p>
            )}
          </div>

          {/* Срок оплаты */}
          <div>
            <Label htmlFor="due_date">Срок оплаты *</Label>
            <Input
              id="due_date"
              type="date"
              value={formData.due_date}
              onChange={(e) => handleInputChange('due_date', e.target.value)}
              className={errors.due_date ? 'border-red-500' : ''}
              min={format(new Date(), 'yyyy-MM-dd')}
            />
            {errors.due_date && (
              <p className="text-sm text-red-500 mt-1">{errors.due_date}</p>
            )}
          </div>

          {/* Описание */}
          <div>
            <Label htmlFor="description">Описание *</Label>
            <Textarea
              id="description"
              placeholder="Например: Оплата за занятия по математике за декабрь 2025 года"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              className={errors.description ? 'border-red-500' : ''}
              rows={4}
              maxLength={2000}
            />
            <div className="flex justify-between items-center mt-1">
              {errors.description ? (
                <p className="text-sm text-red-500">{errors.description}</p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Максимум 2000 символов
                </p>
              )}
              <p className="text-sm text-muted-foreground">
                {formData.description.length} / 2000
              </p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={createMutation.isPending}
          >
            Отмена
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Создание...
              </>
            ) : (
              'Создать счёт'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
