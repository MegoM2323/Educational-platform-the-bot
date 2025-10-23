import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { BookOpen, MessageCircle, Target, Bell, CheckCircle, Clock, LogOut } from "lucide-react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { useAuth } from "@/hooks/useAuth";

const StudentDashboard = () => {
  const { signOut } = useAuth();

  const handleSignOut = async () => {
    await signOut();
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
                <h1 className="text-3xl font-bold">Привет, Иван! 👋</h1>
                <p className="text-muted-foreground">Продолжай двигаться к своей цели</p>
              </div>

      {/* Progress Section */}
      <Card className="p-6 gradient-primary text-primary-foreground shadow-glow">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 bg-primary-foreground/20 rounded-full flex items-center justify-center">
            <Target className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-bold">Твой прогресс</h3>
            <p className="text-primary-foreground/80">Цель: Подготовка к ЕГЭ по математике</p>
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Выполнено заданий: 45 из 100</span>
            <span className="font-bold">45%</span>
          </div>
          <Progress value={45} className="h-3 bg-primary-foreground/20" />
        </div>
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="text-center">
            <div className="text-2xl font-bold">23</div>
            <div className="text-sm text-primary-foreground/80">Дней подряд</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">145</div>
            <div className="text-sm text-primary-foreground/80">Баллов</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">92%</div>
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
            {currentMaterials.map((material, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer">
                <div className="flex-1">
                  <div className="font-medium">{material.title}</div>
                  <div className="text-sm text-muted-foreground">{material.teacher}</div>
                </div>
                <Badge variant={material.status === "new" ? "default" : "secondary"}>
                  {material.status === "new" ? "Новое" : "В процессе"}
                </Badge>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full mt-4">
            Смотреть все материалы
          </Button>
        </Card>

        {/* Homework */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-bold">Домашние задания</h3>
          </div>
          <div className="space-y-3">
            {homeworks.map((hw, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div className="flex-1">
                  <div className="font-medium">{hw.title}</div>
                  <div className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                    <Clock className="w-3 h-3" />
                    {hw.deadline}
                  </div>
                </div>
                <Badge variant={hw.checked ? "default" : "outline"}>
                  {hw.checked ? "Проверено" : "На проверке"}
                </Badge>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full mt-4">
            Все задания
          </Button>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="p-6">
        <h3 className="text-xl font-bold mb-4">Быстрые действия</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <MessageCircle className="w-6 h-6" />
            <span>Задать вопрос</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <BookOpen className="w-6 h-6" />
            <span>Материалы</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <Target className="w-6 h-6" />
            <span>Моя цель</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <CheckCircle className="w-6 h-6" />
            <span>Задания</span>
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

const currentMaterials = [
  { title: "Тригонометрия: основные формулы", teacher: "Иванова М.П.", status: "new" },
  { title: "Решение логарифмических уравнений", teacher: "Иванова М.П.", status: "progress" },
  { title: "Геометрия: задачи на углы", teacher: "Петров А.С.", status: "progress" }
];

const homeworks = [
  { title: "Задачи на производные", deadline: "До 25 октября", checked: false },
  { title: "Тест по тригонометрии", deadline: "До 23 октября", checked: true },
  { title: "Практическая работа №5", deadline: "До 27 октября", checked: false }
];

export default StudentDashboard;
