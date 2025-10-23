import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { FileText, Plus, Send, Clock, BookOpen } from "lucide-react";
import { useState } from "react";

export default function TutorReports() {
  const [showCreateForm, setShowCreateForm] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Финальные отчёты</h1>
          <p className="text-muted-foreground">Создавайте и отправляйте отчёты родителям</p>
        </div>
        <Button className="gradient-primary shadow-glow" onClick={() => setShowCreateForm(!showCreateForm)}>
          <Plus className="w-4 h-4 mr-2" />
          Создать отчёт
        </Button>
      </div>

      {/* Create Report Form */}
      {showCreateForm && (
        <Card className="p-6">
          <h3 className="text-xl font-bold mb-4">Новый финальный отчёт</h3>
          <div className="space-y-4">
            <div>
              <Label>Ученик</Label>
              <Input placeholder="Выберите ученика..." />
            </div>
            <div>
              <Label>Период</Label>
              <Input type="text" placeholder="например: 16-22 октября 2024" />
            </div>
            <div>
              <Label>Общая оценка прогресса</Label>
              <Textarea 
                placeholder="Опишите общий прогресс ученика..."
                rows={4}
              />
            </div>
            <div>
              <Label>Успехи и достижения</Label>
              <Textarea 
                placeholder="Что получается хорошо..."
                rows={4}
              />
            </div>
            <div>
              <Label>Области для улучшения</Label>
              <Textarea 
                placeholder="Над чем нужно поработать..."
                rows={4}
              />
            </div>
            <div>
              <Label>Рекомендации для родителей</Label>
              <Textarea 
                placeholder="Ваши рекомендации..."
                rows={4}
              />
            </div>
            <div className="flex gap-2">
              <Button className="gradient-primary">
                <Send className="w-4 h-4 mr-2" />
                Отправить родителям
              </Button>
              <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                Отмена
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Teacher Reports Section */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <BookOpen className="w-5 h-5 text-primary" />
          <h3 className="text-xl font-bold">Отчёты от преподавателей</h3>
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
                  <Badge variant="default" className="text-xs">Новый</Badge>
                )}
              </div>
              <div className="text-sm text-muted-foreground mb-2">{report.preview}</div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="w-3 h-3" />
                {report.date}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* My Reports */}
      <div>
        <h3 className="text-xl font-bold mb-4">Мои отчёты</h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {finalReports.map((report, index) => (
            <Card key={index} className="p-6 hover:border-primary transition-colors cursor-pointer">
              <div className="flex items-start gap-3 mb-4">
                <Avatar className="w-12 h-12">
                  <AvatarFallback className="gradient-primary text-primary-foreground">
                    {report.studentInitials}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="font-bold mb-1">{report.student}</div>
                  <div className="text-sm text-muted-foreground">{report.period}</div>
                </div>
              </div>
              <Badge variant={report.status === "ready" ? "default" : "outline"} className="mb-4">
                {report.status === "ready" ? "Готов к отправке" : "В работе"}
              </Badge>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" className="flex-1">
                  Редактировать
                </Button>
                {report.status === "ready" && (
                  <Button size="sm" className="flex-1">
                    <Send className="w-4 h-4 mr-2" />
                    Отправить
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

const teacherReports = [
  {
    teacher: "Иванова М.П.",
    subject: "Математика",
    preview: "Группа показывает хорошие результаты по тригонометрии...",
    date: "22 октября 2024",
    isNew: true
  },
  {
    teacher: "Петров А.С.",
    subject: "Физика",
    preview: "Требуется дополнительное внимание к теме динамики...",
    date: "21 октября 2024",
    isNew: true
  },
  {
    teacher: "Смирнова О.В.",
    subject: "Русский язык",
    preview: "Отличные результаты по написанию сочинений...",
    date: "20 октября 2024",
    isNew: false
  }
];

const finalReports = [
  {
    student: "Иванов Иван",
    studentInitials: "ИИ",
    period: "16-22 октября",
    status: "ready"
  },
  {
    student: "Петрова Мария",
    studentInitials: "ПМ",
    period: "16-22 октября",
    status: "ready"
  },
  {
    student: "Сидоров Петр",
    studentInitials: "СП",
    period: "16-22 октября",
    status: "draft"
  },
  {
    student: "Кузнецова Анна",
    studentInitials: "КА",
    period: "16-22 октября",
    status: "draft"
  }
];
