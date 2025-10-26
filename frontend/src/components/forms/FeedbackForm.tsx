import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { 
  Star, 
  MessageSquare, 
  FileText, 
  Download, 
  Calendar,
  User,
  Send,
  CheckCircle,
  Clock,
  RotateCcw
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";

interface Submission {
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

interface FeedbackFormProps {
  submission: Submission;
  onSuccess: () => void;
  onCancel: () => void;
}

interface FeedbackData {
  feedback_text: string;
  grade?: number;
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

export default function FeedbackForm({ submission, onSuccess, onCancel }: FeedbackFormProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [feedbackData, setFeedbackData] = useState<FeedbackData>({
    feedback_text: submission.feedback?.feedback_text || "",
    grade: submission.feedback?.grade || undefined
  });

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFeedbackData(prev => ({
      ...prev,
      feedback_text: event.target.value
    }));
  };

  const handleGradeChange = (value: string) => {
    setFeedbackData(prev => ({
      ...prev,
      grade: value ? parseInt(value) : undefined
    }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!feedbackData.feedback_text.trim()) {
      toast({
        title: "Ошибка",
        description: "Необходимо написать текст фидбэка",
        variant: "destructive",
      });
      return;
    }

    try {
      setLoading(true);

      const response = await apiClient.request('/submissions/submit_feedback/', {
        method: 'POST',
        data: {
          submission_id: submission.id,
          feedback_text: feedbackData.feedback_text,
          grade: feedbackData.grade,
        },
      });

      if (response.data) {
        toast({
          title: "Успешно",
          description: "Фидбэк отправлен студенту",
        });
        onSuccess();
      } else {
        throw new Error(response.error || 'Ошибка отправки фидбэка');
      }
    } catch (error: any) {
      console.error('Feedback error:', error);
      toast({
        title: "Ошибка",
        description: error.message || "Произошла ошибка при отправке фидбэка",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

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

  const statusInfo = statusConfig[submission.status];
  const StatusIcon = statusInfo.icon;

  return (
    <div className="space-y-6">
      {/* Информация об ответе */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <StatusIcon className={`w-5 h-5 ${statusInfo.color}`} />
                Ответ студента
              </CardTitle>
              <CardDescription>
                Материал: <strong>{submission.material_title}</strong>
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
          {/* Информация о студенте и дате */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <User className="w-4 h-4" />
              <span>{submission.student_name}</span>
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              <span>{new Date(submission.submitted_at).toLocaleString('ru-RU')}</span>
            </div>
          </div>

          {/* Текстовый ответ */}
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
        </CardContent>
      </Card>

      {/* Форма фидбэка */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            {submission.feedback ? 'Редактировать фидбэк' : 'Отправить фидбэк'}
          </CardTitle>
          <CardDescription>
            {submission.feedback 
              ? 'Вы можете изменить существующий фидбэк'
              : 'Напишите фидбэк для студента'
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Оценка */}
            <div className="space-y-2">
              <Label htmlFor="grade">Оценка (необязательно)</Label>
              <Select 
                value={feedbackData.grade?.toString() || ""} 
                onValueChange={handleGradeChange}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Выберите оценку" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Без оценки</SelectItem>
                  {[1, 2, 3, 4, 5].map(grade => (
                    <SelectItem key={grade} value={grade.toString()}>
                      <div className="flex items-center gap-2">
                        <Star className="w-4 h-4 text-yellow-500 fill-current" />
                        <span>{grade}/5</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Текст фидбэка */}
            <div className="space-y-2">
              <Label htmlFor="feedback-text">Текст фидбэка *</Label>
              <Textarea
                id="feedback-text"
                placeholder="Напишите фидбэк для студента..."
                value={feedbackData.feedback_text}
                onChange={handleTextChange}
                rows={6}
                className="resize-none"
                required
              />
            </div>

            {/* Кнопки */}
            <div className="flex gap-3 justify-end">
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={loading}
              >
                Отмена
              </Button>
              <Button
                type="submit"
                disabled={loading || !feedbackData.feedback_text.trim()}
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                    Отправка...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    {submission.feedback ? 'Обновить фидбэк' : 'Отправить фидбэк'}
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
