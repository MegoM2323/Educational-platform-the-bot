import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, CheckCircle, FileText, MessageCircle, Bell, Plus, Clock, AlertCircle, ExternalLink, Users, TrendingUp } from "lucide-react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { unifiedAPI } from "@/integrations/api/unifiedClient";
import { teacherAPI } from "@/integrations/api/teacher";
import { useToast } from "@/hooks/use-toast";

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
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingSubmissions, setPendingSubmissions] = useState<any[]>([]);

  // Загрузка данных дашборда
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await unifiedAPI.getTeacherDashboard();
        
        if (response.data) {
          setDashboardData(response.data);
        } else {
          setError(response.error || 'Ошибка загрузки данных');
        }
        try {
          const pend = await teacherAPI.getPendingSubmissions();
          setPendingSubmissions(pend);
        } catch (e) {
          console.warn('Не удалось загрузить pending submissions', e);
        }
      } catch (err) {
        setError('Произошла ошибка при загрузке данных');
        console.error('Dashboard fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const handleMaterialClick = (materialId: number) => {
    navigate(`/dashboard/teacher/materials/${materialId}`);
  };

  const handleStudentClick = (studentId: number) => {
    navigate(`/dashboard/teacher/students/${studentId}`);
  };

  const handleAssignmentClick = (assignmentId: number) => {
    navigate(`/dashboard/teacher/assignments/${assignmentId}`);
  };

  const handleReportClick = (reportId: number) => {
    navigate(`/dashboard/teacher/reports/${reportId}`);
  };

  const handleCreateMaterial = () => {
    navigate('/dashboard/teacher/materials/create');
  };

  const handleCreateReport = () => {
    navigate('/dashboard/teacher/reports/create');
  };

  const handleChatClick = () => {
    navigate('/dashboard/chat');
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
            <Button variant="outline" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground rounded-full text-xs flex items-center justify-center">
                5
              </span>
            </Button>
            <Button 
              className="gradient-primary shadow-glow"
              onClick={handleCreateMaterial}
            >
              <Plus className="w-4 h-4 mr-2" />
              Создать материал
            </Button>
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
                <Card className="p-4 border-destructive bg-destructive/10">
                  <div className="flex items-center gap-2 text-destructive">
                    <AlertCircle className="w-5 h-5" />
                    <span>{error}</span>
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
                          <div className="text-2xl font-bold">{dashboardData.progress_overview.total_materials}</div>
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
                          <div className="text-2xl font-bold">{Math.max((dashboardData.progress_overview.total_assignments - dashboardData.progress_overview.completed_assignments), 0)}</div>
                          <div className="text-sm text-muted-foreground">На проверке</div>
                        </div>
                      </div>
                    </Card>
                    <Card className="p-4 hover:border-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard/teacher/students')}>
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-accent/20 rounded-lg flex items-center justify-center">
                          <Users className="w-6 h-6 text-accent" />
                        </div>
                        <div>
                          <div className="text-2xl font-bold">{dashboardData.progress_overview.total_students}</div>
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
                          <div className="text-2xl font-bold">{dashboardData.reports.length}</div>
                          <div className="text-sm text-muted-foreground">Отправлено отчетов</div>
                        </div>
                      </div>
                    </Card>
                  </div>

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
                        {pendingSubmissions.slice(0, 3).map((assignment: any) => (
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
                      <Button 
                        variant="outline" 
                        className="w-full mt-4"
                        onClick={() => navigate('/dashboard/teacher/assignments')}
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
                        <Button size="sm" variant="outline" onClick={handleCreateMaterial}>
                          <Plus className="w-4 h-4 mr-1" />
                          Добавить
                        </Button>
                      </div>
                      <div className="space-y-3">
                        {dashboardData.materials.slice(0, 3).map((material) => (
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
                        {dashboardData.materials.length === 0 && (
                          <div className="text-center py-8 text-muted-foreground">
                            <BookOpen className="w-12 h-12 mx-auto mb-4 opacity-50" />
                            <p>Нет опубликованных материалов</p>
                          </div>
                        )}
                      </div>
                      <Button 
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
                      <Badge variant="outline">{dashboardData.students.length} всего</Badge>
                    </div>
                    <div className="grid md:grid-cols-2 gap-4">
                      {dashboardData.students.slice(0, 4).map((student) => (
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
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                    <Button 
                      variant="outline" 
                      className="w-full mt-4"
                      onClick={() => navigate('/dashboard/teacher/students')}
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
                      <Button size="sm" variant="outline" onClick={handleCreateReport}>
                        <Plus className="w-4 h-4 mr-1" />
                        Создать
                      </Button>
                    </div>
                    <div className="space-y-3">
                      {dashboardData.reports.slice(0, 3).map((report) => (
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
                      {dashboardData.reports.length === 0 && (
                        <div className="text-center py-8 text-muted-foreground">
                          <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                          <p>Нет созданных отчетов</p>
                        </div>
                      )}
                    </div>
                    <Button 
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
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={handleCreateMaterial}
                      >
                        <BookOpen className="w-6 h-6" />
                        <span>Создать материал</span>
                      </Button>
                      <Button 
                        variant="outline" 
                        className="h-auto flex-col gap-2 py-6"
                        onClick={handleCreateReport}
                      >
                        <FileText className="w-6 h-6" />
                        <span>Создать отчёт</span>
                      </Button>
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
                        onClick={() => navigate('/dashboard/teacher/students')}
                      >
                        <Users className="w-6 h-6" />
                        <span>Ученики</span>
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
