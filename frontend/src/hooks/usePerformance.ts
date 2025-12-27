/**
 * usePerformance Hook
 * React hook for tracking component render times and reporting to performance monitor
 *
 * Usage:
 * const { trackRender, startMeasure } = usePerformance('MyComponent');
 *
 * // In component mount/render
 * useEffect(() => {
 *   const stopMeasure = startMeasure();
 *   return () => stopMeasure();
 * }, [startMeasure]);
 */

import { useEffect, useRef, useCallback } from 'react';
import { performanceMonitor } from '@/utils/performance';

export interface UsePerformanceOptions {
  enabled?: boolean;
  onSlowRender?: (duration: number) => void;
  slowRenderThreshold?: number;
}

/**
 * Hook to measure component render time
 */
export const usePerformance = (
  componentName: string,
  options: UsePerformanceOptions = {}
) => {
  const {
    enabled = true,
    onSlowRender,
    slowRenderThreshold = 50,
  } = options;

  const startTimeRef = useRef<number | null>(null);
  const renderCountRef = useRef(0);

  /**
   * Start measuring render time
   */
  const startMeasure = useCallback(() => {
    if (!enabled) return () => {};

    startTimeRef.current = performance.now();

    return () => {
      if (startTimeRef.current === null) return;

      const duration = performance.now() - startTimeRef.current;
      renderCountRef.current++;

      const phase = renderCountRef.current === 1 ? 'mount' : 'update';

      // Track in performance monitor
      performanceMonitor.trackComponentRender(componentName, duration, phase);

      // Call callback if slow
      if (duration > slowRenderThreshold && onSlowRender) {
        onSlowRender(duration);
      }

      startTimeRef.current = null;
    };
  }, [componentName, enabled, onSlowRender, slowRenderThreshold]);

  /**
   * Track render time on effect
   */
  useEffect(() => {
    const stopMeasure = startMeasure();
    return stopMeasure;
  }, [startMeasure]);

  /**
   * Track custom operation
   */
  const trackOperation = useCallback(
    (operationName: string, duration: number) => {
      if (enabled) {
        performanceMonitor.addMetric(
          `${componentName}.${operationName}`,
          duration,
          'ms'
        );
      }
    },
    [componentName, enabled]
  );

  /**
   * Measure async operation
   */
  const measureAsync = useCallback(
    async <T,>(
      operationName: string,
      asyncFn: () => Promise<T>
    ): Promise<T> => {
      if (!enabled) {
        return asyncFn();
      }

      const startTime = performance.now();

      try {
        const result = await asyncFn();
        const duration = performance.now() - startTime;
        trackOperation(operationName, duration);
        return result;
      } catch (error) {
        const duration = performance.now() - startTime;
        trackOperation(`${operationName}_error`, duration);
        throw error;
      }
    },
    [enabled, trackOperation]
  );

  /**
   * Measure sync operation
   */
  const measure = useCallback(
    <T,>(
      operationName: string,
      syncFn: () => T
    ): T => {
      if (!enabled) {
        return syncFn();
      }

      const startTime = performance.now();

      try {
        const result = syncFn();
        const duration = performance.now() - startTime;
        trackOperation(operationName, duration);
        return result;
      } catch (error) {
        const duration = performance.now() - startTime;
        trackOperation(`${operationName}_error`, duration);
        throw error;
      }
    },
    [enabled, trackOperation]
  );

  return {
    startMeasure,
    trackOperation,
    measure,
    measureAsync,
    renderCount: renderCountRef.current,
  };
};

/**
 * Hook to track API calls within a component
 */
export const useApiPerformance = () => {
  const trackApiCall = useCallback(
    (
      method: string,
      endpoint: string,
      duration: number,
      status: number,
      cached = false,
      retries = 0
    ) => {
      performanceMonitor.trackApiRequest(
        method,
        endpoint,
        duration,
        status,
        cached,
        retries
      );
    },
    []
  );

  return { trackApiCall };
};

/**
 * Hook to get Core Web Vitals
 */
export const useCoreWebVitals = () => {
  return performanceMonitor.getCoreWebVitals();
};

/**
 * Hook to get performance report
 */
export const usePerformanceReport = () => {
  return performanceMonitor.getReport();
};

/**
 * Hook to monitor performance alerts
 */
export const usePerformanceAlerts = () => {
  return performanceMonitor.getAlerts();
};

/**
 * Hook to measure fetch requests
 */
export const useFetchPerformance = () => {
  const { trackApiCall } = useApiPerformance();

  const fetchWithMetrics = useCallback(
    async (
      input: RequestInfo | URL,
      init?: RequestInit
    ): Promise<Response> => {
      const startTime = performance.now();

      try {
        const response = await fetch(input, init);
        const duration = performance.now() - startTime;

        // Extract method and endpoint
        const url = typeof input === 'string' ? input : input.toString();
        const method = init?.method || 'GET';
        const endpoint = new URL(url, window.location.origin).pathname;

        trackApiCall(method, endpoint, duration, response.status);

        return response;
      } catch (error) {
        const duration = performance.now() - startTime;
        const url = typeof input === 'string' ? input : input.toString();
        const method = init?.method || 'GET';
        const endpoint = new URL(url, window.location.origin).pathname;

        trackApiCall(method, endpoint, duration, 0); // 0 = network error
        throw error;
      }
    },
    [trackApiCall]
  );

  return { fetchWithMetrics };
};

export default usePerformance;
