import React, { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { AlertCircle, Upload, FileText, Loader2, CheckCircle, X } from 'lucide-react';
import { Assignment } from '@/integrations/api/assignmentsAPI';

// Validation schema
const submissionSchema = z.object({
  answers: z.record(z.any()).optional(),
  notes: z.string().max(5000, 'Максимум 5000 символов'),
});

type SubmissionFormData = z.infer<typeof submissionSchema>;

export interface SubmissionFormProps {
  assignment: Assignment;
  questionCount?: number;
  onSubmit: (data: SubmissionFormData, files: File[]) => Promise<void>;
  isLoading?: boolean;
  showConfirmation?: boolean;
}

interface FileUpload {
  file: File;
  id: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
}

const ALLOWED_FILE_TYPES = ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar', '7z'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB per file
const MAX_TOTAL_SIZE = 200 * 1024 * 1024; // 200MB total
const MAX_FILES = 10;

export const AssignmentSubmitForm: React.FC<SubmissionFormProps> = ({
  assignment,
  questionCount = 0,
  onSubmit,
  isLoading = false,
  showConfirmation = true,
}) => {
  const form = useForm<SubmissionFormData>({
    resolver: zodResolver(submissionSchema),
    defaultValues: {
      answers: {},
      notes: '',
    },
  });

  const [files, setFiles] = useState<FileUpload[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [totalFileSize, setTotalFileSize] = useState(0);
  const [submissionDialogOpen, setSubmissionDialogOpen] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [draftSaved, setDraftSaved] = useState(false);
  const [draftSaveError, setDraftSaveError] = useState<string | null>(null);

  // Calculate total file size
  useEffect(() => {
    const total = files.reduce((sum, f) => sum + f.file.size, 0);
    setTotalFileSize(total);
  }, [files]);

  // Auto-save draft to localStorage
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        const draft = {
          timestamp: new Date().toISOString(),
          answers: form.getValues('answers'),
          notes: form.getValues('notes'),
        };
        localStorage.setItem(`assignment-draft-${assignment.id}`, JSON.stringify(draft));
        setDraftSaved(true);
        setDraftSaveError(null);
        setTimeout(() => setDraftSaved(false), 2000);
      } catch (error) {
        setDraftSaveError('Ошибка при сохранении черновика');
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [form, assignment.id]);

  // Load draft from localStorage
  useEffect(() => {
    try {
      const draft = localStorage.getItem(`assignment-draft-${assignment.id}`);
      if (draft) {
        const parsed = JSON.parse(draft);
        form.reset({
          answers: parsed.answers || {},
          notes: parsed.notes || '',
        });
      }
    } catch (error) {
      console.error('Error loading draft:', error);
    }
  }, [assignment.id, form]);

  const validateFileType = (file: File): boolean => {
    const extension = file.name.split('.').pop()?.toLowerCase();
    return extension ? ALLOWED_FILE_TYPES.includes(extension) : false;
  };

  const validateFileSize = (file: File): boolean => {
    return file.size <= MAX_FILE_SIZE;
  };

  const validateTotalSize = (newFile: File): boolean => {
    return totalFileSize + newFile.size <= MAX_TOTAL_SIZE;
  };

  const handleFileSelect = useCallback((selectedFiles: FileList) => {
    const newFiles = Array.from(selectedFiles);

    for (const file of newFiles) {
      if (!validateFileType(file)) {
        form.setError('notes', {
          type: 'manual',
          message: `Тип файла .${file.name.split('.').pop()} не поддерживается`,
        });
        return;
      }

      if (!validateFileSize(file)) {
        form.setError('notes', {
          type: 'manual',
          message: `Файл ${file.name} слишком большой (максимум 50MB)`,
        });
        return;
      }

      if (!validateTotalSize(file)) {
        form.setError('notes', {
          type: 'manual',
          message: `Общий размер файлов превышает 200MB`,
        });
        return;
      }

      if (files.length >= MAX_FILES) {
        form.setError('notes', {
          type: 'manual',
          message: `Максимум ${MAX_FILES} файлов`,
        });
        return;
      }

      const fileUpload: FileUpload = {
        file,
        id: `${Date.now()}-${Math.random()}`,
        progress: 0,
        status: 'pending',
      };

      setFiles((prev) => [...prev, fileUpload]);
    }
  }, [files.length, form, totalFileSize]);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files) {
      handleFileSelect(e.dataTransfer.files);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFileSelect(e.target.files);
    }
  };

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleSubmitClick = () => {
    if (showConfirmation && questionCount > 0) {
      setSubmissionDialogOpen(true);
    } else {
      handleFormSubmit();
    }
  };

  const handleFormSubmit = async () => {
    const formData = form.getValues();
    try {
      await onSubmit(formData, files.map((f) => f.file));
      // Clear draft after successful submission
      localStorage.removeItem(`assignment-draft-${assignment.id}`);
      form.reset();
      setFiles([]);
      setSubmissionDialogOpen(false);
    } catch (error) {
      console.error('Error submitting:', error);
    }
  };

  const fileSizeDisplay = (bytes: number): string => {
    if (bytes === 0) return '0 Б';
    const k = 1024;
    const sizes = ['Б', 'КБ', 'МБ', 'ГБ'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const progressPercentage = questionCount > 0 ? ((currentQuestionIndex + 1) / questionCount) * 100 : 0;
  const totalSize = fileSizeDisplay(totalFileSize);
  const maxSize = fileSizeDisplay(MAX_TOTAL_SIZE);

  return (
    <>
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Отправить ответы</span>
            {draftSaved && (
              <Badge variant="outline" className="bg-green-50">
                <CheckCircle className="w-4 h-4 mr-1" />
                Черновик сохранен
              </Badge>
            )}
            {draftSaveError && (
              <Badge variant="destructive">
                <AlertCircle className="w-4 h-4 mr-1" />
                {draftSaveError}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Заполните все обязательные поля и загрузите файлы при необходимости
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Progress Indicator */}
          {questionCount > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Прогресс ответов</span>
                <span className="text-muted-foreground">
                  {currentQuestionIndex + 1} из {questionCount}
                </span>
              </div>
              <Progress value={progressPercentage} className="h-2" />
            </div>
          )}

          {/* Notes/Answers Section */}
          <div className="space-y-2">
            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Ответы и комментарии</FormLabel>
                  <Textarea
                    {...field}
                    placeholder="Введите ваши ответы..."
                    className="min-h-[200px] resize-none"
                    disabled={isLoading}
                  />
                  <div className="flex justify-between text-sm text-muted-foreground mt-2">
                    <span>{field.value.length} / 5000</span>
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* File Upload Section */}
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium mb-2">Загрузить файлы</h3>
              <p className="text-xs text-muted-foreground mb-3">
                Поддерживаемые типы: {ALLOWED_FILE_TYPES.join(', ')}
              </p>

              {/* Drag and Drop Area */}
              <div
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors
                  ${dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-muted-foreground/50'}
                  ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              >
                <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm font-medium">Перетащите файлы сюда</p>
                <p className="text-xs text-muted-foreground mt-1">или</p>
                <label className="block">
                  <input
                    type="file"
                    multiple
                    onChange={handleFileInputChange}
                    disabled={isLoading}
                    className="hidden"
                    accept={ALLOWED_FILE_TYPES.map((t) => `.${t}`).join(',')}
                  />
                  <span className="text-sm text-primary hover:underline">
                    нажмите для выбора
                  </span>
                </label>
              </div>

              {/* File Size Info */}
              <div className="mt-3 text-xs text-muted-foreground">
                <p>Всего: {totalSize} / {maxSize}</p>
                <p>Файлов: {files.length} / {MAX_FILES}</p>
              </div>
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Загруженные файлы</h4>
                {files.map((fileUpload) => (
                  <div
                    key={fileUpload.id}
                    className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg border"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">
                          {fileUpload.file.name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {fileSizeDisplay(fileUpload.file.size)}
                        </p>
                      </div>
                    </div>

                    {fileUpload.status === 'success' && (
                      <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
                    )}

                    {fileUpload.status === 'uploading' && (
                      <Loader2 className="w-5 h-5 text-primary animate-spin flex-shrink-0" />
                    )}

                    {fileUpload.status === 'error' && (
                      <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
                    )}

                    {fileUpload.status === 'pending' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(fileUpload.id)}
                        disabled={isLoading}
                        className="flex-shrink-0"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Time Limit Warning */}
          {assignment.time_limit && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex gap-2">
              <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-800">
                <p className="font-medium">Ограничение по времени</p>
                <p>На выполнение задания отведено {assignment.time_limit} минут</p>
              </div>
            </div>
          )}

          {/* Attempts Limit Warning */}
          {assignment.attempts_limit && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex gap-2">
              <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-800">
                <p className="font-medium">Ограничение попыток</p>
                <p>Доступно {assignment.attempts_limit} попыток отправки</p>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <Button
            onClick={handleSubmitClick}
            disabled={isLoading || (!form.getValues('notes').trim() && files.length === 0)}
            className="w-full"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Отправка...
              </>
            ) : (
              'Отправить ответы'
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Submission Confirmation Dialog */}
      {showConfirmation && (
        <Dialog open={submissionDialogOpen} onOpenChange={setSubmissionDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Подтверждение отправки</DialogTitle>
            </DialogHeader>

            <div className="space-y-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <p className="text-sm text-amber-900">
                  Вы заполнили {currentQuestionIndex + 1} из {questionCount} вопросов.
                </p>
                {currentQuestionIndex + 1 < questionCount && (
                  <p className="text-sm text-amber-800 mt-2">
                    Некоторые вопросы остались без ответа. Вы уверены, что хотите отправить?
                  </p>
                )}
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-900">
                  После отправки вы не сможете изменить ответы.
                </p>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium">Резюме отправки:</p>
                <ul className="text-sm space-y-1 text-muted-foreground">
                  <li>Ответы заполнены: {currentQuestionIndex + 1}/{questionCount}</li>
                  <li>Загружено файлов: {files.length}</li>
                  <li>Общий размер: {totalSize}</li>
                </ul>
              </div>
            </div>

            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={() => setSubmissionDialogOpen(false)}
                disabled={isLoading}
              >
                Вернуться
              </Button>
              <Button
                onClick={handleFormSubmit}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Отправка...
                  </>
                ) : (
                  'Подтвердить отправку'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};
