import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, Play, AlertCircle } from 'lucide-react';
import type { ElementTypeProps, VideoContent, VideoAnswer } from '@/types/knowledgeGraph';

export const Video: React.FC<ElementTypeProps> = ({
  element,
  progress,
  onSubmit,
  isLoading = false,
  readOnly = false,
}) => {
  const content = element.content as VideoContent;
  const previousAnswer = progress?.answer as VideoAnswer | null;

  const [watchedUntil, setWatchedUntil] = useState<number>(previousAnswer?.watched_until || 0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string>('');
  const [videoError, setVideoError] = useState<string>('');

  const videoRef = useRef<HTMLVideoElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const isCompleted = progress?.status === 'completed';
  const isDisabled = isLoading || isCompleted || readOnly;

  useEffect(() => {
    if (previousAnswer?.watched_until) {
      setWatchedUntil(previousAnswer.watched_until);
    }
  }, [previousAnswer]);

  // Определение типа видео по URL
  const getVideoType = (url: string): 'youtube' | 'vimeo' | 'file' | 'unknown' => {
    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      return 'youtube';
    }
    if (url.includes('vimeo.com')) {
      return 'vimeo';
    }
    if (url.match(/\.(mp4|webm|ogg)$/i)) {
      return 'file';
    }
    return 'unknown';
  };

  // Извлечение YouTube ID
  const getYouTubeId = (url: string): string | null => {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return match && match[2].length === 11 ? match[2] : null;
  };

  // Извлечение Vimeo ID
  const getVimeoId = (url: string): string | null => {
    const regExp = /vimeo.com\/(\d+)/;
    const match = url.match(regExp);
    return match ? match[1] : null;
  };

  const videoType = getVideoType(content.url);

  // Обработка прогресса просмотра для HTML5 видео
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const currentTime = Math.floor(videoRef.current.currentTime);
      if (currentTime > watchedUntil) {
        setWatchedUntil(currentTime);
      }
    }
  };

  const handleVideoEnd = () => {
    if (videoRef.current) {
      const duration = Math.floor(videoRef.current.duration);
      setWatchedUntil(duration);
    }
  };

  const handleMarkAsCompleted = async () => {
    setError('');

    // Проверка минимального времени просмотра (80% видео)
    const minWatchTime = content.duration_seconds ? content.duration_seconds * 0.8 : 0;
    if (minWatchTime > 0 && watchedUntil < minWatchTime) {
      setError(`Просмотрите минимум 80% видео для завершения (${Math.floor(minWatchTime / 60)} мин)`);
      return;
    }

    try {
      await onSubmit({ watched_until: watchedUntil });
    } catch (err) {
      setError('Ошибка при сохранении. Попробуйте ещё раз.');
    }
  };

  const renderVideo = () => {
    switch (videoType) {
      case 'youtube': {
        const videoId = getYouTubeId(content.url);
        if (!videoId) {
          setVideoError('Некорректный YouTube URL');
          return null;
        }

        return (
          <div className="relative w-full pb-[56.25%] rounded-lg overflow-hidden bg-black">
            <iframe
              ref={iframeRef}
              className="absolute top-0 left-0 w-full h-full"
              src={`https://www.youtube.com/embed/${videoId}?enablejsapi=1`}
              title={content.title || element.title}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        );
      }

      case 'vimeo': {
        const videoId = getVimeoId(content.url);
        if (!videoId) {
          setVideoError('Некорректный Vimeo URL');
          return null;
        }

        return (
          <div className="relative w-full pb-[56.25%] rounded-lg overflow-hidden bg-black">
            <iframe
              ref={iframeRef}
              className="absolute top-0 left-0 w-full h-full"
              src={`https://player.vimeo.com/video/${videoId}`}
              title={content.title || element.title}
              allow="autoplay; fullscreen; picture-in-picture"
              allowFullScreen
            />
          </div>
        );
      }

      case 'file': {
        return (
          <div className="rounded-lg overflow-hidden bg-black">
            <video
              ref={videoRef}
              className="w-full"
              controls
              onTimeUpdate={handleTimeUpdate}
              onEnded={handleVideoEnd}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            >
              <source src={content.url} type="video/mp4" />
              <source src={content.url} type="video/webm" />
              <source src={content.url} type="video/ogg" />
              Ваш браузер не поддерживает воспроизведение видео.
            </video>
          </div>
        );
      }

      default: {
        setVideoError('Неподдерживаемый формат видео');
        return null;
      }
    }
  };

  return (
    <div className="space-y-4">
      {/* Заголовок и описание видео */}
      {content.title && (
        <div>
          <h3 className="text-lg font-semibold text-foreground">{content.title}</h3>
          {content.description && (
            <p className="text-sm text-muted-foreground mt-1">{content.description}</p>
          )}
        </div>
      )}

      {/* Видео плеер */}
      {videoError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{videoError}</AlertDescription>
        </Alert>
      ) : (
        renderVideo()
      )}

      {/* Прогресс просмотра */}
      {watchedUntil > 0 && !isCompleted && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Просмотрено:</span>
            <Badge variant="secondary">
              {Math.floor(watchedUntil / 60)}:{(watchedUntil % 60).toString().padStart(2, '0')}
              {content.duration_seconds && ` / ${Math.floor(content.duration_seconds / 60)}:${(content.duration_seconds % 60).toString().padStart(2, '0')}`}
            </Badge>
          </div>

          {content.duration_seconds && (
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all"
                style={{
                  width: `${Math.min((watchedUntil / content.duration_seconds) * 100, 100)}%`,
                }}
              />
            </div>
          )}
        </div>
      )}

      {/* Ошибки */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Кнопка завершения */}
      {!isCompleted && !readOnly && (
        <Button
          type="button"
          onClick={handleMarkAsCompleted}
          disabled={isDisabled || watchedUntil === 0}
          className="w-full"
        >
          {isLoading ? 'Сохранение...' : 'Отметить как просмотренное'}
        </Button>
      )}

      {isCompleted && (
        <Alert className="bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-sm text-green-800 dark:text-green-200">
            Видео просмотрено!
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};
