# FEN - Insurance Deck Builder

An AI-powered system that transforms insurance plan PDFs into dynamic Slidev presentations with synchronized narration, powered by LangGraph orchestration, GPT-4o content analysis, and OpenAI's Text-to-Speech.

🎥 [Watch the Demo Video](https://youtu.be/Il_U4ssIE7w)

## Overview

The system automatically:
- Processes and analyzes insurance plan PDFs
- Generates professional slide decks with consistent branding
- Creates synchronized voiceover narration
- Validates content accuracy and structural alignment
- Exports to multiple formats (PDF/web)

## Quick Start
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

### AI-Powered Generation
1. **Template System**
   - Dynamic template injection
   - Automatic variable replacement
   - Consistent branding and styling
   - Smart layout selection based on content

2. **Content Processing**
   - Intelligent section breakdown
   - Key information extraction
   - Benefit comparison tables
   - Feature highlight detection

3. **Presentation Structure**
   - Overview slides
   - Feature breakdowns
   - Plan comparisons
   - Cost management tools
   - Service descriptions
   - Definitions and limitations

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
│   ├── builder/          # Core pipeline logic
│   ├── config/           # AI configuration
│   └── utils/            # Helper functions
├── decks/                # Generated presentations
│   ├── FEN_TEMPLATE/     # Base template
│   └── [DECK_ID]/       # Generated decks
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