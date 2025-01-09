import { defineConfig } from 'vite'

export default defineConfig({
  // ... other config options ...
  
  // Enable JSON imports
  assetsInclude: ['**/*.json'],
  
  // Configure JSON handling
  json: {
    stringify: true
  }
}) 