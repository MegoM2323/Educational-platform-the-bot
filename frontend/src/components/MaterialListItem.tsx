import React, { memo } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  BookOpen,
  Download,
  Eye,
  Clock,
  User,
  Send,
  MessageSquare,
  Video,
  Presentation,
  FileText,
  Home,
  TestTube,
} from "lucide-react";
import { LazyImage } from "@/components/LazyImage";

interface Material {
  id: number;
  title: string;
  description: string;
  author_name: string;
  subject_name: string;
  type: string;
  difficulty_level: number;
  created_at: string;
  progress?: {
    is_completed: boolean;
    progress_percentage: number;
    time_spent: number;
  };
  file?: string;
  video_url?: string;
}

interface MaterialListItemProps {
  material: Material;
  index: number;
  onView: (material: Material) => void;
  onSubmit: (material: Material) => void;
  onStatus: (material: Material) => void;
  onDownload: (material: Material) => void;
  onProgress: (materialId: number, progress: number) => void;
}

const typeIcons = {
  lesson: BookOpen,
  presentation: Presentation,
  video: Video,
  document: FileText,
  test: TestTube,
  homework: Home,
};

const typeLabels = {
  lesson: "Урок",
  presentation: "Презентация",
  video: "Видео",
  document: "Документ",
  test: "Тест",
  homework: "Домашнее задание",
};

const getDifficultyColor = (level: number) => {
  if (level <= 2) return "bg-green-100 text-green-800";
  if (level <= 3) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
};

export const MaterialListItem = memo(
  ({
    material,
    onView,
    onSubmit,
    onStatus,
    onDownload,
    onProgress,
  }: MaterialListItemProps) => {
    const TypeIcon =
      typeIcons[material.type as keyof typeof typeIcons] || BookOpen;

    return (
      <Card className="p-6 hover:border-primary transition-colors">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center flex-shrink-0">
            <TypeIcon className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-bold mb-1">{material.title}</h3>
                <p className="text-sm text-muted-foreground flex items-center gap-1">
                  <User className="w-3 h-3" />
                  {material.author_name}
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <Badge
                  variant={
                    material.progress?.is_completed ? "default" : "secondary"
                  }
                >
                  {material.progress?.is_completed ? "Завершено" : "В процессе"}
                </Badge>
                <Badge className={getDifficultyColor(material.difficulty_level)}>
                  Уровень {material.difficulty_level}
                </Badge>
              </div>
            </div>

            <p className="text-sm text-muted-foreground mb-2">
              {material.description}
            </p>

            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
              <span className="font-medium">{material.subject_name}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <TypeIcon className="w-3 h-3" />
                {typeLabels[material.type as keyof typeof typeLabels]}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(material.created_at).toLocaleDateString("ru-RU")}
              </span>
            </div>

            {material.progress && (
              <div className="mb-4">
                <div className="flex justify-between text-xs text-muted-foreground mb-1">
                  <span>Прогресс изучения</span>
                  <span>{material.progress.progress_percentage}%</span>
                </div>
                <Progress
                  value={material.progress.progress_percentage}
                  className="h-2"
                />
                {material.progress.time_spent > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Время изучения: {material.progress.time_spent} мин
                  </p>
                )}
              </div>
            )}

            <div className="flex gap-2 flex-wrap">
              <Button
                type="button"
                size="sm"
                className="flex-1 min-w-[100px]"
                onClick={() => onView(material)}
              >
                <Eye className="w-4 h-4 mr-2" />
                Изучить
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => onSubmit(material)}
              >
                <Send className="w-4 h-4 mr-1" />
                Ответить
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => onStatus(material)}
              >
                <MessageSquare className="w-4 h-4" />
              </Button>
              {material.file && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => onDownload(material)}
                >
                  <Download className="w-4 h-4" />
                </Button>
              )}
              {material.video_url && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => window.open(material.video_url, "_blank")}
                >
                  <Video className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </Card>
    );
  },
  (prevProps, nextProps) => {
    // Кастомное сравнение для оптимизации перерисовок
    return (
      prevProps.material.id === nextProps.material.id &&
      prevProps.material.progress?.progress_percentage ===
        nextProps.material.progress?.progress_percentage &&
      prevProps.material.title === nextProps.material.title
    );
  }
);

MaterialListItem.displayName = "MaterialListItem";
