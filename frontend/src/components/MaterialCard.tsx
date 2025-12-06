import { useState } from "react";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  BookOpen, 
  Download, 
  Eye, 
  Play, 
  FileText, 
  Presentation, 
  Video, 
  File, 
  CheckCircle2,
  Clock,
  User,
  MessageCircle,
  Share2,
  Edit,
  Trash2,
  Users
} from "lucide-react";
import { toast } from "sonner";

export interface Material {
  id: number;
  title: string;
  description: string;
  content: string;
  type: 'lesson' | 'presentation' | 'video' | 'document' | 'test' | 'homework';
  status: 'draft' | 'active' | 'archived';
  subject: {
    id: number;
    name: string;
    color: string;
  };
  author: {
    id: number;
    first_name: string;
    last_name: string;
  };
  file?: string;
  video_url?: string;
  difficulty_level: number;
  tags: string[];
  created_at: string;
  published_at?: string;
  progress?: {
    is_completed: boolean;
    progress_percentage: number;
    time_spent: number;
    last_accessed: string;
  };
  assigned_count?: number;
  comments_count?: number;
}

interface MaterialCardProps {
  material: Material;
  userRole: 'student' | 'teacher' | 'parent';
  onView?: (material: Material) => void;
  onDownload?: (material: Material) => void;
  onEdit?: (material: Material) => void;
  onDelete?: (material: Material) => void;
  onAssign?: (material: Material) => void;
  onProgressUpdate?: (material: Material, progress: number) => void;
  className?: string;
}

const typeIcons = {
  lesson: BookOpen,
  presentation: Presentation,
  video: Video,
  document: File,
  test: FileText,
  homework: FileText,
};

const typeLabels = {
  lesson: 'Урок',
  presentation: 'Презентация',
  video: 'Видео',
  document: 'Документ',
  test: 'Тест',
  homework: 'Домашнее задание',
};

const statusLabels = {
  draft: 'Черновик',
  active: 'Активно',
  archived: 'Архив',
};

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  active: 'bg-green-100 text-green-800',
  archived: 'bg-orange-100 text-orange-800',
};

export const MaterialCard = ({
  material,
  userRole,
  onView,
  onDownload,
  onEdit,
  onDelete,
  onAssign,
  onProgressUpdate,
  className = ""
}: MaterialCardProps) => {
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(material.progress?.progress_percentage || 0);

  const TypeIcon = typeIcons[material.type];
  const typeLabel = typeLabels[material.type];
  const statusLabel = statusLabels[material.status];
  const statusColor = statusColors[material.status];

  const handleView = async () => {
    if (onView) {
      setIsLoading(true);
      try {
        await onView(material);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleDownload = async () => {
    if (onDownload && material.file) {
      setIsLoading(true);
      try {
        await onDownload(material);
        toast.success("Файл загружен");
      } catch (error) {
        toast.error("Ошибка при загрузке файла");
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleProgressUpdate = async (newProgress: number) => {
    if (onProgressUpdate) {
      setIsLoading(true);
      try {
        await onProgressUpdate(material, newProgress);
        setProgress(newProgress);
        toast.success("Прогресс обновлен");
      } catch (error) {
        toast.error("Ошибка при обновлении прогресса");
      } finally {
        setIsLoading(false);
      }
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatTime = (minutes: number) => {
    if (minutes < 60) {
      return `${minutes} мин`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}ч ${mins}мин`;
  };

  const getDifficultyColor = (level: number) => {
    if (level <= 2) return 'text-green-600';
    if (level <= 3) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getDifficultyText = (level: number) => {
    if (level <= 2) return 'Легкий';
    if (level <= 3) return 'Средний';
    return 'Сложный';
  };

  return (
    <Card className={`group hover:shadow-lg transition-all duration-200 ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-lg" style={{ backgroundColor: material.subject.color + '20' }}>
              <TypeIcon className="h-5 w-5" style={{ color: material.subject.color }} />
            </div>
            <div>
              <Badge variant="secondary" className="text-xs">
                {typeLabel}
              </Badge>
              <Badge 
                variant="outline" 
                className={`text-xs ml-1 ${statusColor}`}
              >
                {statusLabel}
              </Badge>
            </div>
          </div>
          
          <div className="flex items-center space-x-1">
            <span className={`text-sm font-medium ${getDifficultyColor(material.difficulty_level)}`}>
              {getDifficultyText(material.difficulty_level)}
            </span>
            <div className="flex space-x-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className={`w-1 h-4 rounded ${
                    i < material.difficulty_level ? 'bg-current' : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>

        <CardTitle className="text-lg leading-tight line-clamp-2">
          {material.title}
        </CardTitle>

        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
          <div className="flex items-center space-x-1">
            <User className="h-4 w-4" />
            <span>{material.author.first_name} {material.author.last_name}</span>
          </div>
          <div className="flex items-center space-x-1">
            <Clock className="h-4 w-4" />
            <span>{formatDate(material.created_at)}</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        {material.description && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
            {material.description}
          </p>
        )}

        {/* Progress for students */}
        {userRole === 'student' && material.progress && (
          <div className="space-y-2 mb-3">
            <div className="flex justify-between text-sm">
              <span>Прогресс изучения</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Время: {formatTime(material.progress.time_spent)}</span>
              {material.progress.is_completed && (
                <span className="flex items-center text-green-600">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Завершено
                </span>
              )}
            </div>
          </div>
        )}

        {/* Tags */}
        {material.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {material.tags.slice(0, 3).map((tag, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
            {material.tags.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{material.tags.length - 3}
              </Badge>
            )}
          </div>
        )}

        {/* Stats for teachers */}
        {userRole === 'teacher' && (
          <div className="flex items-center space-x-4 text-sm text-muted-foreground">
            {material.assigned_count !== undefined && (
              <div className="flex items-center space-x-1">
                <Users className="h-4 w-4" />
                <span>{material.assigned_count} назначено</span>
              </div>
            )}
            {material.comments_count !== undefined && (
              <div className="flex items-center space-x-1">
                <MessageCircle className="h-4 w-4" />
                <span>{material.comments_count} комментариев</span>
              </div>
            )}
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-0">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center space-x-2">
            {/* View button */}
            <Button type="button"
              variant="outline"
              size="sm"
              onClick={handleView}
              disabled={isLoading}
              className="flex items-center space-x-1"
            >
              <Eye className="h-4 w-4" />
              <span>Просмотр</span>
            </Button>

            {/* Download button for files */}
            {material.file && (
              <Button type="button"
                variant="outline"
                size="sm"
                onClick={handleDownload}
                disabled={isLoading}
                className="flex items-center space-x-1"
              >
                <Download className="h-4 w-4" />
                <span>Скачать</span>
              </Button>
            )}

            {/* Video play button */}
            {material.video_url && (
              <Button type="button"
                variant="outline"
                size="sm"
                onClick={handleView}
                disabled={isLoading}
                className="flex items-center space-x-1"
              >
                <Play className="h-4 w-4" />
                <span>Смотреть</span>
              </Button>
            )}
          </div>

          {/* Role-specific actions */}
          <div className="flex items-center space-x-1">
            {userRole === 'teacher' && (
              <>
                <Button type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit?.(material)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => onAssign?.(material)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Share2 className="h-4 w-4" />
                </Button>
                <Button type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => onDelete?.(material)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </>
            )}

            {userRole === 'student' && !material.progress?.is_completed && (
              <Button type="button"
                variant="default"
                size="sm"
                onClick={() => handleProgressUpdate(Math.min(progress + 25, 100))}
                disabled={isLoading}
                className="gradient-primary shadow-glow hover:opacity-90 transition-opacity"
              >
                <CheckCircle2 className="h-4 w-4 mr-1" />
                Отметить прогресс
              </Button>
            )}
          </div>
        </div>
      </CardFooter>
    </Card>
  );
};
