/**
 * Sentry error tracking configuration for React frontend.
 *
 * Integrates Sentry SDK with:
 * - React error boundaries
 * - Automatic error and performance monitoring
 * - User context attachment
 * - Source maps support
 * - Environment separation
 * - Custom error fingerprinting
 */

import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';

/**
 * Initialize Sentry SDK for React frontend.
 *
 * Should be called early in app initialization (before React mount).
 *
 * Environment variables:
 * - VITE_SENTRY_DSN: Sentry Data Source Name
 * - VITE_SENTRY_ENVIRONMENT: Environment (development, staging, production)
 * - VITE_SENTRY_TRACES_SAMPLE_RATE: Performance monitoring sample rate
 * - VITE_SENTRY_RELEASE: Release version
 * - VITE_DJANGO_API_URL: Backend API URL (for frontend-backend correlation)
 */
export function initSentry(): void {
  const sentryDSN = import.meta.env.VITE_SENTRY_DSN;
  const environment = import.meta.env.VITE_SENTRY_ENVIRONMENT || 'production';
  const release = import.meta.env.VITE_SENTRY_RELEASE || 'unknown';
  const apiUrl = import.meta.env.VITE_DJANGO_API_URL || 'http://localhost:8000';

  // Skip initialization if DSN is not configured
  if (!sentryDSN) {
    console.warn('[Sentry] DSN not configured - skipping initialization');
    return;
  }

  // Determine trace sample rate based on environment
  const tracesSampleRate = {
    development: 1.0,
    staging: 0.5,
    production: 0.1,
  }[environment] || 0.1;

  // Determine replays sample rate (session recording)
  const replaysSessionSampleRate = {
    development: 1.0,
    staging: 0.1,
    production: 0.01,
  }[environment] || 0.01;

  const replaysOnErrorSampleRate = {
    development: 1.0,
    staging: 0.5,
    production: 0.1,
  }[environment] || 0.1;

  Sentry.init({
    dsn: sentryDSN,
    environment,
    release,

    // Performance monitoring
    tracesSampleRate,

    // Session replays (record user session on errors)
    replaysSessionSampleRate,
    replaysOnErrorSampleRate,

    // Integration with React
    integrations: [
      new BrowserTracing({
        // Track React Router navigation
        routingInstrumentation: Sentry.reactRouterV6Instrumentation(
          window.history
        ),
        // Track fetch and XMLHttpRequest
        traceFetch: true,
        traceXHR: true,
        // Track performance metrics
        shouldCreateSpanForRequest: (url: string) => {
          // Skip tracking static assets and health checks
          const skipPatterns = [
            /\/static\//,
            /\/assets\//,
            /\/api\/system\/health/,
            /\.js$/,
            /\.css$/,
            /\.woff/,
            /\.png$/,
            /\.jpg$/,
            /\.svg$/,
          ];

          return !skipPatterns.some(pattern => pattern.test(url));
        },
      }),
      // Replay integration for debugging errors with video
      new Sentry.Replay({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],

    // Error filtering
    beforeSend(event, hint) {
      return filterError(event, hint, apiUrl);
    },

    beforeSendTransaction(event) {
      return filterTransaction(event, environment);
    },

    // Attach stack traces to all events
    attachStacktrace: true,

    // Ignore errors from common sources
    ignoreErrors: [
      // Browser extensions
      'top.GLOBALS',
      'chrome-extension://',
      'moz-extension://',

      // Common browser errors
      'NetworkError',
      'Network request failed',
      'Failed to fetch',
      'The user aborted a request',

      // Cross-origin errors
      'Script error',
      'ResizeObserver loop limit exceeded',

      // Ignored third-party scripts
      'Non-Error promise rejection captured',
    ],

    // Max breadcrumbs to capture
    maxBreadcrumbs: 50,

    // Sensitive data redaction
    allowUrls: [
      // Only capture errors from our app
      new RegExp('^' + window.location.origin),
    ],
  });

  console.log('[Sentry] Initialized successfully', {
    environment,
    tracesSampleRate,
    replaysSessionSampleRate,
  });
}

/**
 * Error filtering and redaction.
 *
 * - Redacts sensitive headers
 * - Filters low-priority errors
 * - Adds custom fingerprinting
 */
function filterError(
  event: Sentry.ErrorEvent,
  hint: Sentry.EventHint,
  apiUrl: string
): Sentry.ErrorEvent | null {
  // Skip rate limit errors
  const message = event.message || '';
  if (message.includes('429') || message.includes('Too Many Requests')) {
    return null;
  }

  // Skip transient network errors unless there's user context
  if (
    message.includes('NetworkError') ||
    message.includes('Failed to fetch') ||
    message.includes('Network request failed')
  ) {
    // Only send if error has meaningful context
    if (!event.user && !event.tags?.critical) {
      return null;
    }
  }

  // Redact sensitive headers
  if (event.request?.headers) {
    const sensitivePatterns = [
      'authorization',
      'cookie',
      'x-token',
      'x-api-key',
      'password',
    ];

    for (const header of Object.keys(event.request.headers)) {
      if (
        sensitivePatterns.some(pattern =>
          header.toLowerCase().includes(pattern)
        )
      ) {
        event.request.headers[header] = '[REDACTED]';
      }
    }
  }

  // Add fingerprinting for intelligent grouping
  addErrorFingerprint(event);

  return event;
}

/**
 * Transaction filtering for performance monitoring.
 *
 * - Sample based on response status
 * - Skip noise (successful requests in production)
 * - Add performance tags
 */
function filterTransaction(
  event: Sentry.TransactionEvent,
  environment: string
): Sentry.TransactionEvent | null {
  // Sample successful requests more aggressively in production
  if (event.status === 'ok' && environment === 'production') {
    if (Math.random() > 0.3) {
      return null;
    }
  }

  // Tag slow transactions
  const duration = event.measurements?.duration?.value || 0;
  if (duration > 3000) {
    if (!event.tags) {
      event.tags = {};
    }
    event.tags.performance_issue = 'slow_transaction';
  }

  return event;
}

/**
 * Add custom fingerprinting for intelligent error grouping.
 *
 * Groups similar errors even if stack traces differ.
 */
function addErrorFingerprint(event: Sentry.ErrorEvent): void {
  const fingerprint: string[] = [];

  // Get exception type
  const exceptions = event.exception?.values || [];
  if (exceptions.length === 0) return;

  const exception = exceptions[0];
  const excType = exception.type || 'Unknown';

  fingerprint.push(excType);

  // Special handling for common errors
  if (excType === 'TypeError' && exception.value) {
    const value = exception.value;

    if (value.includes('Cannot read property')) {
      // Group by property name
      const match = value.match(/Cannot read property '(\w+)'/);
      if (match) {
        fingerprint.push(`property_${match[1]}`);
      }
    } else if (value.includes('Cannot set property')) {
      const match = value.match(/Cannot set property '(\w+)'/);
      if (match) {
        fingerprint.push(`set_${match[1]}`);
      }
    }
  } else if (excType === 'ReferenceError') {
    // Group by undefined variable
    const value = exception.value;
    const match = value.match(/(\w+) is not defined/);
    if (match) {
      fingerprint.push(`undefined_${match[1]}`);
    }
  } else if (excType === 'SyntaxError') {
    // Group syntax errors by type
    const value = exception.value;
    if (value.includes('Unexpected token')) {
      fingerprint.push('unexpected_token');
    }
  } else if (excType === 'NetworkError' || event.request?.url) {
    // Group by endpoint, not exact path
    const url = event.request?.url || '';
    const path = url.split('?')[0]; // Remove query string
    const pathWithoutIds = path.replace(/\/\d+/g, '/{id}');
    fingerprint.push(pathWithoutIds);
  }

  // Set fingerprint if we have useful grouping
  if (fingerprint.length > 1) {
    event.fingerprint = fingerprint;
  } else {
    event.fingerprint = ['{{ default }}'];
  }
}

/**
 * Attach user context to Sentry events.
 *
 * Helps identify affected users and adds debugging context.
 *
 * Usage:
 * ```
 * attachUserContext({
 *   id: user.id,
 *   email: user.email,
 *   username: user.username,
 *   role: user.role,
 * });
 * ```
 */
export function attachUserContext(context: {
  id: string | number;
  email?: string;
  username?: string;
  role?: string;
}): void {
  Sentry.setUser({
    id: String(context.id),
    email: context.email,
    username: context.username,
    other: {
      role: context.role,
    },
  });
}

/**
 * Clear user context (e.g., on logout).
 */
export function clearUserContext(): void {
  Sentry.setUser(null);
}

/**
 * Add a breadcrumb to track user actions before an error.
 *
 * Breadcrumbs appear in error context and help understand what led to the error.
 *
 * Usage:
 * ```
 * addBreadcrumb('Form submitted', {
 *   category: 'user-action',
 *   data: { formName: 'login' },
 * });
 * ```
 */
export function addBreadcrumb(
  message: string,
  options?: {
    category?: string;
    level?: Sentry.SeverityLevel;
    data?: Record<string, any>;
  }
): void {
  Sentry.captureMessage(message, {
    level: options?.level || 'info',
    breadcrumb: {
      message,
      category: options?.category || 'default',
      level: options?.level || 'info',
      data: options?.data,
    },
  });
}

/**
 * Capture a custom message.
 *
 * Usage:
 * ```
 * captureMessage('Unusual condition detected', {
 *   level: 'warning',
 *   extra: { condition: 'high_error_rate' },
 * });
 * ```
 */
export function captureMessage(
  message: string,
  options?: {
    level?: Sentry.SeverityLevel;
    extra?: Record<string, any>;
  }
): void {
  Sentry.captureMessage(message, {
    level: options?.level || 'info',
    contexts: {
      custom: options?.extra,
    },
  });
}

/**
 * Capture an exception with additional context.
 *
 * Usage:
 * ```
 * try {
 *   riskyOperation();
 * } catch (error) {
 *   captureException(error, {
 *     extra: { operation: 'payment' },
 *     tags: { critical: 'true' },
 *   });
 * }
 * ```
 */
export function captureException(
  error: Error | any,
  options?: {
    extra?: Record<string, any>;
    tags?: Record<string, string>;
    level?: Sentry.SeverityLevel;
  }
): void {
  Sentry.withScope(scope => {
    if (options?.extra) {
      for (const [key, value] of Object.entries(options.extra)) {
        scope.setExtra(key, value);
      }
    }

    if (options?.tags) {
      for (const [key, value] of Object.entries(options.tags)) {
        scope.setTag(key, value);
      }
    }

    if (options?.level) {
      scope.setLevel(options.level);
    }

    Sentry.captureException(error);
  });
}

/**
 * Set a tag on current scope for error categorization.
 *
 * Tags help organize and filter errors in Sentry dashboard.
 *
 * Usage:
 * ```
 * setTag('payment_provider', 'yookassa');
 * setTag('feature', 'invoicing');
 * ```
 */
export function setTag(key: string, value: string): void {
  Sentry.setTag(key, value);
}

/**
 * React Error Boundary component for catching React errors.
 *
 * Usage in your app:
 * ```
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */
export const ErrorBoundary = Sentry.ErrorBoundary;

/**
 * HOC to wrap component for Sentry profiling.
 *
 * Usage:
 * ```
 * export default withProfiler(YourComponent, 'ComponentName');
 * ```
 */
export const withProfiler = Sentry.withProfiler;

/**
 * Create a React Router instrumentation for performance monitoring.
 *
 * This is already set up in initSentry(), but can be accessed here if needed.
 */
export function createRouterInstrumentation(history: any) {
  return Sentry.reactRouterV6Instrumentation(history);
}

/**
 * Get current Sentry client for advanced operations.
 *
 * Avoid using directly - prefer the exported functions above.
 */
export function getSentryClient() {
  return Sentry.getClient();
}

/**
 * Check if Sentry is initialized and enabled.
 */
export function isSentryEnabled(): boolean {
  const client = getSentryClient();
  return client !== undefined && client.isEnabled();
}

/**
 * Performance monitoring utilities.
 */
export const performance = {
  /**
   * Start a custom span for performance tracking.
   *
   * Usage:
   * ```
   * const span = performance.startSpan({ op: 'db.query' });
   * // ... do work ...
   * span.end();
   * ```
   */
  startSpan(options: { op: string; description?: string; name?: string }) {
    return Sentry.startSpan(options, () => {
      return {};
    });
  },

  /**
   * Measure execution time of a function.
   *
   * Usage:
   * ```
   * await performance.measure('fetch_data', async () => {
   *   return fetchFromAPI();
   * });
   * ```
   */
  async measure(
    name: string,
    fn: () => Promise<any> | any
  ): Promise<any> {
    const start = performance.now();
    try {
      const result = await fn();
      const duration = performance.now() - start;
      setTag('measured_operation', name);
      captureMessage(`Operation '${name}' took ${duration.toFixed(2)}ms`, {
        level: 'debug',
      });
      return result;
    } catch (error) {
      const duration = performance.now() - start;
      captureException(error, {
        extra: { operation: name, duration },
        tags: { measured_operation: name },
      });
      throw error;
    }
  },
};

export default {
  initSentry,
  attachUserContext,
  clearUserContext,
  addBreadcrumb,
  captureMessage,
  captureException,
  setTag,
  ErrorBoundary,
  withProfiler,
  isSentryEnabled,
  performance,
};
