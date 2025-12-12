import { useState, useEffect } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { TutorSidebar } from '@/components/layout/TutorSidebar';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useInvoicesList } from '@/hooks/useInvoicesList';
import { TutorInvoicesList } from '@/components/invoices/TutorInvoicesList';
import { CreateInvoiceForm } from '@/components/invoices/CreateInvoiceForm';
import { InvoiceDetail } from '@/components/invoices/InvoiceDetail';
import { Invoice } from '@/integrations/api/invoiceAPI';
import { Plus, FileText, DollarSign, Clock, CheckCircle2 } from 'lucide-react';
import { useInvoiceWebSocket } from '@/hooks/useInvoiceWebSocket';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/hooks/use-toast';

export default function InvoicesPage() {
  const {
    invoices,
    isLoading,
    error,
    filters,
    setStatus,
    setDateRange,
    setSort,
    clearFilters,
    page,
    setPage,
    totalPages,
    totalCount,
  } = useInvoicesList();

  const [isCreateFormOpen, setIsCreateFormOpen] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // WebSocket для real-time обновлений
  const { on, off } = useInvoiceWebSocket();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Подключаем обработчики WebSocket событий
  useEffect(() => {
    // Обработчик создания счёта
    const handleInvoiceCreated = (data: any) => {
      console.log('[InvoicesPage] Invoice created via WebSocket:', data);
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast({
        title: 'Новый счёт создан',
        description: `Счёт #${data.invoice_id} успешно создан`,
      });
    };

    // Обработчик обновления статуса
    const handleStatusUpdate = (data: any) => {
      console.log('[InvoicesPage] Invoice status updated via WebSocket:', data);
      queryClient.invalidateQueries({ queryKey: ['invoices'] });

      // Показываем уведомление только для важных статусов
      if (data.new_status === 'viewed' || data.new_status === 'paid') {
        const statusText = data.new_status === 'viewed' ? 'просмотрен' : 'оплачен';
        toast({
          title: 'Счёт обновлён',
          description: `Счёт #${data.invoice_id} ${statusText}`,
        });
      }
    };

    // Обработчик оплаты счёта
    const handleInvoicePaid = (data: any) => {
      console.log('[InvoicesPage] Invoice paid via WebSocket:', data);
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

  const handleDetailClose = (open: boolean) => {
    setIsDetailOpen(open);
    if (!open) {
      setSelectedInvoice(null);
    }
  };

  // Подсчёт статистики
  const stats = {
    total: totalCount,
    draft: invoices.filter((inv) => inv.status === 'draft').length,
    sent: invoices.filter((inv) => inv.status === 'sent').length,
    paid: invoices.filter((inv) => inv.status === 'paid').length,
    totalAmount: invoices.reduce((sum, inv) => sum + parseFloat(inv.amount), 0),
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TutorSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center justify-between gap-4 border-b bg-background px-6">
            <div className="flex items-center gap-4">
              <SidebarTrigger />
              <h1 className="text-2xl font-bold">Счета</h1>
            </div>
            <Button type="button" onClick={() => setIsCreateFormOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Создать счёт
            </Button>
          </header>

          <main className="p-6">
            <div className="space-y-6">
              {/* Описание */}
              <div>
                <p className="text-muted-foreground">
                  Создавайте и отправляйте счета своим студентам, отслеживайте статус
                  оплаты
                </p>
              </div>

              {/* Статистика */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                      <FileText className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold">{stats.total}</div>
                      <div className="text-sm text-muted-foreground">Всего счетов</div>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex items-center justify-center">
                      <Clock className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold">{stats.draft}</div>
                      <div className="text-sm text-muted-foreground">Черновиков</div>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/20 rounded-lg flex items-center justify-center">
                      <FileText className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold">{stats.sent}</div>
                      <div className="text-sm text-muted-foreground">Отправлено</div>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-green-100 dark:bg-green-900/20 rounded-lg flex items-center justify-center">
                      <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold">{stats.paid}</div>
                      <div className="text-sm text-muted-foreground">Оплачено</div>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Общая сумма */}
              {stats.totalAmount > 0 && (
                <Card className="p-6 bg-gradient-to-br from-primary/5 to-primary/10">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground mb-1">
                        Общая сумма на текущей странице
                      </p>
                      <p className="text-3xl font-bold">
                        {stats.totalAmount.toLocaleString('ru-RU')} ₽
                      </p>
                    </div>
                    <DollarSign className="h-12 w-12 text-primary/30" />
                  </div>
                </Card>
              )}

              {/* Список счетов */}
              <TutorInvoicesList
                invoices={invoices}
                isLoading={isLoading}
                onInvoiceClick={handleInvoiceClick}
                selectedStatuses={filters.status}
                onStatusChange={setStatus}
                dateFrom={filters.dateFrom}
                dateTo={filters.dateTo}
                onDateRangeChange={setDateRange}
                ordering={filters.ordering}
                onOrderingChange={setSort}
                currentPage={page}
                totalPages={totalPages}
                onPageChange={setPage}
                onClearFilters={clearFilters}
              />

              {/* Сообщение об ошибке */}
              {error && (
                <Card className="p-4 border-red-500">
                  <p className="text-red-600 dark:text-red-400">
                    Ошибка загрузки счетов: {error}
                  </p>
                </Card>
              )}
            </div>
          </main>
        </SidebarInset>
      </div>

      {/* Форма создания счёта */}
      <CreateInvoiceForm open={isCreateFormOpen} onOpenChange={setIsCreateFormOpen} />

      {/* Детали счёта */}
      <InvoiceDetail
        invoice={selectedInvoice}
        open={isDetailOpen}
        onOpenChange={handleDetailClose}
      />
    </SidebarProvider>
  );
}
