export const BUILDER_CONFIG = {
  // Python process settings
  python: {
    timeout: 5 * 60 * 1000, // 5 minutes
    maxBuffer: 1024 * 1024 * 10, // 10MB
  },
  
  // Template settings
  templates: {
    allowed: ['US', 'MC', 'PM'],
    defaultTheme: {},
  },
  
  // Rate limiting
  rateLimit: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
  },
  
  // Paths
  paths: {
    decks: 'decks',
    templates: 'decks/templates',
    python: {
      script: 'agents.builder.run'
    }
  }
} as const; 