"""
Admin Navigation Structure Test

This test verifies the admin cabinet navigation structure by:
1. Checking that all expected admin pages are correctly routed
2. Verifying menu items match their corresponding routes
3. Testing that admin-only access control is in place
4. Checking page components exist and are importable

This is a unit test that doesn't require frontend/backend running.
"""

import pytest
import os
import json
from datetime import datetime
from pathlib import Path


class TestAdminNavigationStructure:
    """Test admin cabinet navigation structure"""

    def setup_method(self):
        """Setup test variables"""
        self.project_root = Path(__file__).parent.parent.parent
        self.frontend_dir = self.project_root / "frontend" / "src"
        self.admin_pages_dir = self.frontend_dir / "pages" / "admin"

    def test_admin_sidebar_component_exists(self):
        """Test that AdminSidebar component exists"""
        sidebar_path = self.frontend_dir / "components" / "admin" / "AdminSidebar.tsx"
        assert sidebar_path.exists(), f"AdminSidebar component not found at {sidebar_path}"

    def test_admin_layout_component_exists(self):
        """Test that AdminLayout component exists"""
        layout_path = self.admin_pages_dir / "AdminLayout.tsx"
        assert layout_path.exists(), f"AdminLayout component not found at {layout_path}"

    def test_admin_pages_exist(self):
        """Test that all expected admin pages exist"""
        expected_pages = [
            "AdminDashboard.tsx",
            "SystemMonitoring.tsx",
            "AccountManagement.tsx",
            "AdminSchedulePage.tsx",
            "AdminChatsPage.tsx",
            "AdminBroadcastsPage.tsx",
            "NotificationTemplatesPage.tsx",
            "NotificationAnalytics.tsx",
            "SystemSettings.tsx",
        ]

        missing_pages = []
        for page_name in expected_pages:
            page_path = self.admin_pages_dir / page_name
            if not page_path.exists():
                missing_pages.append(page_name)

        assert not missing_pages, f"Missing admin pages: {', '.join(missing_pages)}"

    def test_admin_sidebar_menu_items(self):
        """Test that AdminSidebar has all expected menu items"""
        sidebar_path = self.frontend_dir / "components" / "admin" / "AdminSidebar.tsx"

        with open(sidebar_path, "r", encoding="utf-8") as f:
            content = f.read()

        expected_items = [
            ("Мониторинг системы", "/admin/monitoring"),
            ("Управление аккаунтами", "/admin/accounts"),
            ("Расписание", "/admin/schedule"),
            ("Все чаты", "/admin/chats"),
            ("Рассылки", "/admin/broadcasts"),
            ("Шаблоны уведомлений", "/admin/notification-templates"),
            ("Аналитика уведомлений", "/admin/notifications"),
            ("Параметры системы", "/admin/settings"),
        ]

        missing_items = []
        for title, url in expected_items:
            if title not in content:
                missing_items.append(f'"{title}"')
            if url not in content:
                missing_items.append(f'"{url}"')

        assert not missing_items, f"Missing menu items in AdminSidebar: {', '.join(missing_items)}"

    def test_admin_protected_route_exists(self):
        """Test that ProtectedAdminRoute component exists"""
        route_path = self.frontend_dir / "components" / "ProtectedAdminRoute.tsx"
        assert route_path.exists(), f"ProtectedAdminRoute component not found at {route_path}"

    def test_admin_routes_in_app_tsx(self):
        """Test that admin routes are configured in App.tsx"""
        app_path = self.frontend_dir / "App.tsx"

        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for admin route and admin-related path definitions
        # Routes can be split across multiple lines, so check for path= values
        required_paths = [
            "monitoring",
            "accounts",
            "schedule",
            "chats",
            "broadcasts",
            "notification-templates",
            "notifications",
            "settings",
        ]

        # Also check for imports of admin components
        required_imports = [
            "AdminLayout",
            "AccountManagement",
            "AdminSchedulePage",
            "AdminChatsPage",
            "AdminBroadcastsPage",
            "NotificationAnalytics",
            "NotificationTemplatesPage",
            "SystemSettings",
            "SystemMonitoring",
        ]

        missing_paths = []
        for path in required_paths:
            if f'path="{path}"' not in content and f"path=\"{path}" not in content:
                missing_paths.append(path)

        missing_imports = []
        for import_name in required_imports:
            if import_name not in content:
                missing_imports.append(import_name)

        assert not missing_paths, f"Missing admin route paths in App.tsx: {', '.join(missing_paths)}"
        assert not missing_imports, f"Missing admin component imports in App.tsx: {', '.join(missing_imports)}"

    def test_admin_api_integration(self):
        """Test that admin API integration exists"""
        api_path = self.frontend_dir / "integrations" / "api" / "adminAPI.ts"
        assert api_path.exists(), f"Admin API integration not found at {api_path}"

        with open(api_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for key admin API methods
        required_methods = [
            "getStudents",
            "getTutors",
            "getParents",
            "updateUser",
            "deleteUser",
            "createUser",
        ]

        missing_methods = []
        for method in required_methods:
            if f"async {method}" not in content:
                missing_methods.append(method)

        assert not missing_methods, f"Missing admin API methods: {', '.join(missing_methods)}"

    def test_admin_menu_consistency(self):
        """Test that menu items in sidebar match with routes"""
        sidebar_path = self.frontend_dir / "components" / "admin" / "AdminSidebar.tsx"
        app_path = self.frontend_dir / "App.tsx"

        with open(sidebar_path, "r", encoding="utf-8") as f:
            sidebar_content = f.read()

        with open(app_path, "r", encoding="utf-8") as f:
            app_content = f.read()

        # Extract URLs from AdminSidebar
        import re
        sidebar_urls = set(re.findall(r'url:\s*"(/admin/[^"]*)"', sidebar_content))

        # Check that all sidebar URLs have corresponding routes or path definitions in App.tsx
        missing_routes = []
        for url in sidebar_urls:
            # Extract the path part after /admin/
            path_part = url.replace("/admin/", "")

            # Check if the path is referenced in App.tsx as a path definition or route
            # Routes can be: path="monitoring", path="accounts", etc.
            if f'path="{path_part}"' not in app_content:
                # Also check if full URL is mentioned
                if url not in app_content:
                    missing_routes.append(url)

        assert not missing_routes, f"Sidebar URLs not fully routed in App.tsx: {', '.join(missing_routes)}"

    def test_admin_auth_check_in_layout(self):
        """Test that AdminLayout checks for admin authorization"""
        layout_path = self.frontend_dir / "pages" / "admin" / "AdminLayout.tsx"

        with open(layout_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "is_staff" in content, "AdminLayout doesn't check is_staff"
        assert "useAuth" in content, "AdminLayout doesn't use useAuth hook"
        assert "navigate" in content or "useNavigate" in content, "AdminLayout doesn't navigate on unauthorized access"

    def test_admin_protected_route_auth_check(self):
        """Test that ProtectedAdminRoute enforces auth"""
        route_path = self.frontend_dir / "components" / "ProtectedAdminRoute.tsx"

        with open(route_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "is_staff" in content, "ProtectedAdminRoute doesn't check is_staff"
        assert "useAuth" in content, "ProtectedAdminRoute doesn't use useAuth"
        # Check for navigation/redirect logic for unauthorized users
        assert "Navigate" in content, "ProtectedAdminRoute doesn't use Navigate for redirects"
        # Should redirect non-staff users somewhere
        assert "/dashboard" in content or "/auth" in content, "ProtectedAdminRoute doesn't properly redirect unauthorized users"

    def test_sidebar_test_component_exists(self):
        """Test that AdminSidebar test file exists"""
        test_path = self.frontend_dir / "components" / "admin" / "__tests__" / "AdminSidebar.test.tsx"
        assert test_path.exists(), f"AdminSidebar test file not found at {test_path}"

    def test_menu_items_count(self):
        """Test that sidebar has correct number of menu items"""
        sidebar_path = self.frontend_dir / "components" / "admin" / "AdminSidebar.tsx"

        with open(sidebar_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Count "url:" occurrences which represent menu items
        import re
        menu_count = len(re.findall(r'url:\s*"', content))

        # Should have 8 menu items (plus possible hidden ones)
        assert menu_count >= 8, f"Expected at least 8 menu items, found {menu_count}"

    def test_admin_sections_exist(self):
        """Test that admin sections directory exists"""
        sections_dir = self.admin_pages_dir / "sections"
        assert sections_dir.exists(), f"Admin sections directory not found at {sections_dir}"

        expected_sections = [
            "StudentSection.tsx",
            "TeacherSection.tsx",
            "TutorSection.tsx",
            "ParentSection.tsx",
        ]

        missing_sections = []
        for section in expected_sections:
            section_path = sections_dir / section
            if not section_path.exists():
                missing_sections.append(section)

        assert not missing_sections, f"Missing admin sections: {', '.join(missing_sections)}"




if __name__ == "__main__":
    pytest.main([__file__, "-v"])
