import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { BookOpen, User, Calendar } from "lucide-react";
import { studentDashboardAPI } from "@/integrations/api/dashboard";
import { useToast } from "@/hooks/use-toast";

interface Subject {
  enrollment_id: number;
  subject: {
    id: number;
    name: string;
    description: string;
    color: string;
  };
  teacher: {
    id: number;
    name: string;
    email: string;
  };
  assigned_by: {
    id: number;
    name: string;
  } | null;
  enrolled_at: string;
  is_active: boolean;
}

const Subjects = () => {
  const { toast } = useToast();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSubjects = async () => {
      try {
        setLoading(true);
        const data = await studentDashboardAPI.getSubjects();
        setSubjects(data);
      } catch (error: any) {
        console.error('Error fetching subjects:', error);
        toast({
          title: "Ошибка загрузки",
          description: error.message || "Не удалось загрузить предметы",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchSubjects();
  }, [toast]);

  if (loading) {
    return (
      <SidebarProvider>
        <StudentSidebar />
        <SidebarInset>
          <div className="flex flex-col gap-4 p-6">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </SidebarInset>
      </SidebarProvider>
    );
  }

  return (
    <SidebarProvider>
      <StudentSidebar />
      <SidebarInset>
        <div className="flex flex-col gap-6 p-6">
          <div>
            <h1 className="text-3xl font-bold">Мои предметы</h1>
            <p className="text-muted-foreground">
              Предметы, назначенные вам преподавателями
            </p>
          </div>

          {subjects.length === 0 ? (
            <Card className="p-12 text-center">
              <BookOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">Нет назначенных предметов</h3>
              <p className="text-muted-foreground">
                Вам еще не назначены предметы. Обратитесь к преподавателю.
              </p>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {subjects.map((item) => (
                <Card key={item.enrollment_id} className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-4 h-4 rounded-full"
                        style={{ backgroundColor: item.subject.color }}
                      />
                      <h3 className="text-lg font-semibold">{item.subject.name}</h3>
                    </div>
                    {item.is_active ? (
                      <Badge variant="default">Активен</Badge>
                    ) : (
                      <Badge variant="secondary">Неактивен</Badge>
                    )}
                  </div>

                  {item.subject.description && (
                    <p className="text-sm text-muted-foreground mb-4">
                      {item.subject.description}
                    </p>
                  )}

                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">Преподаватель</p>
                        <p className="text-sm text-muted-foreground">{item.teacher.name}</p>
                      </div>
                    </div>

                    {item.assigned_by && (
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">Назначено</p>
                          <p className="text-sm text-muted-foreground">{item.assigned_by.name}</p>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">Дата назначения</p>
                        <p className="text-sm text-muted-foreground">
                          {new Date(item.enrolled_at).toLocaleDateString('ru-RU')}
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
};

export default Subjects;

