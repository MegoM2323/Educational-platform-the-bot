import { Users, Calendar, MessageCircle, Send, LogOut, Activity, Bell, BarChart3, Settings } from "lucide-react";
import { logger } from '@/utils/logger';
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
import { toast } from "sonner";

const items = [
  {
    title: "Мониторинг системы",
    url: "/admin/monitoring",
    icon: Activity,
    description: "Состояние системы и метрики"
  },
  {
    title: "Управление аккаунтами",
    url: "/admin/accounts",
    icon: Users,
    description: "Управление пользователями системы"
  },
  {
    title: "Расписание",
    url: "/admin/schedule",
    icon: Calendar,
    description: "Календарь всех занятий"
  },
  {
    title: "Все чаты",
    url: "/admin/chats",
    icon: MessageCircle,
    description: "Все чаты в системе"
  },
  {
    title: "Рассылки",
    url: "/admin/broadcasts",
    icon: Send,
    description: "Управление рассылками"
  },
  {
    title: "Шаблоны уведомлений",
    url: "/admin/notification-templates",
    icon: Bell,
    description: "Управление шаблонами уведомлений"
  },
  {
    title: "Аналитика уведомлений",
    url: "/admin/notifications",
    icon: BarChart3,
    description: "Аналитика доставки и метрики уведомлений"
  },
  {
    title: "Параметры системы",
    url: "/admin/settings",
    icon: Settings,
    description: "Управление параметрами платформы"
  },
];

export function AdminSidebar() {
  const { state } = useSidebar();
  const { logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      toast.success('Вы вышли из системы');
    } catch (error) {
      logger.error('AdminSidebar logout error:', error);
      toast.error('Ошибка при выходе');
    }
  };

  return (
    <Sidebar collapsible="icon">
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Администратор</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.description}>
                    <NavLink
                      to={item.url}
                      className={({ isActive }) =>
                        isActive ? "bg-sidebar-accent text-sidebar-accent-foreground" : ""
                      }
                    >
                      <item.icon className="h-4 w-4" />
                      {state === "expanded" && (
                        <span>{item.title}</span>
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
            <Button type="button"
              variant="ghost"
              className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4 mr-2" />
              {state === "expanded" && <span>Выход</span>}
            </Button>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}