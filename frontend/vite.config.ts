import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendTarget = env.VITE_BACKEND_URL || process.env.VITE_BACKEND_URL || 'http://localhost:8000';
  const apiKey = env.VERIFICATION_SERVICE_API_KEY || process.env.VERIFICATION_SERVICE_API_KEY;

  return {
    plugins: [react()],
    server: {
      port: 3000,
      open: false,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
          headers: apiKey ? { 'X-API-Key': apiKey } : {},
        },
      },
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: false,
    },
    resolve: {
      alias: {
        '@': '/src',
        '@components': '/src/components',
        '@features': '/src/features',
        '@lib': '/src/lib',
        '@types': '/src/types',
      },
    },
  };
});
