import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, MessageCircle, Target, Bell, CheckCircle, Clock, LogOut, ExternalLink, AlertCircle } from "lucide-react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { unifiedAPI } from "@/integrations/api/unifiedClient";
import { useToast } from "@/hooks/use-toast";
import { useErrorNotification, useSuccessNotification } from "@/components/NotificationSystem";
import { DashboardSkeleton, ErrorState, EmptyState, LoadingWithRetry } from "@/components/LoadingStates";
import { useErrorReporter } from "@/components/ErrorHandlingProvider";
import { useNetworkStatus } from "@/components/NetworkStatusHandler";
import { FallbackUI, OfflineContent } from "@/components/FallbackUI";
import { useStudentSubjects } from "@/hooks/useStudent";

// Интерфейсы для данных
interface Material {
  id: number;
  title: string;
  description: string;
  teacher_name: string;
  subject: string;
  status: 'new' | 'in_progress' | 'completed';
  progress_percentage: number;
  created_at: string;
  file_url?: string;
}

interface DashboardData {
  student_info: {
    id: number;
    name: string;
    role: string;
    avatar?: string;
  };
  materials_by_subject: {
    [subjectName: string]: {
      subject_info: {
        id: number;
        name: string;
        color?: string;
        teacher?: {
          id: number;
          full_name: string;
        };
      };
      materials: Array<{
        id: number;
        title: string;
        description?: string;
        created_at: string;
        type?: string;
        status?: string;
        progress_percentage?: number;
      }>;
    };
  };
  progress_statistics: {
    overall_percentage: number;
    completed_tasks: number;
    total_tasks: number;
    streak_days: number;
    accuracy_percentage: number;
  };
  recent_activity: Array<{
    id: number;
    title: string;
    deadline: string;
    status: 'pending' | 'completed' | 'overdue';
  }>;
  general_chat: {
    id: number;
    name: string;
    last_message?: string;
  };
}

const StudentDashboard = () => {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();
  const { reportError, reportNetworkError } = useErrorReporter();
  const networkStatus = useNetworkStatus();
  
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // const { data: subjects, isLoading: subjectsLoading } = useStudentSubjects();
  
  // console.log('StudentDashboard: subjects data:', subjects);
  // console.log('StudentDashboard: subjects loading:', subjectsLoading);

  // Загрузка данных дашборда с улучшенной обработкой ошибок
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await unifiedAPI.getStudentDashboard();
      
        if (response.success && response.data) {
          setDashboardData(response.data);
          setLoading(false);
          showSuccess('Данные успешно загружены');
        } else {
        const errorMessage = response.error || 'Ошибка загрузки данных';
        setError(errorMessage);
        reportError(new Error(errorMessage), {
          operation: 'fetchDashboardData',
          component: 'StudentDashboard',
          response,
        });
      }
    } catch (err: any) {
      const errorMessage = 'Произошла ошибка при загрузке данных';
      setError(errorMessage);
      reportNetworkError(err, {
        operation: 'fetchDashboardData',
        component: 'StudentDashboard',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleSignOut = async () => {
    await signOut();
  };

  const handleMaterialClick = (materialId: number) => {
    navigate(`/dashboard/student/materials/${materialId}`);
  };

  const handleChatClick = () => {
    navigate('/dashboard/chat');
  };

  const handleAssignmentClick = (assignmentId: number) => {
    navigate(`/dashboard/student/assignments/${assignmentId}`);
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <StudentSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
            <Button variant="outline" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground rounded-full text-xs flex items-center justify-center">
                3
              </span>
            </Button>
            <Button variant="outline" onClick={handleSignOut}>
              <LogOut className="w-4 h-4 mr-2" />
              Выйти
            </Button>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold">
                  Привет, {user?.first_name || 'Студент'}! 👋
                </h1>
                <p className="text-muted-foreground">Продолжай двигаться к своей цели</p>
              </div>

              {/* Обработка офлайн режима */}
              {!networkStatus.isOnline && (
                <OfflineContent 
                  cachedData={dashboardData ? {
                    materials: dashboardData.materials,
                    reports: dashboardData.recent_assignments,
                  } : undefined}
                  onRetry={fetchDashboardData}
                />
              )}

              {/* Обработка ошибок и загрузки */}
              <LoadingWithRetry
                isLoading={loading}
                error={error}
                onRetry={fetchDashboardData}
              >
                {dashboardData && (
                <>

                  {/* Progress Section */}
                  <Card className="p-6 gradient-primary text-primary-foreground shadow-glow">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="w-12 h-12 bg-primary-foreground/20 rounded-full flex items-center justify-center">
                        <Target className="w-6 h-6" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-xl font-bold">Твой прогресс</h3>
                        <p className="text-primary-foreground/80">Продолжай двигаться к цели</p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Выполнено заданий: {dashboardData.progress_statistics?.completed_tasks || 0} из {dashboardData.progress_statistics?.total_tasks || 0}</span>
                        <span className="font-bold">{dashboardData.progress_statistics?.overall_percentage || 0}%</span>
                      </div>
                      <Progress value={dashboardData.progress_statistics?.overall_percentage || 0} className="h-3 bg-primary-foreground/20" />
                    </div>
                    <div className="grid grid-cols-3 gap-4 mt-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold">{dashboardData.progress_statistics?.streak_days || 0}</div>
                        <div className="text-sm text-primary-foreground/80">Дней подряд</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{dashboardData.progress_statistics?.completed_tasks || 0}</div>
                        <div className="text-sm text-primary-foreground/80">Заданий</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{dashboardData.progress_statistics?.accuracy_percentage || 0}%</div>
                        <div className="text-sm text-primary-foreground/80">Точность</div>
                      </div>
                    </div>
                  </Card>

                  <div className="grid md:grid-cols-2 gap-6">
                    {/* Current Materials */}
                    <Card className="p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <BookOpen className="w-5 h-5 text-primary" />
                        <h3 className="text-xl font-bold">Текущие материалы</h3>
                      </div>
                      <div className="space-y-3">
                        {Object.values(dashboardData?.materials_by_subject || {}).flatMap(subjectData => subjectData.materials).slice(0, 3).map((material) => (
                          <div 
                            key={material.id} 
                            className="flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer"
                            onClick={() => handleMaterialClick(material.id)}
                          >
                            <div className="flex-1">
                              <div className="font-medium">{material.title}</div>
                              <div className="text-sm text-muted-foreground">
                                {material.description || 'Без описания'}
                              </div>
                              {material.progress_percentage > 0 && (
                                <div className="mt-1">
                                  <Progress value={material.progress_percentage} className="h-2" />
                                  <span className="text-xs text-muted-foreground">
                                    {material.progress_percentage}% завершено
                                  </span>
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              {material.type === 'file' && (
                                <ExternalLink className="w-4 h-4 text-muted-foreground" />
                              )}
                              <Badge variant={
                                material.status === "new" ? "default" : 
                                material.status === "in_progress" ? "secondary" : 
                                "outline"
                              }>
                                {material.status === "new" ? "Новое" : 
                                 material.status === "in_progress" ? "В процессе" : 
                                 "Завершено"}
                              </Badge>
                            </div>
                          </div>
                        ))}
                        {Object.values(dashboardData?.materials_by_subject || {}).flatMap(subjectData => subjectData.materials).length === 0 && (
                          <EmptyState
                            title="Нет доступных материалов"
                            description="Пока нет материалов для изучения. Обратитесь к преподавателю."
                            icon={<BookOpen className="w-8 h-8 text-muted-foreground" />}
                          />
                        )}
                      </div>
                      <Button 
                        variant="outline" 
                        className="w-full mt-4"
                        onClick={() => navigate('/dashboard/student/materials')}
                      >
                        Смотреть все материалы
                      </Button>
                    </Card>

                    {/* Subjects Section */}
                    <Card className="p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <BookOpen className="w-5 h-5 text-primary" />
                        <h3 className="text-xl font-bold">Мои предметы</h3>
                        <Badge variant="secondary" className="ml-auto">{Object.keys(dashboardData?.materials_by_subject || {}).length}</Badge>
                      </div>
                      {loading ? (
                        <div>Загрузка...</div>
                      ) : (
                        <div className="space-y-3">
                          {Object.values(dashboardData?.materials_by_subject || {}).map((subjectData) => (
                              <div key={subjectData.subject_info.id} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                                <div>
                                  <div className="font-medium">{subjectData.subject_info.name}</div>
                                  <div className="text-sm text-muted-foreground">Преподаватель: {subjectData.subject_info.teacher?.full_name || 'Не назначен'}</div>
                                  <div className="text-xs text-muted-foreground">Материалов: {subjectData.materials.length}</div>
                                </div>
                                <Button size="sm" onClick={() => navigate(`/dashboard/student/materials?subject=${subjectData.subject_info.id}`)}>Материалы</Button>
                              </div>
                            ))}
                          {Object.keys(dashboardData?.materials_by_subject || {}).length === 0 && (
                            <EmptyState
                              title="Нет назначенных предметов"
                              description="Обратитесь к тьютору для назначения предметов."
                              icon={<BookOpen className="w-8 h-8 text-muted-foreground" />}
                            />
                          )}
                        </div>
                      )}
                    </Card>
                  </div>

                  {/* Recent Assignments */}
                  <Card className="p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <h3 className="text-xl font-bold">Последние задания</h3>
                    </div>
                    <div className="space-y-3">
                      {(dashboardData?.recent_activity || []).slice(0, 3).map((assignment) => (
                        <div 
                          key={assignment.id} 
                          className="flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer"
                          onClick={() => handleAssignmentClick(assignment.id)}
                        >
                          <div className="flex-1">
                            <div className="font-medium">{assignment.title}</div>
                            <div className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                              <Clock className="w-3 h-3" />
                              {assignment.deadline}
                            </div>
                          </div>
                          <Badge variant={
                            assignment.status === "completed" ? "default" : 
                            assignment.status === "overdue" ? "destructive" : 
                            "outline"
                          }>
                            {assignment.status === "completed" ? "Выполнено" : 
                             assignment.status === "overdue" ? "Просрочено" : 
                             "В процессе"}
                          </Badge>
                        </div>
                      ))}
                      {(dashboardData?.recent_activity || []).length === 0 && (
                        <EmptyState
                          title="Нет активных заданий"
                          description="Пока нет заданий для выполнения. Ожидайте новых заданий от преподавателя."
                          icon={<CheckCircle className="w-8 h-8 text-muted-foreground" />}
                        />
                      )}
                    </div>
                    <Button 
                      variant="outline" 
                      className="w-full mt-4"
                      onClick={() => navigate('/dashboard/student/assignments')}
                    >
                      Все задания
                    </Button>
                  </Card>

                  {/* Quick Actions */}
                  <Card className="p-6">
                    <h3 className="text-xl font-bold mb-4">Быстрые действия</h3>
                    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={handleChatClick}
                      >
                        <MessageCircle className="w-6 h-6" />
                        <span>Общий чат</span>
                      </Button>
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={() => navigate('/dashboard/student/materials')}
                      >
                        <BookOpen className="w-6 h-6" />
                        <span>Материалы</span>
                      </Button>
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={() => navigate('/dashboard/student/progress')}
                      >
                        <Target className="w-6 h-6" />
                        <span>Мой прогресс</span>
                      </Button>
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={() => navigate('/dashboard/student/assignments')}
                      >
                        <CheckCircle className="w-6 h-6" />
                        <span>Задания</span>
                      </Button>
                    </div>
                  </Card>
                </>
                )}
              </LoadingWithRetry>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default StudentDashboard;
