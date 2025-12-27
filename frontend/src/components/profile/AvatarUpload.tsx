import { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { toast } from 'sonner';
import { Upload, X, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AvatarUploadProps {
  currentAvatar?: string | null;
  onAvatarUpload: (file: File) => Promise<void>;
  isLoading?: boolean;
  fallbackInitials?: string;
}

/**
 * Компонент для загрузки и предпросмотра аватара
 * Поддерживает валидацию файла и отображение текущего аватара
 */
export const AvatarUpload = ({
  currentAvatar,
  onAvatarUpload,
  isLoading = false,
  fallbackInitials = 'АА',
}: AvatarUploadProps) => {
  const [preview, setPreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
  const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

  const validateFile = useCallback((file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'Разрешены только JPEG, PNG и WebP файлы';
    }

    if (file.size > MAX_FILE_SIZE) {
      return 'Размер файла не должен превышать 5MB';
    }

    return null;
  }, []);

  const handleFileSelect = useCallback(
    async (file: File) => {
      setUploadError(null);

      const error = validateFile(file);
      if (error) {
        setUploadError(error);
        toast.error(error);
        return;
      }

      try {
        // Создаём preview
        const reader = new FileReader();
        reader.onload = (e) => {
          setPreview(e.target?.result as string);
        };
        reader.readAsDataURL(file);

        // Загружаем файл
        await onAvatarUpload(file);
        toast.success('Аватар успешно загружен');
        setPreview(null);
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : 'Ошибка при загрузке аватара';
        setUploadError(errorMsg);
        toast.error(errorMsg);
        setPreview(null);
      }
    },
    [onAvatarUpload, validateFile]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleClearPreview = () => {
    setPreview(null);
    setUploadError(null);
  };

  const displayImage = preview || currentAvatar;
  const showFallback = !displayImage;

  return (
    <Card className="w-full">
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Текущий аватар или preview */}
          <div className="flex justify-center">
            {showFallback ? (
              <div
                className="w-48 h-48 rounded-full bg-gradient-to-br from-blue-400 to-purple-500
                  flex items-center justify-center text-white text-4xl font-bold shadow-lg"
                role="img"
                aria-label={`Аватар с инициалами ${fallbackInitials}`}
              >
                {fallbackInitials}
              </div>
            ) : (
              <div className="relative">
                <img
                  src={displayImage}
                  alt="Аватар"
                  className="w-48 h-48 rounded-full object-cover shadow-lg border-4 border-gray-100"
                />
                {preview && (
                  <div
                    className="absolute inset-0 rounded-full bg-black/20 flex items-center justify-center"
                    aria-live="polite"
                  >
                    <Check className="w-12 h-12 text-white" />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Зона для перетаскивания файла */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClick}
            className={cn(
              'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
              isDragging
                ? 'border-blue-500 bg-blue-50'
                : uploadError
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300 hover:border-gray-400 bg-gray-50 hover:bg-gray-100'
            )}
            role="button"
            tabIndex={0}
            aria-label="Зона для загрузки изображения"
            aria-describedby={uploadError ? 'avatar-error' : undefined}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                handleClick();
              }
            }}
          >
            <Upload className="w-8 h-8 mx-auto mb-2 text-gray-500" />
            <p className="text-sm text-gray-600 mb-1">
              Перетащите изображение сюда или нажмите для выбора
            </p>
            <p className="text-xs text-gray-500">
              JPG, PNG, WebP (макс. 5MB)
            </p>
          </div>

          {/* Сообщение об ошибке */}
          {uploadError && (
            <div
              id="avatar-error"
              className="text-sm text-red-600 bg-red-50 p-3 rounded-md"
              role="alert"
            >
              {uploadError}
            </div>
          )}

          {/* Кнопки действий */}
          <div className="flex gap-2 justify-center">
            <Button type="button"
              onClick={handleClick}
              disabled={isLoading}
              aria-label="Загрузить аватар"
            >
              <Upload className="w-4 h-4 mr-2" />
              {isLoading ? 'Загрузка...' : 'Выбрать файл'}
            </Button>

            {preview && (
              <Button type="button"
                variant="outline"
                onClick={handleClearPreview}
                disabled={isLoading}
                aria-label="Отменить выбор аватара"
              >
                <X className="w-4 h-4 mr-2" />
                Отменить
              </Button>
            )}
          </div>

          {/* Скрытое input для файла */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleChange}
            className="hidden"
            aria-label="Выбор файла аватара"
            disabled={isLoading}
          />

          {/* Подсказка */}
          <p className="text-xs text-gray-500 text-center">
            Загруженное изображение будет обрезано квадратом (1:1)
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

export default AvatarUpload;
