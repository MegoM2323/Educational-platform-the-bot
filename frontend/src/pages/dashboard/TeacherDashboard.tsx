import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { BookOpen, CheckCircle, FileText, MessageCircle, Bell, Plus, Clock } from "lucide-react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";

const TeacherDashboard = () => {
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
            <Button className="gradient-primary shadow-glow">
              <Plus className="w-4 h-4 mr-2" />
              Создать материал
            </Button>
          </header>
          <main className="p-6">
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold">Личный кабинет преподавателя</h1>
                <p className="text-muted-foreground">Математика | 42 ученика</p>
              </div>

      {/* Stats Overview */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center">
              <BookOpen className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <div className="text-2xl font-bold">28</div>
              <div className="text-sm text-muted-foreground">Материалов</div>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 gradient-secondary rounded-lg flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-secondary-foreground" />
            </div>
            <div>
              <div className="text-2xl font-bold">15</div>
              <div className="text-sm text-muted-foreground">На проверке</div>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-accent/20 rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-accent" />
            </div>
            <div>
              <div className="text-2xl font-bold">42</div>
              <div className="text-sm text-muted-foreground">Учеников</div>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-success/20 rounded-lg flex items-center justify-center">
              <MessageCircle className="w-6 h-6 text-success" />
            </div>
            <div>
              <div className="text-2xl font-bold">8</div>
              <div className="text-sm text-muted-foreground">Новых вопросов</div>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Homework to Check */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-primary" />
              <h3 className="text-xl font-bold">Задания на проверку</h3>
            </div>
            <Badge variant="destructive">{homeworkToCheck.length}</Badge>
          </div>
          <div className="space-y-3">
            {homeworkToCheck.map((hw, index) => (
              <div key={index} className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer">
                <div className="flex items-start gap-3">
                  <Avatar className="w-10 h-10">
                    <AvatarFallback className="gradient-primary text-primary-foreground">
                      {hw.studentInitials}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-medium">{hw.student}</div>
                      <Badge variant="outline" className="text-xs">
                        {hw.grade} класс
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground mb-2">{hw.task}</div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Clock className="w-3 h-3" />
                      Сдано {hw.submittedTime}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full mt-4">
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
            <Button size="sm" variant="outline">
              <Plus className="w-4 h-4 mr-1" />
              Добавить
            </Button>
          </div>
          <div className="space-y-3">
            {materials.map((material, index) => (
              <div key={index} className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer">
                <div className="flex items-center justify-between mb-2">
                  <div className="font-medium">{material.title}</div>
                  <Badge variant={material.status === "active" ? "default" : "secondary"}>
                    {material.status === "active" ? "Активно" : "Черновик"}
                  </Badge>
                </div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>{material.students} учеников</span>
                  <span>•</span>
                  <span>{material.date}</span>
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full mt-4">
            Все материалы
          </Button>
        </Card>
      </div>

      {/* Questions from Students */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <MessageCircle className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-bold">Вопросы от учеников</h3>
          </div>
          <Badge>{questions.length} новых</Badge>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {questions.map((question, index) => (
            <div key={index} className="p-4 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer">
              <div className="flex items-start gap-3">
                <Avatar className="w-10 h-10">
                  <AvatarFallback className="gradient-secondary text-secondary-foreground">
                    {question.studentInitials}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-medium">{question.student}</div>
                    {question.unread && (
                      <Badge variant="destructive" className="text-xs">Новый</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">{question.preview}</p>
                  <div className="text-xs text-muted-foreground mt-2">{question.time}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
        <Button variant="outline" className="w-full mt-4">
          Все вопросы
        </Button>
      </Card>

      {/* Reports to Send */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <FileText className="w-5 h-5 text-primary" />
          <h3 className="text-xl font-bold">Отчёты по предмету</h3>
        </div>
        <div className="space-y-3">
          {reports.map((report, index) => (
            <div key={index} className="p-4 bg-muted rounded-lg flex items-center justify-between">
              <div>
                <div className="font-medium mb-1">{report.title}</div>
                <div className="text-sm text-muted-foreground">{report.period}</div>
              </div>
              <Button size="sm" variant={report.sent ? "outline" : "default"}>
                {report.sent ? "Отправлено" : "Отправить"}
              </Button>
            </div>
          ))}
        </div>
        <Button variant="outline" className="w-full mt-4">
          Создать новый отчёт
        </Button>
      </Card>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

const homeworkToCheck = [
  {
    student: "Иванов Иван",
    studentInitials: "ИИ",
    grade: "9",
    task: "Задачи на производные",
    submittedTime: "2 часа назад"
  },
  {
    student: "Петрова Мария",
    studentInitials: "ПМ",
    grade: "9",
    task: "Тест по тригонометрии",
    submittedTime: "3 часа назад"
  },
  {
    student: "Сидоров Петр",
    studentInitials: "СП",
    grade: "10",
    task: "Практическая работа №5",
    submittedTime: "5 часов назад"
  }
];

const materials = [
  {
    title: "Тригонометрия: основные формулы",
    students: 28,
    date: "20 октября 2024",
    status: "active"
  },
  {
    title: "Решение логарифмических уравнений",
    students: 28,
    date: "18 октября 2024",
    status: "active"
  },
  {
    title: "Производные сложных функций",
    students: 0,
    date: "Черновик",
    status: "draft"
  }
];

const questions = [
  {
    student: "Кузнецова Анна",
    studentInitials: "КА",
    preview: "Не могу понять, как решать уравнение с двумя переменными в задаче №5...",
    time: "1 час назад",
    unread: true
  },
  {
    student: "Смирнов Алексей",
    studentInitials: "СА",
    preview: "Можете объяснить ещё раз про пределы функций?",
    time: "2 часа назад",
    unread: true
  },
  {
    student: "Волкова Елена",
    studentInitials: "ВЕ",
    preview: "Где можно найти дополнительные задачи по интегралам?",
    time: "Вчера в 18:30",
    unread: false
  },
  {
    student: "Николаев Дмитрий",
    studentInitials: "НД",
    preview: "Спасибо за подробное объяснение темы!",
    time: "Вчера в 15:20",
    unread: false
  }
];

const reports = [
  {
    title: "Отчёт за неделю - группа 9А",
    period: "16-22 октября 2024",
    sent: false
  },
  {
    title: "Отчёт за неделю - группа 10Б",
    period: "16-22 октября 2024",
    sent: false
  },
  {
    title: "Месячный отчёт - все группы",
    period: "Сентябрь 2024",
    sent: true
  }
];

export default TeacherDashboard;
