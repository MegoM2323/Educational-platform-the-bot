import { useState, useEffect } from "react";
import { logger } from '@/utils/logger';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { 
  CheckCircle, 
  Clock, 
  RotateCcw, 
  MessageSquare, 
  Star, 
  Download,
  FileText,
  Calendar
} from "lucide-react";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { useToast } from "@/hooks/use-toast";

interface MaterialSubmission {
  id: number;
  material: number;
  material_title: string;
  student: number;
  student_name: string;
  submission_file?: string;
  submission_text: string;
  status: 'submitted' | 'reviewed' | 'returned';
  is_late: boolean;
  submitted_at: string;
  feedback?: {
    id: number;
    teacher: number;
    teacher_name: string;
    feedback_text: string;
    grade?: number;
    created_at: string;
  };
}

interface MaterialSubmissionStatusProps {
  materialId: number;
  materialTitle: string;
  onEditSubmission?: () => void;
}

const statusConfig = {
  submitted: {
    label: 'Отправлено',
    icon: Clock,
    variant: 'secondary' as const,
    color: 'text-blue-600'
  },
  reviewed: {
    label: 'Проверено',
    icon: CheckCircle,
    variant: 'default' as const,
    color: 'text-green-600'
  },
  returned: {
    label: 'Возвращено',
    icon: RotateCcw,
    variant: 'destructive' as const,
    color: 'text-orange-600'
  }
};

export default function MaterialSubmissionStatus({ 
  materialId, 
  materialTitle, 
  onEditSubmission 
}: MaterialSubmissionStatusProps) {
  const { toast } = useToast();
  const [submission, setSubmission] = useState<MaterialSubmission | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSubmission = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.request<MaterialSubmission[]>(`/submissions/?material=${materialId}`);
      
      if (response.data && response.data.length > 0) {
        setSubmission(response.data[0]);
      } else {
        setSubmission(null);
      }
    } catch (err: any) {
      logger.error('Fetch submission error:', err);
      setError('Ошибка загрузки статуса ответа');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmission();
  }, [materialId]);

  const handleDownloadFile = async (fileUrl: string, filename: string) => {
    try {
      const response = await fetch(fileUrl, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Ошибка скачивания файла');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast({
        title: "Успешно",
        description: "Файл скачан",
      });
    } catch (err: any) {
      toast({
        title: "Ошибка",
        description: "Ошибка при скачивании файла",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="ml-2">Загрузка статуса ответа...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            <p>{error}</p>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchSubmission}
              className="mt-2"
            >
              Попробовать снова
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!submission) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Ответ не отправлен</p>
            <p className="text-sm">Отправьте ответ на материал, чтобы увидеть его статус</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const statusInfo = statusConfig[submission.status];
  const StatusIcon = statusInfo.icon;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <StatusIcon className={`w-5 h-5 ${statusInfo.color}`} />
              Статус ответа
            </CardTitle>
            <CardDescription>
              Ответ на материал: <strong>{submission.material_title}</strong>
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Badge variant={statusInfo.variant}>
              {statusInfo.label}
            </Badge>
            {submission.is_late && (
              <Badge variant="outline" className="text-orange-600">
                С опозданием
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Информация об отправке */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="w-4 h-4" />
          <span>Отправлено: {new Date(submission.submitted_at).toLocaleString('ru-RU')}</span>
        </div>

        {/* Содержимое ответа */}
        {submission.submission_text && (
          <div>
            <h4 className="font-medium mb-2">Текстовый ответ:</h4>
            <div className="bg-muted p-3 rounded-lg">
              <p className="whitespace-pre-wrap">{submission.submission_text}</p>
            </div>
          </div>
        )}

        {/* Файл ответа */}
        {submission.submission_file && (
          <div>
            <h4 className="font-medium mb-2">Файл ответа:</h4>
            <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
              <FileText className="w-4 h-4" />
              <span className="flex-1">{submission.submission_file.split('/').pop()}</span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleDownloadFile(submission.submission_file!, submission.submission_file!.split('/').pop()!)}
              >
                <Download className="w-4 h-4 mr-1" />
                Скачать
              </Button>
            </div>
          </div>
        )}

        {/* Фидбэк преподавателя */}
        {submission.feedback && (
          <>
            <Separator />
            <div>
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Фидбэк преподавателя
              </h4>
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{submission.feedback.teacher_name}</span>
                  {submission.feedback.grade && (
                    <div className="flex items-center gap-1">
                      <Star className="w-4 h-4 text-yellow-500 fill-current" />
                      <span className="font-medium">{submission.feedback.grade}/5</span>
                    </div>
                  )}
                </div>
                <p className="text-sm whitespace-pre-wrap">{submission.feedback.feedback_text}</p>
                <p className="text-xs text-muted-foreground mt-2">
                  {new Date(submission.feedback.created_at).toLocaleString('ru-RU')}
                </p>
              </div>
            </div>
          </>
        )}

        {/* Кнопка редактирования для возвращенных ответов */}
        {submission.status === 'returned' && onEditSubmission && (
          <div className="pt-4">
            <Button onClick={onEditSubmission} className="w-full">
              <RotateCcw className="w-4 h-4 mr-2" />
              Отправить исправленный ответ
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
