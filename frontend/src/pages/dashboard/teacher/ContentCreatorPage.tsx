import React from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { ContentCreatorTab } from './ContentCreatorTab';

/**
 * Teacher Content Creator Page
 * Обертка для ContentCreatorTab с sidebar
 */
const ContentCreatorPage: React.FC = () => {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b bg-background px-6">
            <SidebarTrigger />
            <div className="flex-1">
              <h1 className="text-2xl font-bold">Создание контента</h1>
            </div>
          </header>
          <main className="p-6">
            <ContentCreatorTab />
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default ContentCreatorPage;
