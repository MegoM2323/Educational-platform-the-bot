// Performance Monitoring Service
// Tracks API response times, network performance, and system health

export interface PerformanceMetric {
  id: string;
  timestamp: string;
  type: 'api' | 'page' | 'component' | 'websocket';
  name: string;
  duration: number; // in milliseconds
  status: 'success' | 'error' | 'timeout';
  metadata?: Record<string, any>;
}

export interface PerformanceSummary {
  totalRequests: number;
  averageResponseTime: number;
  minResponseTime: number;
  maxResponseTime: number;
  successRate: number;
  errorRate: number;
  slowestRequests: Array<{
    name: string;
    duration: number;
    timestamp: string;
  }>;
}

class PerformanceMonitoringService {
  private metrics: PerformanceMetric[] = [];
  private maxMetrics = 1000;
  private activeTimers: Map<string, number> = new Map();

  startTimer(name: string): string {
    const id = `${name}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    this.activeTimers.set(id, performance.now());
    return id;
  }

  endTimer(id: string, metadata?: Record<string, any>): number {
    const startTime = this.activeTimers.get(id);
    if (!startTime) {
      console.warn(`Timer ${id} not found`);
      return 0;
    }

    const duration = performance.now() - startTime;
    this.activeTimers.delete(id);

    this.recordMetric({
      id,
      timestamp: new Date().toISOString(),
      type: 'api',
      name: id.split('_')[0],
      duration,
      status: 'success',
      metadata,
    });

    return duration;
  }

  recordAPICall(name: string, duration: number, status: 'success' | 'error' | 'timeout', metadata?: Record<string, any>): void {
    this.recordMetric({
      id: `${name}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      type: 'api',
      name,
      duration,
      status,
      metadata,
    });
  }

  recordPageLoad(pageName: string, duration: number, metadata?: Record<string, any>): void {
    this.recordMetric({
      id: `page_${pageName}_${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: 'page',
      name: pageName,
      duration,
      status: 'success',
      metadata,
    });
  }

  recordComponentRender(componentName: string, duration: number, metadata?: Record<string, any>): void {
    this.recordMetric({
      id: `component_${componentName}_${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: 'component',
      name: componentName,
      duration,
      status: 'success',
      metadata,
    });
  }

  recordWebSocketEvent(eventName: string, duration: number, status: 'success' | 'error', metadata?: Record<string, any>): void {
    this.recordMetric({
      id: `ws_${eventName}_${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: 'websocket',
      name: eventName,
      duration,
      status,
      metadata,
    });
  }

  private recordMetric(metric: PerformanceMetric): void {
    this.metrics.push(metric);

    // Keep only the most recent metrics
    if (this.metrics.length > this.maxMetrics) {
      this.metrics = this.metrics.slice(-this.maxMetrics);
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`📊 Performance: ${metric.name} - ${metric.duration.toFixed(2)}ms`);
    }

    // Send to server in production
    if (process.env.NODE_ENV === 'production' && metric.duration > 5000) {
      // Send slow requests to server for analysis
      this.sendSlowMetricToServer(metric);
    }
  }

  private async sendSlowMetricToServer(metric: PerformanceMetric): Promise<void> {
    try {
      // In a real application, you would send this to your monitoring service
      // await fetch('/api/monitoring/slow-request', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(metric),
      // });
    } catch (error) {
      console.error('Failed to send slow metric to server:', error);
    }
  }

  getMetricsByType(type: 'api' | 'page' | 'component' | 'websocket'): PerformanceMetric[] {
    return this.metrics.filter(m => m.type === type);
  }

  getMetricsByName(name: string): PerformanceMetric[] {
    return this.metrics.filter(m => m.name === name);
  }

  getRecentMetrics(limit: number = 50): PerformanceMetric[] {
    return this.metrics.slice(-limit);
  }

  getPerformanceSummary(timeWindow?: number): PerformanceSummary {
    let metricsToAnalyze = this.metrics;

    if (timeWindow) {
      const cutoff = Date.now() - timeWindow;
      metricsToAnalyze = this.metrics.filter(m => new Date(m.timestamp).getTime() > cutoff);
    }

    if (metricsToAnalyze.length === 0) {
      return {
        totalRequests: 0,
        averageResponseTime: 0,
        minResponseTime: 0,
        maxResponseTime: 0,
        successRate: 0,
        errorRate: 0,
        slowestRequests: [],
      };
    }

    const durations = metricsToAnalyze.map(m => m.duration);
    const successCount = metricsToAnalyze.filter(m => m.status === 'success').length;
    const errorCount = metricsToAnalyze.filter(m => m.status === 'error').length;

    const averageResponseTime = durations.reduce((a, b) => a + b, 0) / durations.length;
    const minResponseTime = Math.min(...durations);
    const maxResponseTime = Math.max(...durations);

    // Get 10 slowest requests
    const slowestRequests = [...metricsToAnalyze]
      .sort((a, b) => b.duration - a.duration)
      .slice(0, 10)
      .map(m => ({
        name: m.name,
        duration: m.duration,
        timestamp: m.timestamp,
      }));

    return {
      totalRequests: metricsToAnalyze.length,
      averageResponseTime: Math.round(averageResponseTime * 100) / 100,
      minResponseTime: Math.round(minResponseTime * 100) / 100,
      maxResponseTime: Math.round(maxResponseTime * 100) / 100,
      successRate: metricsToAnalyze.length > 0 ? (successCount / metricsToAnalyze.length) * 100 : 0,
      errorRate: metricsToAnalyze.length > 0 ? (errorCount / metricsToAnalyze.length) * 100 : 0,
      slowestRequests,
    };
  }

  getSlowRequests(threshold: number = 1000): PerformanceMetric[] {
    return this.metrics.filter(m => m.duration > threshold);
  }

  getFailedRequests(): PerformanceMetric[] {
    return this.metrics.filter(m => m.status === 'error' || m.status === 'timeout');
  }

  clearMetrics(): void {
    this.metrics = [];
  }

  exportMetrics(): string {
    return JSON.stringify({
      timestamp: new Date().toISOString(),
      summary: this.getPerformanceSummary(),
      metrics: this.metrics,
    }, null, 2);
  }

  // Web Vitals tracking
  trackWebVitals(): void {
    if (typeof window === 'undefined') return;

    // Track Largest Contentful Paint (LCP)
    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1] as any;
        
        this.recordMetric({
          id: `web-vitals-lcp_${Date.now()}`,
          timestamp: new Date().toISOString(),
          type: 'page',
          name: 'LCP',
          duration: lastEntry.renderTime || lastEntry.loadTime,
          status: lastEntry.renderTime < 2500 ? 'success' : 'error',
          metadata: {
            element: lastEntry.element?.tagName,
          },
        });
      });

      observer.observe({ type: 'largest-contentful-paint', buffered: true });
    } catch (e) {
      console.warn('Web Vitals LCP tracking not supported:', e);
    }

    // Track First Input Delay (FID)
    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry: any) => {
          this.recordMetric({
            id: `web-vitals-fid_${Date.now()}`,
            timestamp: new Date().toISOString(),
            type: 'component',
            name: 'FID',
            duration: entry.processingStart - entry.startTime,
            status: (entry.processingStart - entry.startTime) < 100 ? 'success' : 'error',
            metadata: {
              eventType: entry.name,
            },
          });
        });
      });

      observer.observe({ type: 'first-input', buffered: true });
    } catch (e) {
      console.warn('Web Vitals FID tracking not supported:', e);
    }
  }
}

// Export singleton instance
export const performanceMonitoringService = new PerformanceMonitoringService();

// Initialize Web Vitals tracking in browser
if (typeof window !== 'undefined') {
  performanceMonitoringService.trackWebVitals();
}

// Export class for testing
export { PerformanceMonitoringService };

