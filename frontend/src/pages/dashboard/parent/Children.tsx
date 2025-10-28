import { Card } from "@/components/ui/card";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { ParentSidebar } from "@/components/layout/ParentSidebar";
import { Users, CreditCard } from "lucide-react";
import { useParentChildren, useInitiatePayment } from "@/hooks/useParent";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";

const Children = () => {
  const navigate = useNavigate();
  const { data: children, isLoading } = useParentChildren();

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <ParentSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Мои дети</h1>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <Card className="p-6">
              {isLoading ? (
                <div>Загрузка...</div>
              ) : (
                <div className="grid md:grid-cols-2 gap-4">
                  {children?.map((child) => (
                    <Card key={child.id} className="p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold">{child.full_name || child.name}</div>
                        <Badge variant="outline">{child.grade}</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">Цель: {child.goal || '—'}</div>
                      <div className="space-y-2">
                        {child.subjects.map((s) => (
                          <div key={s.id} className="flex items-center justify-between p-2 bg-muted rounded">
                            <div>
                              <div className="font-medium text-sm">{s.name}</div>
                              <div className="text-xs text-muted-foreground">Преподаватель: {s.teacher_name}</div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant={s.payment_status === 'paid' ? 'default' : s.payment_status === 'pending' ? 'secondary' : 'destructive'}>
                                {s.payment_status === 'paid' ? 'Оплачено' : s.payment_status === 'pending' ? 'Ожидание' : 'Просрочено'}
                              </Badge>
                              <PayButton childId={child.id} subjectId={s.id} />
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="pt-2">
                        <Button variant="outline" onClick={() => navigate(`/dashboard/parent/children/${child.id}`)}>Детали</Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </Card>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

function PayButton({ childId, subjectId }: { childId: number; subjectId: number }) {
  const payment = useInitiatePayment(childId, subjectId);
  return (
    <Button size="sm" onClick={() => payment.mutate()} disabled={payment.isPending}>
      <CreditCard className="w-4 h-4 mr-1" /> Оплатить
    </Button>
  );
}

export default Children;
