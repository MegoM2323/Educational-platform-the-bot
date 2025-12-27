import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { adminAPI } from '@/integrations/api/adminAPI';
import { BroadcastModal } from '@/components/admin/BroadcastModal';
import { BroadcastDetailsModal } from '@/components/admin/BroadcastDetailsModal';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Plus, Eye, ChevronLeft, ChevronRight, Send, AlertCircle } from 'lucide-react';

interface Broadcast {
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

export default function AdminBroadcastsPage() {
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [selectedBroadcastId, setSelectedBroadcastId] = useState<number | null>(null);

  // Пагинация
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 20;
  const totalPages = Math.ceil(totalCount / pageSize);

  // Фильтры
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dateFromFilter, setDateFromFilter] = useState('');
  const [dateToFilter, setDateToFilter] = useState('');

  useEffect(() => {
    loadBroadcasts();
  }, [currentPage, statusFilter, dateFromFilter, dateToFilter]);

  const loadBroadcasts = async () => {
    setLoading(true);
    setError(null);

    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize,
      };

      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      if (dateFromFilter) {
        params.date_from = dateFromFilter;
      }

      if (dateToFilter) {
        params.date_to = dateToFilter;
      }

      const response = await adminAPI.getBroadcasts(params);

      if (response.success && response.data) {
        setBroadcasts(response.data.results || []);
        setTotalCount(response.data.count || 0);
      } else {
        setError(response.error || 'Не удалось загрузить рассылки');
        setBroadcasts([]);
      }
    } catch (err: any) {
      setError(err?.message || 'Ошибка загрузки рассылок');
      setBroadcasts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSuccess = () => {
    setCurrentPage(1);
    loadBroadcasts();
  };

  const handleViewDetails = (broadcastId: number) => {
    setSelectedBroadcastId(broadcastId);
    setDetailsModalOpen(true);
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

  const getTargetGroupLabel = (broadcast: Broadcast): string => {
    switch (broadcast.target_group) {
      case 'all_students':
        return 'Все студенты';
      case 'all_teachers':
        return 'Все учителя';
      case 'all_tutors':
        return 'Все тьютеры';
      case 'all_parents':
        return 'Все родители';
      case 'by_subject':
        return `По предмету: ${broadcast.metadata?.subject_name || 'N/A'}`;
      case 'by_tutor':
        return `По тьютору: ${broadcast.metadata?.tutor_name || 'N/A'}`;
      case 'custom':
        return 'Кастомная группа';
      default:
        return broadcast.target_group;
    }
  };

  const truncateMessage = (message: string, maxLength: number = 80): string => {
    if (message.length <= maxLength) return message;
    return message.substring(0, maxLength) + '...';
  };

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Send className="h-5 w-5" />
              Управление рассылками
            </CardTitle>
            <Button type="button" onClick={() => setCreateModalOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Создать рассылку
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {/* Фильтры */}
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Все статусы" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все статусы</SelectItem>
                <SelectItem value="draft">Черновик</SelectItem>
                <SelectItem value="sent">Отправлено</SelectItem>
                <SelectItem value="failed">Ошибка</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex items-center gap-2">
              <Input
                type="date"
                placeholder="Дата от"
                value={dateFromFilter}
                onChange={(e) => setDateFromFilter(e.target.value)}
                className="w-[160px]"
              />
              <span className="text-muted-foreground">—</span>
              <Input
                type="date"
                placeholder="Дата до"
                value={dateToFilter}
                onChange={(e) => setDateToFilter(e.target.value)}
                className="w-[160px]"
              />
            </div>

            {(statusFilter !== 'all' || dateFromFilter || dateToFilter) && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setStatusFilter('all');
                  setDateFromFilter('');
                  setDateToFilter('');
                }}
              >
                Сбросить фильтры
              </Button>
            )}
          </div>

          {/* Ошибка */}
          {error && (
            <div className="flex items-center gap-2 text-red-500 mb-4 p-3 bg-red-50 rounded-md">
              <AlertCircle className="h-5 w-5" />
              <p>{error}</p>
            </div>
          )}

          {/* Таблица рассылок */}
          {loading ? (
            <div className="space-y-2">
              {[...Array(10)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : broadcasts.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Send className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>Рассылок пока нет</p>
            </div>
          ) : (
            <div className="border rounded-md overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="text-left p-3 font-medium">Дата</th>
                    <th className="text-left p-3 font-medium">Кто создал</th>
                    <th className="text-left p-3 font-medium">Целевая группа</th>
                    <th className="text-left p-3 font-medium">Сообщение</th>
                    <th className="text-center p-3 font-medium">Статус</th>
                    <th className="text-center p-3 font-medium">Получателей</th>
                    <th className="text-center p-3 font-medium">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {broadcasts.map((broadcast) => (
                    <tr key={broadcast.id} className="border-t hover:bg-muted/50">
                      <td className="p-3">
                        <div className="flex flex-col">
                          <span className="font-medium">
                            {format(new Date(broadcast.created_at), 'dd.MM.yyyy', { locale: ru })}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {format(new Date(broadcast.created_at), 'HH:mm', { locale: ru })}
                          </span>
                        </div>
                      </td>
                      <td className="p-3">{broadcast.created_by.full_name}</td>
                      <td className="p-3 text-xs">{getTargetGroupLabel(broadcast)}</td>
                      <td className="p-3">
                        <span
                          className="text-xs cursor-help"
                          title={broadcast.message}
                        >
                          {truncateMessage(broadcast.message)}
                        </span>
                      </td>
                      <td className="p-3 text-center">{getStatusBadge(broadcast.status)}</td>
                      <td className="p-3 text-center">
                        <div className="flex flex-col items-center">
                          <span className="font-medium text-green-700">{broadcast.successful_sends}</span>
                          <span className="text-xs text-muted-foreground">
                            / {broadcast.total_recipients}
                          </span>
                          {broadcast.failed_sends > 0 && (
                            <span className="text-xs text-red-600">({broadcast.failed_sends} ошибок)</span>
                          )}
                        </div>
                      </td>
                      <td className="p-3">
                        <div className="flex items-center justify-center gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => handleViewDetails(broadcast.id)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Пагинация */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">
                Показано {broadcasts.length} из {totalCount}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1 || loading}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm">
                  Страница {currentPage} из {totalPages}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages || loading}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Модалы */}
      <BroadcastModal open={createModalOpen} onOpenChange={setCreateModalOpen} onSuccess={handleCreateSuccess} />
      <BroadcastDetailsModal
        broadcastId={selectedBroadcastId}
        open={detailsModalOpen}
        onOpenChange={setDetailsModalOpen}
      />
    </div>
  );
}
