import { Card } from "@/components/ui/card";
import { logger } from '@/utils/logger';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, CheckCircle, FileText, MessageCircle, Plus, Clock, AlertCircle, ExternalLink, Users, TrendingUp } from "lucide-react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { ProfileCard } from "@/components/ProfileCard";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { useTeacherDashboard, usePendingSubmissions } from "@/hooks/useTeacher";
import { PendingSubmission } from "@/integrations/api/teacher";
import { TeacherScheduleWidget } from "@/components/dashboard/TeacherScheduleWidget";
import { useEffect } from "react";

// Интерфейсы для данных
interface Material {
  id: number;
  title: string;
  description: string;
  subject: { id: number; name: string; color: string };
  status: 'active' | 'draft';
  assigned_count: number;
  created_at: string;
  file_url?: string;
}

interface Student {
  id: number;
  name: string;
  profile?: { grade: string; progress_percentage: number };
  subjects?: Array<{
    id: number;
    name: string;
    color: string;
    enrollment_id: number;
    enrolled_at: string;
  }>;
}

type Assignment = never;

interface Report {
  id: number;
  title: string;
  student_name: string;
  subject: string;
  created_at: string;
  status: 'draft' | 'sent';
}

interface DashboardData {
  materials: Material[];
  students: Student[];
  reports: Report[];
  progress_overview: {
    total_students: number;
    total_materials: number;
    total_assignments: number;
    completed_assignments: number;
  };
}

const TeacherDashboard = () => {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  // Используем TanStack Query для кеширования данных
  const {
    data: dashboardData,
    isLoading: dashboardLoading,
    error: dashboardError,
    refetch: refetchDashboard,
  } = useTeacherDashboard();

  const {
    data: pendingSubmissions = [],
    isLoading: submissionsLoading,
  } = usePendingSubmissions();

  const loading = dashboardLoading || submissionsLoading;
  const error = dashboardError?.message || null;

  // Debug logging for "CANNOT ENTER" issue
  useEffect(() => {
    if (dashboardError) {
      logger.error('[TeacherDashboard] Dashboard fetch error:', dashboardError);
      logger.error('[TeacherDashboard] Error message:', dashboardError.message);
      logger.error('[TeacherDashboard] Full error:', JSON.stringify(dashboardError, null, 2));
    }
    if (dashboardData) {
      logger.debug('[TeacherDashboard] Dashboard data loaded:', dashboardData);
      logger.debug('[TeacherDashboard] Profile data:', dashboardData.profile);
      logger.debug('[TeacherDashboard] Teacher info:', dashboardData.teacher_info);
    }
  }, [dashboardError, dashboardData]);

  const handleMaterialClick = (materialId: number) => {
    // Детальной страницы пока нет — ведём на список материалов
    navigate('/dashboard/teacher/materials');
  };

  const handleStudentClick = (studentId: number) => {
    // Страницы студентов пока нет — ведём на материалы
    navigate('/dashboard/teacher/materials');
  };

  const handleAssignmentClick = (assignmentId: number) => {
    // Страницы заданий пока нет — ведём на ожидающие проверки
    navigate('/dashboard/teacher/submissions/pending');
  };

  const handleReportClick = (reportId: number) => {
    // Детальной страницы отчёта пока нет — ведём на список отчётов
    navigate('/dashboard/teacher/reports');
  };

  const handleCreateMaterial = () => {
    navigate('/dashboard/teacher/materials/create');
  };

  const handleCreateReport = () => {
    navigate('/dashboard/teacher/reports');
  };

  const handleChatClick = () => {
    // Для преподавателя используем маршрут форума
    navigate('/dashboard/teacher/forum');
  };

  const handleEditProfile = () => {
    navigate('/profile/teacher');
  };


  /**
   * Подготавливаем данные профиля для ProfileCard
   * На основе данных из dashboardData (единственный источник)
   * With defensive programming to prevent crashes if data format is unexpected
   */
  const getProfileData = () => {
    try {
      const subjects = dashboardData?.profile?.subjects;
      let subjectsArray: string[] = [];

      if (subjects) {
        if (Array.isArray(subjects)) {
          subjectsArray = subjects.map((s: any) => {
            if (typeof s === 'string') return s;
            if (s && typeof s === 'object' && s.name) return s.name;
            return String(s);
          });
        } else if (typeof subjects === 'string') {
          subjectsArray = [subjects];
        }
      }

      return {
        subjects: subjectsArray,
        experience: Number(dashboardData?.profile?.experience) || 0,
        studentsCount: Number(dashboardData?.progress_overview?.total_students) || 0,
        materialsCount: Number(dashboardData?.progress_overview?.total_materials) || 0,
      };
    } catch (err) {
      logger.error('[TeacherDashboard] Error extracting profile data:', err);
      return {
        subjects: [],
        experience: 0,
        studentsCount: 0,
        materialsCount: 0,
      };
    }
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
            <div className="flex items-center gap-2">
              <Button type="button"
                className="gradient-primary shadow-glow"
                onClick={handleCreateMaterial}
              >
                <Plus className="w-4 h-4 mr-2" />
                Создать материал
              </Button>
            </div>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold">Личный кабинет преподавателя</h1>
                <p className="text-muted-foreground">
                  {user?.first_name || 'Преподаватель'} | {dashboardData?.progress_overview?.total_students ?? 0} учеников
                </p>
              </div>

              {/* Обработка ошибок */}
              {error && (
                <Card className="p-6 border-destructive bg-destructive/10">
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-destructive">
                      <AlertCircle className="w-5 h-5" />
                      <div className="flex-1">
                        <div className="font-medium">Не удалось загрузить данные дашборда</div>
                        <div className="text-sm mt-1">{error}</div>
                      </div>
                    </div>
                    <Button type="button" onClick={() => refetchDashboard()} variant="outline" size="sm">
                      Повторить попытку
                    </Button>
                  </div>
                </Card>
              )}

              {/* Профиль преподавателя */}
              {!loading && !error && dashboardData && (
                <ProfileCard
                  userName={dashboardData.teacher_info?.name || user?.first_name || 'Преподаватель'}
                  userEmail={user?.email || 'email@example.com'}
                  userRole="teacher"
                  avatarUrl={dashboardData.teacher_info?.avatar || dashboardData.profile?.avatar_url}
                  profileData={getProfileData()}
                  onEdit={handleEditProfile}
                />
              )}

              {/* Скелетон для профиля */}
              {loading && (
                <Card className="p-6">
                  <div className="flex gap-4 items-start">
                    <Skeleton className="w-24 h-24 rounded-full" />
                    <div className="flex-1 space-y-3">
                      <Skeleton className="h-6 w-48" />
                      <Skeleton className="h-4 w-64" />
                      <Skeleton className="h-4 w-40" />
                    </div>
                  </div>
                </Card>
              )}

              {/* Загрузка */}
              {loading && (
                <div className="space-y-6">
                  <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map((i) => (
                      <Card key={i} className="p-4">
                        <Skeleton className="h-12 w-12 mb-3" />
                        <Skeleton className="h-6 w-16 mb-2" />
                        <Skeleton className="h-4 w-20" />
                      </Card>
                    ))}
                  </div>
                  <div className="grid md:grid-cols-2 gap-6">
                    <Card className="p-6">
                      <Skeleton className="h-6 w-32 mb-4" />
                      <div className="space-y-3">
                        {[1, 2, 3].map((i) => (
                          <Skeleton key={i} className="h-16 w-full" />
                        ))}
                      </div>
                    </Card>
                    <Card className="p-6">
                      <Skeleton className="h-6 w-32 mb-4" />
                      <div className="space-y-3">
                        {[1, 2, 3].map((i) => (
                          <Skeleton key={i} className="h-16 w-full" />
                        ))}
                      </div>
                    </Card>
                  </div>
                </div>
              )}

              {/* Основной контент */}
              {!loading && !error && dashboardData && (
                <>

                  {/* Stats Overview */}
                  <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card className="p-4 hover:border-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard/teacher/materials')}>
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center">
                          <BookOpen className="w-6 h-6 text-primary-foreground" />
                        </div>
                        <div>
                          <div className="text-2xl font-bold">{dashboardData.progress_overview?.total_materials ?? 0}</div>
                          <div className="text-sm text-muted-foreground">Материалов</div>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4 hover:border-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard/teacher/submissions/pending')}>
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 gradient-secondary rounded-lg flex items-center justify-center">
                          <CheckCircle className="w-6 h-6 text-secondary-foreground" />
                        </div>
                        <div>
                          <div className="text-2xl font-bold">{Math.max(((dashboardData.progress_overview?.total_assignments ?? 0) - (dashboardData.progress_overview?.completed_assignments ?? 0)), 0)}</div>
                          <div className="text-sm text-muted-foreground">На проверке</div>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4 hover:border-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard/teacher/materials')}>
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-accent/20 rounded-lg flex items-center justify-center">
                          <Users className="w-6 h-6 text-accent" />
                        </div>
                        <div>
                          <div className="text-2xl font-bold">{dashboardData.progress_overview?.total_students ?? 0}</div>
                          <div className="text-sm text-muted-foreground">Учеников</div>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4 hover:border-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard/teacher/reports')}>
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-success/20 rounded-lg flex items-center justify-center">
                          <FileText className="w-6 h-6 text-success" />
                        </div>
                        <div>
                          <div className="text-2xl font-bold">{(dashboardData.reports ?? []).length}</div>
                          <div className="text-sm text-muted-foreground">Отправлено отчетов</div>
                        </div>
                      </div>
                    </Card>
                  </div>

                  {/* Schedule Widget */}
                  <TeacherScheduleWidget />

                  <div className="grid md:grid-cols-2 gap-6">
                    {/* Assignments to Check */}
                    <Card className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <CheckCircle className="w-5 h-5 text-primary" />
                          <h3 className="text-xl font-bold">Задания на проверку</h3>
                        </div>
                        <Badge variant="destructive">{pendingSubmissions.length}</Badge>
                      </div>
                      <div className="space-y-3">
                        {pendingSubmissions.slice(0, 3).map((assignment: PendingSubmission) => (
                          <div 
                            key={assignment.id} 
                            className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer"
                            onClick={() => handleAssignmentClick(assignment.id)}
                          >
                            <div className="flex items-start gap-3">
                              <Avatar className="w-10 h-10">
                                <AvatarFallback className="gradient-primary text-primary-foreground">
                                  {assignment.student_name.split(' ').map(n => n[0]).join('')}
                                </AvatarFallback>
                              </Avatar>
                              <div className="flex-1">
                                <div className="flex items-center justify-between mb-1">
                                  <div className="font-medium">{assignment.student_name}</div>
                                  <Badge variant="outline" className="text-xs">
                                    {assignment.student_grade || ''}
                                  </Badge>
                                </div>
                                <div className="text-sm text-muted-foreground mb-2">{assignment.material_title}</div>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                  <Clock className="w-3 h-3" />
                                  Сдано {new Date(assignment.submitted_at).toLocaleDateString('ru-RU')}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                        {pendingSubmissions.length === 0 && (
                          <div className="text-center py-8 text-muted-foreground">
                            <CheckCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                            <p>Нет заданий на проверку</p>
                          </div>
                        )}
                      </div>
                      <Button type="button" 
                        variant="outline" 
                        className="w-full mt-4"
                        onClick={() => navigate('/dashboard/teacher/submissions/pending')}
                      >
                        Все задания
                      </Button>
                    </Card>

                    {/* Published Materials */}
                    <Card className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <BookOpen className="w-5 h-5 text-primary" />
                          <h3 className="text-xl font-bold">Опубликованные материалы</h3>
                        </div>
                        <Button type="button" size="sm" variant="outline" onClick={handleCreateMaterial}>
                          <Plus className="w-4 h-4 mr-1" />
                          Добавить
                        </Button>
                      </div>
                      <div className="space-y-3">
                        {(dashboardData.materials ?? []).slice(0, 3).map((material) => (
                          <div 
                            key={material.id} 
                            className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer"
                            onClick={() => handleMaterialClick(material.id)}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="font-medium">{material.title}</div>
                              <div className="flex items-center gap-2">
                                {material.file_url && (
                                  <ExternalLink className="w-4 h-4 text-muted-foreground" />
                                )}
                                <Badge variant={material.status === "active" ? "default" : "secondary"}>
                                  {material.status === "active" ? "Активно" : "Черновик"}
                                </Badge>
                              </div>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                              <span>{material.assigned_count} учеников</span>
                              <span>•</span>
                              <span>{material.subject?.name}</span>
                              <span>•</span>
                              <span>{new Date(material.created_at).toLocaleDateString('ru-RU')}</span>
                            </div>
                          </div>
                        ))}
                        {(dashboardData.materials ?? []).length === 0 && (
                          <div className="text-center py-8 text-muted-foreground">
                            <BookOpen className="w-12 h-12 mx-auto mb-4 opacity-50" />
                            <p>Нет опубликованных материалов</p>
                          </div>
                        )}
                      </div>
                      <Button type="button" 
                        variant="outline" 
                        className="w-full mt-4"
                        onClick={() => navigate('/dashboard/teacher/materials')}
                      >
                        Все материалы
                      </Button>
                    </Card>
                  </div>

                  {/* Students Overview */}
                  <Card className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <Users className="w-5 h-5 text-primary" />
                        <h3 className="text-xl font-bold">Ученики</h3>
                      </div>
                      <Badge variant="outline">{(dashboardData.students ?? []).length} всего</Badge>
                    </div>
                    <div className="grid md:grid-cols-2 gap-4">
                      {(dashboardData.students ?? []).slice(0, 4).map((student) => (
                        <div 
                          key={student.id} 
                          className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer"
                          onClick={() => handleStudentClick(student.id)}
                        >
                          <div className="flex items-start gap-3">
                            <Avatar className="w-10 h-10">
                              <AvatarFallback className="gradient-secondary text-secondary-foreground">
                                {student.name.split(' ').map(n => n[0]).join('')}
                              </AvatarFallback>
                            </Avatar>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-1">
                                <div className="font-medium">{student.name}</div>
                                <Badge variant="outline" className="text-xs">
                                  {student.profile?.grade} класс
                                </Badge>
                              </div>
                              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                                <TrendingUp className="w-3 h-3" />
                                Прогресс: {student.profile?.progress_percentage}%
                              </div>
                              {student.subjects && student.subjects.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                  {student.subjects.map((subject) => (
                                    <Badge
                                      key={subject.id}
                                      variant="outline"
                                      className="text-xs"
                                      style={{ borderColor: subject.color }}
                                    >
                                      <div
                                        className="w-2 h-2 rounded-full mr-1"
                                        style={{ backgroundColor: subject.color }}
                                      />
                                      {subject.name}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                      <Button type="button" 
                        variant="outline" 
                        className="w-full mt-4"
                        onClick={() => navigate('/dashboard/teacher/materials')}
                      >
                      Все ученики
                    </Button>
                  </Card>

                  {/* Reports Management */}
                  <Card className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-primary" />
                        <h3 className="text-xl font-bold">Отчёты</h3>
                      </div>
                      <Button type="button" size="sm" variant="outline" onClick={handleCreateReport}>
                        <Plus className="w-4 h-4 mr-1" />
                        Создать
                      </Button>
                    </div>
                    <div className="space-y-3">
                      {(dashboardData.reports ?? []).slice(0, 3).map((report) => (
                        <div 
                          key={report.id} 
                          className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer"
                          onClick={() => handleReportClick(report.id)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="font-medium mb-1">{report.title}</div>
                              <div className="text-sm text-muted-foreground">
                                {report.student_name} • {report.subject}
                              </div>
                              <div className="text-xs text-muted-foreground mt-1">
                                {new Date(report.created_at).toLocaleDateString('ru-RU')}
                              </div>
                            </div>
                            <Badge variant={report.status === "sent" ? "default" : "secondary"}>
                              {report.status === "sent" ? "Отправлено" : "Черновик"}
                            </Badge>
                          </div>
                        </div>
                      ))}
                      {(dashboardData.reports ?? []).length === 0 && (
                        <div className="text-center py-8 text-muted-foreground">
                          <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                          <p>Нет созданных отчетов</p>
                        </div>
                      )}
                    </div>
                    <Button type="button" 
                      variant="outline" 
                      className="w-full mt-4"
                      onClick={() => navigate('/dashboard/teacher/reports')}
                    >
                      Все отчёты
                    </Button>
                  </Card>

                  {/* Quick Actions */}
                  <Card className="p-6">
                    <h3 className="text-xl font-bold mb-4">Быстрые действия</h3>
                    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      <Button type="button" 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={handleCreateMaterial}
                      >
                        <BookOpen className="w-6 h-6" />
                        <span>Создать материал</span>
                      </Button>
                      <Button type="button" 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={handleCreateReport}
                      >
                        <FileText className="w-6 h-6" />
                        <span>Создать отчёт</span>
                      </Button>
                      <Button type="button"
                        variant="outline"
                        className="h-auto flex-col gap-2 py-6"
                        onClick={handleChatClick}
                      >
                        <MessageCircle className="w-6 h-6" />
                        <span>Форум</span>
                      </Button>
                      <Button type="button" 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={() => navigate('/dashboard/teacher/assign-subject')}
                      >
                        <Users className="w-6 h-6" />
                        <span>Назначить предмет</span>
                      </Button>
                    </div>
                  </Card>
                </>
              )}
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default TeacherDashboard;
