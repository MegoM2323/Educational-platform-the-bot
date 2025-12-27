import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { logger } from "@/utils/logger";
import { getErrorMessage, extractErrorInfo } from "@/utils/errors";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { useToast } from "@/hooks/useToast";
import {
  useErrorNotification,
  useSuccessNotification,
} from "@/components/NotificationSystem";
import {
  ErrorState,
  EmptyState,
  LoadingSpinner,
  MaterialSkeleton,
} from "@/components/LoadingStates";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import {
  AlertTriangle,
  ArrowLeft,
  Download,
  Eye,
  FileText,
  Home,
  Lock,
  LogIn,
  MapPin,
  RefreshCw,
  Send,
  User,
  Video,
  WifiOff,
} from "lucide-react";

// Type definitions
interface Material {
  id: number;
  title: string;
  description: string;
  content: string;
  author: number;
  author_name: string;
  subject: number;
  subject_name: string;
  type: "lesson" | "presentation" | "video" | "document" | "test" | "homework";
  status: "draft" | "active" | "archived";
  is_public: boolean;
  file?: string;
  video_url?: string;
  tags: string;
  difficulty_level: number;
  created_at: string;
  published_at?: string;
  progress?: {
    is_completed: boolean;
    progress_percentage: number;
    time_spent: number;
    started_at?: string;
    completed_at?: string;
    last_accessed?: string;
  };
}

type ErrorType =
  | "404_NOT_FOUND"
  | "403_FORBIDDEN"
  | "401_UNAUTHORIZED"
  | "408_TIMEOUT"
  | "410_GONE"
  | "400_INVALID_ID"
  | "500_SERVER_ERROR"
  | "ENROLLMENT_REQUIRED"
  | "ARCHIVED"
  | "NETWORK_ERROR";

interface MaterialDetailError {
  type: ErrorType;
  statusCode?: number;
  message: string;
  retryable: boolean;
}

// Error boundary component
interface ErrorFallbackProps {
  error: MaterialDetailError;
  onRetry: () => void;
  onNavigateBack: () => void;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  onRetry,
  onNavigateBack,
}) => {
  const getErrorContent = () => {
    switch (error.type) {
      case "404_NOT_FOUND":
        return {
          title: "Материал не найден",
          description:
            "К сожалению, запрашиваемый материал не существует или был удален.",
          icon: <FileText className="w-8 h-8 text-muted-foreground" />,
          showRetry: true,
          suggestions: [
            "Проверьте ссылку на материал",
            "Вернитесь к списку материалов",
            "Свяжитесь с преподавателем, если материал должен быть доступен",
          ],
        };

      case "403_FORBIDDEN":
        return {
          title: "Доступ запрещен",
          description:
            "У вас нет прав доступа к этому материалу. Возможно, материал не был вам назначен или вы неавторизованы.",
          icon: <Lock className="w-8 h-8 text-muted-foreground" />,
          showRetry: false,
          suggestions: [
            "Убедитесь, что вы авторизованы под правильным аккаунтом",
            "Попросите преподавателя назначить вам этот материал",
            "Проверьте, зарегистрированы ли вы на курс",
          ],
        };

      case "401_UNAUTHORIZED":
        return {
          title: "Требуется авторизация",
          description:
            "Пожалуйста, авторизуйтесь, чтобы получить доступ к материалу.",
          icon: <LogIn className="w-8 h-8 text-muted-foreground" />,
          showRetry: true,
          suggestions: [
            "Убедитесь, что вы авторизованы в системе",
            "Обновите страницу и попробуйте снова",
            "Очистите кэш браузера при необходимости",
          ],
        };

      case "408_TIMEOUT":
      case "NETWORK_ERROR":
        return {
          title: "Ошибка сети или истекло время ожидания",
          description:
            "Не удается загрузить материал из-за проблем с сетью. Пожалуйста, проверьте подключение к интернету и попробуйте снова.",
          icon: <WifiOff className="w-8 h-8 text-muted-foreground" />,
          showRetry: true,
          suggestions: [
            "Проверьте подключение к интернету",
            "Убедитесь, что сервер доступен",
            "Подождите несколько секунд и попробуйте снова",
          ],
        };

      case "410_GONE":
        return {
          title: "Материал был удален",
          description:
            "Этот материал больше не доступен. Он был удален администратором или преподавателем.",
          icon: <MapPin className="w-8 h-8 text-muted-foreground" />,
          showRetry: false,
          suggestions: [
            "Свяжитесь с преподавателем для получения альтернативного материала",
            "Обратитесь в службу поддержки платформы",
          ],
        };

      case "ARCHIVED":
        return {
          title: "Материал больше не доступен",
          description:
            "Этот материал был архивирован и больше не используется в курсе.",
          icon: <MapPin className="w-8 h-8 text-muted-foreground" />,
          showRetry: false,
          suggestions: [
            "Используйте актуальные материалы из списка курса",
            "Попросите преподавателя активировать материал при необходимости",
          ],
        };

      case "ENROLLMENT_REQUIRED":
        return {
          title: "Требуется регистрация на предмет",
          description:
            "Для доступа к этому материалу вам необходимо зарегистрироваться на соответствующий предмет.",
          icon: <Lock className="w-8 h-8 text-muted-foreground" />,
          showRetry: false,
          suggestions: [
            "Зарегистрируйтесь на предмет в разделе 'Предметы'",
            "Попросите преподавателя добавить вас на курс",
            "Свяжитесь с администратором платформы",
          ],
        };

      case "400_INVALID_ID":
        return {
          title: "Неправильный идентификатор материала",
          description:
            "Идентификатор материала содержит недопустимые символы или неверный формат.",
          icon: <AlertTriangle className="w-8 h-8 text-muted-foreground" />,
          showRetry: false,
          suggestions: [
            "Проверьте правильность ссылки",
            "Скопируйте ссылку из списка материалов",
          ],
        };

      case "500_SERVER_ERROR":
        return {
          title: "Ошибка сервера",
          description:
            "Произошла ошибка при обработке вашего запроса. Мы уже работаем над исправлением проблемы.",
          icon: <AlertTriangle className="w-8 h-8 text-muted-foreground" />,
          showRetry: true,
          suggestions: [
            "Попробуйте снова через несколько минут",
            "Свяжитесь с поддержкой: support@thebot.com",
            "Вернитесь к списку материалов и попробуйте позже",
          ],
        };

      default:
        return {
          title: "Произошла ошибка",
          description: error.message || "Не удалось загрузить материал.",
          icon: <AlertTriangle className="w-8 h-8 text-muted-foreground" />,
          showRetry: error.retryable,
          suggestions: [
            "Обновите страницу и попробуйте снова",
            "Свяжитесь с поддержкой платформы",
          ],
        };
    }
  };

  const content = getErrorContent();

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <StudentSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onNavigateBack}
              aria-label="Вернуться к списку материалов"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Назад
            </Button>
          </header>

          <main className="p-6">
            <div className="max-w-2xl mx-auto space-y-6">
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>{content.title}</AlertTitle>
                <AlertDescription className="mt-2">
                  {content.description}
                </AlertDescription>
              </Alert>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Рекомендации</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {content.suggestions.map((suggestion, index) => (
                      <li key={index} className="flex items-start gap-3">
                        <span className="text-primary font-bold text-sm mt-0.5">
                          {index + 1}.
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {suggestion}
                        </span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <div className="flex gap-3 justify-center">
                <Button
                  type="button"
                  variant="outline"
                  onClick={onNavigateBack}
                  aria-label="Вернуться к списку материалов"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  К списку материалов
                </Button>

                {content.showRetry && (
                  <Button
                    type="button"
                    onClick={onRetry}
                    aria-label="Попробовать загрузить материал снова"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Попробовать снова
                  </Button>
                )}

                <Button
                  type="button"
                  variant="ghost"
                  onClick={() =>
                    window.open(
                      "mailto:support@thebot.com?subject=Ошибка при загрузке материала",
                      "_blank"
                    )
                  }
                  aria-label="Связаться с поддержкой"
                >
                  Поддержка
                </Button>
              </div>

              {error.statusCode && (
                <div className="text-xs text-muted-foreground text-center">
                  Код ошибки: {error.statusCode}
                </div>
              )}
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

// Main component
export default function MaterialDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();

  const [material, setMaterial] = useState<Material | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<MaterialDetailError | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  // Validate material ID format
  const isValidId = useCallback((): boolean => {
    if (!id) return false;
    // Check if ID is a valid positive integer
    const numId = parseInt(id, 10);
    return !isNaN(numId) && numId > 0 && numId.toString() === id;
  }, [id]);

  // Error handler
  const handleError = useCallback(
    (err: unknown): MaterialDetailError => {
      logger.error("Material detail error:", err);

      const errorInfo = extractErrorInfo(err);
      const statusCode = errorInfo.statusCode;

      // Check for specific error types
      if (!isValidId()) {
        return {
          type: "400_INVALID_ID",
          message: "Неправильный формат идентификатора материала",
          retryable: false,
        };
      }

      switch (statusCode) {
        case 401:
          return {
            type: "401_UNAUTHORIZED",
            statusCode: 401,
            message: "Требуется авторизация",
            retryable: true,
          };

        case 403:
          // Check if error message indicates enrollment issue
          const message = errorInfo.message.toLowerCase();
          if (
            message.includes("enrollment") ||
            message.includes("enroll") ||
            message.includes("зарегистр") ||
            message.includes("курс")
          ) {
            return {
              type: "ENROLLMENT_REQUIRED",
              statusCode: 403,
              message: "Требуется регистрация на предмет",
              retryable: false,
            };
          }
          return {
            type: "403_FORBIDDEN",
            statusCode: 403,
            message: "Доступ запрещен",
            retryable: false,
          };

        case 404:
          return {
            type: "404_NOT_FOUND",
            statusCode: 404,
            message: "Материал не найден",
            retryable: false,
          };

        case 410:
          return {
            type: "410_GONE",
            statusCode: 410,
            message: "Материал был удален",
            retryable: false,
          };

        case 408:
        case 504:
        case 503:
        case 502:
          return {
            type: "408_TIMEOUT",
            statusCode,
            message: "Истекло время ожидания при загрузке материала",
            retryable: true,
          };

        case 500:
          return {
            type: "500_SERVER_ERROR",
            statusCode: 500,
            message: "Ошибка сервера при загрузке материала",
            retryable: true,
          };

        default:
          // Network error
          if (
            err instanceof Error &&
            (err.message.includes("timeout") ||
              err.message.includes("Network") ||
              err.message.includes("Failed to fetch"))
          ) {
            return {
              type: "NETWORK_ERROR",
              message: "Ошибка сети при загрузке материала",
              retryable: true,
            };
          }

          return {
            type: "500_SERVER_ERROR",
            statusCode,
            message: errorInfo.message,
            retryable: errorInfo.isRetryable ?? true,
          };
      }
    },
    [isValidId]
  );

  // Fetch material
  const fetchMaterial = useCallback(async () => {
    try {
      // Clear previous error
      setError(null);
      setLoading(true);

      // Validate ID first
      if (!isValidId()) {
        const err: MaterialDetailError = {
          type: "400_INVALID_ID",
          message: "Неправильный формат идентификатора материала",
          retryable: false,
        };
        setError(err);
        setLoading(false);
        return;
      }

      // Set timeout for fetch
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

      try {
        const response = await apiClient.request<Material>(
          `/materials/materials/${id}/`,
          {
            signal: controller.signal,
          }
        );

        clearTimeout(timeoutId);

        if (response.data) {
          // Check if material is archived
          if (response.data.status === "archived") {
            setError({
              type: "ARCHIVED",
              message: "Материал был архивирован",
              retryable: false,
            });
            setLoading(false);
            return;
          }

          setMaterial(response.data);
          setError(null);
          logger.debug("Material loaded successfully", response.data);
        } else {
          const err: MaterialDetailError = handleError(
            response.error || "Ошибка загрузки материала"
          );
          setError(err);
        }
      } catch (timeoutErr) {
        clearTimeout(timeoutId);
        if (timeoutErr instanceof Error && timeoutErr.name === "AbortError") {
          const err: MaterialDetailError = {
            type: "408_TIMEOUT",
            statusCode: 408,
            message: "Истекло время ожидания при загрузке материала",
            retryable: true,
          };
          setError(err);
        } else {
          const err = handleError(timeoutErr);
          setError(err);
        }
      }
    } catch (err) {
      const materialError = handleError(err);
      setError(materialError);
    } finally {
      setLoading(false);
    }
  }, [id, isValidId, handleError]);

  // Initial load
  useEffect(() => {
    fetchMaterial();
  }, [id, fetchMaterial]);

  // Handle retry
  const handleRetry = useCallback(() => {
    setRetryCount((prev) => prev + 1);
    fetchMaterial();
  }, [fetchMaterial]);

  // Handle navigation back
  const handleNavigateBack = useCallback(() => {
    navigate("/dashboard/student/materials");
  }, [navigate]);

  // Handle download
  const handleDownload = useCallback(async () => {
    if (!material?.file) {
      showError("Файл не найден");
      return;
    }

    try {
      const response = await fetch(
        `/api/materials/materials/${material.id}/download/`,
        {
          headers: {
            Authorization: `Token ${localStorage.getItem("authToken") || ""}`,
          },
        }
      );

      if (!response.ok) {
        if (response.status === 404) {
          showError("Файл не найден на сервере");
        } else if (response.status === 403) {
          showError("У вас нет доступа к этому файлу");
        } else {
          showError("Ошибка при скачивании файла");
        }
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = material.file.split("/").pop() || "material";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showSuccess("Файл успешно скачан");
    } catch (err) {
      logger.error("Download error:", err);
      if (err instanceof Error && err.message.includes("Network")) {
        showError("Ошибка сети при скачивании файла. Проверьте подключение.");
      } else {
        showError("Ошибка при скачивании файла");
      }
    }
  }, [material?.file, material?.id, showError, showSuccess]);

  // Render error state
  if (error) {
    return (
      <ErrorFallback
        error={error}
        onRetry={handleRetry}
        onNavigateBack={handleNavigateBack}
      />
    );
  }

  // Render loading state
  if (loading) {
    return (
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <StudentSidebar />
          <SidebarInset>
            <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
              <SidebarTrigger />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleNavigateBack}
                aria-label="Вернуться к списку материалов"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Назад
              </Button>
            </header>

            <main className="p-6">
              <div className="max-w-4xl mx-auto">
                <div className="space-y-4">
                  <MaterialSkeleton count={1} />
                  <MaterialSkeleton count={3} />
                </div>
              </div>
            </main>
          </SidebarInset>
        </div>
      </SidebarProvider>
    );
  }

  // Render empty state (no material and no error)
  if (!material) {
    return (
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <StudentSidebar />
          <SidebarInset>
            <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
              <SidebarTrigger />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleNavigateBack}
                aria-label="Вернуться к списку материалов"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Назад
              </Button>
            </header>

            <main className="p-6">
              <EmptyState
                title="Материал не найден"
                description="Материал не загрузился. Попробуйте обновить страницу или вернитесь к списку материалов."
                icon={<FileText className="w-8 h-8 text-muted-foreground" />}
                action={
                  <Button
                    type="button"
                    onClick={handleNavigateBack}
                    variant="outline"
                  >
                    К списку материалов
                  </Button>
                }
              />
            </main>
          </SidebarInset>
        </div>
      </SidebarProvider>
    );
  }

  // Render material detail
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <StudentSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleNavigateBack}
              aria-label="Вернуться к списку материалов"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Назад
            </Button>
          </header>

          <main className="p-6">
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Header card */}
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <CardTitle className="text-3xl">
                          {material.title}
                        </CardTitle>
                        <Badge
                          variant={
                            material.status === "active"
                              ? "default"
                              : "secondary"
                          }
                        >
                          {material.status === "active"
                            ? "Активно"
                            : "Черновик"}
                        </Badge>
                      </div>
                      <CardDescription>{material.description}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-sm">
                      <p className="text-muted-foreground">Предмет</p>
                      <p className="font-medium">{material.subject_name}</p>
                    </div>
                    <div className="text-sm">
                      <p className="text-muted-foreground">Тип</p>
                      <p className="font-medium capitalize">{material.type}</p>
                    </div>
                    <div className="text-sm">
                      <p className="text-muted-foreground">Уровень</p>
                      <p className="font-medium">Уровень {material.difficulty_level}</p>
                    </div>
                    <div className="text-sm">
                      <p className="text-muted-foreground">Автор</p>
                      <p className="font-medium flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {material.author_name}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Content card */}
              {material.content && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Содержание</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="prose prose-sm max-w-none">
                      {material.content}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Files section */}
              {(material.file || material.video_url) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Материалы</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {material.file && (
                      <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm font-medium truncate">
                            {material.file.split("/").pop() || "Файл"}
                          </span>
                        </div>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={handleDownload}
                          aria-label="Скачать файл"
                        >
                          <Download className="w-4 h-4 mr-1" />
                          Скачать
                        </Button>
                      </div>
                    )}

                    {material.video_url && (
                      <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                        <div className="flex items-center gap-2">
                          <Video className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm font-medium">Видео</span>
                        </div>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            window.open(material.video_url, "_blank")
                          }
                          aria-label="Открыть видео"
                        >
                          <Eye className="w-4 h-4 mr-1" />
                          Смотреть
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Progress section */}
              {material.progress && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Ваш прогресс</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Завершено</span>
                        <Badge
                          variant={
                            material.progress.is_completed
                              ? "default"
                              : "secondary"
                          }
                        >
                          {material.progress.progress_percentage}%
                        </Badge>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className="bg-primary rounded-full h-2 transition-all"
                          style={{
                            width: `${material.progress.progress_percentage}%`,
                          }}
                        />
                      </div>
                      {material.progress.time_spent > 0 && (
                        <p className="text-sm text-muted-foreground">
                          Время изучения: {material.progress.time_spent} минут
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Action buttons */}
              <div className="flex gap-2 justify-center">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleNavigateBack}
                  aria-label="Вернуться к списку материалов"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  К списку материалов
                </Button>
                <Button
                  type="button"
                  onClick={() => {
                    /* Handle submission */
                  }}
                  aria-label="Отправить ответ на материал"
                >
                  <Send className="w-4 h-4 mr-2" />
                  Отправить ответ
                </Button>
              </div>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
