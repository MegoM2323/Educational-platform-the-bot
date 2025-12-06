import { Home, BookOpen, MessageSquare, LogOut, User, Calendar, CalendarCheck } from "lucide-react";
import { logger } from '@/utils/logger';
import { NavLink, useNavigate } from "react-router-dom";
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
  { title: "Главная", url: "/dashboard/student", icon: Home },
  { title: "Предметы", url: "/dashboard/student/subjects", icon: BookOpen },
  { title: "Материалы", url: "/dashboard/student/materials", icon: BookOpen },
  { title: "Расписание", url: "/dashboard/student/schedule", icon: Calendar },
  { title: "Форум", url: "/dashboard/student/forum", icon: MessageSquare },
];

export function StudentSidebar() {
  const { state } = useSidebar();
  const { signOut } = useAuth();

  const handleLogout = async () => {
    try {
      await signOut();
    } catch (error) {
      logger.error('StudentSidebar sign out error:', error);
    }
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
            <Button variant="ghost" className="w-full justify-start" onClick={handleLogout}>
              <LogOut className="h-4 w-4 mr-2" />
              {state === "expanded" && <span>Выход</span>}
            </Button>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
