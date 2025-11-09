import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileText, Plus, Send, Clock, Eye, Users, Calendar, FileDown } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TutorSidebar } from "@/components/layout/TutorSidebar";
import { tutorWeeklyReportsAPI, teacherWeeklyReportsAPI, TutorWeeklyReport, TeacherWeeklyReport, TutorStudent, CreateTutorWeeklyReportRequest } from "@/integrations/api/reports";
import { useToast } from "@/hooks/use-toast";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function TutorReports() {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tutorReports, setTutorReports] = useState<TutorWeeklyReport[]>([]);
  const [teacherReports, setTeacherReports] = useState<TeacherWeeklyReport[]>([]);
  const [students, setStudents] = useState<TutorStudent[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<number | null>(null);
  const [selectedReport, setSelectedReport] = useState<TutorWeeklyReport | null>(null);
  const [selectedTeacherReport, setSelectedTeacherReport] = useState<TeacherWeeklyReport | null>(null);
  const [activeTab, setActiveTab] = useState<'my-reports' | 'teacher-reports'>('my-reports');
  const { toast } = useToast();

  // Форма создания отчета
  const [formData, setFormData] = useState<CreateTutorWeeklyReportRequest>({
    student: 0,
    week_start: '',
    week_end: '',
    title: 'Еженедельный отчет',
    summary: '',
    academic_progress: '',
    behavior_notes: '',
    achievements: '',
    concerns: '',
    recommendations: '',
    attendance_days: 0,
    total_days: 7,
    progress_percentage: 0,
    attachment: undefined,
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      console.log('[Tutor Reports] Loading data...');
      const [reports, studentsData] = await Promise.all([
        tutorWeeklyReportsAPI.getReports(),
        tutorWeeklyReportsAPI.getAvailableStudents(),
      ]);
      console.log('[Tutor Reports] Reports loaded:', reports);
      console.log('[Tutor Reports] Students loaded:', studentsData);
      const reportsArray = Array.isArray(reports) ? reports : [];
      const studentsArray = Array.isArray(studentsData) ? studentsData : [];
      console.log('[Tutor Reports] Setting reports:', reportsArray.length);
      console.log('[Tutor Reports] Setting students:', studentsArray.length);
      setTutorReports(reportsArray);
      setStudents(studentsArray);
    } catch (error: any) {
      console.error('[Tutor Reports] Error loading reports data:', error);
      console.error('[Tutor Reports] Error details:', {
        message: error?.message,
        response: error?.response,
        stack: error?.stack,
      });
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось загрузить данные',
        variant: 'destructive',
      });
      setTutorReports([]);
      setStudents([]);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const loadTeacherReports = useCallback(async (studentId: number | null = null) => {
    try {
      setLoading(true);
      console.log('[Tutor Reports] Loading teacher reports, studentId:', studentId);
      // Загружаем все отчеты преподавателей для тьютора
      const allReports = await teacherWeeklyReportsAPI.getReports();
      console.log('[Tutor Reports] Teacher reports loaded:', allReports);
      let reports = Array.isArray(allReports) ? allReports : [];
      console.log('[Tutor Reports] Teacher reports array length:', reports.length);
      
      // Если выбран конкретный студент, фильтруем на фронтенде
      if (studentId) {
        const beforeFilter = reports.length;
        reports = reports.filter(r => r.student === studentId);
        console.log('[Tutor Reports] Filtered reports:', beforeFilter, '->', reports.length);
      }
      
      console.log('[Tutor Reports] Setting teacher reports:', reports.length);
      setTeacherReports(reports);
    } catch (error: any) {
      console.error('[Tutor Reports] Error loading teacher reports:', error);
      console.error('[Tutor Reports] Error details:', {
        message: error?.message,
        response: error?.response,
        stack: error?.stack,
      });
      toast({
        title: 'Ошибка',
        description: error.message || 'Не удалось загрузить отчеты преподавателей',
        variant: 'destructive',
      });
      setTeacherReports([]);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    // Очищаем кэш при загрузке страницы для получения свежих данных
    const clearCache = async () => {
      const { cacheService } = await import('../../../services/cacheService');
      cacheService.delete('/reports/tutor-weekly-reports/');
      cacheService.delete('/reports/tutor-weekly-reports/available_students/');
      cacheService.delete('/reports/teacher-weekly-reports/');
    };
    clearCache().then(() => {
      loadData();
    });
  }, [loadData]);

  useEffect(() => {
    if (activeTab === 'teacher-reports') {
      // Загружаем все отчеты преподавателей, фильтруем по выбранному студенту если есть
      loadTeacherReports(selectedStudent);
    }
  }, [selectedStudent, activeTab, loadTeacherReports]);

  const handleCreateReport = async () => {
    if (!formData.student || formData.student === 0 || !formData.week_start || !formData.week_end || !formData.summary) {
      toast({
        title: 'Ошибка',
        description: 'Заполните все обязательные поля (ученик, период, резюме)',
        variant: 'destructive',
      });
      return;
    }

    try {
      setLoading(true);
      console.log('Creating tutor report with data:', {
        student: formData.student,
        week_start: formData.week_start,
        week_end: formData.week_end,
        summary: formData.summary,
        title: formData.title,
      });
      const createdReport = await tutorWeeklyReportsAPI.createReport(formData);
      console.log('Report created successfully:', createdReport);
      
      // Добавляем созданный отчет в список сразу
      if (createdReport && createdReport.id) {
        setTutorReports(prev => {
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
      cacheService.delete('/reports/tutor-weekly-reports/');
      // Обновляем данные в фоне для синхронизации
      loadData().catch(err => console.error('Error refreshing data:', err));
    } catch (error: any) {
      console.error('Error creating tutor report:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Не удалось создать отчет';
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
      console.log('Sending tutor report:', reportId);
      await tutorWeeklyReportsAPI.sendReport(reportId);
      console.log('Report sent successfully');
      toast({
        title: 'Успешно',
        description: 'Отчет отправлен родителю',
      });
      // Очищаем кэш и обновляем список отчетов тьютора
      const { cacheService } = await import('../../../services/cacheService');
      cacheService.delete('/reports/tutor-weekly-reports/');
      cacheService.delete('/reports/teacher-weekly-reports/');
      await loadData();
      // Обновляем список отчетов преподавателей, если открыта соответствующая вкладка
      if (activeTab === 'teacher-reports') {
        await loadTeacherReports(selectedStudent);
      }
    } catch (error: any) {
      console.error('Error sending tutor report:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Не удалось отправить отчет';
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
      week_start: '',
      week_end: '',
      title: 'Еженедельный отчет',
      summary: '',
      academic_progress: '',
      behavior_notes: '',
      achievements: '',
      concerns: '',
      recommendations: '',
      attendance_days: 0,
      total_days: 7,
      progress_percentage: 0,
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

  // Вычисляем начало и конец текущей недели
  const getCurrentWeek = () => {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1); // Понедельник
    const monday = new Date(now.setDate(diff));
    monday.setHours(0, 0, 0, 0);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    sunday.setHours(23, 59, 59, 999);
    return {
      start: monday.toISOString().split('T')[0],
      end: sunday.toISOString().split('T')[0],
    };
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

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TutorSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Отчёты</h1>
            </div>
            <div className="ml-auto">
              <Button
                className="gradient-primary shadow-glow"
                onClick={() => setShowCreateForm(true)}
                disabled={students.length === 0}
              >
                <Plus className="w-4 h-4 mr-2" />
                Создать отчёт родителю
              </Button>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'my-reports' | 'teacher-reports')}>
              <TabsList>
                <TabsTrigger value="my-reports">Мои отчёты родителям</TabsTrigger>
                <TabsTrigger value="teacher-reports">Отчёты от преподавателей</TabsTrigger>
              </TabsList>

              <TabsContent value="my-reports" className="space-y-4">
                {/* Мои отчеты родителям */}
                {loading && tutorReports.length === 0 ? (
                  <Card className="p-6">
                    <div className="text-center text-muted-foreground">Загрузка...</div>
                  </Card>
                ) : (
                  <div className="grid md:grid-cols-2 gap-4">
                    {tutorReports.length === 0 && !loading && (
                      <Card className="p-6 col-span-2">
                        <div className="text-center text-muted-foreground">
                          <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                          <p>Отчётов пока нет</p>
                          <p className="text-xs mt-2">Создайте новый отчёт, нажав кнопку "Создать отчёт родителю"</p>
                        </div>
                      </Card>
                    )}
                  {tutorReports.filter(report => report && report.id).map((report) => (
                    <Card key={report.id} className="p-6 hover:border-primary transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h3 className="font-bold mb-1">{report.title || 'Без названия'}</h3>
                          <div className="text-sm text-muted-foreground mb-2">
                            Ученик: {report.student_name || 'Не указан'}
                          </div>
                          <div className="text-sm text-muted-foreground mb-2">
                            Родитель: {report.parent_name || 'Не назначен'}
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
                        {report && report.status === 'draft' && report.id && (
                          <Button
                            size="sm"
                            onClick={() => handleSendReport(report.id)}
                            disabled={loading}
                          >
                            <Send className="w-4 h-4 mr-2" />
                            Отправить
                          </Button>
                        )}
                      </div>
                    </Card>
                  ))}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="teacher-reports" className="space-y-4">
                {/* Отчёты от преподавателей */}
                <Card className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <Label>Фильтр по ученику</Label>
                    {selectedStudent && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedStudent(null)}
                      >
                        Показать все
                      </Button>
                    )}
                  </div>
                  <Select
                    value={selectedStudent?.toString() || 'all'}
                    onValueChange={(value) => {
                      if (value === 'all') {
                        setSelectedStudent(null);
                      } else {
                        setSelectedStudent(parseInt(value));
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Все ученики" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Все ученики</SelectItem>
                      {students.map((student) => (
                        <SelectItem key={student.id} value={student.id.toString()}>
                          {student.name} ({student.grade} класс)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Card>

                {loading && teacherReports.length === 0 ? (
                  <Card className="p-6">
                    <div className="text-center text-muted-foreground">Загрузка...</div>
                  </Card>
                ) : (
                  <div className="grid md:grid-cols-2 gap-4">
                    {teacherReports.length === 0 && !loading && (
                      <Card className="p-6 col-span-2">
                        <div className="text-center text-muted-foreground">
                          <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                          <p>
                            {selectedStudent 
                              ? 'Отчётов от преподавателей по выбранному ученику пока нет'
                              : 'Отчётов от преподавателей пока нет'}
                          </p>
                        </div>
                      </Card>
                    )}
                    {teacherReports.filter(report => report && report.id).map((report) => (
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
                              Преподаватель: {report.teacher_name || 'Не указан'}
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
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full mt-4"
                          onClick={() => report && setSelectedTeacherReport(report)}
                          disabled={!report}
                        >
                          <Eye className="w-4 h-4 mr-2" />
                          Просмотр
                        </Button>
                      </Card>
                    ))}
                    </div>
                )}
              </TabsContent>
            </Tabs>
          </main>
        </SidebarInset>
      </div>

      {/* Диалог создания отчета */}
      <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Создать еженедельный отчёт</DialogTitle>
            <DialogDescription>Заполните форму для создания отчёта родителю</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Ученик *</Label>
              <Select
                value={formData.student && formData.student > 0 ? formData.student.toString() : ''}
                onValueChange={(value) => setFormData({ ...formData, student: parseInt(value) })}
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
              <Label>Заметки о поведении</Label>
              <Textarea
                value={formData.behavior_notes}
                onChange={(e) => setFormData({ ...formData, behavior_notes: e.target.value })}
                placeholder="Заметки о поведении..."
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
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Дней посещения</Label>
                <Input
                  type="number"
                  min="0"
                  max="7"
                  value={formData.attendance_days}
                  onChange={(e) => setFormData({ ...formData, attendance_days: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div>
                <Label>Всего дней</Label>
                <Input
                  type="number"
                  min="1"
                  value={formData.total_days}
                  onChange={(e) => setFormData({ ...formData, total_days: parseInt(e.target.value) || 7 })}
                />
              </div>
              <div>
                <Label>Процент прогресса</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={formData.progress_percentage}
                  onChange={(e) => setFormData({ ...formData, progress_percentage: parseInt(e.target.value) || 0 })}
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

      {/* Диалог просмотра отчета тьютора */}
      <Dialog open={!!selectedReport} onOpenChange={() => setSelectedReport(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedReport?.title}</DialogTitle>
            <DialogDescription>
              Отчёт по ученику {selectedReport?.student_name || 'Не указан'} {selectedReport?.parent_name && `(Родитель: ${selectedReport.parent_name})`} {selectedReport?.week_start && selectedReport?.week_end && `за период ${new Date(selectedReport.week_start).toLocaleDateString('ru-RU')} - ${new Date(selectedReport.week_end).toLocaleDateString('ru-RU')}`}
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
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Диалог просмотра отчета преподавателя */}
      <Dialog open={!!selectedTeacherReport} onOpenChange={() => setSelectedTeacherReport(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedTeacherReport?.title}</DialogTitle>
            <DialogDescription>
              Отчёт от {selectedTeacherReport?.teacher_name || 'Не указан'} по предмету {selectedTeacherReport?.subject_name || 'Не указан'} по ученику {selectedTeacherReport?.student_name || 'Не указан'} {selectedTeacherReport?.tutor_name && `(Тьютор: ${selectedTeacherReport.tutor_name})`}
            </DialogDescription>
          </DialogHeader>
          {selectedTeacherReport && (
            <div className="space-y-4">
              <div>
                <strong>Общее резюме:</strong>
                <p className="mt-1">{selectedTeacherReport.summary || 'Не указано'}</p>
              </div>
              {selectedTeacherReport.academic_progress && (
                <div>
                  <strong>Академический прогресс:</strong>
                  <p className="mt-1">{selectedTeacherReport.academic_progress}</p>
                </div>
              )}
              {selectedTeacherReport.performance_notes && (
                <div>
                  <strong>Заметки об успеваемости:</strong>
                  <p className="mt-1">{selectedTeacherReport.performance_notes}</p>
                </div>
              )}
              {selectedTeacherReport.achievements && (
                <div>
                  <strong>Достижения:</strong>
                  <p className="mt-1">{selectedTeacherReport.achievements}</p>
                </div>
              )}
              {selectedTeacherReport.concerns && (
                <div>
                  <strong>Обеспокоенности:</strong>
                  <p className="mt-1">{selectedTeacherReport.concerns}</p>
                </div>
              )}
              {selectedTeacherReport.recommendations && (
                <div>
                  <strong>Рекомендации:</strong>
                  <p className="mt-1">{selectedTeacherReport.recommendations}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <strong>Выполнено заданий:</strong>
                  <p>{selectedTeacherReport.assignments_completed || 0} / {selectedTeacherReport.assignments_total || 0} ({selectedTeacherReport.completion_percentage || 0}%)</p>
                </div>
                {(selectedTeacherReport.average_score !== undefined && selectedTeacherReport.average_score !== null) && (
                  <div>
                    <strong>Средний балл:</strong>
                    <p>{selectedTeacherReport.average_score}</p>
                  </div>
                )}
                {(selectedTeacherReport.attendance_percentage !== undefined && selectedTeacherReport.attendance_percentage > 0) && (
                  <div>
                    <strong>Посещаемость:</strong>
                    <p>{selectedTeacherReport.attendance_percentage}%</p>
                  </div>
                )}
                <div>
                  <strong>Статус:</strong>
                  <div>{getStatusBadge(selectedTeacherReport.status || 'draft')}</div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </SidebarProvider>
  );
}