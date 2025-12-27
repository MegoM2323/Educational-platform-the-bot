import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useAssignment, useSubmitAssignment, useAssignmentSubmissions } from '@/hooks/useAssignments';
import { AssignmentSubmitForm } from '@/components/assignments/AssignmentSubmitForm';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { StudentSidebar } from '@/components/layout/StudentSidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, Clock, FileText, ArrowLeft, CheckCircle } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { logger } from '@/utils/logger';

interface AssignmentQuestion {
  id: number;
  question_text: string;
  question_type: 'single_choice' | 'multiple_choice' | 'text' | 'number';
  points: number;
  options?: string[];
}

interface SubmissionAttempt {
  id: number;
  submitted_at: string;
  status: 'submitted' | 'graded' | 'returned';
  score?: number;
  max_score?: number;
}

export const AssignmentSubmit: React.FC = () => {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [questions, setQuestions] = useState<AssignmentQuestion[]>([]);
  const [questionsLoading, setQuestionsLoading] = useState(true);
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null);
  const [showTimeWarning, setShowTimeWarning] = useState(false);

  const assignmentId_num = assignmentId ? parseInt(assignmentId, 10) : 0;

  const { data: assignment, isLoading: assignmentLoading, error: assignmentError } = useAssignment(assignmentId_num);
  const { data: submissions = [] } = useAssignmentSubmissions(assignmentId_num);
  const submitMutation = useSubmitAssignment(assignmentId_num);

  // Redirect if not a student
  useEffect(() => {
    if (user && user.role !== 'student') {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  // Load questions (mock - in real implementation would come from API)
  useEffect(() => {
    setQuestionsLoading(true);
    // Mock questions loading
    const mockQuestions: AssignmentQuestion[] = [
      {
        id: 1,
        question_text: 'Вопрос 1 - Один правильный ответ',
        question_type: 'single_choice',
        points: 10,
        options: ['Вариант A', 'Вариант B', 'Вариант C', 'Вариант D'],
      },
      {
        id: 2,
        question_text: 'Вопрос 2 - Несколько правильных ответов',
        question_type: 'multiple_choice',
        points: 15,
        options: ['Вариант A', 'Вариант B', 'Вариант C', 'Вариант D'],
      },
      {
        id: 3,
        question_text: 'Вопрос 3 - Ответ текстом',
        question_type: 'text',
        points: 20,
      },
      {
        id: 4,
        question_text: 'Вопрос 4 - Числовой ответ',
        question_type: 'number',
        points: 15,
      },
    ];
    setQuestions(mockQuestions);
    setQuestionsLoading(false);
  }, [assignmentId_num]);

  // Calculate time remaining
  useEffect(() => {
    if (!assignment) return;

    const updateTime = () => {
      const now = new Date();
      const dueDate = new Date(assignment.due_date);
      const diff = dueDate.getTime() - now.getTime();

      if (diff <= 0) {
        setTimeRemaining(0);
      } else {
        setTimeRemaining(Math.ceil(diff / 1000 / 60)); // in minutes
        // Show warning if less than 1 hour
        if (diff < 60 * 60 * 1000) {
          setShowTimeWarning(true);
        }
      }
    };

    updateTime();
    const interval = setInterval(updateTime, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [assignment]);

  const handleSubmitForm = async (data: any, files: File[]) => {
    try {
      await submitMutation.mutateAsync({
        content: data.notes,
        file: files[0], // For now, just first file
      });

      // Show success and redirect
      setTimeout(() => {
        navigate(`/assignment/${assignmentId}/submission-success`, { replace: true });
      }, 2000);
    } catch (error) {
      logger.error('Error submitting assignment:', error);
    }
  };

  if (!user || user.role !== 'student') {
    return null;
  }

  const isOverdue = assignment && new Date(assignment.due_date) < new Date();
  const canSubmit = assignment && assignment.status === 'published' && !isOverdue;
  const hasSubmitted = submissions && submissions.length > 0;
  const remainingAttempts = assignment ? assignment.attempts_limit - (submissions?.length || 0) : 0;

  return (
    <SidebarProvider>
      <StudentSidebar />
      <SidebarInset>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="border-b bg-white sticky top-0 z-10">
            <div className="flex items-center justify-between p-4">
              <div className="flex items-center gap-4">
                <SidebarTrigger />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate('/dashboard/assignments')}
                  className="gap-2"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Назад к заданиям
                </Button>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 overflow-auto p-4 md:p-6">
            <div className="max-w-4xl mx-auto space-y-6">
              {/* Loading State */}
              {assignmentLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-12 w-3/4" />
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-40 w-full" />
                </div>
              ) : assignmentError ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Ошибка при загрузке задания. Пожалуйста, попробуйте позже.
                  </AlertDescription>
                </Alert>
              ) : assignment ? (
                <>
                  {/* Assignment Header */}
                  <div className="space-y-3">
                    <div>
                      <h1 className="text-3xl font-bold">{assignment.title}</h1>
                      <p className="text-muted-foreground mt-2">{assignment.description}</p>
                    </div>

                    {/* Status Badges */}
                    <div className="flex flex-wrap gap-2">
                      {isOverdue && (
                        <Badge variant="destructive">Просрочено</Badge>
                      )}
                      {!canSubmit && assignment.status !== 'published' && (
                        <Badge variant="secondary">Задание недоступно</Badge>
                      )}
                      {hasSubmitted && (
                        <Badge variant="outline" className="bg-green-50">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Отправлено
                        </Badge>
                      )}
                      <Badge variant="outline">
                        Баллы: {assignment.max_score}
                      </Badge>
                    </div>
                  </div>

                  {/* Instructions Card */}
                  {assignment.instructions && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Инструкции</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="prose prose-sm max-w-none dark:prose-invert">
                          {assignment.instructions}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Due Date and Time Info */}
                  <div className="grid md:grid-cols-2 gap-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          Дата и время
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <div>
                          <p className="text-xs text-muted-foreground">Срок сдачи</p>
                          <p className="font-medium">
                            {format(new Date(assignment.due_date), 'PPpp', { locale: ru })}
                          </p>
                        </div>
                        {timeRemaining !== null && (
                          <div>
                            <p className="text-xs text-muted-foreground">Осталось времени</p>
                            <p className={`font-medium ${timeRemaining < 60 ? 'text-destructive' : ''}`}>
                              {timeRemaining <= 0
                                ? 'Время истекло'
                                : timeRemaining < 60
                                  ? `${timeRemaining} минут`
                                  : `${Math.floor(timeRemaining / 60)} часов ${timeRemaining % 60} минут`}
                            </p>
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          Попытки
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <div>
                          <p className="text-xs text-muted-foreground">Максимум попыток</p>
                          <p className="font-medium">{assignment.attempts_limit}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Осталось попыток</p>
                          <p className={`font-medium ${remainingAttempts === 0 ? 'text-destructive' : ''}`}>
                            {remainingAttempts}
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Warnings */}
                  {isOverdue && !canSubmit && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        Срок сдачи этого задания истек. Вы больше не можете отправлять ответы.
                      </AlertDescription>
                    </Alert>
                  )}

                  {showTimeWarning && timeRemaining && timeRemaining < 60 && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        До срока сдачи осталось менее часа! Поспешите отправить ваши ответы.
                      </AlertDescription>
                    </Alert>
                  )}

                  {remainingAttempts === 0 && hasSubmitted && (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        Вы использовали все доступные попытки.
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Submission History */}
                  {hasSubmitted && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">История отправок</CardTitle>
                        <CardDescription>
                          Всего отправлено: {submissions.length}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {submissions.map((submission: SubmissionAttempt, index: number) => (
                            <div
                              key={submission.id}
                              className="p-3 border rounded-lg flex justify-between items-center"
                            >
                              <div className="space-y-1">
                                <p className="font-medium">Попытка {index + 1}</p>
                                <p className="text-sm text-muted-foreground">
                                  {formatDistanceToNow(new Date(submission.submitted_at), {
                                    addSuffix: true,
                                    locale: ru,
                                  })}
                                </p>
                              </div>
                              <div className="text-right space-y-1">
                                <Badge variant="outline">{submission.status}</Badge>
                                {submission.score !== undefined && (
                                  <p className="text-sm font-medium">
                                    {submission.score}/{submission.max_score} баллов
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Submission Form */}
                  {canSubmit && remainingAttempts > 0 && (
                    <AssignmentSubmitForm
                      assignment={assignment}
                      questionCount={questions.length}
                      onSubmit={handleSubmitForm}
                      isLoading={submitMutation.isPending}
                      showConfirmation={true}
                    />
                  )}

                  {/* No Remaining Attempts */}
                  {remainingAttempts === 0 && (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        Вы использовали все доступные попытки. Форма отправки закрыта.
                      </AlertDescription>
                    </Alert>
                  )}
                </>
              ) : null}
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
};
