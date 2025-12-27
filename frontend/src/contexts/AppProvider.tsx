// Combined App Provider that wraps all contexts
import React, { ReactNode } from 'react';
import { AuthProvider } from './AuthContext';
import { UIProvider } from './UIContext';
import { DataProvider } from './DataContext';
import { NotificationProvider } from './NotificationContext';
import { ThemeProvider } from './ThemeProvider';

interface AppProviderProps {
  children: ReactNode;
}

/**
 * AppProvider wraps all context providers for the application.
 * Order matters: more general providers should be outermost.
 *
 * Provider hierarchy:
 * 1. AuthProvider (authentication state)
 * 2. DataProvider (caching and filters)
 * 3. UIProvider (UI state like theme, sidebar)
 * 4. ThemeProvider (dark mode support - must wrap components that use theme)
 * 5. NotificationProvider (notifications)
 */
export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  return (
    <AuthProvider>
      <DataProvider>
        <UIProvider>
          <ThemeProvider defaultTheme="system">
            <NotificationProvider>
              {children}
            </NotificationProvider>
          </ThemeProvider>
        </UIProvider>
      </DataProvider>
    </AuthProvider>
  );
};

export default AppProvider;
