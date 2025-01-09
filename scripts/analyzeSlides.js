import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function countVClicks(slideContent) {
    let count = 0;
    
    // Count individual v-click tags
    const vClickMatches = slideContent.match(/<v-click>[\s\S]*?<\/v-click>/g) || [];
    count += vClickMatches.length;
    
    // Count items within v-clicks tags
    const vClicksBlocks = slideContent.match(/<v-clicks>[\s\S]*?<\/v-clicks>/g) || [];
    for (const block of vClicksBlocks) {
        // Count bullet points and list items
        const bulletPoints = (block.match(/^[•\-\*]\s|^\d+\.\s/gm) || []).length;
        const listItems = (block.match(/<li>/g) || []).length;
        count += Math.max(bulletPoints, listItems) || 1; // If no items found, count as 1
    }
    
    return count;
}

function isContentSlide(slide) {
    const content = slide.trim();
    
    // Skip slides that are just metadata
    if (!content || content.length === 0) return false;
    
    // Check if the slide has actual content beyond metadata
    const lines = content.split('\n');
    let hasContent = false;
    let isFirstSlide = false;
    let hasTitle = false;
    
    for (const line of lines) {
        const trimmedLine = line.trim();
        
        // Skip metadata lines and empty lines
        if (!trimmedLine || 
            trimmedLine.startsWith('transition:') || 
            trimmedLine.startsWith('layout:') || 
            trimmedLine.startsWith('image:') ||
            trimmedLine.startsWith('line:') ||
            trimmedLine.startsWith('id:') ||
            trimmedLine.startsWith('theme:') ||
            trimmedLine.startsWith('title:') ||
            trimmedLine.startsWith('info:') ||
            trimmedLine.startsWith('verticalCenter:') ||
            trimmedLine.startsWith('themeConfig:') ||
            trimmedLine.startsWith('drawings:') ||
            trimmedLine.startsWith('audioEnabled:') ||
            trimmedLine.startsWith('logoHeader:') ||
            trimmedLine.startsWith('persist:')) {
            continue;
        }
        
        // Check for title slide components
        if (trimmedLine.startsWith('# ')) {
            hasTitle = true;
        }
        
        // Check if this is the first slide with SlideAudio
        if (trimmedLine.includes('<SlideAudio')) {
            isFirstSlide = true;
        }
        
        hasContent = true;
    }
    
    // Skip the first slide if it only has SlideAudio and title
    if (isFirstSlide && hasTitle) {
        return false;
    }
    
    return hasContent;
}

function parseSlides(content) {
    // Split content into slides using markdown separator
    const slides = content.split(/^---$/m)
        .filter(slide => slide.trim())
        .filter(isContentSlide);
    
    return slides.map((slide, index) => ({
        slideIndex: index + 1,
        vClickCount: countVClicks(slide)
    }));
}

function analyzeSlides(deckId) {
    try {
        const projectRoot = path.resolve(__dirname, '..');
        const slidePath = path.join(projectRoot, 'decks', deckId, 'slides.md');
        const content = fs.readFileSync(slidePath, 'utf8');
        const analysis = parseSlides(content);
        
        // Create output object
        const output = {
            deckId,
            totalSlides: analysis.length,
            slides: analysis
        };
        
        return output;
    } catch (error) {
        console.error(`Error analyzing slides for deck ${deckId}:`, error.message);
        process.exit(1);
    }
}

// Handle command line argument
const deckId = process.argv[2];
if (!deckId) {
    console.error('Please provide a deck ID as an argument');
    process.exit(1);
}

// Run analysis and output JSON
const result = analyzeSlides(deckId);
console.log(JSON.stringify(result, null, 2)); 