/**
 * Service Worker Manager
 *
 * Handles registration, updates, and lifecycle of the service worker.
 * Provides utilities for cache management and offline mode handling.
 */

interface ServiceWorkerRegistration {
  registration: ServiceWorkerRegistration | null;
  isSupported: boolean;
  isRegistered: boolean;
}

interface UpdateCheckResult {
  updateAvailable: boolean;
  installingWorker?: ServiceWorker;
}

// Singleton instance
let swRegistration: ServiceWorkerRegistration | null = null;
let updateCallback: ((available: boolean) => void) | null = null;

/**
 * Register the service worker
 * Call this once when the app initializes
 */
export async function registerServiceWorker(): Promise<boolean> {
  // Check browser support
  if (!('serviceWorker' in navigator)) {
    console.warn('Service Workers are not supported in this browser');
    return false;
  }

  try {
    const registration = await navigator.serviceWorker.register('/service-worker.js', {
      scope: '/',
    });

    console.log('Service Worker registered successfully:', registration);

    // Listen for updates
    registration.addEventListener('updatefound', () => {
      handleUpdateFound(registration);
    });

    // Check for updates periodically
    setInterval(() => {
      registration.update().catch(error => {
        console.error('Failed to check for service worker updates:', error);
      });
    }, 60 * 60 * 1000); // Check every hour

    swRegistration = registration;
    return true;
  } catch (error) {
    console.error('Service Worker registration failed:', error);
    return false;
  }
}

/**
 * Handle when a new service worker is found
 */
function handleUpdateFound(registration: ServiceWorkerRegistration): void {
  const newWorker = registration.installing;

  if (!newWorker) {
    return;
  }

  newWorker.addEventListener('statechange', () => {
    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
      // New service worker is ready
      console.log('New service worker version available');

      // Notify the app that an update is available
      if (updateCallback) {
        updateCallback(true);
      }

      // Trigger background sync if available
      if ('serviceWorker' in navigator && 'SyncManager' in window) {
        try {
          registration.sync.register('sync-messages');
        } catch {
          console.warn('Background sync not available');
        }
      }
    }
  });
}

/**
 * Listen for service worker updates
 */
export function onServiceWorkerUpdate(callback: (available: boolean) => void): () => void {
  updateCallback = callback;

  // Cleanup function
  return () => {
    updateCallback = null;
  };
}

/**
 * Check if an update is available
 */
export async function checkForServiceWorkerUpdate(): Promise<UpdateCheckResult> {
  if (!swRegistration) {
    return { updateAvailable: false };
  }

  try {
    const registration = await navigator.serviceWorker.getRegistrations();
    const currentReg = registration[0];

    if (!currentReg) {
      return { updateAvailable: false };
    }

    await currentReg.update();

    if (currentReg.installing) {
      return {
        updateAvailable: true,
        installingWorker: currentReg.installing,
      };
    }

    return { updateAvailable: false };
  } catch (error) {
    console.error('Failed to check for updates:', error);
    return { updateAvailable: false };
  }
}

/**
 * Install a pending service worker update
 */
export function installServiceWorkerUpdate(): void {
  if (!swRegistration?.installing) {
    console.warn('No pending service worker update to install');
    return;
  }

  // Tell the service worker to skip waiting
  swRegistration.installing.postMessage({ type: 'SKIP_WAITING' });

  // Reload page when the new service worker takes over
  let refreshing = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!refreshing) {
      refreshing = true;
      window.location.reload();
    }
  });
}

/**
 * Unregister the service worker
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  if (!('serviceWorker' in navigator)) {
    return false;
  }

  try {
    const registrations = await navigator.serviceWorker.getRegistrations();

    for (const registration of registrations) {
      await registration.unregister();
    }

    swRegistration = null;
    console.log('Service Worker unregistered');
    return true;
  } catch (error) {
    console.error('Failed to unregister service worker:', error);
    return false;
  }
}

/**
 * Clear all caches
 * Call this on logout to remove cached user data
 */
export async function clearServiceWorkerCache(): Promise<boolean> {
  // Message the service worker to clear caches
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_CACHE' });
  }

  // Also clear all caches directly
  if ('caches' in window) {
    try {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(name => caches.delete(name)));
      console.log('All caches cleared');
      return true;
    } catch (error) {
      console.error('Failed to clear caches:', error);
      return false;
    }
  }

  return false;
}

/**
 * Check if the app is currently online
 */
export function isOnline(): boolean {
  return navigator.onLine;
}

/**
 * Listen for online/offline status changes
 */
export function onOnlineStatusChange(
  callback: (online: boolean) => void
): () => void {
  const handleOnline = () => callback(true);
  const handleOffline = () => callback(false);

  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);

  // Return cleanup function
  return () => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  };
}

/**
 * Get service worker registration details
 */
export async function getServiceWorkerStatus(): Promise<{
  isSupported: boolean;
  isRegistered: boolean;
  isOnline: boolean;
  updateAvailable: boolean;
}> {
  const isSupported = 'serviceWorker' in navigator;
  let isRegistered = false;
  let updateAvailable = false;

  if (isSupported) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    isRegistered = registrations.length > 0;

    if (isRegistered) {
      const result = await checkForServiceWorkerUpdate();
      updateAvailable = result.updateAvailable;
    }
  }

  return {
    isSupported,
    isRegistered,
    isOnline: navigator.onLine,
    updateAvailable,
  };
}

/**
 * Sync pending messages when connection is restored
 * Used for offline-first chat functionality
 */
export async function syncPendingMessages(): Promise<void> {
  if (!isOnline()) {
    console.log('Still offline, will retry sync later');
    return;
  }

  try {
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      const registration = await navigator.serviceWorker.ready;
      // @ts-ignore - SyncManager type not available in all browsers
      await registration.sync.register('sync-messages');
      console.log('Message sync registered');
    }
  } catch (error) {
    console.warn('Failed to register message sync:', error);
  }
}

/**
 * Pre-cache critical assets
 * Call this after login to improve offline experience
 */
export async function precacheCriticalAssets(urls: string[]): Promise<void> {
  if (!('caches' in window)) {
    console.warn('Caches API not available');
    return;
  }

  try {
    const cache = await caches.open(`app-shell-v1`);
    const failedUrls: string[] = [];

    for (const url of urls) {
      try {
        const response = await fetch(url);
        if (response.ok) {
          await cache.put(url, response);
        } else {
          failedUrls.push(url);
        }
      } catch (error) {
        failedUrls.push(url);
        console.warn(`Failed to precache: ${url}`, error);
      }
    }

    if (failedUrls.length === 0) {
      console.log(`Successfully precached ${urls.length} assets`);
    } else {
      console.warn(`Precached ${urls.length - failedUrls.length}/${urls.length} assets`);
    }
  } catch (error) {
    console.error('Failed to precache assets:', error);
  }
}

/**
 * Get cache statistics
 * Useful for debugging and monitoring
 */
export async function getCacheStats(): Promise<{
  totalCaches: number;
  totalSize: number;
  caches: Array<{ name: string; entryCount: number }>;
}> {
  if (!('caches' in window)) {
    return {
      totalCaches: 0,
      totalSize: 0,
      caches: [],
    };
  }

  try {
    const cacheNames = await caches.keys();
    const cacheStats = [];
    let totalSize = 0;

    for (const name of cacheNames) {
      const cache = await caches.open(name);
      const keys = await cache.keys();

      let cacheSize = 0;
      for (const request of keys) {
        const response = await cache.match(request);
        if (response) {
          const blob = await response.blob();
          cacheSize += blob.size;
        }
      }

      totalSize += cacheSize;
      cacheStats.push({
        name,
        entryCount: keys.length,
      });
    }

    return {
      totalCaches: cacheNames.length,
      totalSize,
      caches: cacheStats,
    };
  } catch (error) {
    console.error('Failed to get cache stats:', error);
    return {
      totalCaches: 0,
      totalSize: 0,
      caches: [],
    };
  }
}
