import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, CheckCircle, XCircle, Clock } from 'lucide-react';
import { adminAPI } from '@/integrations/api/adminAPI';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

interface BroadcastDetailsModalProps {
  broadcastId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface BroadcastDetail {
  id: number;
  target_group: string;
  message: string;
  status: 'draft' | 'sent' | 'failed';
  created_by: {
    id: number;
    full_name: string;
  };
  created_at: string;
  sent_at?: string;
  total_recipients: number;
  successful_sends: number;
  failed_sends: number;
  metadata?: {
    subject_id?: number;
    subject_name?: string;
    tutor_id?: number;
    tutor_name?: string;
  };
}

interface Recipient {
  user_id: number;
  user_email: string;
  user_name: string;
  status: 'pending' | 'sent' | 'failed';
  error_message?: string;
  sent_at?: string;
}

export const BroadcastDetailsModal = ({ broadcastId, open, onOpenChange }: BroadcastDetailsModalProps) => {
  const [broadcast, setBroadcast] = useState<BroadcastDetail | null>(null);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && broadcastId) {
      loadBroadcastDetails();
    } else {
      // Сброс при закрытии
      setBroadcast(null);
      setRecipients([]);
      setError(null);
    }
  }, [open, broadcastId]);

  const loadBroadcastDetails = async () => {
    if (!broadcastId) return;

    setLoading(true);
    setError(null);

    try {
      const [detailsResponse, recipientsResponse] = await Promise.all([
        adminAPI.getBroadcast(broadcastId),
        adminAPI.getBroadcastRecipients(broadcastId),
      ]);

      if (detailsResponse.success && detailsResponse.data?.data) {
        setBroadcast(detailsResponse.data.data);
      } else {
        setError(detailsResponse.error || 'Не удалось загрузить детали рассылки');
      }

      if (recipientsResponse.success && recipientsResponse.data?.recipients) {
        setRecipients(recipientsResponse.data.recipients);
      }
    } catch (err: any) {
      setError(err?.message || 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: 'draft' | 'sent' | 'failed') => {
    switch (status) {
      case 'draft':
        return <Badge variant="secondary" className="bg-gray-100 text-gray-800">Черновик</Badge>;
      case 'sent':
        return <Badge variant="default" className="bg-green-100 text-green-800">Отправлено</Badge>;
      case 'failed':
        return <Badge variant="destructive">Ошибка</Badge>;
      default:
        return null;
    }
  };

  const getRecipientStatusIcon = (status: 'pending' | 'sent' | 'failed') => {
    switch (status) {
      case 'sent':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      default:
        return null;
    }
  };

  const getTargetGroupLabel = (targetGroup: string): string => {
    switch (targetGroup) {
      case 'all_students':
        return 'Все студенты';
      case 'all_teachers':
        return 'Все учителя';
      case 'all_tutors':
        return 'Все тьютеры';
      case 'all_parents':
        return 'Все родители';
      case 'by_subject':
        return `По предмету: ${broadcast?.metadata?.subject_name || 'N/A'}`;
      case 'by_tutor':
        return `По тьютору: ${broadcast?.metadata?.tutor_name || 'N/A'}`;
      case 'custom':
        return 'Кастомная группа';
      default:
        return targetGroup;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Детали рассылки #{broadcastId}</DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-60 w-full" />
          </div>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {!loading && !error && broadcast && (
          <div className="space-y-6">
            {/* Информация о рассылке */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Информация</h3>
                {getStatusBadge(broadcast.status)}
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground">Дата создания:</p>
                  <p className="font-medium">
                    {format(new Date(broadcast.created_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
                  </p>
                </div>

                {broadcast.sent_at && (
                  <div>
                    <p className="text-muted-foreground">Дата отправки:</p>
                    <p className="font-medium">
                      {format(new Date(broadcast.sent_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
                    </p>
                  </div>
                )}

                <div>
                  <p className="text-muted-foreground">Кто создал:</p>
                  <p className="font-medium">{broadcast.created_by.full_name}</p>
                </div>

                <div>
                  <p className="text-muted-foreground">Целевая группа:</p>
                  <p className="font-medium">{getTargetGroupLabel(broadcast.target_group)}</p>
                </div>
              </div>
            </div>

            {/* Текст сообщения */}
            <div className="space-y-2">
              <h3 className="font-semibold">Текст сообщения</h3>
              <div className="p-3 bg-muted rounded-md">
                <p className="whitespace-pre-wrap text-sm">{broadcast.message}</p>
              </div>
            </div>

            {/* Статистика доставки */}
            <div className="space-y-2">
              <h3 className="font-semibold">Статистика доставки</h3>
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-muted rounded-md">
                  <p className="text-xs text-muted-foreground">Всего получателей</p>
                  <p className="text-2xl font-bold">{broadcast.total_recipients}</p>
                </div>
                <div className="p-3 bg-green-50 rounded-md">
                  <p className="text-xs text-green-700">Успешно</p>
                  <p className="text-2xl font-bold text-green-700">{broadcast.successful_sends}</p>
                </div>
                <div className="p-3 bg-red-50 rounded-md">
                  <p className="text-xs text-red-700">Ошибок</p>
                  <p className="text-2xl font-bold text-red-700">{broadcast.failed_sends}</p>
                </div>
              </div>
            </div>

            {/* Список получателей (если рассылка отправлена) */}
            {broadcast.status !== 'draft' && recipients.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-semibold">Получатели ({recipients.length})</h3>
                <div className="border rounded-md max-h-[300px] overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted sticky top-0">
                      <tr>
                        <th className="text-left p-2 font-medium">Email</th>
                        <th className="text-left p-2 font-medium">Имя</th>
                        <th className="text-center p-2 font-medium">Статус</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recipients.map((recipient) => (
                        <tr key={recipient.user_id} className="border-t hover:bg-muted/50">
                          <td className="p-2">{recipient.user_email}</td>
                          <td className="p-2">{recipient.user_name}</td>
                          <td className="p-2">
                            <div className="flex flex-col items-center gap-1">
                              <div className="flex items-center gap-1">
                                {getRecipientStatusIcon(recipient.status)}
                                <span className="text-xs">
                                  {recipient.status === 'sent' && 'Отправлено'}
                                  {recipient.status === 'failed' && 'Ошибка'}
                                  {recipient.status === 'pending' && 'В очереди'}
                                </span>
                              </div>
                              {recipient.error_message && (
                                <span className="text-xs text-red-600">{recipient.error_message}</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
