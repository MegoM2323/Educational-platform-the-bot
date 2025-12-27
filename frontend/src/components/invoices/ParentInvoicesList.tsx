import React, { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, Calendar, User, CreditCard } from 'lucide-react';
import { type Invoice, type InvoiceStatus } from '@/integrations/api/invoiceAPI';
import { cn } from '@/lib/utils';

interface ParentInvoicesListProps {
  invoices: Invoice[];
  isLoading: boolean;
  onInvoiceClick: (invoice: Invoice) => void;
  onFilterChange?: (status?: InvoiceStatus[]) => void;
  summary?: {
    total_unpaid_amount: number;
    overdue_count: number;
    upcoming_count: number;
  };
}

const getStatusBadge = (status: InvoiceStatus, dueDate?: string) => {
  const isOverdue = dueDate && new Date(dueDate) < new Date() && status !== 'paid';

  if (isOverdue) {
    return (
      <Badge variant="destructive" className="bg-orange-600 hover:bg-orange-700">
        <AlertCircle className="w-3 h-3 mr-1" />
        Overdue
      </Badge>
    );
  }

  switch (status) {
    case 'paid':
      return (
        <Badge variant="default" className="bg-green-600 hover:bg-green-700">
          Paid
        </Badge>
      );
    case 'viewed':
      return (
        <Badge variant="secondary" className="bg-yellow-600 hover:bg-yellow-700">
          Viewed
        </Badge>
      );
    case 'sent':
      return (
        <Badge variant="outline" className="border-blue-600 text-blue-600">
          Waiting
        </Badge>
      );
    case 'draft':
      return <Badge variant="outline">Draft</Badge>;
    case 'cancelled':
      return <Badge variant="secondary">Cancelled</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
};

const getDaysRemaining = (dueDate: string): { days: number; isOverdue: boolean } => {
  const due = new Date(dueDate);
  const now = new Date();
  const diffTime = due.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  return {
    days: Math.abs(diffDays),
    isOverdue: diffDays < 0,
  };
};

export const ParentInvoicesList: React.FC<ParentInvoicesListProps> = ({
  invoices,
  isLoading,
  onInvoiceClick,
  onFilterChange,
  summary,
}) => {
  const sortedInvoices = useMemo(() => {
    return [...invoices].sort((a, b) => {
      const aOverdue = new Date(a.due_date) < new Date() && a.status !== 'paid';
      const bOverdue = new Date(b.due_date) < new Date() && b.status !== 'paid';

      if (aOverdue && !bOverdue) return -1;
      if (!aOverdue && bOverdue) return 1;

      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [invoices]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {summary && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Summary</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">Unpaid</div>
              <div className="text-2xl font-bold text-orange-600">
                {summary.total_unpaid_amount.toLocaleString('en-US')} RUB
              </div>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">Overdue</div>
              <div className="text-2xl font-bold text-destructive">
                {summary.overdue_count}
              </div>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">Upcoming (7 days)</div>
              <div className="text-2xl font-bold text-blue-600">
                {summary.upcoming_count}
              </div>
            </div>
          </div>
        </Card>
      )}

      {onFilterChange && (
        <div className="flex items-center gap-4">
          <Select onValueChange={(value) => {
            if (value === 'all') {
              onFilterChange(undefined);
            } else {
              onFilterChange([value as InvoiceStatus]);
            }
          }}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="All invoices" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All invoices</SelectItem>
              <SelectItem value="sent">Waiting for payment</SelectItem>
              <SelectItem value="viewed">Viewed</SelectItem>
              <SelectItem value="paid">Paid</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      <Card>
        {sortedInvoices.length === 0 ? (
          <div className="p-12 text-center">
            <CreditCard className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">No invoices</h3>
            <p className="text-muted-foreground">
              You have no issued invoices yet
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Child</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedInvoices.map((invoice) => {
                const { days, isOverdue } = getDaysRemaining(invoice.due_date);
                const isPaid = invoice.status === 'paid';
                const needsPayment = !isPaid && (invoice.status === 'sent' || invoice.status === 'viewed');

                return (
                  <TableRow
                    key={invoice.id}
                    className={cn(
                      'cursor-pointer hover:bg-muted/50 transition-colors',
                      isOverdue && !isPaid && 'bg-orange-50 dark:bg-orange-950/20'
                    )}
                    onClick={() => onInvoiceClick(invoice)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar className="h-10 w-10">
                          <AvatarImage src={invoice.student.avatar} />
                          <AvatarFallback className="gradient-primary text-primary-foreground">
                            {invoice.student.full_name
                              .split(' ')
                              .map((n) => n[0])
                              .join('')}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="font-medium">{invoice.student.full_name}</div>
                          {invoice.enrollment && (
                            <div className="text-sm text-muted-foreground">
                              {invoice.enrollment.subject_name}
                            </div>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="font-semibold text-lg">
                        {parseFloat(invoice.amount).toLocaleString('en-US')} RUB
                      </div>
                    </TableCell>
                    <TableCell>
                      {getStatusBadge(invoice.status, invoice.due_date)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <div className="font-medium">
                            {new Date(invoice.due_date).toLocaleDateString('en-US')}
                          </div>
                          <div
                            className={cn(
                              'text-xs',
                              isOverdue && !isPaid
                                ? 'text-destructive font-medium'
                                : 'text-muted-foreground'
                            )}
                          >
                            {isPaid
                              ? 'Paid'
                              : isOverdue
                              ? `Overdue by ${days} days`
                              : `${days} days left`}
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      {needsPayment && (
                        <Button
                          type="button"
                          size="sm"
                          variant={isOverdue ? 'default' : 'outline'}
                          className={cn(
                            isOverdue &&
                              'bg-orange-600 hover:bg-orange-700 text-white font-semibold'
                          )}
                          onClick={(e) => {
                            e.stopPropagation();
                            onInvoiceClick(invoice);
                          }}
                        >
                          <CreditCard className="w-4 h-4 mr-1" />
                          Pay
                        </Button>
                      )}
                      {isPaid && (
                        <Badge variant="default" className="bg-green-600">
                          Paid
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  );
};
