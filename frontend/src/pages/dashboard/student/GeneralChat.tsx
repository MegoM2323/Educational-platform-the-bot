import { Card } from "@/components/ui/card";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { MessageSquare } from "lucide-react";
import { GeneralChatForum } from "@/components/chat/GeneralChatForum";

const GeneralChat = () => {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <StudentSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Чат</h1>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            <GeneralChatForum />
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default GeneralChat;
