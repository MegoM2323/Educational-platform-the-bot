import { useState, useEffect } from "react";
import { logger } from '@/utils/logger';
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { CreditCard, Calendar, User, BookOpen, ArrowLeft, ExternalLink } from "lucide-react";
import { parentDashboardAPI } from "@/integrations/api/dashboard";
import { useToast } from "@/hooks/use-toast";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { PaymentStatusBadge, PaymentStatus } from "@/components/PaymentStatusBadge";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

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
  const [searchParams, setSearchParams] = useSearchParams();
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [payingPaymentId, setPayingPaymentId] = useState<number | null>(null);

  // Pagination state
  const pageSize = 20;
  const currentPage = parseInt(searchParams.get('page') || '1', 10);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    const fetchPayments = async () => {
      try {
        setLoading(true);
        const data = await parentDashboardAPI.getPaymentHistory();
        setPayments(data);
        // Calculate total pages
        setTotalPages(Math.ceil(data.length / pageSize));
      } catch (error: any) {
        logger.error('Error fetching payment history:', error);
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

  // Calculate pagination
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedPayments = payments.slice(startIndex, endIndex);

  // Handle page change
  const handlePageChange = (page: number) => {
    setSearchParams({ page: page.toString() });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Handle payment
  const handlePayment = async (payment: Payment) => {
    if (payment.status !== 'pending' && payment.status !== 'waiting_for_payment') {
      return;
    }

    setPayingPaymentId(payment.id);

    try {
      // Используем правильный endpoint для инициации платежа
      const response = await parentDashboardAPI.initiatePayment(
        payment.student_id,
        payment.enrollment_id,
        {
          description: `Оплата за предмет "${payment.subject}" для ученика ${payment.student}`,
          create_subscription: payment.is_recurring
        }
      );

      if (response.confirmation_url) {
        toast({
          title: "Перенаправление на страницу оплаты",
          description: "Откроется новое окно для оплаты"
        });

        // Открываем страницу оплаты в новом окне
        const paymentWindow = window.open(response.confirmation_url, '_blank');

        if (!paymentWindow) {
          toast({
            title: "Ошибка",
            description: "Не удалось открыть окно оплаты. Проверьте настройки блокировки всплывающих окон.",
            variant: "destructive"
          });
        }
      } else {
        throw new Error("Не получена ссылка для оплаты");
      }
    } catch (error: any) {
      logger.error("Error creating payment:", error);
      toast({
        title: "Ошибка оплаты",
        description: error.message || "Не удалось создать платеж",
        variant: "destructive"
      });
    } finally {
      setPayingPaymentId(null);
    }
  };

  // Generate page numbers to display
  const getPageNumbers = () => {
    const pages: (number | 'ellipsis')[] = [];
    const maxPagesToShow = 5;

    if (totalPages <= maxPagesToShow) {
      // Show all pages if total is less than max
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always show first page
      pages.push(1);

      if (currentPage > 3) {
        pages.push('ellipsis');
      }

      // Show pages around current page
      const startPage = Math.max(2, currentPage - 1);
      const endPage = Math.min(totalPages - 1, currentPage + 1);

      for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
      }

      if (currentPage < totalPages - 2) {
        pages.push('ellipsis');
      }

      // Always show last page
      if (totalPages > 1) {
        pages.push(totalPages);
      }
    }

    return pages;
  };


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
            <Button type="button"
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
            <>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-muted-foreground">
                  Показаны {startIndex + 1}-{Math.min(endIndex, payments.length)} из {payments.length} платежей
                </p>
              </div>

              <div className="space-y-4">
                {paginatedPayments.map((payment) => (
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

                    <div className="flex items-center justify-between gap-4 text-sm border-t pt-4">
                      <div className="flex items-center gap-4 text-muted-foreground">
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
                      {(payment.status === 'pending' || payment.status === 'waiting_for_payment') && (
                        <Button type="button"
                          onClick={() => handlePayment(payment)}
                          disabled={payingPaymentId === payment.id}
                          size="sm"
                          className="gradient-primary shadow-glow hover:opacity-90 transition-opacity"
                        >
                          {payingPaymentId === payment.id ? (
                            "Обработка..."
                          ) : (
                            <>
                              <ExternalLink className="h-4 w-4 mr-2" />
                              Оплатить
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  </Card>
                ))}
              </div>

              {totalPages > 1 && (
                <div className="mt-6">
                  <Pagination>
                    <PaginationContent>
                      <PaginationItem>
                        <PaginationPrevious
                          onClick={() => currentPage > 1 && handlePageChange(currentPage - 1)}
                          className={currentPage === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                        />
                      </PaginationItem>

                      {getPageNumbers().map((page, index) => (
                        <PaginationItem key={index}>
                          {page === 'ellipsis' ? (
                            <PaginationEllipsis />
                          ) : (
                            <PaginationLink
                              onClick={() => handlePageChange(page as number)}
                              isActive={currentPage === page}
                              className="cursor-pointer"
                            >
                              {page}
                            </PaginationLink>
                          )}
                        </PaginationItem>
                      ))}

                      <PaginationItem>
                        <PaginationNext
                          onClick={() => currentPage < totalPages && handlePageChange(currentPage + 1)}
                          className={currentPage === totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                        />
                      </PaginationItem>
                    </PaginationContent>
                  </Pagination>
                </div>
              )}
            </>
          )}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
};

export default PaymentHistory;

