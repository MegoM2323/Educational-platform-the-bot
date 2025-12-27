import React, { useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import {
  Calendar,
  User,
  CreditCard,
  FileText,
  MessageCircle,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { type Invoice } from '@/integrations/api/invoiceAPI';
import { cn } from '@/lib/utils';

interface ParentInvoiceDetailProps {
  invoice: Invoice | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPayClick: (invoice: Invoice) => void;
  onMarkAsViewed?: (invoiceId: number) => void;
  isPaymentLoading?: boolean;
}

const getStatusColor = (status: Invoice['status']) => {
  switch (status) {
    case 'paid':
      return 'bg-green-600 hover:bg-green-700';
    case 'viewed':
      return 'bg-yellow-600 hover:bg-yellow-700';
    case 'sent':
      return 'border-blue-600 text-blue-600';
    case 'cancelled':
      return 'bg-gray-600 hover:bg-gray-700';
    default:
      return '';
  }
};

export const ParentInvoiceDetail: React.FC<ParentInvoiceDetailProps> = ({
  invoice,
  open,
  onOpenChange,
  onPayClick,
  onMarkAsViewed,
  isPaymentLoading,
}) => {
  useEffect(() => {
    if (invoice && open && invoice.status === 'sent' && onMarkAsViewed) {
      onMarkAsViewed(invoice.id);
    }
  }, [invoice, open, onMarkAsViewed]);

  if (!invoice) return null;

  const isPaid = invoice.status === 'paid';
  const dueDate = new Date(invoice.due_date);
  const now = new Date();
  const isOverdue = dueDate < now && !isPaid;
  const diffTime = dueDate.getTime() - now.getTime();
  const daysRemaining = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  const daysOverdue = isOverdue ? Math.abs(daysRemaining) : 0;

  const getStatusTimeline = () => {
    const timeline = [
      { label: 'Created', completed: true, date: invoice.created_at },
      { label: 'Sent', completed: !!invoice.sent_at, date: invoice.sent_at },
      { label: 'Viewed', completed: !!invoice.viewed_at, date: invoice.viewed_at },
      { label: 'Paid', completed: !!invoice.paid_at, date: invoice.paid_at },
    ];
    return timeline;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl">Invoice for Payment</DialogTitle>
          <DialogDescription>
            Details for invoice #{invoice.id}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarImage src={invoice.student.avatar} />
              <AvatarFallback className="gradient-primary text-primary-foreground text-lg">
                {invoice.student.full_name
                  .split(' ')
                  .map((n) => n[0])
                  .join('')}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-muted-foreground" />
                <div className="font-semibold text-lg">{invoice.student.full_name}</div>
              </div>
              {invoice.enrollment && (
                <div className="text-sm text-muted-foreground">
                  {invoice.enrollment.subject_name}
                </div>
              )}
            </div>
          </div>

          <Separator />

          <div className="p-6 bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg border-2 border-primary/20">
            <div className="text-center">
              <div className="text-sm text-muted-foreground mb-2">Amount to pay</div>
              <div className="text-4xl font-bold text-primary mb-2">
                {parseFloat(invoice.amount).toLocaleString('en-US')} RUB
              </div>
              <Badge
                variant={invoice.status === 'paid' ? 'default' : 'outline'}
                className={cn(getStatusColor(invoice.status))}
              >
                {invoice.status === 'paid' && '✓ '}
                {invoice.status === 'paid'
                  ? 'Paid'
                  : invoice.status === 'viewed'
                  ? 'Viewed'
                  : invoice.status === 'sent'
                  ? 'Waiting'
                  : invoice.status}
              </Badge>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <h4 className="font-semibold">Description</h4>
            </div>
            <p className="text-sm text-muted-foreground bg-muted p-4 rounded-lg">
              {invoice.description}
            </p>
          </div>

          <div
            className={cn(
              'p-4 rounded-lg border-2',
              isOverdue
                ? 'bg-orange-50 border-orange-400 dark:bg-orange-950/20 dark:border-orange-800'
                : isPaid
                ? 'bg-green-50 border-green-400 dark:bg-green-950/20 dark:border-green-800'
                : 'bg-blue-50 border-blue-400 dark:bg-blue-950/20 dark:border-blue-800'
            )}
          >
            <div className="flex items-center gap-3">
              {isOverdue && !isPaid ? (
                <AlertCircle className="h-5 w-5 text-orange-600" />
              ) : isPaid ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <Clock className="h-5 w-5 text-blue-600" />
              )}
              <div className="flex-1">
                <div className="font-medium">
                  {isPaid
                    ? 'Invoice paid'
                    : isOverdue
                    ? 'Payment overdue'
                    : 'Due date'}
                </div>
                <div className="text-sm">
                  {isPaid ? (
                    <>
                      Paid on{' '}
                      {invoice.paid_at &&
                        new Date(invoice.paid_at).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                    </>
                  ) : (
                    <>
                      {dueDate.toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                      {isOverdue ? (
                        <span className="ml-2 font-medium text-orange-700 dark:text-orange-400">
                          (overdue by {daysOverdue} days)
                        </span>
                      ) : (
                        <span className="ml-2 text-blue-600">
                          ({daysRemaining} days left)
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-semibold mb-3">Invoice history</h4>
            <div className="space-y-3">
              {getStatusTimeline().map((item, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div
                    className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center border-2',
                      item.completed
                        ? 'bg-primary border-primary text-primary-foreground'
                        : 'bg-muted border-muted-foreground/30 text-muted-foreground'
                    )}
                  >
                    {item.completed ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-muted-foreground/30" />
                    )}
                  </div>
                  <div className="flex-1 pt-1">
                    <div
                      className={cn(
                        'font-medium',
                        item.completed ? 'text-foreground' : 'text-muted-foreground'
                      )}
                    >
                      {item.label}
                    </div>
                    {item.date && (
                      <div className="text-xs text-muted-foreground">
                        {new Date(item.date).toLocaleString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          <div className="flex gap-3">
            {!isPaid && (
              <>
                <Button
                  type="button"
                  onClick={() => onPayClick(invoice)}
                  disabled={isPaymentLoading}
                  className={cn(
                    'flex-1',
                    isOverdue &&
                      'bg-orange-600 hover:bg-orange-700 text-white font-semibold shadow-lg'
                  )}
                >
                  <CreditCard className="w-4 h-4 mr-2" />
                  {isPaymentLoading ? 'Processing...' : 'Pay Now'}
                </Button>
                <Button type="button" variant="outline" className="flex-1">
                  <MessageCircle className="w-4 h-4 mr-2" />
                  Contact Tutor
                </Button>
              </>
            )}
            {isPaid && (
              <Button type="button" variant="outline" className="w-full" disabled>
                <CheckCircle className="w-4 h-4 mr-2" />
                Invoice Paid
              </Button>
            )}
          </div>

          <div className="text-xs text-muted-foreground text-center">
            Created{' '}
            {new Date(invoice.created_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
