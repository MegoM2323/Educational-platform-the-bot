import { useState } from "react";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  FileText, 
  User, 
  Calendar, 
  TrendingUp, 
  TrendingDown,
  Award,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  Eye,
  Star,
  Users,
  BookOpen,
  Target,
  MessageSquare
} from "lucide-react";
import { toast } from "sonner";

export interface StudentReport {
  id: number;
  title: string;
  description: string;
  report_type: 'progress' | 'behavior' | 'achievement' | 'attendance' | 'performance' | 'custom';
  status: 'draft' | 'sent' | 'read' | 'archived';
  teacher: {
    id: number;
    first_name: string;
    last_name: string;
  };
  student: {
    id: number;
    first_name: string;
    last_name: string;
  };
  parent?: {
    id: number;
    first_name: string;
    last_name: string;
  };
  period_start: string;
  period_end: string;
  content: Record<string, any>;
  overall_grade?: string;
  progress_percentage: number;
  attendance_percentage: number;
  behavior_rating: number;
  recommendations?: string;
  concerns?: string;
  achievements?: string;
  attachment?: string;
  created_at: string;
  sent_at?: string;
  read_at?: string;
}

interface ReportCardProps {
  report: StudentReport;
  userRole: 'teacher' | 'parent' | 'student';
  onView?: (report: StudentReport) => void;
  onDownload?: (report: StudentReport) => void;
  onMarkAsRead?: (report: StudentReport) => void;
  onEdit?: (report: StudentReport) => void;
  onDelete?: (report: StudentReport) => void;
  onSend?: (report: StudentReport) => void;
  className?: string;
}

const reportTypeConfig = {
  progress: {
    label: 'Прогресс',
    icon: TrendingUp,
    color: 'bg-blue-100 text-blue-800',
  },
  behavior: {
    label: 'Поведение',
    icon: Users,
    color: 'bg-green-100 text-green-800',
  },
  achievement: {
    label: 'Достижения',
    icon: Award,
    color: 'bg-yellow-100 text-yellow-800',
  },
  attendance: {
    label: 'Посещаемость',
    icon: Calendar,
    color: 'bg-purple-100 text-purple-800',
  },
  performance: {
    label: 'Успеваемость',
    icon: Target,
    color: 'bg-red-100 text-red-800',
  },
  custom: {
    label: 'Пользовательский',
    icon: FileText,
    color: 'bg-gray-100 text-gray-800',
  },
};

const statusConfig = {
  draft: {
    label: 'Черновик',
    color: 'bg-gray-100 text-gray-800',
    icon: Clock,
  },
  sent: {
    label: 'Отправлен',
    color: 'bg-blue-100 text-blue-800',
    icon: CheckCircle2,
  },
  read: {
    label: 'Прочитан',
    color: 'bg-green-100 text-green-800',
    icon: Eye,
  },
  archived: {
    label: 'Архив',
    color: 'bg-orange-100 text-orange-800',
    icon: FileText,
  },
};

export const ReportCard = ({
  report,
  userRole,
  onView,
  onDownload,
  onMarkAsRead,
  onEdit,
  onDelete,
  onSend,
  className = ""
}: ReportCardProps) => {
  const [isLoading, setIsLoading] = useState(false);

  const typeConfig = reportTypeConfig[report.report_type];
  const statusConfigItem = statusConfig[report.status];
  const TypeIcon = typeConfig.icon;
  const StatusIcon = statusConfigItem.icon;

  const handleView = async () => {
    if (onView) {
      setIsLoading(true);
      try {
        await onView(report);
        if (userRole === 'parent' && report.status === 'sent' && onMarkAsRead) {
          await onMarkAsRead(report);
        }
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleDownload = async () => {
    if (onDownload && report.attachment) {
      setIsLoading(true);
      try {
        await onDownload(report);
        toast.success("Отчет загружен");
      } catch (error) {
        toast.error("Ошибка при загрузке отчета");
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

  const formatDateRange = (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    
    if (startDate.getMonth() === endDate.getMonth()) {
      return `${startDate.getDate()}-${endDate.getDate()} ${startDate.toLocaleDateString('ru-RU', { month: 'long' })}`;
    }
    
    return `${formatDate(start)} - ${formatDate(end)}`;
  };

  const getGradeColor = (grade?: string) => {
    if (!grade) return 'text-gray-600';
    
    const numGrade = parseFloat(grade);
    if (numGrade >= 4.5) return 'text-green-600';
    if (numGrade >= 3.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getBehaviorRating = (rating: number) => {
    if (rating >= 8) return { label: 'Отлично', color: 'text-green-600' };
    if (rating >= 6) return { label: 'Хорошо', color: 'text-yellow-600' };
    if (rating >= 4) return { label: 'Удовлетворительно', color: 'text-orange-600' };
    return { label: 'Требует внимания', color: 'text-red-600' };
  };

  const behaviorRating = getBehaviorRating(report.behavior_rating);

  return (
    <Card className={`group hover:shadow-lg transition-all duration-200 ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-lg bg-blue-50">
              <TypeIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <Badge className={typeConfig.color}>
                {typeConfig.label}
              </Badge>
              <Badge 
                variant="outline" 
                className={`ml-1 ${statusConfigItem.color}`}
              >
                <StatusIcon className="h-3 w-3 mr-1" />
                {statusConfigItem.label}
              </Badge>
            </div>
          </div>
          
          {report.overall_grade && (
            <div className={`text-2xl font-bold ${getGradeColor(report.overall_grade)}`}>
              {report.overall_grade}
            </div>
          )}
        </div>

        <CardTitle className="text-lg leading-tight line-clamp-2">
          {report.title}
        </CardTitle>

        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
          <div className="flex items-center space-x-1">
            <User className="h-4 w-4" />
            <span>
              {userRole === 'teacher' 
                ? `${report.student.first_name} ${report.student.last_name}`
                : `${report.teacher.first_name} ${report.teacher.last_name}`
              }
            </span>
          </div>
          <div className="flex items-center space-x-1">
            <Calendar className="h-4 w-4" />
            <span>{formatDateRange(report.period_start, report.period_end)}</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        {report.description && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
            {report.description}
          </p>
        )}

        {/* Progress and Metrics */}
        <div className="space-y-3">
          {/* Progress */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Прогресс</span>
              <span>{report.progress_percentage}%</span>
            </div>
            <Progress value={report.progress_percentage} className="h-2" />
          </div>

          {/* Attendance */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Посещаемость</span>
              <span>{report.attendance_percentage}%</span>
            </div>
            <Progress value={report.attendance_percentage} className="h-2" />
          </div>

          {/* Behavior Rating */}
          <div className="flex items-center justify-between text-sm">
            <span>Поведение</span>
            <div className="flex items-center space-x-2">
              <div className="flex space-x-1">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star
                    key={i}
                    className={`h-4 w-4 ${
                      i < Math.floor(report.behavior_rating / 2) 
                        ? 'text-yellow-400 fill-current' 
                        : 'text-gray-300'
                    }`}
                  />
                ))}
              </div>
              <span className={`font-medium ${behaviorRating.color}`}>
                {behaviorRating.label}
              </span>
            </div>
          </div>
        </div>

        {/* Key Highlights */}
        {(report.achievements || report.concerns || report.recommendations) && (
          <div className="mt-4 space-y-2">
            {report.achievements && (
              <div className="flex items-start space-x-2 text-sm">
                <Award className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-medium text-yellow-800">Достижения:</span>
                  <p className="text-muted-foreground line-clamp-2">{report.achievements}</p>
                </div>
              </div>
            )}
            
            {report.concerns && (
              <div className="flex items-start space-x-2 text-sm">
                <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-medium text-red-800">Обеспокоенности:</span>
                  <p className="text-muted-foreground line-clamp-2">{report.concerns}</p>
                </div>
              </div>
            )}
            
            {report.recommendations && (
              <div className="flex items-start space-x-2 text-sm">
                <Target className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-medium text-blue-800">Рекомендации:</span>
                  <p className="text-muted-foreground line-clamp-2">{report.recommendations}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Timestamps */}
        <div className="mt-4 pt-3 border-t space-y-1 text-xs text-muted-foreground">
          <div className="flex justify-between">
            <span>Создан:</span>
            <span>{formatDate(report.created_at)}</span>
          </div>
          {report.sent_at && (
            <div className="flex justify-between">
              <span>Отправлен:</span>
              <span>{formatDate(report.sent_at)}</span>
            </div>
          )}
          {report.read_at && (
            <div className="flex justify-between">
              <span>Прочитан:</span>
              <span>{formatDate(report.read_at)}</span>
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className="pt-0">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center space-x-2">
            {/* View button */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleView}
              disabled={isLoading}
              className="flex items-center space-x-1"
            >
              <Eye className="h-4 w-4" />
              <span>Просмотр</span>
            </Button>

            {/* Download button for attachments */}
            {report.attachment && (
              <Button
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
          </div>

          {/* Role-specific actions */}
          <div className="flex items-center space-x-1">
            {userRole === 'teacher' && (
              <>
                {report.status === 'draft' && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEdit?.(report)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <FileText className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => onSend?.(report)}
                      className="gradient-primary shadow-glow hover:opacity-90 transition-opacity"
                    >
                      <MessageSquare className="h-4 w-4 mr-1" />
                      Отправить
                    </Button>
                  </>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDelete?.(report)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-red-600 hover:text-red-700"
                >
                  <FileText className="h-4 w-4" />
                </Button>
              </>
            )}

            {userRole === 'parent' && report.status === 'sent' && !report.read_at && (
              <Button
                variant="default"
                size="sm"
                onClick={() => onMarkAsRead?.(report)}
                className="gradient-primary shadow-glow hover:opacity-90 transition-opacity"
              >
                <CheckCircle2 className="h-4 w-4 mr-1" />
                Отметить как прочитанный
              </Button>
            )}
          </div>
        </div>
      </CardFooter>
    </Card>
  );
};
