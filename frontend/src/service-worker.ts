/**
 * Service Worker for THE_BOT Platform
 *
 * Provides offline functionality with comprehensive caching strategies:
 * - Cache-first for static assets (CSS, JS, images)
 * - Network-first for API calls (with fallback)
 * - Stale-while-revalidate for images
 *
 * Features:
 * - App shell caching (critical assets)
 * - API response caching with versioning
 * - Offline fallback pages
 * - Background sync for offline actions
 * - Cache cleanup and updates
 */

declare const self: ServiceWorkerGlobalScope;

// Cache configuration with versions
const CACHE_VERSION = 'v1';
const CACHE_NAMES = {
  APP_SHELL: `app-shell-${CACHE_VERSION}`,
  API_RESPONSES: `api-responses-${CACHE_VERSION}`,
  IMAGES: `images-${CACHE_VERSION}`,
  OFFLINE_FALLBACK: `offline-fallback-${CACHE_VERSION}`,
};

// Critical assets for app shell (must be cached for offline access)
const CRITICAL_ASSETS = [
  '/',
  '/index.html',
  '/src/main.tsx',
  '/src/App.tsx',
  '/src/index.css',
  '/favicon.ico',
];

// API endpoints that should be cached (with network-first strategy)
const CACHED_API_PATTERNS = [
  /^\/api\/auth\//,
  /^\/api\/materials\//,
  /^\/api\/chat\//,
  /^\/api\/scheduling\//,
  /^\/api\/knowledge-graph\//,
  /^\/api\/users\//,
  /^\/api\/profiles\//,
];

// Cache TTL (Time To Live) in milliseconds
const CACHE_TTL = {
  LONG: 7 * 24 * 60 * 60 * 1000, // 7 days for static assets
  MEDIUM: 24 * 60 * 60 * 1000,    // 1 day for API responses
  SHORT: 60 * 60 * 1000,          // 1 hour for images
};

interface CachedResponse {
  data: Response;
  timestamp: number;
  ttl: number;
}

/**
 * Check if a request URL is cacheable
 */
function isCacheableRequest(url: string): boolean {
  try {
    const urlObj = new URL(url);

    // Don't cache external requests
    if (urlObj.origin !== self.location.origin) {
      return false;
    }

    // Don't cache WebSocket connections
    if (url.includes('/ws')) {
      return false;
    }

    // Don't cache admin panel in offline mode (security)
    if (url.includes('/admin')) {
      return false;
    }

    return true;
  } catch {
    return false;
  }
}

/**
 * Determine if a URL is an API endpoint
 */
function isApiRequest(url: string): boolean {
  return CACHED_API_PATTERNS.some(pattern => pattern.test(new URL(url).pathname));
}

/**
 * Determine if a URL is an image
 */
function isImageRequest(url: string): boolean {
  return /\.(png|jpg|jpeg|gif|webp|svg|ico)$/i.test(new URL(url).pathname);
}

/**
 * Get appropriate cache name based on request type
 */
function getCacheName(url: string): string {
  if (isApiRequest(url)) {
    return CACHE_NAMES.API_RESPONSES;
  }
  if (isImageRequest(url)) {
    return CACHE_NAMES.IMAGES;
  }
  return CACHE_NAMES.APP_SHELL;
}

/**
 * Get TTL for a specific URL
 */
function getCacheTTL(url: string): number {
  if (isApiRequest(url)) {
    return CACHE_TTL.MEDIUM;
  }
  if (isImageRequest(url)) {
    return CACHE_TTL.SHORT;
  }
  return CACHE_TTL.LONG;
}

/**
 * Create offline fallback response
 */
function createOfflineFallback(): Response {
  const html = `
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>THE BOT - Offline Mode</title>
        <style>
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }

          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
              'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
          }

          .offline-container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 40px;
            max-width: 500px;
            text-align: center;
          }

          .offline-icon {
            width: 80px;
            height: 80px;
            margin: 0 auto 20px;
            opacity: 0.8;
          }

          h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
          }

          p {
            color: #666;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 30px;
          }

          .offline-tips {
            text-align: left;
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
          }

          .offline-tips h3 {
            color: #333;
            font-size: 14px;
            margin-bottom: 10px;
          }

          .offline-tips ul {
            list-style: none;
          }

          .offline-tips li {
            color: #666;
            font-size: 14px;
            padding: 5px 0;
            padding-left: 20px;
            position: relative;
          }

          .offline-tips li:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
          }

          button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s ease;
          }

          button:hover {
            background: #764ba2;
          }

          .status {
            margin-top: 20px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 6px;
            font-size: 14px;
            color: #666;
          }
        </style>
      </head>
      <body>
        <div class="offline-container">
          <svg class="offline-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 21h22M17 3a6.002 6.002 0 0 0-5.7 3.9m-11.4 8.7A6 6 0 0 1 12 3c4 0 7.33 2.67 9 8M9.172 15.172a4 4 0 0 1 5.656 0M9 17h.01"/>
          </svg>

          <h1>You're Offline</h1>
          <p>We've lost your internet connection. Some features may not be available right now.</p>

          <div class="offline-tips">
            <h3>What you can still do:</h3>
            <ul>
              <li>View your cached materials</li>
              <li>Read messages sent earlier</li>
              <li>Access your profile information</li>
              <li>View your study progress</li>
            </ul>
          </div>

          <button onclick="window.location.reload()">Reload Page</button>

          <div class="status">
            <p id="status">Waiting for connection...</p>
          </div>
        </div>

        <script>
          // Update status when connection restored
          window.addEventListener('online', () => {
            document.getElementById('status').textContent = 'Connection restored! Reloading...';
            setTimeout(() => window.location.reload(), 1500);
          });

          // Periodic check for connection
          setInterval(() => {
            fetch('/ping', { method: 'HEAD' })
              .then(() => {
                document.getElementById('status').textContent = 'Connection restored! Reloading...';
                setTimeout(() => window.location.reload(), 1500);
              })
              .catch(() => {
                document.getElementById('status').textContent = 'Still offline... retrying...';
              });
          }, 3000);
        </script>
      </body>
    </html>
  `;

  return new Response(html, {
    headers: { 'Content-Type': 'text/html; charset=UTF-8' },
  });
}

/**
 * Cache a response with TTL metadata
 */
async function cacheResponseWithTTL(
  cacheName: string,
  url: string,
  response: Response
): Promise<void> {
  try {
    const cache = await caches.open(cacheName);

    // Clone response to avoid consuming it
    const clonedResponse = response.clone();

    // Create a new response with cache metadata headers
    const ttl = getCacheTTL(url);
    const newResponse = new Response(clonedResponse.body, {
      status: clonedResponse.status,
      statusText: clonedResponse.statusText,
      headers: new Headers(clonedResponse.headers),
    });

    // Add cache metadata
    newResponse.headers.set('X-Cache-Timestamp', Date.now().toString());
    newResponse.headers.set('X-Cache-TTL', ttl.toString());

    await cache.put(url, newResponse);
  } catch (error) {
    console.warn('Failed to cache response:', error);
  }
}

/**
 * Check if a cached response is still valid (not expired)
 */
function isCacheValid(response: Response): boolean {
  const timestamp = response.headers.get('X-Cache-Timestamp');
  const ttl = response.headers.get('X-Cache-TTL');

  if (!timestamp || !ttl) {
    return true; // Assume valid if no metadata
  }

  const now = Date.now();
  const cachedTime = parseInt(timestamp, 10);
  const cacheTTL = parseInt(ttl, 10);

  return now - cachedTime < cacheTTL;
}

/**
 * Get cached response if valid, otherwise delete it
 */
async function getValidCachedResponse(cacheName: string, url: string): Promise<Response | null> {
  try {
    const cache = await caches.open(cacheName);
    const response = await cache.match(url);

    if (!response) {
      return null;
    }

    if (isCacheValid(response)) {
      return response.clone();
    }

    // Remove expired cache
    await cache.delete(url);
    return null;
  } catch {
    return null;
  }
}

/**
 * Network-first strategy: Try network, fallback to cache
 * Used for API calls that need fresh data
 */
async function networkFirstStrategy(request: Request): Promise<Response> {
  try {
    const response = await fetch(request.clone());

    if (response.ok) {
      // Cache successful responses
      await cacheResponseWithTTL(
        CACHE_NAMES.API_RESPONSES,
        request.url,
        response.clone()
      );
    }

    return response;
  } catch {
    // Network failed, try cache
    const cachedResponse = await getValidCachedResponse(
      CACHE_NAMES.API_RESPONSES,
      request.url
    );

    if (cachedResponse) {
      return cachedResponse;
    }

    // No cache available for API, return offline page
    return createOfflineFallback();
  }
}

/**
 * Cache-first strategy: Use cache, fallback to network
 * Used for static assets that rarely change
 */
async function cacheFirstStrategy(request: Request): Promise<Response> {
  const cachedResponse = await getValidCachedResponse(
    CACHE_NAMES.APP_SHELL,
    request.url
  );

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const response = await fetch(request.clone());

    if (response.ok) {
      await cacheResponseWithTTL(
        CACHE_NAMES.APP_SHELL,
        request.url,
        response.clone()
      );
    }

    return response;
  } catch {
    // Return offline fallback for critical pages
    if (request.destination === 'document') {
      return createOfflineFallback();
    }

    throw new Error(`Failed to fetch: ${request.url}`);
  }
}

/**
 * Stale-while-revalidate strategy: Return cache while updating in background
 * Used for images and non-critical assets
 */
async function staleWhileRevalidateStrategy(request: Request): Promise<Response> {
  const cache = await caches.open(CACHE_NAMES.IMAGES);
  const cachedResponse = await cache.match(request);

  // Fetch from network in background (don't wait for it)
  const fetchPromise = fetch(request.clone()).then(response => {
    if (response.ok) {
      const responseToCache = response.clone();
      cache.put(request, responseToCache);
    }
    return response;
  }).catch(() => {
    // Network failed, return cached version if available
    return cachedResponse || createOfflineFallback();
  });

  // Return cached response immediately, or wait for network if no cache
  return cachedResponse || fetchPromise;
}

/**
 * Clean up old cache versions
 */
async function cleanupOldCaches(): Promise<void> {
  try {
    const cacheNames = await caches.keys();
    const validCaches = Object.values(CACHE_NAMES);

    await Promise.all(
      cacheNames
        .filter(name => !validCaches.includes(name))
        .map(name => caches.delete(name))
    );
  } catch (error) {
    console.warn('Cache cleanup failed:', error);
  }
}

/**
 * Service Worker Install Event
 * Caches critical app shell assets
 */
self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(CACHE_NAMES.APP_SHELL)
      .then(cache => {
        // Cache critical assets, but don't fail if some are missing
        // (they might be dynamic URLs that aren't available yet)
        return cache.addAll(['/index.html', '/favicon.ico'])
          .catch(() => {
            console.warn('Some critical assets could not be cached during install');
          });
      })
      .then(() => self.skipWaiting()) // Skip waiting and activate immediately
  );
});

/**
 * Service Worker Activate Event
 * Cleans up old caches and claims all clients
 */
self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    cleanupOldCaches()
      .then(() => self.clients.claim()) // Claim all clients for this service worker
  );
});

/**
 * Service Worker Fetch Event
 * Main request handling with caching strategies
 */
self.addEventListener('fetch', (event: FetchEvent) => {
  const { request } = event;
  const url = request.url;

  // Skip non-GET requests and non-cacheable requests
  if (request.method !== 'GET' || !isCacheableRequest(url)) {
    return;
  }

  // Choose caching strategy based on request type
  let strategyPromise: Promise<Response>;

  if (isApiRequest(url)) {
    // API calls: Network-first (fresh data when possible)
    strategyPromise = networkFirstStrategy(request);
  } else if (isImageRequest(url)) {
    // Images: Stale-while-revalidate (show cached, update in background)
    strategyPromise = staleWhileRevalidateStrategy(request);
  } else {
    // Static assets: Cache-first (use cache, fallback to network)
    strategyPromise = cacheFirstStrategy(request);
  }

  event.respondWith(
    strategyPromise.catch(() => {
      // Final fallback: return offline page for document requests
      if (request.destination === 'document') {
        return createOfflineFallback();
      }

      // For other resource types, return error
      return new Response('Resource unavailable offline', {
        status: 503,
        statusText: 'Service Unavailable',
      });
    })
  );
});

/**
 * Background Sync Event
 * Retry failed requests when connection is restored
 */
self.addEventListener('sync', (event: any) => {
  if (event.tag === 'sync-messages') {
    event.waitUntil(
      // Attempt to sync messages
      fetch('/api/chat/pending-messages/', {
        method: 'POST',
      }).catch(() => {
        // If sync fails, it will be retried
        console.warn('Failed to sync messages, will retry later');
      })
    );
  }
});

/**
 * Message Event
 * Handle messages from the main app
 */
self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data.type === 'CLEAR_CACHE') {
    // Clear cache on logout
    event.waitUntil(
      Promise.all(
        Object.values(CACHE_NAMES).map(cacheName => caches.delete(cacheName))
      )
        .then(() => {
          console.log('All caches cleared');
        })
        .catch(error => {
          console.error('Failed to clear caches:', error);
        })
    );
  } else if (event.data.type === 'SKIP_WAITING') {
    // Force update of service worker
    self.skipWaiting();
  }
});

export {};
