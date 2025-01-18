# FEN - Insurance Deck Builder

An AI-powered system that transforms insurance plan PDFs into dynamic Slidev presentations with synchronized narration, powered by LangGraph orchestration, GPT-4o content analysis, and OpenAI's Text-to-Speech.

## Overview

The system automatically:
- Processes and analyzes insurance plan PDFs
- Generates professional slide decks with consistent branding
- Creates synchronized voiceover narration
- Validates content accuracy and structural alignment
- Exports to multiple formats (PDF/web)

## Quick Start

### Create a New Deck
```bash
npm run create-deck <DECK_ID> "<Deck Title>"
# Example: npm run create-deck FEN_EXAMPLE "Example Insurance Plan"
```

### Development Commands
```bash
npm run dev:<DECK_ID>      # Start development server
npm run build:<DECK_ID>    # Build for production
npm run export:<DECK_ID>   # Export to PDF
npm run preview:<DECK_ID>  # Preview remotely
```

### Generate Audio
```bash
npm run generate-audio <DECK_ID>
```

## Technical Architecture

### Core Technologies
- **LangGraph**: Orchestrates the multi-step generation pipeline
- **GPT-4o**: Powers content analysis and generation
- **OpenAI TTS**: Creates natural narration
- **Slidev**: Renders markdown into presentations

### Processing Pipeline
1. **PDF Analysis**
   - Image extraction
   - Content analysis with GPT-4o
   - Table detection and processing

2. **Content Generation**
   - Markdown generation with Slidev syntax
   - Template-based formatting
   - Branding integration

3. **Validation**
   - Structure alignment verification
   - Content accuracy checks
   - Template compliance

4. **Audio Generation**
   - Script creation
   - TTS processing
   - Timing synchronization

### State Management
```typescript
interface BuilderState {
    messages: any[];              // Processing messages
    metadata: DeckMetadata;       // Deck configuration
    slides: Record<string, any>[]; // Generated slides
    audio_config?: Record<string, any>; // Audio settings
    error_context?: Record<string, any>; // Error tracking
    deck_info?: Record<string, string>;
    pdf_info?: Record<string, any>;
    page_summaries?: Record<string, any>[];
}
```

## Project Structure
```
insurance-deck-builder/
├── agents/                # AI processing agents
│   └── builder/          # Core pipeline logic
├── decks/                # Generated presentations
├── scripts/              # Utility scripts
└── types/                # TypeScript definitions
```

## License & Credits

### License
MIT License - Free to use, modify, and distribute

### Built With
- [Slidev](https://sli.dev/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- OpenAI GPT-4o and TTS APIs