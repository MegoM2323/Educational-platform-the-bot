import { useState, useEffect } from "react";
import { logger } from '@/utils/logger';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  CheckCircle,
  AlertCircle,
  Loader2,
  Send,
  X,
  Eye,
} from "lucide-react";
import { toast } from "sonner";
import { useErrorNotification, useSuccessNotification } from "@/components/NotificationSystem";
import { LoadingSpinner, ErrorState } from "@/components/LoadingStates";
import { unifiedAPI } from "@/integrations/api/unifiedClient";

/**
 * Report Template Interface
 */
export interface ReportTemplate {
  id: number;
  name: string;
  report_type: string;
  template_content: string;
  created_at: string;
  description?: string;
}

/**
 * Report Create Form Data Interface
 */
export interface ReportCreateFormData {
  template_id: number;
  report_name: string;
  date_start: string;
  date_end: string;
  student_id?: number;
  class_id?: number;
}

/**
 * Report Response Interface
 */
export interface GeneratedReport {
  id: number;
  name: string;
  template_id: number;
  content: string;
  date_created: string;
  date_start: string;
  date_end: string;
  status: 'generated' | 'sent' | 'archived';
}

interface ReportCreateFormProps {
  onSuccess?: (report: GeneratedReport) => void;
  onCancel?: () => void;
  className?: string;
  students?: Array<{ id: number; name: string }>;
  classes?: Array<{ id: number; name: string }>;
}

/**
 * ReportCreateForm - Form for generating custom reports from templates
 *
 * Features:
 * - Template selection with preview
 * - Report name and date range inputs
 * - Student/class filtering options
 * - Form validation with real-time feedback
 * - Loading indicator during generation
 * - Preview of selected template
 */
export const ReportCreateForm = ({
  onSuccess,
  onCancel,
  className = "",
  students = [],
  classes = [],
}: ReportCreateFormProps) => {
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();

  // State management
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const [formData, setFormData] = useState<ReportCreateFormData>({
    template_id: 0,
    report_name: '',
    date_start: '',
    date_end: '',
    student_id: undefined,
    class_id: undefined,
  });

  // Validation errors state
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Load templates on component mount
  useEffect(() => {
    loadTemplates();
  }, []);

  /**
   * Load available report templates from API
   */
  const loadTemplates = async () => {
    try {
      setLoadingTemplates(true);
      logger.debug('[ReportCreateForm] Loading templates...');

      const response = await unifiedAPI.request<ReportTemplate[]>('/reports/templates/');

      if (response.error) {
        logger.error('[ReportCreateForm] Error loading templates:', response.error);
        throw new Error(response.error);
      }

      const templatesArray = Array.isArray(response.data) ? response.data : [];
      logger.debug('[ReportCreateForm] Templates loaded:', templatesArray.length);
      setTemplates(templatesArray);

      // Auto-select first template if available
      if (templatesArray.length > 0 && formData.template_id === 0) {
        setFormData(prev => ({ ...prev, template_id: templatesArray[0].id }));
      }
    } catch (error: any) {
      logger.error('[ReportCreateForm] Error loading templates:', error);
      showError(error.message || 'Не удалось загрузить шаблоны отчетов');
    } finally {
      setLoadingTemplates(false);
    }
  };

  /**
   * Validate form data
   */
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.template_id || formData.template_id === 0) {
      errors.template_id = 'Пожалуйста, выберите шаблон отчета';
    }

    if (!formData.report_name || formData.report_name.trim() === '') {
      errors.report_name = 'Название отчета обязательно';
    }

    if (!formData.date_start) {
      errors.date_start = 'Дата начала обязательна';
    }

    if (!formData.date_end) {
      errors.date_end = 'Дата окончания обязательна';
    }

    if (formData.date_start && formData.date_end) {
      const startDate = new Date(formData.date_start);
      const endDate = new Date(formData.date_end);

      if (startDate > endDate) {
        errors.date_range = 'Дата начала не может быть позже даты окончания';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate form
    if (!validateForm()) {
      showError('Пожалуйста, исправьте ошибки в форме');
      return;
    }

    try {
      setSubmitError(null);
      setLoading(true);
      logger.debug('[ReportCreateForm] Submitting form:', formData);

      // Prepare request data
      const requestData = {
        template_id: formData.template_id,
        report_name: formData.report_name.trim(),
        date_start: formData.date_start,
        date_end: formData.date_end,
        ...(formData.student_id && { student_id: formData.student_id }),
        ...(formData.class_id && { class_id: formData.class_id }),
      };

      logger.debug('[ReportCreateForm] Request data:', requestData);

      // Call API to generate report
      const response = await unifiedAPI.request<GeneratedReport>('/reports/generate/', {
        method: 'POST',
        body: JSON.stringify(requestData),
      });

      if (response.error || !response.success) {
        throw new Error(response.error || 'Ошибка при создании отчета');
      }

      if (!response.data) {
        throw new Error('Отчет не был создан');
      }

      logger.debug('[ReportCreateForm] Report generated successfully:', response.data);

      showSuccess('Отчет успешно создан');

      // Call success callback if provided
      if (onSuccess) {
        onSuccess(response.data);
      }

      // Reset form
      setFormData({
        template_id: templates.length > 0 ? templates[0].id : 0,
        report_name: '',
        date_start: '',
        date_end: '',
        student_id: undefined,
        class_id: undefined,
      });
    } catch (error: any) {
      logger.error('[ReportCreateForm] Error submitting form:', error);
      const errorMessage = error?.message || 'Ошибка при создании отчета';
      setSubmitError(errorMessage);
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Get selected template for preview
   */
  const selectedTemplate = templates.find(t => t.id === formData.template_id);

  /**
   * Handle field change with real-time validation
   */
  const handleFieldChange = (field: keyof ReportCreateFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));

    // Clear validation error for this field when user starts typing
    if (validationErrors[field]) {
      setValidationErrors(prev => {
        const updated = { ...prev };
        delete updated[field];
        return updated;
      });
    }
  };

  // Render loading state
  if (loadingTemplates) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />
            <span>Загрузка шаблонов отчетов...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render empty state when no templates
  if (templates.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <FileText className="h-5 w-5" />
            <span>Создание отчета</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ErrorState
            error="Шаблоны отчетов недоступны. Пожалуйста, попробуйте позже или свяжитесь с администратором."
            onRetry={loadTemplates}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <FileText className="h-5 w-5" />
          <span>Создание пользовательского отчета</span>
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
          {/* Template Selection */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Выбор шаблона</h3>

            <div className="space-y-2">
              <Label htmlFor="template">Шаблон отчета *</Label>
              <Select
                value={formData.template_id.toString()}
                onValueChange={(value) =>
                  handleFieldChange('template_id', parseInt(value))
                }
              >
                <SelectTrigger id="template">
                  <SelectValue placeholder="Выберите шаблон отчета" />
                </SelectTrigger>
                <SelectContent>
                  {templates.map((template) => (
                    <SelectItem key={template.id} value={template.id.toString()}>
                      <div className="flex items-center gap-2">
                        <span>{template.name}</span>
                        {template.description && (
                          <span className="text-xs text-muted-foreground">
                            ({template.description})
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {validationErrors.template_id && (
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  {validationErrors.template_id}
                </div>
              )}
            </div>

            {/* Template Preview Button */}
            {selectedTemplate && (
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowPreview(!showPreview)}
                className="w-full"
              >
                <Eye className="h-4 w-4 mr-2" />
                {showPreview ? 'Скрыть превью' : 'Показать превью'}
              </Button>
            )}

            {/* Template Preview */}
            {showPreview && selectedTemplate && (
              <Card className="bg-muted p-4 border-dashed">
                <div className="space-y-2">
                  <h4 className="font-medium">Превью шаблона</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    <strong>Тип:</strong> {selectedTemplate.report_type}
                  </p>
                  <div className="bg-background p-3 rounded text-sm max-h-40 overflow-y-auto whitespace-pre-wrap">
                    {selectedTemplate.template_content}
                  </div>
                </div>
              </Card>
            )}
          </div>

          {/* Report Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Информация об отчете</h3>

            <div className="space-y-2">
              <Label htmlFor="report_name">Название отчета *</Label>
              <Input
                id="report_name"
                value={formData.report_name}
                onChange={(e) => handleFieldChange('report_name', e.target.value)}
                placeholder="Например: Квартальный отчет"
                required
              />
              {validationErrors.report_name && (
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  {validationErrors.report_name}
                </div>
              )}
            </div>

            {/* Date Range */}
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="date_start">Дата начала *</Label>
                <Input
                  id="date_start"
                  type="date"
                  value={formData.date_start}
                  onChange={(e) => handleFieldChange('date_start', e.target.value)}
                  required
                />
                {validationErrors.date_start && (
                  <div className="flex items-center gap-2 text-sm text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    {validationErrors.date_start}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="date_end">Дата окончания *</Label>
                <Input
                  id="date_end"
                  type="date"
                  value={formData.date_end}
                  onChange={(e) => handleFieldChange('date_end', e.target.value)}
                  required
                />
                {validationErrors.date_end && (
                  <div className="flex items-center gap-2 text-sm text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    {validationErrors.date_end}
                  </div>
                )}
              </div>
            </div>

            {validationErrors.date_range && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                {validationErrors.date_range}
              </div>
            )}
          </div>

          {/* Optional Filters */}
          {(students.length > 0 || classes.length > 0) && (
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Фильтры (опционально)</h3>

              <div className="grid md:grid-cols-2 gap-4">
                {students.length > 0 && (
                  <div className="space-y-2">
                    <Label htmlFor="student">Выберите студента</Label>
                    <Select
                      value={formData.student_id?.toString() ?? ''}
                      onValueChange={(value) =>
                        handleFieldChange(
                          'student_id',
                          value ? parseInt(value) : undefined
                        )
                      }
                    >
                      <SelectTrigger id="student">
                        <SelectValue placeholder="Все студенты" />
                      </SelectTrigger>
                      <SelectContent>
                        {students.map((student) => (
                          <SelectItem key={student.id} value={student.id.toString()}>
                            {student.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {classes.length > 0 && (
                  <div className="space-y-2">
                    <Label htmlFor="class">Выберите класс</Label>
                    <Select
                      value={formData.class_id?.toString() ?? ''}
                      onValueChange={(value) =>
                        handleFieldChange(
                          'class_id',
                          value ? parseInt(value) : undefined
                        )
                      }
                    >
                      <SelectTrigger id="class">
                        <SelectValue placeholder="Все классы" />
                      </SelectTrigger>
                      <SelectContent>
                        {classes.map((cls) => (
                          <SelectItem key={cls.id} value={cls.id.toString()}>
                            {cls.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex items-center justify-end space-x-2 pt-6 border-t">
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
                <X className="h-4 w-4 mr-2" />
                Отмена
              </Button>
            )}

            <Button type="submit" disabled={loading} className="gradient-primary shadow-glow hover:opacity-90 transition-opacity">
              {loading ? (
                <LoadingSpinner size="sm" text="Создание..." />
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Создать отчет
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

/**
 * Export display name for debugging
 */
ReportCreateForm.displayName = 'ReportCreateForm';
