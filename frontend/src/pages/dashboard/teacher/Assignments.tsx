import React, { useState, useMemo } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { Navigate } from "react-router-dom";
import { useAssignments, useCreateAssignment, useDeleteAssignment, useAssignmentSubmissions, useGradeSubmission } from "@/hooks/useAssignments";
import { useTeacherDashboard } from "@/hooks/useTeacher";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileText, Plus, Clock, AlertCircle, CheckCircle, Trash2, Eye } from "lucide-react";
import { Assignment, AssignmentSubmission, CreateAssignmentPayload } from "@/integrations/api/assignmentsAPI";
import { format } from "date-fns";
import { ru } from "date-fns/locale";

const TeacherAssignments: React.FC = () => {
  const { user } = useAuth();
  const { data: assignments = [], isLoading, error } = useAssignments();
  const { data: dashboardData } = useTeacherDashboard();
  const createMutation = useCreateAssignment();
  const deleteMutation = useDeleteAssignment();

  const [activeTab, setActiveTab] = useState<'all' | 'grading'>('all');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [submissionsDialogOpen, setSubmissionsDialogOpen] = useState(false);
  const [gradeDialogOpen, setGradeDialogOpen] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState<Assignment | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<AssignmentSubmission | null>(null);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('');
  const [type, setType] = useState<string>('homework');
  const [maxScore, setMaxScore] = useState(100);
  const [startDate, setStartDate] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [selectedStudents, setSelectedStudents] = useState<number[]>([]);

  // Grade form state
  const [score, setScore] = useState(0);
  const [feedback, setFeedback] = useState('');

  const { data: submissions = [] } = useAssignmentSubmissions(selectedAssignment?.id || 0);
  const gradeMutation = useGradeSubmission(selectedSubmission?.id || 0);

  if (user?.role !== 'teacher') {
    return <Navigate to="/dashboard" replace />;
  }

  const students = dashboardData?.students || [];

  const pendingGradingCount = useMemo(() => {
    return assignments.reduce((count, assignment) => {
      // This is a simplified count - in real implementation, fetch submissions per assignment
      return count;
    }, 0);
  }, [assignments]);

  const handleCreate = async () => {
    if (!title.trim() || !description.trim() || !startDate || !dueDate) {
      return;
    }

    const payload: CreateAssignmentPayload = {
      title,
      description,
      instructions,
      type,
      max_score: maxScore,
      start_date: new Date(startDate).toISOString(),
      due_date: new Date(dueDate).toISOString(),
      assigned_to: selectedStudents,
    };

    try {
      await createMutation.mutateAsync(payload);
      setCreateDialogOpen(false);
      resetForm();
    } catch (error) {
      console.error('Failed to create assignment:', error);
    }
  };

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setInstructions('');
    setType('homework');
    setMaxScore(100);
    setStartDate('');
    setDueDate('');
    setSelectedStudents([]);
  };

  const handleDelete = async (id: number) => {
    if (window.confirm('Вы уверены, что хотите удалить это задание?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const handleGrade = async () => {
    if (!selectedSubmission) return;

    try {
      await gradeMutation.mutateAsync({
        score,
        feedback,
        status: 'graded',
      });
      setGradeDialogOpen(false);
      setScore(0);
      setFeedback('');
      setSelectedSubmission(null);
    } catch (error) {
      console.error('Failed to grade submission:', error);
    }
  };

  const viewSubmissions = (assignment: Assignment) => {
    setSelectedAssignment(assignment);
    setSubmissionsDialogOpen(true);
  };

  const renderAssignmentCard = (assignment: Assignment) => {
    const dueDate = new Date(assignment.due_date);
    const now = new Date();
    const isOverdue = dueDate < now;

    return (
      <Card key={assignment.id} className="overflow-hidden hover:shadow-lg transition-shadow">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5" />
                {assignment.title}
              </CardTitle>
              <CardDescription className="mt-2">{assignment.description}</CardDescription>
            </div>
            <Badge variant={isOverdue ? 'destructive' : 'outline'}>
              {assignment.status === 'draft' && 'Черновик'}
              {assignment.status === 'published' && 'Опубликовано'}
              {assignment.status === 'closed' && 'Закрыто'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              <span>
                Срок: {format(dueDate, 'dd MMMM yyyy, HH:mm', { locale: ru })}
              </span>
            </div>
            <Badge variant="outline">{assignment.max_score} баллов</Badge>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {assignment.type === 'homework' && 'Домашнее задание'}
              {assignment.type === 'test' && 'Тест'}
              {assignment.type === 'project' && 'Проект'}
              {assignment.type === 'essay' && 'Эссе'}
              {assignment.type === 'practical' && 'Практическая работа'}
            </Badge>
            <Badge variant="outline" className="text-xs">
              Уровень {assignment.difficulty_level}
            </Badge>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => viewSubmissions(assignment)}
            >
              <Eye className="w-4 h-4 mr-2" />
              Ответы
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => handleDelete(assignment.id)}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Удалить
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <TeacherSidebar />
        <SidebarInset className="flex-1">
          <header className="sticky top-0 z-10 flex h-16 items-center border-b bg-background px-6">
            <SidebarTrigger />
            <h1 className="ml-4 text-xl font-semibold flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Задания
            </h1>
            <div className="ml-auto">
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Создать задание
              </Button>
            </div>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'all' | 'grading')}>
                <TabsList className="grid w-full sm:w-auto grid-cols-2">
                  <TabsTrigger value="all">
                    Все задания ({assignments.length})
                  </TabsTrigger>
                  <TabsTrigger value="grading">
                    На проверке ({pendingGradingCount})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="all" className="space-y-4 mt-6">
                  {isLoading ? (
                    <div className="space-y-4">
                      {[...Array(3)].map((_, i) => (
                        <Card key={i}>
                          <CardContent className="p-6">
                            <div className="space-y-3">
                              <Skeleton className="h-6 w-1/2" />
                              <Skeleton className="h-4 w-full" />
                              <Skeleton className="h-4 w-2/3" />
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : error ? (
                    <Card className="border-destructive">
                      <CardContent className="p-12 text-center">
                        <AlertCircle className="w-12 h-12 mx-auto mb-4 text-destructive" />
                        <h3 className="text-lg font-semibold mb-2 text-destructive">
                          Ошибка загрузки заданий
                        </h3>
                        <p className="text-muted-foreground">
                          {error instanceof Error ? error.message : 'Не удалось загрузить задания'}
                        </p>
                      </CardContent>
                    </Card>
                  ) : assignments.length === 0 ? (
                    <Card>
                      <CardContent className="p-12 text-center">
                        <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                        <h3 className="text-lg font-semibold mb-2">Нет заданий</h3>
                        <p className="text-muted-foreground mb-4">
                          Вы еще не создали ни одного задания
                        </p>
                        <Button onClick={() => setCreateDialogOpen(true)}>
                          <Plus className="w-4 h-4 mr-2" />
                          Создать первое задание
                        </Button>
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="grid gap-4">
                      {assignments.map(renderAssignmentCard)}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="grading" className="space-y-4 mt-6">
                  <Card>
                    <CardContent className="p-12 text-center">
                      <CheckCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                      <h3 className="text-lg font-semibold mb-2">Все проверено</h3>
                      <p className="text-muted-foreground">
                        Нет заданий, ожидающих проверки
                      </p>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          </main>
        </SidebarInset>
      </div>

      {/* Create Assignment Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Создать задание</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Название</label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Название задания"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Описание</label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Краткое описание задания"
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Инструкции</label>
              <Textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Подробные инструкции по выполнению"
                rows={5}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Тип</label>
                <Select value={type} onValueChange={setType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="homework">Домашнее задание</SelectItem>
                    <SelectItem value="test">Тест</SelectItem>
                    <SelectItem value="project">Проект</SelectItem>
                    <SelectItem value="essay">Эссе</SelectItem>
                    <SelectItem value="practical">Практическая работа</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Максимальный балл</label>
                <Input
                  type="number"
                  value={maxScore}
                  onChange={(e) => setMaxScore(Number(e.target.value))}
                  min={1}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Дата начала</label>
                <Input
                  type="datetime-local"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Срок сдачи</label>
                <Input
                  type="datetime-local"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Назначить студентам (опционально)</label>
              <p className="text-xs text-muted-foreground mb-2">
                Выберите студентов для назначения задания
              </p>
              <div className="max-h-40 overflow-y-auto border rounded-lg p-2 space-y-1">
                {students.map(student => (
                  <label
                    key={student.id}
                    className="flex items-center gap-2 p-2 hover:bg-muted rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedStudents.includes(student.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedStudents([...selectedStudents, student.id]);
                        } else {
                          setSelectedStudents(selectedStudents.filter(id => id !== student.id));
                        }
                      }}
                      className="rounded"
                    />
                    <span className="text-sm">{student.full_name}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setCreateDialogOpen(false);
                resetForm();
              }}
            >
              Отмена
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!title.trim() || !description.trim() || !startDate || !dueDate || createMutation.isPending}
            >
              {createMutation.isPending ? 'Создание...' : 'Создать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Submissions Dialog */}
      <Dialog open={submissionsDialogOpen} onOpenChange={setSubmissionsDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Ответы на задание: {selectedAssignment?.title}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {submissions.length === 0 ? (
              <div className="p-12 text-center">
                <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                <p className="text-muted-foreground">Пока нет ответов на это задание</p>
              </div>
            ) : (
              <div className="space-y-3">
                {submissions.map(submission => (
                  <Card key={submission.id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="font-medium">{submission.student.full_name}</p>
                          <p className="text-sm text-muted-foreground mt-1">
                            Отправлено: {format(new Date(submission.submitted_at), 'dd MMMM yyyy, HH:mm', { locale: ru })}
                          </p>
                          {submission.status === 'graded' && submission.score !== undefined && (
                            <Badge variant="outline" className="mt-2">
                              {submission.score} / {submission.max_score} баллов
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {submission.status === 'submitted' && (
                            <Button
                              size="sm"
                              onClick={() => {
                                setSelectedSubmission(submission);
                                setScore(0);
                                setFeedback('');
                                setGradeDialogOpen(true);
                              }}
                            >
                              Оценить
                            </Button>
                          )}
                          <Badge variant={submission.status === 'graded' ? 'default' : 'secondary'}>
                            {submission.status === 'submitted' && 'Отправлено'}
                            {submission.status === 'graded' && 'Оценено'}
                            {submission.status === 'returned' && 'Возвращено'}
                          </Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Grade Submission Dialog */}
      <Dialog open={gradeDialogOpen} onOpenChange={setGradeDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Оценить ответ: {selectedSubmission?.student.full_name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedSubmission && (
              <>
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm font-medium mb-2">Ответ студента:</p>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {selectedSubmission.content}
                  </p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Балл (из {selectedSubmission.max_score})
                  </label>
                  <Input
                    type="number"
                    value={score}
                    onChange={(e) => setScore(Number(e.target.value))}
                    min={0}
                    max={selectedSubmission.max_score || 100}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Комментарий</label>
                  <Textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Напишите комментарий к ответу..."
                    rows={5}
                  />
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setGradeDialogOpen(false);
                setScore(0);
                setFeedback('');
                setSelectedSubmission(null);
              }}
            >
              Отмена
            </Button>
            <Button
              onClick={handleGrade}
              disabled={gradeMutation.isPending}
            >
              {gradeMutation.isPending ? 'Сохранение...' : 'Сохранить оценку'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SidebarProvider>
  );
};

export default TeacherAssignments;
