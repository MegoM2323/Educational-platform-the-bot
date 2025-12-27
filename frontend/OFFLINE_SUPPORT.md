# Offline Support Implementation

## Quick Start

### 1. Service Worker is Auto-Registered
```typescript
// In src/main.tsx - already configured
import { registerServiceWorker } from "@/services/serviceWorkerManager";
registerServiceWorker();
```

### 2. Update Notification is Auto-Enabled
```typescript
// In src/App.tsx - already added
import { ServiceWorkerUpdateNotification } from "@/components/ServiceWorkerUpdateNotification";
<ServiceWorkerUpdateNotification />
```

### 3. Use in Your Components
```typescript
import { useServiceWorker, useOnlineStatus } from "@/hooks/useServiceWorker";

function MyComponent() {
  const isOnline = useOnlineStatus();
  const { updateAvailable, installUpdate } = useServiceWorker();

  return (
    <>
      {!isOnline && <div>You are offline</div>}
      {updateAvailable && <button onClick={installUpdate}>Update</button>}
    </>
  );
}
```

## What Gets Cached

### Static Assets (7 days)
- CSS files
- JavaScript bundles
- Images and icons
- Fonts
- HTML documents

### API Responses (1 day)
- `/api/auth/*` - Authentication
- `/api/materials/*` - Learning materials
- `/api/chat/*` - Chat history
- `/api/scheduling/*` - Lesson schedules
- `/api/knowledge-graph/*` - Lesson graphs
- `/api/users/*` - User data
- `/api/profiles/*` - Profile information

### Images (1 hour)
- Profile pictures
- Material thumbnails
- Course banners

## What Doesn't Get Cached

- WebSocket connections (`/ws`)
- Admin panel routes (`/admin`)
- External resources
- Error responses
- Request bodies (only GET requests)

## Offline Features

### 1. Offline Fallback Page
When the app can't load, users see a helpful page with:
- Status indication (You're Offline)
- List of available offline content
- Button to reload when online
- Auto-reload detection

### 2. Smart Caching
- **Cache-first**: Static assets load from cache
- **Network-first**: API calls try network, fallback to cache
- **Stale-while-revalidate**: Images show cached while updating

### 3. Background Sync
- Chat messages sent while offline are queued
- Messages sync when connection restored
- Automatic retry if sync fails

### 4. Update Management
- Checks for new service worker version hourly
- Shows notification when update available
- Gracefully installs new version
- Auto-reloads with new code

## Testing Offline Mode

### Using Chrome DevTools

1. Open DevTools (F12)
2. Go to **Network** tab
3. Check **Offline** checkbox
4. Navigate around the app
5. Notice the offline fallback page when app can't load
6. Check **Application → Cache Storage** to see what's cached

### Manual Testing

```typescript
// In browser console
await navigator.serviceWorker.getRegistrations().then(regs => {
  console.log('Service Workers:', regs);
});

// Check cache contents
const cache = await caches.open('app-shell-v1');
const keys = await cache.keys();
console.log('Cached URLs:', keys.map(r => r.url));

// Get cache statistics
import { getCacheStats } from "@/services/serviceWorkerManager";
const stats = await getCacheStats();
console.log('Cache size:', stats.totalSize, 'bytes');
```

## User Settings

### Clear Cache
```typescript
import { clearServiceWorkerCache } from "@/services/serviceWorkerManager";

// Add to settings page
<button onClick={() => clearServiceWorkerCache()}>
  Clear Offline Cache
</button>
```

### Disable Service Worker
```typescript
import { unregisterServiceWorker } from "@/services/serviceWorkerManager";

// Add to settings page
<button onClick={() => unregisterServiceWorker()}>
  Disable Offline Support
</button>
```

## Performance Impact

### Bundle Size
- Service worker: ~15KB (gzipped)
- Manager: ~8KB (gzipped)
- Hook: ~5KB (gzipped)
- Total: ~28KB (one-time, separate from main bundle)

### Cache Storage
- Average app: 10-20MB
- With heavy caching: 50-100MB
- Users can clear anytime

### Network Improvement
- Offline capability: enables offline usage
- Faster loads: cached assets load instantly
- Better reliability: fallback when network fails

## Troubleshooting

### Service Worker Not Registered
```typescript
// Check in console
await navigator.serviceWorker.getRegistrations()
  .then(regs => console.log(regs.length, 'workers registered'));
```

### Cache Not Growing
1. Check that API endpoints match `CACHED_API_PATTERNS`
2. Verify responses have status 200
3. Check cache version in `service-worker.ts`
4. Look for errors in Service Worker console

### Update Not Installing
1. Wait for update check (every hour)
2. Or manually trigger: `checkForServiceWorkerUpdate()`
3. Look for notification dialog
4. Check DevTools → Application → Service Workers

### High Cache Size
```typescript
// Monitor cache size
setInterval(async () => {
  const stats = await getCacheStats();
  console.log('Cache size:', (stats.totalSize / 1024 / 1024).toFixed(2), 'MB');
}, 60000); // Every minute
```

## Advanced Configuration

### Change Cache Versions
In `src/service-worker.ts`:
```typescript
const CACHE_NAMES = {
  APP_SHELL: `app-shell-v2`,        // Increment to invalidate
  API_RESPONSES: `api-responses-v2`,
  // ... etc
};
```

### Add API Endpoints to Cache
In `src/service-worker.ts`:
```typescript
const CACHED_API_PATTERNS = [
  // ... existing patterns
  /^\/api\/assignments\//,  // Add new endpoint
  /^\/api\/reports\//,
];
```

### Change Cache TTL
In `src/service-worker.ts`:
```typescript
const CACHE_TTL = {
  LONG: 7 * 24 * 60 * 60 * 1000,   // Change 7 days
  MEDIUM: 2 * 24 * 60 * 60 * 1000,  // Change 2 days
  SHORT: 30 * 60 * 1000,            // Change 30 mins
};
```

## Security Notes

### What's Protected
- Admin routes never cached (`/admin`)
- Authentication endpoints have TTL
- Error responses not cached
- External resources not cached
- Only HTTPS in production

### Clearing on Logout
Always call after logout:
```typescript
import { clearServiceWorkerCache } from "@/services/serviceWorkerManager";

function handleLogout() {
  await clearServiceWorkerCache();
  // Continue logout...
}
```

## Browser Compatibility

Works on:
- Chrome 40+
- Firefox 44+
- Safari 11.1+
- Edge 17+
- Mobile browsers (same versions)

Gracefully degrades on older browsers (no offline support, but app still works).

## File Locations

- Service Worker: `src/service-worker.ts`
- Manager: `src/services/serviceWorkerManager.ts`
- Hook: `src/hooks/useServiceWorker.ts`
- Component: `src/components/ServiceWorkerUpdateNotification.tsx`
- Manifest: `public/manifest.json`
- Tests: `src/__tests__/services/serviceWorkerManager.test.ts`
- Tests: `src/__tests__/hooks/useServiceWorker.test.ts`
- Guide: `SERVICE_WORKER_GUIDE.md`

## Next Steps

1. Test offline mode with DevTools
2. Monitor cache usage
3. Adjust cache TTLs based on needs
4. Consider pre-caching after login
5. Implement sync UI for offline queued items
6. Add offline indicator to app UI

## Resources

- Full guide: `SERVICE_WORKER_GUIDE.md`
- MDN Service Workers: https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
- Web.dev PWA: https://web.dev/progressive-web-apps/
- Offline Cookbook: https://jakearchibald.com/2014/offline-cookbook/
