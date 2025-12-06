import { Card } from '@/components/ui/card';
import { logger } from '@/utils/logger';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { ParentSidebar } from '@/components/layout/ParentSidebar';
import { useParams } from 'react-router-dom';
import { useChildSubjects, useChildProgress, useInitiatePayment } from '@/hooks/useParent';
import { parentDashboardAPI } from '@/integrations/api/dashboard';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { CreditCard, Repeat } from 'lucide-react';
import { PaymentStatusBadge, PaymentStatus } from '@/components/PaymentStatusBadge';
import { Badge } from '@/components/ui/badge';

export default function ChildDetail() {
  const params = useParams();
  const childId = Number(params.id);
  const { data: subjects, isLoading: subLoading } = useChildSubjects(childId);
  const { data: progress, isLoading: progLoading } = useChildProgress(childId);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ParentSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold">Детали ребенка</h1>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <div className="grid md:grid-cols-2 gap-4">
              <Card className="p-6">
                <h3 className="text-xl font-bold mb-4">Прогресс</h3>
                {progLoading ? (
                  <div>Загрузка...</div>
                ) : progress ? (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Общий прогресс</span>
                      <span className="font-semibold">{progress.overall_percentage || 0}%</span>
                    </div>
                    <Progress value={progress.overall_percentage || 0} />
                  </div>
                ) : null}
              </Card>
              <Card className="p-6">
                <h3 className="text-xl font-bold mb-4">Предметы и оплата</h3>
                {subLoading ? (
                  <div>Загрузка...</div>
                ) : (
                  <div className="space-y-3">
                    {subjects?.map((s) => (
                      <div key={s.enrollment_id || s.id} className="flex items-center justify-between p-3 bg-muted rounded">
                        <div>
                          <div className="font-medium">{s.subject?.name || s.name}</div>
                          <div className="text-sm text-muted-foreground">Преподаватель: {s.teacher?.name || s.teacher_name}</div>
                        </div>
                        <div className="flex items-center gap-2">
                          <PaymentStatusBadge status={s.payment_status as PaymentStatus} size="sm" />
                          {s.enrollment_id && (
                            <PayButton 
                              childId={childId} 
                              enrollmentId={s.enrollment_id}
                              subjectName={s.subject?.name || s.name}
                              teacherName={s.teacher?.name || s.teacher_name}
                              hasSubscription={s.has_subscription || false}
                              paymentStatus={s.payment_status}
                            />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}

function PayButton({ 
  childId, 
  enrollmentId, 
  subjectName, 
  teacherName, 
  hasSubscription,
  paymentStatus 
}: { 
  childId: number; 
  enrollmentId: number;
  subjectName: string;
  teacherName: string;
  hasSubscription: boolean;
  paymentStatus: string;
}) {
  // Сумма будет определена на бэкенде в зависимости от режима
  const payment = useInitiatePayment(childId, enrollmentId, {
    description: `Оплата за предмет "${subjectName}" (преподаватель: ${teacherName})`,
    create_subscription: true,
  });
  
  // Если есть активная подписка и оплачено - показываем информацию о подписке и кнопку "Отключить автосписание"
  if (hasSubscription && paymentStatus === 'paid') {
    return (
      <div className="flex flex-col items-end gap-2">
        <div className="flex items-center gap-2">
          <Repeat className="h-4 w-4 text-green-600" />
          <Badge variant="secondary" className="text-xs">Автосписание активно</Badge>
        </div>
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
              logger.error('Cancel subscription error:', err);
            }
          }}
        >
          Отключить автосписание
        </Button>
      </div>
    );
  }
  
  // Иначе показываем кнопку "Подключить предмет"
  return (
    <Button 
      size="sm" 
      onClick={() => payment.mutate()} 
      disabled={payment.isPending}
      variant={paymentStatus === 'overdue' ? 'destructive' : 'default'}
    >
      <CreditCard className="w-4 h-4 mr-1" /> 
      Подключить предмет
    </Button>
  );
}
