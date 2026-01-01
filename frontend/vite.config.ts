import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// Sentry plugin for source maps and error tracking
let sentryVitePlugin: any = null;
try {
  const sentryPlugin = require('@sentry/vite-plugin');
  sentryVitePlugin = sentryPlugin;
} catch (e) {
  // Sentry plugin is optional
}

// Service Worker plugin for proper handling
const serviceWorkerPlugin = {
  name: 'service-worker',
  apply: 'build' as const,
};

// Optional visualizer plugin - install with: npm install --save-dev rollup-plugin-visualizer
// Loaded dynamically in the config function to handle optional dependency gracefully
const visualizer: any = null;

// Build analyzer plugin to track build performance
const buildAnalyzerPlugin = () => {
  let startTime: number;

  return {
    name: 'build-analyzer',
    configResolved(config: any) {
      startTime = Date.now();
    },
    buildStart() {
      console.log('[Build Analyzer] Build started...');
      startTime = Date.now();
    },
    buildEnd() {
      const duration = Date.now() - startTime;
      console.log(`[Build Analyzer] Build completed in ${(duration / 1000).toFixed(2)}s`);
    },
  };
};

// Плагин для динамической настройки CSP
const cspPlugin = (mode: string) => {
  return {
    name: 'csp-headers',
    transformIndexHtml(html: string) {
      const isDev = mode === 'development';

      // Для development - полностью удаляем CSP из HTML
      // Vite dev server требует слишком много разрешений для HMR и модулей
      // CSP будет установлен только в production через build
      if (isDev) {
        // В development режиме удаляем комментарий о CSP - не добавляем CSP вообще
        return html.replace(
          /<!-- CSP будет установлен через Vite плагин для поддержки development режима -->/,
          ''
        );
      }

      // Для production - CSP с поддержкой WebAssembly
      const prodCSP = "script-src 'self' 'unsafe-inline' https: 'wasm-unsafe-eval' 'unsafe-eval' 'report-sample' https://static.yoomoney.ru; object-src 'none'; base-uri 'self';";

      return html.replace(
        /<!-- CSP будет установлен через Vite плагин для поддержки development режима -->/,
        `<meta http-equiv="Content-Security-Policy" content="${prodCSP}" />`
      );
    },
  };
};

// CDN Configuration for CloudFront static asset delivery
const cdnConfig = {
  enabled: process.env.VITE_CDN_ENABLED === 'true',
  domain: process.env.VITE_CDN_DOMAIN || '',
  // Base path for assets on CDN
  basePath: '/static/',
};

// https://vitejs.dev/config/
export default defineConfig(({ mode, command }) => {
  // Загружаем переменные окружения из корневого .env файла
  const env = loadEnv(mode, process.cwd() + "/..", "");
  const isDev = mode === 'development';
  const isBuild = command === 'build';

  return {
    appType: 'spa',

    // Configure base URL for assets (CDN in production, relative in dev)
    base: isBuild && cdnConfig.enabled && cdnConfig.domain
      ? `https://${cdnConfig.domain}${cdnConfig.basePath}`
      : '/',

    server: {
      host: '0.0.0.0',
      port: 8080,
      fs: {
        strict: false,
      },
      // HMR configuration для development
      // Позволяет WebSocket подключению работать корректно
      hmr: {
        host: 'localhost',
        port: 8080,
        protocol: 'ws',
      },
      // API proxy configuration
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path,
        },
        '/ws': {
          target: 'ws://localhost:8000',
          ws: true,
          changeOrigin: true,
        }
      }
    },
    plugins: [
      react(),
      cspPlugin(mode),
      buildAnalyzerPlugin(),
      serviceWorkerPlugin,
      // Sentry plugin for source maps and error tracking (production only)
      isBuild && sentryVitePlugin && sentryVitePlugin({
        org: process.env.SENTRY_ORG,
        project: process.env.SENTRY_PROJECT,
        authToken: process.env.SENTRY_AUTH_TOKEN,
        url: process.env.SENTRY_URL || 'https://sentry.io',
        release: process.env.VITE_SENTRY_RELEASE || 'unknown',
        dist: process.env.VITE_SENTRY_RELEASE || 'unknown',
        sourceMaps: {
          include: ['./dist'],
          ignore: ['node_modules'],
          rewriteSourcesAbsolutePath: true,
        },
        telemetry: false,
        debug: false,
      }),
      // Bundle analyzer - only on build with ANALYZE=true
      isBuild && process.env.ANALYZE === 'true' && visualizer({
        open: false,
        gzipSize: true,
        brotliSize: true,
        template: 'treemap',
        filename: 'dist/stats.html',
      }),
    ].filter(Boolean),
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
      // Ensure single instance of React packages to prevent context issues
      dedupe: ['react', 'react-dom', 'react-router-dom'],
    },
    define: {
      // Передаем переменные окружения в приложение
      "import.meta.env.VITE_DJANGO_API_URL": JSON.stringify(env.VITE_DJANGO_API_URL),
      "import.meta.env.VITE_WEBSOCKET_URL": JSON.stringify(env.VITE_WEBSOCKET_URL),
      // CDN configuration
      "import.meta.env.VITE_CDN_ENABLED": JSON.stringify(cdnConfig.enabled),
      "import.meta.env.VITE_CDN_DOMAIN": JSON.stringify(cdnConfig.domain),
    },
    build: {
      // Target modern browsers for optimal performance
      target: ['esnext', 'edge88', 'firefox78', 'chrome87', 'safari13'],

      // Parallel output chunks for faster builds
      modulePreload: {
        polyfill: true,
      },

      // Optimize minification
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: false,
          drop_debugger: true,
          pure_funcs: ['console.log', 'console.debug', 'console.info'],
          passes: 1,
        },
        format: {
          comments: false,
        },
        // Disable problematic toplevel optimization
        toplevel: false,
        ecma: 2020,
      },

      // CSS processing optimizations
      cssCodeSplit: true,
      // Note: cssMinify: 'lightningcss' requires additional validation
      // Using default esbuild minification for compatibility

      // Inline small assets
      assetsInlineLimit: 4096,

      // Rollup output configuration with optimized chunking
      rollupOptions: {
        input: {
          main: path.resolve(__dirname, 'index.html'),
          'service-worker': path.resolve(__dirname, 'src/service-worker.ts'),
        },
        output: {
          // Output directory structure
          entryFileNames: (chunkInfo) => {
            // Service worker should not have hash in name
            if (chunkInfo.name === 'service-worker') {
              return '[name].js';
            }
            return 'js/[name]-[hash].js';
          },
          chunkFileNames: 'js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const info = assetInfo.name.split('.');
            const ext = info[info.length - 1];
            if (/png|jpe?g|gif|tiff|bmp|ico/i.test(ext)) {
              return `images/[name]-[hash][extname]`;
            } else if (/woff|woff2|ttf|otf|eot/i.test(ext)) {
              return `fonts/[name]-[hash][extname]`;
            } else if (ext === 'css') {
              return `css/[name]-[hash][extname]`;
            } else if (ext === 'svg') {
              return `svg/[name]-[hash][extname]`;
            }
            return `[name]-[hash][extname]`;
          },

          manualChunks(id) {
            // КРИТИЧНО: React core должен быть в отдельном чанке для правильной инициализации
            if (id.includes('node_modules/react/') && !id.includes('node_modules/react-dom/')) {
              return 'react-core';
            }

            // React DOM должен быть отдельно после React
            if (id.includes('node_modules/react-dom/')) {
              return 'react-dom';
            }

            // React Router после React DOM
            if (id.includes('node_modules/react-router') || id.includes('node_modules/@remix-run/router')) {
              return 'react-router';
            }

            // Radix UI и другие React компоненты после основных библиотек
            if (id.includes('node_modules/@radix-ui/')) {
              return 'radix-ui';
            }

            // TanStack Query отдельно
            if (id.includes('node_modules/@tanstack/react-query/')) {
              return 'react-query';
            }

            // Тяжелые библиотеки в отдельные чанки
            if (id.includes('node_modules/d3/') ||
                id.includes('node_modules/d3-')) {
              return 'd3-lib';
            }

            if (id.includes('node_modules/recharts/')) {
              return 'charts';
            }

            // Все остальные node_modules в общий vendor
            if (id.includes('node_modules/')) {
              return 'vendor';
            }
          },
        },
      },

      // Performance tuning
      chunkSizeWarningLimit: 200,
      sourcemap: isDev ? 'inline' : false,
      reportCompressedSize: true,

      // Faster build with increased parallelism
      commonjsOptions: {
        transformMixedEsModules: true,
      },
    },

    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@tanstack/react-query',
        '@radix-ui/react-dialog',
        '@radix-ui/react-dropdown-menu',
        'lodash',
        'recharts',
      ],
      // Исключить огромные библиотеки из pre-bundling
      exclude: ['d3', 'd3-*'],
      // Parallel processing
      esbuildOptions: {
        target: 'esnext',
      },
    },
  };
});
