/**
 * Theme Switcher Component Examples
 *
 * Shows different ways to integrate theme switching
 * into your application UI
 */

import React from 'react';
import ThemeSwitcher, { ThemeToggleButton, ThemeSwitcherDropdown } from './ThemeSwitcher';
import { useThemeMode } from '@/contexts/ThemeProvider';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

/**
 * Example 1: Simple Toggle Button in Header
 */
export const HeaderWithThemeToggle = () => {
  return (
    <header className="flex items-center justify-between p-4 border-b">
      <h1 className="text-xl font-bold">THE_BOT</h1>

      <div className="flex items-center gap-4">
        <nav className="flex gap-2">
          <Button variant="ghost">Home</Button>
          <Button variant="ghost">Dashboard</Button>
          <Button variant="ghost">Settings</Button>
        </nav>

        {/* Theme toggle button - simple and clean */}
        <ThemeSwitcher variant="button" />
      </div>
    </header>
  );
};

/**
 * Example 2: Dropdown Menu in Settings
 */
export const SettingsPageWithTheme = () => {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">Settings</h2>

      <div className="space-y-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Theme</h3>
              <p className="text-sm text-muted-foreground">
                Choose your preferred theme
              </p>
            </div>

            {/* Theme dropdown menu with label */}
            <ThemeSwitcher variant="dropdown" showLabel />
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="font-semibold">Language</h3>
          <p className="text-sm text-muted-foreground">
            Select your preferred language
          </p>
        </Card>
      </div>
    </div>
  );
};

/**
 * Example 3: Theme Panel with Custom Controls
 */
export const ThemeControlPanel = () => {
  const { mode, resolvedTheme, setMode, isDark } = useThemeMode();

  return (
    <Card className="p-6 max-w-md">
      <h3 className="text-lg font-semibold mb-4">Theme Settings</h3>

      <div className="space-y-4">
        {/* Current theme display */}
        <div className="text-sm">
          <p className="text-muted-foreground">Current Mode</p>
          <p className="font-medium capitalize">
            {mode === 'system' ? `System (${resolvedTheme})` : mode}
          </p>
        </div>

        {/* Custom button group for theme selection */}
        <div className="flex gap-2">
          <Button
            variant={mode === 'light' ? 'default' : 'outline'}
            className="flex-1"
            onClick={() => setMode('light')}
          >
            Light
          </Button>
          <Button
            variant={mode === 'dark' ? 'default' : 'outline'}
            className="flex-1"
            onClick={() => setMode('dark')}
          >
            Dark
          </Button>
          <Button
            variant={mode === 'system' ? 'default' : 'outline'}
            className="flex-1"
            onClick={() => setMode('system')}
          >
            System
          </Button>
        </div>

        {/* Display indicator */}
        <div className={`p-3 rounded-lg text-center text-sm ${
          isDark ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-900'
        }`}>
          {isDark ? '🌙 Dark Mode Enabled' : '☀️ Light Mode Enabled'}
        </div>

        {/* Help text */}
        <p className="text-xs text-muted-foreground">
          Your preference is saved automatically to your browser.
        </p>
      </div>
    </Card>
  );
};

/**
 * Example 4: Header with Integrated Theme Switcher
 */
export const NavbarWithThemeSwitcher = () => {
  return (
    <nav className="border-b sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg" />
            <h1 className="font-bold text-lg">App</h1>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:flex gap-6">
            <a href="#" className="text-sm hover:text-primary">
              Home
            </a>
            <a href="#" className="text-sm hover:text-primary">
              Features
            </a>
            <a href="#" className="text-sm hover:text-primary">
              Pricing
            </a>
            <a href="#" className="text-sm hover:text-primary">
              Docs
            </a>
          </div>

          {/* Right side: Theme switcher and user menu */}
          <div className="flex items-center gap-2">
            <ThemeSwitcher variant="button" />
            <Button variant="outline">Sign In</Button>
          </div>
        </div>
      </div>
    </nav>
  );
};

/**
 * Example 5: Responsive Header
 */
export const ResponsiveHeaderWithTheme = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  return (
    <header className="border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <h1 className="font-bold text-xl">THE_BOT</h1>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
            <nav className="flex gap-4">
              <Button variant="ghost" size="sm">
                Dashboard
              </Button>
              <Button variant="ghost" size="sm">
                Materials
              </Button>
              <Button variant="ghost" size="sm">
                Settings
              </Button>
            </nav>

            {/* Theme switcher with dropdown */}
            <div className="border-l pl-6">
              <ThemeSwitcher variant="dropdown" showLabel />
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <ThemeSwitcher variant="button" />
          </div>
        </div>
      </div>
    </header>
  );
};

/**
 * Example 6: User Profile Card with Theme Selector
 */
export const UserProfileWithTheme = () => {
  const { isDark } = useThemeMode();

  return (
    <Card className="p-6 max-w-sm">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-lg">John Doe</h3>
          <p className="text-sm text-muted-foreground">john@example.com</p>
        </div>
      </div>

      <div className="space-y-4">
        {/* Avatar with theme-dependent styling */}
        <div className={`w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold ${
          isDark ? 'bg-slate-700' : 'bg-slate-200'
        }`}>
          JD
        </div>

        {/* Theme preference setting */}
        <div className="border-t pt-4">
          <p className="text-sm font-medium mb-2">Theme Preference</p>
          <div className="flex gap-2">
            <ThemeToggleButton showLabel />
            <ThemeSwitcherDropdown />
          </div>
        </div>

        {/* Additional settings */}
        <div className="border-t pt-4">
          <Button variant="outline" className="w-full">
            View Full Profile
          </Button>
        </div>
      </div>
    </Card>
  );
};

/**
 * Example 7: Dashboard Layout with Theme Controls
 */
export const DashboardWithTheme = () => {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Navigation */}
      <nav className="border-b p-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <ThemeSwitcher variant="dropdown" showLabel />
      </nav>

      {/* Main Content */}
      <div className="flex-1 p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1 */}
          <Card className="p-4">
            <h3 className="font-semibold mb-2">Statistics</h3>
            <p className="text-3xl font-bold">1,234</p>
          </Card>

          {/* Card 2 */}
          <Card className="p-4">
            <h3 className="font-semibold mb-2">Progress</h3>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-primary h-2 rounded-full w-3/4"></div>
            </div>
          </Card>

          {/* Card 3 */}
          <Card className="p-4">
            <h3 className="font-semibold mb-2">Status</h3>
            <p className="text-green-600 dark:text-green-400">Active</p>
          </Card>
        </div>
      </div>
    </div>
  );
};

/**
 * Example 8: Modal with Theme Selection
 */
export const PreferenceModal = () => {
  const { mode, setMode } = useThemeMode();

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <Card className="w-96 p-6">
        <h2 className="text-xl font-bold mb-4">Preferences</h2>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium block mb-2">
              Theme
            </label>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as any)}
              className="w-full p-2 border rounded-md"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </div>

          <div className="flex gap-2 pt-4 border-t">
            <Button className="flex-1">Save</Button>
            <Button variant="outline" className="flex-1">
              Cancel
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

/**
 * Example 9: Sidebar with Theme Selector
 */
export const SidebarWithTheme = () => {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r p-4">
        <h2 className="text-xl font-bold mb-6">Menu</h2>

        <nav className="space-y-2 mb-8">
          <Button variant="ghost" className="w-full justify-start">
            Dashboard
          </Button>
          <Button variant="ghost" className="w-full justify-start">
            Materials
          </Button>
          <Button variant="ghost" className="w-full justify-start">
            Settings
          </Button>
        </nav>

        {/* Theme selector at bottom of sidebar */}
        <div className="border-t pt-4">
          <p className="text-xs font-medium text-muted-foreground mb-2">
            APPEARANCE
          </p>
          <ThemeSwitcher variant="dropdown" showLabel />
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1">
        <header className="border-b p-4">
          <h1>Welcome to Dashboard</h1>
        </header>
        <main className="p-6">
          {/* Content here */}
        </main>
      </div>
    </div>
  );
};

/**
 * Example 10: Complete App Shell with Theme Support
 */
export const AppShellWithTheme = () => {
  const { isDark } = useThemeMode();

  return (
    <div className={`min-h-screen ${isDark ? 'dark' : ''}`}>
      <div className="flex flex-col h-screen">
        {/* Header */}
        <header className="border-b">
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <h1 className="text-2xl font-bold">THE_BOT</h1>
            <div className="flex items-center gap-4">
              <nav className="hidden md:flex gap-4">
                <Button variant="ghost">Dashboard</Button>
                <Button variant="ghost">Learn</Button>
                <Button variant="ghost">Settings</Button>
              </nav>
              <ThemeSwitcher variant="dropdown" showLabel />
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <div className="container mx-auto px-4 py-8">
            <h2 className="text-3xl font-bold mb-4">Welcome</h2>
            <p className="text-muted-foreground mb-8">
              Your theme preference is saved automatically.
            </p>

            {/* Sample cards showing theme support */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="p-4">
                  <h3 className="font-semibold mb-2">Card {i}</h3>
                  <p className="text-sm text-muted-foreground">
                    This card adapts to your theme preference.
                  </p>
                </Card>
              ))}
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t p-4 text-center text-sm text-muted-foreground">
          <p>THE_BOT Platform</p>
        </footer>
      </div>
    </div>
  );
};

export default {
  HeaderWithThemeToggle,
  SettingsPageWithTheme,
  ThemeControlPanel,
  NavbarWithThemeSwitcher,
  ResponsiveHeaderWithTheme,
  UserProfileWithTheme,
  DashboardWithTheme,
  PreferenceModal,
  SidebarWithTheme,
  AppShellWithTheme,
};
