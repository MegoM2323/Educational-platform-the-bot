# Error Handling Implementation Guide

This document describes the comprehensive error handling system implemented in the THE_BOT platform frontend.

## Overview

The frontend error handling system provides:

- **Error Boundaries**: Catch React component render errors
- **Error Logging**: Centralized error tracking and analytics
- **User-Friendly Messages**: Error recovery options for users
- **Error Recovery**: Retry mechanisms and graceful degradation
- **Network Monitoring**: Offline detection and recovery
- **Error Analytics**: Track error patterns and metrics

## Architecture

### Component Hierarchy

```
App
└── ErrorHandlingProvider
    ├── ErrorBoundary (root level)
    │   ├── NotificationProvider
    │   ├── NetworkStatusHandler
    │   └── Routes (with lazy-loaded components)
    │       └── ErrorBoundary (per route section)
    └── QueryClientProvider
```

## Core Components

### 1. ErrorBoundary

**Location**: `frontend/src/components/ErrorBoundary.tsx`

Error boundary component that catches React rendering errors and provides fallback UI.

#### Features

- Catches component render errors
- Displays user-friendly error messages
- Logs errors with stack traces
- Provides recovery actions (retry, go home)
- Custom fallback UI support
- Development mode error details

#### Usage

```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';

// Basic usage
<ErrorBoundary>
  <MyComponent />
</ErrorBoundary>

// With custom fallback
<ErrorBoundary fallback={<CustomErrorUI />}>
  <MyComponent />
</ErrorBoundary>

// With error handler callback
<ErrorBoundary onError={(error, errorInfo) => {
  console.log('Error caught:', error, errorInfo);
}}>
  <MyComponent />
</ErrorBoundary>
```

#### Error Handler Hook

```tsx
import { useErrorHandler } from '@/components/ErrorBoundary';

function MyComponent() {
  const { captureError, resetError } = useErrorHandler();

  const handleAsyncError = async () => {
    try {
      await riskyOperation();
    } catch (error) {
      captureError(error as Error);
    }
  };

  return (
    <button onClick={handleAsyncError}>Perform Action</button>
  );
}
```

### 2. ErrorHandlingProvider

**Location**: `frontend/src/components/ErrorHandlingProvider.tsx`

Provider component that sets up all error handling infrastructure.

#### Features

- Integrates error boundary at root level
- Sets up global error handlers
- Monitors network status
- Provides error reporting hooks
- Manages retry strategies
- Supports error logging service

#### Usage

```tsx
import { ErrorHandlingProvider, useErrorHandling, useErrorReporter } from '@/components/ErrorHandlingProvider';

// Access error handling context
function MyComponent() {
  const { reportError, getErrorStats, resetErrorStats } = useErrorHandling();

  const handleError = () => {
    reportError(new Error('Something went wrong'));
  };

  return <button onClick={handleError}>Report Error</button>;
}

// Use error reporter hook
function ReportingComponent() {
  const { reportError, reportNetworkError, reportAuthError } = useErrorReporter();

  return (
    <div>
      <button onClick={() => reportError(new Error('General error'))}>
        Report Error
      </button>
    </div>
  );
}

// Use retry hook
function RetryComponent() {
  const { retryApiCall, retryWebSocketConnection } = useRetry();

  const fetchData = async () => {
    try {
      const result = await retryApiCall(
        () => fetch('/api/data'),
        'fetchData'
      );
      return result;
    } catch (error) {
      console.error('Failed after retries:', error);
    }
  };

  return <button onClick={fetchData}>Fetch Data</button>;
}
```

### 3. Error Logging Service

**Location**: `frontend/src/services/errorLoggingService.ts`

Centralized error logging and analytics service.

#### Features

- In-memory error log storage (max 1000 logs)
- Local storage persistence
- Session tracking
- Error categorization
- Error analytics (24-hour window)
- Pending log queue for offline mode

#### Error Categories

- `network`: Network connectivity errors
- `auth`: Authentication/authorization errors
- `validation`: Form validation errors
- `server`: Server-side errors (5xx)
- `client`: Client-side errors
- `websocket`: WebSocket connection errors

#### Usage

```tsx
import { errorLoggingService } from '@/services/errorLoggingService';

// Log an error
const errorId = errorLoggingService.logError({
  level: 'error',
  category: 'network',
  message: 'Failed to fetch user data',
  stack: error.stack,
  context: {
    userId: 123,
    endpoint: '/api/users'
  }
});

// Get analytics
const analytics = errorLoggingService.getErrorAnalytics();
console.log('Total errors:', analytics.totalErrors);
console.log('By category:', analytics.errorsByCategory);
console.log('By level:', analytics.errorsByLevel);
console.log('Error rate (per hour):', analytics.errorRate);
console.log('Resolution rate:', analytics.resolutionRate);

// Specific error type logging
errorLoggingService.logNetworkError(error, { endpoint: '/api/data' });
errorLoggingService.logAuthError(error, { operation: 'login' });
errorLoggingService.logValidationError(error, { form: 'profile' });
errorLoggingService.logServerError(error, 500, { endpoint: '/api/data' });
errorLoggingService.logWebSocketError(error, { url: 'wss://api.example.com' });

// Mark error as resolved
errorLoggingService.markErrorAsResolved(errorId);

// Export logs
const logJson = errorLoggingService.exportLogs();

// Clear logs
errorLoggingService.clearLogs();
```

### 4. Error Handling Service

**Location**: `frontend/src/services/errorHandlingService.ts`

Service that provides user-friendly error messages and recovery options.

#### Features

- Error categorization
- User-friendly message generation
- Recovery action suggestions
- Error severity assessment
- Notification integration
- Support contact functionality

#### Error Severity Levels

- `low`: Minor issues, no action required
- `medium`: User action may be needed (validation errors)
- `high`: Important issues (network, auth)
- `critical`: System-critical errors (server errors)

#### Usage

```tsx
import { errorHandlingService } from '@/services/errorHandlingService';

// Handle error with user-friendly message
const userFriendlyError = errorHandlingService.handleError(
  error,
  {
    operation: 'fetch_materials',
    component: 'MaterialsList',
    userId: '123',
    retryAction: () => fetchMaterials(),
    customMessage: 'Custom error message'
  }
);

// Check error properties
console.log(userFriendlyError.title); // "Проблема с подключением"
console.log(userFriendlyError.message); // User-friendly message
console.log(userFriendlyError.severity); // 'high'
console.log(userFriendlyError.canRetry); // true
console.log(userFriendlyError.recoveryOptions); // Array of recovery actions

// Specific error handlers
errorHandlingService.handleNetworkError(error, retryFn);
errorHandlingService.handleAuthError(error, retryFn);
errorHandlingService.handleValidationError(error, retryFn);
errorHandlingService.handleServerError(error, retryFn);
errorHandlingService.handleWebSocketError(error, retryFn);

// Utility methods
const isRetryable = errorHandlingService.isRetryableError(error);
const shouldReport = errorHandlingService.shouldReportError(error);
const severity = errorHandlingService.getErrorSeverity(error);
```

### 5. Retry Service

**Location**: `frontend/src/services/retryService.ts`

Service for managing retries with exponential backoff and circuit breaker pattern.

#### Features

- Exponential backoff retry strategy
- Circuit breaker pattern
- Request-specific retry configuration
- WebSocket connection retry
- File upload retry
- Retry statistics

#### Usage

```tsx
import { retryService } from '@/services/retryService';

// Retry API call
const result = await retryService.retryApiCall(
  async () => {
    const response = await fetch('/api/data');
    if (!response.ok) throw new Error('API Error');
    return response.json();
  },
  'fetchData' // context
);

// Retry WebSocket connection
const ws = await retryService.retryWebSocketConnection(
  () => new WebSocket('wss://api.example.com'),
  'chatConnection'
);

// Retry file upload
const uploadResult = await retryService.retryFileUpload(
  () => uploadFile(file),
  'fileUpload'
);

// Get retry statistics
const stats = retryService.getStats();
console.log('Total retry attempts:', stats.totalAttempts);
console.log('Successful retries:', stats.successfulRetries);
console.log('Failed retries:', stats.failedRetries);

// Reset circuit breaker
retryService.resetCircuitBreaker();
```

### 6. Network Status Handler

**Location**: `frontend/src/components/NetworkStatusHandler.tsx`

Component that detects network status and provides offline UI.

#### Features

- Online/offline detection
- Network status indicator
- Offline content display
- Automatic reconnection attempts
- Service-specific unavailability handling

#### Usage

```tsx
import { NetworkStatusHandler } from '@/components/NetworkStatusHandler';

<NetworkStatusHandler showStatusIndicator={true}>
  <MyContent />
</NetworkStatusHandler>
```

### 7. Fallback UI Components

**Location**: `frontend/src/components/FallbackUI.tsx`

Pre-built fallback UI components for different error scenarios.

#### Components

- **FallbackUI**: Generic error UI for offline, server error, maintenance, slow connection
- **OfflineContent**: Display cached data when offline
- **ServiceUnavailable**: Service-specific unavailability message
- **LoadingWithTimeout**: Loading state with timeout handling

#### Usage

```tsx
import { FallbackUI, OfflineContent, ServiceUnavailable, LoadingWithTimeout } from '@/components/FallbackUI';

// Generic fallback
<FallbackUI
  type="offline"
  title="No Internet"
  message="Check your connection"
  onRetry={() => window.location.reload()}
  onGoHome={() => window.location.href = '/'}
/>

// Offline content with cache
<OfflineContent
  cachedData={{
    materials: cachedMaterials,
    messages: cachedMessages,
    reports: cachedReports
  }}
  onRetry={refetch}
/>

// Service unavailable
<ServiceUnavailable
  service="chat"
  onRetry={reconnect}
/>

// Loading with timeout
<LoadingWithTimeout
  timeout={10000}
  onTimeout={() => console.log('Timeout')}
>
  <MyComponent />
</LoadingWithTimeout>
```

## Error Handling Patterns

### Pattern 1: Component-Level Error Handling

```tsx
import { useErrorReporter } from '@/components/ErrorHandlingProvider';

function MyComponent() {
  const { reportError } = useErrorReporter();
  const [error, setError] = useState<Error | null>(null);

  const handleAsyncOperation = async () => {
    try {
      const data = await fetchData();
      processData(data);
    } catch (err) {
      const error = err as Error;
      reportError(error, {
        operation: 'fetchData',
        component: 'MyComponent'
      });
      setError(error);
    }
  };

  if (error) {
    return <ErrorFallback error={error} onRetry={handleAsyncOperation} />;
  }

  return <div>Content here</div>;
}
```

### Pattern 2: Custom Error Boundary for Routes

```tsx
// pages/dashboard/index.tsx
<ErrorBoundary onError={handleDashboardError}>
  <DashboardLayout>
    <Routes>
      <Route path="/" element={<DashboardHome />} />
      <Route path="/materials" element={<MaterialsList />} />
    </Routes>
  </DashboardLayout>
</ErrorBoundary>
```

### Pattern 3: API Integration with Error Handling

```tsx
import { useErrorReporter } from '@/components/ErrorHandlingProvider';

function useApi(url: string) {
  const { reportNetworkError } = useErrorReporter();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const json = await response.json();
        setData(json);
      } catch (err) {
        const error = err as Error;
        reportNetworkError(error, { url });
        setError(error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [url, reportNetworkError]);

  return { data, loading, error };
}
```

### Pattern 4: Error Logging in Services

```tsx
import { errorLoggingService } from '@/services/errorLoggingService';

class UserService {
  async getUser(id: string) {
    try {
      const response = await fetch(`/api/users/${id}`);
      if (!response.ok) {
        throw new Error(`User not found: ${id}`);
      }
      return response.json();
    } catch (error) {
      errorLoggingService.logError({
        level: 'error',
        category: error instanceof NetworkError ? 'network' : 'server',
        message: error.message,
        stack: error.stack,
        context: {
          service: 'UserService',
          method: 'getUser',
          userId: id
        }
      });
      throw error;
    }
  }
}
```

## Testing Error Boundaries

The ErrorBoundary component includes comprehensive tests covering:

### Test Coverage

- Error catching and fallback UI rendering
- Error logging and monitoring
- Recovery actions (retry, home navigation)
- useErrorHandler hook functionality
- Nested error boundaries
- Edge cases (undefined errors, async errors)
- Error state management
- Accessibility features

### Running Tests

```bash
# Run ErrorBoundary tests
npm test -- src/components/__tests__/ErrorBoundary.test.tsx

# Run all tests
npm test

# Run tests with coverage
npm test -- --coverage
```

### Test File

Location: `frontend/src/components/__tests__/ErrorBoundary.test.tsx`

28 test cases covering:
- Error catching and display
- Custom fallback UI
- Error logging
- Retry mechanism
- Error handler callbacks
- Hook usage
- Nested boundaries
- Edge cases
- State management
- Performance
- Accessibility
- Error tracking integration

## Error Recovery Strategies

### 1. Automatic Retry

Automatically retry failed API calls with exponential backoff.

```tsx
const { retryApiCall } = useRetry();

const fetchWithRetry = async () => {
  return await retryApiCall(
    () => fetch('/api/data'),
    'fetchData'
  );
};
```

### 2. Fallback Content

Show cached or default content when primary content fails.

```tsx
<Suspense fallback={<LoadingUI />}>
  <ErrorBoundary fallback={<CachedContent />}>
    <LiveContent />
  </ErrorBoundary>
</Suspense>
```

### 3. Progressive Degradation

Show partial content when some features fail.

```tsx
try {
  const fullContent = await fetchFullContent();
} catch (error) {
  const basicContent = await fetchBasicContent();
  return <PartialView data={basicContent} />;
}
```

### 4. User-Initiated Retry

Provide explicit retry options to users.

```tsx
<ErrorFallback
  error={error}
  onRetry={refetch}
  actions={[
    { label: 'Retry', onClick: refetch },
    { label: 'Go Home', onClick: () => navigate('/') },
    { label: 'Contact Support', onClick: contactSupport }
  ]}
/>
```

## Configuration

### Error Handling Provider Options

```tsx
<ErrorHandlingProvider
  enableLogging={true}        // Enable error logging (default: true)
  enableRetry={true}          // Enable retry service (default: true)
  enableNetworkMonitoring={true} // Monitor network status (default: true)
>
  {children}
</ErrorHandlingProvider>
```

### Error Logging Configuration

Via environment variables:

```bash
VITE_ENABLE_LOGGING=true      # Enable logging
VITE_LOG_LEVEL=info           # Log level: debug, info, warn, error
```

## Best Practices

### 1. Always Use Error Boundaries

Wrap major sections of your app with error boundaries:

```tsx
<ErrorBoundary>
  <DashboardSection />
</ErrorBoundary>
```

### 2. Handle Async Errors

Use try-catch in async operations and report them:

```tsx
try {
  await operation();
} catch (error) {
  reportError(error as Error, { operation: 'name' });
}
```

### 3. Provide Context

Always include context in error reports:

```tsx
reportError(error, {
  component: 'ComponentName',
  operation: 'operationName',
  userId: currentUser?.id
});
```

### 4. Log Error Categories

Use appropriate error categories for better tracking:

```tsx
if (isNetworkError) {
  errorLoggingService.logNetworkError(error);
} else if (isAuthError) {
  errorLoggingService.logAuthError(error);
}
```

### 5. Test Error Scenarios

Include error cases in your tests:

```tsx
it('should handle API errors', () => {
  vi.mock('@/api', () => ({
    fetchData: () => Promise.reject(new Error('API Error'))
  }));

  render(<MyComponent />);
  // Assert error handling
});
```

## Monitoring and Analytics

### Error Metrics

Track these metrics for system health:

- **Total Errors**: Sum of all errors in 24-hour window
- **Error Rate**: Errors per hour
- **By Category**: Breakdown by error type
- **By Level**: Distribution across severity levels
- **Resolution Rate**: Percentage of errors marked resolved

### Accessing Analytics

```tsx
import { useErrorHandling } from '@/components/ErrorHandlingProvider';

function Analytics() {
  const { getErrorStats } = useErrorHandling();

  const stats = getErrorStats();
  console.log(stats.errorStats);
  console.log(stats.retryStats);
}
```

## Troubleshooting

### Error Not Being Caught

- Ensure component is wrapped in ErrorBoundary
- Error boundaries don't catch event handler errors (use try-catch)
- Error boundaries don't catch async errors (use try-catch)

### Duplicate Error Logs

- Errors may be logged by multiple handlers
- Use error deduplication if needed
- Check for multiple error boundaries logging the same error

### Missing Error Context

- Always provide context when reporting errors
- Include component name, operation, and user info
- Use specific error logging methods (logNetworkError, etc.)

### Performance Issues

- Limit error log storage (max 1000 in memory)
- Clear old logs periodically
- Implement log rotation for long-running sessions

## Future Enhancements

- [ ] Centralized error dashboard
- [ ] Real-time error alerts
- [ ] Error pattern detection
- [ ] Automated error recovery
- [ ] Integration with error tracking services (Sentry, etc.)
- [ ] A/B testing of error messages
- [ ] Machine learning-based error prediction
- [ ] Cross-session error correlation

## References

- [React Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [Error Handling Best Practices](https://javascript.info/async-await)
- [Network Error Handling](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)

## Support

For questions or issues with the error handling system:

1. Check the test file for examples
2. Review error logs in browser console (dev tools)
3. Check error analytics dashboard
4. Contact support team with error logs

---

**Document Version**: 1.0.0
**Last Updated**: December 27, 2025
**Status**: Production Ready
