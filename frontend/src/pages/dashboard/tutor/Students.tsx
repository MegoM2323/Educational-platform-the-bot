import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { TutorSidebar } from '@/components/layout/TutorSidebar';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useTutorStudents, useCreateTutorStudent } from '@/hooks/useTutor';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import AssignSubjectDialog from '@/components/tutor/AssignSubjectDialog';
import { TutorStudentSchedule } from '@/components/scheduling/tutor/TutorStudentSchedule';

export default function TutorStudentsPage() {
  const { data: students, isLoading } = useTutorStudents();
  const createMutation = useCreateTutorStudent();
  const { toast } = useToast();

  const [open, setOpen] = useState(false);
  const [credsOpen, setCredsOpen] = useState(false);
  const [generatedCreds, setGeneratedCreds] = useState<{ student: { username: string; password: string }; parent: { username: string; password: string } } | null>(null);
  const [assignOpen, setAssignOpen] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedStudentForDetails, setSelectedStudentForDetails] = useState<any | null>(null);
  const [detailsTab, setDetailsTab] = useState<'overview' | 'schedule'>('overview');
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  
  // Логируем изменения в данных студентов для отладки
  useEffect(() => {
    if (students) {
      const totalSubjects = students.reduce((sum, s) => sum + (s.subjects?.length || 0), 0);
      logger.debug(`[TutorStudentsPage] Rendered with ${students.length} students, ${totalSubjects} total subjects`);
      
      students.forEach(s => {
        const subjectsCount = s.subjects?.length || 0;
        logger.debug(`[TutorStudentsPage] - Student ${s.id} (${s.full_name}): ${subjectsCount} subjects`);
        if (subjectsCount > 0) {
          s.subjects?.forEach(subj => {
            logger.debug(`    * ${subj.name} (teacher: ${subj.teacher_name})`);
          });
        }
      });
    }
  }, [students]);

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    grade: '',
    goal: '',
    parent_first_name: '',
    parent_last_name: '',
    parent_email: '',
    parent_phone: '',
  });

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    
    if (!form.first_name.trim()) {
      errors.first_name = 'Имя обязательно для заполнения';
    }
    
    if (!form.last_name.trim()) {
      errors.last_name = 'Фамилия обязательна для заполнения';
    }
    
    if (!form.grade.trim()) {
      errors.grade = 'Класс обязателен для заполнения';
    }
    
    if (!form.parent_first_name.trim()) {
      errors.parent_first_name = 'Имя родителя обязательно для заполнения';
    }
    
    if (!form.parent_last_name.trim()) {
      errors.parent_last_name = 'Фамилия родителя обязательна для заполнения';
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const submit = async () => {
    if (!validateForm()) {
      toast({
        title: "Ошибка валидации",
        description: "Пожалуйста, заполните все обязательные поля",
        variant: "destructive"
      });
      return;
    }

    try {
      logger.debug('Submitting student creation form:', form);
      const res = await createMutation.mutateAsync(form);
      logger.debug('Student created successfully:', res);
      
      setGeneratedCreds(res.credentials);
      setOpen(false);
      setCredsOpen(true);
      
      // Очищаем форму
      setForm({
        first_name: '',
        last_name: '',
        grade: '',
        goal: '',
        parent_first_name: '',
        parent_last_name: '',
        parent_email: '',
        parent_phone: '',
      });
      setValidationErrors({});
      
      // Данные уже обновляются через onSuccess в useCreateTutorStudent
      // Toast показывается в хуке useCreateTutorStudent
      logger.debug('[Students] Student created, data should be refreshed automatically');
    } catch (error: any) {
      // Ошибка уже обрабатывается в onError хука useCreateTutorStudent
      logger.error('Error creating student:', error);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setForm({ ...form, [field]: value });
    // Очищаем ошибку для этого поля
    if (validationErrors[field]) {
      const newErrors = { ...validationErrors };
      delete newErrors[field];
      setValidationErrors(newErrors);
    }
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TutorSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
            <Button onClick={() => setOpen(true)}>Создать ученика</Button>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <Card className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold">Мои ученики</h2>
                  <Badge variant="secondary">{students?.length || 0}</Badge>
                </div>
                {isLoading ? (
                  <div>Загрузка...</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {students?.map((s) => {
                      const subjectsCount = s.subjects?.length || 0;
                      return (
                        <Card
                          key={s.id}
                          className="p-4 space-y-3 cursor-pointer hover:border-primary transition-colors"
                          onClick={() => {
                            setSelectedStudentForDetails(s);
                            setDetailsTab('overview');
                            setDetailsOpen(true);
                          }}
                        >
                          <div className="font-medium">{s.full_name || `${s.first_name || ''} ${s.last_name || ''}`}</div>
                          <div className="text-sm text-muted-foreground">Класс: {s.grade || '-'}</div>
                          <div className="text-sm text-muted-foreground">Цель: {s.goal || '-'}</div>

                          {/* Назначенные предметы */}
                          {subjectsCount > 0 ? (
                            <div className="space-y-2">
                              <div className="text-sm font-semibold">Назначенные предметы ({subjectsCount}):</div>
                              <div className="space-y-1 max-h-32 overflow-y-auto">
                                {s.subjects?.map((subject) => (
                                  <div key={subject.enrollment_id} className="text-sm text-muted-foreground pl-2 border-l-2 border-primary">
                                    <div className="font-medium">{subject.name}</div>
                                    <div className="text-xs">Преподаватель: {subject.teacher_name || 'Не указан'}</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <div className="text-sm text-muted-foreground italic">Нет назначенных предметов</div>
                          )}

                          <div className="pt-2 flex gap-2" onClick={(e) => e.stopPropagation()}>
                            <Button variant="secondary" size="sm" onClick={() => {
                              logger.debug('[Students] Opening assign dialog for student:', s.id);
                              setSelectedStudentId(s.id);
                              setAssignOpen(true);
                            }}>Назначить предмет</Button>
                          </div>
                        </Card>
                      );
                    })}
                  </div>
                )}
              </Card>
            </div>
          </main>
        </SidebarInset>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Создание ученика</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="first_name">Имя *</Label>
              <Input 
                id="first_name"
                value={form.first_name} 
                onChange={(e) => handleInputChange('first_name', e.target.value)}
                className={validationErrors.first_name ? 'border-red-500' : ''}
              />
              {validationErrors.first_name && (
                <p className="text-sm text-red-500 mt-1">{validationErrors.first_name}</p>
              )}
            </div>
            <div>
              <Label htmlFor="last_name">Фамилия *</Label>
              <Input 
                id="last_name"
                value={form.last_name} 
                onChange={(e) => handleInputChange('last_name', e.target.value)}
                className={validationErrors.last_name ? 'border-red-500' : ''}
              />
              {validationErrors.last_name && (
                <p className="text-sm text-red-500 mt-1">{validationErrors.last_name}</p>
              )}
            </div>
            <div>
              <Label htmlFor="grade">Класс *</Label>
              <Input 
                id="grade"
                value={form.grade} 
                onChange={(e) => handleInputChange('grade', e.target.value)}
                className={validationErrors.grade ? 'border-red-500' : ''}
                placeholder="например, 7Б"
              />
              {validationErrors.grade && (
                <p className="text-sm text-red-500 mt-1">{validationErrors.grade}</p>
              )}
            </div>
            <div className="md:col-span-2">
              <Label htmlFor="goal">Цель (необязательно)</Label>
              <Input 
                id="goal"
                value={form.goal} 
                onChange={(e) => handleInputChange('goal', e.target.value)}
                placeholder="Дополнительная информация о целях обучения"
              />
            </div>
            <div className="md:col-span-2">
              <h3 className="text-lg font-semibold mb-3">Данные родителя</h3>
            </div>
            <div>
              <Label htmlFor="parent_first_name">Имя родителя *</Label>
              <Input 
                id="parent_first_name"
                value={form.parent_first_name} 
                onChange={(e) => handleInputChange('parent_first_name', e.target.value)}
                className={validationErrors.parent_first_name ? 'border-red-500' : ''}
              />
              {validationErrors.parent_first_name && (
                <p className="text-sm text-red-500 mt-1">{validationErrors.parent_first_name}</p>
              )}
            </div>
            <div>
              <Label htmlFor="parent_last_name">Фамилия родителя *</Label>
              <Input 
                id="parent_last_name"
                value={form.parent_last_name} 
                onChange={(e) => handleInputChange('parent_last_name', e.target.value)}
                className={validationErrors.parent_last_name ? 'border-red-500' : ''}
              />
              {validationErrors.parent_last_name && (
                <p className="text-sm text-red-500 mt-1">{validationErrors.parent_last_name}</p>
              )}
            </div>
            <div>
              <Label htmlFor="parent_email">Email родителя (необязательно)</Label>
              <Input 
                id="parent_email"
                type="email"
                value={form.parent_email} 
                onChange={(e) => handleInputChange('parent_email', e.target.value)}
                placeholder="parent@example.com"
              />
            </div>
            <div>
              <Label htmlFor="parent_phone">Телефон родителя (необязательно)</Label>
              <Input 
                id="parent_phone"
                type="tel"
                value={form.parent_phone} 
                onChange={(e) => handleInputChange('parent_phone', e.target.value)}
                placeholder="+79991234567"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Отмена</Button>
            <Button onClick={submit} disabled={createMutation.isPending}>Создать</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={credsOpen} onOpenChange={setCredsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Сгенерированные учетные данные</DialogTitle>
          </DialogHeader>
          {generatedCreds ? (
            <div className="space-y-3">
              <Card className="p-3">
                <div className="font-semibold mb-2">Ученик</div>
                <div className="text-sm">Логин: {generatedCreds.student.username}</div>
                <div className="text-sm">Пароль: {generatedCreds.student.password}</div>
              </Card>
              <Card className="p-3">
                <div className="font-semibold mb-2">Родитель</div>
                <div className="text-sm">Логин: {generatedCreds.parent.username}</div>
                <div className="text-sm">Пароль: {generatedCreds.parent.password}</div>
              </Card>
            </div>
          ) : null}
          <DialogFooter>
            <Button onClick={() => setCredsOpen(false)}>Закрыть</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {selectedStudentId !== null && (
        <AssignSubjectDialog
          open={assignOpen}
          onOpenChange={(open) => {
            setAssignOpen(open);
            if (!open) {
              setSelectedStudentId(null);
            }
          }}
          studentId={selectedStudentId}
        />
      )}

      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {selectedStudentForDetails?.full_name || `${selectedStudentForDetails?.first_name || ''} ${selectedStudentForDetails?.last_name || ''}`}
            </DialogTitle>
          </DialogHeader>

          {selectedStudentForDetails && (
            <Tabs value={detailsTab} onValueChange={(v) => setDetailsTab(v as 'overview' | 'schedule')}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="overview">Обзор</TabsTrigger>
                <TabsTrigger value="schedule">Расписание</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-semibold text-muted-foreground">Класс</label>
                      <p className="text-base font-medium">{selectedStudentForDetails.grade || '-'}</p>
                    </div>
                    <div>
                      <label className="text-sm font-semibold text-muted-foreground">Цель обучения</label>
                      <p className="text-base font-medium">{selectedStudentForDetails.goal || '-'}</p>
                    </div>
                  </div>

                  {selectedStudentForDetails.subjects && selectedStudentForDetails.subjects.length > 0 ? (
                    <div className="space-y-2">
                      <label className="text-sm font-semibold text-muted-foreground">
                        Назначенные предметы ({selectedStudentForDetails.subjects.length})
                      </label>
                      <div className="space-y-2">
                        {selectedStudentForDetails.subjects.map((subject: any) => (
                          <Card key={subject.enrollment_id} className="p-3">
                            <div className="font-medium text-sm">{subject.name}</div>
                            <div className="text-xs text-muted-foreground">
                              Преподаватель: {subject.teacher_name || 'Не указан'}
                            </div>
                          </Card>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 bg-muted rounded-lg text-center text-sm text-muted-foreground">
                      Нет назначенных предметов
                    </div>
                  )}

                  <Button
                    variant="secondary"
                    className="w-full"
                    onClick={() => {
                      setSelectedStudentId(selectedStudentForDetails.id);
                      setAssignOpen(true);
                    }}
                  >
                    Назначить новый предмет
                  </Button>
                </div>
              </TabsContent>

              <TabsContent value="schedule">
                <TutorStudentSchedule studentId={selectedStudentForDetails.id.toString()} />
              </TabsContent>
            </Tabs>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailsOpen(false)}>
              Закрыть
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SidebarProvider>
  );
}
