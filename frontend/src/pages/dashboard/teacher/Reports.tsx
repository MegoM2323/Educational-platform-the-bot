import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileText, Plus, Send, Clock, Eye, Calendar, Edit2, Trash2 } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { teacherWeeklyReportsAPI, TeacherWeeklyReport, TeacherStudent, CreateTeacherWeeklyReportRequest } from "@/integrations/api/reports";
import { useToast } from "@/hooks/use-toast";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function TeacherReports() {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingReport, setEditingReport] = useState<TeacherWeeklyReport | null>(null);
  const [deleteConfirmReport, setDeleteConfirmReport] = useState<TeacherWeeklyReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<TeacherWeeklyReport[]>([]);
  const [students, setStudents] = useState<TeacherStudent[]>([]);
  const [selectedReport, setSelectedReport] = useState<TeacherWeeklyReport | null>(null);
  const { toast } = useToast();

  // Форма создания отчета
  const [formData, setFormData] = useState<CreateTeacherWeeklyReportRequest>({
    student: 0,
    subject: 0,
    week_start: '',
    week_end: '',
    title: 'Еженедельный отчет',
    summary: '',
    academic_progress: '',
    performance_notes: '',
    achievements: '',
    concerns: '',
    recommendations: '',
    assignments_completed: 0,
    assignments_total: 0,
    average_score: undefined,
    attendance_percentage: 0,
    attachment: undefined,
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      console.log('[Teacher Reports] Loading data...');
      const [reportsData, studentsData] = await Promise.all([
        teacherWeeklyReportsAPI.getReports(),
        teacherWeeklyReportsAPI.getAvailableStudents(),
      ]);
      console.log('[Teacher Reports] Reports loaded:', reportsData);
      console.log('[Teacher Reports] Students loaded:', studentsData);
      const reportsArray = Array.isArray(reportsData) ? reportsData : [];
      const studentsArray = Array.isArray(studentsData) ? studentsData : [];
      console.log('[Teacher Reports] Setting reports:', reportsArray.length);
      console.log('[Teacher Reports] Setting students:', studentsArray.length);
      setReports(reportsArray);
      setStudents(studentsArray);
    } catch (error: any) {
      console.error('[Teacher Reports] Error loading reports data:', error);
      console.error('[Teacher Reports] Error details:', {
        message: error?.message,
        response: error?.response,
        stack: error?.stack,
      });
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось загрузить данные',
        variant: 'destructive',
      });
      setReports([]);
      setStudents([]);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    // Очищаем кэш при загрузке страницы для получения свежих данных
    const clearCache = async () => {
      const { cacheService } = await import('../../../services/cacheService');
      cacheService.delete('/reports/teacher-weekly-reports/');
      cacheService.delete('/reports/teacher-weekly-reports/available_students/');
    };
    clearCache().then(() => {
      loadData();
    });
  }, [loadData]);

  const handleCreateReport = async () => {
    if (!formData.student || formData.student === 0 || !formData.subject || formData.subject === 0 || !formData.week_start || !formData.week_end || !formData.summary) {
      toast({
        title: 'Ошибка',
        description: 'Заполните все обязательные поля (ученик, предмет, период, резюме)',
        variant: 'destructive',
      });
      return;
    }

    try {
      setLoading(true);
      console.log('Creating teacher report with data:', {
        student: formData.student,
        subject: formData.subject,
        week_start: formData.week_start,
        week_end: formData.week_end,
        summary: formData.summary,
        title: formData.title,
      });
      const createdReport = await teacherWeeklyReportsAPI.createReport(formData);
      console.log('Report created successfully:', createdReport);
      
      // Добавляем созданный отчет в список сразу
      if (createdReport && createdReport.id) {
        setReports(prev => {
          // Проверяем, нет ли уже такого отчета в списке
          const exists = prev.some(r => r.id === createdReport.id);
          if (!exists) {
            return [createdReport, ...prev];
          }
          return prev.map(r => r.id === createdReport.id ? createdReport : r);
        });
      }
      
      toast({
        title: 'Успешно',
        description: 'Отчет создан',
      });
      setShowCreateForm(false);
      resetForm();
      
      // Очищаем кэш и обновляем список отчетов для синхронизации
      const { cacheService } = await import('../../../services/cacheService');
      cacheService.delete('/reports/teacher-weekly-reports/');
      // Обновляем данные в фоне для синхронизации
      loadData().catch(err => console.error('Error refreshing data:', err));
    } catch (error: any) {
      console.error('Error creating teacher report:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || error?.response?.data?.error || 'Не удалось создать отчет';
      console.error('Error details:', {
        message: errorMessage,
        response: error?.response?.data,
        status: error?.response?.status,
      });
      toast({
        title: 'Ошибка',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSendReport = async (reportId: number) => {
    try {
      setLoading(true);
      console.log('Sending teacher report:', reportId);
      await teacherWeeklyReportsAPI.sendReport(reportId);
      console.log('Report sent successfully');

      // Обновляем статус отчета в состоянии немедленно
      setReports(prev => prev.map(r =>
        r.id === reportId ? { ...r, status: 'sent' as const, sent_at: new Date().toISOString() } : r
      ));

      toast({
        title: 'Успешно',
        description: 'Отчет отправлен тьютору',
      });
      // Очищаем кэш и обновляем список отчетов преподавателя
      const { cacheService } = await import('../../../services/cacheService');
      cacheService.delete('/reports/teacher-weekly-reports/');
      await loadData();
    } catch (error: any) {
      console.error('Error sending teacher report:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || error?.response?.data?.error || 'Не удалось отправить отчет';
      toast({
        title: 'Ошибка',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleEditReport = (report: TeacherWeeklyReport) => {
    setEditingReport(report);
    setFormData({
      student: report.student,
      subject: report.subject,
      week_start: report.week_start,
      week_end: report.week_end,
      title: report.title,
      summary: report.summary,
      academic_progress: report.academic_progress || '',
      performance_notes: report.performance_notes || '',
      achievements: report.achievements || '',
      concerns: report.concerns || '',
      recommendations: report.recommendations || '',
      assignments_completed: report.assignments_completed || 0,
      assignments_total: report.assignments_total || 0,
      average_score: report.average_score,
      attendance_percentage: report.attendance_percentage || 0,
      attachment: undefined,
    });
    setShowEditForm(true);
  };

  const handleUpdateReport = async () => {
    if (!editingReport) return;

    if (!formData.student || formData.student === 0 || !formData.subject || formData.subject === 0 || !formData.week_start || !formData.week_end || !formData.summary) {
      toast({
        title: 'Ошибка',
        description: 'Заполните все обязательные поля (ученик, предмет, период, резюме)',
        variant: 'destructive',
      });
      return;
    }

    try {
      setLoading(true);
      console.log('Updating teacher report:', editingReport.id, formData);
      const updatedReport = await teacherWeeklyReportsAPI.updateReport(editingReport.id, formData);
      console.log('Report updated successfully:', updatedReport);

      // Обновляем отчет в состоянии немедленно
      setReports(prev => prev.map(r =>
        r.id === editingReport.id ? updatedReport : r
      ));

      toast({
        title: 'Успешно',
        description: 'Отчет обновлен',
      });
      setShowEditForm(false);
      setEditingReport(null);
      resetForm();

      // Очищаем кэш
      const { cacheService } = await import('../../../services/cacheService');
      cacheService.delete('/reports/teacher-weekly-reports/');
    } catch (error: any) {
      console.error('Error updating teacher report:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Не удалось обновить отчет';
      toast({
        title: 'Ошибка',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteReport = async (reportId: number) => {
    try {
      setLoading(true);
      console.log('Deleting teacher report:', reportId);
      await teacherWeeklyReportsAPI.deleteReport(reportId);
      console.log('Report deleted successfully');

      // Удаляем отчет из состояния немедленно
      setReports(prev => prev.filter(r => r.id !== reportId));

      toast({
        title: 'Успешно',
        description: 'Отчет удален',
      });
      setDeleteConfirmReport(null);

      // Очищаем кэш
      const { cacheService } = await import('../../../services/cacheService');
      cacheService.delete('/reports/teacher-weekly-reports/');
    } catch (error: any) {
      console.error('Error deleting teacher report:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Не удалось удалить отчет';
      toast({
        title: 'Ошибка',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      student: 0,
      subject: 0,
      week_start: '',
      week_end: '',
      title: 'Еженедельный отчет',
      summary: '',
      academic_progress: '',
      performance_notes: '',
      achievements: '',
      concerns: '',
      recommendations: '',
      assignments_completed: 0,
      assignments_total: 0,
      average_score: undefined,
      attendance_percentage: 0,
      attachment: undefined,
    });
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

  // Получаем предметы для выбранного студента
  const getStudentSubjects = () => {
    if (!formData.student) return [];
    const student = students.find(s => s.id === formData.student);
    return student?.subjects || [];
  };

  // Вычисляем начало и конец текущей недели
  const getCurrentWeek = () => {
    try {
      const now = new Date();
      const day = now.getDay();
      const diff = now.getDate() - day + (day === 0 ? -6 : 1); // Понедельник
      const monday = new Date(now);
      monday.setDate(diff);
      monday.setHours(0, 0, 0, 0);
      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);
      sunday.setHours(23, 59, 59, 999);
      return {
        start: monday.toISOString().split('T')[0],
        end: sunday.toISOString().split('T')[0],
      };
    } catch (error) {
      console.error('Error calculating current week:', error);
      // Fallback на текущую дату
      const today = new Date();
      return {
        start: today.toISOString().split('T')[0],
        end: today.toISOString().split('T')[0],
      };
    }
  };

  useEffect(() => {
    if (showCreateForm && !formData.week_start) {
      try {
        const week = getCurrentWeek();
        if (week.start && week.end) {
          setFormData(prev => ({ ...prev, week_start: week.start, week_end: week.end }));
        }
      } catch (error) {
        console.error('Error setting week dates:', error);
      }
    }
  }, [showCreateForm]);

  // Сбрасываем предмет при смене студента
  useEffect(() => {
    if (formData.student && getStudentSubjects().length > 0 && !getStudentSubjects().find(s => s.id === formData.subject)) {
      setFormData(prev => ({ ...prev, subject: 0 }));
    }
  }, [formData.student]);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Еженедельные отчёты тьютору</h1>
            </div>
            <div className="ml-auto">
              <Button
                className="gradient-primary shadow-glow"
                onClick={() => setShowCreateForm(true)}
                disabled={students.length === 0}
              >
                <Plus className="w-4 h-4 mr-2" />
                Создать отчёт
              </Button>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <div className="space-y-6">
              {/* Reports List */}
              <div className="grid md:grid-cols-2 gap-4">
                {reports.length === 0 && !loading && (
                  <Card className="p-6 col-span-2">
                    <div className="text-center text-muted-foreground">
                      <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>Отчётов пока нет</p>
                      <p className="text-xs mt-2">Создайте новый отчёт, нажав кнопку "Создать отчёт"</p>
                    </div>
                  </Card>
                )}
                {reports.filter(report => report && report.id).map((report) => (
                  <Card key={report.id} className="p-6 hover:border-primary transition-colors">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-bold">{report.title || 'Без названия'}</h3>
                          {report.subject_name && (
                            <Badge
                              style={{ backgroundColor: report.subject_color || '#808080', color: 'white' }}
                            >
                              {report.subject_name}
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground mb-2">
                          Ученик: {report.student_name || 'Не указан'}
                        </div>
                        {report.tutor_name && (
                          <div className="text-sm text-muted-foreground mb-2">
                            Тьютор: {report.tutor_name}
                          </div>
                        )}
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
                        {(report.average_score !== undefined && report.average_score !== null) && (
                          <div className="text-sm mb-2">
                            Средний балл: <strong>{report.average_score}</strong>
                          </div>
                        )}
                      </div>
                      {getStatusBadge(report.status || 'draft')}
                    </div>
                    <div className="flex items-center gap-2 mt-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => report && setSelectedReport(report)}
                        disabled={!report}
                      >
                        <Eye className="w-4 h-4 mr-2" />
                        Просмотр
                      </Button>
                      {report && report.status === 'draft' && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEditReport(report)}
                            disabled={loading}
                          >
                            <Edit2 className="w-4 h-4 mr-2" />
                            Изменить
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleSendReport(report.id)}
                            disabled={loading}
                          >
                            <Send className="w-4 h-4 mr-2" />
                            Отправить
                          </Button>
                        </>
                      )}
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setDeleteConfirmReport(report)}
                        disabled={loading}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Удалить
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </main>
        </SidebarInset>
      </div>

      {/* Диалог создания отчета */}
      <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Создать еженедельный отчёт тьютору</DialogTitle>
            <DialogDescription>Заполните форму для создания отчёта о прогрессе ученика</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Ученик *</Label>
              <Select
                value={formData.student && formData.student > 0 ? formData.student.toString() : ''}
                onValueChange={(value) => setFormData({ ...formData, student: parseInt(value), subject: 0 })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Выберите ученика" />
                </SelectTrigger>
                <SelectContent>
                  {students.map((student) => (
                    <SelectItem key={student.id} value={student.id.toString()}>
                      {student.name} ({student.grade} класс)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {formData.student > 0 && (
              <div>
                <Label>Предмет *</Label>
                <Select
                  value={formData.subject && formData.subject > 0 ? formData.subject.toString() : ''}
                  onValueChange={(value) => setFormData({ ...formData, subject: parseInt(value) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите предмет" />
                  </SelectTrigger>
                  <SelectContent>
                    {getStudentSubjects().map((subject) => (
                      <SelectItem key={subject.id} value={subject.id.toString()}>
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: subject.color }}
                          />
                          {subject.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Начало недели *</Label>
                <Input
                  type="date"
                  value={formData.week_start}
                  onChange={(e) => setFormData({ ...formData, week_start: e.target.value })}
                />
              </div>
              <div>
                <Label>Конец недели *</Label>
                <Input
                  type="date"
                  value={formData.week_end}
                  onChange={(e) => setFormData({ ...formData, week_end: e.target.value })}
                />
              </div>
            </div>
            <div>
              <Label>Название</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Еженедельный отчёт"
              />
            </div>
            <div>
              <Label>Общее резюме *</Label>
              <Textarea
                value={formData.summary}
                onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                placeholder="Общее резюме недели..."
                rows={4}
              />
            </div>
            <div>
              <Label>Академический прогресс</Label>
              <Textarea
                value={formData.academic_progress}
                onChange={(e) => setFormData({ ...formData, academic_progress: e.target.value })}
                placeholder="Опишите академический прогресс..."
                rows={3}
              />
            </div>
            <div>
              <Label>Заметки об успеваемости</Label>
              <Textarea
                value={formData.performance_notes}
                onChange={(e) => setFormData({ ...formData, performance_notes: e.target.value })}
                placeholder="Заметки об успеваемости..."
                rows={3}
              />
            </div>
            <div>
              <Label>Достижения</Label>
              <Textarea
                value={formData.achievements}
                onChange={(e) => setFormData({ ...formData, achievements: e.target.value })}
                placeholder="Достижения ученика..."
                rows={3}
              />
            </div>
            <div>
              <Label>Обеспокоенности</Label>
              <Textarea
                value={formData.concerns}
                onChange={(e) => setFormData({ ...formData, concerns: e.target.value })}
                placeholder="Обеспокоенности..."
                rows={3}
              />
            </div>
            <div>
              <Label>Рекомендации</Label>
              <Textarea
                value={formData.recommendations}
                onChange={(e) => setFormData({ ...formData, recommendations: e.target.value })}
                placeholder="Рекомендации..."
                rows={3}
              />
            </div>
            <div className="grid grid-cols-4 gap-4">
              <div>
                <Label>Выполнено заданий</Label>
                <Input
                  type="number"
                  min="0"
                  value={formData.assignments_completed}
                  onChange={(e) => setFormData({ ...formData, assignments_completed: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div>
                <Label>Всего заданий</Label>
                <Input
                  type="number"
                  min="0"
                  value={formData.assignments_total}
                  onChange={(e) => setFormData({ ...formData, assignments_total: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div>
                <Label>Средний балл</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={formData.average_score || ''}
                  onChange={(e) => setFormData({ ...formData, average_score: e.target.value ? parseFloat(e.target.value) : undefined })}
                />
              </div>
              <div>
                <Label>Посещаемость (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={formData.attendance_percentage}
                  onChange={(e) => setFormData({ ...formData, attendance_percentage: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => { setShowCreateForm(false); resetForm(); }}>
                Отмена
              </Button>
              <Button onClick={handleCreateReport} disabled={loading}>
                <Send className="w-4 h-4 mr-2" />
                Создать отчёт
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Диалог просмотра отчета */}
      <Dialog open={!!selectedReport} onOpenChange={() => setSelectedReport(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedReport?.title}</DialogTitle>
            <DialogDescription>
              Отчёт по ученику {selectedReport?.student_name || 'Не указан'} по предмету {selectedReport?.subject_name || 'Не указан'} {selectedReport?.tutor_name && `(Тьютор: ${selectedReport.tutor_name})`} {selectedReport?.week_start && selectedReport?.week_end && `за период ${new Date(selectedReport.week_start).toLocaleDateString('ru-RU')} - ${new Date(selectedReport.week_end).toLocaleDateString('ru-RU')}`}
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
              {selectedReport.performance_notes && (
                <div>
                  <strong>Заметки об успеваемости:</strong>
                  <p className="mt-1">{selectedReport.performance_notes}</p>
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
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <strong>Выполнено заданий:</strong>
                  <p>{selectedReport.assignments_completed || 0} / {selectedReport.assignments_total || 0} ({selectedReport.completion_percentage || 0}%)</p>
                </div>
                {(selectedReport.average_score !== undefined && selectedReport.average_score !== null) && (
                  <div>
                    <strong>Средний балл:</strong>
                    <p>{selectedReport.average_score}</p>
                  </div>
                )}
                {(selectedReport.attendance_percentage !== undefined && selectedReport.attendance_percentage > 0) && (
                  <div>
                    <strong>Посещаемость:</strong>
                    <p>{selectedReport.attendance_percentage}%</p>
                  </div>
                )}
                <div>
                  <strong>Статус:</strong>
                  <div>{getStatusBadge(selectedReport.status || 'draft')}</div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Диалог редактирования отчета */}
      <Dialog open={showEditForm} onOpenChange={(open) => {
        setShowEditForm(open);
        if (!open) {
          setEditingReport(null);
          resetForm();
        }
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Редактировать отчёт</DialogTitle>
            <DialogDescription>Внесите изменения в отчёт</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Ученик *</Label>
              <Select
                value={formData.student && formData.student > 0 ? formData.student.toString() : ''}
                onValueChange={(value) => setFormData({ ...formData, student: parseInt(value), subject: 0 })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Выберите ученика" />
                </SelectTrigger>
                <SelectContent>
                  {students.map((student) => (
                    <SelectItem key={student.id} value={student.id.toString()}>
                      {student.name} ({student.grade} класс)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {formData.student > 0 && (
              <div>
                <Label>Предмет *</Label>
                <Select
                  value={formData.subject && formData.subject > 0 ? formData.subject.toString() : ''}
                  onValueChange={(value) => setFormData({ ...formData, subject: parseInt(value) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите предмет" />
                  </SelectTrigger>
                  <SelectContent>
                    {getStudentSubjects().map((subject) => (
                      <SelectItem key={subject.id} value={subject.id.toString()}>
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: subject.color }}
                          />
                          {subject.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Начало недели *</Label>
                <Input
                  type="date"
                  value={formData.week_start}
                  onChange={(e) => setFormData({ ...formData, week_start: e.target.value })}
                />
              </div>
              <div>
                <Label>Конец недели *</Label>
                <Input
                  type="date"
                  value={formData.week_end}
                  onChange={(e) => setFormData({ ...formData, week_end: e.target.value })}
                />
              </div>
            </div>
            <div>
              <Label>Название</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Еженедельный отчёт"
              />
            </div>
            <div>
              <Label>Общее резюме *</Label>
              <Textarea
                value={formData.summary}
                onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                placeholder="Общее резюме недели..."
                rows={4}
              />
            </div>
            <div>
              <Label>Академический прогресс</Label>
              <Textarea
                value={formData.academic_progress}
                onChange={(e) => setFormData({ ...formData, academic_progress: e.target.value })}
                placeholder="Опишите академический прогресс..."
                rows={3}
              />
            </div>
            <div>
              <Label>Заметки об успеваемости</Label>
              <Textarea
                value={formData.performance_notes}
                onChange={(e) => setFormData({ ...formData, performance_notes: e.target.value })}
                placeholder="Заметки об успеваемости..."
                rows={3}
              />
            </div>
            <div>
              <Label>Достижения</Label>
              <Textarea
                value={formData.achievements}
                onChange={(e) => setFormData({ ...formData, achievements: e.target.value })}
                placeholder="Достижения ученика..."
                rows={3}
              />
            </div>
            <div>
              <Label>Обеспокоенности</Label>
              <Textarea
                value={formData.concerns}
                onChange={(e) => setFormData({ ...formData, concerns: e.target.value })}
                placeholder="Обеспокоенности..."
                rows={3}
              />
            </div>
            <div>
              <Label>Рекомендации</Label>
              <Textarea
                value={formData.recommendations}
                onChange={(e) => setFormData({ ...formData, recommendations: e.target.value })}
                placeholder="Рекомендации..."
                rows={3}
              />
            </div>
            <div className="grid grid-cols-4 gap-4">
              <div>
                <Label>Выполнено заданий</Label>
                <Input
                  type="number"
                  min="0"
                  value={formData.assignments_completed}
                  onChange={(e) => setFormData({ ...formData, assignments_completed: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div>
                <Label>Всего заданий</Label>
                <Input
                  type="number"
                  min="0"
                  value={formData.assignments_total}
                  onChange={(e) => setFormData({ ...formData, assignments_total: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div>
                <Label>Средний балл</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={formData.average_score || ''}
                  onChange={(e) => setFormData({ ...formData, average_score: e.target.value ? parseFloat(e.target.value) : undefined })}
                />
              </div>
              <div>
                <Label>Посещаемость (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={formData.attendance_percentage}
                  onChange={(e) => setFormData({ ...formData, attendance_percentage: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => {
                setShowEditForm(false);
                setEditingReport(null);
                resetForm();
              }}>
                Отмена
              </Button>
              <Button onClick={handleUpdateReport} disabled={loading}>
                <Send className="w-4 h-4 mr-2" />
                Сохранить изменения
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Диалог подтверждения удаления */}
      <AlertDialog open={!!deleteConfirmReport} onOpenChange={(open) => !open && setDeleteConfirmReport(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить отчёт?</AlertDialogTitle>
            <AlertDialogDescription>
              Вы уверены, что хотите удалить отчёт "{deleteConfirmReport?.title}"? Это действие нельзя отменить.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={loading}>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteConfirmReport && handleDeleteReport(deleteConfirmReport.id)}
              disabled={loading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Удалить
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </SidebarProvider>
  );
}