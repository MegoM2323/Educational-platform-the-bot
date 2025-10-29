import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { 
  FileText, 
  User, 
  Calendar, 
  Star, 
  Award, 
  AlertTriangle, 
  Target,
  Send,
  Save,
  X,
  Plus,
  Trash2
} from "lucide-react";
import { toast } from "sonner";
import { useErrorNotification, useSuccessNotification } from "@/components/NotificationSystem";
import { LoadingSpinner, ErrorState } from "@/components/LoadingStates";

export interface Student {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export interface Parent {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export interface ReportFormData {
  title: string;
  description: string;
  report_type: 'progress' | 'behavior' | 'achievement' | 'attendance' | 'performance' | 'custom';
  student_id: number;
  parent_id?: number;
  period_start: string;
  period_end: string;
  overall_grade?: string;
  progress_percentage: number;
  attendance_percentage: number;
  behavior_rating: number;
  recommendations?: string;
  concerns?: string;
  achievements?: string;
  content: Record<string, any>;
}

interface ReportFormProps {
  students: Student[];
  parents: Parent[];
  initialData?: Partial<ReportFormData>;
  onSubmit: (data: ReportFormData) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  className?: string;
}

const reportTypeConfig = {
  progress: {
    label: 'Прогресс',
    description: 'Отчет о прогрессе обучения',
    icon: Target,
  },
  behavior: {
    label: 'Поведение',
    description: 'Отчет о поведении в классе',
    icon: User,
  },
  achievement: {
    label: 'Достижения',
    description: 'Отчет о достижениях и успехах',
    icon: Award,
  },
  attendance: {
    label: 'Посещаемость',
    description: 'Отчет о посещаемости занятий',
    icon: Calendar,
  },
  performance: {
    label: 'Успеваемость',
    description: 'Отчет об успеваемости по предметам',
    icon: Star,
  },
  custom: {
    label: 'Пользовательский',
    description: 'Пользовательский отчет',
    icon: FileText,
  },
};

const gradeOptions = [
  { value: '5', label: '5 (Отлично)' },
  { value: '4', label: '4 (Хорошо)' },
  { value: '3', label: '3 (Удовлетворительно)' },
  { value: '2', label: '2 (Неудовлетворительно)' },
  { value: 'A+', label: 'A+ (Отлично)' },
  { value: 'A', label: 'A (Хорошо)' },
  { value: 'B', label: 'B (Удовлетворительно)' },
  { value: 'C', label: 'C (Неудовлетворительно)' },
];

export const ReportForm = ({
  students,
  parents,
  initialData,
  onSubmit,
  onCancel,
  isLoading = false,
  className = ""
}: ReportFormProps) => {
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();
  const [submitError, setSubmitError] = useState<string | null>(null);
  
  const [formData, setFormData] = useState<ReportFormData>({
    title: '',
    description: '',
    report_type: 'progress',
    student_id: 0,
    parent_id: undefined,
    period_start: '',
    period_end: '',
    overall_grade: '',
    progress_percentage: 0,
    attendance_percentage: 0,
    behavior_rating: 5,
    recommendations: '',
    concerns: '',
    achievements: '',
    content: {},
    ...initialData
  });

  const [customFields, setCustomFields] = useState<Array<{key: string, value: string}>>([]);
  const [newCustomField, setNewCustomField] = useState({key: '', value: ''});

  useEffect(() => {
    if (initialData) {
      setFormData(prev => ({ ...prev, ...initialData }));
    }
  }, [initialData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.title || !formData.student_id || !formData.period_start || !formData.period_end) {
      showError("Пожалуйста, заполните все обязательные поля");
      return;
    }

    if (new Date(formData.period_start) > new Date(formData.period_end)) {
      showError("Дата начала не может быть позже даты окончания");
      return;
    }

    try {
      setSubmitError(null);
      
      // Add custom fields to content
      const content = { ...formData.content };
      customFields.forEach(field => {
        if (field.key && field.value) {
          content[field.key] = field.value;
        }
      });

      await onSubmit({
        ...formData,
        content
      });
      
      showSuccess("Отчет успешно создан и отправлен родителям");
    } catch (error: any) {
      console.error("Error submitting report:", error);
      const errorMessage = error?.message || "Ошибка создания отчета";
      setSubmitError(errorMessage);
      showError(errorMessage, {
        action: {
          label: 'Повторить',
          onClick: () => handleSubmit(e),
        },
      });
    }
  };

  const addCustomField = () => {
    if (newCustomField.key && newCustomField.value) {
      setCustomFields(prev => [...prev, newCustomField]);
      setNewCustomField({key: '', value: ''});
    }
  };

  const removeCustomField = (index: number) => {
    setCustomFields(prev => prev.filter((_, i) => i !== index));
  };

  const getBehaviorRatingLabel = (rating: number) => {
    if (rating >= 8) return 'Отлично';
    if (rating >= 6) return 'Хорошо';
    if (rating >= 4) return 'Удовлетворительно';
    return 'Требует внимания';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU');
  };

  const selectedStudent = students.find(s => s.id === formData.student_id);
  const selectedParent = parents.find(p => p.id === formData.parent_id);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <FileText className="h-5 w-5" />
          <span>Создание отчета</span>
        </CardTitle>
      </CardHeader>

      <CardContent>
        {/* Error Display */}
        {submitError && (
          <ErrorState 
            error={submitError}
            onRetry={() => setSubmitError(null)}
            className="mb-6"
          />
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Основная информация</h3>
            
            <div className="space-y-2">
              <Label htmlFor="title">Название отчета *</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Например: Отчет о прогрессе за октябрь"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Описание</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Краткое описание отчета"
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label>Тип отчета *</Label>
              <RadioGroup
                value={formData.report_type}
                onValueChange={(value: any) => setFormData({ ...formData, report_type: value })}
                className="grid grid-cols-2 gap-4"
              >
                {Object.entries(reportTypeConfig).map(([key, config]) => {
                  const Icon = config.icon;
                  return (
                    <div key={key} className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-muted/50 cursor-pointer">
                      <RadioGroupItem value={key} id={key} />
                      <Label htmlFor={key} className="flex items-center space-x-2 cursor-pointer flex-1">
                        <Icon className="h-4 w-4" />
                        <div>
                          <div className="font-medium">{config.label}</div>
                          <div className="text-xs text-muted-foreground">{config.description}</div>
                        </div>
                      </Label>
                    </div>
                  );
                })}
              </RadioGroup>
            </div>
          </div>

          {/* Student and Parent Selection */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Участники</h3>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="student">Студент *</Label>
                <Select 
                  value={formData.student_id.toString()} 
                  onValueChange={(value) => setFormData({ ...formData, student_id: parseInt(value) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите студента" />
                  </SelectTrigger>
                  <SelectContent>
                    {students.map((student) => (
                      <SelectItem key={student.id} value={student.id.toString()}>
                        {student.first_name} {student.last_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="parent">Родитель</Label>
                <Select 
                  value={formData.parent_id?.toString() ?? 'none'} 
                  onValueChange={(value) => setFormData({ ...formData, parent_id: value === 'none' ? undefined : parseInt(value) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите родителя (необязательно)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Не выбран</SelectItem>
                    {parents.map((parent) => (
                      <SelectItem key={parent.id} value={parent.id.toString()}>
                        {parent.first_name} {parent.last_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Period */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Период отчета</h3>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="period_start">Дата начала *</Label>
                <Input
                  id="period_start"
                  type="date"
                  value={formData.period_start}
                  onChange={(e) => setFormData({ ...formData, period_start: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="period_end">Дата окончания *</Label>
                <Input
                  id="period_end"
                  type="date"
                  value={formData.period_end}
                  onChange={(e) => setFormData({ ...formData, period_end: e.target.value })}
                  required
                />
              </div>
            </div>
          </div>

          {/* Metrics */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Метрики и оценки</h3>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="overall_grade">Общая оценка</Label>
                  <Select 
                    value={formData.overall_grade ?? 'none'} 
                    onValueChange={(value) => setFormData({ ...formData, overall_grade: value === 'none' ? undefined : value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите оценку" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Не указана</SelectItem>
                      {gradeOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Прогресс: {formData.progress_percentage}%</Label>
                  <Slider
                    value={[formData.progress_percentage]}
                    onValueChange={([value]) => setFormData({ ...formData, progress_percentage: value })}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Посещаемость: {formData.attendance_percentage}%</Label>
                  <Slider
                    value={[formData.attendance_percentage]}
                    onValueChange={([value]) => setFormData({ ...formData, attendance_percentage: value })}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Поведение: {formData.behavior_rating}/10 - {getBehaviorRatingLabel(formData.behavior_rating)}</Label>
                  <Slider
                    value={[formData.behavior_rating]}
                    onValueChange={([value]) => setFormData({ ...formData, behavior_rating: value })}
                    max={10}
                    step={1}
                    className="w-full"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Достижения</Label>
                  <Textarea
                    value={formData.achievements || ''}
                    onChange={(e) => setFormData({ ...formData, achievements: e.target.value })}
                    placeholder="Опишите достижения студента"
                    rows={3}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Additional Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Дополнительная информация</h3>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="recommendations">Рекомендации</Label>
                <Textarea
                  id="recommendations"
                  value={formData.recommendations || ''}
                  onChange={(e) => setFormData({ ...formData, recommendations: e.target.value })}
                  placeholder="Рекомендации для улучшения"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="concerns">Обеспокоенности</Label>
                <Textarea
                  id="concerns"
                  value={formData.concerns || ''}
                  onChange={(e) => setFormData({ ...formData, concerns: e.target.value })}
                  placeholder="Области, требующие внимания"
                  rows={3}
                />
              </div>
            </div>
          </div>

          {/* Custom Fields */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Дополнительные поля</h3>
            
            <div className="space-y-2">
              {customFields.map((field, index) => (
                <div key={index} className="flex items-center space-x-2">
                  <Input
                    value={field.key}
                    onChange={(e) => {
                      const newFields = [...customFields];
                      newFields[index].key = e.target.value;
                      setCustomFields(newFields);
                    }}
                    placeholder="Название поля"
                    className="flex-1"
                  />
                  <Input
                    value={field.value}
                    onChange={(e) => {
                      const newFields = [...customFields];
                      newFields[index].value = e.target.value;
                      setCustomFields(newFields);
                    }}
                    placeholder="Значение"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeCustomField(index)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              
              <div className="flex items-center space-x-2">
                <Input
                  value={newCustomField.key}
                  onChange={(e) => setNewCustomField({ ...newCustomField, key: e.target.value })}
                  placeholder="Название поля"
                  className="flex-1"
                />
                <Input
                  value={newCustomField.value}
                  onChange={(e) => setNewCustomField({ ...newCustomField, value: e.target.value })}
                  placeholder="Значение"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addCustomField}
                  disabled={!newCustomField.key || !newCustomField.value}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end space-x-2 pt-6 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isLoading}
            >
              <X className="h-4 w-4 mr-2" />
              Отмена
            </Button>
            
            <Button
              type="button"
              variant="outline"
              disabled={isLoading}
            >
              <Save className="h-4 w-4 mr-2" />
              Сохранить черновик
            </Button>
            
            <Button
              type="submit"
              disabled={isLoading}
              className="gradient-primary shadow-glow hover:opacity-90 transition-opacity"
            >
              {isLoading ? (
                <LoadingSpinner size="sm" text="Отправка..." />
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Отправить отчет
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
