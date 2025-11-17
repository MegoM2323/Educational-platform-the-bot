import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

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
      
      // Для production - строгий CSP
      const prodCSP = "script-src 'self' 'unsafe-inline' https: 'wasm-unsafe-eval' 'strict-dynamic' 'report-sample' https://static.yoomoney.ru; object-src 'none'; base-uri 'self';";
      
      return html.replace(
        /<!-- CSP будет установлен через Vite плагин для поддержки development режима -->/,
        `<meta http-equiv="Content-Security-Policy" content="${prodCSP}" />`
      );
    },
  };
};

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Загружаем переменные окружения из корневого .env файла
  const env = loadEnv(mode, process.cwd() + "/..", "");
  
  return {
    server: {
      host: "::",
      port: 5173,
      fs: {
        strict: false,
      },
    },
    plugins: [react(), cspPlugin(mode)],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    define: {
      // Передаем переменные окружения в приложение
      "import.meta.env.VITE_DJANGO_API_URL": JSON.stringify(env.VITE_DJANGO_API_URL),
    },
    build: {
      // Оптимизации для продакшена
      target: 'esnext',
      minify: 'esbuild',
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom'],
            router: ['react-router-dom'],
            ui: ['lucide-react', 'sonner'],
            query: ['@tanstack/react-query'],
          },
        },
      },
      chunkSizeWarningLimit: 1000,
    },
    optimizeDeps: {
      include: ['react', 'react-dom', 'react-router-dom'],
    },
  };
});
