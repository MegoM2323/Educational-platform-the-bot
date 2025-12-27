// Data Context для управления кешированием и фильтрами
import React, { createContext, useContext, useCallback, useMemo, ReactNode, useReducer } from 'react';
import { logger } from '@/utils/logger';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
}

interface DataState {
  cache: Record<string, CacheEntry<any>>;
  filters: Record<string, Record<string, any>>;
  loading: Record<string, boolean>;
  errors: Record<string, string | null>;
}

type DataAction =
  | { type: 'SET_CACHE'; payload: { key: string; data: any; ttl: number } }
  | { type: 'GET_CACHE'; payload: string }
  | { type: 'CLEAR_CACHE'; payload?: string }
  | { type: 'SET_FILTER'; payload: { namespace: string; filters: Record<string, any> } }
  | { type: 'CLEAR_FILTER'; payload: string }
  | { type: 'SET_LOADING'; payload: { key: string; loading: boolean } }
  | { type: 'SET_ERROR'; payload: { key: string; error: string | null } };

interface DataContextType {
  state: DataState;
  setCache: <T,>(key: string, data: T, ttl?: number) => void;
  getCache: <T,>(key: string) => T | null;
  isCacheValid: (key: string) => boolean;
  clearCache: (key?: string) => void;
  setFilters: (namespace: string, filters: Record<string, any>) => void;
  getFilters: (namespace: string) => Record<string, any>;
  clearFilters: (namespace: string) => void;
  setLoading: (key: string, loading: boolean) => void;
  isLoading: (key: string) => boolean;
  setError: (key: string, error: string | null) => void;
  getError: (key: string) => string | null;
}

const initialState: DataState = {
  cache: {},
  filters: {},
  loading: {},
  errors: {},
};

const DataContext = createContext<DataContextType | undefined>(undefined);

function dataReducer(state: DataState, action: DataAction): DataState {
  switch (action.type) {
    case 'SET_CACHE':
      return {
        ...state,
        cache: {
          ...state.cache,
          [action.payload.key]: {
            data: action.payload.data,
            timestamp: Date.now(),
            ttl: action.payload.ttl,
          },
        },
      };
    case 'GET_CACHE':
      return state; // Cache retrieval is handled in the hook
    case 'CLEAR_CACHE':
      if (action.payload) {
        const newCache = { ...state.cache };
        delete newCache[action.payload];
        return { ...state, cache: newCache };
      }
      return { ...state, cache: {} };
    case 'SET_FILTER':
      return {
        ...state,
        filters: {
          ...state.filters,
          [action.payload.namespace]: action.payload.filters,
        },
      };
    case 'CLEAR_FILTER':
      const newFilters = { ...state.filters };
      delete newFilters[action.payload];
      return { ...state, filters: newFilters };
    case 'SET_LOADING':
      return {
        ...state,
        loading: {
          ...state.loading,
          [action.payload.key]: action.payload.loading,
        },
      };
    case 'SET_ERROR':
      return {
        ...state,
        errors: {
          ...state.errors,
          [action.payload.key]: action.payload.error,
        },
      };
    default:
      return state;
  }
}

interface DataProviderProps {
  children: ReactNode;
}

export const DataProvider: React.FC<DataProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(dataReducer, initialState);

  const setCache = useCallback(<T,>(key: string, data: T, ttl = 300000) => {
    dispatch({ type: 'SET_CACHE', payload: { key, data, ttl } });
    logger.debug('[DataContext] Cache set:', key);
  }, []);

  const getCache = useCallback(<T,>(key: string): T | null => {
    const entry = state.cache[key];
    if (!entry) {
      return null;
    }

    // Check if cache has expired
    const age = Date.now() - entry.timestamp;
    if (age > entry.ttl) {
      dispatch({ type: 'CLEAR_CACHE', payload: key });
      logger.debug('[DataContext] Cache expired:', key);
      return null;
    }

    return entry.data as T;
  }, [state.cache]);

  const isCacheValid = useCallback((key: string): boolean => {
    const entry = state.cache[key];
    if (!entry) {
      return false;
    }
    const age = Date.now() - entry.timestamp;
    return age <= entry.ttl;
  }, [state.cache]);

  const clearCache = useCallback((key?: string) => {
    dispatch({ type: 'CLEAR_CACHE', payload: key });
    logger.debug('[DataContext] Cache cleared:', key || 'all');
  }, []);

  const setFilters = useCallback((namespace: string, filters: Record<string, any>) => {
    dispatch({ type: 'SET_FILTER', payload: { namespace, filters } });
    logger.debug('[DataContext] Filters set for namespace:', namespace);
  }, []);

  const getFilters = useCallback((namespace: string): Record<string, any> => {
    return state.filters[namespace] || {};
  }, [state.filters]);

  const clearFilters = useCallback((namespace: string) => {
    dispatch({ type: 'CLEAR_FILTER', payload: namespace });
    logger.debug('[DataContext] Filters cleared for namespace:', namespace);
  }, []);

  const setLoading = useCallback((key: string, loading: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: { key, loading } });
  }, []);

  const isLoading = useCallback((key: string): boolean => {
    return state.loading[key] ?? false;
  }, [state.loading]);

  const setError = useCallback((key: string, error: string | null) => {
    dispatch({ type: 'SET_ERROR', payload: { key, error } });
  }, []);

  const getError = useCallback((key: string): string | null => {
    return state.errors[key] ?? null;
  }, [state.errors]);

  const value: DataContextType = useMemo(
    () => ({
      state,
      setCache,
      getCache,
      isCacheValid,
      clearCache,
      setFilters,
      getFilters,
      clearFilters,
      setLoading,
      isLoading,
      setError,
      getError,
    }),
    [state, setCache, getCache, isCacheValid, clearCache, setFilters, getFilters, clearFilters, setLoading, isLoading, setError, getError]
  );

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
};

export const useData = (): DataContextType => {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
};

// Selectors to prevent re-renders
export const useCache = <T,>(key: string, ttl = 300000) => {
  const { getCache, setCache, isCacheValid, clearCache } = useData();
  return useMemo(
    () => ({
      data: getCache<T>(key),
      set: (data: T) => setCache(key, data, ttl),
      isValid: isCacheValid(key),
      clear: () => clearCache(key),
    }),
    [key, getCache, setCache, isCacheValid, clearCache, ttl]
  );
};

export const useFilters = (namespace: string) => {
  const { getFilters, setFilters, clearFilters } = useData();
  const filters = getFilters(namespace);

  return useMemo(
    () => ({
      filters,
      setFilters: (newFilters: Record<string, any>) => setFilters(namespace, newFilters),
      clearFilters: () => clearFilters(namespace),
      setFilter: (key: string, value: any) =>
        setFilters(namespace, { ...filters, [key]: value }),
      getFilter: (key: string) => filters[key],
      hasFilter: (key: string) => key in filters,
    }),
    [filters, namespace, setFilters, clearFilters]
  );
};

export const useLoadingState = (key: string) => {
  const { setLoading, isLoading, state } = useData();
  const loading = isLoading(key);

  return useMemo(
    () => ({
      loading,
      setLoading: (value: boolean) => setLoading(key, value),
    }),
    [key, loading, setLoading]
  );
};

export const useErrorState = (key: string) => {
  const { setError, getError, state } = useData();
  const error = getError(key);

  return useMemo(
    () => ({
      error,
      setError: (value: string | null) => setError(key, value),
      clearError: () => setError(key, null),
    }),
    [key, error, setError]
  );
};
