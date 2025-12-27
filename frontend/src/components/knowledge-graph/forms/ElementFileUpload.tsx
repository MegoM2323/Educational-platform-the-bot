import React, { useState, useCallback } from 'react';
import { Upload, X, Download, Loader2 } from 'lucide-react';
import { elementFilesAPI, ElementFile } from '@/integrations/api/elementFilesAPI';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';

interface ElementFileUploadProps {
  elementId: number;
  onFilesChange?: (files: ElementFile[]) => void;
  disabled?: boolean;
}

/**
 * Компонент для загрузки файлов к элементам графа знаний
 * Поддерживает drag-and-drop, отображение списка файлов, удаление
 */
export const ElementFileUpload: React.FC<ElementFileUploadProps> = ({
  elementId,
  onFilesChange,
  disabled = false,
}) => {
  const [files, setFiles] = useState<ElementFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<Set<string>>(new Set());

  // Загрузить список файлов при монтировании компонента
  React.useEffect(() => {
    loadFiles();
  }, [elementId]);

  const loadFiles = async () => {
    try {
      setIsLoading(true);
      const loadedFiles = await elementFilesAPI.listFiles(elementId);
      setFiles(loadedFiles);
      onFilesChange?.(loadedFiles);
    } catch (error) {
      console.error('Failed to load files:', error);
      toast.error('Ошибка загрузки файлов');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async (file: File) => {
    const uploadId = `${file.name}-${Date.now()}`;

    try {
      setUploadingFiles(prev => new Set(prev).add(uploadId));

      const newFile = await elementFilesAPI.uploadFile(elementId, file);
      const updatedFiles = [newFile, ...files];
      setFiles(updatedFiles);
      onFilesChange?.(updatedFiles);

      toast.success(`Файл "${file.name}" загружен`);
    } catch (error) {
      console.error('Upload failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Ошибка загрузки файла';
      toast.error(errorMessage);
    } finally {
      setUploadingFiles(prev => {
        const updated = new Set(prev);
        updated.delete(uploadId);
        return updated;
      });
    }
  };

  const handleDelete = async (fileId: number, fileName: string) => {
    if (!confirm(`Вы уверены, что хотите удалить файл "${fileName}"?`)) {
      return;
    }

    try {
      await elementFilesAPI.deleteFile(elementId, fileId);
      const updated = files.filter(f => f.id !== fileId);
      setFiles(updated);
      onFilesChange?.(updated);
      toast.success('Файл удален');
    } catch (error) {
      console.error('Delete failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Ошибка удаления файла';
      toast.error(errorMessage);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const droppedFiles = Array.from(e.dataTransfer.files);
    for (const file of droppedFiles) {
      await handleUpload(file);
    }
  };

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;

    const selectedFiles = Array.from(e.target.files);
    for (const file of selectedFiles) {
      await handleUpload(file);
    }

    // Сбросить input для возможности загрузить тот же файл повторно
    e.target.value = '';
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Б';
    const k = 1024;
    const sizes = ['Б', 'КБ', 'МБ', 'ГБ'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isUploading = uploadingFiles.size > 0;

  return (
    <div className="space-y-4">
      {/* Upload Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Зона для загрузки файлов"
        onKeyDown={(e) => {
          if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
            document.getElementById('file-input')?.click();
          }
        }}
      >
        <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
        <p className="text-sm font-medium text-gray-700 mb-1">
          Перетащите файлы сюда или
        </p>
        <label className="inline-block">
          <span className="text-blue-600 hover:underline cursor-pointer">
            выберите файлы
          </span>
          <input
            id="file-input"
            type="file"
            multiple
            onChange={handleFileInput}
            disabled={disabled}
            className="hidden"
            accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.mp4,.zip"
          />
        </label>
        <p className="text-xs text-gray-500 mt-2">
          Максимум 10МБ. Допустимые типы: PDF, DOC, DOCX, TXT, JPG, PNG, MP4, ZIP
        </p>
      </div>

      {/* Upload Progress */}
      {isUploading && (
        <div className="flex items-center justify-center p-3 bg-blue-50 rounded-lg">
          <Loader2 className="w-4 h-4 animate-spin mr-2 text-blue-600" />
          <span className="text-sm text-blue-700">Загрузка файлов...</span>
        </div>
      )}

      {/* Files List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-4 h-4 animate-spin mr-2 text-gray-400" />
          <span className="text-sm text-gray-500">Загрузка файлов...</span>
        </div>
      ) : files.length > 0 ? (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">
            Файлы ({files.length})
          </p>
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="flex-1 min-w-0 mr-4">
                <a
                  href={file.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-blue-600 hover:underline truncate block"
                  title={file.original_filename}
                >
                  {file.original_filename}
                </a>
                <p className="text-xs text-gray-500 mt-1">
                  {formatFileSize(file.file_size)} · {formatDate(file.uploaded_at)}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <a
                  href={file.file_url}
                  download={file.original_filename}
                  className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                  title="Скачать"
                  aria-label={`Скачать ${file.original_filename}`}
                >
                  <Download className="w-4 h-4 text-gray-600" />
                </a>
                <button
                  type="button"
                  onClick={() => handleDelete(file.id, file.original_filename)}
                  disabled={disabled}
                  className="p-1.5 hover:bg-red-100 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="Удалить"
                  aria-label={`Удалить ${file.original_filename}`}
                >
                  <X className="w-4 h-4 text-red-600" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500 text-center py-4">
          Файлы еще не загружены
        </p>
      )}
    </div>
  );
};
