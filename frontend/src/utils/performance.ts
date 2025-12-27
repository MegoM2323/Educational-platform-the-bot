/**
 * Performance Monitoring Utility
 * Tracks Core Web Vitals, API latency, component render times, and memory usage.
 *
 * Features:
 * - Core Web Vitals tracking (LCP, FID, CLS)
 * - API response time measurement
 * - Component render time profiling
 * - Memory usage monitoring (development)
 * - User interaction latency tracking
 * - Performance budgets and alerts
 * - Real User Monitoring (RUM)
 * - Custom event tracking
 * - Historical trending
 *
 * Goals:
 * - LCP < 2.5s
 * - FID < 100ms
 * - CLS < 0.1
 * - API < 500ms
 */

import { logger } from './logger';

// Types
export interface PerformanceMetric {
  name: string;
  value: number;
  unit: string;
  timestamp: number;
  context?: Record<string, any>;
}

export interface CoreWebVitals {
  lcp: number | null;
  fid: number | null;
  cls: number | null;
  inp: number | null;
  fcpValue?: number;
  tlsValue?: number;
}

export interface ApiMetric {
  method: string;
  endpoint: string;
  duration: number;
  status: number;
  timestamp: number;
  cached?: boolean;
  retries?: number;
}

export interface ComponentMetric {
  componentName: string;
  renderTime: number;
  timestamp: number;
  phase?: 'mount' | 'update';
}

export interface MemoryMetric {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
  timestamp: number;
}

export interface PerformanceBudget {
  metric: string;
  threshold: number;
  unit: string;
}

export interface PerformanceAlert {
  metric: string;
  value: number;
  threshold: number;
  severity: 'warning' | 'error';
  timestamp: number;
}

// Configuration
interface PerformanceConfig {
  enabled: boolean;
  trackCoreWebVitals: boolean;
  trackApiMetrics: boolean;
  trackComponentMetrics: boolean;
  trackMemoryUsage: boolean;
  trackUserInteractions: boolean;
  debugMode: boolean;
  maxMetricsStored: number;
  reportingEndpoint?: string;
}

// Default budgets (in milliseconds)
const DEFAULT_BUDGETS: Record<string, PerformanceBudget> = {
  lcp: { metric: 'LCP', threshold: 2500, unit: 'ms' },
  fid: { metric: 'FID', threshold: 100, unit: 'ms' },
  cls: { metric: 'CLS', threshold: 0.1, unit: 'score' },
  inp: { metric: 'INP', threshold: 200, unit: 'ms' },
  api_default: { metric: 'API', threshold: 500, unit: 'ms' },
  api_get: { metric: 'API GET', threshold: 300, unit: 'ms' },
  api_post: { metric: 'API POST', threshold: 500, unit: 'ms' },
};

/**
 * Performance Monitor Class
 * Central monitoring hub for all performance metrics
 */
class PerformanceMonitor {
  private config: PerformanceConfig;
  private metrics: PerformanceMetric[] = [];
  private apiMetrics: ApiMetric[] = [];
  private componentMetrics: ComponentMetric[] = [];
  private memoryMetrics: MemoryMetric[] = [];
  private alerts: PerformanceAlert[] = [];
  private budgets: Map<string, PerformanceBudget>;
  private coreWebVitals: CoreWebVitals = {
    lcp: null,
    fid: null,
    cls: null,
    inp: null,
  };
  private observer: PerformanceObserver | null = null;
  private interactionObserver: PerformanceObserver | null = null;

  constructor(config: Partial<PerformanceConfig> = {}) {
    this.config = {
      enabled: true,
      trackCoreWebVitals: true,
      trackApiMetrics: true,
      trackComponentMetrics: true,
      trackMemoryUsage: import.meta.env.DEV,
      trackUserInteractions: true,
      debugMode: import.meta.env.DEV,
      maxMetricsStored: 500,
      ...config,
    };

    this.budgets = new Map(
      Object.entries(DEFAULT_BUDGETS).map(([key, value]) => [key, value])
    );

    if (this.config.enabled) {
      this.initialize();
    }
  }

  /**
   * Initialize performance monitoring
   */
  private initialize(): void {
    if (typeof window === 'undefined') return;

    this.logger('Initializing performance monitor');

    // Track Core Web Vitals
    if (this.config.trackCoreWebVitals) {
      this.setupCoreWebVitalsTracking();
    }

    // Track user interactions
    if (this.config.trackUserInteractions) {
      this.setupInteractionTracking();
    }

    // Track memory in development
    if (this.config.trackMemoryUsage) {
      this.setupMemoryTracking();
    }

    // Log initial page load
    this.trackPageLoad();
  }

  /**
   * Setup Core Web Vitals tracking using PerformanceObserver
   */
  private setupCoreWebVitalsTracking(): void {
    if (!('PerformanceObserver' in window)) {
      this.logger('PerformanceObserver not supported', 'warn');
      return;
    }

    try {
      // Track Largest Contentful Paint (LCP)
      this.observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];

        if ('renderTime' in lastEntry) {
          const lcpValue = (lastEntry as any).renderTime;
          this.coreWebVitals.lcp = lcpValue;
          this.addMetric('LCP', lcpValue, 'ms');

          if (this.isOverBudget('lcp', lcpValue)) {
            this.createAlert('LCP', lcpValue, DEFAULT_BUDGETS.lcp.threshold);
          }

          if (this.config.debugMode) {
            this.logger(`LCP: ${lcpValue.toFixed(2)}ms`, 'debug');
          }
        }
      });

      this.observer.observe({ entryTypes: ['largest-contentful-paint'] });

      // Track Cumulative Layout Shift (CLS)
      const clsObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();

        for (const entry of entries) {
          if ((entry as any).hadRecentInput) continue; // Ignore user input

          const clsValue = (entry as any).value || 0;
          this.coreWebVitals.cls = (this.coreWebVitals.cls || 0) + clsValue;
          this.addMetric('CLS', this.coreWebVitals.cls, 'score');

          if (this.isOverBudget('cls', this.coreWebVitals.cls)) {
            this.createAlert(
              'CLS',
              this.coreWebVitals.cls,
              DEFAULT_BUDGETS.cls.threshold
            );
          }

          if (this.config.debugMode) {
            this.logger(`CLS: ${this.coreWebVitals.cls.toFixed(3)}`, 'debug');
          }
        }
      });

      clsObserver.observe({ entryTypes: ['layout-shift'] });

      // Track First Contentful Paint (FCP)
      const fcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();

        for (const entry of entries) {
          const fcpValue = entry.startTime;
          if (entry.name === 'first-contentful-paint') {
            this.coreWebVitals.fcpValue = fcpValue;
            this.addMetric('FCP', fcpValue, 'ms');

            if (this.config.debugMode) {
              this.logger(`FCP: ${fcpValue.toFixed(2)}ms`, 'debug');
            }
          }
        }
      });

      fcpObserver.observe({ entryTypes: ['paint'] });

      // Use Web Vitals polyfill for older browsers (FID/INP)
      this.setupLegacyVitals();
    } catch (error) {
      this.logger('Failed to setup Core Web Vitals tracking', 'warn', error);
    }
  }

  /**
   * Setup legacy vitals for browsers without PerformanceObserver support
   */
  private setupLegacyVitals(): void {
    // Track First Input Delay (FID) - for older browsers
    if ('PerformanceObserver' in window) {
      try {
        const fidObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();

          for (const entry of entries) {
            if (entry.entryType === 'first-input') {
              const fidValue = (entry as any).processingDuration;
              this.coreWebVitals.fid = fidValue;
              this.addMetric('FID', fidValue, 'ms');

              if (this.isOverBudget('fid', fidValue)) {
                this.createAlert('FID', fidValue, DEFAULT_BUDGETS.fid.threshold);
              }

              if (this.config.debugMode) {
                this.logger(`FID: ${fidValue.toFixed(2)}ms`, 'debug');
              }
            }
          }
        });

        fidObserver.observe({
          entryTypes: ['first-input', 'measure'],
          buffered: true,
        });
      } catch (error) {
        this.logger('Failed to setup FID tracking', 'warn', error);
      }
    }
  }

  /**
   * Setup interaction latency tracking
   */
  private setupInteractionTracking(): void {
    if (!('PerformanceObserver' in window)) return;

    try {
      this.interactionObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();

        for (const entry of entries) {
          const duration = entry.duration;

          // Track as INP (Interaction to Next Paint)
          if (!this.coreWebVitals.inp || duration > this.coreWebVitals.inp) {
            this.coreWebVitals.inp = duration;
            this.addMetric('INP', duration, 'ms');

            if (this.isOverBudget('inp', duration)) {
              this.createAlert('INP', duration, DEFAULT_BUDGETS.inp.threshold);
            }
          }

          if (this.config.debugMode && duration > 100) {
            this.logger(`Interaction latency: ${duration.toFixed(2)}ms`, 'debug');
          }
        }
      });

      this.interactionObserver.observe({
        entryTypes: ['interaction'],
        buffered: true,
      });
    } catch (error) {
      this.logger('Failed to setup interaction tracking', 'warn', error);
    }
  }

  /**
   * Setup memory usage tracking (development only)
   */
  private setupMemoryTracking(): void {
    if (
      !('memory' in performance) ||
      !import.meta.env.DEV
    ) {
      return;
    }

    // Track memory every 30 seconds
    setInterval(() => {
      const memory = (performance as any).memory;

      if (memory) {
        this.memoryMetrics.push({
          usedJSHeapSize: memory.usedJSHeapSize,
          totalJSHeapSize: memory.totalJSHeapSize,
          jsHeapSizeLimit: memory.jsHeapSizeLimit,
          timestamp: Date.now(),
        });

        // Keep memory metrics limited
        if (this.memoryMetrics.length > this.config.maxMetricsStored) {
          this.memoryMetrics = this.memoryMetrics.slice(-this.config.maxMetricsStored);
        }

        if (this.config.debugMode) {
          const heapUsed = (memory.usedJSHeapSize / 1048576).toFixed(2);
          const heapLimit = (memory.jsHeapSizeLimit / 1048576).toFixed(2);
          this.logger(
            `Memory: ${heapUsed}MB / ${heapLimit}MB`,
            'debug'
          );
        }
      }
    }, 30000);
  }

  /**
   * Track API request metrics
   */
  trackApiRequest(
    method: string,
    endpoint: string,
    duration: number,
    status: number,
    cached: boolean = false,
    retries: number = 0
  ): void {
    if (!this.config.trackApiMetrics || !this.config.enabled) return;

    const metric: ApiMetric = {
      method,
      endpoint,
      duration,
      status,
      timestamp: Date.now(),
      cached,
      retries,
    };

    this.apiMetrics.push(metric);

    // Keep metrics limited
    if (this.apiMetrics.length > this.config.maxMetricsStored) {
      this.apiMetrics = this.apiMetrics.slice(-this.config.maxMetricsStored);
    }

    // Check against budget
    const budgetKey = `api_${method.toLowerCase()}`;
    const budget = this.budgets.get(budgetKey) || this.budgets.get('api_default');

    if (budget && duration > budget.threshold) {
      this.createAlert(
        `${method} ${endpoint}`,
        duration,
        budget.threshold,
        'warning'
      );
    }

    if (this.config.debugMode) {
      this.logger(
        `API ${method} ${endpoint}: ${duration.toFixed(2)}ms (${status})`,
        'debug'
      );
    }

    // Send to reporting endpoint if configured
    if (this.config.reportingEndpoint) {
      this.reportMetric({ name: `api_${method}`, value: duration, unit: 'ms', timestamp: Date.now() });
    }
  }

  /**
   * Track component render time
   */
  trackComponentRender(
    componentName: string,
    renderTime: number,
    phase: 'mount' | 'update' = 'mount'
  ): void {
    if (!this.config.trackComponentMetrics || !this.config.enabled) return;

    const metric: ComponentMetric = {
      componentName,
      renderTime,
      timestamp: Date.now(),
      phase,
    };

    this.componentMetrics.push(metric);

    // Keep metrics limited
    if (this.componentMetrics.length > this.config.maxMetricsStored) {
      this.componentMetrics = this.componentMetrics.slice(
        -this.config.maxMetricsStored
      );
    }

    // Alert if render is slow (> 50ms for mount, > 16ms for update)
    const threshold = phase === 'mount' ? 50 : 16;
    if (renderTime > threshold) {
      this.createAlert(
        `${componentName} render (${phase})`,
        renderTime,
        threshold,
        'warning'
      );
    }

    if (this.config.debugMode && renderTime > threshold) {
      this.logger(
        `${componentName} ${phase}: ${renderTime.toFixed(2)}ms`,
        'debug'
      );
    }
  }

  /**
   * Track JavaScript execution time
   */
  trackScriptExecution(scriptName: string, duration: number): void {
    if (!this.config.enabled) return;

    this.addMetric(`Script: ${scriptName}`, duration, 'ms');

    // Alert if script execution is slow (> 50ms)
    if (duration > 50) {
      this.createAlert(scriptName, duration, 50, 'warning');
    }

    if (this.config.debugMode && duration > 50) {
      this.logger(`Script execution ${scriptName}: ${duration.toFixed(2)}ms`);
    }
  }

  /**
   * Track page load time
   */
  private trackPageLoad(): void {
    if (typeof window === 'undefined') return;

    window.addEventListener('load', () => {
      const perfData = window.performance.timing;

      const pageLoadTime =
        perfData.loadEventEnd - perfData.navigationStart;
      const connectTime = perfData.responseEnd - perfData.requestStart;
      const renderTime = perfData.domComplete - perfData.domLoading;
      const domContentLoaded =
        perfData.domContentLoadedEventEnd - perfData.navigationStart;

      this.addMetric('Page Load Time', pageLoadTime, 'ms');
      this.addMetric('Connect Time', connectTime, 'ms');
      this.addMetric('Render Time', renderTime, 'ms');
      this.addMetric('DOM Content Loaded', domContentLoaded, 'ms');

      if (this.config.debugMode) {
        this.logger(`Page Load Performance:`, 'info');
        this.logger(`  - Total Load: ${pageLoadTime}ms`, 'debug');
        this.logger(`  - Connect: ${connectTime}ms`, 'debug');
        this.logger(`  - Render: ${renderTime}ms`, 'debug');
        this.logger(`  - DOM Ready: ${domContentLoaded}ms`, 'debug');
      }
    });
  }

  /**
   * Add custom metric
   */
  addMetric(name: string, value: number, unit: string, context?: Record<string, any>): void {
    if (!this.config.enabled) return;

    const metric: PerformanceMetric = {
      name,
      value,
      unit,
      timestamp: Date.now(),
      context,
    };

    this.metrics.push(metric);

    // Check against custom budgets
    if (this.isOverBudget(name, value)) {
      this.createAlert(name, value, this.budgets.get(name)?.threshold || 0);
    }

    // Keep metrics limited
    if (this.metrics.length > this.config.maxMetricsStored) {
      this.metrics = this.metrics.slice(-this.config.maxMetricsStored);
    }
  }

  /**
   * Check if metric is over budget
   */
  private isOverBudget(metricKey: string, value: number): boolean {
    const budget = this.budgets.get(metricKey);
    return budget ? value > budget.threshold : false;
  }

  /**
   * Create performance alert
   */
  private createAlert(
    metric: string,
    value: number,
    threshold: number,
    severity: 'warning' | 'error' = 'error'
  ): void {
    const alert: PerformanceAlert = {
      metric,
      value,
      threshold,
      severity,
      timestamp: Date.now(),
    };

    this.alerts.push(alert);

    // Keep alerts limited
    if (this.alerts.length > 100) {
      this.alerts = this.alerts.slice(-100);
    }

    const message = `Performance Alert: ${metric} = ${value.toFixed(2)} (threshold: ${threshold.toFixed(2)})`;
    this.logger(message, severity === 'error' ? 'error' : 'warn');

    // Send to reporting endpoint if configured
    if (this.config.reportingEndpoint) {
      this.reportAlert(alert);
    }
  }

  /**
   * Report metric to endpoint
   */
  private reportMetric(metric: PerformanceMetric): void {
    if (!this.config.reportingEndpoint) return;

    try {
      // Use sendBeacon for reliability
      if (navigator.sendBeacon) {
        navigator.sendBeacon(
          this.config.reportingEndpoint,
          JSON.stringify({ type: 'metric', data: metric })
        );
      }
    } catch (error) {
      this.logger('Failed to report metric', 'warn', error);
    }
  }

  /**
   * Report alert to endpoint
   */
  private reportAlert(alert: PerformanceAlert): void {
    if (!this.config.reportingEndpoint) return;

    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(
          this.config.reportingEndpoint,
          JSON.stringify({ type: 'alert', data: alert })
        );
      }
    } catch (error) {
      this.logger('Failed to report alert', 'warn', error);
    }
  }

  /**
   * Set custom performance budget
   */
  setBudget(metric: string, threshold: number, unit: string = 'ms'): void {
    this.budgets.set(metric, { metric, threshold, unit });
    this.logger(`Budget set: ${metric} = ${threshold}${unit}`);
  }

  /**
   * Get all Core Web Vitals
   */
  getCoreWebVitals(): CoreWebVitals {
    return { ...this.coreWebVitals };
  }

  /**
   * Get average API latency
   */
  getAverageApiLatency(method?: string): number {
    const metrics = method
      ? this.apiMetrics.filter((m) => m.method === method)
      : this.apiMetrics;

    if (metrics.length === 0) return 0;

    const total = metrics.reduce((sum, m) => sum + m.duration, 0);
    return total / metrics.length;
  }

  /**
   * Get API latency by method
   */
  getApiLatencyByMethod(): Record<string, number> {
    const result: Record<string, number> = {};

    const methods = new Set(this.apiMetrics.map((m) => m.method));

    for (const method of methods) {
      result[method] = this.getAverageApiLatency(method);
    }

    return result;
  }

  /**
   * Get average component render time
   */
  getAverageComponentRenderTime(componentName?: string): number {
    const metrics = componentName
      ? this.componentMetrics.filter((m) => m.componentName === componentName)
      : this.componentMetrics;

    if (metrics.length === 0) return 0;

    const total = metrics.reduce((sum, m) => sum + m.renderTime, 0);
    return total / metrics.length;
  }

  /**
   * Get memory stats
   */
  getMemoryStats(): {
    current: MemoryMetric | null;
    average: MemoryMetric | null;
    peak: MemoryMetric | null;
  } {
    if (this.memoryMetrics.length === 0) {
      return { current: null, average: null, peak: null };
    }

    const current = this.memoryMetrics[this.memoryMetrics.length - 1];

    const avgUsed =
      this.memoryMetrics.reduce((sum, m) => sum + m.usedJSHeapSize, 0) /
      this.memoryMetrics.length;
    const avgTotal =
      this.memoryMetrics.reduce((sum, m) => sum + m.totalJSHeapSize, 0) /
      this.memoryMetrics.length;
    const avgLimit =
      this.memoryMetrics.reduce((sum, m) => sum + m.jsHeapSizeLimit, 0) /
      this.memoryMetrics.length;

    const average: MemoryMetric = {
      usedJSHeapSize: avgUsed,
      totalJSHeapSize: avgTotal,
      jsHeapSizeLimit: avgLimit,
      timestamp: Date.now(),
    };

    const peak = this.memoryMetrics.reduce((max, m) =>
      m.usedJSHeapSize > max.usedJSHeapSize ? m : max
    );

    return { current, average, peak };
  }

  /**
   * Get all alerts
   */
  getAlerts(): PerformanceAlert[] {
    return [...this.alerts];
  }

  /**
   * Get alerts for specific metric
   */
  getAlertsForMetric(metric: string): PerformanceAlert[] {
    return this.alerts.filter((a) => a.metric.includes(metric));
  }

  /**
   * Get performance summary report
   */
  getReport(): {
    coreWebVitals: CoreWebVitals;
    apiMetrics: {
      totalRequests: number;
      averageLatency: number;
      byMethod: Record<string, number>;
    };
    componentMetrics: {
      totalComponents: number;
      averageRenderTime: number;
    };
    alerts: PerformanceAlert[];
  } {
    return {
      coreWebVitals: this.getCoreWebVitals(),
      apiMetrics: {
        totalRequests: this.apiMetrics.length,
        averageLatency: this.getAverageApiLatency(),
        byMethod: this.getApiLatencyByMethod(),
      },
      componentMetrics: {
        totalComponents: new Set(
          this.componentMetrics.map((m) => m.componentName)
        ).size,
        averageRenderTime: this.getAverageComponentRenderTime(),
      },
      alerts: this.getAlerts(),
    };
  }

  /**
   * Export metrics as JSON
   */
  exportMetrics(): {
    metrics: PerformanceMetric[];
    apiMetrics: ApiMetric[];
    componentMetrics: ComponentMetric[];
    memoryMetrics: MemoryMetric[];
  } {
    return {
      metrics: [...this.metrics],
      apiMetrics: [...this.apiMetrics],
      componentMetrics: [...this.componentMetrics],
      memoryMetrics: [...this.memoryMetrics],
    };
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics = [];
    this.apiMetrics = [];
    this.componentMetrics = [];
    this.memoryMetrics = [];
    this.alerts = [];
    this.coreWebVitals = {
      lcp: null,
      fid: null,
      cls: null,
      inp: null,
    };
    this.logger('All performance metrics cleared');
  }

  /**
   * Enable/disable monitoring
   */
  setEnabled(enabled: boolean): void {
    this.config.enabled = enabled;
    this.logger(`Performance monitoring ${enabled ? 'enabled' : 'disabled'}`);
  }

  /**
   * Internal logger
   */
  private logger(message: string, level: 'debug' | 'info' | 'warn' | 'error' = 'info', error?: any): void {
    if (!this.config.debugMode && level === 'debug') return;

    const prefix = '[Performance]';
    const logMessage = `${prefix} ${message}`;

    if (error) {
      logger[level](logMessage, error);
    } else {
      logger[level](logMessage);
    }
  }

  /**
   * Cleanup on page unload
   */
  destroy(): void {
    if (this.observer) {
      this.observer.disconnect();
    }

    if (this.interactionObserver) {
      this.interactionObserver.disconnect();
    }

    this.logger('Performance monitor destroyed');
  }
}

// Singleton instance
export const performanceMonitor = new PerformanceMonitor({
  enabled: true,
  trackCoreWebVitals: true,
  trackApiMetrics: true,
  trackComponentMetrics: true,
  trackMemoryUsage: import.meta.env.DEV,
  trackUserInteractions: true,
  debugMode: import.meta.env.DEV,
  reportingEndpoint: import.meta.env.VITE_PERFORMANCE_ENDPOINT,
});

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('unload', () => {
    performanceMonitor.destroy();
  });
}

export type {
  PerformanceConfig,
  PerformanceMetric,
  CoreWebVitals,
  ApiMetric,
  ComponentMetric,
  MemoryMetric,
  PerformanceBudget,
  PerformanceAlert,
};

export default performanceMonitor;
