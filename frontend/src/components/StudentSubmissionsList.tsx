import { useState, useEffect } from "react";
import { logger } from '@/utils/logger';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { 
  Search, 
  MessageSquare, 
  User, 
  Calendar, 
  Clock, 
  CheckCircle, 
  RotateCcw,
  FileText,
  Star,
  Eye
} from "lucide-react";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { useToast } from "@/hooks/use-toast";
import FeedbackForm from "@/components/forms/FeedbackForm";

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

interface StudentSubmissionsListProps {
  materialId: number;
  materialTitle: string;
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

export default function StudentSubmissionsList({ materialId, materialTitle }: StudentSubmissionsListProps) {
  const { toast } = useToast();
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
  const [feedbackDialogOpen, setFeedbackDialogOpen] = useState(false);

  const fetchSubmissions = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.request<Submission[]>(`/submissions/?material=${materialId}`);
      
      if (response.data) {
        setSubmissions(response.data);
      } else {
        setError('Ошибка загрузки ответов студентов');
      }
    } catch (err: any) {
      logger.error('Fetch submissions error:', err);
      setError('Ошибка загрузки ответов студентов');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmissions();
  }, [materialId]);

  const handleOpenFeedbackDialog = (submission: Submission) => {
    setSelectedSubmission(submission);
    setFeedbackDialogOpen(true);
  };

  const handleFeedbackSuccess = () => {
    setFeedbackDialogOpen(false);
    setSelectedSubmission(null);
    fetchSubmissions(); // Обновляем список
  };

  const handleFeedbackCancel = () => {
    setFeedbackDialogOpen(false);
    setSelectedSubmission(null);
  };

  // Фильтрация
  const filteredSubmissions = submissions.filter(submission => {
    const matchesSearch = submission.student_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         submission.material_title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || submission.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusInfo = (status: string) => {
    return statusConfig[status as keyof typeof statusConfig] || statusConfig.submitted;
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="ml-2">Загрузка ответов студентов...</span>
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
            <Button type="button" 
              variant="outline" 
              size="sm" 
              onClick={fetchSubmissions}
              className="mt-2"
            >
              Попробовать снова
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div>
        <h2 className="text-2xl font-bold">Ответы студентов</h2>
        <p className="text-muted-foreground">Материал: {materialTitle}</p>
      </div>

      {/* Фильтры */}
      <Card className="p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input 
              placeholder="Поиск по имени студента..." 
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Статус" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все статусы</SelectItem>
              <SelectItem value="submitted">Отправлено</SelectItem>
              <SelectItem value="reviewed">Проверено</SelectItem>
              <SelectItem value="returned">Возвращено</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Список ответов */}
      <div className="space-y-4">
        {filteredSubmissions.length === 0 ? (
          <Card>
            <CardContent className="p-6">
              <div className="text-center text-muted-foreground">
                <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Ответы не найдены</p>
                <p className="text-sm">
                  {searchQuery || statusFilter !== "all" 
                    ? "Попробуйте изменить фильтры поиска"
                    : "Студенты еще не отправили ответы на этот материал"
                  }
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          filteredSubmissions.map((submission) => {
            const statusInfo = getStatusInfo(submission.status);
            const StatusIcon = statusInfo.icon;

            return (
              <Card key={submission.id} className="hover:border-primary transition-colors">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <StatusIcon className={`w-5 h-5 ${statusInfo.color}`} />
                        <h3 className="font-semibold">{submission.student_name}</h3>
                        <Badge variant={statusInfo.variant}>
                          {statusInfo.label}
                        </Badge>
                        {submission.is_late && (
                          <Badge variant="outline" className="text-orange-600">
                            С опозданием
                          </Badge>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                        <div className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          <span>{new Date(submission.submitted_at).toLocaleString('ru-RU')}</span>
                        </div>
                        {submission.feedback?.grade && (
                          <div className="flex items-center gap-1">
                            <Star className="w-4 h-4 text-yellow-500 fill-current" />
                            <span>{submission.feedback.grade}/5</span>
                          </div>
                        )}
                      </div>

                      {/* Краткий предварительный просмотр ответа */}
                      <div className="space-y-2">
                        {submission.submission_text && (
                          <div>
                            <p className="text-sm font-medium">Текстовый ответ:</p>
                            <p className="text-sm text-muted-foreground line-clamp-2">
                              {submission.submission_text}
                            </p>
                          </div>
                        )}
                        {submission.submission_file && (
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4" />
                            <span className="text-sm">
                              {submission.submission_file.split('/').pop()}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2 ml-4">
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button type="button" variant="outline" size="sm">
                            <Eye className="w-4 h-4 mr-1" />
                            Просмотр
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle>Ответ студента</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            {/* Полный ответ студента */}
                            <Card>
                              <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                  <User className="w-5 h-5" />
                                  {submission.student_name}
                                </CardTitle>
                                <CardDescription>
                                  Отправлено: {new Date(submission.submitted_at).toLocaleString('ru-RU')}
                                </CardDescription>
                              </CardHeader>
                              <CardContent className="space-y-4">
                                {submission.submission_text && (
                                  <div>
                                    <h4 className="font-medium mb-2">Текстовый ответ:</h4>
                                    <div className="bg-muted p-3 rounded-lg">
                                      <p className="whitespace-pre-wrap">{submission.submission_text}</p>
                                    </div>
                                  </div>
                                )}
                                {submission.submission_file && (
                                  <div>
                                    <h4 className="font-medium mb-2">Файл ответа:</h4>
                                    <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                                      <FileText className="w-4 h-4" />
                                      <span className="flex-1">{submission.submission_file.split('/').pop()}</span>
                                    </div>
                                  </div>
                                )}
                              </CardContent>
                            </Card>

                            {/* Существующий фидбэк */}
                            {submission.feedback && (
                              <Card>
                                <CardHeader>
                                  <CardTitle className="flex items-center gap-2">
                                    <MessageSquare className="w-5 h-5" />
                                    Фидбэк преподавателя
                                  </CardTitle>
                                </CardHeader>
                                <CardContent>
                                  <div className="space-y-2">
                                    {submission.feedback.grade && (
                                      <div className="flex items-center gap-1">
                                        <Star className="w-4 h-4 text-yellow-500 fill-current" />
                                        <span className="font-medium">{submission.feedback.grade}/5</span>
                                      </div>
                                    )}
                                    <p className="whitespace-pre-wrap">{submission.feedback.feedback_text}</p>
                                    <p className="text-xs text-muted-foreground">
                                      {new Date(submission.feedback.created_at).toLocaleString('ru-RU')}
                                    </p>
                                  </div>
                                </CardContent>
                              </Card>
                            )}
                          </div>
                        </DialogContent>
                      </Dialog>

                      <Button type="button" 
                        size="sm"
                        onClick={() => handleOpenFeedbackDialog(submission)}
                      >
                        <MessageSquare className="w-4 h-4 mr-1" />
                        {submission.feedback ? 'Изменить' : 'Фидбэк'}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Диалог фидбэка */}
      <Dialog open={feedbackDialogOpen} onOpenChange={setFeedbackDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Фидбэк для студента</DialogTitle>
          </DialogHeader>
          {selectedSubmission && (
            <FeedbackForm
              submission={selectedSubmission}
              onSuccess={handleFeedbackSuccess}
              onCancel={handleFeedbackCancel}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
