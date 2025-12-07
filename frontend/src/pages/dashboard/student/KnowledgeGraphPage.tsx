import React from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { KnowledgeGraphTab } from './KnowledgeGraphTab';

/**
 * Student Knowledge Graph Page
 * Обертка для KnowledgeGraphTab с sidebar
 */
const KnowledgeGraphPage: React.FC = () => {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <StudentSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1">
              <h1 className="text-2xl font-bold">Граф знаний</h1>
            </div>
          </header>
          <main className="p-6">
            <KnowledgeGraphTab />
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default KnowledgeGraphPage;
