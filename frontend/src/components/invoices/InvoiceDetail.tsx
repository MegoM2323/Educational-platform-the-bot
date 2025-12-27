import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { Invoice, InvoiceStatus } from '@/integrations/api/invoiceAPI';
import {
  useSendInvoice,
  useCancelInvoice,
  useDeleteInvoice,
} from '@/hooks/useInvoicesList';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import {
  Send,
  X,
  Trash2,
  CheckCircle2,
  Clock,
  Eye,
  Ban,
  Loader2,
} from 'lucide-react';

interface InvoiceDetailProps {
  invoice: Invoice | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
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

const statusIcons: Record<InvoiceStatus, React.ReactNode> = {
  draft: <Clock className="h-4 w-4" />,
  sent: <Send className="h-4 w-4" />,
  viewed: <Eye className="h-4 w-4" />,
  paid: <CheckCircle2 className="h-4 w-4" />,
  cancelled: <Ban className="h-4 w-4" />,
};

export const InvoiceDetail = ({ invoice, open, onOpenChange }: InvoiceDetailProps) => {
  const sendMutation = useSendInvoice();
  const cancelMutation = useCancelInvoice();
  const deleteMutation = useDeleteInvoice();

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [showSendConfirm, setShowSendConfirm] = useState(false);

  if (!invoice) return null;

  const handleSend = async () => {
    try {
      await sendMutation.mutateAsync(invoice.id);
      setShowSendConfirm(false);
    } catch (error) {
      // Обработка ошибки в хуке
    }
  };

  const handleCancel = async () => {
    try {
      await cancelMutation.mutateAsync(invoice.id);
      setShowCancelConfirm(false);
    } catch (error) {
      // Обработка ошибки в хуке
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(invoice.id);
      setShowDeleteConfirm(false);
      onOpenChange(false);
    } catch (error) {
      // Обработка ошибки в хуке
    }
  };

  const canSend = invoice.status === 'draft';
  const canEdit = invoice.status === 'draft';
  const canDelete = invoice.status === 'draft';
  const canCancel = ['sent', 'viewed'].includes(invoice.status);

  const isProcessing =
    sendMutation.isPending || cancelMutation.isPending || deleteMutation.isPending;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Счёт #{invoice.id}</DialogTitle>
          </DialogHeader>

          <div className="space-y-6">
            {/* Информация о студенте */}
            <Card className="p-4">
              <div className="flex items-center gap-4">
                <Avatar className="h-16 w-16">
                  <AvatarImage src={invoice.student.avatar} />
                  <AvatarFallback className="text-lg">
                    {invoice.student.full_name.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold">{invoice.student.full_name}</h3>
                  {invoice.enrollment && (
                    <p className="text-sm text-muted-foreground">
                      Предмет: {invoice.enrollment.subject_name}
                    </p>
                  )}
                </div>
                <Badge variant={statusColors[invoice.status]} className="text-base px-4 py-2">
                  <span className="mr-2">{statusIcons[invoice.status]}</span>
                  {statusLabels[invoice.status]}
                </Badge>
              </div>
            </Card>

            {/* Сумма */}
            <Card className="p-6 bg-gradient-to-br from-primary/5 to-primary/10">
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">Сумма к оплате</p>
                <p className="text-4xl font-bold">
                  {parseFloat(invoice.amount).toLocaleString('ru-RU')} ₽
                </p>
              </div>
            </Card>

            {/* Детали */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Срок оплаты</p>
                <p className="font-medium">
                  {format(new Date(invoice.due_date), 'd MMMM yyyy', { locale: ru })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Создан</p>
                <p className="font-medium">
                  {format(new Date(invoice.created_at), 'd MMMM yyyy, HH:mm', {
                    locale: ru,
                  })}
                </p>
              </div>
            </div>

            {/* Описание */}
            <div>
              <p className="text-sm text-muted-foreground mb-2">Описание</p>
              <Card className="p-4">
                <p className="whitespace-pre-wrap">{invoice.description}</p>
              </Card>
            </div>

            <Separator />

            {/* Timeline статусов */}
            <div>
              <p className="text-sm font-semibold mb-3">История изменений</p>
              <div className="space-y-3">
                {/* Draft */}
                <div className="flex items-start gap-3">
                  <div
                    className={`mt-1 ${
                      invoice.status !== 'draft'
                        ? 'text-primary'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {statusIcons.draft}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">Черновик</p>
                    <p className="text-sm text-muted-foreground">
                      {format(new Date(invoice.created_at), 'd MMM yyyy, HH:mm', {
                        locale: ru,
                      })}
                    </p>
                  </div>
                </div>

                {/* Sent */}
                {invoice.sent_at && (
                  <div className="flex items-start gap-3">
                    <div
                      className={`mt-1 ${
                        ['sent', 'viewed', 'paid'].includes(invoice.status)
                          ? 'text-primary'
                          : 'text-muted-foreground'
                      }`}
                    >
                      {statusIcons.sent}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">Отправлен студенту</p>
                      <p className="text-sm text-muted-foreground">
                        {format(new Date(invoice.sent_at), 'd MMM yyyy, HH:mm', {
                          locale: ru,
                        })}
                      </p>
                    </div>
                  </div>
                )}

                {/* Viewed */}
                {invoice.viewed_at && (
                  <div className="flex items-start gap-3">
                    <div
                      className={`mt-1 ${
                        ['viewed', 'paid'].includes(invoice.status)
                          ? 'text-primary'
                          : 'text-muted-foreground'
                      }`}
                    >
                      {statusIcons.viewed}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">Просмотрен студентом</p>
                      <p className="text-sm text-muted-foreground">
                        {format(new Date(invoice.viewed_at), 'd MMM yyyy, HH:mm', {
                          locale: ru,
                        })}
                      </p>
                    </div>
                  </div>
                )}

                {/* Paid */}
                {invoice.paid_at && (
                  <div className="flex items-start gap-3">
                    <div className="mt-1 text-green-600">{statusIcons.paid}</div>
                    <div className="flex-1">
                      <p className="font-medium text-green-600">Оплачен</p>
                      <p className="text-sm text-muted-foreground">
                        {format(new Date(invoice.paid_at), 'd MMM yyyy, HH:mm', {
                          locale: ru,
                        })}
                      </p>
                    </div>
                  </div>
                )}

                {/* Cancelled */}
                {invoice.cancelled_at && (
                  <div className="flex items-start gap-3">
                    <div className="mt-1 text-red-600">{statusIcons.cancelled}</div>
                    <div className="flex-1">
                      <p className="font-medium text-red-600">Отменён</p>
                      <p className="text-sm text-muted-foreground">
                        {format(new Date(invoice.cancelled_at), 'd MMM yyyy, HH:mm', {
                          locale: ru,
                        })}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <DialogFooter className="flex-col sm:flex-row gap-2">
            {canSend && (
              <Button
                type="button"
                onClick={() => setShowSendConfirm(true)}
                disabled={isProcessing}
              >
                <Send className="h-4 w-4 mr-2" />
                Отправить
              </Button>
            )}

            {canCancel && (
              <Button
                type="button"
                variant="destructive"
                onClick={() => setShowCancelConfirm(true)}
                disabled={isProcessing}
              >
                <X className="h-4 w-4 mr-2" />
                Отменить
              </Button>
            )}

            {canDelete && (
              <Button
                type="button"
                variant="destructive"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={isProcessing}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Удалить
              </Button>
            )}

            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isProcessing}
            >
              Закрыть
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Подтверждение отправки */}
      <AlertDialog open={showSendConfirm} onOpenChange={setShowSendConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Отправить счёт?</AlertDialogTitle>
            <AlertDialogDescription>
              Счёт будет отправлен студенту {invoice.student.full_name}. После отправки вы не
              сможете изменить или удалить счёт.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={sendMutation.isPending}>
              Отмена
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleSend} disabled={sendMutation.isPending}>
              {sendMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Отправка...
                </>
              ) : (
                'Отправить'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Подтверждение отмены */}
      <AlertDialog open={showCancelConfirm} onOpenChange={setShowCancelConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Отменить счёт?</AlertDialogTitle>
            <AlertDialogDescription>
              Счёт будет отменён и больше не будет доступен студенту для оплаты. Это
              действие нельзя отменить.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={cancelMutation.isPending}>
              Назад
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {cancelMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Отмена...
                </>
              ) : (
                'Отменить счёт'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Подтверждение удаления */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить счёт?</AlertDialogTitle>
            <AlertDialogDescription>
              Счёт будет удалён без возможности восстановления. Это действие нельзя
              отменить.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              Отмена
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Удаление...
                </>
              ) : (
                'Удалить'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};
