import { Home, Users, FileText, MessageSquare, LogOut, User, ReceiptText } from "lucide-react";
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
  { title: "Главная", url: "/dashboard/tutor", icon: Home },
  { title: "Мои ученики", url: "/dashboard/tutor/students", icon: Users },
  { title: "Отчёты", url: "/dashboard/tutor/reports", icon: FileText },
  { title: "Счета", url: "/dashboard/tutor/invoices", icon: ReceiptText },
  { title: "Форум", url: "/dashboard/tutor/forum", icon: MessageSquare },
  { title: "Сообщения", url: "/dashboard/tutor/chat", icon: MessageSquare },
];

export function TutorSidebar() {
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
