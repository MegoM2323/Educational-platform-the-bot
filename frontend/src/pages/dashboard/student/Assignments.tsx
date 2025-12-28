import React, { useState, useMemo } from 'react';
import { logger } from '@/utils/logger';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { Navigate } from "react-router-dom";
import { useAssignments, useSubmitAssignment } from "@/hooks/useAssignments";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { FileText, Clock, AlertCircle, CheckCircle, Upload } from "lucide-react";
import { Assignment } from "@/integrations/api/assignmentsAPI";
import { format } from "date-fns";
import { ru } from "date-fns/locale";

const StudentAssignments: React.FC = () => {
  const { user } = useAuth();
  const { data: assignments = [], isLoading, error } = useAssignments();
  const [activeTab, setActiveTab] = useState<'active' | 'completed'>('active');
  const [selectedAssignment, setSelectedAssignment] = useState<Assignment | null>(null);
  const [submitDialogOpen, setSubmitDialogOpen] = useState(false);
  const [content, setContent] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const submitMutation = useSubmitAssignment(selectedAssignment?.id || 0);

  if (user?.role !== 'student') {
    return <Navigate to="/dashboard" replace />;
  }

  const now = new Date();

  const activeAssignments = useMemo(() => {
    return assignments.filter(a =>
      a.status === 'published' &&
      new Date(a.due_date) > now
    ).sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime());
  }, [assignments, now]);

  const completedAssignments = useMemo(() => {
    return assignments.filter(a =>
      a.status === 'closed' || new Date(a.due_date) <= now
    ).sort((a, b) => new Date(b.due_date).getTime() - new Date(a.due_date).getTime());
  }, [assignments, now]);

  const handleSubmit = async () => {
    if (!selectedAssignment || !content.trim()) return;

    try {
      await submitMutation.mutateAsync({ content, file: file || undefined });
      setSubmitDialogOpen(false);
      setContent('');
      setFile(null);
      setSelectedAssignment(null);
    } catch (error) {
      logger.error('Failed to submit assignment:', error);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const getStatusBadge = (assignment: Assignment) => {
    const dueDate = new Date(assignment.due_date);
    if (assignment.status === 'closed') {
      return <Badge variant="secondary">Закрыто</Badge>;
    }
    if (dueDate < now) {
      return <Badge variant="destructive">Просрочено</Badge>;
    }
    const hoursLeft = (dueDate.getTime() - now.getTime()) / (1000 * 60 * 60);
    if (hoursLeft < 24) {
      return <Badge variant="destructive">Срочно</Badge>;
    }
    if (hoursLeft < 72) {
      return <Badge variant="default">Скоро</Badge>;
    }
    return <Badge variant="outline">Активно</Badge>;
  };

  const renderAssignmentCard = (assignment: Assignment) => (
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
          {getStatusBadge(assignment)}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            <span>
              Срок: {format(new Date(assignment.due_date), 'dd MMMM yyyy, HH:mm', { locale: ru })}
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

        {assignment.status === 'published' && new Date(assignment.due_date) > now && (
          <Button type="button"
            onClick={() => {
              setSelectedAssignment(assignment);
              setSubmitDialogOpen(true);
            }}
            className="w-full"
          >
            Отправить ответ
          </Button>
        )}
      </CardContent>
    </Card>
  );

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <StudentSidebar />
        <SidebarInset className="flex-1">
          <header className="sticky top-0 z-10 flex h-16 items-center border-b bg-background px-6">
            <SidebarTrigger />
            <h1 className="ml-4 text-xl font-semibold flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Мои задания
            </h1>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'active' | 'completed')}>
                <TabsList className="grid w-full sm:w-auto grid-cols-2">
                  <TabsTrigger value="active">
                    Активные ({activeAssignments.length})
                  </TabsTrigger>
                  <TabsTrigger value="completed">
                    Завершенные ({completedAssignments.length})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="active" className="space-y-4 mt-6">
                  {isLoading ? (
                    <div className="space-y-4">
                      {[...Array(3)].map((_, i) => (
                        <Card key={`assignment-skeleton-${i}`}>
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
                  ) : activeAssignments.length === 0 ? (
                    <Card>
                      <CardContent className="p-12 text-center">
                        <CheckCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                        <h3 className="text-lg font-semibold mb-2">Нет активных заданий</h3>
                        <p className="text-muted-foreground">
                          У вас пока нет активных заданий. Они появятся здесь, когда преподаватель назначит их вам.
                        </p>
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="grid gap-4">
                      {activeAssignments.map(renderAssignmentCard)}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="completed" className="space-y-4 mt-6">
                  {isLoading ? (
                    <div className="space-y-4">
                      {[...Array(3)].map((_, i) => (
                        <Card key={`assignment-skeleton-${i}`}>
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
                  ) : completedAssignments.length === 0 ? (
                    <Card>
                      <CardContent className="p-12 text-center">
                        <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                        <h3 className="text-lg font-semibold mb-2">Нет завершенных заданий</h3>
                        <p className="text-muted-foreground">
                          Здесь будут отображаться завершенные задания
                        </p>
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="grid gap-4">
                      {completedAssignments.map(renderAssignmentCard)}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          </main>
        </SidebarInset>
      </div>

      {/* Submit Dialog */}
      <Dialog open={submitDialogOpen} onOpenChange={setSubmitDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Отправить ответ: {selectedAssignment?.title}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedAssignment && (
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm font-medium mb-2">Инструкции:</p>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {selectedAssignment.instructions}
                </p>
              </div>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium">Ваш ответ</label>
              <Textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Введите ваш ответ..."
                rows={8}
                className="resize-none"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Файл (опционально)</label>
              <div className="flex items-center gap-2">
                <Input
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png"
                />
                {file && (
                  <Badge variant="outline" className="flex items-center gap-1">
                    <Upload className="w-3 h-3" />
                    {file.name}
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="button"
              variant="outline"
              onClick={() => {
                setSubmitDialogOpen(false);
                setContent('');
                setFile(null);
              }}
            >
              Отмена
            </Button>
            <Button type="button"
              onClick={handleSubmit}
              disabled={!content.trim() || submitMutation.isPending}
            >
              {submitMutation.isPending ? 'Отправка...' : 'Отправить'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SidebarProvider>
  );
};

export default StudentAssignments;
