import { Home, Users, FileText, CreditCard, BarChart3, MessageSquare, LogOut, User, ReceiptText } from "lucide-react";
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
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { ChatNotificationBadge } from "@/components/chat/ChatNotificationBadge";
import { useQuery } from "@tanstack/react-query";
import { invoiceAPI } from "@/integrations/api/invoiceAPI";

const items = [
  { title: "Главная", url: "/dashboard/parent", icon: Home },
  { title: "Мои дети", url: "/dashboard/parent/children", icon: Users },
  { title: "История платежей", url: "/dashboard/parent/payment-history", icon: CreditCard },
  { title: "Счета", url: "/dashboard/parent/invoices", icon: ReceiptText, hasBadge: true },
  { title: "Статистика", url: "/dashboard/parent/statistics", icon: BarChart3 },
  { title: "Отчёты", url: "/dashboard/parent/reports", icon: FileText },
  { title: "Форум", url: "/dashboard/parent/forum", icon: MessageSquare },
];

export function ParentSidebar() {
  const { state } = useSidebar();
  const { signOut } = useAuth();

  // Запрос количества неоплаченных счетов
  const { data: unpaidCount } = useQuery({
    queryKey: ['parent-invoices-unpaid-count'],
    queryFn: async () => {
      try {
        return await invoiceAPI.getUnpaidCount();
      } catch (err) {
        return 0;
      }
    },
    staleTime: 60000, // 1 минута
    refetchInterval: 120000, // Обновлять каждые 2 минуты
  });

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
                          {item.hasBadge && unpaidCount && unpaidCount > 0 && (
                            <Badge variant="destructive" className="ml-auto">
                              {unpaidCount}
                            </Badge>
                          )}
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
