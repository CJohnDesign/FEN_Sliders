import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get __dirname equivalent in ES modules
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

/**
 * Count script sections and get line counts for each
 * @param {string} content - Content of the audio script
 * @returns {{ sectionCount: number, lineCounts: number[], sectionTitles: string[] }} Section count, lines per section, and section titles
 */
function analyzeScript(content) {
  // Split by section headers but keep the headers
  const allParts = content.split(/(----.*?----)/);
  const sections = [];
  const sectionTitles = [];
  
  for (let i = 1; i < allParts.length; i += 2) {
    const header = allParts[i];
    const sectionContent = allParts[i + 1] || '';
    
    // Extract section title from header (remove the ---- markers)
    const title = header.replace(/----\s*/, '').replace(/\s*----/, '').trim();
    sectionTitles.push(title);
    
    // Count lines in section content
    const lineCount = sectionContent.trim().split(/\n[\s\n]*\n/).filter(line => line.trim()).length;
    sections.push(lineCount);
  }
  
  return {
    sectionCount: sections.length,
    lineCounts: sections,
    sectionTitles
  };
}

/**
 * Count v-clicks in a slide
 * @param {string} slideContent - Content of a single slide
 * @returns {number} Total number of clicks in the slide
 */
function countClicksInSlide(slideContent) {
  let totalClicks = 0;

  // Count individual <v-click> tags
  const individualClicks = (slideContent.match(/<v-click>/g) || []).length;
  totalClicks += individualClicks;

  // Find all <v-clicks> blocks
  const vClicksBlocks = slideContent.match(/<v-clicks>[\s\S]*?<\/v-clicks>/g) || [];
  
  // For each <v-clicks> block, count bullet points or lines
  vClicksBlocks.forEach(block => {
    // Remove the v-clicks tags
    const content = block.replace(/<\/?v-clicks>/g, '');
    // Count non-empty lines that start with - or are just text
    const lines = content.split('\n')
      .map(line => line.trim())
      .filter(line => line && line !== '-' && !line.match(/^[<\s]/));
    totalClicks += lines.length;
  });

  return totalClicks;
}

/**
 * Extract the slide title from slide content
 * @param {string} slideContent - Content of a single slide
 * @returns {string} Title of the slide
 */
function extractSlideTitle(slideContent) {
  const lines = slideContent.split('\n');
  
  for (const line of lines) {
    const trimmed = line.trim();
    // Look for markdown headers (# or ##)
    if (trimmed.startsWith('#')) {
      // Clean up markdown formatting and return the title
      return trimmed.replace(/^#+\s*/, '').replace(/\*\*/g, '').replace(/`/g, '').trim();
    }
  }
  
  return 'No title found';
}

/**
 * Extract the first meaningful line from slide content (excluding title)
 * @param {string} slideContent - Content of a single slide
 * @returns {string} First meaningful line of the slide
 */
function extractFirstLine(slideContent) {
  const lines = slideContent.split('\n');
  let foundTitle = false;
  
  for (const line of lines) {
    const trimmed = line.trim();
    
    // Skip the title line
    if (trimmed.startsWith('#')) {
      foundTitle = true;
      continue;
    }
    
    // Skip empty lines, HTML tags, and markdown frontmatter
    if (trimmed && 
        !trimmed.startsWith('<') && 
        !trimmed.match(/^-+$/) &&
        !trimmed.includes('transition:') &&
        !trimmed.includes('layout:') &&
        foundTitle) {
      // Clean up markdown formatting
      return trimmed.replace(/\*\*/g, '').replace(/`/g, '').replace(/\[|\]/g, '');
    }
  }
  
  return 'No meaningful content found';
}

/**
 * Count slides and get v-click counts for each
 * @param {string} content - Content of the slides markdown
 * @returns {{ slideCount: number, clickCounts: number[], firstLines: string[], slideTitles: string[] }} Slide count, clicks per slide, first lines, and slide titles
 */
function analyzeSlides(content) {
  // Split content by frontmatter markers and filter empty sections
  const allSections = content.split(/^---$/m).filter(section => section.trim());
  
  // Group sections into slides (each content slide has a transition section before it)
  const contentSlides = [];
  const firstLines = [];
  const slideTitles = [];
  let currentSlide = '';
  
  allSections.forEach((section, index) => {
    // Skip the frontmatter
    if (index === 0) return;
    
    // If it's a transition section, start a new slide
    if (section.includes('transition: fade-out')) {
      if (currentSlide) {
        contentSlides.push(currentSlide);
        slideTitles.push(extractSlideTitle(currentSlide));
        firstLines.push(extractFirstLine(currentSlide));
      }
      currentSlide = '';
    } else {
      // Add content to current slide
      currentSlide += section;
    }
  });
  
  // Add the last slide if exists
  if (currentSlide) {
    contentSlides.push(currentSlide);
    slideTitles.push(extractSlideTitle(currentSlide));
    firstLines.push(extractFirstLine(currentSlide));
  }
  
  // Process each content slide
  const clickCounts = contentSlides.map(slide => countClicksInSlide(slide));
  
  return {
    slideCount: contentSlides.length,
    clickCounts,
    firstLines,
    slideTitles
  };
}

/**
 * Compare script sections with slides
 * @param {{ sectionCount: number, lineCounts: number[], sectionTitles: string[] }} scriptInfo
 * @param {{ slideCount: number, clickCounts: number[], firstLines: string[], slideTitles: string[] }} slideInfo
 */
function compareContent(scriptInfo, slideInfo) {
  let hasErrors = false;
  let errorMessages = [];
  let totalErrors = 0;
  
  // Compare section counts first - if they don't match, only show this error
  if (scriptInfo.sectionCount !== slideInfo.slideCount) {
    console.log('\n❌ Slide Count Mismatch:');
    console.log('----------------------------------------');
    console.log(`Audio script has ${scriptInfo.sectionCount} sections`);
    console.log(`Slides deck has ${slideInfo.slideCount} slides`);
    console.log('\nPossible issues:');
    
    // Help identify where the mismatch might be
    const maxSections = Math.max(scriptInfo.sectionCount, slideInfo.slideCount);
    const minSections = Math.min(scriptInfo.sectionCount, slideInfo.slideCount);
    console.log(`• Missing ${maxSections - minSections} ${scriptInfo.sectionCount > slideInfo.slideCount ? 'slides' : 'script sections'}`);
    console.log('\n');
    return false;
  }
  
  // If section counts match, check click counts vs script lines
  scriptInfo.lineCounts.forEach((lineCount, index) => {
    const clickCount = slideInfo.clickCounts[index] || 0;
    
    // Compare script lines with click counts (assuming first line addresses headline)
    const expectedClicks = Math.max(0, lineCount - 1);
    
    if (expectedClicks !== clickCount) {
      hasErrors = true;
      totalErrors++;
      
      const slideTitle = slideInfo.slideTitles[index] || 'No title found';
      
      errorMessages.push(`\n❌ Sync Mismatch in Section ${index + 1}:`);
      errorMessages.push(`   Slide Title: "${slideTitle}"`);
      errorMessages.push(`   Script lines: ${lineCount}`);
      errorMessages.push(`   Click events: ${clickCount}`);
      errorMessages.push(`   Expected clicks: ${expectedClicks} (script lines - 1 for headline)`);
    }
  });
  
  // Display output based on results
  if (hasErrors) {
    console.log('\nFound Synchronization Issues:');
    console.log('----------------------------------------');
    console.log(`Total issues found: ${totalErrors}`);
    errorMessages.forEach(msg => console.log(msg));
    console.log('\n');
  } else {
    console.log('\n');
    console.log('┌─────────────────────────────────────────────┐');
    console.log('│                                             │');
    console.log('│  ✅ All checks passed!                      │');
    console.log('│                                             │');
    console.log('│  Audio script and slides are perfectly      │');
    console.log('│  synchronized for deck: ' + deckId.padEnd(19) + ' │');
    console.log('│                                             │');
    console.log('└─────────────────────────────────────────────┘');
    console.log('\n');
  }
  
  return !hasErrors;
}

/**
 * Analyze synchronization between deck script and slides
 * @param {string} deckId - ID of the deck to analyze
 */
async function analyzeDeckSync(deckId) {
  try {
    // Construct paths
    const deckPath = path.join(projectRoot, 'decks', deckId);
    const audioScriptPath = path.join(deckPath, 'audio', 'audio_script.md');
    const slidesPath = path.join(deckPath, 'slides.md');

    console.log(`\nAnalyzing deck: ${deckId}`);
    console.log('----------------------------------------');

    // Read files
    const scriptContent = await fs.readFile(audioScriptPath, 'utf8');
    const slidesContent = await fs.readFile(slidesPath, 'utf8');

    // Analyze content
    const scriptInfo = analyzeScript(scriptContent);
    const slideInfo = analyzeSlides(slidesContent);

    // Compare content
    compareContent(scriptInfo, slideInfo);

  } catch (error) {
    console.error(`Error processing deck ${deckId}:`, error);
  }
}

// Get deck ID from command line arguments
const deckId = process.argv[2];

if (!deckId) {
  console.error('Please provide a deck ID');
  console.error('Usage: node deckSyncCounter.js DECK_ID');
  process.exit(1);
}

analyzeDeckSync(deckId); 