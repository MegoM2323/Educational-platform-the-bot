import { Card } from "@/components/ui/card";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { Users, CreditCard, Repeat } from "lucide-react";
import { useParentChildren, useInitiatePayment } from "@/hooks/useParent";
import { parentDashboardAPI } from "@/integrations/api/dashboard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";
import { PaymentStatusBadge, PaymentStatus } from "@/components/PaymentStatusBadge";

const Children = () => {
  const navigate = useNavigate();
  const { data: children, isLoading } = useParentChildren();

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ParentSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Мои дети</h1>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <Card className="p-6">
              {isLoading ? (
                <div>Загрузка...</div>
              ) : (
                <div className="grid md:grid-cols-2 gap-4">
                  {children?.map((child) => (
                    <Card key={child.id} className="p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold">{child.full_name || child.name}</div>
                        <Badge variant="outline">{child.grade}</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">Цель: {child.goal || '—'}</div>
                      <div className="space-y-2">
                        {child.subjects.map((s) => (
                          <div key={s.enrollment_id || s.id} className="flex items-center justify-between p-2 bg-muted rounded">
                            <div className="flex-1">
                              <div className="font-medium text-sm">{s.name}</div>
                              <div className="text-xs text-muted-foreground">Преподаватель: {s.teacher_name}</div>
                              {s.subscription_status === 'cancelled' && s.expires_at && (
                                <div className="text-xs text-orange-600 dark:text-orange-400 mt-1">
                                  Доступ до: {new Date(s.expires_at).toLocaleString('ru-RU', {
                                    year: 'numeric',
                                    month: '2-digit',
                                    day: '2-digit',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })}
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <PaymentStatusBadge status={s.payment_status as PaymentStatus} size="sm" />
                              {s.enrollment_id && (
                                <PayButton
                                  childId={child.id}
                                  enrollmentId={s.enrollment_id}
                                  subjectName={s.name}
                                  teacherName={s.teacher_name}
                                  hasSubscription={s.has_subscription || false}
                                  paymentStatus={s.payment_status}
                                  subscriptionStatus={s.subscription_status}
                                  expiresAt={s.expires_at}
                                  nextPaymentDate={s.next_payment_date}
                                />
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="pt-2">
                        <Button variant="outline" onClick={() => navigate(`/dashboard/parent/children/${child.id}`)}>Детали</Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </Card>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

function PayButton({
  childId,
  enrollmentId,
  subjectName,
  teacherName,
  hasSubscription,
  paymentStatus,
  subscriptionStatus,
  expiresAt,
  nextPaymentDate
}: {
  childId: number;
  enrollmentId: number;
  subjectName: string;
  teacherName: string;
  hasSubscription: boolean;
  paymentStatus: string;
  subscriptionStatus?: string;
  expiresAt?: string;
  nextPaymentDate?: string;
}) {
  // Сумма будет определена на бэкенде в зависимости от режима
  const payment = useInitiatePayment(childId, enrollmentId, {
    description: `Оплата за предмет "${subjectName}" (преподаватель: ${teacherName})`,
    create_subscription: true,
  });

  // Проверяем, находится ли следующий платеж в будущем
  const isNextPaymentInFuture = nextPaymentDate ? new Date(nextPaymentDate) > new Date() : false;

  // Если подписка отменена и есть дата истечения - показываем дату истечения доступа
  if (subscriptionStatus === 'cancelled' && expiresAt) {
    return (
      <div className="flex flex-col items-end gap-1">
        <Badge variant="secondary" className="text-xs bg-orange-100 text-orange-800">Доступ ограничен</Badge>
        <div className="text-xs text-orange-600 dark:text-orange-400 text-right">
          До: {new Date(expiresAt).toLocaleString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>
    );
  }

  // Если предмет оплачен И следующий платеж еще не наступил - показываем что предмет активен
  if (paymentStatus === 'paid' && isNextPaymentInFuture) {
    return (
      <div className="flex flex-col items-end gap-1">
        <Badge variant="secondary" className="text-xs bg-green-100 text-green-800">Активен</Badge>
        <Button
          size="sm"
          variant="outline"
          onClick={async () => {
            const confirmed = window.confirm(
              `Отключить автосписание для предмета "${subjectName}"?`
            );
            if (!confirmed) return;

            try {
              await parentDashboardAPI.cancelSubscription(childId, enrollmentId);
              window.location.reload();
            } catch (err) {
              console.error('Cancel subscription error:', err);
            }
          }}
        >
          Отключить автосписание
        </Button>
      </div>
    );
  }

  // Если есть активная подписка и оплачено - показываем кнопку "Отключить автосписание"
  if (hasSubscription && paymentStatus === 'paid') {
    return (
      <div className="flex flex-col items-end gap-1">
        <Badge variant="secondary" className="text-xs">Автосписание активно</Badge>
        <Button
          size="sm"
          variant="outline"
          onClick={async () => {
            const confirmed = window.confirm(
              `Отключить автосписание для предмета "${subjectName}"?`
            );
            if (!confirmed) return;

            try {
              await parentDashboardAPI.cancelSubscription(childId, enrollmentId);
              window.location.reload();
            } catch (err) {
              console.error('Cancel subscription error:', err);
            }
          }}
        >
          Отключить автосписание
        </Button>
      </div>
    );
  }

  // Если платеж просрочен или нет платежа - показываем кнопку "Подключить предмет"
  return (
    <Button
      size="sm"
      onClick={() => payment.mutate()}
      disabled={payment.isPending}
      variant={paymentStatus === 'overdue' ? 'destructive' : 'default'}
    >
      <CreditCard className="w-4 h-4 mr-1" />
      {paymentStatus === 'overdue' ? 'Оплатить предмет' : 'Подключить предмет'}
    </Button>
  );
}

export default Children;
