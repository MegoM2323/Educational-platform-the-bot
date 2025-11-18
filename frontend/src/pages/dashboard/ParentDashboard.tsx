import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { Users, FileText, MessageCircle, Bell, TrendingUp, Calendar, CreditCard, AlertCircle, ExternalLink } from "lucide-react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { parentDashboardAPI } from "@/integrations/api/dashboard";
import { useToast } from "@/hooks/use-toast";
import { useErrorNotification, useSuccessNotification } from "@/components/NotificationSystem";
import { DashboardSkeleton, ErrorState, EmptyState } from "@/components/LoadingStates";
import { PaymentStatusBadge, PaymentStatus } from "@/components/PaymentStatusBadge";
import { useParentDashboard } from "@/hooks/useParent";

// Интерфейсы для данных
interface Child {
  id: number;
  name: string;
  grade: string;
  goal: string;
  tutor_name: string;
  progress_percentage: number;
  avatar?: string;
  subjects: Array<{
    id: number;
    enrollment_id: number;
    name: string;
    teacher_name: string;
    teacher_id: number;
    payment_status: PaymentStatus;
    next_payment_date?: string;
    has_subscription?: boolean;
  }>;
}

interface Report {
  id: number;
  child_name: string;
  subject: string;
  title: string;
  content: string;
  teacher_name: string;
  created_at: string;
  type: 'progress' | 'behavior' | 'achievement';
}

interface DashboardData {
  children: Child[];
  reports: Report[];
  statistics: {
    total_children: number;
    average_progress: number;
    completed_payments: number;
    pending_payments: number;
    overdue_payments: number;
  };
}

const ParentDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();

  // Use TanStack Query instead of useState
  const {
    data: dashboardData,
    isLoading: loading,
    error: queryError,
    refetch
  } = useParentDashboard();

  const error = queryError?.message || null;

  // Debounced refetch when window regains focus
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    const handleFocus = () => {
      if (document.hasFocus()) {
        // Debounce: wait 1 second before refetching
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          refetch();
        }, 1000);
      }
    };

    window.addEventListener('focus', handleFocus);
    return () => {
      window.removeEventListener('focus', handleFocus);
      clearTimeout(timeoutId);
    };
  }, [refetch]);

  const handlePaymentClick = async (childId: number, enrollmentId: number | undefined, subjectName: string, teacherName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!enrollmentId) {
      showError("Ошибка: не указан идентификатор зачисления. Обновите страницу.");
      return;
    }
    
    try {
      // Сумма будет определена на бэкенде в зависимости от режима
      const paymentData = await parentDashboardAPI.initiatePayment(childId, enrollmentId, {
        description: `Оплата за предмет "${subjectName}" (преподаватель: ${teacherName})`,
        create_subscription: true
      });
      
      const paymentUrl = paymentData?.confirmation_url || paymentData?.payment_url || paymentData?.return_url;
      
      if (paymentUrl) {
        window.location.href = paymentUrl;
      } else {
        showError("Не удалось создать платеж. Проверьте настройки ЮКассы.");
      }
    } catch (err: any) {
      console.error('Payment error:', err);
      showError(err.message || "Произошла ошибка при создании платежа");
    }
  };

  const handleCancelSubscription = async (childId: number, enrollmentId: number) => {
    try {
      const result = await parentDashboardAPI.cancelSubscription(childId, enrollmentId);

      // Проверяем ответ от API
      if (result && (result.success || result.message)) {
        showSuccess(result.message || "Подписка успешно отменена");
        // Обновляем данные дашборда
        await refetch();
      } else if (result?.error) {
        showError(result.error);
      } else {
        // Если ответ не содержит success/message, но и нет ошибки, считаем успешным
        showSuccess("Подписка успешно отменена");
        await refetch();
      }
    } catch (err: any) {
      console.error('Cancel subscription error:', err);
      const errorMessage = err.response?.data?.error || err.message || "Произошла ошибка при отмене подписки";
      showError(errorMessage);
    }
  };

  const handleChildClick = (childId: number) => {
    navigate(`/dashboard/parent/children/${childId}`);
  };

  const handleReportClick = (reportId: number) => {
    navigate(`/dashboard/parent/reports/${reportId}`);
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ParentSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
            <Button variant="outline" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground rounded-full text-xs flex items-center justify-center">
                2
              </span>
            </Button>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold" aria-label="Личный кабинет родителя">Личный кабинет родителя</h1>
                <p className="text-muted-foreground">Следите за успехами ваших детей</p>
              </div>

              {/* Обработка ошибок */}
              {error && (
                <ErrorState
                  error={error}
                  onRetry={() => refetch()}
                />
              )}

              {/* Загрузка */}
              {loading && <DashboardSkeleton />}

              {/* Основной контент */}
              {!loading && !error && dashboardData && (
                <>
                  {/* Children Profiles */}
                  <Card className="p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <Users className="w-5 h-5 text-primary" />
                      <h3 className="text-xl font-bold">Профили детей</h3>
                      <Badge variant="outline">{dashboardData.children?.length || 0} детей</Badge>
                    </div>
                    <div className="grid md:grid-cols-2 gap-4">
                      {dashboardData.children && dashboardData.children.length > 0 ? (
                        dashboardData.children.map((child) => (
                        <Card 
                          key={child.id} 
                          className="p-4 hover:border-primary transition-colors cursor-pointer"
                          onClick={() => handleChildClick(child.id)}
                        >
                          <div className="flex items-start gap-4">
                            <Avatar className="w-16 h-16">
                              <AvatarImage src={child.avatar} />
                              <AvatarFallback className="gradient-primary text-primary-foreground text-lg">
                                {child.name.split(' ').map(n => n[0]).join('')}
                              </AvatarFallback>
                            </Avatar>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className="font-bold text-lg">{child.name}</h4>
                                <Badge variant="outline">{child.grade} класс</Badge>
                              </div>
                              <p className="text-sm text-muted-foreground mb-3">{child.goal}</p>
                              <div className="grid grid-cols-2 gap-2 text-sm">
                                <div>
                                  <div className="text-muted-foreground">Тьютор</div>
                                  <div className="font-medium">{child.tutor_name}</div>
                                </div>
                                <div>
                                  <div className="text-muted-foreground">Прогресс</div>
                                  <div className="font-medium text-success">{child.progress_percentage}%</div>
                                </div>
                              </div>
                              {/* Предметы с кнопками оплаты */}
                              <div className="mt-3 space-y-2">
                                {child.subjects.slice(0, 2).map((subject) => (
                                  <div
                                    key={subject.enrollment_id || subject.id}
                                    className={`flex items-center justify-between p-3 rounded-lg border-2 transition-all ${
                                      subject.payment_status === 'no_payment' || subject.payment_status === 'overdue'
                                        ? 'bg-orange-50 border-orange-400 shadow-md dark:bg-orange-950/20 dark:border-orange-800'
                                        : 'bg-muted border-transparent'
                                    }`}
                                  >
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 mb-1">
                                        <div className="text-sm font-medium">{subject.name}</div>
                                        {(subject.payment_status === 'no_payment' || subject.payment_status === 'overdue') && (
                                          <Badge variant="destructive" className="text-xs font-bold bg-orange-600 hover:bg-orange-700 animate-pulse">
                                            ТРЕБУЕТСЯ ОПЛАТА
                                          </Badge>
                                        )}
                                      </div>
                                      <div className="text-xs text-muted-foreground space-y-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                          <span>Преподаватель: {subject.teacher_name}</span>
                                          <PaymentStatusBadge status={subject.payment_status} size="sm" />
                                          {subject.has_subscription && (
                                            <Badge variant="secondary" className="text-xs">Подписка активна</Badge>
                                          )}
                                        </div>
                                        {subject.next_payment_date && (
                                          <div className="text-xs text-blue-600">
                                            Следующий платеж: {new Date(subject.next_payment_date).toLocaleDateString('ru-RU', {
                                              year: 'numeric',
                                              month: 'long',
                                              day: 'numeric'
                                            })}
                                          </div>
                                        )}
                                        {subject.payment_status === 'no_payment' && (
                                          <div className="text-xs text-orange-700 dark:text-orange-400 font-medium mt-1">
                                            Нажмите "Подключить предмет" для оплаты
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                    <div className="flex gap-2 items-center">
                                      {subject.has_subscription && subject.payment_status === 'paid' ? (
                                        // Если есть активная подписка И платеж оплачен - показываем только кнопку "Остановить оплату"
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          onClick={async (e) => {
                                            e.stopPropagation();
                                            if (!subject.enrollment_id) {
                                              showError("Ошибка: не указан идентификатор зачисления. Обновите страницу.");
                                              return;
                                            }
                                            
                                            const confirmed = window.confirm(
                                              `Отключить предмет "${subject.name}"?`
                                            );
                                            
                                            if (!confirmed) return;
                                            
                                            try {
                                              await handleCancelSubscription(child.id, subject.enrollment_id);
                                            } catch (err) {
                                              console.error('Cancel subscription error:', err);
                                              showError("Произошла ошибка при отключении предмета");
                                            }
                                          }}
                                        >
                                          Отключить предмет
                                        </Button>
                                      ) : (
                                        // Если нет подписки или платеж не оплачен - показываем кнопку "Оплатить"
                                        <Button
                                          size="sm"
                                          variant={
                                            subject.payment_status === 'overdue' || subject.payment_status === 'no_payment'
                                              ? 'default'
                                              : subject.payment_status === 'waiting_for_payment'
                                              ? 'default'
                                              : 'default'
                                          }
                                          className={
                                            subject.payment_status === 'no_payment' || subject.payment_status === 'overdue'
                                              ? 'bg-orange-600 hover:bg-orange-700 text-white font-semibold shadow-lg border-2 border-orange-700 dark:bg-orange-600 dark:hover:bg-orange-700'
                                              : ''
                                          }
                                          disabled={!subject.enrollment_id}
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            if (!subject.enrollment_id) {
                                              showError("Ошибка: не указан идентификатор зачисления. Обновите страницу.");
                                              return;
                                            }
                                            handlePaymentClick(
                                              child.id,
                                              subject.enrollment_id,
                                              subject.name,
                                              subject.teacher_name,
                                              e
                                            );
                                          }}
                                        >
                                          <CreditCard className="w-4 h-4 mr-1" />
                                          {subject.payment_status === 'waiting_for_payment' ? 'Перейти к оплате' : 'Подключить предмет'}
                                        </Button>
                                      )}
                                    </div>
                                  </div>
                                ))}
                                {child.subjects.length > 2 && (
                                  <div className="text-xs text-muted-foreground text-center">
                                    +{child.subjects.length - 2} других предметов
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </Card>
                        ))
                      ) : (
                        <div className="col-span-2">
                          <EmptyState
                            title="Нет зарегистрированных детей"
                            description="Пока нет зарегистрированных детей. Обратитесь к администратору для регистрации."
                            icon={<Users className="w-8 h-8 text-muted-foreground" />}
                          />
                        </div>
                      )}
                    </div>
                  </Card>

                  <div className="grid md:grid-cols-2 gap-6">
                    {/* Recent Reports */}
                    <Card className="p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <FileText className="w-5 h-5 text-primary" />
                        <h3 className="text-xl font-bold">Последние отчёты</h3>
                      </div>
                      <div className="space-y-3">
                        {(dashboardData.reports ?? []).slice(0, 3).map((report) => (
                          <div 
                            key={report.id} 
                            className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer"
                            onClick={() => handleReportClick(report.id)}
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div>
                                <div className="font-medium">{report.child_name}</div>
                                <div className="text-sm text-muted-foreground">{report.subject}</div>
                                <div className="text-xs text-muted-foreground mt-1">{report.title}</div>
                              </div>
                              <Badge variant={
                                report.type === "achievement" ? "default" : 
                                report.type === "behavior" ? "secondary" : 
                                "outline"
                              }>
                                {report.type === "achievement" ? "Достижение" : 
                                 report.type === "behavior" ? "Поведение" : 
                                 "Прогресс"}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <Calendar className="w-3 h-3" />
                              {new Date(report.created_at).toLocaleDateString('ru-RU')}
                              <span>•</span>
                              <span>{report.teacher_name}</span>
                            </div>
                          </div>
                        ))}
                        {(dashboardData.reports ?? []).length === 0 && (
                          <EmptyState
                            title="Нет новых отчетов"
                            description="Пока нет отчетов от преподавателей. Ожидайте новых отчетов о прогрессе вашего ребенка."
                            icon={<FileText className="w-8 h-8 text-muted-foreground" />}
                          />
                        )}
                      </div>
                      <Button 
                        variant="outline" 
                        className="w-full mt-4"
                        onClick={() => navigate('/dashboard/parent/reports')}
                      >
                        Смотреть все отчёты
                      </Button>
                    </Card>

                    {/* Statistics */}
                    <Card className="p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <TrendingUp className="w-5 h-5 text-primary" />
                        <h3 className="text-xl font-bold">Статистика</h3>
                      </div>
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="p-3 bg-muted rounded-lg">
                            <div className="text-2xl font-bold text-primary">{dashboardData.statistics.total_children}</div>
                            <div className="text-sm text-muted-foreground">Детей</div>
                          </div>
                          <div className="p-3 bg-muted rounded-lg">
                            <div className="text-2xl font-bold text-success">{dashboardData.statistics.average_progress}%</div>
                            <div className="text-sm text-muted-foreground">Средний прогресс</div>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Оплачено</span>
                            <span className="font-medium text-success">{dashboardData.statistics.completed_payments}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span>Ожидает оплаты</span>
                            <span className="font-medium text-warning">{dashboardData.statistics.pending_payments}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span>Просрочено</span>
                            <span className="font-medium text-destructive">{dashboardData.statistics.overdue_payments}</span>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>

                  {/* Quick Actions */}
                  <Card className="p-6">
                    <h3 className="text-xl font-bold mb-4">Быстрые действия</h3>
                    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={() => navigate('/dashboard/parent/children')}
                      >
                        <Users className="w-6 h-6" />
                        <span>Управление детьми</span>
                      </Button>
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={() => navigate('/dashboard/parent/payments')}
                      >
                        <CreditCard className="w-6 h-6" />
                        <span>Оплаты</span>
                      </Button>
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={() => navigate('/dashboard/parent/reports')}
                      >
                        <FileText className="w-6 h-6" />
                        <span>Отчёты</span>
                      </Button>
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={() => navigate('/dashboard/parent/statistics')}
                      >
                        <TrendingUp className="w-6 h-6" />
                        <span>Статистика</span>
                      </Button>
                    </div>
                  </Card>
                </>
              )}
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default ParentDashboard;
