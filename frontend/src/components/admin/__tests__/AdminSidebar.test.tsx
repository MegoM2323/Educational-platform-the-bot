import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { AdminSidebar } from '../AdminSidebar';
import * as AuthContext from '@/contexts/AuthContext';
import * as sonner from 'sonner';

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    logout: vi.fn().mockResolvedValue(undefined),
    user: { id: 1, role: 'admin' },
  })),
}));

vi.mock('sonner');

vi.mock('@/components/ui/sidebar', () => ({
  Sidebar: ({ children, collapsible }: any) => (
    <aside data-testid="sidebar" data-collapsible={collapsible}>
      {children}
    </aside>
  ),
  SidebarContent: ({ children }: any) => (
    <div data-testid="sidebar-content">{children}</div>
  ),
  SidebarGroup: ({ children }: any) => (
    <div data-testid="sidebar-group">{children}</div>
  ),
  SidebarGroupLabel: ({ children }: any) => (
    <div data-testid="sidebar-label">{children}</div>
  ),
  SidebarGroupContent: ({ children }: any) => (
    <div data-testid="sidebar-group-content">{children}</div>
  ),
  SidebarMenu: ({ children }: any) => (
    <nav data-testid="sidebar-menu">{children}</nav>
  ),
  SidebarMenuItem: ({ children }: any) => <div data-testid="sidebar-menu-item">{children}</div>,
  SidebarMenuButton: ({ children, asChild, tooltip }: any) => (
    <button data-testid="sidebar-menu-button" data-as-child={asChild} title={tooltip}>
      {children}
    </button>
  ),
  SidebarFooter: ({ children }: any) => <div data-testid="sidebar-footer">{children}</div>,
  useSidebar: () => ({
    state: 'expanded',
    toggleSidebar: vi.fn(),
  }),
}));

describe('AdminSidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (sonner.toast.success as any).mockImplementation(() => {});
    (sonner.toast.error as any).mockImplementation(() => {});
  });

  describe('Hidden Sections - Should NOT Display', () => {
    it('should not display "Мониторинг системы" section', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.queryByText('Мониторинг системы')).not.toBeInTheDocument();
    });

    it('should not display "Рассылки" section', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.queryByText('Рассылки')).not.toBeInTheDocument();
    });

    it('should not display "Шаблоны уведомлений" section', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.queryByText('Шаблоны уведомлений')).not.toBeInTheDocument();
    });

    it('should not display "Аналитика уведомлений" section', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.queryByText('Аналитика уведомлений')).not.toBeInTheDocument();
    });

    it('should not display "Параметры системы" section', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.queryByText('Параметры системы')).not.toBeInTheDocument();
    });
  });

  describe('Visible Sections - Should Display', () => {
    it('should display "Управление аккаунтами" section', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.getByText('Управление аккаунтами')).toBeInTheDocument();
    });

    it('should display "Расписание" section', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.getByText('Расписание')).toBeInTheDocument();
    });

    it('should display "Все чаты" section', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.getByText('Все чаты')).toBeInTheDocument();
    });
  });

  describe('Sidebar Structure and Labels', () => {
    it('should render sidebar with collapsible icon mode', () => {
      const { getByTestId } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const sidebar = getByTestId('sidebar');
      expect(sidebar).toHaveAttribute('data-collapsible', 'icon');
    });

    it('should display "Администратор" label', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.getByText('Администратор')).toBeInTheDocument();
    });

    it('should render footer with logout button', () => {
      const { getByTestId } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const footer = getByTestId('sidebar-footer');
      expect(footer).toBeInTheDocument();
    });

    it('should have "Выход" button', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      expect(screen.getByText('Выход')).toBeInTheDocument();
    });
  });

  describe('Menu Items and Icons', () => {
    it('should render correct number of visible menu items', () => {
      const { getAllByTestId } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const menuItems = getAllByTestId('sidebar-menu-item');
      // 3 visible items + 1 logout button
      expect(menuItems.length).toBeGreaterThanOrEqual(3);
    });

    it('should have tooltip descriptions for menu items', () => {
      const { getAllByTestId } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const menuButtons = getAllByTestId('sidebar-menu-button');
      expect(menuButtons.length).toBeGreaterThan(0);

      // Check that at least some buttons have tooltips (title attribute)
      const hasTooltips = menuButtons.some((btn) => btn.getAttribute('title'));
      expect(hasTooltips).toBe(true);
    });

    it('should have proper links for visible sections', () => {
      const { container } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      // Check for NavLink elements with correct hrefs
      const accountsLink = container.querySelector('a[href="/admin/accounts"]');
      expect(accountsLink).toBeInTheDocument();

      const scheduleLink = container.querySelector('a[href="/admin/schedule"]');
      expect(scheduleLink).toBeInTheDocument();

      const chatsLink = container.querySelector('a[href="/admin/chats"]');
      expect(chatsLink).toBeInTheDocument();
    });
  });

  describe('Logout Functionality', () => {
    it('should call logout when logout button clicked', async () => {
      const user = userEvent.setup();
      const mockLogout = vi.fn().mockResolvedValue(undefined);

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        logout: mockLogout,
        user: { id: 1, role: 'admin' },
      } as any);

      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const logoutButton = screen.getByText('Выход');
      await user.click(logoutButton);

      await waitFor(() => {
        expect(mockLogout).toHaveBeenCalled();
      });
    });

    it('should show success toast on successful logout', async () => {
      const user = userEvent.setup();
      const mockLogout = vi.fn().mockResolvedValue(undefined);

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        logout: mockLogout,
        user: { id: 1, role: 'admin' },
      } as any);

      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const logoutButton = screen.getByText('Выход');
      await user.click(logoutButton);

      await waitFor(() => {
        expect(sonner.toast.success).toHaveBeenCalledWith('Вы вышли из системы');
      });
    });

    it('should show error toast on logout failure', async () => {
      const user = userEvent.setup();
      const mockLogout = vi.fn().mockRejectedValue(new Error('Logout failed'));

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        logout: mockLogout,
        user: { id: 1, role: 'admin' },
      } as any);

      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const logoutButton = screen.getByText('Выход');
      await user.click(logoutButton);

      await waitFor(() => {
        expect(sonner.toast.error).toHaveBeenCalledWith('Ошибка при выходе');
      });
    });
  });

  describe('Section Filtering', () => {
    it('should filter out all hidden sections', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const hiddenSections = [
        'Мониторинг системы',
        'Рассылки',
        'Шаблоны уведомлений',
        'Аналитика уведомлений',
        'Параметры системы',
      ];

      hiddenSections.forEach((section) => {
        expect(screen.queryByText(section)).not.toBeInTheDocument();
      });
    });

    it('should only display exactly 3 visible sections', () => {
      const { getAllByTestId } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      // Get all sidebar menu containers
      const allMenus = getAllByTestId('sidebar-menu');
      // First menu is the main content menu
      const mainMenu = allMenus[0];
      const menuItems = mainMenu.querySelectorAll('[data-testid="sidebar-menu-item"]');
      // Should only have 3 visible sections (Accounts, Schedule, Chats)
      expect(menuItems.length).toBe(3);
    });

    it('should maintain order of visible sections', () => {
      const { container } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const links = container.querySelectorAll('a');
      const linkTexts = Array.from(links)
        .map((link) => link.textContent)
        .filter((text) => text && text.trim());

      // Check that visible sections appear in correct order
      const accountsIndex = linkTexts.findIndex((text) => text.includes('Управление аккаунтами'));
      const scheduleIndex = linkTexts.findIndex((text) => text.includes('Расписание'));
      const chatsIndex = linkTexts.findIndex((text) => text.includes('Все чаты'));

      expect(accountsIndex).toBeLessThan(scheduleIndex);
      expect(scheduleIndex).toBeLessThan(chatsIndex);
    });
  });

  describe('Accessibility', () => {
    it('should have proper semantic HTML structure', () => {
      const { getByTestId, getAllByTestId } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const sidebar = getByTestId('sidebar');
      expect(sidebar.tagName).toBe('ASIDE');

      const allMenus = getAllByTestId('sidebar-menu');
      // First menu is the main content menu
      const menu = allMenus[0];
      expect(menu.tagName).toBe('NAV');
    });

    it('should have footer navigation structure', () => {
      const { getByTestId } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const footer = getByTestId('sidebar-footer');
      expect(footer).toBeInTheDocument();

      const footerMenu = footer.querySelector('[data-testid="sidebar-menu"]');
      expect(footerMenu).toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('should render sidebar with collapsible functionality', () => {
      const { getByTestId } = render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      const sidebar = getByTestId('sidebar');
      expect(sidebar).toHaveAttribute('data-collapsible', 'icon');
    });

    it('should display content when expanded', () => {
      render(
        <BrowserRouter>
          <AdminSidebar />
        </BrowserRouter>
      );

      // With expanded state, text should be visible
      expect(screen.getByText('Управление аккаунтами')).toBeInTheDocument();
      expect(screen.getByText('Расписание')).toBeInTheDocument();
      expect(screen.getByText('Все чаты')).toBeInTheDocument();
    });
  });
});
