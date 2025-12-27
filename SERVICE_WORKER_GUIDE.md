# Service Worker Implementation Guide

## Overview

This guide documents the service worker implementation for THE_BOT platform, providing offline functionality, intelligent caching strategies, and background synchronization.

## Features

### 1. Offline Functionality
- **Offline Fallback Page**: Beautiful, informative page shown when app cannot load offline
- **App Shell Caching**: Critical assets cached for instant load times
- **API Response Caching**: Intelligent caching of API endpoints with TTL

### 2. Caching Strategies

#### Cache-First (Static Assets)
- **Used for**: CSS, JavaScript, images, fonts
- **Behavior**: Load from cache first, fallback to network
- **TTL**: 7 days
- **Use case**: Files that rarely change

```
Request → Cache? YES → Return cached response
Request → Cache? NO → Fetch from network → Cache response
```

#### Network-First (API Calls)
- **Used for**: API endpoints (`/api/*`)
- **Behavior**: Try network first, fallback to cache if network fails
- **TTL**: 1 day
- **Use case**: Fresh data is important, but offline access is valued

```
Request → Network? SUCCESS → Cache and return response
Request → Network? FAIL → Return cached response
```

#### Stale-While-Revalidate (Images)
- **Used for**: Image files
- **Behavior**: Return cached immediately while fetching fresh version
- **TTL**: 1 hour
- **Use case**: Images that may update but immediate display is important

```
Request → Cache? YES → Return cached response
          → Fetch in background → Update cache
```

### 3. Cache Management
- **Automatic cleanup**: Old cache versions are deleted during activation
- **Manual clearing**: Users can clear cache from settings
- **TTL-based expiration**: Cached responses include timestamp and TTL
- **Size tracking**: Monitor total cache size for debugging

### 4. Background Sync
- **Offline messaging**: Messages sent while offline are queued
- **Auto-sync**: Queued data syncs when connection is restored
- **Retry logic**: Failed syncs are retried by the browser

### 5. Service Worker Updates
- **Periodic checks**: Updates checked every hour
- **User notification**: Prompt shown when new version available
- **Graceful installation**: New version installed without interrupting user
- **Auto-reload**: Page reloads when update is installed

## Installation

### 1. Service Worker Registration

The service worker is automatically registered in `main.tsx`:

```typescript
import { registerServiceWorker } from "@/services/serviceWorkerManager";

registerServiceWorker().catch(error => {
  console.error("Failed to register service worker:", error);
});
```

### 2. Update Notification Component

Add to your main App component:

```typescript
import { ServiceWorkerUpdateNotification } from "@/components/ServiceWorkerUpdateNotification";

// In your render:
<ServiceWorkerUpdateNotification />
```

This component:
- Displays alert when update is available
- Allows user to install update or dismiss
- Handles page reload after installation

## Usage

### Basic Setup

```typescript
import { useServiceWorker } from "@/hooks/useServiceWorker";

function MyComponent() {
  const {
    isSupported,
    isRegistered,
    isOnline,
    updateAvailable,
    installUpdate,
    clearCache,
  } = useServiceWorker({
    autoRegister: true,
    precacheUrls: ['/index.html', '/favicon.ico'],
    onUpdateAvailable: () => {
      console.log('New version available!');
    },
    onOnlineStatusChange: (online) => {
      console.log('Online status:', online);
    },
  });

  return (
    <div>
      {!isOnline && <div>You are offline</div>}
      {updateAvailable && (
        <button onClick={installUpdate}>Install Update</button>
      )}
    </div>
  );
}
```

### Clearing Cache on Logout

```typescript
import { clearServiceWorkerCache } from "@/services/serviceWorkerManager";

async function handleLogout() {
  await clearServiceWorkerCache();
  // Continue with logout process
}
```

### Checking Online Status

```typescript
import { useOnlineStatus } from "@/hooks/useServiceWorker";

function MyComponent() {
  const isOnline = useOnlineStatus();

  if (!isOnline) {
    return <OfflineModeContent />;
  }

  return <NormalContent />;
}
```

### Pre-caching Critical Assets

```typescript
import { precacheCriticalAssets } from "@/services/serviceWorkerManager";

// After login, pre-cache user's critical content
await precacheCriticalAssets([
  '/dashboard',
  '/materials',
  '/profile',
]);
```

### Getting Cache Statistics

```typescript
import { getCacheStats } from "@/services/serviceWorkerManager";

const stats = await getCacheStats();
console.log('Cache size:', stats.totalSize);
console.log('Number of caches:', stats.totalCaches);
console.log('Cache details:', stats.caches);
```

## Configuration

### Cache Names
Located in `src/service-worker.ts`:

```typescript
const CACHE_NAMES = {
  APP_SHELL: `app-shell-v1`,
  API_RESPONSES: `api-responses-v1`,
  IMAGES: `images-v1`,
  OFFLINE_FALLBACK: `offline-fallback-v1`,
};
```

Update the version number (e.g., `v1` → `v2`) to force cache invalidation.

### Cache TTL
```typescript
const CACHE_TTL = {
  LONG: 7 * 24 * 60 * 60 * 1000,   // 7 days for static assets
  MEDIUM: 24 * 60 * 60 * 1000,      // 1 day for API responses
  SHORT: 60 * 60 * 1000,            // 1 hour for images
};
```

### Cacheable APIs
```typescript
const CACHED_API_PATTERNS = [
  /^\/api\/auth\//,
  /^\/api\/materials\//,
  /^\/api\/chat\//,
  /^\/api\/scheduling\//,
  /^\/api\/knowledge-graph\//,
  /^\/api\/users\//,
  /^\/api\/profiles\//,
];
```

## Build Configuration

### Vite Configuration
The service worker is built as a separate entry point in `vite.config.ts`:

```typescript
input: {
  main: path.resolve(__dirname, 'index.html'),
  'service-worker': path.resolve(__dirname, 'src/service-worker.ts'),
},
output: {
  entryFileNames: (chunkInfo) => {
    if (chunkInfo.name === 'service-worker') {
      return '[name].js';  // No hash for service worker
    }
    return 'js/[name]-[hash].js';
  },
}
```

## File Structure

```
frontend/
├── src/
│   ├── service-worker.ts              # Main service worker
│   ├── services/
│   │   └── serviceWorkerManager.ts    # Registration & lifecycle
│   ├── hooks/
│   │   └── useServiceWorker.ts        # React hook integration
│   ├── components/
│   │   └── ServiceWorkerUpdateNotification.tsx
│   └── __tests__/
│       ├── services/
│       │   └── serviceWorkerManager.test.ts
│       ├── hooks/
│       │   └── useServiceWorker.test.ts
│       └── integration/
│           └── offline.test.ts
├── public/
│   └── manifest.json                  # PWA manifest
├── vite.config.ts                     # Service worker build config
└── index.html                         # Links to manifest
```

## Security Considerations

### What IS Cached
- Public API responses (materials, chat history, etc.)
- Static assets (CSS, JavaScript, images)
- User profile data (cached with TTL)

### What IS NOT Cached
- Authentication endpoints (`/api/auth/`)
- Admin panel routes (`/admin`)
- Error responses (HTTP errors)
- WebSocket connections (`/ws`)
- External resources (different origins)

### Cache Clearing
- Automatic: Old cache versions cleaned up on activation
- Manual: User can clear cache from app settings
- On logout: All caches cleared immediately

## Testing

### Run Tests
```bash
npm test -- src/__tests__/services/serviceWorkerManager.test.ts
npm test -- src/__tests__/hooks/useServiceWorker.test.ts
npm test -- src/__tests__/integration/offline.test.ts
```

### Manual Testing

1. **Open DevTools**: F12 → Application → Service Workers
2. **Test Offline Mode**:
   - Go to Network tab
   - Throttle to offline
   - Browse app, observe fallback page
   - Check cache in Application → Cache Storage

3. **Test Update**:
   - Make code change
   - Deploy new version
   - Open app, notification should appear
   - Click "Update Now"
   - Page should reload with new version

4. **Check Cache Stats**:
   - Console: `await getCacheStats()`
   - See cache sizes and entry counts

## Performance Tips

### 1. Optimize Cache Size
- Exclude heavy assets if not needed offline
- Clean up old cache versions regularly
- Monitor cache size with `getCacheStats()`

### 2. Smart Pre-caching
```typescript
// After login, pre-cache essentials
await precacheCriticalAssets([
  '/dashboard',
  '/materials',
  '/profile',
  '/chat',
]);
```

### 3. Cache Versioning
Update cache version to invalidate:
```typescript
const CACHE_NAMES = {
  APP_SHELL: `app-shell-v2`,  // Increment version
  API_RESPONSES: `api-responses-v2`,
};
```

### 4. Monitor Cache Health
```typescript
// Periodically check cache health
const stats = await getCacheStats();
if (stats.totalSize > 50 * 1024 * 1024) {
  // Cache is getting large, clean up
  await clearServiceWorkerCache();
}
```

## Troubleshooting

### Service Worker Not Registering
1. Check browser console for errors
2. Verify `/service-worker.js` exists in dist folder
3. Check `HTTPS` in production (required by spec)
4. Verify service worker scope is correct (default: `/`)

### Cache Not Working
1. Check Application → Cache Storage in DevTools
2. Verify API patterns in `CACHED_API_PATTERNS`
3. Check that response status is 200 (errors not cached)
4. Verify TTL hasn't expired

### Update Not Installing
1. Check service worker is listening for updates
2. Verify update check is running (every hour)
3. Check browser console for errors
4. Manually trigger with `checkForServiceWorkerUpdate()`

### High Cache Size
1. Reduce TTL for large assets
2. Exclude unnecessary endpoints from caching
3. Clear cache periodically: `clearServiceWorkerCache()`
4. Monitor with: `getCacheStats()`

## Browser Support

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Service Workers | 40+ | 44+ | 11.1+ | 17+ |
| Cache API | 43+ | 39+ | 11.1+ | 17+ |
| Background Sync | 49+ | No | No | 17+ |
| Manifest.json | 31+ | 55+ | 15+ | 79+ |

## References

- [MDN Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Web.dev PWA Guide](https://web.dev/progressive-web-apps/)
- [Service Worker Cookbook](https://serviceworke.rs/)
- [Cache API](https://developer.mozilla.org/en-US/docs/Web/API/Cache)
- [Background Sync API](https://developer.mozilla.org/en-US/docs/Web/API/Background_Sync_API)

## Future Enhancements

1. **Offline Form Submission**: Queue form submissions for later
2. **Sync Notifications**: Notify user when offline data is synced
3. **Compression**: Use compression for cached API responses
4. **Analytics**: Track offline usage patterns
5. **Testing Tools**: Build UI for testing offline scenarios
6. **Bandwidth Optimization**: Different cache strategies based on connection type

## Contributing

When adding new features to the service worker:

1. Update `CACHED_API_PATTERNS` for new API endpoints
2. Add appropriate TTL values for the cache type
3. Update cache version number to invalidate old caches
4. Add tests for the new functionality
5. Update this documentation
6. Test in offline mode before submitting PR
