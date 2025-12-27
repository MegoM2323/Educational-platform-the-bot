/**
 * useServiceWorker Hook Tests
 *
 * Tests for service worker React hook functionality
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useServiceWorker, useOnlineStatus, useServiceWorkerUpdate } from '@/hooks/useServiceWorker';
import * as swManager from '@/services/serviceWorkerManager';

// Mock the service worker manager
vi.mock('@/services/serviceWorkerManager', () => ({
  registerServiceWorker: vi.fn().mockResolvedValue(true),
  unregisterServiceWorker: vi.fn().mockResolvedValue(true),
  onServiceWorkerUpdate: vi.fn((callback) => {
    return () => {};
  }),
  checkForServiceWorkerUpdate: vi.fn().mockResolvedValue({ updateAvailable: false }),
  installServiceWorkerUpdate: vi.fn(),
  clearServiceWorkerCache: vi.fn().mockResolvedValue(true),
  isOnline: vi.fn().mockReturnValue(true),
  onOnlineStatusChange: vi.fn((callback) => {
    return () => {};
  }),
  syncPendingMessages: vi.fn().mockResolvedValue(undefined),
  precacheCriticalAssets: vi.fn().mockResolvedValue(undefined),
  getCacheStats: vi.fn().mockResolvedValue({ totalSize: 0, caches: [] }),
  getServiceWorkerStatus: vi.fn().mockResolvedValue({
    isSupported: true,
    isRegistered: true,
    isOnline: true,
    updateAvailable: false,
  }),
}));

describe('useServiceWorker Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return initial state', () => {
    const { result } = renderHook(() => useServiceWorker({ autoRegister: false }));

    expect(result.current.isSupported).toBe(true);
    expect(result.current.isRegistered).toBe(false);
    expect(result.current.isOnline).toBe(true);
    expect(result.current.updateAvailable).toBe(false);
  });

  it('should register service worker on mount', async () => {
    const { result } = renderHook(() => useServiceWorker({ autoRegister: true }));

    await waitFor(() => {
      expect(swManager.registerServiceWorker).toHaveBeenCalled();
    });
  });

  it('should precache critical assets', async () => {
    const urls = ['/index.html', '/style.css'];

    const { result } = renderHook(() =>
      useServiceWorker({
        autoRegister: true,
        precacheUrls: urls,
      })
    );

    await waitFor(() => {
      expect(swManager.precacheCriticalAssets).toHaveBeenCalledWith(urls);
    });
  });

  it('should listen for update availability', async () => {
    const { result } = renderHook(() => useServiceWorker({ autoRegister: false }));

    // Simulate update available
    const callback = (swManager.onServiceWorkerUpdate as any).mock.calls[0]?.[0];
    if (callback) {
      act(() => {
        callback(true);
      });
    }

    await waitFor(() => {
      expect(result.current.updateAvailable).toBe(true);
    });
  });

  it('should install update when requested', async () => {
    const { result } = renderHook(() => useServiceWorker({ autoRegister: false }));

    await act(async () => {
      await result.current.installUpdate();
    });

    expect(swManager.installServiceWorkerUpdate).toHaveBeenCalled();
  });

  it('should clear cache when requested', async () => {
    const { result } = renderHook(() => useServiceWorker({ autoRegister: false }));

    await act(async () => {
      await result.current.clearCache();
    });

    expect(swManager.clearServiceWorkerCache).toHaveBeenCalled();
  });

  it('should unregister service worker', async () => {
    const { result } = renderHook(() => useServiceWorker({ autoRegister: false }));

    await act(async () => {
      await result.current.unregister();
    });

    expect(swManager.unregisterServiceWorker).toHaveBeenCalled();
  });

  it('should check for updates', async () => {
    const { result } = renderHook(() => useServiceWorker({ autoRegister: false }));

    await act(async () => {
      await result.current.checkForUpdates();
    });

    expect(swManager.checkForServiceWorkerUpdate).toHaveBeenCalled();
  });

  it('should refresh cache stats', async () => {
    const { result } = renderHook(() => useServiceWorker({ autoRegister: false }));

    await act(async () => {
      await result.current.refreshCacheStats();
    });

    expect(swManager.getCacheStats).toHaveBeenCalled();
  });

  it('should handle online/offline status changes', async () => {
    const onStatusChange = vi.fn();
    const { result } = renderHook(() =>
      useServiceWorker({
        autoRegister: false,
        onOnlineStatusChange: onStatusChange,
      })
    );

    // Simulate online event
    const callback = (swManager.onOnlineStatusChange as any).mock.calls[0]?.[0];
    if (callback) {
      act(() => {
        callback(false);
      });
    }

    await waitFor(() => {
      expect(result.current.isOnline).toBe(false);
    });
  });
});

describe('useOnlineStatus Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true,
      configurable: true,
    });
  });

  it('should return initial online status', () => {
    const { result } = renderHook(() => useOnlineStatus());

    expect(result.current).toBe(true);
  });

  it('should update on online event', async () => {
    const { result } = renderHook(() => useOnlineStatus());

    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false,
        configurable: true,
      });
      window.dispatchEvent(new Event('offline'));
    });

    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });
});

describe('useServiceWorkerUpdate Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return initial state', () => {
    const { result } = renderHook(() => useServiceWorkerUpdate());

    expect(result.current.showUpdatePrompt).toBe(false);
    expect(result.current.updateAvailable).toBe(false);
  });

  it('should show update prompt when update available', async () => {
    const { result } = renderHook(() => useServiceWorkerUpdate());

    // Simulate update available
    const callback = (swManager.onServiceWorkerUpdate as any).mock.calls[0]?.[0];
    if (callback) {
      act(() => {
        callback(true);
      });
    }

    await waitFor(() => {
      expect(result.current.showUpdatePrompt).toBe(true);
    });
  });

  it('should handle update installation', async () => {
    const { result } = renderHook(() => useServiceWorkerUpdate());

    await act(async () => {
      await result.current.handleUpdate();
    });

    expect(swManager.installServiceWorkerUpdate).toHaveBeenCalled();
  });

  it('should dismiss update prompt', async () => {
    const { result } = renderHook(() => useServiceWorkerUpdate());

    // Show prompt first
    const callback = (swManager.onServiceWorkerUpdate as any).mock.calls[0]?.[0];
    if (callback) {
      act(() => {
        callback(true);
      });
    }

    await waitFor(() => {
      expect(result.current.showUpdatePrompt).toBe(true);
    });

    // Dismiss it
    act(() => {
      result.current.handleDismiss();
    });

    await waitFor(() => {
      expect(result.current.showUpdatePrompt).toBe(false);
    });
  });
});
