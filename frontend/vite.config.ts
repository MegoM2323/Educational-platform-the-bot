import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

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
    plugins: [react()],
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
