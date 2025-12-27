import React, { useState, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { logger } from '@/utils/logger';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { TeacherSidebar } from '@/components/layout/TeacherSidebar';
import { useAuth } from '@/contexts/AuthContext';
import { Navigate } from 'react-router-dom';
import { useAssignment, useAssignmentSubmissions, useGradeSubmission } from '@/hooks/useAssignments';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { FileText, Clock, AlertCircle, CheckCircle, ArrowLeft, Filter } from 'lucide-react';
import { Assignment, AssignmentSubmission } from '@/integrations/api/assignmentsAPI';
import { format, formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import { GradingForm } from '@/components/assignments/GradingForm';
import { SubmissionAnswerDisplay } from '@/components/assignments/SubmissionAnswerDisplay';
import { GradeHistoryView } from '@/components/assignments/GradeHistoryView';

export const GradingPanel: React.FC = () => {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [selectedSubmissionId, setSelectedSubmissionId] = useState<number | null>(null);
  const [filterStatus, setFilterStatus] = useState<'all' | 'submitted' | 'graded' | 'returned'>('submitted');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'grading' | 'history'>('grading');

  const assignmentId_num = assignmentId ? parseInt(assignmentId, 10) : 0;

  const { data: assignment, isLoading: assignmentLoading, error: assignmentError } = useAssignment(assignmentId_num);
  const { data: submissions = [], isLoading: submissionsLoading, refetch: refetchSubmissions } = useAssignmentSubmissions(assignmentId_num);

  // Redirect if not a teacher
  if (user?.role !== 'teacher') {
    return <Navigate to="/dashboard" replace />;
  }

  // Filter submissions based on status and search
  const filteredSubmissions = useMemo(() => {
    return submissions.filter(submission => {
      const matchesStatus = filterStatus === 'all' || submission.status === filterStatus;
      const matchesSearch = searchQuery === '' ||
        submission.student.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        submission.student.email.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [submissions, filterStatus, searchQuery]);

  // Get current submission
  const selectedSubmission = selectedSubmissionId
    ? submissions.find(s => s.id === selectedSubmissionId)
    : null;

  // Calculate grading statistics
  const stats = useMemo(() => {
    return {
      total: submissions.length,
      submitted: submissions.filter(s => s.status === 'submitted').length,
      graded: submissions.filter(s => s.status === 'graded').length,
      returned: submissions.filter(s => s.status === 'returned').length,
    };
  }, [submissions]);

  const handleSelectSubmission = useCallback((submissionId: number) => {
    setSelectedSubmissionId(submissionId);
    setActiveTab('grading');
  }, []);

  const handleGradingComplete = useCallback(() => {
    refetchSubmissions();
    // Move to next ungraded submission
    const nextUngraded = filteredSubmissions.find(s => s.status === 'submitted' && s.id !== selectedSubmissionId);
    if (nextUngraded) {
      setSelectedSubmissionId(nextUngraded.id);
    } else {
      setSelectedSubmissionId(null);
    }
  }, [filteredSubmissions, selectedSubmissionId, refetchSubmissions]);

  if (!assignmentId_num) {
    return (
      <SidebarProvider>
        <div className="flex min-h-screen w-full bg-background">
          <TeacherSidebar />
          <SidebarInset className="flex-1">
            <header className="sticky top-0 z-10 flex h-16 items-center border-b bg-background px-6">
              <SidebarTrigger />
              <h1 className="ml-4 text-xl font-semibold flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Проверка задания
              </h1>
            </header>
            <main className="p-6">
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>Задание не найдено</AlertDescription>
              </Alert>
            </main>
          </SidebarInset>
        </div>
      </SidebarProvider>
    );
  }

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <TeacherSidebar />
        <SidebarInset className="flex-1">
          {/* Header */}
          <header className="sticky top-0 z-10 flex h-16 items-center border-b bg-background px-6">
            <SidebarTrigger />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/dashboard/teacher/assignments')}
              className="ml-2"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="ml-4 flex-1">
              <h1 className="text-xl font-semibold flex items-center gap-2">
                <FileText className="w-5 h-5" />
                {assignmentLoading ? 'Загрузка...' : assignment?.title || 'Проверка задания'}
              </h1>
            </div>
          </header>

          <main className="flex flex-col lg:flex-row gap-6 p-6 overflow-hidden">
            {/* Left Panel: Submission List */}
            <div className="w-full lg:w-96 min-h-0 flex flex-col gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Ответы на проверку</CardTitle>
                  <CardDescription>
                    {stats.total} ответов
                    {stats.submitted > 0 && ` • ${stats.submitted} на проверке`}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {/* Statistics Badges */}
                  <div className="grid grid-cols-2 gap-2">
                    <Badge variant="outline" className="justify-center py-2">
                      <span className="text-xs font-medium">Всего: {stats.total}</span>
                    </Badge>
                    <Badge variant="secondary" className="justify-center py-2">
                      <span className="text-xs font-medium">На проверке: {stats.submitted}</span>
                    </Badge>
                    <Badge variant="outline" className="justify-center py-2">
                      <span className="text-xs font-medium">Оценено: {stats.graded}</span>
                    </Badge>
                    <Badge variant="outline" className="justify-center py-2">
                      <span className="text-xs font-medium">Возвращено: {stats.returned}</span>
                    </Badge>
                  </div>

                  {/* Search */}
                  <div className="space-y-2">
                    <Input
                      placeholder="Поиск по имени или email..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="h-9"
                    />
                  </div>

                  {/* Filter */}
                  <div className="space-y-2">
                    <Select value={filterStatus} onValueChange={(v: any) => setFilterStatus(v)}>
                      <SelectTrigger className="h-9">
                        <Filter className="w-4 h-4 mr-2" />
                        <SelectValue placeholder="Фильтр по статусу" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Все ответы</SelectItem>
                        <SelectItem value="submitted">На проверке</SelectItem>
                        <SelectItem value="graded">Оценено</SelectItem>
                        <SelectItem value="returned">Возвращено</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              {/* Submissions List */}
              <Card className="flex-1 min-h-0">
                <ScrollArea className="h-full">
                  <div className="p-4 space-y-2">
                    {submissionsLoading ? (
                      <div className="space-y-2">
                        {[...Array(5)].map((_, i) => (
                          <Skeleton key={i} className="h-20 w-full" />
                        ))}
                      </div>
                    ) : filteredSubmissions.length === 0 ? (
                      <div className="text-center py-8">
                        <FileText className="w-8 h-8 mx-auto mb-2 text-muted-foreground opacity-50" />
                        <p className="text-sm text-muted-foreground">Нет ответов для отображения</p>
                      </div>
                    ) : (
                      filteredSubmissions.map(submission => (
                        <SubmissionListItem
                          key={submission.id}
                          submission={submission}
                          isSelected={selectedSubmissionId === submission.id}
                          onSelect={handleSelectSubmission}
                        />
                      ))
                    )}
                  </div>
                </ScrollArea>
              </Card>
            </div>

            {/* Right Panel: Grading Form */}
            <div className="flex-1 min-h-0 flex flex-col">
              {selectedSubmission ? (
                <Tabs value={activeTab} onValueChange={(v: any) => setActiveTab(v)} className="flex-1 flex flex-col">
                  <TabsList>
                    <TabsTrigger value="grading">Оценивание</TabsTrigger>
                    <TabsTrigger value="history">История оценок</TabsTrigger>
                  </TabsList>

                  <TabsContent value="grading" className="flex-1 min-h-0 flex flex-col gap-4">
                    {/* Student Info */}
                    <Card>
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <CardTitle className="text-base">{selectedSubmission.student.full_name}</CardTitle>
                            <CardDescription className="text-xs">
                              {selectedSubmission.student.email}
                            </CardDescription>
                          </div>
                          <Badge variant={getSubmissionStatusVariant(selectedSubmission.status)}>
                            {getSubmissionStatusLabel(selectedSubmission.status)}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-2 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Отправлено:</span>
                          <span>
                            {format(new Date(selectedSubmission.submitted_at), 'dd MMMM yyyy, HH:mm', { locale: ru })}
                          </span>
                        </div>
                        {selectedSubmission.graded_at && (
                          <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">Оценено:</span>
                            <span>
                              {format(new Date(selectedSubmission.graded_at), 'dd MMMM yyyy, HH:mm', { locale: ru })}
                            </span>
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    {/* Student Answers */}
                    <SubmissionAnswerDisplay submission={selectedSubmission} />

                    {/* Grading Form */}
                    <GradingForm
                      submission={selectedSubmission}
                      assignment={assignment}
                      onGradingComplete={handleGradingComplete}
                    />
                  </TabsContent>

                  <TabsContent value="history" className="flex-1 min-h-0">
                    <GradeHistoryView submission={selectedSubmission} />
                  </TabsContent>
                </Tabs>
              ) : (
                <Card className="flex items-center justify-center min-h-96">
                  <CardContent className="text-center">
                    <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                    <h3 className="text-lg font-semibold mb-2">Выберите ответ для оценивания</h3>
                    <p className="text-muted-foreground text-sm">
                      Выберите ответ студента из списка слева, чтобы начать оценивание
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

// Submission List Item Component
interface SubmissionListItemProps {
  submission: AssignmentSubmission;
  isSelected: boolean;
  onSelect: (id: number) => void;
}

const SubmissionListItem: React.FC<SubmissionListItemProps> = ({
  submission,
  isSelected,
  onSelect,
}) => {
  return (
    <button
      onClick={() => onSelect(submission.id)}
      className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
        isSelected
          ? 'border-primary bg-primary/5'
          : 'border-transparent hover:bg-muted/50'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="font-medium text-sm line-clamp-1">
          {submission.student.full_name}
        </div>
        <Badge
          variant={getSubmissionStatusVariant(submission.status)}
          className="text-xs"
        >
          {getSubmissionStatusLabel(submission.status)}
        </Badge>
      </div>
      <div className="text-xs text-muted-foreground mb-2">
        {submission.student.email}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {formatDistanceToNow(new Date(submission.submitted_at), {
            locale: ru,
            addSuffix: true,
          })}
        </span>
        {submission.score !== undefined && submission.max_score && (
          <Badge variant="outline" className="text-xs font-mono">
            {submission.score} / {submission.max_score}
          </Badge>
        )}
      </div>
    </button>
  );
};

// Helper functions
function getSubmissionStatusVariant(
  status: string
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'submitted':
      return 'secondary';
    case 'graded':
      return 'default';
    case 'returned':
      return 'outline';
    default:
      return 'outline';
  }
}

function getSubmissionStatusLabel(status: string): string {
  switch (status) {
    case 'submitted':
      return 'На проверке';
    case 'graded':
      return 'Оценено';
    case 'returned':
      return 'Возвращено';
    default:
      return status;
  }
}

export default GradingPanel;
