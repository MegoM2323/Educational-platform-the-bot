import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileText, Plus, Send, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { unifiedAPI } from "@/integrations/api/unifiedClient";
import { useToast } from "@/hooks/use-toast";

export default function TeacherReports() {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<any[]>([]);
  const { toast } = useToast();

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const resp = await unifiedAPI.request<{reports:any[]}>(`/materials/reports/teacher/`);
        if (resp.data?.reports) setReports(resp.data.reports);
      } catch (e) {
        toast({ title: 'Ошибка', description: 'Не удалось загрузить отчёты', variant: 'destructive' });
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

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

      {/* Reports List — без лишних картинок, только кликабельные карточки */}
      <div className="grid md:grid-cols-2 gap-4">
        {(!loading && reports.length === 0) && (
          <Card className="p-6">
            <div className="text-sm text-muted-foreground">Отчётов пока нет</div>
          </Card>
        )}
        {reports.map((report) => (
          <Card key={report.id} className="p-6 hover:border-primary transition-colors cursor-pointer" role="button" tabIndex={0}>
            <div className="flex-1">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-bold mb-1">{report.title}</h3>
                  <div className="text-sm text-muted-foreground">
                    {report.student?.name}
                  </div>
                </div>
                <Badge variant={report.status === 'sent' ? 'default' : 'outline'}>
                  {report.status === 'sent' ? 'Отправлено' : 'Черновик'}
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="w-3 h-3" />
                {new Date(report.created_at).toLocaleDateString('ru-RU')}
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

// Убраны мок-данные; используется загрузка с бэкенда
