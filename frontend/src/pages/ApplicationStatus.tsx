import { useState, useEffect } from "react";
import { logger } from '@/utils/logger';
import { useParams, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen, ArrowLeft, CheckCircle, Clock, XCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { safeJsonParse } from "../utils/jsonUtils";

interface ApplicationStatus {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  applicant_type: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  updated_at: string;
  rejection_reason?: string;
  tracking_token: string;
}

const ApplicationStatus = () => {
  const { trackingToken } = useParams<{ trackingToken: string }>();
  const [application, setApplication] = useState<ApplicationStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchApplicationStatus = async () => {
    if (!trackingToken) return;

    try {
      // Используем относительный URL для автоматического определения хоста
      const apiUrl = `/api/applications/status/${trackingToken}/`;
      const response = await fetch(apiUrl);
      
      const result = await safeJsonParse(response);
      
      if (result.success) {
        setApplication(result.data);
      } else if (response.status === 404) {
        toast.error("Заявка не найдена");
      } else {
        toast.error(result.error || "Ошибка при получении статуса заявки");
      }
    } catch (error) {
      toast.error("Произошла ошибка при загрузке статуса заявки");
      logger.error('Status fetch error:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchApplicationStatus();
  }, [trackingToken]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchApplicationStatus();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="w-6 h-6 text-green-500" />;
      case 'rejected':
        return <XCircle className="w-6 h-6 text-red-500" />;
      default:
        return <Clock className="w-6 h-6 text-yellow-500" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'approved':
        return 'Одобрена';
      case 'rejected':
        return 'Отклонена';
      default:
        return 'На рассмотрении';
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'approved':
        return 'default';
      case 'rejected':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  const getApplicantTypeText = (type: string) => {
    switch (type) {
      case 'student':
        return 'Студент';
      case 'teacher':
        return 'Преподаватель';
      case 'parent':
        return 'Родитель';
      default:
        return type;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-muted/20 to-background">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Загрузка статуса заявки...</p>
        </div>
      </div>
    );
  }

  if (!application) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-muted/20 to-background">
        <Card className="w-full max-w-md p-8 text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Заявка не найдена</h1>
          <p className="text-muted-foreground mb-6">
            Заявка с указанным номером не найдена или была удалена.
          </p>
          <Link to="/application">
            <Button>Подать новую заявку</Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-background via-muted/20 to-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-10 h-10 gradient-primary rounded-lg flex items-center justify-center">
                <BookOpen className="w-6 h-6 text-primary-foreground" />
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                THE BOT
              </span>
            </Link>
            <Link to="/" className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span>На главную</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-4">
        <Card className="w-full max-w-2xl p-8 shadow-lg">
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              {getStatusIcon(application.status)}
            </div>
            <h1 className="text-3xl font-bold mb-2">Статус заявки</h1>
            <Badge variant={getStatusBadgeVariant(application.status)} className="text-lg px-4 py-2">
              {getStatusText(application.status)}
            </Badge>
          </div>

          <div className="space-y-6">
            {/* Applicant Info */}
            <div className="bg-muted/50 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Информация о заявителе</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Имя</p>
                  <p className="font-medium">{application.first_name} {application.last_name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Email</p>
                  <p className="font-medium">{application.email}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Тип заявки</p>
                  <p className="font-medium">{getApplicantTypeText(application.applicant_type)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Дата подачи</p>
                  <p className="font-medium">
                    {new Date(application.created_at).toLocaleDateString('ru-RU', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              </div>
            </div>

            {/* Status Details */}
            {application.status === 'approved' && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <h3 className="text-lg font-semibold text-green-800">Заявка одобрена!</h3>
                </div>
                <p className="text-green-700">
                  Ваша заявка была одобрена. Данные для входа в систему отправлены на ваш Telegram.
                  Если у вас есть вопросы, обратитесь к администратору.
                </p>
                <div className="mt-4">
                  <Link to="/auth">
                    <Button className="bg-green-600 hover:bg-green-700">
                      Войти в систему
                    </Button>
                  </Link>
                </div>
              </div>
            )}

            {application.status === 'rejected' && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <div className="flex items-center gap-2 mb-2">
                  <XCircle className="w-5 h-5 text-red-600" />
                  <h3 className="text-lg font-semibold text-red-800">Заявка отклонена</h3>
                </div>
                {application.rejection_reason && (
                  <p className="text-red-700 mb-4">
                    <strong>Причина отклонения:</strong> {application.rejection_reason}
                  </p>
                )}
                <p className="text-red-700">
                  К сожалению, ваша заявка была отклонена. Вы можете подать новую заявку, 
                  исправив указанные недостатки.
                </p>
                <div className="mt-4">
                  <Link to="/application">
                    <Button variant="outline" className="border-red-300 text-red-700 hover:bg-red-50">
                      Подать новую заявку
                    </Button>
                  </Link>
                </div>
              </div>
            )}

            {application.status === 'pending' && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-5 h-5 text-yellow-600" />
                  <h3 className="text-lg font-semibold text-yellow-800">Заявка на рассмотрении</h3>
                </div>
                <p className="text-yellow-700">
                  Ваша заявка находится на рассмотрении. Мы уведомим вас о результате 
                  через Telegram. Обычно рассмотрение занимает 1-3 рабочих дня.
                </p>
                <div className="mt-4 flex gap-2">
                  <Button 
                    variant="outline" 
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                    className="border-yellow-300 text-yellow-700 hover:bg-yellow-50"
                  >
                    {isRefreshing ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        Обновление...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Обновить статус
                      </>
                    )}
                  </Button>
                  <Link to="/application">
                    <Button variant="outline">
                      Подать новую заявку
                    </Button>
                  </Link>
                </div>
              </div>
            )}

            {/* Tracking Info */}
            <div className="text-center text-sm text-muted-foreground">
              <p>Номер отслеживания: <code className="bg-muted px-2 py-1 rounded">{application.tracking_token}</code></p>
              <p className="mt-1">
                Последнее обновление: {new Date(application.updated_at).toLocaleString('ru-RU')}
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ApplicationStatus;
