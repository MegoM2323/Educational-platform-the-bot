/**
 * Cloudflare Worker for THE_BOT Platform
 * Handles dynamic caching, cache busting, and request routing
 */

/**
 * Cache configuration for different content types
 */
const CACHE_CONFIG = {
  html: {
    ttl: 0,  // Don't cache (always fresh)
    staleWhileRevalidate: 0,
  },
  css: {
    ttl: 2592000,  // 30 days
    staleWhileRevalidate: 86400,  // 1 day
  },
  js: {
    ttl: 2592000,  // 30 days
    staleWhileRevalidate: 86400,  // 1 day
  },
  images: {
    ttl: 2592000,  // 30 days
    staleWhileRevalidate: 604800,  // 7 days
  },
  fonts: {
    ttl: 2592000,  // 30 days
    staleWhileRevalidate: 604800,  // 7 days
  },
  api: {
    ttl: 0,  // Don't cache (respects Cache-Control headers)
    staleWhileRevalidate: 0,
  },
  media: {
    ttl: 604800,  // 7 days
    staleWhileRevalidate: 86400,  // 1 day
  },
};

/**
 * MIME type to cache config mapping
 */
const MIME_TYPE_CACHE_MAP = {
  'text/html': CACHE_CONFIG.html,
  'text/css': CACHE_CONFIG.css,
  'application/javascript': CACHE_CONFIG.js,
  'application/x-javascript': CACHE_CONFIG.js,
  'text/javascript': CACHE_CONFIG.js,
  'image/jpeg': CACHE_CONFIG.images,
  'image/png': CACHE_CONFIG.images,
  'image/webp': CACHE_CONFIG.images,
  'image/gif': CACHE_CONFIG.images,
  'image/svg+xml': CACHE_CONFIG.images,
  'font/woff': CACHE_CONFIG.fonts,
  'font/woff2': CACHE_CONFIG.fonts,
  'font/ttf': CACHE_CONFIG.fonts,
  'application/font-woff': CACHE_CONFIG.fonts,
  'video/mp4': CACHE_CONFIG.media,
  'audio/mpeg': CACHE_CONFIG.media,
  'video/webm': CACHE_CONFIG.media,
  'application/octet-stream': CACHE_CONFIG.api,
  'application/json': CACHE_CONFIG.api,
  'application/xml': CACHE_CONFIG.api,
  'text/plain': CACHE_CONFIG.api,
};

/**
 * Get cache configuration based on content type
 */
function getCacheConfig(contentType) {
  const mimeType = contentType?.split(';')[0] || 'application/octet-stream';
  return MIME_TYPE_CACHE_MAP[mimeType] || CACHE_CONFIG.api;
}

/**
 * Check if URL has cache busting parameter
 */
function hasCacheBustParam(url) {
  const params = ['v', 'version', 'bust', 'cachebust'];
  return params.some(param => url.searchParams.has(param));
}

/**
 * Generate cache key
 */
function generateCacheKey(request) {
  const url = new URL(request.url);

  // For API requests, include query parameters
  if (url.pathname.includes('/api/')) {
    return request.url;
  }

  // For static assets, exclude cache busting parameters
  url.search = '';
  return url.toString();
}

/**
 * Add cache headers to response
 */
function addCacheHeaders(response, ttl, staleWhileRevalidate) {
  const headers = new Headers(response.headers);

  if (ttl === 0) {
    // Don't cache
    headers.set('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0');
    headers.set('Pragma', 'no-cache');
    headers.set('Expires', '0');
  } else {
    // Cache with TTL and stale-while-revalidate
    let cacheControl = `public, max-age=${ttl}`;
    if (staleWhileRevalidate > 0) {
      cacheControl += `, stale-while-revalidate=${staleWhileRevalidate}`;
    }
    headers.set('Cache-Control', cacheControl);
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: headers,
  });
}

/**
 * Main worker handler
 */
export default {
  async fetch(request, env, ctx) {
    try {
      const url = new URL(request.url);

      // Skip caching for certain paths
      if (url.pathname.includes('/.well-known/')) {
        return fetch(request);
      }

      // Check cache
      const cacheKey = generateCacheKey(request);
      const cache = caches.default;
      let response = await cache.match(cacheKey);

      if (response) {
        // Cache hit
        const newResponse = new Response(response.body, response);
        newResponse.headers.set('X-Cache-Status', 'HIT');
        return newResponse;
      }

      // Cache miss - fetch from origin
      response = await fetch(request);

      // Determine cache TTL based on content type
      const contentType = response.headers.get('content-type');
      const cacheConfig = getCacheConfig(contentType);

      // Don't cache non-successful responses
      if (response.status !== 200) {
        response.headers.set('X-Cache-Status', 'MISS');
        return response;
      }

      // Don't cache if origin set no-cache
      const cacheControl = response.headers.get('cache-control');
      if (cacheControl && cacheControl.includes('no-cache')) {
        response.headers.set('X-Cache-Status', 'MISS');
        return response;
      }

      // Add cache headers and store in cache
      const cachedResponse = addCacheHeaders(
        response,
        cacheConfig.ttl,
        cacheConfig.staleWhileRevalidate
      );

      if (cacheConfig.ttl > 0) {
        ctx.waitUntil(cache.put(cacheKey, cachedResponse.clone()));
      }

      cachedResponse.headers.set('X-Cache-Status', 'MISS');
      return cachedResponse;

    } catch (error) {
      // Return error response
      return new Response(
        JSON.stringify({
          error: 'Worker error',
          message: error.message,
        }),
        {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  },

  /**
   * Handle POST requests for cache purging
   */
  async purgeCache(request, env, ctx) {
    // Verify authorization
    const authHeader = request.headers.get('Authorization');
    if (authHeader !== `Bearer ${env.CACHE_PURGE_TOKEN}`) {
      return new Response('Unauthorized', { status: 401 });
    }

    const { paths } = await request.json();
    const cache = caches.default;

    try {
      for (const path of paths || []) {
        const url = new URL(path, request.url);
        await cache.delete(url.toString());
      }

      return new Response(
        JSON.stringify({
          success: true,
          purged: paths?.length || 0,
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    } catch (error) {
      return new Response(
        JSON.stringify({
          error: 'Purge failed',
          message: error.message,
        }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  },

  /**
   * Handle cache statistics requests
   */
  async getStats(request, env, ctx) {
    return new Response(
      JSON.stringify({
        timestamp: new Date().toISOString(),
        worker: 'thebot-cache-worker',
        version: '1.0.0',
        features: {
          caching: 'enabled',
          compression: 'enabled',
          optimization: 'enabled',
          ddos_protection: 'enabled',
          waf: 'enabled',
        },
      }),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        },
      }
    );
  },
};
