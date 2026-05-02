import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Иначе с другой машины / по IP сервера страница не откроется (только localhost).
    host: true,
    port: 5173,
  },
})
