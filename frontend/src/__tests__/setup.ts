/**
 * Vitest global setup file
 * Runs before each test file
 */

import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, vi } from 'vitest';

// Initialize React DevTools hook (fixes React 19 compatibility)
beforeAll(() => {
  // Mock React DevTools for testing environment
  if (!global.__REACT_DEVTOOLS_GLOBAL_HOOK__) {
    global.__REACT_DEVTOOLS_GLOBAL_HOOK__ = {
      isDisabled: true,
      supportsFiber: true,
      inject: () => null,
      onCommitFiberRoot: () => null,
      onCommitFiberUnmount: () => null,
      onPostCommitFiberRoot: () => null,
      onPostCommitFiberUnmount: () => null,
    } as any;
  }
});

// Cleanup after each test case
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia (used by many UI components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock IntersectionObserver (used by some UI components)
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
} as any;

// Mock ResizeObserver (used by some UI components)
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any;

// Mock pointer capture methods for Radix UI (jsdom doesn't implement these)
if (typeof Element !== 'undefined') {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};

  // Mock scrollIntoView for Radix UI Select
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => {};
  }
}

// Suppress console errors in tests (optional - remove if you want to see them)
// global.console.error = () => {};
// global.console.warn = () => {};
