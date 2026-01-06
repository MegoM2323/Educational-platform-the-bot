import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BookOpen,
  MessageCircle,
  Target,
  CheckCircle,
  Clock,
  ExternalLink,
  AlertCircle,
  WifiOff,
  RefreshCw,
} from "lucide-react";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import {
  useErrorNotification,
  useSuccessNotification,
} from "@/components/NotificationSystem";
import {
  DashboardSkeleton,
  ErrorState,
  EmptyState,
  LoadingWithRetry,
} from "@/components/LoadingStates";
import { useErrorReporter } from "@/components/ErrorHandlingProvider";
import { useNetworkStatus } from "@/components/NetworkStatusHandler";
import { FallbackUI, OfflineContent } from "@/components/FallbackUI";
import {
  useStudentDashboard,
  useStudentDashboardRealTime,
} from "@/hooks/useStudent";
import { ProfileCard } from "@/components/ProfileCard";
import { useProfile } from "@/hooks/useProfile";
import { BookingWidget } from "@/components/dashboard/BookingWidget";

// Интерфейсы для данных
interface Material {
  id: number;
  title: string;
  description?: string;
  type?: string;
  created_at: string;
  file_url?: string;
  progress?: {
    is_completed: boolean;
    progress_percentage: number;
    time_spent: number;
    started_at: string | null;
    completed_at: string | null;
    last_accessed: string | null;
  };
}

interface DashboardData {
  student_info: {
    id: number;
    name: string;
    role: string;
    avatar?: string;
  };
  materials_by_subject: {
    [subjectName: string]: {
      subject_info: {
        id: number;
        name: string;
        color?: string;
        teacher?: {
          id: number;
          full_name: string;
        };
      };
      materials: Array<{
        id: number;
        title: string;
        description?: string;
        created_at: string;
        type?: string;
        status?: string;
        progress_percentage?: number;
      }>;
    };
  };
  progress_statistics?: {
    total_materials: number;
    completed_materials: number;
    in_progress_materials: number;
    not_started_materials: number;
    completion_percentage: number;
    average_progress: number;
    total_time_spent: number;
  };
  recent_activity: Array<{
    id: number;
    title: string;
    deadline: string;
    status: "pending" | "completed" | "overdue";
  }>;
  general_chat: {
    id: number;
    name: string;
    last_message?: string;
  };
}

const StudentDashboard = () => {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();
  const { reportError, reportNetworkError } = useErrorReporter();
  const networkStatus = useNetworkStatus();

  // Используем TanStack Query для кеширования данных
  const {
    data: dashboardData,
    isLoading: loading,
    error: queryError,
    refetch: fetchDashboardData,
  } = useStudentDashboard();

  // Получаем данные профиля студента
  const {
    profileData,
    isLoading: profileLoading,
    error: profileError,
    refetch: refetchProfile,
  } = useProfile();

  // Подключаем WebSocket для real-time обновлений
  useStudentDashboardRealTime(user?.id);

  const error = queryError?.message || null;

  const handleMaterialClick = (materialId: number) => {
    if (networkStatus.isOnline) {
      navigate(`/dashboard/student/materials/${materialId}`);
    }
  };

  const handleMaterialKeyDown = (
    e: React.KeyboardEvent,
    materialId: number,
  ) => {
    if ((e.key === "Enter" || e.key === " ") && networkStatus.isOnline) {
      e.preventDefault();
      handleMaterialClick(materialId);
    }
  };

  const handleProfileEdit = () => {
    if (networkStatus.isOnline) {
      navigate("/profile/student");
    }
  };

  const handleProfileRetry = () => {
    refetchProfile();
  };

  const handleRetryConnection = () => {
    fetchDashboardData();
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <StudentSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
          </header>
          <main className="px-6 pb-6 pt-4">
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold">
                  Привет, {user?.first_name || "Студент"}! 👋
                </h1>
                <p className="text-muted-foreground">
                  Продолжай двигаться к своей цели
                </p>
              </div>

              {/* Секция профиля студента */}
              {profileLoading ? (
                <Card className="p-6">
                  <div className="space-y-4">
                    <Skeleton className="h-24 w-24 rounded-full" />
                    <Skeleton className="h-8 w-1/3" />
                    <Skeleton className="h-4 w-1/2" />
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-5/6" />
                    </div>
                  </div>
                </Card>
              ) : profileError ? (
                <ErrorState
                  title="Не удалось загрузить профиль"
                  description={
                    profileError.message ||
                    "Произошла ошибка при загрузке данных профиля. Попробуйте ещё раз."
                  }
                  onRetry={handleProfileRetry}
                />
              ) : profileData?.user ? (
                <ProfileCard
                  userName={
                    profileData.user.full_name || profileData.user.email
                  }
                  userEmail={profileData.user.email}
                  userRole="student"
                  profileData={{
                    grade: profileData.user.grade || "Не указан",
                    learningGoal:
                      profileData.user.learning_goal || "Не указана",
                    progressPercentage:
                      dashboardData?.progress_statistics
                        ?.completion_percentage ?? 0,
                    subjectsCount:
                      Object.keys(dashboardData?.materials_by_subject || {})
                        .length || 0,
                  }}
                  onEdit={handleProfileEdit}
                />
              ) : null}

              {/* Обработка офлайн режима - показываем banner и disabled контент */}
              {!networkStatus.isOnline && (
                <Card className="p-4 border-amber-500 bg-amber-50 dark:bg-amber-950/30">
                  <div className="flex items-center gap-3">
                    <div className="flex-shrink-0">
                      <WifiOff className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-amber-900 dark:text-amber-100">
                        Вы находитесь в режиме офлайн
                      </h3>
                      <p className="text-sm text-amber-800 dark:text-amber-200">
                        {dashboardData
                          ? "Отображаются кешированные данные. Некоторые функции недоступны."
                          : "Кешированные данные отсутствуют. Подключитесь к интернету для загрузки информации."}
                      </p>
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleRetryConnection}
                      className="flex-shrink-0"
                      variant="outline"
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Обновить
                    </Button>
                  </div>
                </Card>
              )}

              {/* Обработка ошибок и загрузки */}
              <LoadingWithRetry
                isLoading={loading}
                error={!networkStatus.isOnline && dashboardData ? null : error}
                onRetry={fetchDashboardData}
              >
                {dashboardData && (
                  <div
                    className={!networkStatus.isOnline ? "opacity-75" : ""}
                    aria-disabled={!networkStatus.isOnline}
                    aria-label={
                      !networkStatus.isOnline
                        ? "Контент недоступен в режиме офлайн. Отображаются кешированные данные."
                        : undefined
                    }
                  >
                    <div className="grid lg:grid-cols-3 gap-6">
                      {/* Progress Section */}
                      <Card className="p-6 gradient-primary text-primary-foreground shadow-glow lg:col-span-2">
                        <div className="flex items-center gap-4 mb-4">
                          <div className="w-12 h-12 bg-primary-foreground/20 rounded-full flex items-center justify-center">
                            <Target className="w-6 h-6" />
                          </div>
                          <div className="flex-1">
                            <h3 className="text-xl font-bold">Твой прогресс</h3>
                            <p className="text-primary-foreground/80">
                              Продолжай двигаться к цели
                            </p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>
                              Выполнено материалов:{" "}
                              {dashboardData.progress_statistics
                                ?.completed_materials ?? 0}{" "}
                              из{" "}
                              {dashboardData.progress_statistics
                                ?.total_materials ?? 0}
                            </span>
                            <span className="font-bold">
                              {dashboardData.progress_statistics
                                ?.completion_percentage ?? 0}
                              %
                            </span>
                          </div>
                          <Progress
                            value={
                              dashboardData.progress_statistics
                                ?.completion_percentage ?? 0
                            }
                            className="h-3 bg-primary-foreground/20"
                          />
                        </div>
                        <div className="grid grid-cols-3 gap-4 mt-6">
                          <div className="text-center">
                            <div className="text-2xl font-bold">
                              {dashboardData.progress_statistics
                                ?.completed_materials ?? 0}
                            </div>
                            <div className="text-sm text-primary-foreground/80">
                              Завершено
                            </div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold">
                              {dashboardData.progress_statistics
                                ?.in_progress_materials ?? 0}
                            </div>
                            <div className="text-sm text-primary-foreground/80">
                              В процессе
                            </div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold">
                              {Math.round(
                                dashboardData.progress_statistics
                                  ?.average_progress ?? 0,
                              )}
                              %
                            </div>
                            <div className="text-sm text-primary-foreground/80">
                              Средний прогресс
                            </div>
                          </div>
                        </div>
                      </Card>

                      {/* Booking Widget */}
                      <div className="lg:col-span-1">
                        <BookingWidget disabled={!networkStatus.isOnline} />
                      </div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                      {/* Current Materials */}
                      <Card className="p-6">
                        <div className="flex items-center gap-3 mb-4">
                          <BookOpen className="w-5 h-5 text-primary" />
                          <h3 className="text-xl font-bold">
                            Текущие материалы
                          </h3>
                        </div>
                        <div className="space-y-3">
                          {Object.values(
                            dashboardData?.materials_by_subject || {},
                          )
                            .flatMap((subjectData) => subjectData.materials)
                            .slice(0, 3)
                            .map((material) => (
                              <button
                                key={material.id}
                                type="button"
                                className="flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer text-left w-full disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-muted"
                                onClick={() => handleMaterialClick(material.id)}
                                onKeyDown={(e) =>
                                  handleMaterialKeyDown(e, material.id)
                                }
                                disabled={!networkStatus.isOnline}
                                aria-label={`Материал: ${material.title}. ${material.description || "Без описания"}. ${material.progress?.progress_percentage ? `Прогресс: ${material.progress.progress_percentage}%` : "Не начато"}`}
                                title={
                                  !networkStatus.isOnline
                                    ? "Недоступно в режиме офлайн"
                                    : ""
                                }
                              >
                                <div className="flex-1">
                                  <div className="font-medium">
                                    {material.title}
                                  </div>
                                  <div className="text-sm text-muted-foreground">
                                    {material.description || "Без описания"}
                                  </div>
                                  {(material.progress?.progress_percentage ??
                                    0) > 0 && (
                                    <div className="mt-1">
                                      <Progress
                                        value={
                                          material.progress
                                            ?.progress_percentage ?? 0
                                        }
                                        className="h-2"
                                      />
                                      <span className="text-xs text-muted-foreground">
                                        {material.progress
                                          ?.progress_percentage ?? 0}
                                        % завершено
                                      </span>
                                    </div>
                                  )}
                                </div>
                                <div className="flex items-center gap-2">
                                  {material.type === "file" && (
                                    <ExternalLink
                                      className="w-4 h-4 text-muted-foreground"
                                      aria-hidden="true"
                                    />
                                  )}
                                  <Badge
                                    variant={
                                      material.progress?.is_completed
                                        ? "default"
                                        : (material.progress
                                              ?.progress_percentage ?? 0) > 0
                                          ? "secondary"
                                          : "outline"
                                    }
                                  >
                                    {material.progress?.is_completed
                                      ? "Завершено"
                                      : (material.progress
                                            ?.progress_percentage ?? 0) > 0
                                        ? "В процессе"
                                        : "Не начато"}
                                  </Badge>
                                </div>
                              </button>
                            ))}
                          {Object.values(
                            dashboardData?.materials_by_subject || {},
                          ).flatMap((subjectData) => subjectData.materials)
                            .length === 0 && (
                            <EmptyState
                              title="Нет доступных материалов"
                              description="Пока нет материалов для изучения. Обратитесь к преподавателю."
                              icon={
                                <BookOpen className="w-8 h-8 text-muted-foreground" />
                              }
                            />
                          )}
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          className="w-full mt-4"
                          onClick={() =>
                            networkStatus.isOnline &&
                            navigate("/dashboard/student/materials")
                          }
                          disabled={!networkStatus.isOnline}
                          title={
                            !networkStatus.isOnline
                              ? "Недоступно в режиме офлайн"
                              : ""
                          }
                          aria-label="Просмотреть все доступные материалы"
                        >
                          Смотреть все материалы
                        </Button>
                      </Card>

                      {/* Subjects Section */}
                      <Card className="p-6">
                        <div className="flex items-center gap-3 mb-4">
                          <BookOpen className="w-5 h-5 text-primary" />
                          <h3 className="text-xl font-bold">Мои предметы</h3>
                          <Badge variant="secondary" className="ml-auto">
                            {
                              Object.keys(
                                dashboardData?.materials_by_subject || {},
                              ).length
                            }
                          </Badge>
                        </div>
                        {loading ? (
                          <div>Загрузка...</div>
                        ) : (
                          <div className="space-y-3">
                            {Object.values(
                              dashboardData?.materials_by_subject || {},
                            ).map((subjectData) => (
                              <div
                                key={subjectData.subject_info.id}
                                className="flex items-center justify-between p-3 bg-muted rounded-lg"
                              >
                                <div>
                                  <div className="font-medium">
                                    {subjectData.subject_info.name}
                                  </div>
                                  <div className="text-sm text-muted-foreground">
                                    Преподаватель:{" "}
                                    {subjectData.subject_info.teacher
                                      ?.full_name || "Не назначен"}
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    Материалов: {subjectData.materials.length}
                                  </div>
                                </div>
                                <Button
                                  type="button"
                                  size="sm"
                                  onClick={() =>
                                    networkStatus.isOnline &&
                                    navigate(
                                      `/dashboard/student/materials?subject=${subjectData.subject_info.id}`,
                                    )
                                  }
                                  disabled={!networkStatus.isOnline}
                                  title={
                                    !networkStatus.isOnline
                                      ? "Недоступно в режиме офлайн"
                                      : ""
                                  }
                                  aria-label={`Материалы по предмету ${subjectData.subject_info.name}`}
                                >
                                  Материалы
                                </Button>
                              </div>
                            ))}
                            {Object.keys(
                              dashboardData?.materials_by_subject || {},
                            ).length === 0 && (
                              <EmptyState
                                title="Нет назначенных предметов"
                                description="Обратитесь к тьютору для назначения предметов."
                                icon={
                                  <BookOpen className="w-8 h-8 text-muted-foreground" />
                                }
                              />
                            )}
                          </div>
                        )}
                      </Card>
                    </div>

                    {/* Recent Assignments */}
                    <Card className="p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <CheckCircle className="w-5 h-5 text-primary" />
                        <h3 className="text-xl font-bold">Последние задания</h3>
                      </div>
                      <div className="space-y-3">
                        {(dashboardData?.recent_activity || [])
                          .slice(0, 3)
                          .map((assignment) => (
                            <div
                              key={assignment.id}
                              className="flex items-center justify-between p-3 bg-muted rounded-lg"
                            >
                              <div className="flex-1">
                                <div className="font-medium">
                                  {assignment.title}
                                </div>
                                <div className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                                  <Clock className="w-3 h-3" />
                                  {assignment.deadline}
                                </div>
                              </div>
                              <Badge
                                variant={
                                  assignment.status === "completed"
                                    ? "default"
                                    : assignment.status === "overdue"
                                      ? "destructive"
                                      : "outline"
                                }
                              >
                                {assignment.status === "completed"
                                  ? "Выполнено"
                                  : assignment.status === "overdue"
                                    ? "Просрочено"
                                    : "В процессе"}
                              </Badge>
                            </div>
                          ))}
                        {(dashboardData?.recent_activity || []).length ===
                          0 && (
                          <EmptyState
                            title="Нет активных заданий"
                            description="Пока нет заданий для выполнения. Ожидайте новых заданий от преподавателя."
                            icon={
                              <CheckCircle className="w-8 h-8 text-muted-foreground" />
                            }
                          />
                        )}
                      </div>
                    </Card>

                    {/* Quick Actions */}
                    <Card className="p-6">
                      <h3 className="text-xl font-bold mb-4">
                        Быстрые действия
                      </h3>
                      <div className="grid sm:grid-cols-2 gap-4">
                        <Button
                          type="button"
                          variant="outline"
                          className="h-auto flex-col gap-2 py-6"
                          onClick={() =>
                            networkStatus.isOnline &&
                            navigate("/dashboard/student/materials")
                          }
                          disabled={!networkStatus.isOnline}
                          title={
                            !networkStatus.isOnline
                              ? "Недоступно в режиме офлайн"
                              : ""
                          }
                          aria-label="Перейти к материалам"
                        >
                          <BookOpen className="w-6 h-6" aria-hidden="true" />
                          <span>Материалы</span>
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          className="h-auto flex-col gap-2 py-6"
                          onClick={() =>
                            networkStatus.isOnline &&
                            navigate("/dashboard/student/forum")
                          }
                          disabled={!networkStatus.isOnline}
                          title={
                            !networkStatus.isOnline
                              ? "Недоступно в режиме офлайн"
                              : ""
                          }
                          aria-label="Перейти к форуму обсуждения"
                        >
                          <MessageCircle
                            className="w-6 h-6"
                            aria-hidden="true"
                          />
                          <span>Форум</span>
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          className="h-auto flex-col gap-2 py-6"
                          onClick={() =>
                            networkStatus.isOnline &&
                            navigate("/dashboard/student/chat")
                          }
                          disabled={!networkStatus.isOnline}
                          title={
                            !networkStatus.isOnline
                              ? "Недоступно в режиме офлайн"
                              : ""
                          }
                          aria-label="Перейти к личным сообщениям"
                        >
                          <MessageCircle
                            className="w-6 h-6"
                            aria-hidden="true"
                          />
                          <span>Сообщения</span>
                        </Button>
                      </div>
                    </Card>
                  </div>
                )}
              </LoadingWithRetry>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default StudentDashboard;
