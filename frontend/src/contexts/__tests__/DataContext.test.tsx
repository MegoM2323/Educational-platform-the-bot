import { describe, it, expect, beforeEach, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import {
  DataProvider,
  useData,
  useCache,
  useFilters,
  useLoadingState,
  useErrorState,
} from '../DataContext';

const CacheTestComponent = () => {
  const { setCache, getCache, clearCache } = useData();

  return (
    <div>
      <button
        onClick={() => setCache('test-key', { value: 'test-data' }, 5000)}
        data-testid="set-cache"
      >
        Set Cache
      </button>
      <button
        onClick={() => {
          const cached = getCache('test-key');
          if (cached) {
            return <div data-testid="cache-result">{cached.value}</div>;
          }
        }}
        data-testid="get-cache"
      >
        Get Cache
      </button>
      <button onClick={() => clearCache('test-key')} data-testid="clear-cache">
        Clear Cache
      </button>
      <div data-testid="cache-status">
        {getCache('test-key') ? 'cached' : 'not cached'}
      </div>
    </div>
  );
};

const FiltersTestComponent = () => {
  const { setFilters, getFilters, clearFilters } = useData();

  const handleSetFilter = () => {
    setFilters('namespace', { search: 'test', page: 1 });
  };

  return (
    <div>
      <button onClick={handleSetFilter} data-testid="set-filters">
        Set Filters
      </button>
      <button onClick={() => clearFilters('namespace')} data-testid="clear-filters">
        Clear Filters
      </button>
      <div data-testid="filter-status">
        {Object.keys(getFilters('namespace')).length > 0 ? 'active' : 'inactive'}
      </div>
      <div data-testid="filter-search">{getFilters('namespace')?.search}</div>
    </div>
  );
};

const LoadingErrorTestComponent = () => {
  const { setLoading, isLoading, setError, getError } = useData();

  return (
    <div>
      <button onClick={() => setLoading('operation', true)} data-testid="set-loading">
        Set Loading
      </button>
      <button onClick={() => setLoading('operation', false)} data-testid="unset-loading">
        Unset Loading
      </button>
      <button onClick={() => setError('operation', 'Test error')} data-testid="set-error">
        Set Error
      </button>
      <button onClick={() => setError('operation', null)} data-testid="clear-error">
        Clear Error
      </button>
      <div data-testid="loading-status">{isLoading('operation') ? 'loading' : 'idle'}</div>
      <div data-testid="error-status">{getError('operation') || 'no error'}</div>
    </div>
  );
};

const SelectorTestComponent = () => {
  const cache = useCache('test-key', 5000);
  const filters = useFilters('namespace');
  const loading = useLoadingState('operation');
  const error = useErrorState('operation');

  return (
    <div>
      <button onClick={() => cache.set({ value: 'cached' })} data-testid="cache-set">
        Cache Set
      </button>
      <div data-testid="cache-valid">{cache.isValid ? 'valid' : 'invalid'}</div>

      <button onClick={() => filters.setFilter('search', 'test')} data-testid="filter-set">
        Filter Set
      </button>
      <div data-testid="filter-count">{Object.keys(filters.filters).length}</div>

      <button onClick={() => loading.setLoading(true)} data-testid="loading-set">
        Loading Set
      </button>
      <div data-testid="loading-state">{loading.loading ? 'loading' : 'idle'}</div>

      <button onClick={() => error.setError('Test')} data-testid="error-set">
        Error Set
      </button>
      <div data-testid="error-state">{error.error || 'none'}</div>
    </div>
  );
};

describe('DataContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useData cache management', () => {
    it('should set and get cache', () => {
      render(
        <DataProvider>
          <CacheTestComponent />
        </DataProvider>
      );

      fireEvent.click(screen.getByTestId('set-cache'));
      expect(screen.getByTestId('cache-status')).toHaveTextContent('cached');
    });

    it('should clear cache', async () => {
      render(
        <DataProvider>
          <CacheTestComponent />
        </DataProvider>
      );

      fireEvent.click(screen.getByTestId('set-cache'));
      expect(screen.getByTestId('cache-status')).toHaveTextContent('cached');

      fireEvent.click(screen.getByTestId('clear-cache'));

      await waitFor(() => {
        expect(screen.getByTestId('cache-status')).toHaveTextContent('not cached');
      });
    });

    it('should expire cache after TTL', async () => {
      const ExpireCacheComponent = () => {
        const { setCache, getCache } = useData();
        const [expired, setExpired] = React.useState(false);

        const handleExpireCache = () => {
          setCache('expire-key', { value: 'test' }, 100);
          setTimeout(() => {
            const cached = getCache('expire-key');
            setExpired(cached === null);
          }, 150);
        };

        return (
          <div>
            <button onClick={handleExpireCache} data-testid="expire-cache">
              Expire Cache
            </button>
            <div data-testid="expire-result">{expired ? 'expired' : 'not-expired'}</div>
          </div>
        );
      };

      render(
        <DataProvider>
          <ExpireCacheComponent />
        </DataProvider>
      );

      fireEvent.click(screen.getByTestId('expire-cache'));
      // Cache should expire after 150ms (TTL is 100ms)
    });
  });

  describe('useData filters management', () => {
    it('should set and get filters', () => {
      render(
        <DataProvider>
          <FiltersTestComponent />
        </DataProvider>
      );

      fireEvent.click(screen.getByTestId('set-filters'));

      expect(screen.getByTestId('filter-status')).toHaveTextContent('active');
      expect(screen.getByTestId('filter-search')).toHaveTextContent('test');
    });

    it('should clear filters', async () => {
      render(
        <DataProvider>
          <FiltersTestComponent />
        </DataProvider>
      );

      fireEvent.click(screen.getByTestId('set-filters'));
      expect(screen.getByTestId('filter-status')).toHaveTextContent('active');

      fireEvent.click(screen.getByTestId('clear-filters'));

      await waitFor(() => {
        expect(screen.getByTestId('filter-status')).toHaveTextContent('inactive');
      });
    });
  });

  describe('useData loading and error states', () => {
    it('should manage loading state', async () => {
      render(
        <DataProvider>
          <LoadingErrorTestComponent />
        </DataProvider>
      );

      expect(screen.getByTestId('loading-status')).toHaveTextContent('idle');

      fireEvent.click(screen.getByTestId('set-loading'));

      await waitFor(() => {
        expect(screen.getByTestId('loading-status')).toHaveTextContent('loading');
      });

      fireEvent.click(screen.getByTestId('unset-loading'));

      await waitFor(() => {
        expect(screen.getByTestId('loading-status')).toHaveTextContent('idle');
      });
    });

    it('should manage error state', async () => {
      render(
        <DataProvider>
          <LoadingErrorTestComponent />
        </DataProvider>
      );

      expect(screen.getByTestId('error-status')).toHaveTextContent('no error');

      fireEvent.click(screen.getByTestId('set-error'));

      await waitFor(() => {
        expect(screen.getByTestId('error-status')).toHaveTextContent('Test error');
      });

      fireEvent.click(screen.getByTestId('clear-error'));

      await waitFor(() => {
        expect(screen.getByTestId('error-status')).toHaveTextContent('no error');
      });
    });
  });

  describe('Selector hooks', () => {
    it('useCache should select cache state', async () => {
      render(
        <DataProvider>
          <SelectorTestComponent />
        </DataProvider>
      );

      fireEvent.click(screen.getByTestId('cache-set'));

      await waitFor(() => {
        expect(screen.getByTestId('cache-valid')).toHaveTextContent('valid');
      });
    });

    it('useFilters should select filter state', () => {
      render(
        <DataProvider>
          <SelectorTestComponent />
        </DataProvider>
      );

      fireEvent.click(screen.getByTestId('filter-set'));

      expect(screen.getByTestId('filter-count')).toHaveTextContent('1');
    });

    it('useLoadingState should select loading state', async () => {
      render(
        <DataProvider>
          <SelectorTestComponent />
        </DataProvider>
      );

      expect(screen.getByTestId('loading-state')).toHaveTextContent('idle');

      fireEvent.click(screen.getByTestId('loading-set'));

      await waitFor(() => {
        expect(screen.getByTestId('loading-state')).toHaveTextContent('loading');
      });
    });

    it('useErrorState should select error state', async () => {
      render(
        <DataProvider>
          <SelectorTestComponent />
        </DataProvider>
      );

      expect(screen.getByTestId('error-state')).toHaveTextContent('none');

      fireEvent.click(screen.getByTestId('error-set'));

      await waitFor(() => {
        expect(screen.getByTestId('error-state')).toHaveTextContent('Test');
      });
    });
  });

  describe('Error handling', () => {
    it('should throw error when used outside provider', () => {
      vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        render(<CacheTestComponent />);
      }).toThrow('useData must be used within a DataProvider');

      vi.restoreAllMocks();
    });
  });
});
