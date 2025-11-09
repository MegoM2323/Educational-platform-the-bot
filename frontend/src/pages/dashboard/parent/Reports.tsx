import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Eye, Calendar, CheckCircle } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { tutorWeeklyReportsAPI, TutorWeeklyReport } from "@/integrations/api/reports";
import { useToast } from "@/hooks/use-toast";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { unifiedAPI } from "@/integrations/api/unifiedClient";

interface Child {
  id: number;
  name: string;
  grade: string;
}

export default function ParentReports() {
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<TutorWeeklyReport[]>([]);
  const [children, setChildren] = useState<Child[]>([]);
  const [selectedChild, setSelectedChild] = useState<number | null>(null);
  const [selectedReport, setSelectedReport] = useState<TutorWeeklyReport | null>(null);
  const { toast } = useToast();

  const loadChildren = useCallback(async () => {
    try {
      setLoading(true);
      const response = await unifiedAPI.request<{ children: Child[] }>('/materials/dashboard/parent/children/');
      if (response.data?.children) {
        setChildren(response.data.children);
        if (response.data.children.length > 0) {
          setSelectedChild(response.data.children[0].id);
        }
      }
    } catch (error: any) {
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось загрузить список детей',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const loadReports = useCallback(async () => {
    try {
      setLoading(true);
      console.log('[Parent Reports] Loading reports, selectedChild:', selectedChild);
      // Backend автоматически фильтрует отчеты по родителю
      const allReports = await tutorWeeklyReportsAPI.getReports();
      console.log('[Parent Reports] Reports loaded:', allReports);
      const reportsArray = Array.isArray(allReports) ? allReports : [];
      console.log('[Parent Reports] Reports array length:', reportsArray.length);
      
      // Если выбран конкретный ребенок, фильтруем на фронтенде
      // Иначе показываем все отчеты о всех детях
      if (selectedChild) {
        const beforeFilter = reportsArray.length;
        const childReports = reportsArray.filter(r => r.student === selectedChild);
        console.log('[Parent Reports] Filtered reports:', beforeFilter, '->', childReports.length);
        setReports(childReports);
      } else {
        console.log('[Parent Reports] Setting all reports:', reportsArray.length);
        setReports(reportsArray);
      }
    } catch (error: any) {
      console.error('[Parent Reports] Error loading reports:', error);
      console.error('[Parent Reports] Error details:', {
        message: error?.message,
        response: error?.response,
        stack: error?.stack,
      });
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось загрузить отчёты',
        variant: 'destructive',
      });
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [selectedChild, toast]);

  useEffect(() => {
    loadChildren();
  }, [loadChildren]);

  useEffect(() => {
    // Очищаем кэш при загрузке страницы для получения свежих данных
    const clearCache = async () => {
      const { cacheService } = await import('../../../services/cacheService');
      cacheService.delete('/reports/tutor-weekly-reports/');
    };
    clearCache().then(() => {
      loadReports();
    });
  }, [loadReports]);

  const handleMarkAsRead = async (reportId: number) => {
    try {
      setLoading(true);
      await tutorWeeklyReportsAPI.markAsRead(reportId);
      toast({
        title: 'Успешно',
        description: 'Отчёт отмечен как прочитанный',
      });
      // Очищаем кэш и обновляем список отчетов
      const { cacheService } = await import('../../../services/cacheService');
      cacheService.delete('/reports/tutor-weekly-reports/');
      await loadReports();
    } catch (error: any) {
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось отметить отчёт',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string | undefined) => {
    if (!status) return <Badge variant="outline">Не указан</Badge>;
    const variants: Record<string, 'default' | 'secondary' | 'outline'> = {
      sent: 'default',
      read: 'default',
      draft: 'secondary',
      archived: 'outline',
    };
    const labels: Record<string, string> = {
      sent: 'Отправлен',
      read: 'Прочитан',
      draft: 'Черновик',
      archived: 'Архив',
    };
    return (
      <Badge variant={variants[status] || 'outline'}>
        {labels[status] || status}
      </Badge>
    );
  };

  const unreadCount = reports.filter(r => r.status === 'sent').length;

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ParentSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Отчёты от тьютора</h1>
              {unreadCount > 0 && (
                <Badge variant="default" className="ml-2">
                  {unreadCount} непрочитанных
                </Badge>
              )}
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <div className="space-y-6">
              {/* Выбор ребенка */}
              {children.length > 1 && (
                <Card className="p-4">
                  <label className="text-sm font-medium mb-2 block">Выберите ребёнка</label>
                  <Select
                    value={selectedChild?.toString() || ''}
                    onValueChange={(value) => setSelectedChild(parseInt(value))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите ребёнка" />
                    </SelectTrigger>
                    <SelectContent>
                      {children.map((child) => (
                        <SelectItem key={child.id} value={child.id.toString()}>
                          {child.name} ({child.grade} класс)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Card>
              )}

              {/* Список отчетов */}
              <div className="grid md:grid-cols-2 gap-4">
                {reports.length === 0 && !loading && (
                  <Card className="p-6 col-span-2">
                    <div className="text-center text-muted-foreground">
                      <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>Отчётов пока нет</p>
                      <p className="text-xs mt-2">Отчёты от тьютора появятся здесь после их отправки</p>
                    </div>
                  </Card>
                )}
                {reports.filter(report => report && report.id).map((report) => (
                  <Card
                    key={report.id}
                    className={`p-6 hover:border-primary transition-colors ${
                      report.status === 'sent' ? 'border-primary border-2' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h3 className="font-bold mb-1">{report.title || 'Без названия'}</h3>
                        <div className="text-sm text-muted-foreground mb-2">
                          Ученик: {report.student_name || 'Не указан'}
                        </div>
                        <div className="text-sm text-muted-foreground mb-2">
                          Тьютор: {report.tutor_name || 'Не указан'}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                          <Calendar className="w-3 h-3" />
                          {report.week_start && report.week_end ? (
                            <>
                              {new Date(report.week_start).toLocaleDateString('ru-RU')} - {new Date(report.week_end).toLocaleDateString('ru-RU')}
                            </>
                          ) : (
                            'Период не указан'
                          )}
                        </div>
                        {(report.progress_percentage !== undefined && report.progress_percentage > 0) && (
                          <div className="text-sm mb-2">
                            Прогресс: <strong>{report.progress_percentage}%</strong>
                          </div>
                        )}
                        {(report.attendance_percentage !== undefined && report.attendance_percentage > 0) && (
                          <div className="text-sm mb-2">
                            Посещаемость: <strong>{report.attendance_percentage}%</strong>
                          </div>
                        )}
                      </div>
                      {getStatusBadge(report.status || 'draft')}
                    </div>
                    <div className="flex items-center gap-2 mt-4">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => report && setSelectedReport(report)}
                        disabled={!report}
                      >
                        <Eye className="w-4 h-4 mr-2" />
                        Просмотр
                      </Button>
                      {report && report.status === 'sent' && report.id && (
                        <Button
                          size="sm"
                          variant="default"
                          onClick={() => handleMarkAsRead(report.id)}
                          disabled={loading}
                        >
                          <CheckCircle className="w-4 h-4 mr-2" />
                          Прочитано
                        </Button>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </main>
        </SidebarInset>
      </div>

      {/* Диалог просмотра отчета */}
      <Dialog open={!!selectedReport} onOpenChange={() => setSelectedReport(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedReport?.title}</DialogTitle>
            <DialogDescription>
              Отчёт от {selectedReport?.tutor_name || 'тьютора'} по ученику {selectedReport?.student_name || 'Не указан'} {selectedReport?.week_start && selectedReport?.week_end && `за период ${new Date(selectedReport.week_start).toLocaleDateString('ru-RU')} - ${new Date(selectedReport.week_end).toLocaleDateString('ru-RU')}`}
            </DialogDescription>
          </DialogHeader>
          {selectedReport && (
            <div className="space-y-4">
              <div>
                <strong>Общее резюме:</strong>
                <p className="mt-1">{selectedReport.summary || 'Не указано'}</p>
              </div>
              {selectedReport.academic_progress && (
                <div>
                  <strong>Академический прогресс:</strong>
                  <p className="mt-1">{selectedReport.academic_progress}</p>
                </div>
              )}
              {selectedReport.behavior_notes && (
                <div>
                  <strong>Заметки о поведении:</strong>
                  <p className="mt-1">{selectedReport.behavior_notes}</p>
                </div>
              )}
              {selectedReport.achievements && (
                <div>
                  <strong>Достижения:</strong>
                  <p className="mt-1">{selectedReport.achievements}</p>
                </div>
              )}
              {selectedReport.concerns && (
                <div>
                  <strong>Обеспокоенности:</strong>
                  <p className="mt-1">{selectedReport.concerns}</p>
                </div>
              )}
              {selectedReport.recommendations && (
                <div>
                  <strong>Рекомендации:</strong>
                  <p className="mt-1">{selectedReport.recommendations}</p>
                </div>
              )}
              <div className="grid grid-cols-3 gap-4 pt-4 border-t">
                <div>
                  <strong>Посещаемость:</strong>
                  <p>{selectedReport.attendance_days || 0} / {selectedReport.total_days || 0} дней ({selectedReport.attendance_percentage || 0}%)</p>
                </div>
                <div>
                  <strong>Прогресс:</strong>
                  <p>{selectedReport.progress_percentage || 0}%</p>
                </div>
                <div>
                  <strong>Статус:</strong>
                  <div>{getStatusBadge(selectedReport.status || 'draft')}</div>
                </div>
              </div>
              {selectedReport && selectedReport.status === 'sent' && selectedReport.id && (
                <div className="flex justify-end pt-4 border-t">
                  <Button
                    onClick={() => {
                      handleMarkAsRead(selectedReport.id);
                      setSelectedReport(null);
                    }}
                    disabled={loading}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Отметить как прочитанный
                  </Button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </SidebarProvider>
  );
}