import { Card } from "@/components/ui/card";
import { logger } from '@/utils/logger';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { Users } from "lucide-react";
import { useParentChildren, useInitiatePayment } from "@/hooks/useParent";
import { parentDashboardAPI } from "@/integrations/api/dashboard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";
import { PaymentStatusBadge, PaymentStatus } from "@/components/PaymentStatusBadge";
import { PayButton } from "@/components/ui/PayButton";

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
                        {child.subjects && child.subjects.length > 0 ? (
                          child.subjects.map((s) => (
                            <div key={s.enrollment_id} className="flex items-center justify-between p-2 bg-muted rounded">
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
                                <PayButtonWrapper
                                  childId={child.id}
                                  enrollmentId={s.enrollment_id}
                                  subjectName={s.name}
                                  teacherName={s.teacher_name}
                                  hasSubscription={s.has_subscription}
                                  paymentStatus={s.payment_status}
                                  subscriptionStatus={s.subscription_status}
                                  expiresAt={s.expires_at}
                                  nextPaymentDate={s.next_payment_date}
                                />
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="text-sm text-muted-foreground text-center py-4">
                            У ребенка еще нет предметов
                          </div>
                        )}
                      </div>
                      <div className="pt-2">
                        <Button type="button" variant="outline" onClick={() => navigate(`/dashboard/parent/children/${child.id}`)}>Детали</Button>
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

function PayButtonWrapper({
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
  const payment = useInitiatePayment(childId, enrollmentId, {
    description: `Оплата за предмет "${subjectName}" (преподаватель: ${teacherName})`,
    create_subscription: true,
  });

  const handleCancel = async () => {
    const confirmed = window.confirm(
      `Отключить автосписание для предмета "${subjectName}"?`
    );
    if (!confirmed) return;

    try {
      await parentDashboardAPI.cancelSubscription(childId, enrollmentId);
      window.location.reload();
    } catch (err) {
      logger.error('Cancel subscription error:', err);
    }
  };

  return (
    <PayButton
      paymentStatus={paymentStatus}
      subscriptionStatus={subscriptionStatus}
      expiresAt={expiresAt}
      nextPaymentDate={nextPaymentDate}
      hasSubscription={hasSubscription}
      onPayClick={() => payment.mutate()}
      onCancelClick={handleCancel}
      isLoading={payment.isPending}
    />
  );
}

export default Children;
