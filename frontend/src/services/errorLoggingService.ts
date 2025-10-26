// Error Logging and Reporting Service
// Provides centralized error logging, reporting, and analytics

export interface ErrorLogEntry {
  id: string;
  timestamp: string;
  level: 'error' | 'warning' | 'info' | 'debug';
  category: 'network' | 'auth' | 'validation' | 'server' | 'client' | 'websocket';
  message: string;
  stack?: string;
  context?: Record<string, any>;
  userAgent: string;
  url: string;
  userId?: string;
  sessionId: string;
  retryCount?: number;
  resolved?: boolean;
}

export interface ErrorAnalytics {
  totalErrors: number;
  errorsByCategory: Record<string, number>;
  errorsByLevel: Record<string, number>;
  recentErrors: ErrorLogEntry[];
  errorRate: number;
  resolutionRate: number;
}

class ErrorLoggingService {
  private logs: ErrorLogEntry[] = [];
  private maxLogs = 1000; // Maximum number of logs to keep in memory
  private sessionId: string;
  private userId: string | null = null;
  private isOnline: boolean = true;
  private pendingLogs: ErrorLogEntry[] = [];

  constructor() {
    this.sessionId = this.generateSessionId();
    this.setupOnlineDetection();
    this.setupErrorHandlers();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private setupOnlineDetection(): void {
    this.isOnline = navigator.onLine;
    
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.flushPendingLogs();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  private setupErrorHandlers(): void {
    // Global error handler for unhandled errors
    window.addEventListener('error', (event) => {
      this.logError({
        level: 'error',
        category: 'client',
        message: event.message,
        stack: event.error?.stack,
        context: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
      });
    });

    // Global handler for unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.logError({
        level: 'error',
        category: 'client',
        message: `Unhandled Promise Rejection: ${event.reason}`,
        stack: event.reason?.stack,
        context: {
          reason: event.reason,
        },
      });
    });
  }

  setUserId(userId: string | null): void {
    this.userId = userId;
  }

  logError(errorData: {
    level: 'error' | 'warning' | 'info' | 'debug';
    category: 'network' | 'auth' | 'validation' | 'server' | 'client' | 'websocket';
    message: string;
    stack?: string;
    context?: Record<string, any>;
    retryCount?: number;
  }): string {
    const logEntry: ErrorLogEntry = {
      id: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      level: errorData.level,
      category: errorData.category,
      message: errorData.message,
      stack: errorData.stack,
      context: errorData.context,
      userAgent: navigator.userAgent,
      url: window.location.href,
      userId: this.userId || undefined,
      sessionId: this.sessionId,
      retryCount: errorData.retryCount,
      resolved: false,
    };

    // Add to logs array
    this.logs.push(logEntry);
    
    // Keep only the most recent logs
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    // Send to server if online, otherwise queue for later
    if (this.isOnline) {
      this.sendLogToServer(logEntry);
    } else {
      this.pendingLogs.push(logEntry);
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.group(`🚨 ${errorData.level.toUpperCase()}: ${errorData.category}`);
      console.error('Message:', errorData.message);
      if (errorData.stack) console.error('Stack:', errorData.stack);
      if (errorData.context) console.error('Context:', errorData.context);
      console.groupEnd();
    }

    return logEntry.id;
  }

  private async sendLogToServer(logEntry: ErrorLogEntry): Promise<void> {
    try {
      // In a real application, you would send this to your logging service
      // For now, we'll just store it in localStorage for persistence
      const storedLogs = this.getStoredLogs();
      storedLogs.push(logEntry);
      
      // Keep only last 100 logs in localStorage
      const recentLogs = storedLogs.slice(-100);
      localStorage.setItem('error_logs', JSON.stringify(recentLogs));

      // Simulate sending to server (replace with actual API call)
      if (process.env.NODE_ENV === 'production') {
        // await fetch('/api/logs/error', {
        //   method: 'POST',
        //   headers: { 'Content-Type': 'application/json' },
        //   body: JSON.stringify(logEntry),
        // });
      }
    } catch (error) {
      console.error('Failed to send error log to server:', error);
    }
  }

  private getStoredLogs(): ErrorLogEntry[] {
    try {
      const stored = localStorage.getItem('error_logs');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

  private async flushPendingLogs(): Promise<void> {
    if (this.pendingLogs.length === 0) return;

    const logsToSend = [...this.pendingLogs];
    this.pendingLogs = [];

    for (const log of logsToSend) {
      await this.sendLogToServer(log);
    }
  }

  markErrorAsResolved(errorId: string): void {
    const logEntry = this.logs.find(log => log.id === errorId);
    if (logEntry) {
      logEntry.resolved = true;
    }
  }

  getErrorAnalytics(): ErrorAnalytics {
    const now = new Date();
    const last24Hours = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    
    const recentErrors = this.logs.filter(
      log => new Date(log.timestamp) > last24Hours
    );

    const errorsByCategory = recentErrors.reduce((acc, log) => {
      acc[log.category] = (acc[log.category] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const errorsByLevel = recentErrors.reduce((acc, log) => {
      acc[log.level] = (acc[log.level] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const resolvedErrors = recentErrors.filter(log => log.resolved).length;
    const resolutionRate = recentErrors.length > 0 ? resolvedErrors / recentErrors.length : 0;

    return {
      totalErrors: recentErrors.length,
      errorsByCategory,
      errorsByLevel,
      recentErrors: recentErrors.slice(-10), // Last 10 errors
      errorRate: recentErrors.length / 24, // Errors per hour
      resolutionRate,
    };
  }

  getLogsByCategory(category: string): ErrorLogEntry[] {
    return this.logs.filter(log => log.category === category);
  }

  getLogsByLevel(level: string): ErrorLogEntry[] {
    return this.logs.filter(log => log.level === level);
  }

  clearLogs(): void {
    this.logs = [];
    this.pendingLogs = [];
    localStorage.removeItem('error_logs');
  }

  exportLogs(): string {
    return JSON.stringify({
      sessionId: this.sessionId,
      userId: this.userId,
      timestamp: new Date().toISOString(),
      logs: this.logs,
    }, null, 2);
  }

  // Network error specific logging
  logNetworkError(error: Error, context?: Record<string, any>): string {
    return this.logError({
      level: 'error',
      category: 'network',
      message: `Network error: ${error.message}`,
      stack: error.stack,
      context: {
        ...context,
        networkType: navigator.connection?.effectiveType || 'unknown',
        onlineStatus: navigator.onLine,
      },
    });
  }

  // Authentication error specific logging
  logAuthError(error: Error, context?: Record<string, any>): string {
    return this.logError({
      level: 'error',
      category: 'auth',
      message: `Authentication error: ${error.message}`,
      stack: error.stack,
      context: {
        ...context,
        hasToken: !!localStorage.getItem('authToken'),
        hasRefreshToken: !!localStorage.getItem('refreshToken'),
      },
    });
  }

  // Validation error specific logging
  logValidationError(error: Error, context?: Record<string, any>): string {
    return this.logError({
      level: 'warning',
      category: 'validation',
      message: `Validation error: ${error.message}`,
      stack: error.stack,
      context,
    });
  }

  // Server error specific logging
  logServerError(error: Error, statusCode?: number, context?: Record<string, any>): string {
    return this.logError({
      level: 'error',
      category: 'server',
      message: `Server error: ${error.message}`,
      stack: error.stack,
      context: {
        ...context,
        statusCode,
      },
    });
  }

  // WebSocket error specific logging
  logWebSocketError(error: Error, context?: Record<string, any>): string {
    return this.logError({
      level: 'error',
      category: 'websocket',
      message: `WebSocket error: ${error.message}`,
      stack: error.stack,
      context: {
        ...context,
        readyState: 'WebSocket' in window ? 'available' : 'unavailable',
      },
    });
  }
}

// Export singleton instance
export const errorLoggingService = new ErrorLoggingService();

// Export class for testing
export { ErrorLoggingService };

