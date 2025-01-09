import { defineConfig } from 'vite'
import svgLoader from 'vite-svg-loader'

export default defineConfig({
  plugins: [
    svgLoader({
      svgoConfig: {
        multipass: true,
      },
    }),
  ],
  publicDir: 'public',
  server: {
    fs: {
      allow: ['..', 'decks']
    }
  }
}) 