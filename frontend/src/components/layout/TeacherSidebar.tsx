import { Home, Send, FileText, MessageSquare, LogOut, CheckSquare, BookOpen, Calendar, CalendarDays, Clock, User, Sparkles, PenTool, Network, TrendingUp } from "lucide-react";
import { NavLink } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { ChatNotificationBadge } from "@/components/chat/ChatNotificationBadge";

const items = [
  { title: "Главная", url: "/dashboard/teacher", icon: Home },
  { title: "Распределение материалов", url: "/dashboard/teacher/materials", icon: Send },
  { title: "Планы занятий", url: "/dashboard/teacher/study-plans", icon: Calendar },
  { title: "AI Генератор планов", url: "/dashboard/teacher/study-plan-generator", icon: Sparkles },
  { title: "Управление расписанием", url: "/dashboard/teacher/schedule", icon: CalendarDays },
  { title: "Проверка заданий", url: "/dashboard/teacher/submissions/pending", icon: CheckSquare },
  { title: "Отчёты", url: "/dashboard/teacher/reports", icon: FileText },
  { title: "Чат", url: "/dashboard/teacher/chat", icon: MessageSquare },
  // { title: "Сообщения", url: "/dashboard/*/chat", icon: MessageSquare },
  { title: "Создание контента", url: "/dashboard/teacher/content-creator", icon: PenTool },
  { title: "Редактор графа", url: "/dashboard/teacher/graph-editor", icon: Network },
  { title: "Прогресс учеников", url: "/dashboard/teacher/progress", icon: TrendingUp },
];

export function TeacherSidebar() {
  const { state } = useSidebar();
  const { signOut } = useAuth();

  const handleLogout = async () => {
    await signOut();
  };

  return (
    <Sidebar collapsible="icon">
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Навигация</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink to={item.url} className={({ isActive }) => isActive ? "bg-sidebar-accent" : ""}>
                      <item.icon className="h-4 w-4" />
                      {state === "expanded" && (
                        <div className="flex items-center justify-between w-full">
                          <span>{item.title}</span>
                          {item.title === "Форум" && <ChatNotificationBadge />}
                        </div>
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild>
              <NavLink to="/profile">
                <User className="h-4 w-4" />
                {state === "expanded" && <span>Профиль</span>}
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <Button type="button" variant="ghost" className="w-full justify-start" onClick={handleLogout}>
              <LogOut className="h-4 w-4 mr-2" />
              {state === "expanded" && <span>Выход</span>}
            </Button>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
