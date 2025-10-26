import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { MessageSquare } from "lucide-react";
import { GeneralChatForum } from "@/components/chat/GeneralChatForum";

const GeneralChat = () => {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Общий чат</h1>
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
