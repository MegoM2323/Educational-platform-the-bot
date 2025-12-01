import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
// убраны аватарки
import { Users, FileText, MessageCircle } from "lucide-react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TutorSidebar } from "@/components/layout/TutorSidebar";
import { useNavigate } from "react-router-dom";
import { useTutorStudents } from "@/hooks/useTutor";
import { useProfile } from "@/hooks/useProfile";
import { ProfileCard } from "@/components/ProfileCard";

const TutorDashboard = () => {
  const navigate = useNavigate();
  const { data: students, isLoading } = useTutorStudents();
  const { profileData, isLoading: isProfileLoading, error: profileError } = useProfile();
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TutorSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
          </header>
          <main className="p-6">
            <div className="space-y-6">
              {/* Секция "Мой профиль" */}
              {isProfileLoading ? (
                <Card className="p-6 h-64 flex items-center justify-center">
                  <div className="text-center">
                    <div className="inline-block w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mb-2" />
                    <p className="text-muted-foreground">Загружаю профиль...</p>
                  </div>
                </Card>
              ) : profileError ? (
                <Card className="p-6 border-destructive/50 bg-destructive/5">
                  <div className="text-center">
                    <p className="text-destructive font-medium">Ошибка загрузки профиля</p>
                    <p className="text-sm text-muted-foreground mt-1">{profileError.message}</p>
                  </div>
                </Card>
              ) : profileData?.user ? (
                <ProfileCard
                  userName={profileData.user.full_name || `${profileData.user.first_name} ${profileData.user.last_name}`.trim()}
                  userEmail={profileData.user.email}
                  userRole="tutor"
                  profileData={{
                    specialization: (profileData.profile?.specialization as string) || undefined,
                    experience: (profileData.profile?.experience_years as number) || undefined,
                    studentsCount: students?.length ?? 0,
                    reportsCount: (profileData.profile?.reportsCount as number) ?? 0,
                  }}
                  onEdit={() => navigate('/profile/tutor')}
                />
              ) : null}

              <div>
                <h1 className="text-3xl font-bold">Личный кабинет тьютора</h1>
                <p className="text-muted-foreground">Ученики: {isLoading ? 'Загрузка…' : (students?.length ?? 0)}</p>
              </div>

      {/* Overview: только реальный счётчик учеников */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 hover:border-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard/tutor/students')}>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center">
              <Users className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <div className="text-2xl font-bold">{isLoading ? '…' : (students?.length ?? 0)}</div>
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
          </div>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {(students ?? []).map((s) => (
            <Card key={s.id} className="p-4 hover:border-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard/tutor/students')}>
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-medium">{s.full_name || `${s.first_name || ''} ${s.last_name || ''}`}</div>
                    <Badge variant="outline">{s.grade || '-'} класс</Badge>
                  </div>
                  {s.goal ? (
                    <div className="text-sm text-muted-foreground mb-1">Цель: {s.goal}</div>
                  ) : null}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </Card>

      {/* Быстрые действия */}
      <Card className="p-6">
        <h3 className="text-xl font-bold mb-4">Быстрые действия</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Button variant="outline" className="h-auto flex-col gap-2 py-6" onClick={() => navigate('/dashboard/tutor/students')}>
            <Users className="w-6 h-6" />
            <span>Мои ученики</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6" onClick={() => navigate('/dashboard/tutor/reports')}>
            <FileText className="w-6 h-6" />
            <span>Отчёты</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6" onClick={() => navigate('/dashboard/tutor/forum')}>
            <MessageCircle className="w-6 h-6" />
            <span>Форум</span>
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
