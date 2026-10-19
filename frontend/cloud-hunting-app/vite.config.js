import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Frontend gọi API bằng đường dẫn tương đối (/api, /auth, /content).
// Khi chạy `npm run dev`, chuyển tiếp các request này sang Gateway (port 8000).
const GATEWAY_URL = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': GATEWAY_URL,
      '/auth': GATEWAY_URL,
      '/content': GATEWAY_URL,
    },
  },
})
