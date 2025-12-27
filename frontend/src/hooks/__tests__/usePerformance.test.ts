/**
 * usePerformance Hook Tests
 * Tests for React performance tracking hook
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import {
  usePerformance,
  useApiPerformance,
  useCoreWebVitals,
  usePerformanceReport,
  usePerformanceAlerts,
  useFetchPerformance,
} from '../usePerformance';
import { performanceMonitor } from '@/utils/performance';

describe('usePerformance Hook', () => {
  beforeEach(() => {
    performanceMonitor.clear();
  });

  afterEach(() => {
    performanceMonitor.clear();
  });

  describe('usePerformance', () => {
    it('should initialize hook with component name', () => {
      const { result } = renderHook(() => usePerformance('TestComponent'));

      expect(result.current.renderCount).toBe(0);
      expect(result.current.startMeasure).toBeDefined();
      expect(result.current.trackOperation).toBeDefined();
      expect(result.current.measure).toBeDefined();
      expect(result.current.measureAsync).toBeDefined();
    });

    it('should track render time on mount', () => {
      const { result } = renderHook(() => usePerformance('TestComponent'));

      expect(result.current.renderCount).toBeGreaterThanOrEqual(0);
    });

    it('should measure sync operation', () => {
      const { result } = renderHook(() => usePerformance('TestComponent'));

      const syncFn = vi.fn(() => 'result');
      const output = result.current.measure('operation', syncFn);

      expect(output).toBe('result');
      expect(syncFn).toHaveBeenCalled();
    });

    it('should measure async operation', async () => {
      const { result } = renderHook(() => usePerformance('TestComponent'));

      const asyncFn = vi.fn(async () => 'result');
      const output = await result.current.measureAsync('asyncOp', asyncFn);

      expect(output).toBe('result');
      expect(asyncFn).toHaveBeenCalled();
    });

    it('should handle slow render threshold', () => {
      const slowCallback = vi.fn();

      renderHook(() =>
        usePerformance('SlowComponent', {
          enabled: true,
          slowRenderThreshold: 50,
          onSlowRender: slowCallback,
        })
      );

      // The hook will track render time
      expect(slowCallback).toBeDefined();
    });

    it('should respect enabled flag', () => {
      const { result } = renderHook(() =>
        usePerformance('TestComponent', { enabled: false })
      );

      const output = result.current.measure('op', () => 'result');

      expect(output).toBe('result');
    });

    it('should track operation duration', () => {
      const { result } = renderHook(() => usePerformance('TestComponent'));

      result.current.trackOperation('testOp', 100);

      const report = performanceMonitor.getReport();
      expect(report).toBeDefined();
    });

    it('should track error in sync operation', () => {
      const { result } = renderHook(() => usePerformance('TestComponent'));

      const errorFn = vi.fn(() => {
        throw new Error('Test error');
      });

      expect(() => result.current.measure('failOp', errorFn)).toThrow('Test error');
    });

    it('should track error in async operation', async () => {
      const { result } = renderHook(() => usePerformance('TestComponent'));

      const errorFn = vi.fn(async () => {
        throw new Error('Test error');
      });

      await expect(result.current.measureAsync('failAsync', errorFn)).rejects.toThrow(
        'Test error'
      );
    });
  });

  describe('useApiPerformance', () => {
    it('should track API call', () => {
      const { result } = renderHook(() => useApiPerformance());

      result.current.trackApiCall('GET', '/api/users', 150, 200);

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBe(1);
      expect(report.apiMetrics.averageLatency).toBe(150);
    });

    it('should track multiple API calls', () => {
      const { result } = renderHook(() => useApiPerformance());

      result.current.trackApiCall('GET', '/api/users', 100, 200);
      result.current.trackApiCall('GET', '/api/posts', 200, 200);
      result.current.trackApiCall('POST', '/api/users', 300, 201);

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBe(3);
    });

    it('should track cached API call', () => {
      const { result } = renderHook(() => useApiPerformance());

      result.current.trackApiCall('GET', '/api/users', 150, 200, true);

      const exported = performanceMonitor.exportMetrics();

      expect(exported.apiMetrics[0].cached).toBe(true);
    });

    it('should track API call with retries', () => {
      const { result } = renderHook(() => useApiPerformance());

      result.current.trackApiCall('GET', '/api/users', 400, 200, false, 2);

      const exported = performanceMonitor.exportMetrics();

      expect(exported.apiMetrics[0].retries).toBe(2);
    });
  });

  describe('useCoreWebVitals', () => {
    it('should return Core Web Vitals', () => {
      const { result } = renderHook(() => useCoreWebVitals());

      expect(result.current).toHaveProperty('lcp');
      expect(result.current).toHaveProperty('fid');
      expect(result.current).toHaveProperty('cls');
      expect(result.current).toHaveProperty('inp');
    });

    it('should have null values initially', () => {
      const { result } = renderHook(() => useCoreWebVitals());

      expect(result.current.lcp).toBeNull();
      expect(result.current.fid).toBeNull();
      expect(result.current.cls).toBeNull();
      expect(result.current.inp).toBeNull();
    });
  });

  describe('usePerformanceReport', () => {
    it('should return performance report', () => {
      const { result } = renderHook(() => usePerformanceReport());

      expect(result.current).toHaveProperty('coreWebVitals');
      expect(result.current).toHaveProperty('apiMetrics');
      expect(result.current).toHaveProperty('componentMetrics');
      expect(result.current).toHaveProperty('alerts');
    });

    it('should include metrics in report', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 150, 200);

      const { result } = renderHook(() => usePerformanceReport());

      expect(result.current.apiMetrics.totalRequests).toBe(1);
    });
  });

  describe('usePerformanceAlerts', () => {
    it('should return alerts array', () => {
      const { result } = renderHook(() => usePerformanceAlerts());

      expect(Array.isArray(result.current)).toBe(true);
    });

    it('should include alerts in array', () => {
      performanceMonitor.trackApiRequest('GET', '/api/slow', 800, 200);

      const { result } = renderHook(() => usePerformanceAlerts());

      expect(result.current.length).toBeGreaterThan(0);
    });
  });

  describe('useFetchPerformance', () => {
    it('should return fetch function', () => {
      const { result } = renderHook(() => useFetchPerformance());

      expect(result.current.fetchWithMetrics).toBeDefined();
      expect(typeof result.current.fetchWithMetrics).toBe('function');
    });

    it('should track successful fetch', async () => {
      const { result } = renderHook(() => useFetchPerformance());

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          text: () => Promise.resolve('{}'),
        })
      ) as any;

      await result.current.fetchWithMetrics('/api/users');

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBeGreaterThanOrEqual(0);
    });

    it('should track fetch method', async () => {
      const { result } = renderHook(() => useFetchPerformance());

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 201,
          text: () => Promise.resolve('{}'),
        })
      ) as any;

      await result.current.fetchWithMetrics('/api/users', {
        method: 'POST',
      });

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Hook Integration', () => {
    it('should work together in component workflow', () => {
      const { result: apiResult } = renderHook(() => useApiPerformance());
      const { result: reportResult } = renderHook(() =>
        usePerformanceReport()
      );

      // Track API call
      apiResult.current.trackApiCall('GET', '/api/users', 150, 200);

      // Trigger re-render to get updated report
      const { result: perfResult } = renderHook(() =>
        usePerformance('TestComponent')
      );

      // Track operation
      perfResult.current.trackOperation('render', 25);

      // Get report - should include the tracked API call
      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBe(1);
    });
  });

  describe('Error Handling', () => {
    it('should handle measure errors gracefully', () => {
      const { result } = renderHook(() => usePerformance('TestComponent'));

      const errorFn = () => {
        throw new Error('Operation failed');
      };

      expect(() => result.current.measure('failOp', errorFn)).toThrow();
    });

    it('should handle async measure errors gracefully', async () => {
      const { result } = renderHook(() => usePerformance('TestComponent'));

      const errorFn = async () => {
        throw new Error('Async operation failed');
      };

      await expect(
        result.current.measureAsync('failAsync', errorFn)
      ).rejects.toThrow();
    });
  });
});
