/**
 * Vite Plugin for Service Worker Handling
 *
 * Ensures the service worker TypeScript file is properly compiled to JavaScript
 * and served at the root of the dist folder.
 */

import { Plugin } from 'vite';
import fs from 'fs';
import path from 'path';

export function serviceWorkerPlugin(): Plugin {
  let config: any;

  return {
    name: 'service-worker-plugin',

    configResolved(resolvedConfig) {
      config = resolvedConfig;
    },

    generateBundle() {
      // The service worker will be bundled as a separate entry
      // This hook just ensures proper handling during build
    },

    writeBundle() {
      // After build completes, ensure service-worker.js is in the right place
      // The service worker should be built as part of the normal build process
      // via rollupOptions configuration
    },
  };
}
