/**
 * NotificationTemplatesAdmin Component
 *
 * Admin component for managing notification templates
 * Features:
 * - List all templates with pagination
 * - Create new templates
 * - Edit existing templates
 * - Delete templates
 * - Preview templates with variable substitution
 * - Validate template syntax
 */

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Copy,
  Edit2,
  Eye,
  Loader2,
  Plus,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import {
  notificationTemplatesAPI,
  NotificationTemplate,
  NotificationType,
} from '@/integrations/api/notificationTemplatesAPI';

/**
 * Validation schema for template form
 */
const templateFormSchema = z.object({
  name: z.string().min(1, 'Название обязательно').max(200),
  description: z.string().max(1000).optional().default(''),
  type: z.string().min(1, 'Тип уведомления обязателен'),
  title_template: z.string().min(1, 'Шаблон заголовка обязателен'),
  message_template: z.string().min(1, 'Шаблон сообщения обязателен'),
  is_active: z.boolean().default(true),
});

type TemplateFormData = z.infer<typeof templateFormSchema>;

/**
 * Available notification types
 */
const NOTIFICATION_TYPES: Array<{ value: NotificationType; label: string }> = [
  { value: 'assignment_new', label: 'Новое задание' },
  { value: 'assignment_due', label: 'Срок сдачи задания' },
  { value: 'assignment_graded', label: 'Задание оценено' },
  { value: 'material_new', label: 'Новый материал' },
  { value: 'message_new', label: 'Новое сообщение' },
  { value: 'report_ready', label: 'Отчет готов' },
  { value: 'payment_success', label: 'Платеж успешен' },
  { value: 'payment_failed', label: 'Платеж не прошел' },
  { value: 'system', label: 'Системное уведомление' },
  { value: 'reminder', label: 'Напоминание' },
  { value: 'student_created', label: 'Ученик создан' },
  { value: 'subject_assigned', label: 'Предмет назначен' },
  { value: 'material_published', label: 'Материал опубликован' },
  { value: 'homework_submitted', label: 'Домашнее задание отправлено' },
  { value: 'payment_processed', label: 'Платеж обработан' },
  { value: 'invoice_sent', label: 'Счет выставлен' },
  { value: 'invoice_paid', label: 'Счет оплачен' },
  { value: 'invoice_overdue', label: 'Счет просрочен' },
  { value: 'invoice_viewed', label: 'Счет просмотрен' },
];

/**
 * Supported template variables with descriptions and examples
 */
const TEMPLATE_VARIABLES = [
  { name: 'user_name', description: 'Имя пользователя', example: 'Иван Сидоров' },
  { name: 'user_email', description: 'Email пользователя', example: 'ivan@example.com' },
  { name: 'subject', description: 'Название предмета', example: 'Математика' },
  { name: 'date', description: 'Дата', example: '2025-12-27' },
  { name: 'title', description: 'Название/заголовок', example: 'Контрольная работа' },
  { name: 'grade', description: 'Оценка', example: '5' },
  { name: 'feedback', description: 'Обратная связь', example: 'Отличная работа!' },
];

/**
 * Dialog for creating/editing templates
 */
interface TemplateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  template?: NotificationTemplate;
  onSuccess: () => void;
}

const TemplateDialog = ({
  open,
  onOpenChange,
  template,
  onSuccess,
}: TemplateDialogProps) => {
  const [loading, setLoading] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [preview, setPreview] = useState<{ title: string; message: string } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
    reset,
    setValue,
  } = useForm<TemplateFormData>({
    resolver: zodResolver(templateFormSchema),
    defaultValues: template || {
      name: '',
      description: '',
      type: '',
      title_template: '',
      message_template: '',
      is_active: true,
    },
  });

  const titleTemplate = watch('title_template');
  const messageTemplate = watch('message_template');
  const type = watch('type');

  useEffect(() => {
    if (open && template) {
      reset(template);
    } else if (open) {
      reset({
        name: '',
        description: '',
        type: '',
        title_template: '',
        message_template: '',
        is_active: true,
      });
    }
  }, [open, template, reset]);

  const onSubmit = async (data: TemplateFormData) => {
    setLoading(true);
    setValidationErrors([]);

    try {
      if (template) {
        const response = await notificationTemplatesAPI.updateTemplate(
          template.id,
          data
        );
        if (response.success) {
          toast.success('Шаблон обновлен');
          onSuccess();
          onOpenChange(false);
        } else {
          toast.error(response.error || 'Ошибка обновления');
        }
      } else {
        const response = await notificationTemplatesAPI.createTemplate(data);
        if (response.success) {
          toast.success('Шаблон создан');
          onSuccess();
          onOpenChange(false);
        } else {
          toast.error(response.error || 'Ошибка создания');
        }
      }
    } catch (err: any) {
      toast.error(err?.message || 'Ошибка сохранения шаблона');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async () => {
    setPreviewLoading(true);
    setValidationErrors([]);

    try {
      const sampleContext = {
        user_name: 'Иван Сидоров',
        user_email: 'ivan@example.com',
        subject: 'Математика',
        date: format(new Date(), 'dd.MM.yyyy', { locale: ru }),
        title: 'Контрольная работа',
        grade: '5',
        feedback: 'Отличная работа!',
      };

      if (template) {
        const response = await notificationTemplatesAPI.previewTemplate(
          template.id,
          sampleContext
        );
        if (response.success && response.data) {
          setPreview({
            title: response.data.rendered_title,
            message: response.data.rendered_message,
          });
          setPreviewOpen(true);
        } else {
          setValidationErrors([response.error || 'Ошибка предпросмотра']);
        }
      }
    } catch (err: any) {
      setValidationErrors([err?.message || 'Ошибка предпросмотра']);
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {template ? 'Редактировать шаблон' : 'Создать новый шаблон'}
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {validationErrors.length > 0 && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <ul className="list-disc pl-5 space-y-1">
                    {validationErrors.map((error, idx) => (
                      <li key={idx}>{error}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            {/* Name */}
            <div>
              <Label htmlFor="name">Название</Label>
              <Input
                id="name"
                placeholder="Название шаблона"
                {...register('name')}
              />
              {errors.name && (
                <p className="text-sm text-red-500 mt-1">{errors.name.message}</p>
              )}
            </div>

            {/* Description */}
            <div>
              <Label htmlFor="description">Описание</Label>
              <Textarea
                id="description"
                placeholder="Описание шаблона"
                className="h-20"
                {...register('description')}
              />
            </div>

            {/* Type */}
            <div>
              <Label htmlFor="type">Тип уведомления</Label>
              <Select
                defaultValue={type}
                onValueChange={(value) => setValue('type', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Выберите тип" />
                </SelectTrigger>
                <SelectContent>
                  {NOTIFICATION_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.type && (
                <p className="text-sm text-red-500 mt-1">{errors.type.message}</p>
              )}
            </div>

            {/* Title Template */}
            <div>
              <Label htmlFor="title_template">Шаблон заголовка</Label>
              <Textarea
                id="title_template"
                placeholder="Пример: Новое задание: {{title}}"
                className="h-20 font-mono text-sm"
                {...register('title_template')}
              />
              <p className="text-xs text-gray-500 mt-1">
                Используйте переменные в формате: {'{{variable_name}}'}
              </p>
              {errors.title_template && (
                <p className="text-sm text-red-500 mt-1">
                  {errors.title_template.message}
                </p>
              )}
            </div>

            {/* Message Template */}
            <div>
              <Label htmlFor="message_template">Шаблон сообщения</Label>
              <Textarea
                id="message_template"
                placeholder="Пример: Привет {{user_name}}, у вас новое задание по {{subject}}..."
                className="h-32 font-mono text-sm"
                {...register('message_template')}
              />
              <p className="text-xs text-gray-500 mt-1">
                Используйте переменные в формате: {'{{variable_name}}'}
              </p>
              {errors.message_template && (
                <p className="text-sm text-red-500 mt-1">
                  {errors.message_template.message}
                </p>
              )}
            </div>

            {/* Variable Reference */}
            <Card className="bg-gray-50">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Доступные переменные</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {TEMPLATE_VARIABLES.map((variable) => (
                    <div
                      key={variable.name}
                      className="p-2 bg-white border rounded text-sm"
                    >
                      <code className="text-blue-600 font-mono">
                        {'{{'}{variable.name}{'}'}
                      </code>
                      <p className="text-gray-600">{variable.description}</p>
                      <p className="text-gray-400 text-xs">
                        Пример: {variable.example}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Active checkbox */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_active"
                {...register('is_active')}
              />
              <Label htmlFor="is_active" className="cursor-pointer">
                Активен
              </Label>
            </div>

            {/* Preview and Submit */}
            <DialogFooter className="space-x-2">
              {template && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handlePreview}
                  disabled={previewLoading || !titleTemplate || !messageTemplate}
                >
                  {previewLoading ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Eye className="h-4 w-4 mr-2" />
                  )}
                  Предпросмотр
                </Button>
              )}
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={loading}
              >
                Отмена
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <>
                    {template ? (
                      <>
                        <Edit2 className="h-4 w-4 mr-2" />
                        Обновить
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        Создать
                      </>
                    )}
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Предпросмотр шаблона</DialogTitle>
          </DialogHeader>
          {preview && (
            <div className="space-y-4">
              <div>
                <Label>Заголовок</Label>
                <div className="p-3 bg-gray-50 border rounded mt-1 text-sm">
                  {preview.title}
                </div>
              </div>
              <div>
                <Label>Сообщение</Label>
                <div className="p-3 bg-gray-50 border rounded mt-1 text-sm whitespace-pre-wrap">
                  {preview.message}
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setPreviewOpen(false)}>Закрыть</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

/**
 * Main NotificationTemplatesAdmin component
 */
export const NotificationTemplatesAdmin = () => {
  const [templates, setTemplates] = useState<NotificationTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 20;
  const totalPages = Math.ceil(totalCount / pageSize);

  // Modals
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<NotificationTemplate | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Filters
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [activeFilter, setActiveFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadTemplates();
  }, [currentPage, typeFilter, activeFilter, searchQuery]);

  const loadTemplates = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await notificationTemplatesAPI.getTemplates(
        currentPage,
        pageSize,
        {
          type: (typeFilter || undefined) as NotificationType | undefined,
          is_active: activeFilter ? activeFilter === 'true' : undefined,
          search: searchQuery || undefined,
        }
      );

      if (response.success && response.data) {
        setTemplates(response.data.results || []);
        setTotalCount(response.data.count || 0);
      } else {
        setError(response.error || 'Ошибка загрузки шаблонов');
      }
    } catch (err: any) {
      setError(err?.message || 'Ошибка загрузки шаблонов');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTargetId) return;

    setDeleting(true);
    try {
      const response = await notificationTemplatesAPI.deleteTemplate(deleteTargetId);
      if (response.success) {
        toast.success('Шаблон удален');
        setDeleteDialogOpen(false);
        setDeleteTargetId(null);
        loadTemplates();
      } else {
        toast.error(response.error || 'Ошибка удаления');
      }
    } catch (err: any) {
      toast.error(err?.message || 'Ошибка удаления');
    } finally {
      setDeleting(false);
    }
  };

  const handleClone = async (template: NotificationTemplate) => {
    try {
      const response = await notificationTemplatesAPI.cloneTemplate(template.id);
      if (response.success) {
        toast.success('Шаблон скопирован');
        loadTemplates();
      } else {
        toast.error(response.error || 'Ошибка копирования');
      }
    } catch (err: any) {
      toast.error(err?.message || 'Ошибка копирования');
    }
  };

  const handleEditClick = (template: NotificationTemplate) => {
    setSelectedTemplate(template);
    setEditDialogOpen(true);
  };

  const handleDeleteClick = (id: number) => {
    setDeleteTargetId(id);
    setDeleteDialogOpen(true);
  };

  const getTypeLabel = (type: NotificationType): string => {
    const found = NOTIFICATION_TYPES.find((t) => t.value === type);
    return found?.label || type;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Шаблоны уведомлений</h1>
          <p className="text-gray-600 mt-1">
            Управление шаблонами для отправки уведомлений
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Новый шаблон
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Search */}
            <div>
              <Label htmlFor="search">Поиск</Label>
              <Input
                id="search"
                placeholder="Введите название или описание"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
              />
            </div>

            {/* Type Filter */}
            <div>
              <Label htmlFor="type-filter">Тип уведомления</Label>
              <Select
                value={typeFilter}
                onValueChange={(value) => {
                  setTypeFilter(value);
                  setCurrentPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Все типы" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все типы</SelectItem>
                  {NOTIFICATION_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Active Filter */}
            <div>
              <Label htmlFor="active-filter">Статус</Label>
              <Select
                value={activeFilter}
                onValueChange={(value) => {
                  setActiveFilter(value);
                  setCurrentPage(1);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Все" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все</SelectItem>
                  <SelectItem value="true">Активные</SelectItem>
                  <SelectItem value="false">Неактивные</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Templates Table */}
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">Шаблоны не найдены</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Название</TableHead>
                    <TableHead>Тип</TableHead>
                    <TableHead>Статус</TableHead>
                    <TableHead>Создано</TableHead>
                    <TableHead className="text-right">Действия</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {templates.map((template) => (
                    <TableRow key={template.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{template.name}</p>
                          {template.description && (
                            <p className="text-sm text-gray-600">
                              {template.description.substring(0, 60)}
                              {template.description.length > 60 ? '...' : ''}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {getTypeLabel(template.type as NotificationType)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {template.is_active ? (
                          <Badge className="bg-green-100 text-green-800">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Активен
                          </Badge>
                        ) : (
                          <Badge variant="secondary">Неактивен</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {format(new Date(template.created_at), 'dd.MM.yyyy', {
                          locale: ru,
                        })}
                      </TableCell>
                      <TableCell className="text-right space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditClick(template)}
                          title="Редактировать"
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleClone(template)}
                          title="Скопировать"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteClick(template.id)}
                          title="Удалить"
                          className="text-red-600 hover:text-red-800"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Всего: {totalCount} шаблонов
          </p>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <p className="text-sm">
              Страница {currentPage} из {totalPages}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Create Dialog */}
      <TemplateDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => {
          setCurrentPage(1);
          loadTemplates();
        }}
      />

      {/* Edit Dialog */}
      {selectedTemplate && (
        <TemplateDialog
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          template={selectedTemplate}
          onSuccess={loadTemplates}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить шаблон?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Шаблон будет удален.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={deleting}
            className="bg-red-600 hover:bg-red-700"
          >
            {deleting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : null}
            Удалить
          </AlertDialogAction>
          <AlertDialogCancel>Отмена</AlertDialogCancel>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default NotificationTemplatesAdmin;
