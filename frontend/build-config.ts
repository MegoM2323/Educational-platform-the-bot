/**
 * Build Configuration and Performance Monitoring
 * Tracks build performance metrics and generates reports
 */

export interface BuildMetrics {
  startTime: number;
  endTime: number;
  duration: number; // in milliseconds
  bundleSize?: {
    gzip: number;
    brotli: number;
    raw: number;
  };
  chunkCount?: number;
  warnings?: string[];
  errors?: string[];
}

export interface BuildReport {
  success: boolean;
  metrics: BuildMetrics;
  timestamp: string;
  environment: string;
  commitHash?: string;
}

/**
 * Build performance thresholds
 */
export const BUILD_THRESHOLDS = {
  // Target build time: < 15 seconds
  maxBuildTime: 15000, // milliseconds

  // Maximum bundle size: 250KB gzipped
  maxBundleSize: 250000, // bytes

  // Maximum number of chunks
  maxChunks: 20,

  // CSS file size limit: 100KB gzipped
  maxCSSSize: 100000,

  // JavaScript per chunk: 200KB gzipped
  maxChunkSize: 200000,
};

/**
 * Asset preloading configuration for SPA
 */
export const PRELOAD_CONFIG = {
  // Critical CSS that should be preloaded
  criticalCSS: [
    'css/main',
    'css/layout',
  ],

  // Critical JS chunks that should be preloaded
  criticalJS: [
    'js/react-core',
    'js/router',
  ],

  // Fonts to preload
  fonts: [
    '/fonts/inter-var.woff2',
  ],

  // DNS prefetch for external services
  dnsPrefetch: [
    'https://api.example.com',
    'https://cdn.example.com',
  ],

  // Preconnect for critical resources
  preconnect: [
    'https://api.example.com',
    'https://fonts.googleapis.com',
  ],

  // Prefetch for likely navigation
  prefetch: [
    '/pages/dashboard',
    '/pages/profile',
  ],
};

/**
 * Environment-specific build optimizations
 */
export const ENVIRONMENT_OPTIMIZATIONS = {
  development: {
    minify: false,
    sourcemap: true,
    reportCompressedSize: false,
    terserOptions: undefined,
  },
  staging: {
    minify: 'terser',
    sourcemap: true,
    reportCompressedSize: true,
    terserOptions: {
      compress: { drop_console: false },
    },
  },
  production: {
    minify: 'terser',
    sourcemap: false,
    reportCompressedSize: true,
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        passes: 2,
      },
    },
  },
};

/**
 * Cache busting strategy for CI/CD
 */
export const CACHE_CONFIG = {
  // Cache key patterns for GitHub Actions or other CI systems
  cacheKey: 'vite-cache',

  // Include/exclude patterns
  cachePaths: [
    'node_modules',
    '.vite',
    'dist',
  ],

  // Cache invalidation based on:
  // - package-lock.json or package.json changes
  // - vite.config.ts changes
  // - source code changes
};

/**
 * Artifact generation for deployment
 */
export const ARTIFACT_CONFIG = {
  // Output directory
  outputDir: 'dist',

  // Artifact name for CI/CD
  artifactName: 'frontend-build',

  // Files to include in artifact
  includePatterns: [
    'dist/**/*',
    'dist/stats.html', // Bundle analyzer report
  ],

  // Deployment commands by environment
  deployCommands: {
    staging: 'npm run build && npm run build:analyze',
    production: 'npm run build && npm run build:stats',
  },
};

/**
 * Performance regression detection thresholds
 */
export const REGRESSION_DETECTION = {
  // Allow 5% increase in build time
  buildTimeThreshold: 1.05,

  // Allow 3% increase in bundle size
  bundleSizeThreshold: 1.03,

  // Track historical builds for trending
  historicalDataPoints: 100,

  // Alert on regression
  alertOnRegression: true,

  // Notification config
  notifications: {
    slack: true,
    email: true,
    github: true, // Post to PR comments
  },
};

/**
 * Generate HTML resource hints for index.html
 */
export function generateResourceHints(): string {
  const hints: string[] = [];

  // DNS prefetch
  PRELOAD_CONFIG.dnsPrefetch.forEach((url) => {
    hints.push(`<link rel="dns-prefetch" href="${url}" />`);
  });

  // Preconnect
  PRELOAD_CONFIG.preconnect.forEach((url) => {
    hints.push(`<link rel="preconnect" href="${url}" crossorigin />`);
  });

  // Preload critical resources
  PRELOAD_CONFIG.criticalCSS.forEach((file) => {
    hints.push(`<link rel="preload" href="/${file}.css" as="style" />`);
  });

  PRELOAD_CONFIG.criticalJS.forEach((file) => {
    hints.push(`<link rel="preload" href="/${file}.js" as="script" />`);
  });

  // Preload fonts
  PRELOAD_CONFIG.fonts.forEach((font) => {
    hints.push(`<link rel="preload" href="${font}" as="font" type="font/woff2" crossorigin />`);
  });

  return hints.join('\n');
}

/**
 * SPA manifest configuration for deployment
 */
export interface SpaManifest {
  version: string;
  buildTime: string;
  assets: {
    js: string[];
    css: string[];
    fonts: string[];
  };
  preloadResources: string[];
  cacheStrategy: 'network-first' | 'cache-first' | 'stale-while-revalidate';
}

/**
 * Generate deployment manifest
 */
export function generateManifest(buildInfo: any): SpaManifest {
  return {
    version: process.env.npm_package_version || '1.0.0',
    buildTime: new Date().toISOString(),
    assets: {
      js: buildInfo.assets?.js || [],
      css: buildInfo.assets?.css || [],
      fonts: buildInfo.assets?.fonts || [],
    },
    preloadResources: [
      ...PRELOAD_CONFIG.criticalCSS,
      ...PRELOAD_CONFIG.criticalJS,
    ],
    cacheStrategy: 'stale-while-revalidate',
  };
}
