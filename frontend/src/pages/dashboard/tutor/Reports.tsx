import { Card } from "@/components/ui/card";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TutorSidebar } from "@/components/layout/TutorSidebar";
import { FileText } from "lucide-react";

export default function TutorReports() {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TutorSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Отчёты</h1>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <Card className="p-6">
              <div className="space-y-2">
                <h2 className="text-xl font-bold">Реализуем в будущем</h2>
                <p className="text-muted-foreground">
                  Раздел находится в разработке. Функциональность появится позже.
                </p>
              </div>
            </Card>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
