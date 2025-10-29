import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileText, Plus, Send, Clock } from "lucide-react";
import { useState } from "react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";

export default function TeacherReports() {
  const [showCreateForm, setShowCreateForm] = useState(false);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Отчёты по предмету</h1>
            </div>
            <div className="ml-auto">
              <Button className="gradient-primary shadow-glow" onClick={() => setShowCreateForm(!showCreateForm)}>
                <Plus className="w-4 h-4 mr-2" />
                Создать отчёт
              </Button>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <div className="space-y-6">
              <div className="hidden" />

      {/* Create Report Form */}
      {showCreateForm && (
        <Card className="p-6">
          <h3 className="text-xl font-bold mb-4">Новый отчёт</h3>
          <div className="space-y-4">
            <div>
              <Label>Группа учеников</Label>
              <Input placeholder="Выберите группу..." />
            </div>
            <div>
              <Label>Период</Label>
              <Input type="text" placeholder="например: 16-22 октября 2024" />
            </div>
            <div>
              <Label>Содержание отчёта</Label>
              <Textarea 
                placeholder="Опишите прогресс учеников, сложности, рекомендации..."
                rows={8}
              />
            </div>
            <div className="flex gap-2">
              <Button className="gradient-primary">
                <Send className="w-4 h-4 mr-2" />
                Отправить отчёт
              </Button>
              <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                Отмена
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Reports List */}
      <div className="grid md:grid-cols-2 gap-4">
        {reports.map((report, index) => (
          <Card key={index} className="p-6 hover:border-primary transition-colors">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="w-6 h-6 text-primary-foreground" />
              </div>
              <div className="flex-1">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-bold mb-1">{report.title}</h3>
                    <p className="text-sm text-muted-foreground">{report.period}</p>
                  </div>
                  <Badge variant={report.sent ? "default" : "outline"}>
                    {report.sent ? "Отправлено" : "Черновик"}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mb-4">{report.preview}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
                  <Clock className="w-3 h-3" />
                  {report.date}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" className="flex-1">
                    Редактировать
                  </Button>
                  {!report.sent && (
                    <Button size="sm" className="flex-1">
                      <Send className="w-4 h-4 mr-2" />
                      Отправить
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}

const reports = [
  {
    title: "Отчёт за неделю - группа 9А",
    period: "16-22 октября 2024",
    preview: "Группа показывает хорошие результаты. Большинство учеников активно участвуют...",
    date: "22 октября 2024",
    sent: false
  },
  {
    title: "Отчёт за неделю - группа 10Б",
    period: "16-22 октября 2024",
    preview: "Требуется дополнительная работа с несколькими учениками по теме производных...",
    date: "22 октября 2024",
    sent: false
  },
  {
    title: "Месячный отчёт - все группы",
    period: "Сентябрь 2024",
    preview: "Общий прогресс положительный. Средний балл по группам составил 4.2...",
    date: "30 сентября 2024",
    sent: true
  },
  {
    title: "Отчёт за неделю - группа 9А",
    period: "9-15 октября 2024",
    preview: "Продолжаем работу над тригонометрией. Иванов и Петрова показывают отличные...",
    date: "15 октября 2024",
    sent: true
  }
];
