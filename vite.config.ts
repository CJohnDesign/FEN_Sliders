import { defineConfig } from 'vite'
import svgLoader from 'vite-svg-loader'
import path from 'path'

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
      allow: [
        '..',
        'decks',
        path.resolve(__dirname)
      ],
      strict: false
    },
    middlewareMode: false,
    cors: true,
    host: true
  },
  assetsInclude: ['**/*.mp3'],
  build: {
    assetsInlineLimit: 0, // Never inline MP3 files
  },
  resolve: {
    alias: {
      '@': '/src',
      'decks': path.resolve(__dirname, 'decks'),
      '/decks': path.resolve(__dirname, 'decks')
    }
  }
}) 