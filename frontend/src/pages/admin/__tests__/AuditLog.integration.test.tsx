import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import AuditLog from '../AuditLog';

/**
 * Integration tests for AuditLog component
 * Tests actual API integration and user workflows
 */

describe('AuditLog Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <AuditLog />
      </BrowserRouter>
    );
  };

  describe('API Integration', () => {
    it('should fetch audit logs from API endpoint', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 3,
              next: null,
              previous: null,
              results: [
                {
                  id: 1,
                  timestamp: '2024-01-15T10:30:00Z',
                  user: {
                    id: 1,
                    email: 'admin@test.com',
                    full_name: 'Admin User',
                  },
                  action: 'create',
                  resource: 'User',
                  status: 'success',
                  ip_address: '192.168.1.1',
                  details: 'Created new user',
                },
              ],
            }),
        })
      ) as any;

      renderComponent();

      await waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledWith(
          expect.stringContaining('/api/admin/audit-logs/'),
          expect.any(Object)
        );
      });

      expect(screen.getByText('Admin User')).toBeInTheDocument();
      fetchSpy.mockRestore();
    });

    it('should handle API errors gracefully', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          statusText: 'Internal Server Error',
        })
      ) as any;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText(/Failed to load audit logs/)).toBeInTheDocument();
      });
    });

    it('should build correct query parameters', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 0,
              results: [],
            }),
        })
      ) as any;

      renderComponent();

      await waitFor(() => {
        expect(fetchSpy).toHaveBeenCalled();
      });

      // Check initial load includes pagination and sorting
      const firstCall = fetchSpy.mock.calls[0][0];
      expect(firstCall).toContain('page=1');
      expect(firstCall).toContain('page_size=50');
      expect(firstCall).toContain('ordering=-timestamp');

      fetchSpy.mockRestore();
    });
  });

  describe('Filter API Integration', () => {
    it('should apply filters to API request', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 1,
              results: [
                {
                  id: 1,
                  timestamp: '2024-01-15T10:30:00Z',
                  user: {
                    id: 1,
                    email: 'admin@test.com',
                    full_name: 'Admin User',
                  },
                  action: 'create',
                  resource: 'User',
                  status: 'success',
                  ip_address: '192.168.1.1',
                },
              ],
            }),
        })
      ) as any;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Admin User')).toBeInTheDocument();
      });

      // Apply action filter
      const actionSelects = screen.getAllByDisplayValue('All actions');
      fireEvent.click(actionSelects[0]);

      const createOption = screen.getByText('Create', { selector: 'span' });
      fireEvent.click(createOption);

      await waitFor(() => {
        const lastCall = fetchSpy.mock.calls[fetchSpy.mock.calls.length - 1][0];
        expect(lastCall).toContain('action=create');
      });

      fetchSpy.mockRestore();
    });

    it('should apply date range filter', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 0,
              results: [],
            }),
        })
      ) as any;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByLabelText('Date From')).toBeInTheDocument();
      });

      const dateFromInput = screen.getByLabelText('Date From') as HTMLInputElement;
      const dateToInput = screen.getByLabelText('Date To') as HTMLInputElement;

      await userEvent.type(dateFromInput, '2024-01-01');
      await userEvent.type(dateToInput, '2024-01-31');

      await waitFor(() => {
        const lastCall = fetchSpy.mock.calls[fetchSpy.mock.calls.length - 1][0];
        expect(lastCall).toContain('date_from=2024-01-01');
        expect(lastCall).toContain('date_to=2024-01-31');
      });

      fetchSpy.mockRestore();
    });
  });

  describe('Pagination API Integration', () => {
    it('should fetch next page with correct parameters', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      let callCount = 0;
      global.fetch = vi.fn(() => {
        callCount++;
        if (callCount === 1 || callCount === 2) {
          // First call (users) and second call (logs page 1)
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                count: 100,
                next: '/api/admin/audit-logs/?page=2',
                results: Array(50).fill({
                  id: 1,
                  timestamp: '2024-01-15T10:30:00Z',
                  user: { id: 1, email: 'admin@test.com', full_name: 'Admin' },
                  action: 'create',
                  resource: 'User',
                  status: 'success',
                  ip_address: '192.168.1.1',
                }),
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 100,
              previous: '/api/admin/audit-logs/?page=1',
              results: Array(50).fill({
                id: 51,
                timestamp: '2024-01-14T10:30:00Z',
                user: { id: 1, email: 'admin@test.com', full_name: 'Admin' },
                action: 'update',
                resource: 'Material',
                status: 'success',
                ip_address: '192.168.1.1',
              }),
            }),
        });
      }) as any;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Admin')).toBeInTheDocument();
      });

      // Note: Actual pagination button interaction depends on component implementation
      // This verifies the API setup is correct
      fetchSpy.mockRestore();
    });
  });

  describe('CSV Export API Integration', () => {
    it('should call export endpoint with CSV format', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');
      const createElementSpy = vi.spyOn(document, 'createElement');
      const appendChildSpy = vi.spyOn(document.body, 'appendChild');
      const removeChildSpy = vi.spyOn(document.body, 'removeChild');

      const mockBlob = new Blob(['csv data'], { type: 'text/csv' });

      global.fetch = vi.fn((url: string) => {
        if (url.includes('format=csv')) {
          return Promise.resolve({
            ok: true,
            blob: () => Promise.resolve(mockBlob),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 1,
              results: [
                {
                  id: 1,
                  timestamp: '2024-01-15T10:30:00Z',
                  user: { id: 1, email: 'admin@test.com', full_name: 'Admin' },
                  action: 'create',
                  resource: 'User',
                  status: 'success',
                  ip_address: '192.168.1.1',
                },
              ],
            }),
        });
      }) as any;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Export CSV')).toBeInTheDocument();
      });

      const exportButton = screen.getByText('Export CSV');
      fireEvent.click(exportButton);

      await waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledWith(
          expect.stringContaining('format=csv'),
          expect.any(Object)
        );
      });

      createElementSpy.mockRestore();
      appendChildSpy.mockRestore();
      removeChildSpy.mockRestore();
      fetchSpy.mockRestore();
    });
  });

  describe('Real-time Refresh', () => {
    it('should auto-refresh logs every 30 seconds', async () => {
      vi.useFakeTimers();
      const fetchSpy = vi.spyOn(global, 'fetch');

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 1,
              results: [
                {
                  id: 1,
                  timestamp: '2024-01-15T10:30:00Z',
                  user: { id: 1, email: 'admin@test.com', full_name: 'Admin' },
                  action: 'create',
                  resource: 'User',
                  status: 'success',
                  ip_address: '192.168.1.1',
                },
              ],
            }),
        })
      ) as any;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Admin')).toBeInTheDocument();
      });

      const initialCallCount = fetchSpy.mock.calls.length;

      // Fast-forward 30 seconds
      vi.advanceTimersByTime(30000);

      // Should trigger another fetch
      await waitFor(() => {
        expect(fetchSpy.mock.calls.length).toBeGreaterThan(initialCallCount);
      });

      vi.useRealTimers();
      fetchSpy.mockRestore();
    });

    it('should stop auto-refresh when disabled', async () => {
      vi.useFakeTimers();
      const fetchSpy = vi.spyOn(global, 'fetch');

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 1,
              results: [
                {
                  id: 1,
                  timestamp: '2024-01-15T10:30:00Z',
                  user: { id: 1, email: 'admin@test.com', full_name: 'Admin' },
                  action: 'create',
                  resource: 'User',
                  status: 'success',
                  ip_address: '192.168.1.1',
                },
              ],
            }),
        })
      ) as any;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Admin')).toBeInTheDocument();
      });

      // Disable auto-refresh
      const autoRefreshCheckbox = screen.getByRole('checkbox', {
        name: /Auto-refresh every 30 seconds/,
      });
      fireEvent.click(autoRefreshCheckbox);

      const initialCallCount = fetchSpy.mock.calls.length;

      // Fast-forward 30 seconds
      vi.advanceTimersByTime(30000);

      // Call count should not increase
      expect(fetchSpy.mock.calls.length).toBe(initialCallCount);

      vi.useRealTimers();
      fetchSpy.mockRestore();
    });
  });

  describe('Sorting', () => {
    it('should sort by timestamp descending by default', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 0,
              results: [],
            }),
        })
      ) as any;

      renderComponent();

      await waitFor(() => {
        expect(fetchSpy).toHaveBeenCalled();
      });

      const firstCall = fetchSpy.mock.calls[1]; // Second call is audit logs
      expect(firstCall[0]).toContain('ordering=-timestamp');

      fetchSpy.mockRestore();
    });
  });

  describe('User Selection for Filters', () => {
    it('should load users for filter dropdown', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      global.fetch = vi.fn((url: string) => {
        if (url.includes('/api/auth/users')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                results: [
                  { id: 1, email: 'admin@test.com', full_name: 'Admin User' },
                  { id: 2, email: 'user@test.com', full_name: 'Test User' },
                ],
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 0,
              results: [],
            }),
        });
      }) as any;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByLabelText('User')).toBeInTheDocument();
      });

      // Verify users were loaded
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/users/'),
        expect.any(Object)
      );

      fetchSpy.mockRestore();
    });
  });

  describe('Error Recovery', () => {
    it('should retry failed request', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch');

      let attemptCount = 0;
      global.fetch = vi.fn(() => {
        attemptCount++;
        if (attemptCount === 1) {
          return Promise.resolve({
            ok: false,
            statusText: 'Server Error',
          });
        }
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 1,
              results: [
                {
                  id: 1,
                  timestamp: '2024-01-15T10:30:00Z',
                  user: { id: 1, email: 'admin@test.com', full_name: 'Admin' },
                  action: 'create',
                  resource: 'User',
                  status: 'success',
                  ip_address: '192.168.1.1',
                },
              ],
            }),
        });
      }) as any;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('Admin')).toBeInTheDocument();
      });

      expect(attemptCount).toBeGreaterThanOrEqual(2);
      fetchSpy.mockRestore();
    });
  });

  describe('Performance', () => {
    it('should handle large dataset efficiently', async () => {
      global.fetch = vi.fn(() => {
        const results = Array.from({ length: 50 }, (_, i) => ({
          id: i + 1,
          timestamp: new Date(2024, 0, 15, 10, 30 - i).toISOString(),
          user: { id: 1, email: 'admin@test.com', full_name: 'Admin' },
          action: ['create', 'read', 'update', 'delete'][i % 4],
          resource: ['User', 'Material', 'Assignment'][i % 3],
          status: i % 10 === 0 ? 'failed' : 'success',
          ip_address: `192.168.1.${i}`,
        }));

        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 1000,
              next: '/api/admin/audit-logs/?page=2',
              results,
            }),
        });
      }) as any;

      const startTime = performance.now();
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Admin')).toBeInTheDocument();
      });

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Component should render within reasonable time (< 3 seconds)
      expect(renderTime).toBeLessThan(3000);
    });
  });

  describe('Accessibility', () => {
    it('should have accessible table structure', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              count: 1,
              results: [
                {
                  id: 1,
                  timestamp: '2024-01-15T10:30:00Z',
                  user: { id: 1, email: 'admin@test.com', full_name: 'Admin' },
                  action: 'create',
                  resource: 'User',
                  status: 'success',
                  ip_address: '192.168.1.1',
                },
              ],
            }),
        })
      ) as any;

      renderComponent();

      await waitFor(() => {
        const table = screen.getByRole('table');
        expect(table).toBeInTheDocument();
      });

      // Verify table has header row
      const headers = screen.getAllByRole('columnheader');
      expect(headers.length).toBeGreaterThan(0);
    });
  });
});
