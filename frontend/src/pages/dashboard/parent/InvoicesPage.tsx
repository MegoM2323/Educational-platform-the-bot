import React, { useState, useEffect } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { ParentSidebar } from '@/components/layout/ParentSidebar';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useToast } from '@/hooks/use-toast';
import { ParentInvoicesList } from '@/components/invoices/ParentInvoicesList';
import { ParentInvoiceDetail } from '@/components/invoices/ParentInvoiceDetail';
import { useParentInvoices } from '@/hooks/useParentInvoices';
import { type Invoice } from '@/integrations/api/invoiceAPI';
import { useInvoiceWebSocket } from '@/hooks/useInvoiceWebSocket';
import { useQueryClient } from '@tanstack/react-query';
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination';
import { DashboardSkeleton, ErrorState } from '@/components/LoadingStates';

const InvoicesPage: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // WebSocket для real-time обновлений
  const { on, off } = useInvoiceWebSocket();
  const queryClient = useQueryClient();

  const {
    invoices,
    totalCount,
    totalPages,
    currentPage,
    hasNext,
    hasPrevious,
    summary,
    unpaidCount,
    isLoading,
    error,
    setStatus,
    setPage,
    markAsViewed,
    initiatePayment,
    refetch,
    isInitiatingPayment,
  } = useParentInvoices({ initialPageSize: 20 });

  // Обработка результатов оплаты из URL
  useEffect(() => {
    const paymentStatus = searchParams.get('payment');
    const invoiceId = searchParams.get('invoice_id');

    if (paymentStatus === 'success') {
      toast({
        title: 'Payment successful',
        description: 'Invoice was successfully paid. Thank you!',
        variant: 'default',
      });
      refetch();
      setSearchParams({});
    } else if (paymentStatus === 'failed') {
      toast({
        title: 'Payment failed',
        description: 'Unable to complete payment. Please try again.',
        variant: 'destructive',
      });
      setSearchParams({});
    }
  }, [searchParams, setSearchParams, toast, refetch]);

  // Подключаем обработчики WebSocket событий
  useEffect(() => {
    // Обработчик создания счёта
    const handleInvoiceCreated = (data: any) => {
      console.log('[ParentInvoicesPage] Invoice created via WebSocket:', data);
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast({
        title: 'Новый счёт',
        description: `Получен новый счёт #${data.invoice_id}`,
      });
    };

    // Обработчик обновления статуса
    const handleStatusUpdate = (data: any) => {
      console.log('[ParentInvoicesPage] Invoice status updated via WebSocket:', data);
      queryClient.invalidateQueries({ queryKey: ['invoices'] });

      // Показываем уведомление для родителей при отправке счёта
      if (data.new_status === 'sent') {
        toast({
          title: 'Счёт отправлен',
          description: `Счёт #${data.invoice_id} готов к оплате`,
        });
      }
    };

    // Обработчик оплаты счёта
    const handleInvoicePaid = (data: any) => {
      console.log('[ParentInvoicesPage] Invoice paid via WebSocket:', data);
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast({
        title: 'Счёт оплачен!',
        description: `Счёт #${data.invoice_id} успешно оплачен`,
      });
    };

    // Подписываемся на события
    on('onInvoiceCreated', handleInvoiceCreated);
    on('onStatusUpdate', handleStatusUpdate);
    on('onInvoicePaid', handleInvoicePaid);

    // Отписываемся при размонтировании
    return () => {
      off('onInvoiceCreated', handleInvoiceCreated);
      off('onStatusUpdate', handleStatusUpdate);
      off('onInvoicePaid', handleInvoicePaid);
    };
  }, [on, off, queryClient, toast]);

  const handleInvoiceClick = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
    setIsDetailOpen(true);
  };

  const handlePayClick = (invoice: Invoice) => {
    initiatePayment(invoice.id);
  };

  const handlePageChange = (page: number) => {
    setPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const getPageNumbers = () => {
    const pages: (number | 'ellipsis')[] = [];
    const maxPagesToShow = 5;

    if (totalPages <= maxPagesToShow) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);

      if (currentPage > 3) {
        pages.push('ellipsis');
      }

      const startPage = Math.max(2, currentPage - 1);
      const endPage = Math.min(totalPages - 1, currentPage + 1);

      for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
      }

      if (currentPage < totalPages - 2) {
        pages.push('ellipsis');
      }

      if (totalPages > 1) {
        pages.push(totalPages);
      }
    }

    return pages;
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ParentSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => navigate('/dashboard/parent')}
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                  <h1 className="text-3xl font-bold">Invoices</h1>
                  <p className="text-muted-foreground">
                    Manage invoices for your children's education
                  </p>
                </div>
              </div>

              {error && (
                <ErrorState error={error} onRetry={() => refetch()} />
              )}

              {isLoading && <DashboardSkeleton />}

              {!isLoading && !error && (
                <>
                  <ParentInvoicesList
                    invoices={invoices}
                    isLoading={isLoading}
                    onInvoiceClick={handleInvoiceClick}
                    onFilterChange={setStatus}
                    summary={summary}
                  />

                  {totalPages > 1 && (
                    <div className="mt-6">
                      <Pagination>
                        <PaginationContent>
                          <PaginationItem>
                            <PaginationPrevious
                              onClick={() =>
                                hasPrevious && handlePageChange(currentPage - 1)
                              }
                              className={
                                !hasPrevious
                                  ? 'pointer-events-none opacity-50'
                                  : 'cursor-pointer'
                              }
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
                              onClick={() => hasNext && handlePageChange(currentPage + 1)}
                              className={
                                !hasNext
                                  ? 'pointer-events-none opacity-50'
                                  : 'cursor-pointer'
                              }
                            />
                          </PaginationItem>
                        </PaginationContent>
                      </Pagination>
                    </div>
                  )}

                  {invoices.length > 0 && (
                    <div className="text-sm text-muted-foreground text-center">
                      Showing {(currentPage - 1) * 20 + 1}-
                      {Math.min(currentPage * 20, totalCount)} of {totalCount} invoices
                    </div>
                  )}
                </>
              )}
            </div>
          </main>
        </SidebarInset>
      </div>

      <ParentInvoiceDetail
        invoice={selectedInvoice}
        open={isDetailOpen}
        onOpenChange={setIsDetailOpen}
        onPayClick={handlePayClick}
        onMarkAsViewed={markAsViewed}
        isPaymentLoading={isInitiatingPayment}
      />
    </SidebarProvider>
  );
};

export default InvoicesPage;
