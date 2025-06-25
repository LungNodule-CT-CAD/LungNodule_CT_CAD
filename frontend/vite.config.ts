// vite.config.ts（修改后）
import { defineConfig } from 'vite';
// 关键修改：导入 SWC 版 React 插件
import react from '@vitejs/plugin-react-swc'; 
import viteCompression from 'vite-plugin-compression';

export default defineConfig({
  plugins: [
    react(), // 使用 SWC 编译 React 代码
    viteCompression(), // 启用gzip压缩
  ],
  // 其他配置（如 server、build、resolve 等）保持不变
  server: {
    port: 3000,
    open: true,
    // 代理修正：根据后端代码，正确转发带 /api 前缀的请求
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // 后端服务地址
        changeOrigin: true, // 必须设置为 true，用于跨域
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'redux', 'react-redux', 'axios'],
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
      '@components': '/src/components',
      '@pages': '/src/pages',
      '@store': '/src/store',
      '@assets': '/src/assets',
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@import "@assets/styles.css";`,
      },
    },
  },
});