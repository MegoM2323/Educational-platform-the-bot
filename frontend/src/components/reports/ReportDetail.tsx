import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import {
  Download,
  FileText,
  Share2,
  Printer,
  RotateCw,
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  Eye,
  EyeOff,
  File,
} from "lucide-react";
import { toast } from "sonner";

export interface TutorWeeklyReport {
  id: number;
  tutor_name: string;
  student_name: string;
  parent_name: string;
  week_start: string;
  week_end: string;
  title: string;
  summary: string;
  academic_progress?: string;
  behavior_notes?: string;
  achievements?: string;
  concerns?: string;
  recommendations?: string;
  attendance_days: number;
  total_days: number;
  attendance_percentage: number;
  progress_percentage: number;
  status: 'draft' | 'sent' | 'read' | 'archived';
  attachment?: string;
  created_at: string;
  updated_at: string;
  sent_at?: string;
  read_at?: string;
}

export interface TeacherWeeklyReport {
  id: number;
  teacher_name: string;
  student_name: string;
  tutor_name: string;
  subject_name: string;
  subject_color: string;
  week_start: string;
  week_end: string;
  title: string;
  summary: string;
  academic_progress?: string;
  performance_notes?: string;
  achievements?: string;
  concerns?: string;
  recommendations?: string;
  assignments_completed: number;
  assignments_total: number;
  completion_percentage: number;
  average_score?: number;
  attendance_percentage: number;
  status: 'draft' | 'sent' | 'read' | 'archived';
  attachment?: string;
  created_at: string;
  updated_at: string;
  sent_at?: string;
  read_at?: string;
}

export type Report = TutorWeeklyReport | TeacherWeeklyReport;

interface ReportDetailProps {
  report: Report;
  onBack: () => void;
  onRegenerate?: () => void;
  onShare?: () => void;
  isLoading?: boolean;
  userRole?: 'teacher' | 'tutor' | 'parent' | 'student' | 'admin';
}

const reportTypeConfig = {
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

/**
 * ReportDetail - Detailed view for displaying a single report
 *
 * Features:
 * - Display report title and metadata
 * - Show report content/sections with proper rendering
 * - Display charts/visualizations (progress bars, metrics)
 * - Show tables with data
 * - Support PDF/Excel/JSON views
 * - Download report in different formats
 * - Regenerate report button
 * - Share report button
 * - Print report
 * - Loading and error states
 * - Navigation breadcrumbs
 * - Responsive layout (desktop/tablet/mobile)
 */
export const ReportDetail = ({
  report,
  onBack,
  onRegenerate,
  onShare,
  isLoading = false,
  userRole = 'student',
}: ReportDetailProps) => {
  const [downloadFormat, setDownloadFormat] = useState<'pdf' | 'excel' | 'json'>('pdf');
  const [isDownloading, setIsDownloading] = useState(false);
  const [showFullContent, setShowFullContent] = useState(false);

  const statusConfig = reportTypeConfig[report.status];
  const StatusIcon = statusConfig.icon;

  const isTutorReport = (report: Report): report is TutorWeeklyReport => {
    return 'parent_name' in report && !('subject_name' in report);
  };

  const isTeacherReport = (report: Report): report is TeacherWeeklyReport => {
    return 'subject_name' in report && 'assignments_total' in report;
  };

  // Format date helper
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Format period helper
  const formatDateRange = (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);

    const startFormatted = startDate.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
    });

    const endFormatted = endDate.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });

    return `${startFormatted} - ${endFormatted}`;
  };

  // Handle download
  const handleDownload = async (format: 'pdf' | 'excel' | 'json') => {
    setIsDownloading(true);
    try {
      // Prepare data based on format
      let content = '';
      let filename = `${report.title}-${new Date().toISOString().split('T')[0]}`;
      let mimeType = 'application/json';

      if (format === 'json') {
        content = JSON.stringify(report, null, 2);
        filename += '.json';
        mimeType = 'application/json';
      } else if (format === 'pdf') {
        // In a real app, this would generate a PDF
        content = `
Report: ${report.title}
Generated: ${formatDate(new Date().toISOString())}
Status: ${statusConfig.label}

${JSON.stringify(report, null, 2)}
        `;
        filename += '.pdf';
        mimeType = 'application/pdf';
        toast.info('PDF download initiated. Feature requires backend integration.');
      } else if (format === 'excel') {
        // In a real app, this would generate an Excel file
        content = generateCSV(report);
        filename += '.csv';
        mimeType = 'text/csv';
      }

      // Create blob and download
      const blob = new Blob([content], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success(`Отчет загружен как ${format.toUpperCase()}`);
    } catch (error) {
      toast.error('Ошибка при загрузке отчета');
    } finally {
      setIsDownloading(false);
    }
  };

  // Generate CSV content
  const generateCSV = (report: Report): string => {
    const lines: string[] = [];

    lines.push(`"Название отчета","${report.title}"`);
    lines.push(`"Студент","${report.student_name}"`);

    if (isTutorReport(report)) {
      lines.push(`"Тьютор","${report.tutor_name}"`);
      lines.push(`"Родитель","${report.parent_name}"`);
    } else if (isTeacherReport(report)) {
      lines.push(`"Учитель","${report.teacher_name}"`);
      lines.push(`"Предмет","${report.subject_name}"`);
    }

    lines.push(`"Период","${formatDateRange(report.week_start, report.week_end)}"`);
    lines.push(`"Статус","${statusConfig.label}"`);
    lines.push(`"Дата создания","${formatDate(report.created_at)}"`);
    lines.push('');

    if (report.summary) {
      lines.push(`"Резюме","${report.summary}"`);
      lines.push('');
    }

    if ('attendance_percentage' in report) {
      lines.push(`"Посещаемость (%)","${report.attendance_percentage}"`);
    }

    if ('progress_percentage' in report) {
      lines.push(`"Прогресс (%)","${report.progress_percentage}"`);
    }

    if (isTeacherReport(report)) {
      lines.push(`"Выполненные задания","${report.assignments_completed}/${report.assignments_total}"`);
      if (report.average_score !== undefined) {
        lines.push(`"Средняя оценка","${report.average_score}"`);
      }
    }

    return lines.join('\n');
  };

  // Handle print
  const handlePrint = () => {
    window.print();
    toast.success('Откройте диалог печати для сохранения отчета');
  };

  // Handle regenerate
  const handleRegenerate = async () => {
    if (!onRegenerate) return;

    try {
      await onRegenerate();
      toast.success('Отчет переформирован');
    } catch (error) {
      toast.error('Ошибка при переформировании отчета');
    }
  };

  // Handle share
  const handleShare = async () => {
    if (!onShare) return;

    try {
      await onShare();
      toast.success('Отчет поделен');
    } catch (error) {
      toast.error('Ошибка при совместном доступе к отчету');
    }
  };

  // Check if report is tutor or teacher
  const tutorReport = isTutorReport(report) ? report : null;
  const teacherReport = isTeacherReport(report) ? report : null;

  return (
    <div className="w-full space-y-6 pb-8">
      {/* Breadcrumb Navigation */}
      <Breadcrumb>
        <BreadcrumbItem>
          <button onClick={onBack} className="flex items-center space-x-1 text-blue-600 hover:text-blue-800">
            <ArrowLeft className="h-4 w-4" />
            <span>Отчеты</span>
          </button>
        </BreadcrumbItem>
        <BreadcrumbSeparator />
        <BreadcrumbItem>
          <span className="text-muted-foreground truncate max-w-xs">{report.title}</span>
        </BreadcrumbItem>
      </Breadcrumb>

      {/* Loading State */}
      {isLoading && (
        <Alert className="border-blue-200 bg-blue-50">
          <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
          <AlertDescription className="text-blue-800">Загрузка отчета...</AlertDescription>
        </Alert>
      )}

      {/* Report Header */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <CardTitle className="text-2xl mb-2">{report.title}</CardTitle>
              <div className="flex flex-wrap items-center gap-2">
                <Badge className={statusConfig.color}>
                  <StatusIcon className="h-3 w-3 mr-1" />
                  {statusConfig.label}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  Создан: {formatDate(report.created_at)}
                </span>
                {report.sent_at && (
                  <span className="text-sm text-muted-foreground">
                    Отправлен: {formatDate(report.sent_at)}
                  </span>
                )}
                {report.read_at && (
                  <span className="text-sm text-muted-foreground">
                    Прочитан: {formatDate(report.read_at)}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
            <div>
              <span className="text-xs text-muted-foreground">Студент</span>
              <p className="font-medium text-sm">{report.student_name}</p>
            </div>
            {tutorReport && (
              <>
                <div>
                  <span className="text-xs text-muted-foreground">Тьютор</span>
                  <p className="font-medium text-sm">{tutorReport.tutor_name}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Родитель</span>
                  <p className="font-medium text-sm">{tutorReport.parent_name}</p>
                </div>
              </>
            )}
            {teacherReport && (
              <>
                <div>
                  <span className="text-xs text-muted-foreground">Учитель</span>
                  <p className="font-medium text-sm">{teacherReport.teacher_name}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Предмет</span>
                  <p className="font-medium text-sm" style={{ color: teacherReport.subject_color }}>
                    {teacherReport.subject_name}
                  </p>
                </div>
              </>
            )}
            <div>
              <span className="text-xs text-muted-foreground">Период</span>
              <p className="font-medium text-sm">{formatDateRange(report.week_start, report.week_end)}</p>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Metrics and Charts */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Метрики и показатели</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Attendance */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium">Посещаемость</label>
              <span className="text-sm font-semibold">{report.attendance_percentage}%</span>
            </div>
            <Progress value={report.attendance_percentage} className="h-2" />
            {tutorReport && (
              <p className="text-xs text-muted-foreground">
                {tutorReport.attendance_days} из {tutorReport.total_days} дней
              </p>
            )}
          </div>

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium">Прогресс обучения</label>
              <span className="text-sm font-semibold">{'progress_percentage' in report ? report.progress_percentage : 'N/A'}%</span>
            </div>
            {'progress_percentage' in report && (
              <Progress value={report.progress_percentage} className="h-2" />
            )}
          </div>

          {/* Teacher Report Specific Metrics */}
          {teacherReport && (
            <>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-medium">Выполненные задания</label>
                  <span className="text-sm font-semibold">
                    {teacherReport.assignments_completed}/{teacherReport.assignments_total}
                  </span>
                </div>
                <Progress value={teacherReport.completion_percentage} className="h-2" />
              </div>

              {teacherReport.average_score !== undefined && (
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <label className="text-sm font-medium">Средняя оценка</label>
                    <span className="text-sm font-semibold">{teacherReport.average_score.toFixed(1)}</span>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Content Sections */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Содержание отчета</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-2 md:grid-cols-4">
              <TabsTrigger value="overview">Обзор</TabsTrigger>
              <TabsTrigger value="details">Детали</TabsTrigger>
              <TabsTrigger value="notes">Заметки</TabsTrigger>
              {report.attachment && <TabsTrigger value="attachment">Вложение</TabsTrigger>}
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-4 mt-4">
              {report.summary && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-sm">Резюме</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">{report.summary}</p>
                </div>
              )}

              {/* Achievement Section */}
              {report.achievements && (
                <div className="space-y-2 p-3 rounded-lg bg-green-50 border border-green-200">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <h4 className="font-semibold text-sm text-green-900">Достижения</h4>
                  </div>
                  <p className="text-sm text-green-800">{report.achievements}</p>
                </div>
              )}

              {/* Concerns Section */}
              {report.concerns && (
                <div className="space-y-2 p-3 rounded-lg bg-red-50 border border-red-200">
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                    <h4 className="font-semibold text-sm text-red-900">Обеспокоенности</h4>
                  </div>
                  <p className="text-sm text-red-800">{report.concerns}</p>
                </div>
              )}
            </TabsContent>

            {/* Details Tab */}
            <TabsContent value="details" className="space-y-4 mt-4">
              {isTutorReport(report) && tutorReport && (
                <>
                  {tutorReport.academic_progress && (
                    <div>
                      <h4 className="font-semibold text-sm mb-2">Академический прогресс</h4>
                      <p className="text-sm text-muted-foreground">{tutorReport.academic_progress}</p>
                    </div>
                  )}
                  {tutorReport.behavior_notes && (
                    <div>
                      <h4 className="font-semibold text-sm mb-2">Поведение</h4>
                      <p className="text-sm text-muted-foreground">{tutorReport.behavior_notes}</p>
                    </div>
                  )}
                </>
              )}

              {isTeacherReport(report) && teacherReport && (
                <>
                  {teacherReport.academic_progress && (
                    <div>
                      <h4 className="font-semibold text-sm mb-2">Академический прогресс</h4>
                      <p className="text-sm text-muted-foreground">{teacherReport.academic_progress}</p>
                    </div>
                  )}
                  {teacherReport.performance_notes && (
                    <div>
                      <h4 className="font-semibold text-sm mb-2">Заметки о производительности</h4>
                      <p className="text-sm text-muted-foreground">{teacherReport.performance_notes}</p>
                    </div>
                  )}
                </>
              )}
            </TabsContent>

            {/* Notes Tab */}
            <TabsContent value="notes" className="space-y-4 mt-4">
              {report.recommendations && (
                <div className="space-y-2 p-3 rounded-lg bg-blue-50 border border-blue-200">
                  <h4 className="font-semibold text-sm text-blue-900">Рекомендации</h4>
                  <p className="text-sm text-blue-800">{report.recommendations}</p>
                </div>
              )}

              {!report.recommendations && !report.achievements && !report.concerns && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  В этом отчете нет дополнительных заметок
                </p>
              )}
            </TabsContent>

            {/* Attachment Tab */}
            {report.attachment && (
              <TabsContent value="attachment" className="space-y-4 mt-4">
                <div className="flex items-center justify-between p-4 rounded-lg border border-gray-200 bg-gray-50">
                  <div className="flex items-center space-x-3">
                    <File className="h-5 w-5 text-gray-600" />
                    <div>
                      <p className="font-semibold text-sm">{report.attachment.split('/').pop()}</p>
                      <p className="text-xs text-muted-foreground">Файл прикреплен к отчету</p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      window.open(report.attachment, '_blank');
                    }}
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Скачать
                  </Button>
                </div>
              </TabsContent>
            )}
          </Tabs>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Действия</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Download Section */}
            <div>
              <label className="text-sm font-medium mb-2 block">Загрузить отчет в формате:</label>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant={downloadFormat === 'pdf' ? 'default' : 'outline'}
                  onClick={() => {
                    setDownloadFormat('pdf');
                    handleDownload('pdf');
                  }}
                  disabled={isDownloading}
                >
                  <FileText className="h-4 w-4 mr-1" />
                  PDF
                </Button>
                <Button
                  size="sm"
                  variant={downloadFormat === 'excel' ? 'default' : 'outline'}
                  onClick={() => {
                    setDownloadFormat('excel');
                    handleDownload('excel');
                  }}
                  disabled={isDownloading}
                >
                  <Download className="h-4 w-4 mr-1" />
                  Excel (CSV)
                </Button>
                <Button
                  size="sm"
                  variant={downloadFormat === 'json' ? 'default' : 'outline'}
                  onClick={() => {
                    setDownloadFormat('json');
                    handleDownload('json');
                  }}
                  disabled={isDownloading}
                >
                  <FileText className="h-4 w-4 mr-1" />
                  JSON
                </Button>
              </div>
            </div>

            {/* Primary Actions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-4 border-t">
              <Button
                variant="outline"
                onClick={handlePrint}
                disabled={isLoading || isDownloading}
                className="w-full"
              >
                <Printer className="h-4 w-4 mr-1" />
                Печать
              </Button>

              {onShare && (
                <Button
                  variant="outline"
                  onClick={handleShare}
                  disabled={isLoading || isDownloading}
                  className="w-full"
                >
                  <Share2 className="h-4 w-4 mr-1" />
                  Поделиться
                </Button>
              )}

              {onRegenerate && report.status === 'draft' && (
                <Button
                  variant="outline"
                  onClick={handleRegenerate}
                  disabled={isLoading || isDownloading}
                  className="w-full"
                >
                  <RotateCw className="h-4 w-4 mr-1" />
                  Переформировать
                </Button>
              )}

              <Button
                variant="default"
                onClick={() => setShowFullContent(!showFullContent)}
                disabled={isLoading || isDownloading}
                className="w-full"
              >
                {showFullContent ? (
                  <>
                    <EyeOff className="h-4 w-4 mr-1" />
                    Скрыть
                  </>
                ) : (
                  <>
                    <Eye className="h-4 w-4 mr-1" />
                    Показать все
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Full Content View (Optional) */}
      {showFullContent && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Полные данные отчета</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-4 rounded-md overflow-auto max-h-96">
              {JSON.stringify(report, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
};


