import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Users, FileText, MessageCircle, AlertCircle, RotateCcw } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TutorSidebar } from "@/components/layout/TutorSidebar";
import { useNavigate } from "react-router-dom";
import { useTutorStudents } from "@/hooks/useTutor";
import { useProfile } from "@/hooks/useProfile";
import { ProfileCard } from "@/components/ProfileCard";
import { useAuth } from "@/contexts/AuthContext";
import { useErrorNotification, useSuccessNotification } from "@/components/NotificationSystem";
import { useErrorReporter } from "@/components/ErrorHandlingProvider";
import { ErrorState, EmptyState } from "@/components/LoadingStates";

const TutorDashboard = () => {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const showError = useErrorNotification();
  const showSuccess = useSuccessNotification();
  const { reportError } = useErrorReporter();

  const {
    data: students,
    isLoading,
    error: queryError,
    refetch
  } = useTutorStudents();

  const {
    profileData,
    isLoading: isProfileLoading,
    error: profileError,
    refetch: refetchProfile
  } = useProfile();

  const error = queryError?.message || null;


  const handleProfileEdit = () => {
    navigate('/profile/tutor');
  };

  const handleProfileRetry = () => {
    refetchProfile();
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TutorSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center justify-between gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <h1 className="text-2xl font-bold">Мои студенты</h1>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold">
                  Привет, {user?.first_name || 'Тьютор'}! 👋
                </h1>
                <p className="text-muted-foreground">Управляйте студентами, отправляйте отчеты родителям</p>
              </div>

              {/* Секция профиля тьютора */}
              {isProfileLoading ? (
                <Card className="p-6">
                  <div className="space-y-4">
                    <Skeleton className="h-24 w-24 rounded-full" />
                    <Skeleton className="h-8 w-1/3" />
                    <Skeleton className="h-4 w-1/2" />
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-5/6" />
                    </div>
                  </div>
                </Card>
              ) : profileError ? (
                <ErrorState
                  error={profileError.message || 'Произошла ошибка при загрузке данных профиля. Попробуйте ещё раз.'}
                  onRetry={handleProfileRetry}
                />
              ) : profileData?.user ? (
                <ProfileCard
                  userName={profileData.user.full_name || `${profileData.user.first_name} ${profileData.user.last_name}`.trim()}
                  userEmail={profileData.user.email}
                  userRole="tutor"
                  profileData={{
                    specialization: typeof profileData.profile?.specialization === 'string' ? profileData.profile.specialization : undefined,
                    experience: typeof profileData.profile?.experience_years === 'number' ? profileData.profile.experience_years : undefined,
                    studentsCount: students?.length ?? 0,
                    reportsCount: typeof profileData.profile?.reportsCount === 'number' ? profileData.profile.reportsCount : 0,
                  }}
                  onEdit={handleProfileEdit}
                />
              ) : null}

              {/* Error State */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="flex items-center justify-between">
                    <span>Ошибка загрузки студентов: {error}</span>
                    <Button type="button"
                      onClick={() => refetch()}
                      size="sm"
                      variant="outline"
                      className="ml-2"
                    >
                      <RotateCcw className="w-4 h-4 mr-2" />
                      Повторить
                    </Button>
                  </AlertDescription>
                </Alert>
              )}

              {/* Overview: только реальный счётчик учеников */}
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-4 hover:border-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard/tutor/students')}>
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center">
                      <Users className="w-6 h-6 text-primary-foreground" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold">
                        {isLoading ? '…' : (students?.length ?? 0)}
                      </div>
                      <div className="text-sm text-muted-foreground">Учеников</div>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Список учеников (реальные данные) */}
              <Card className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <Users className="w-5 h-5 text-primary" />
                    <h3 className="text-xl font-bold">Список учеников</h3>
                    {!isLoading && students && students.length > 0 && (
                      <Badge variant="secondary" className="ml-2">{students.length}</Badge>
                    )}
                  </div>
                </div>

                {/* Loading Skeletons */}
                {isLoading && (
                  <div className="grid md:grid-cols-2 gap-4">
                    {[1, 2, 3, 4].map((i) => (
                      <Card key={`student-skeleton-${i}`} className="p-4">
                        <div className="flex items-start gap-3">
                          <Skeleton className="h-12 w-12 rounded-full" />
                          <div className="flex-1 space-y-2">
                            <Skeleton className="h-5 w-3/4" />
                            <Skeleton className="h-4 w-1/2" />
                            <Skeleton className="h-3 w-full" />
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}

                {/* Empty State */}
                {!isLoading && !error && students && students.length === 0 && (
                  <EmptyState
                    title="Нет студентов"
                    description="У вас еще нет назначенных студентов"
                    icon={<Users className="w-12 h-12 text-muted-foreground" />}
                  />
                )}

                {/* Student Cards */}
                {!isLoading && !error && students && students.length > 0 && (
                  <div className="grid md:grid-cols-2 gap-4">
                    {students.map((s) => (
                      <Card
                        key={s.id}
                        className="p-4 hover:border-primary transition-colors cursor-pointer"
                        onClick={() => navigate('/dashboard/tutor/students')}
                      >
                        <div className="flex items-start gap-3">
                          <Avatar className="h-12 w-12">
                            <AvatarFallback>
                              {(s.full_name || s.first_name || 'S').charAt(0).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <div className="font-medium">
                                {s.full_name || `${s.first_name || ''} ${s.last_name || ''}`.trim()}
                              </div>
                              <Badge variant="outline">{s.grade || '-'} класс</Badge>
                            </div>
                            {s.goal ? (
                              <div className="text-sm text-muted-foreground mb-1">
                                Цель: {s.goal}
                              </div>
                            ) : null}
                            {s.subjects && s.subjects.length > 0 ? (
                              <div className="text-xs text-muted-foreground">
                                Предметы: {s.subjects.map((subj) => subj.name).join(', ')}
                              </div>
                            ) : (
                              <div className="text-xs text-muted-foreground">
                                Предметы не назначены
                              </div>
                            )}
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </Card>

              {/* Быстрые действия */}
              <Card className="p-6">
                <h3 className="text-xl font-bold mb-4">Быстрые действия</h3>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <Button type="button"
                    variant="outline"
                    className="h-auto flex-col gap-2 py-6"
                    onClick={() => navigate('/dashboard/tutor/students')}
                  >
                    <Users className="w-6 h-6" />
                    <span>Мои ученики</span>
                  </Button>
                  <Button type="button"
                    variant="outline"
                    className="h-auto flex-col gap-2 py-6"
                    onClick={() => navigate('/dashboard/tutor/reports')}
                  >
                    <FileText className="w-6 h-6" />
                    <span>Отчёты</span>
                  </Button>
                  <Button type="button"
                    variant="outline"
                    className="h-auto flex-col gap-2 py-6"
                    onClick={() => navigate('/dashboard/tutor/forum')}
                  >
                    <MessageCircle className="w-6 h-6" />
                    <span>Форум</span>
                  </Button>
                  <Button type="button"
                    variant="outline"
                    className="h-auto flex-col gap-2 py-6"
                    onClick={() => navigate('/dashboard/tutor/chat')}
                  >
                    <MessageCircle className="w-6 h-6" />
                    <span>Сообщения</span>
                  </Button>
                </div>
              </Card>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default TutorDashboard;
