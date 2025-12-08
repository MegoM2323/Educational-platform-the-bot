import { useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { InvoiceStatus, Invoice } from '@/integrations/api/invoiceAPI';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { ArrowUpDown, ArrowUp, ArrowDown, X, FileText } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';

interface TutorInvoicesListProps {
  invoices: Invoice[];
  isLoading: boolean;
  onInvoiceClick: (invoice: Invoice) => void;

  // Фильтры
  selectedStatuses: InvoiceStatus[];
  onStatusChange: (statuses: InvoiceStatus[]) => void;
  dateFrom?: string;
  dateTo?: string;
  onDateRangeChange: (from?: string, to?: string) => void;

  // Сортировка
  ordering: string;
  onOrderingChange: (ordering: string) => void;

  // Пагинация
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;

  // Очистка фильтров
  onClearFilters: () => void;
}

const statusLabels: Record<InvoiceStatus, string> = {
  draft: 'Черновик',
  sent: 'Отправлен',
  viewed: 'Просмотрен',
  paid: 'Оплачен',
  cancelled: 'Отменён',
};

const statusColors: Record<InvoiceStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  draft: 'secondary',
  sent: 'default',
  viewed: 'outline',
  paid: 'default',
  cancelled: 'destructive',
};

export const TutorInvoicesList = ({
  invoices,
  isLoading,
  onInvoiceClick,
  selectedStatuses,
  onStatusChange,
  dateFrom,
  dateTo,
  onDateRangeChange,
  ordering,
  onOrderingChange,
  currentPage,
  totalPages,
  onPageChange,
  onClearFilters,
}: TutorInvoicesListProps) => {
  const [localDateFrom, setLocalDateFrom] = useState(dateFrom || '');
  const [localDateTo, setLocalDateTo] = useState(dateTo || '');

  const handleStatusToggle = (status: InvoiceStatus) => {
    if (selectedStatuses.includes(status)) {
      onStatusChange(selectedStatuses.filter((s) => s !== status));
    } else {
      onStatusChange([...selectedStatuses, status]);
    }
  };

  const handleApplyDateFilter = () => {
    onDateRangeChange(
      localDateFrom || undefined,
      localDateTo || undefined
    );
  };

  const handleClearDateFilter = () => {
    setLocalDateFrom('');
    setLocalDateTo('');
    onDateRangeChange(undefined, undefined);
  };

  const getSortIcon = (field: string) => {
    if (ordering === field) return <ArrowUp className="h-4 w-4 ml-1" />;
    if (ordering === `-${field}`) return <ArrowDown className="h-4 w-4 ml-1" />;
    return <ArrowUpDown className="h-4 w-4 ml-1 opacity-50" />;
  };

  const toggleSort = (field: string) => {
    if (ordering === field) {
      onOrderingChange(`-${field}`);
    } else {
      onOrderingChange(field);
    }
  };

  const hasActiveFilters = selectedStatuses.length > 0 || dateFrom || dateTo;

  return (
    <div className="space-y-4">
      {/* Фильтры */}
      <Card className="p-4">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Фильтры</h3>
            {hasActiveFilters && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onClearFilters}
              >
                <X className="h-4 w-4 mr-1" />
                Сбросить
              </Button>
            )}
          </div>

          {/* Фильтр по статусу */}
          <div>
            <Label className="mb-2 block">Статус</Label>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(statusLabels) as InvoiceStatus[]).map((status) => (
                <div key={status} className="flex items-center space-x-2">
                  <Checkbox
                    id={`status-${status}`}
                    checked={selectedStatuses.includes(status)}
                    onCheckedChange={() => handleStatusToggle(status)}
                  />
                  <Label
                    htmlFor={`status-${status}`}
                    className="cursor-pointer font-normal"
                  >
                    {statusLabels[status]}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          {/* Фильтр по дате */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="date-from">Дата от</Label>
              <Input
                id="date-from"
                type="date"
                value={localDateFrom}
                onChange={(e) => setLocalDateFrom(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="date-to">Дата до</Label>
              <Input
                id="date-to"
                type="date"
                value={localDateTo}
                onChange={(e) => setLocalDateTo(e.target.value)}
              />
            </div>
            <div className="flex items-end gap-2">
              <Button
                type="button"
                onClick={handleApplyDateFilter}
                className="flex-1"
              >
                Применить
              </Button>
              {(localDateFrom || localDateTo) && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleClearDateFilter}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Таблица счетов */}
      <Card>
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : invoices.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Нет счетов</h3>
            <p className="text-muted-foreground">
              {hasActiveFilters
                ? 'По заданным фильтрам счета не найдены'
                : 'Вы ещё не создали ни одного счёта'}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Студент</TableHead>
                    <TableHead>
                      <button
                        type="button"
                        className="flex items-center hover:text-primary transition-colors"
                        onClick={() => toggleSort('amount')}
                      >
                        Сумма
                        {getSortIcon('amount')}
                      </button>
                    </TableHead>
                    <TableHead>
                      <button
                        type="button"
                        className="flex items-center hover:text-primary transition-colors"
                        onClick={() => toggleSort('due_date')}
                      >
                        Срок оплаты
                        {getSortIcon('due_date')}
                      </button>
                    </TableHead>
                    <TableHead>
                      <button
                        type="button"
                        className="flex items-center hover:text-primary transition-colors"
                        onClick={() => toggleSort('status')}
                      >
                        Статус
                        {getSortIcon('status')}
                      </button>
                    </TableHead>
                    <TableHead>
                      <button
                        type="button"
                        className="flex items-center hover:text-primary transition-colors"
                        onClick={() => toggleSort('created_at')}
                      >
                        Создан
                        {getSortIcon('created_at')}
                      </button>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoices.map((invoice) => (
                    <TableRow
                      key={invoice.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => onInvoiceClick(invoice)}
                    >
                      <TableCell className="font-medium">
                        {invoice.student.full_name}
                      </TableCell>
                      <TableCell className="font-semibold">
                        {parseFloat(invoice.amount).toLocaleString('ru-RU')} ₽
                      </TableCell>
                      <TableCell>
                        {format(new Date(invoice.due_date), 'd MMM yyyy', {
                          locale: ru,
                        })}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusColors[invoice.status]}>
                          {statusLabels[invoice.status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {format(new Date(invoice.created_at), 'd MMM yyyy, HH:mm', {
                          locale: ru,
                        })}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Пагинация */}
            {totalPages > 1 && (
              <div className="p-4 border-t flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  Страница {currentPage + 1} из {totalPages}
                </div>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={currentPage === 0}
                    onClick={() => onPageChange(currentPage - 1)}
                  >
                    Назад
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={currentPage >= totalPages - 1}
                    onClick={() => onPageChange(currentPage + 1)}
                  >
                    Вперёд
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
};
