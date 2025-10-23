import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Users, FileText, MessageCircle, Bell, TrendingUp, Target, BookOpen } from "lucide-react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TutorSidebar } from "@/components/layout/TutorSidebar";

const TutorDashboard = () => {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TutorSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1" />
            <Button variant="outline" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground rounded-full text-xs flex items-center justify-center">
                4
              </span>
            </Button>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold">Личный кабинет тьютора</h1>
                <p className="text-muted-foreground">Группа 9А | 12 учеников</p>
              </div>

      {/* Overview Stats */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center">
              <Users className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <div className="text-2xl font-bold">12</div>
              <div className="text-sm text-muted-foreground">Учеников</div>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 gradient-secondary rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-secondary-foreground" />
            </div>
            <div>
              <div className="text-2xl font-bold">3</div>
              <div className="text-sm text-muted-foreground">Новых отчётов</div>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-accent/20 rounded-lg flex items-center justify-center">
              <MessageCircle className="w-6 h-6 text-accent" />
            </div>
            <div>
              <div className="text-2xl font-bold">5</div>
              <div className="text-sm text-muted-foreground">Вопросов</div>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-success/20 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-success" />
            </div>
            <div>
              <div className="text-2xl font-bold">85%</div>
              <div className="text-sm text-muted-foreground">Ср. прогресс</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Students List */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-bold">Список учеников</h3>
          </div>
          <Button size="sm" variant="outline">Экспорт списка</Button>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {students.map((student, index) => (
            <Card key={index} className="p-4 hover:border-primary transition-colors cursor-pointer">
              <div className="flex items-start gap-3">
                <Avatar className="w-12 h-12">
                  <AvatarFallback className="gradient-primary text-primary-foreground">
                    {student.initials}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-medium">{student.name}</div>
                    <Badge variant="outline">{student.grade} класс</Badge>
                  </div>
                  <div className="text-sm text-muted-foreground mb-3">{student.goal}</div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Прогресс</span>
                      <span className="font-medium">{student.progress}%</span>
                    </div>
                    <Progress value={student.progress} className="h-2" />
                  </div>
                  {student.needsAttention && (
                    <Badge variant="destructive" className="mt-2 text-xs">
                      Требует внимания
                    </Badge>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Teacher Reports */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <BookOpen className="w-5 h-5 text-primary" />
              <h3 className="text-xl font-bold">Отчёты от преподавателей</h3>
            </div>
            <Badge>{teacherReports.length} новых</Badge>
          </div>
          <div className="space-y-3">
            {teacherReports.map((report, index) => (
              <div key={index} className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-medium">{report.teacher}</div>
                    <div className="text-sm text-muted-foreground">{report.subject}</div>
                  </div>
                  {report.isNew && (
                    <Badge variant="destructive" className="text-xs">Новый</Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground mb-2">{report.students} учеников</div>
                <div className="text-xs text-muted-foreground">{report.date}</div>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full mt-4">
            Все отчёты
          </Button>
        </Card>

        {/* Messages from Parents */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <MessageCircle className="w-5 h-5 text-primary" />
              <h3 className="text-xl font-bold">Вопросы от родителей</h3>
            </div>
            <Badge>3 новых</Badge>
          </div>
          <div className="space-y-3">
            {parentMessages.map((message, index) => (
              <div key={index} className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer">
                <div className="flex items-start gap-3">
                  <Avatar className="w-10 h-10">
                    <AvatarFallback className="gradient-secondary text-secondary-foreground">
                      {message.parentInitials}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-medium">{message.parent}</div>
                      {message.unread && (
                        <Badge variant="destructive" className="text-xs">Новый</Badge>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground mb-1">
                      Об ученике: {message.student}
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-2">{message.preview}</p>
                    <div className="text-xs text-muted-foreground mt-2">{message.time}</div>
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

      {/* Final Reports to Create */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-bold">Финальные отчёты для родителей</h3>
          </div>
          <Button className="gradient-primary shadow-glow">
            Создать отчёт
          </Button>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {finalReports.map((report, index) => (
            <Card key={index} className="p-4 hover:border-primary transition-colors cursor-pointer">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 gradient-primary rounded-lg flex items-center justify-center flex-shrink-0">
                  <Target className="w-5 h-5 text-primary-foreground" />
                </div>
                <div className="flex-1">
                  <div className="font-medium mb-1">{report.student}</div>
                  <div className="text-sm text-muted-foreground mb-2">{report.period}</div>
                  <Badge variant={report.status === "ready" ? "default" : "outline"}>
                    {report.status === "ready" ? "Готов к отправке" : "В работе"}
                  </Badge>
                </div>
              </div>
            </Card>
          ))}
        </div>
        <div className="mt-4 p-4 bg-muted rounded-lg">
          <div className="text-sm text-muted-foreground">
            <strong>Следующий дедлайн:</strong> 30 октября 2024 - Финальные отчёты за месяц
          </div>
        </div>
      </Card>

      {/* Quick Actions */}
      <Card className="p-6">
        <h3 className="text-xl font-bold mb-4">Быстрые действия</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <Users className="w-6 h-6" />
            <span>Мои ученики</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <FileText className="w-6 h-6" />
            <span>Создать отчёт</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <MessageCircle className="w-6 h-6" />
            <span>Сообщения</span>
          </Button>
          <Button variant="outline" className="h-auto flex-col gap-2 py-6">
            <TrendingUp className="w-6 h-6" />
            <span>Статистика</span>
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

const students = [
  {
    name: "Иванов Иван",
    initials: "ИИ",
    grade: "9",
    goal: "Подготовка к ОГЭ",
    progress: 67,
    needsAttention: false
  },
  {
    name: "Петрова Мария",
    initials: "ПМ",
    grade: "9",
    goal: "Углубленная математика",
    progress: 82,
    needsAttention: false
  },
  {
    name: "Сидоров Петр",
    initials: "СП",
    grade: "9",
    goal: "Подготовка к ОГЭ",
    progress: 45,
    needsAttention: true
  },
  {
    name: "Кузнецова Анна",
    initials: "КА",
    grade: "9",
    goal: "Подготовка к олимпиаде",
    progress: 91,
    needsAttention: false
  }
];

const teacherReports = [
  {
    teacher: "Иванова М.П.",
    subject: "Математика",
    students: "8 учеников",
    date: "22 октября 2024",
    isNew: true
  },
  {
    teacher: "Петров А.С.",
    subject: "Физика",
    students: "10 учеников",
    date: "21 октября 2024",
    isNew: true
  },
  {
    teacher: "Смирнова О.В.",
    subject: "Русский язык",
    students: "12 учеников",
    date: "20 октября 2024",
    isNew: false
  }
];

const parentMessages = [
  {
    parent: "Иванова Е.А.",
    parentInitials: "ИЕ",
    student: "Иван Иванов",
    preview: "Добрый день! Хотела узнать о прогрессе сына по математике...",
    time: "1 час назад",
    unread: true
  },
  {
    parent: "Петров С.И.",
    parentInitials: "ПС",
    student: "Мария Петрова",
    preview: "Спасибо за подробный отчёт! Есть вопросы по английскому...",
    time: "3 часа назад",
    unread: true
  },
  {
    parent: "Сидорова Н.П.",
    parentInitials: "СН",
    student: "Петр Сидоров",
    preview: "Можем ли мы увеличить нагрузку для Пети?",
    time: "Вчера в 16:45",
    unread: false
  }
];

const finalReports = [
  {
    student: "Иванов Иван",
    period: "16-22 октября",
    status: "ready"
  },
  {
    student: "Петрова Мария",
    period: "16-22 октября",
    status: "ready"
  },
  {
    student: "Сидоров Петр",
    period: "16-22 октября",
    status: "draft"
  },
  {
    student: "Кузнецова Анна",
    period: "16-22 октября",
    status: "draft"
  }
];

export default TutorDashboard;
