# Error Tracking with Sentry

Comprehensive guide to the Sentry integration for error tracking, performance monitoring, and debugging across the THE_BOT platform.

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Backend Configuration](#backend-configuration)
- [Frontend Configuration](#frontend-configuration)
- [Usage Patterns](#usage-patterns)
- [Error Fingerprinting](#error-fingerprinting)
- [Performance Monitoring](#performance-monitoring)
- [User Context](#user-context)
- [Breadcrumbs](#breadcrumbs)
- [Alert Configuration](#alert-configuration)
- [Dashboard & Debugging](#dashboard--debugging)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Sentry is an error tracking and performance monitoring platform that helps identify, diagnose, and fix issues in production and development environments.

### Key Features

- **Automatic Error Capture**: Catches unhandled exceptions
- **Performance Monitoring**: Tracks slow requests and database queries
- **Source Maps**: Maps minified errors back to original source code
- **Error Grouping**: Intelligently groups similar errors
- **User Context**: Identifies affected users
- **Session Replay**: Records user sessions when errors occur
- **Environment Separation**: Different handling for dev/staging/production
- **Alert Rules**: Automatic notifications for critical errors
- **Real-time Notifications**: Slack, email, SMS, PagerDuty integration

### Architecture

```
Frontend (React + TypeScript)
  ├── Error Boundary (Sentry.ErrorBoundary)
  ├── Automatic unhandled exception capture
  ├── Performance monitoring (React Router, API calls)
  └── Source maps upload on build

Backend (Django + Python)
  ├── Middleware for request context
  ├── Celery task monitoring
  ├── Database query tracking
  └── Custom exception handling

Sentry Dashboard (sentry.io)
  ├── Error grouping & stats
  ├── Performance metrics
  ├── User impact analysis
  └── Alert configuration
```

## Setup

### 1. Create Sentry Project

1. Go to https://sentry.io
2. Create a new organization or use existing
3. Create a new project for each environment (or single project with environments)
4. Copy the DSN (Data Source Name)

### 2. Install Dependencies

**Backend:**
```bash
pip install sentry-sdk[django,celery,redis]
```

**Frontend:**
```bash
npm install @sentry/react @sentry/vite-plugin
```

Both are already in `requirements.txt` and `package.json`.

### 3. Environment Variables

Create or update `.env` with Sentry configuration:

```bash
# Sentry configuration
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
SENTRY_ENVIRONMENT=production      # development, staging, production
SENTRY_RELEASE=1.0.0               # Your app version
SENTRY_TRACES_SAMPLE_RATE=0.1     # 10% of transactions in production
SENTRY_PROFILES_SAMPLE_RATE=0.01  # 1% of transactions for profiling

# Source maps and deployment
SENTRY_ORG=your-org-slug
SENTRY_PROJECT=your-project-slug
SENTRY_AUTH_TOKEN=xxxxx            # For source map upload
SENTRY_URL=https://sentry.io       # Custom Sentry instance URL (optional)

# Frontend-specific
VITE_SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
VITE_SENTRY_ENVIRONMENT=production
VITE_SENTRY_RELEASE=1.0.0
VITE_SENTRY_TRACES_SAMPLE_RATE=0.1
```

## Backend Configuration

### Django Integration

Add to `backend/config/settings.py`:

```python
# Sentry initialization
from config.sentry import init_sentry

# Initialize Sentry early in settings
init_sentry(settings)

# Add Sentry middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ... other middleware ...
    'config.sentry.SentryMiddleware',  # Add near end for user context
    'django.middleware.common.CommonMiddleware',
]

# Configure Sentry performance sampling
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))

# Error filtering
SENTRY_IGNORE_ERRORS = [
    'django.http.response.Http404',
    'django.core.exceptions.SuspiciousOperation',
]
```

### What Gets Tracked Automatically

1. **Unhandled Exceptions**: All uncaught errors in views and middleware
2. **Database Queries**: Slow queries and connection errors
3. **Cache Operations**: Cache hit/miss and errors
4. **Middleware Events**: Request/response cycles
5. **Celery Tasks**: Task failures and execution time
6. **Redis Operations**: Connection and command tracking

### Celery Task Monitoring

Tasks are automatically monitored, but you can add custom context:

```python
from celery import shared_task
from config.sentry import capture_exception, set_error_tag

@shared_task
def process_payment(invoice_id):
    try:
        set_error_tag('invoice_id', invoice_id)
        set_error_tag('task', 'process_payment')

        # ... payment processing ...

    except Exception as e:
        capture_exception(
            e,
            extra_data={'invoice_id': invoice_id, 'task': 'process_payment'}
        )
        raise
```

### Custom Exception Handling in Views

```python
from django.http import JsonResponse
from config.sentry import (
    attach_user_context,
    capture_exception,
    set_error_tag,
    add_breadcrumb
)

def create_payment(request):
    try:
        # Attach user context
        attach_user_context(
            user_id=request.user.id,
            email=request.user.email,
            role=request.user.profile.role,
            metadata={'session_id': request.session.session_key}
        )

        # Track action
        add_breadcrumb('Payment creation started', category='payment')
        set_error_tag('payment_type', 'invoice')

        # ... process payment ...

        add_breadcrumb('Payment created successfully', category='payment')
        return JsonResponse({'status': 'success'})

    except PaymentException as e:
        capture_exception(
            e,
            level='error',
            user_id=request.user.id,
            extra_data={'step': 'payment_processing'}
        )
        return JsonResponse({'error': 'Payment failed'}, status=400)
```

## Frontend Configuration

### React Initialization

Add to `src/main.tsx` **before rendering**:

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import * as Sentry from '@sentry/react'

// Initialize Sentry FIRST
Sentry.initSentry()

// Then render app
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

### Error Boundary Setup

Wrap your app with Sentry Error Boundary:

```tsx
import { ErrorBoundary } from '@/utils/sentry'

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Your routes */}
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
```

### User Context in Auth Flow

After user login, set user context:

```typescript
import { attachUserContext } from '@/utils/sentry'

// After successful login
async function handleLogin(credentials) {
  const response = await api.login(credentials)
  const user = response.data.user

  // Set user context for error tracking
  attachUserContext({
    id: user.id,
    email: user.email,
    username: user.username,
    role: user.role,
  })

  // Store auth token, redirect, etc.
}

// On logout
async function handleLogout() {
  await api.logout()

  // Clear user context
  clearUserContext()

  // Redirect, etc.
}
```

## Usage Patterns

### 1. Capturing Exceptions

```typescript
import { captureException, addBreadcrumb } from '@/utils/sentry'

try {
  const data = await fetchData()
  addBreadcrumb('Data fetched', { category: 'api', data: { count: data.length } })
} catch (error) {
  captureException(error, {
    extra: { endpoint: '/api/data' },
    tags: { critical: 'false' },
    level: 'error'
  })
}
```

### 2. Tracking Important Events

```typescript
import { captureMessage, setTag } from '@/utils/sentry'

// Unusual condition
if (errorCount > threshold) {
  setTag('alert_type', 'high_error_rate')
  captureMessage('High error rate detected', {
    level: 'warning',
    extra: { errorCount, threshold }
  })
}
```

### 3. Performance Measurement

```typescript
import { performance } from '@/utils/sentry'

// Measure async operation
const result = await performance.measure('fetch_dashboard', async () => {
  return await api.getDashboard()
})

// Or use span directly
const span = performance.startSpan({ op: 'db.query', name: 'get_user' })
try {
  const user = await getUser()
  span.end()
} catch (error) {
  span.end()
  throw error
}
```

### 4. Breadcrumbs for User Actions

```typescript
import { addBreadcrumb } from '@/utils/sentry'

// Track user interactions
function handleFormSubmit(formData) {
  addBreadcrumb('Form submitted', {
    category: 'user-action',
    data: { formName: 'payment' }
  })

  // ... submit form ...
}

function handlePageNavigation(page) {
  addBreadcrumb('Navigation', {
    category: 'navigation',
    data: { from: currentPage, to: page }
  })

  // ... navigate ...
}
```

### 5. Backend View with Full Context

```python
from django.http import JsonResponse
from config.sentry import (
    attach_user_context,
    capture_exception,
    set_error_tag,
    add_breadcrumb
)

class PaymentViewSet(viewsets.ModelViewSet):
    def create(self, request):
        try:
            # Set user context
            attach_user_context(
                user_id=request.user.id,
                email=request.user.email,
                role=request.user.profile.role,
            )

            # Add breadcrumb
            add_breadcrumb('Payment creation initiated', category='payment')
            set_error_tag('payment_provider', 'yookassa')

            # Process payment
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            payment = serializer.save()

            add_breadcrumb(
                'Payment processed',
                category='payment',
                data={'payment_id': payment.id}
            )

            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_201_CREATED
            )

        except PaymentError as e:
            set_error_tag('error_stage', 'payment_processing')
            capture_exception(
                e,
                level='error',
                user_id=request.user.id,
                extra_data={
                    'payload': request.data,
                    'step': 'payment_processing'
                }
            )
            return Response(
                {'error': 'Payment processing failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
```

## Error Fingerprinting

Sentry automatically fingerprints errors for intelligent grouping. Custom fingerprinting rules:

### Backend Fingerprinting Rules

**Validation Errors** - Group by field name:
```
ValidationError.field_name
```

**Database Errors** - Group by constraint type:
```
IntegrityError.unique_constraint
IntegrityError.foreign_key_constraint
```

**404 Errors** - Group by path pattern (not exact path):
```
Http404./api/users/{id}
Http404./api/materials/{id}/comments
```

**Permission Errors** - Group by endpoint:
```
Http403.POST./api/payments
Http403.DELETE./api/users/{id}
```

### Frontend Fingerprinting Rules

**TypeError** - Group by property:
```
TypeError.property_message
TypeError.set_message
```

**ReferenceError** - Group by variable:
```
ReferenceError.undefined_userContext
```

**NetworkError** - Group by endpoint:
```
NetworkError./api/users/{id}
```

These are handled automatically by Sentry configuration.

## Performance Monitoring

### Automatic Performance Tracking

Sentry automatically tracks:

1. **HTTP Requests**: All fetch() and XMLHttpRequest calls
2. **React Router Navigation**: Page transitions
3. **Database Queries**: Django ORM execution time
4. **Cache Operations**: Redis get/set performance
5. **Celery Tasks**: Task execution time

### Transaction Sampling

Sample rates vary by environment:

| Environment | Traces | Profiles | Replays |
|------------|--------|----------|---------|
| Development | 100% | 100% | 100% |
| Staging | 50% | 10% | 10% |
| Production | 10% | 1% | 1% |

### Manual Performance Tracking

```python
# Backend
from config.sentry import capture_message

def slow_operation():
    import time
    start = time.time()

    # ... operation ...

    duration = time.time() - start
    if duration > 2:
        capture_message(
            f'Slow operation completed in {duration:.2f}s',
            level='warning',
            extra_data={'duration': duration}
        )
```

```typescript
// Frontend
import { performance } from '@/utils/sentry'

async function expensiveDataLoad() {
  return await performance.measure('data_load', async () => {
    return await api.getLargeDataset()
  })
}
```

## User Context

User context helps identify affected users and adds debugging information.

### Automatic User Context (Django)

The `SentryMiddleware` automatically captures:
- User ID
- Email
- Username
- User role
- Session ID
- IP address

### Manual User Context (Frontend)

```typescript
import { attachUserContext, clearUserContext } from '@/utils/sentry'

// After login
attachUserContext({
  id: user.id,
  email: user.email,
  username: user.username,
  role: user.role,
})

// On logout
clearUserContext()
```

### User Context in Events

Set context for specific operations:

```python
# Backend
attach_user_context(
    user_id=request.user.id,
    email=request.user.email,
    role='teacher',
    metadata={
        'organization': 'School #1',
        'class': '10A',
        'subject': 'Mathematics'
    }
)

# Frontend
attachUserContext({
  id: user.id,
  email: user.email,
  username: user.username,
  role: user.profile.role,
})
```

## Breadcrumbs

Breadcrumbs are user actions and events that led to an error.

### Types of Breadcrumbs

| Category | When | Example |
|----------|------|---------|
| `user_action` | User clicks, forms | "Form submitted", "Button clicked" |
| `navigation` | Page transitions | "Navigate to /dashboard" |
| `http` | API calls | "GET /api/users/123" (auto) |
| `database` | DB queries | "SELECT * FROM users" (auto) |
| `payment` | Payment operations | "Payment initiated", "Invoice generated" |
| `websocket` | Real-time events | "Message sent", "Room joined" |
| `auth` | Authentication | "Login attempt", "Token refresh" |
| `cache` | Cache operations | "Cache hit", "Cache miss" (auto) |

### Adding Breadcrumbs

```typescript
import { addBreadcrumb } from '@/utils/sentry'

// Simple
addBreadcrumb('User viewed settings page', {
  category: 'navigation'
})

// With data
addBreadcrumb('Form validation failed', {
  category: 'user_action',
  level: 'warning',
  data: {
    formName: 'payment',
    errors: ['email', 'amount']
  }
})

// Error breadcrumb
addBreadcrumb('API request failed', {
  category: 'http',
  level: 'error',
  data: {
    url: '/api/payments',
    status: 500,
    duration: 1234
  }
})
```

## Alert Configuration

### Alert Rules

Set up alerts in Sentry dashboard:

#### 1. Critical Error Alert

**When**: Any error with tag `critical: true`

**Actions**:
- Send to Slack: #errors
- Send to PagerDuty: critical
- Create Jira issue: High priority

#### 2. High Error Rate Alert

**When**: Error rate > 5% of requests

**Actions**:
- Send email to team@thebot.local
- Send Slack notification: #alerts
- Page on-call engineer (PagerDuty)

#### 3. Payment Failure Alert

**When**: Error containing 'payment' or 'yookassa'

**Actions**:
- Send to Slack: #payments
- Send email to payment-team@thebot.local
- Create incident in Jira

#### 4. Performance Alert

**When**: Transaction duration > 5 seconds

**Actions**:
- Slack notification: #performance
- Email to platform-team@thebot.local

#### 5. New Error Alert

**When**: Error never seen before

**Actions**:
- Send email to team@thebot.local
- Slack notification: #new-errors

### Alert Configuration in Code

```bash
# Navigate to Sentry project settings
1. Settings → Alerts
2. Click "Create Alert Rule"
3. Configure conditions and actions

# Example alert setup:
- Name: "Critical Payment Errors"
- Condition: Error with tag payment_critical=true
- Action: Send to Slack #payments-alerts
- Action: Create PagerDuty incident
- Frequency: For each new issue
```

## Dashboard & Debugging

### Key Dashboards

1. **Issues Dashboard**
   - View all errors grouped by type
   - See affected users and error frequency
   - Track error resolution

2. **Performance Dashboard**
   - Slow transactions
   - Database query performance
   - API response times
   - Resource usage

3. **Release Dashboard**
   - Errors by release
   - Deployment tracking
   - Version comparison

4. **User Impact Dashboard**
   - Most affected users
   - User error timeline
   - Session replay

### Debugging Steps

1. **View Error Details**
   - Click issue in dashboard
   - Review stack trace
   - Check breadcrumbs (user actions)
   - View user context (who affected)

2. **Analyze Stack Trace**
   - Source maps automatically applied
   - Navigate to original source code
   - View surrounding code context

3. **Review Session Replay**
   - Watch user session with error
   - See what user was doing
   - Check network requests in timeline

4. **Check Breadcrumbs**
   - Understand sequence of events
   - Find when error occurred
   - See user context at error time

5. **Compare Releases**
   - Use release comparison
   - Find which release introduced error
   - Track error metrics over time

### Advanced Queries

Search for specific errors:

```
# Find errors from specific user
user.id:123

# Find errors in specific feature
tags.feature:payments

# Find recent errors
timestamp:[now-1h TO now]

# Combine conditions
environment:production tags.critical:true error.type:PaymentError

# Performance issues
has:measurements.duration measurements.duration:>5000
```

## Best Practices

### 1. Set User Context Early

```python
# Backend: in middleware or auth view
attach_user_context(user_id, email, role=user_role)

# Frontend: after login
attachUserContext({ id, email, username, role })
```

### 2. Use Meaningful Tags

```python
set_error_tag('payment_provider', 'yookassa')
set_error_tag('feature', 'invoicing')
set_error_tag('critical', 'true')
```

### 3. Add Breadcrumbs for Context

```typescript
addBreadcrumb('Important action', {
  category: 'user_action',
  data: { action: 'submit', form: 'payment' }
})
```

### 4. Sample Correctly by Environment

```
Development: 100% - catch all issues
Staging: 50% - balance coverage and costs
Production: 10% - focus on real issues
```

### 5. Filter Noise

Ignore common, non-critical errors:
- 404s for missing assets
- Network timeouts (transient)
- Rate limit errors (expected)
- Browser extension errors

### 6. Use Error Fingerprinting

```python
# Instead of noise, group similar errors:
# Bad: "User 123 error", "User 456 error"
# Good: "ValidationError.email_field"
```

### 7. Monitor Critical Paths

```python
# Always capture errors in:
set_error_tag('critical_path', 'payment_processing')
set_error_tag('critical_path', 'authentication')
set_error_tag('critical_path', 'course_enrollment')
```

### 8. Use Performance Monitoring

```typescript
// Measure expensive operations
await performance.measure('fetch_dashboard', async () => {
  return await api.getDashboard()
})
```

## Troubleshooting

### Sentry Events Not Appearing

**Check:**
1. DSN is correctly configured in environment
2. Sentry client is initialized before app starts
3. Sample rate isn't filtering all events
4. Error isn't in ignore list
5. Check `isSentryEnabled()` returns true

**Debug:**
```typescript
import { isSentryEnabled } from '@/utils/sentry'
console.log('Sentry enabled:', isSentryEnabled())
```

### Source Maps Not Working

**Check:**
1. `sourcemap: true` in vite config (only for production)
2. Sentry vite plugin configured with auth token
3. Release version matches between build and upload
4. Upload completed without errors

**Debug:**
```bash
# Check source maps in dist
ls -la dist/js/*.map

# Verify upload with Sentry CLI
npm install -g @sentry/cli
sentry-cli releases files list {version}
```

### Performance Data Not Showing

**Check:**
1. `tracesSampleRate > 0`
2. Transaction not in ignore list
3. Environment variable set correctly
4. Release identifier matches

### Alerts Not Triggering

**Check:**
1. Alert rule condition is correct
2. Matching errors have correct tags
3. Integration configured (Slack, email, etc.)
4. Check alert history in Settings

### High Sentry Costs

**Reduce with:**
1. Adjust sample rates down (especially production)
2. Add error filters to ignore noise
3. Remove expensive integrations
4. Monitor session replays (expensive)

## Source Map Upload

### Automatic Upload (Recommended)

Sentry vite plugin uploads source maps automatically:

```bash
# Configure environment
export SENTRY_ORG=your-org
export SENTRY_PROJECT=your-project
export SENTRY_AUTH_TOKEN=xxxxx
export VITE_SENTRY_RELEASE=1.0.0

# Build (plugin uploads automatically)
npm run build
```

### Manual Upload

If automatic upload fails:

```bash
# Install Sentry CLI
npm install -g @sentry/cli

# Upload source maps
sentry-cli releases -o your-org -p your-project files upload-sourcemaps ./dist

# Or upload specific JS files
sentry-cli releases -o your-org -p your-project files upload-sourcemaps ./dist --release 1.0.0
```

## Integration with Monitoring Stack

### Prometheus Integration

Sentry metrics can be exported to Prometheus:

```
# Endpoint: /api/system/metrics/prometheus/

# Sample metrics:
sentry_events_processed_total{environment="production"}
sentry_error_rate{severity="critical"}
sentry_performance_p95{endpoint="/api/payments"}
```

### Slack Integration

Configure Sentry to Slack:

1. In Sentry: Settings → Integrations → Slack
2. Authorize and select channels
3. Create alert rules with Slack actions

### PagerDuty Integration

For on-call engineering:

1. In Sentry: Settings → Integrations → PagerDuty
2. Link to incident service
3. Set critical alert rules to create incidents

## Further Reading

- [Sentry Documentation](https://docs.sentry.io/)
- [Django Integration](https://docs.sentry.io/platforms/python/guides/django/)
- [React Integration](https://docs.sentry.io/platforms/javascript/guides/react/)
- [Performance Monitoring](https://docs.sentry.io/product/performance/)
- [Source Maps](https://docs.sentry.io/product/source-maps/)
- [Best Practices](https://docs.sentry.io/product/error-monitoring/best-practices/)

---

**Last Updated**: December 27, 2025
**Version**: 1.0.0
**Status**: Production Ready
