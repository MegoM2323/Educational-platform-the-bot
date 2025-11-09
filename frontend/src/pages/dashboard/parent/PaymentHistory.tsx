import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { CreditCard, Calendar, User, BookOpen, ArrowLeft } from "lucide-react";
import { parentDashboardAPI } from "@/integrations/api/dashboard";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { PaymentStatusBadge, PaymentStatus } from "@/components/PaymentStatusBadge";

interface Payment {
  id: number;
  enrollment_id: number;
  subject: string;
  subject_id: number;
  teacher: string;
  teacher_id: number;
  student: string;
  student_id: number;
  status: string;
  amount: string;
  due_date: string | null;
  paid_at: string | null;
  created_at: string;
  payment_id: string;
  gateway_status: string | null;
  is_recurring: boolean;
}

const PaymentHistory = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPayments = async () => {
      try {
        setLoading(true);
        const data = await parentDashboardAPI.getPaymentHistory();
        setPayments(data);
      } catch (error: any) {
        console.error('Error fetching payment history:', error);
        toast({
          title: "Ошибка загрузки",
          description: error.message || "Не удалось загрузить историю платежей",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchPayments();
  }, [toast]);


  if (loading) {
    return (
      <SidebarProvider>
        <ParentSidebar />
        <SidebarInset>
          <div className="flex flex-col gap-4 p-6">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </SidebarInset>
      </SidebarProvider>
    );
  }

  return (
    <SidebarProvider>
      <ParentSidebar />
      <SidebarInset>
        <div className="flex flex-col gap-6 p-6">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/dashboard/parent')}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-3xl font-bold">История платежей</h1>
              <p className="text-muted-foreground">
                Все платежи по предметам ваших детей
              </p>
            </div>
          </div>

          {payments.length === 0 ? (
            <Card className="p-12 text-center">
              <CreditCard className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">Нет платежей</h3>
              <p className="text-muted-foreground">
                История платежей пуста
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {payments.map((payment) => (
                <Card key={payment.id} className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <BookOpen className="h-5 w-5 text-primary" />
                        <h3 className="text-lg font-semibold">{payment.subject}</h3>
                        {payment.is_recurring && (
                          <Badge variant="outline">Регулярный платеж</Badge>
                        )}
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Ученик</p>
                          <p className="font-medium">{payment.student}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Преподаватель</p>
                          <p className="font-medium">{payment.teacher}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Сумма</p>
                          <p className="font-medium">{payment.amount} ₽</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Статус</p>
                          <PaymentStatusBadge 
                            status={payment.status as PaymentStatus} 
                            size="default" 
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-muted-foreground border-t pt-4">
                    {payment.paid_at && (
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4" />
                        <span>Оплачено: {new Date(payment.paid_at).toLocaleDateString('ru-RU')}</span>
                      </div>
                    )}
                    {payment.due_date && !payment.paid_at && (
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4" />
                        <span>Срок оплаты: {new Date(payment.due_date).toLocaleDateString('ru-RU')}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <CreditCard className="h-4 w-4" />
                      <span>ID платежа: {payment.payment_id.slice(0, 8)}...</span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
};

export default PaymentHistory;

