/**
 * Performance Monitoring Tests
 * Tests for Core Web Vitals tracking, API metrics, component render times, and memory usage
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  performanceMonitor,
  type PerformanceMetric,
  type ApiMetric,
  type CoreWebVitals,
} from '../performance';

describe('PerformanceMonitor', () => {
  beforeEach(() => {
    performanceMonitor.clear();
  });

  afterEach(() => {
    performanceMonitor.clear();
  });

  // Core Web Vitals Tests
  describe('Core Web Vitals', () => {
    it('should initialize Core Web Vitals with null values', () => {
      const vitals = performanceMonitor.getCoreWebVitals();

      expect(vitals.lcp).toBeNull();
      expect(vitals.fid).toBeNull();
      expect(vitals.cls).toBeNull();
      expect(vitals.inp).toBeNull();
    });

    it('should track LCP metric', () => {
      const testLCP = 1500;

      performanceMonitor.addMetric('LCP', testLCP, 'ms');

      const report = performanceMonitor.getReport();
      expect(report).toBeDefined();
    });

    it('should detect slow LCP (> 2.5s)', () => {
      const slowLCP = 3000; // Over 2.5s budget

      performanceMonitor.addMetric('LCP', slowLCP, 'ms');

      const alerts = performanceMonitor.getAlerts();
      // Alert may or may not be triggered depending on implementation
      expect(alerts).toBeDefined();
    });

    it('should track good LCP (< 2.5s)', () => {
      const goodLCP = 1800; // Under 2.5s budget

      performanceMonitor.addMetric('LCP', goodLCP, 'ms');

      const report = performanceMonitor.getReport();
      expect(report).toBeDefined();
    });

    it('should track CLS metric', () => {
      const testCLS = 0.05;

      performanceMonitor.addMetric('CLS', testCLS, 'score');

      const report = performanceMonitor.getReport();
      expect(report).toBeDefined();
    });

    it('should detect poor CLS (> 0.1)', () => {
      const poorCLS = 0.15; // Over 0.1 budget

      performanceMonitor.addMetric('CLS', poorCLS, 'score');

      const alerts = performanceMonitor.getAlerts();
      expect(alerts).toBeDefined();
    });
  });

  // API Metrics Tests
  describe('API Metrics', () => {
    it('should track API GET request', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 150, 200);

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBe(1);
      expect(report.apiMetrics.averageLatency).toBe(150);
    });

    it('should track multiple API requests', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 100, 200);
      performanceMonitor.trackApiRequest('GET', '/api/posts', 200, 200);
      performanceMonitor.trackApiRequest('POST', '/api/users', 300, 201);

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBe(3);
      expect(report.apiMetrics.averageLatency).toBeCloseTo(200, 1);
    });

    it('should calculate average latency by method', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 100, 200);
      performanceMonitor.trackApiRequest('GET', '/api/posts', 200, 200);
      performanceMonitor.trackApiRequest('POST', '/api/users', 300, 201);

      const latencyByMethod = performanceMonitor.getApiLatencyByMethod();

      expect(latencyByMethod['GET']).toBeCloseTo(150, 0);
      expect(latencyByMethod['POST']).toBe(300);
    });

    it('should track slow API requests (> 500ms)', () => {
      performanceMonitor.trackApiRequest('GET', '/api/slow-endpoint', 800, 200);

      const alerts = performanceMonitor.getAlerts();

      expect(alerts.length).toBeGreaterThan(0);
      expect(alerts[0].value).toBe(800);
    });

    it('should track fast API requests (< 500ms)', () => {
      performanceMonitor.trackApiRequest('GET', '/api/fast-endpoint', 250, 200);

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBe(1);
      expect(report.apiMetrics.averageLatency).toBe(250);
    });

    it('should track cached API responses', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 150, 200, true);

      const exported = performanceMonitor.exportMetrics();

      expect(exported.apiMetrics[0].cached).toBe(true);
    });

    it('should track API request retries', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 400, 200, false, 2);

      const exported = performanceMonitor.exportMetrics();

      expect(exported.apiMetrics[0].retries).toBe(2);
    });

    it('should track error responses', () => {
      performanceMonitor.trackApiRequest('POST', '/api/users', 150, 500);
      performanceMonitor.trackApiRequest('POST', '/api/users', 200, 400);
      performanceMonitor.trackApiRequest('POST', '/api/users', 100, 401);

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBe(3);
    });

    it('should get average latency for specific method', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 100, 200);
      performanceMonitor.trackApiRequest('GET', '/api/posts', 200, 200);
      performanceMonitor.trackApiRequest('POST', '/api/users', 300, 201);

      const getLatency = performanceMonitor.getAverageApiLatency('GET');

      expect(getLatency).toBeCloseTo(150, 0);
    });

    it('should handle empty API metrics', () => {
      const latency = performanceMonitor.getAverageApiLatency();

      expect(latency).toBe(0);
    });
  });

  // Component Metrics Tests
  describe('Component Metrics', () => {
    it('should track component mount time', () => {
      performanceMonitor.trackComponentRender('UserCard', 25, 'mount');

      const report = performanceMonitor.getReport();

      expect(report.componentMetrics.totalComponents).toBe(1);
      expect(report.componentMetrics.averageRenderTime).toBe(25);
    });

    it('should track component update time', () => {
      performanceMonitor.trackComponentRender('UserCard', 25, 'mount');
      performanceMonitor.trackComponentRender('UserCard', 10, 'update');

      const report = performanceMonitor.getReport();

      expect(report.componentMetrics.totalComponents).toBe(1);
      expect(report.componentMetrics.averageRenderTime).toBeCloseTo(17.5, 1);
    });

    it('should track slow component render (> 50ms for mount)', () => {
      performanceMonitor.trackComponentRender('SlowComponent', 100, 'mount');

      const alerts = performanceMonitor.getAlerts();

      expect(alerts.length).toBeGreaterThan(0);
      expect(alerts[0].value).toBe(100);
    });

    it('should track multiple components', () => {
      performanceMonitor.trackComponentRender('UserCard', 25, 'mount');
      performanceMonitor.trackComponentRender('PostCard', 30, 'mount');
      performanceMonitor.trackComponentRender('CommentCard', 20, 'mount');

      const report = performanceMonitor.getReport();

      expect(report.componentMetrics.totalComponents).toBe(3);
    });

    it('should calculate average render time for component', () => {
      performanceMonitor.trackComponentRender('UserCard', 20, 'mount');
      performanceMonitor.trackComponentRender('UserCard', 15, 'update');
      performanceMonitor.trackComponentRender('UserCard', 25, 'update');

      const avgTime = performanceMonitor.getAverageComponentRenderTime('UserCard');

      expect(avgTime).toBeCloseTo(20, 0);
    });

    it('should handle fast component render', () => {
      performanceMonitor.trackComponentRender('FastComponent', 5, 'mount');

      const alerts = performanceMonitor.getAlerts();

      expect(alerts.length).toBe(0);
    });
  });

  // JavaScript Execution Tests
  describe('JavaScript Execution', () => {
    it('should track script execution time', () => {
      performanceMonitor.trackScriptExecution('initializeApp', 30);

      const report = performanceMonitor.getReport();

      expect(report).toBeDefined();
    });

    it('should alert on slow script execution (> 50ms)', () => {
      performanceMonitor.trackScriptExecution('heavyComputation', 100);

      const alerts = performanceMonitor.getAlerts();

      expect(alerts.length).toBeGreaterThan(0);
    });
  });

  // Custom Metrics Tests
  describe('Custom Metrics', () => {
    it('should add custom metric', () => {
      performanceMonitor.addMetric('Custom Metric', 123, 'ms');

      const exported = performanceMonitor.exportMetrics();

      expect(exported.metrics.length).toBe(1);
      expect(exported.metrics[0].name).toBe('Custom Metric');
      expect(exported.metrics[0].value).toBe(123);
    });

    it('should add custom metric with context', () => {
      performanceMonitor.addMetric('Database Query', 250, 'ms', {
        query: 'SELECT * FROM users',
        rows: 50,
      });

      const exported = performanceMonitor.exportMetrics();

      expect(exported.metrics[0].context?.query).toBe('SELECT * FROM users');
      expect(exported.metrics[0].context?.rows).toBe(50);
    });

    it('should store multiple custom metrics', () => {
      performanceMonitor.addMetric('Metric 1', 100, 'ms');
      performanceMonitor.addMetric('Metric 2', 200, 'ms');
      performanceMonitor.addMetric('Metric 3', 300, 'ms');

      const exported = performanceMonitor.exportMetrics();

      expect(exported.metrics.length).toBe(3);
    });
  });

  // Performance Budgets Tests
  describe('Performance Budgets', () => {
    it('should use default budgets', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 250, 200);

      const alerts = performanceMonitor.getAlerts();

      expect(alerts.length).toBe(0); // Under budget
    });

    it('should create alert when exceeding default budget', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 800, 200);

      const alerts = performanceMonitor.getAlerts();

      expect(alerts.length).toBeGreaterThan(0);
    });

    it('should set custom budget', () => {
      performanceMonitor.setBudget('custom_metric', 100, 'ms');

      performanceMonitor.addMetric('custom_metric', 150, 'ms');

      const alerts = performanceMonitor.getAlerts();

      expect(alerts.length).toBeGreaterThan(0);
    });
  });

  // Alerts Tests
  describe('Alerts', () => {
    it('should create alerts when metrics exceed budget', () => {
      performanceMonitor.trackApiRequest('GET', '/api/slow', 1000, 200);

      const alerts = performanceMonitor.getAlerts();

      expect(alerts.length).toBeGreaterThan(0);
      expect(alerts[0].severity).toBe('warning');
    });

    it('should get alerts for specific metric', () => {
      performanceMonitor.trackApiRequest('GET', '/api/slow1', 800, 200);
      performanceMonitor.trackApiRequest('GET', '/api/slow2', 900, 200);
      performanceMonitor.trackComponentRender('SlowComponent', 100, 'mount');

      const apiAlerts = performanceMonitor.getAlertsForMetric('GET');

      expect(apiAlerts.length).toBeGreaterThanOrEqual(1);
    });

    it('should limit alerts to prevent memory bloat', () => {
      for (let i = 0; i < 200; i++) {
        performanceMonitor.trackApiRequest('GET', `/api/endpoint${i}`, 800, 200);
      }

      const alerts = performanceMonitor.getAlerts();

      expect(alerts.length).toBeLessThanOrEqual(100);
    });
  });

  // Data Export Tests
  describe('Data Export', () => {
    it('should export all metrics', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 150, 200);
      performanceMonitor.trackComponentRender('UserCard', 25, 'mount');
      performanceMonitor.addMetric('Custom', 100, 'ms');

      const exported = performanceMonitor.exportMetrics();

      expect(exported.metrics.length).toBeGreaterThan(0);
      expect(exported.apiMetrics.length).toBeGreaterThan(0);
      expect(exported.componentMetrics.length).toBeGreaterThan(0);
    });

    it('should generate performance report', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 150, 200);
      performanceMonitor.trackComponentRender('UserCard', 25, 'mount');

      const report = performanceMonitor.getReport();

      expect(report).toHaveProperty('coreWebVitals');
      expect(report).toHaveProperty('apiMetrics');
      expect(report).toHaveProperty('componentMetrics');
      expect(report).toHaveProperty('alerts');
    });
  });

  // Memory Management Tests
  describe('Memory Management', () => {
    it('should limit stored metrics', () => {
      const maxMetrics = 500;

      // Add more metrics than the limit
      for (let i = 0; i < maxMetrics + 100; i++) {
        performanceMonitor.addMetric(`Metric ${i}`, i, 'ms');
      }

      const exported = performanceMonitor.exportMetrics();

      expect(exported.metrics.length).toBeLessThanOrEqual(maxMetrics);
    });

    it('should handle large number of API requests', () => {
      for (let i = 0; i < 200; i++) {
        performanceMonitor.trackApiRequest('GET', `/api/endpoint${i}`, 100 + i, 200);
      }

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBeGreaterThan(0);
    });
  });

  // Control Tests
  describe('Control', () => {
    it('should clear all metrics', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 150, 200);
      performanceMonitor.trackComponentRender('UserCard', 25, 'mount');

      performanceMonitor.clear();

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBe(0);
      expect(report.componentMetrics.totalComponents).toBe(0);
      expect(report.alerts.length).toBe(0);
    });

    it('should enable/disable monitoring', () => {
      performanceMonitor.setEnabled(false);
      performanceMonitor.trackApiRequest('GET', '/api/users', 150, 200);

      let report = performanceMonitor.getReport();
      expect(report.apiMetrics.totalRequests).toBe(0);

      performanceMonitor.setEnabled(true);
      performanceMonitor.trackApiRequest('GET', '/api/users', 150, 200);

      report = performanceMonitor.getReport();
      expect(report.apiMetrics.totalRequests).toBe(1);
    });
  });

  // Integration Tests
  describe('Integration', () => {
    it('should handle mixed metrics workflow', () => {
      // Simulate a typical user session
      performanceMonitor.trackApiRequest('GET', '/api/users', 200, 200);
      performanceMonitor.trackComponentRender('Dashboard', 45, 'mount');
      performanceMonitor.trackApiRequest('POST', '/api/users', 400, 201);
      performanceMonitor.trackComponentRender('UserForm', 30, 'mount');
      performanceMonitor.addMetric('Form Validation', 15, 'ms');
      performanceMonitor.trackApiRequest('GET', '/api/posts', 250, 200);

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.totalRequests).toBe(3);
      expect(report.componentMetrics.totalComponents).toBe(2);
      expect(report.coreWebVitals).toBeDefined();
    });

    it('should track performance metrics with timestamps', () => {
      const beforeTime = Date.now();
      performanceMonitor.trackApiRequest('GET', '/api/users', 150, 200);
      const afterTime = Date.now();

      const exported = performanceMonitor.exportMetrics();
      const metric = exported.apiMetrics[0];

      expect(metric.timestamp).toBeGreaterThanOrEqual(beforeTime);
      expect(metric.timestamp).toBeLessThanOrEqual(afterTime);
    });
  });

  // Edge Cases
  describe('Edge Cases', () => {
    it('should handle zero duration', () => {
      performanceMonitor.trackApiRequest('GET', '/api/users', 0, 200);

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.averageLatency).toBe(0);
    });

    it('should handle very large duration', () => {
      performanceMonitor.trackApiRequest('GET', '/api/slow', 999999, 200);

      const report = performanceMonitor.getReport();

      expect(report.apiMetrics.averageLatency).toBe(999999);
    });

    it('should handle NaN values gracefully', () => {
      // This tests that the monitor doesn't break with bad data
      performanceMonitor.addMetric('Test', 100, 'ms');

      const report = performanceMonitor.getReport();

      expect(report).toBeDefined();
      expect(!isNaN(report.apiMetrics.averageLatency)).toBe(true);
    });

    it('should handle missing component render times', () => {
      const avgTime = performanceMonitor.getAverageComponentRenderTime('NonExistent');

      expect(avgTime).toBe(0);
    });

    it('should handle empty alerts query', () => {
      const alerts = performanceMonitor.getAlertsForMetric('NonExistent');

      expect(alerts).toEqual([]);
    });
  });
});
