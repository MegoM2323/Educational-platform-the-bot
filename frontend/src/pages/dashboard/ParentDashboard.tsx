import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Users, FileText, MessageCircle, Bell, TrendingUp, Calendar } from "lucide-react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";

const ParentDashboard = () => {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ParentSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
            <Button variant="outline" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground rounded-full text-xs flex items-center justify-center">
                2
              </span>
            </Button>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold">Личный кабинет родителя</h1>
                <p className="text-muted-foreground">Следите за успехами ваших детей</p>
              </div>

      {/* Children Profiles */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Users className="w-5 h-5 text-primary" />
          <h3 className="text-xl font-bold">Профили детей</h3>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {children.map((child, index) => (
            <Card key={index} className="p-4 hover:border-primary transition-colors cursor-pointer">
              <div className="flex items-start gap-4">
                <Avatar className="w-16 h-16">
                  <AvatarImage src={child.avatar} />
                  <AvatarFallback className="gradient-primary text-primary-foreground text-lg">
                    {child.initials}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-bold text-lg">{child.name}</h4>
                    <Badge variant="outline">{child.grade} класс</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">{child.goal}</p>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <div className="text-muted-foreground">Тьютор</div>
                      <div className="font-medium">{child.tutor}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Прогресс</div>
                      <div className="font-medium text-success">{child.progress}%</div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Recent Reports */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-bold">Последние отчёты</h3>
          </div>
          <div className="space-y-3">
            {reports.map((report, index) => (
              <div key={index} className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-medium">{report.student}</div>
                    <div className="text-sm text-muted-foreground">{report.subject}</div>
                  </div>
                  <Badge variant={report.type === "tutor" ? "default" : "secondary"}>
                    {report.type === "tutor" ? "Тьютор" : "Преподаватель"}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Calendar className="w-3 h-3" />
                  {report.date}
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full mt-4">
            Смотреть все отчёты
          </Button>
        </Card>

        {/* Messages with Tutor */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <MessageCircle className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-bold">Сообщения с тьютором</h3>
          </div>
          <div className="space-y-3">
            {messages.map((message, index) => (
              <div key={index} className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer">
                <div className="flex items-start gap-3">
                  <Avatar className="w-10 h-10">
                    <AvatarFallback className="gradient-secondary text-secondary-foreground">
                      {message.tutorInitials}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-medium">{message.tutor}</div>
                      <Badge variant={message.unread ? "default" : "outline"} className="text-xs">
                        {message.unread ? "Новое" : "Прочитано"}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground truncate">{message.preview}</p>
                    <div className="text-xs text-muted-foreground mt-1">{message.time}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full mt-4">
            Все сообщения
          </Button>
        </Card>
      </div>

      {/* Quick Stats */}
      <Card className="p-6">
        <h3 className="text-xl font-bold mb-4">Статистика успеваемости</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 gradient-primary rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-primary-foreground" />
              </div>
              <div>
                <div className="text-2xl font-bold">87%</div>
                <div className="text-sm text-muted-foreground">Средний балл</div>
              </div>
            </div>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 gradient-secondary rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-secondary-foreground" />
              </div>
              <div>
                <div className="text-2xl font-bold">42</div>
                <div className="text-sm text-muted-foreground">Задания</div>
              </div>
            </div>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-success/20 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-success" />
              </div>
              <div>
                <div className="text-2xl font-bold">+12%</div>
                <div className="text-sm text-muted-foreground">Прогресс</div>
              </div>
            </div>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-accent/20 rounded-lg flex items-center justify-center">
                <Calendar className="w-5 h-5 text-accent" />
              </div>
              <div>
                <div className="text-2xl font-bold">28</div>
                <div className="text-sm text-muted-foreground">Дней подряд</div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Quick Actions */}
      <Card className="p-6">
        <h3 className="text-xl font-bold mb-4">Быстрые действия</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <MessageCircle className="w-6 h-6" />
            <span>Написать тьютору</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <FileText className="w-6 h-6" />
            <span>Просмотреть отчёты</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <TrendingUp className="w-6 h-6" />
            <span>Прогресс детей</span>
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

const children = [
  {
    name: "Иван Петров",
    initials: "ИП",
    grade: "9",
    goal: "Подготовка к ОГЭ по математике",
    tutor: "Сидорова А.В.",
    progress: 67,
    avatar: ""
  },
  {
    name: "Мария Петрова",
    initials: "МП",
    grade: "6",
    goal: "Углубленное изучение английского",
    tutor: "Кузнецова Л.П.",
    progress: 82,
    avatar: ""
  }
];

const reports = [
  {
    student: "Иван Петров",
    subject: "Математика - Тригонометрия",
    type: "teacher",
    date: "22 октября 2024"
  },
  {
    student: "Мария Петрова",
    subject: "Общий отчёт за неделю",
    type: "tutor",
    date: "20 октября 2024"
  },
  {
    student: "Иван Петров",
    subject: "Финальный отчёт за месяц",
    type: "tutor",
    date: "18 октября 2024"
  }
];

const messages = [
  {
    tutor: "Сидорова А.В.",
    tutorInitials: "СА",
    preview: "Иван отлично справляется с новым материалом...",
    time: "2 часа назад",
    unread: true
  },
  {
    tutor: "Кузнецова Л.П.",
    tutorInitials: "КЛ",
    preview: "Предлагаю увеличить нагрузку для Марии...",
    time: "Вчера в 15:30",
    unread: false
  }
];

export default ParentDashboard;
