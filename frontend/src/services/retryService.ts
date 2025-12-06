// Retry Service for API Requests
// Provides intelligent retry mechanisms with exponential backoff and circuit breaker pattern

export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  backoffMultiplier: number;
  jitter: boolean;
  retryCondition: (error: any) => boolean;
}

export interface CircuitBreakerConfig {
  failureThreshold: number;
  recoveryTimeout: number;
  monitoringPeriod: number;
}

export interface RetryStats {
  totalAttempts: number;
  successfulAttempts: number;
  failedAttempts: number;
  averageRetryTime: number;
  lastFailureTime?: Date;
  circuitBreakerState: 'closed' | 'open' | 'half-open';
}

class RetryService {
  private retryConfig: RetryConfig;
  private circuitBreakerConfig: CircuitBreakerConfig;
  private stats: RetryStats;
  private failureCount: number = 0;
  private lastFailureTime?: Date;
  private circuitBreakerState: 'closed' | 'open' | 'half-open' = 'closed';

  constructor(
    retryConfig: Partial<RetryConfig> = {},
    circuitBreakerConfig: Partial<CircuitBreakerConfig> = {}
  ) {
    this.retryConfig = {
      maxRetries: 3,
      baseDelay: 1000,
      maxDelay: 10000,
      backoffMultiplier: 2,
      jitter: true,
      retryCondition: (error) => this.shouldRetry(error),
      ...retryConfig,
    };

    this.circuitBreakerConfig = {
      failureThreshold: 5,
      recoveryTimeout: 30000, // 30 seconds
      monitoringPeriod: 60000, // 1 minute
      ...circuitBreakerConfig,
    };

    this.stats = {
      totalAttempts: 0,
      successfulAttempts: 0,
      failedAttempts: 0,
      averageRetryTime: 0,
      circuitBreakerState: 'closed',
    };
  }

  private shouldRetry(error: any): boolean {
    // Don't retry if circuit breaker is open
    if (this.circuitBreakerState === 'open') {
      return false;
    }

    // Don't retry client errors (4xx) except 408, 429
    if (error?.status >= 400 && error?.status < 500) {
      return error?.status === 408 || error?.status === 429;
    }

    // Retry server errors (5xx) and network errors
    if (error?.status >= 500 || !error?.status) {
      return true;
    }

    // Retry timeout errors
    if (error?.name === 'TimeoutError' || error?.message?.includes('timeout')) {
      return true;
    }

    // Retry network errors
    if (error?.name === 'NetworkError' || error?.message?.includes('Network')) {
      return true;
    }

    return false;
  }

  private calculateDelay(attempt: number): number {
    let delay = this.retryConfig.baseDelay * Math.pow(this.retryConfig.backoffMultiplier, attempt - 1);
    delay = Math.min(delay, this.retryConfig.maxDelay);

    // Add jitter to prevent thundering herd
    if (this.retryConfig.jitter) {
      const jitter = Math.random() * 0.1 * delay;
      delay += jitter;
    }

    return Math.floor(delay);
  }

  private updateCircuitBreaker(success: boolean): void {
    if (success) {
      this.failureCount = 0;
      this.circuitBreakerState = 'closed';
    } else {
      this.failureCount++;
      this.lastFailureTime = new Date();

      if (this.failureCount >= this.circuitBreakerConfig.failureThreshold) {
        this.circuitBreakerState = 'open';
        logger.warn('Circuit breaker opened due to repeated failures');
      }
    }

    this.stats.circuitBreakerState = this.circuitBreakerState;
  }

  private async checkCircuitBreaker(): Promise<boolean> {
    if (this.circuitBreakerState === 'closed') {
      return true;
    }

    if (this.circuitBreakerState === 'open') {
      const timeSinceLastFailure = this.lastFailureTime 
        ? Date.now() - this.lastFailureTime.getTime()
        : 0;

      if (timeSinceLastFailure >= this.circuitBreakerConfig.recoveryTimeout) {
        this.circuitBreakerState = 'half-open';
        this.stats.circuitBreakerState = 'half-open';
        logger.debug('Circuit breaker moved to half-open state');
        return true;
      }

      return false;
    }

    // Half-open state - allow one request to test
    return true;
  }

  async executeWithRetry<T>(
    operation: () => Promise<T>,
    context?: string
  ): Promise<T> {
    const startTime = Date.now();
    let lastError: any;

    // Check circuit breaker
    if (!(await this.checkCircuitBreaker())) {
      throw new Error('Circuit breaker is open - service temporarily unavailable');
    }

    for (let attempt = 1; attempt <= this.retryConfig.maxRetries + 1; attempt++) {
      this.stats.totalAttempts++;

      try {
        const result = await operation();
        
        // Success - update stats and circuit breaker
        this.stats.successfulAttempts++;
        this.updateCircuitBreaker(true);
        
        const totalTime = Date.now() - startTime;
        this.stats.averageRetryTime = 
          (this.stats.averageRetryTime * (this.stats.successfulAttempts - 1) + totalTime) / 
          this.stats.successfulAttempts;

        if (attempt > 1) {
          logger.debug(`Operation succeeded on attempt ${attempt}${context ? ` (${context})` : ''}`);
        }

        return result;
      } catch (error) {
        lastError = error;
        this.stats.failedAttempts++;

        // Check if we should retry
        if (attempt <= this.retryConfig.maxRetries && this.retryConfig.retryCondition(error)) {
          const delay = this.calculateDelay(attempt);
          logger.warn(
            `Operation failed on attempt ${attempt}${context ? ` (${context})` : ''}, retrying in ${delay}ms:`,
            error
          );
          
          await this.sleep(delay);
        } else {
          // No more retries or error is not retryable
          this.updateCircuitBreaker(false);
          break;
        }
      }
    }

    // All retries exhausted
    this.updateCircuitBreaker(false);
    throw lastError;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Specific retry methods for different types of operations
  async retryApiCall<T>(
    apiCall: () => Promise<T>,
    context?: string
  ): Promise<T> {
    return this.executeWithRetry(apiCall, context);
  }

  async retryWebSocketConnection(
    connectionFn: () => WebSocket,
    context?: string
  ): Promise<WebSocket> {
    return this.executeWithRetry(() => {
      return new Promise((resolve, reject) => {
        try {
          const ws = connectionFn();
          
          ws.onopen = () => resolve(ws);
          ws.onerror = (error) => reject(new Error('WebSocket connection failed'));
          ws.onclose = (event) => {
            if (event.code !== 1000) {
              reject(new Error(`WebSocket closed unexpectedly: ${event.code}`));
            }
          };
        } catch (error) {
          reject(error);
        }
      });
    }, context);
  }

  async retryFileUpload<T>(
    uploadFn: () => Promise<T>,
    context?: string
  ): Promise<T> {
    // File uploads have different retry logic - longer delays
    const originalConfig = { ...this.retryConfig };
    this.retryConfig.baseDelay = 2000;
    this.retryConfig.maxDelay = 30000;

    try {
      return await this.executeWithRetry(uploadFn, context);
    } finally {
      this.retryConfig = originalConfig;
    }
  }

  // Health check for circuit breaker
  async healthCheck(): Promise<{
    isHealthy: boolean;
    stats: RetryStats;
    circuitBreakerState: string;
  }> {
    const isHealthy = this.circuitBreakerState !== 'open';
    
    return {
      isHealthy,
      stats: { ...this.stats },
      circuitBreakerState: this.circuitBreakerState,
    };
  }

  // Reset circuit breaker (for manual recovery)
  resetCircuitBreaker(): void {
    this.circuitBreakerState = 'closed';
    this.failureCount = 0;
    this.lastFailureTime = undefined;
    this.stats.circuitBreakerState = 'closed';
    logger.debug('Circuit breaker manually reset');
  }

  // Get current stats
  getStats(): RetryStats {
    return { ...this.stats };
  }

  // Update retry configuration
  updateRetryConfig(newConfig: Partial<RetryConfig>): void {
    this.retryConfig = { ...this.retryConfig, ...newConfig };
  }

  // Update circuit breaker configuration
  updateCircuitBreakerConfig(newConfig: Partial<CircuitBreakerConfig>): void {
    this.circuitBreakerConfig = { ...this.circuitBreakerConfig, ...newConfig };
  }
}

// Export singleton instance
export const retryService = new RetryService();

// Export class for custom instances
export { RetryService };

