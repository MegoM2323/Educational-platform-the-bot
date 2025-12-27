import React, { useState, useRef, useEffect, DragEvent, ChangeEvent } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { AlertCircle, Upload, FileText, X, Send, Loader2, CheckCircle, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { logger } from '@/utils/logger';
import { toast } from 'sonner';
import { unifiedAPI as apiClient } from '@/integrations/api/unifiedClient';

/**
 * Material submission form with comprehensive file upload
 * Supports multiple files, drag-drop, validation, and localStorage draft saving
 */

// Validation schema
const submissionSchema = z.object({
  notes: z
    .string()
    .max(5000, 'Заметки не должны превышать 5000 символов')
    .optional()
    .default(''),
});

type SubmissionFormData = z.infer<typeof submissionSchema>;

interface SubmissionFormProps {
  materialId: number;
  materialTitle?: string;
  onSuccess?: (submissionId?: string | number) => void;
  onCancel?: () => void;
  className?: string;
}

interface UploadedFile {
  id: string;
  file: File;
  preview?: string;
  error?: string;
}

// File validation constants
const ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar', '7z'];
const ALLOWED_MIMETYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'image/jpeg',
  'image/png',
  'image/gif',
  'application/zip',
  'application/x-rar-compressed',
  'application/x-7z-compressed',
];

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB per file
const MAX_TOTAL_SIZE = 200 * 1024 * 1024; // 200MB total
const MAX_FILES = 10;
const DRAFT_STORAGE_KEY = 'submission_draft';

/**
 * Format file size for display
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Get file extension
 */
function getFileExtension(filename: string): string {
  if (!filename.includes('.')) return '';
  return filename.split('.').pop()?.toLowerCase() || '';
}

/**
 * Check if file is an image
 */
function isImageFile(filename: string): boolean {
  const ext = getFileExtension(filename);
  return ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext);
}

/**
 * Validate a single file
 */
function validateFile(file: File): { valid: boolean; error?: string } {
  // Check size
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `Файл "${file.name}" слишком большой (${formatFileSize(file.size)} > ${formatFileSize(MAX_FILE_SIZE)})`,
    };
  }

  // Check extension
  const ext = getFileExtension(file.name);
  if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      error: `Файл "${file.name}" имеет неподдерживаемый тип (.${ext}). Разрешены: ${ALLOWED_EXTENSIONS.join(', ')}`,
    };
  }

  return { valid: true };
}

/**
 * Material Submission Form Component
 */
export const SubmissionForm: React.FC<SubmissionFormProps> = ({
  materialId,
  materialTitle = 'материал',
  onSuccess,
  onCancel,
  className = '',
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<SubmissionFormData>({
    resolver: zodResolver(submissionSchema),
    mode: 'onChange',
    defaultValues: {
      notes: '',
    },
  });

  const notes = watch('notes');

  // Load draft from localStorage on mount
  useEffect(() => {
    try {
      const draft = localStorage.getItem(`${DRAFT_STORAGE_KEY}_${materialId}`);
      if (draft) {
        const parsed = JSON.parse(draft);
        if (parsed.notes) {
          // Reset form with draft data
          reset({ notes: parsed.notes });
        }
      }
    } catch (error) {
      logger.warn('Failed to load draft:', error);
    }
  }, [materialId, reset]);

  // Auto-save draft to localStorage
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        localStorage.setItem(
          `${DRAFT_STORAGE_KEY}_${materialId}`,
          JSON.stringify({ notes })
        );
      } catch (error) {
        logger.warn('Failed to save draft:', error);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [notes, materialId]);

  // Calculate total file size
  const totalSize = files.reduce((sum, f) => sum + f.file.size, 0);
  const remainingSize = MAX_TOTAL_SIZE - totalSize;
  const canAddMoreFiles = files.length < MAX_FILES && remainingSize > 0;

  // Handle file input change
  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newFiles = Array.from(e.target.files || []);
    addFiles(newFiles);
  };

  // Add files with validation
  const addFiles = (newFiles: File[]) => {
    const validationErrors: string[] = [];

    newFiles.forEach((file) => {
      // Check total count
      if (files.length >= MAX_FILES) {
        validationErrors.push(`Максимум ${MAX_FILES} файлов`);
        return;
      }

      // Check total size
      if (totalSize + file.size > MAX_TOTAL_SIZE) {
        validationErrors.push(
          `Файл "${file.name}" превышает оставшееся место (${formatFileSize(remainingSize)} осталось)`
        );
        return;
      }

      // Validate individual file
      const validation = validateFile(file);
      if (!validation.valid) {
        validationErrors.push(validation.error || 'Ошибка валидации файла');
        return;
      }

      // Add file
      const fileId = `${Date.now()}_${Math.random()}`;
      const uploadedFile: UploadedFile = {
        id: fileId,
        file,
      };

      // Create preview for images
      if (isImageFile(file.name)) {
        const reader = new FileReader();
        reader.onloadend = () => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileId ? { ...f, preview: reader.result as string } : f
            )
          );
        };
        reader.onerror = () => {
          logger.error('Failed to read file for preview:', reader.error);
        };
        reader.readAsDataURL(file);
      }

      setFiles((prev) => [...prev, uploadedFile]);
    });

    if (validationErrors.length > 0) {
      validationErrors.forEach((error) => toast.error(error));
    }

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Remove file
  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  // Handle drag and drop
  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (!canAddMoreFiles) {
      toast.error('Максимальное количество файлов или размер достигнут');
      return;
    }

    const droppedFiles = Array.from(e.dataTransfer.files || []);
    addFiles(droppedFiles);
  };

  // Handle form submission
  const onSubmit = async (data: SubmissionFormData) => {
    // Validate that at least one of file or notes is provided
    if (files.length === 0 && !data.notes.trim()) {
      toast.error('Пожалуйста, добавьте хотя бы один файл или напишите заметку');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const formData = new FormData();
      formData.append('material_id', materialId.toString());
      formData.append('submission_text', data.notes);

      // Add files
      files.forEach((uploadedFile, index) => {
        formData.append(`files`, uploadedFile.file);
      });

      logger.debug('Submitting form with files:', {
        fileCount: files.length,
        totalSize: formatFileSize(totalSize),
        notesLength: data.notes.length,
      });

      const response = await apiClient.request('/submissions/submit_answer/', {
        method: 'POST',
        data: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data) {
        // Success - clear draft and reset form
        try {
          localStorage.removeItem(`${DRAFT_STORAGE_KEY}_${materialId}`);
        } catch (error) {
          logger.warn('Failed to clear draft:', error);
        }

        // Reset form state
        setFiles([]);
        reset({ notes: '' });

        // Show success message
        const submissionId = response.data?.id || response.data?.submission_id;
        toast.success(
          submissionId
            ? `Ответ успешно отправлен! ID: ${submissionId}`
            : 'Ответ успешно отправлен преподавателю'
        );

        // Call success callback
        if (onSuccess) {
          onSuccess(submissionId);
        }
      } else {
        throw new Error(response.error || 'Ошибка отправки ответа');
      }
    } catch (error: unknown) {
      logger.error('Submission error:', error);

      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Произошла ошибка при отправке ответа';

      setSubmitError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Send className="w-5 h-5" />
          Отправить ответ
        </CardTitle>
        <CardDescription>
          Отправка ответа на материал: <strong>{materialTitle}</strong>
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Error Alert */}
          {submitError && (
            <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-red-900 dark:text-red-200 text-sm">
                  Ошибка отправки
                </h3>
                <p className="text-red-800 dark:text-red-300 text-sm mt-1">
                  {submitError}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSubmitError(null)}
                className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* File Upload Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-base font-semibold">Файлы (необязательно)</Label>
              <span className="text-xs text-muted-foreground">
                {files.length}/{MAX_FILES} файлов
              </span>
            </div>

            {/* Drag and Drop Zone */}
            <div
              onDragEnter={handleDragEnter}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={cn(
                'relative border-2 border-dashed rounded-lg p-8 transition-all',
                isDragging
                  ? 'border-primary bg-primary/5'
                  : 'border-muted-foreground/20 hover:border-muted-foreground/40',
                !canAddMoreFiles && 'opacity-50 cursor-not-allowed'
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileInputChange}
                accept={ALLOWED_EXTENSIONS.map((ext) => `.${ext}`).join(',')}
                className="hidden"
                disabled={!canAddMoreFiles}
              />

              <div className="flex flex-col items-center justify-center gap-3 text-center">
                <div
                  className={cn(
                    'p-3 rounded-full',
                    isDragging ? 'bg-primary text-white' : 'bg-muted text-muted-foreground'
                  )}
                >
                  <Upload className="w-6 h-6" />
                </div>
                <div>
                  <p className="font-semibold text-foreground">
                    {isDragging ? 'Отпустите файлы здесь' : 'Перетащите файлы сюда'}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    или{' '}
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-primary hover:underline font-medium"
                      disabled={!canAddMoreFiles}
                    >
                      выберите файлы
                    </button>
                  </p>
                </div>
              </div>
            </div>

            {/* File Upload Info */}
            <div className="text-xs text-muted-foreground space-y-1">
              <p>Максимум {MAX_FILES} файлов по {formatFileSize(MAX_FILE_SIZE)} каждый</p>
              <p>
                Общий размер:{' '}
                <span className={cn(remainingSize < MAX_FILE_SIZE / 2 && 'text-orange-600 dark:text-orange-400')}>
                  {formatFileSize(totalSize)}/{formatFileSize(MAX_TOTAL_SIZE)}
                </span>
              </p>
              <p>Поддерживаемые форматы: {ALLOWED_EXTENSIONS.join(', ')}</p>
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="space-y-2 mt-4">
                <Label className="text-sm font-medium">Выбранные файлы:</Label>
                <div className="space-y-2">
                  {files.map((uploadedFile) => (
                    <div
                      key={uploadedFile.id}
                      className="flex items-center gap-3 p-3 border rounded-lg bg-muted/50 hover:bg-muted/70 transition-colors"
                    >
                      {/* File Preview/Icon */}
                      <div className="flex-shrink-0">
                        {uploadedFile.preview ? (
                          <img
                            src={uploadedFile.preview}
                            alt={uploadedFile.file.name}
                            className="w-12 h-12 object-cover rounded"
                          />
                        ) : (
                          <div className="w-12 h-12 flex items-center justify-center bg-muted rounded">
                            <FileText className="w-6 h-6 text-muted-foreground" />
                          </div>
                        )}
                      </div>

                      {/* File Info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {uploadedFile.file.name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatFileSize(uploadedFile.file.size)}
                        </p>
                      </div>

                      {/* Remove Button */}
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeFile(uploadedFile.id)}
                        className="flex-shrink-0"
                        disabled={isSubmitting}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Notes Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="notes" className="text-base font-semibold">
                Заметки (необязательно)
              </Label>
              <span className={cn('text-xs', notes.length > 4500 && 'text-orange-600 dark:text-orange-400')}>
                {notes.length}/5000
              </span>
            </div>

            <Textarea
              id="notes"
              placeholder="Введите заметки, комментарии или текстовый ответ..."
              {...register('notes')}
              rows={6}
              className="resize-none"
              disabled={isSubmitting}
            />

            {errors.notes && (
              <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
                <AlertCircle className="w-4 h-4" />
                <span>{errors.notes.message}</span>
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              Максимум 5000 символов. Это поле опционально.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 justify-end pt-4 border-t">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                Отмена
              </Button>
            )}

            <Button
              type="submit"
              disabled={
                isSubmitting ||
                (files.length === 0 && !notes.trim())
              }
              className="gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Отправка...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Отправить ответ
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default SubmissionForm;
