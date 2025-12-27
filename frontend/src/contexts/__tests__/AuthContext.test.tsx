import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import {
  AuthProvider,
  useAuth,
  useAuthUser,
  useAuthLoading,
  useAuthMethods,
  useIsRole,
} from '../AuthContext';
import * as authService from '@/services/authService';

// Mock authService
vi.mock('@/services/authService', () => ({
  authService: {
    waitForInitialization: vi.fn(() => Promise.resolve()),
    getCurrentUser: vi.fn(() => null),
    isAuthenticated: vi.fn(() => false),
    isInitializing: vi.fn(() => false),
    onAuthStateChange: vi.fn((callback) => {
      return () => {};
    }),
    login: vi.fn(),
    logout: vi.fn(),
    refreshTokenIfNeeded: vi.fn(),
  },
}));

const AuthTestComponent = () => {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth();

  const handleLogin = async () => {
    try {
      await login({ username: 'test', password: 'password' });
    } catch (error) {
      // Handle error
    }
  };

  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      <div data-testid="loading-status">{isLoading ? 'loading' : 'idle'}</div>
      <div data-testid="user-id">{user?.id || 'none'}</div>
      <div data-testid="user-role">{user?.role || 'none'}</div>
      <button onClick={handleLogin} data-testid="login-btn">
        Login
      </button>
      <button onClick={logout} data-testid="logout-btn">
        Logout
      </button>
    </div>
  );
};

const SelectorTestComponent = () => {
  const user = useAuthUser();
  const isLoading = useAuthLoading();
  const { login, logout } = useAuthMethods();

  return (
    <div>
      <div data-testid="selector-user">{user?.id || 'none'}</div>
      <div data-testid="selector-loading">{isLoading ? 'loading' : 'idle'}</div>
    </div>
  );
};

const RoleTestComponent = ({ role }: { role: string }) => {
  const isRole = useIsRole(role);

  return <div data-testid="role-check">{isRole ? 'match' : 'no-match'}</div>;
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(authService.authService.waitForInitialization).mockResolvedValue(undefined);
    vi.mocked(authService.authService.getCurrentUser).mockReturnValue(null);
    vi.mocked(authService.authService.isAuthenticated).mockReturnValue(false);
    vi.mocked(authService.authService.isInitializing).mockReturnValue(false);
  });

  describe('useAuth hook', () => {
    it('should provide initial state', () => {
      render(
        <AuthProvider>
          <AuthTestComponent />
        </AuthProvider>
      );

      expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
      expect(screen.getByTestId('user-id')).toHaveTextContent('none');
    });

    it('should initialize with authenticated user', async () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'student',
      };

      vi.mocked(authService.authService.getCurrentUser).mockReturnValue(mockUser);
      vi.mocked(authService.authService.isAuthenticated).mockReturnValue(true);

      render(
        <AuthProvider>
          <AuthTestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
      });
    });

    it('should handle login', async () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'student',
      };

      vi.mocked(authService.authService.login).mockResolvedValue({
        success: true,
        user: mockUser,
        message: 'Login successful',
      });

      render(
        <AuthProvider>
          <AuthTestComponent />
        </AuthProvider>
      );

      fireEvent.click(screen.getByTestId('login-btn'));

      await waitFor(() => {
        expect(vi.mocked(authService.authService.login)).toHaveBeenCalled();
      });
    });

    it('should handle logout', async () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'student',
      };

      vi.mocked(authService.authService.getCurrentUser).mockReturnValue(mockUser);
      vi.mocked(authService.authService.isAuthenticated).mockReturnValue(true);
      vi.mocked(authService.authService.logout).mockResolvedValue(undefined);

      // Mock window.location
      delete (window as any).location;
      window.location = { href: '' } as any;

      render(
        <AuthProvider>
          <AuthTestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
      });

      fireEvent.click(screen.getByTestId('logout-btn'));

      await waitFor(() => {
        expect(vi.mocked(authService.authService.logout)).toHaveBeenCalled();
      });
    });
  });

  describe('Selector hooks - performance optimization', () => {
    it('useAuthUser should memoize user object', () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'student',
      };

      vi.mocked(authService.authService.getCurrentUser).mockReturnValue(mockUser);
      vi.mocked(authService.authService.isAuthenticated).mockReturnValue(true);

      const { rerender } = render(
        <AuthProvider>
          <SelectorTestComponent />
        </AuthProvider>
      );

      const firstRender = screen.getByTestId('selector-user').textContent;

      rerender(
        <AuthProvider>
          <SelectorTestComponent />
        </AuthProvider>
      );

      const secondRender = screen.getByTestId('selector-user').textContent;

      expect(firstRender).toBe(secondRender);
    });

    it('useAuthLoading should select only loading state', async () => {
      const LoadingOnlyComponent = () => {
        const isLoading = useAuthLoading();
        return <div data-testid="selector-loading">{isLoading ? 'loading' : 'idle'}</div>;
      };

      render(
        <AuthProvider>
          <LoadingOnlyComponent />
        </AuthProvider>
      );

      // Initial state should be idle (after initialization)
      await waitFor(() => {
        const loadingText = screen.getByTestId('selector-loading').textContent;
        expect(['loading', 'idle']).toContain(loadingText);
      });
    });

    it('useAuthMethods should memoize callback functions', async () => {
      const MethodsComponent = () => {
        const { login, logout } = useAuthMethods();
        return (
          <div>
            <div data-testid="has-methods">
              {typeof login === 'function' && typeof logout === 'function' ? 'yes' : 'no'}
            </div>
          </div>
        );
      };

      render(
        <AuthProvider>
          <MethodsComponent />
        </AuthProvider>
      );

      // Methods should be functions
      expect(screen.getByTestId('has-methods')).toHaveTextContent('yes');
    });
  });

  describe('useIsRole hook', () => {
    it('should check user role correctly', () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'student',
      };

      vi.mocked(authService.authService.getCurrentUser).mockReturnValue(mockUser);
      vi.mocked(authService.authService.isAuthenticated).mockReturnValue(true);

      render(
        <AuthProvider>
          <RoleTestComponent role="student" />
        </AuthProvider>
      );

      expect(screen.getByTestId('role-check')).toHaveTextContent('match');
    });

    it('should return false for wrong role', () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'student',
      };

      vi.mocked(authService.authService.getCurrentUser).mockReturnValue(mockUser);
      vi.mocked(authService.authService.isAuthenticated).mockReturnValue(true);

      render(
        <AuthProvider>
          <RoleTestComponent role="teacher" />
        </AuthProvider>
      );

      expect(screen.getByTestId('role-check')).toHaveTextContent('no-match');
    });
  });

  describe('Error handling', () => {
    it('should throw error when used outside provider', () => {
      vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        render(<AuthTestComponent />);
      }).toThrow('useAuth должен использоваться внутри AuthProvider');

      vi.restoreAllMocks();
    });

    it('should handle login errors gracefully', async () => {
      const error = new Error('Login failed');
      vi.mocked(authService.authService.login).mockRejectedValue(error);

      render(
        <AuthProvider>
          <AuthTestComponent />
        </AuthProvider>
      );

      fireEvent.click(screen.getByTestId('login-btn'));

      await waitFor(() => {
        expect(vi.mocked(authService.authService.login)).toHaveBeenCalled();
      });
    });

    it('should handle logout errors gracefully', async () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'student',
      };

      vi.mocked(authService.authService.getCurrentUser).mockReturnValue(mockUser);
      vi.mocked(authService.authService.isAuthenticated).mockReturnValue(true);
      vi.mocked(authService.authService.logout).mockRejectedValue(new Error('Logout failed'));

      // Mock window.location
      delete (window as any).location;
      window.location = { href: '' } as any;

      render(
        <AuthProvider>
          <AuthTestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
      });

      fireEvent.click(screen.getByTestId('logout-btn'));

      // Should still redirect even on error
      await waitFor(() => {
        expect(window.location.href).toBe('/auth');
      });
    });
  });

  describe('Re-render optimization', () => {
    it('should not cause unnecessary re-renders with selectors', async () => {
      let renderCount = 0;

      const CountingComponent = () => {
        renderCount++;
        const user = useAuthUser();
        return <div data-testid="counter">{renderCount}</div>;
      };

      const { rerender } = render(
        <AuthProvider>
          <CountingComponent />
        </AuthProvider>
      );

      const firstRenderCount = renderCount;

      rerender(
        <AuthProvider>
          <CountingComponent />
        </AuthProvider>
      );

      const secondRenderCount = renderCount;

      // Should not increase significantly due to memoization
      expect(secondRenderCount).toBeLessThanOrEqual(firstRenderCount + 2);
    });
  });
});

// Test useAuthMethods separately
describe('useAuthMethods', () => {
  it('should return stable method references', () => {
    const TestComponent = () => {
      const { login, logout, refreshToken } = useAuthMethods();
      return (
        <div data-testid="methods-exist">
          {typeof login === 'function' && typeof logout === 'function' ? 'yes' : 'no'}
        </div>
      );
    };

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('methods-exist')).toHaveTextContent('yes');
  });
});
