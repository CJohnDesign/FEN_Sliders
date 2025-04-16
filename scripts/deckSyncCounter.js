import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get __dirname equivalent in ES modules
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

/**
 * Count script sections and get line counts for each
 * @param {string} content - Content of the audio script
 * @returns {{ sectionCount: number, lineCounts: number[] }} Section count and lines per section
 */
function analyzeScript(content) {
  // Split by section headers (---- Section Name ----)
  const sections = content.split(/----.*?----/).filter(section => section.trim());
  const lineCounts = sections.map(section => {
    // Split by lines that are empty or contain only whitespace
    return section.trim().split(/\n[\s\n]*\n/).filter(line => line.trim()).length;
  });
  
  return {
    sectionCount: sections.length,
    lineCounts
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
 * Count slides and get v-click counts for each
 * @param {string} content - Content of the slides markdown
 * @returns {{ slideCount: number, clickCounts: number[] }} Slide count and clicks per slide
 */
function analyzeSlides(content) {
  // Split content by frontmatter markers and filter empty sections
  const allSections = content.split(/^---$/m).filter(section => section.trim());
  
  // Group sections into slides (each content slide has a transition section before it)
  const contentSlides = [];
  let currentSlide = '';
  
  allSections.forEach((section, index) => {
    // Skip the frontmatter
    if (index === 0) return;
    
    // If it's a transition section, start a new slide
    if (section.includes('transition: fade-out')) {
      if (currentSlide) {
        contentSlides.push(currentSlide);
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
  }
  
  // Process each content slide
  const clickCounts = contentSlides.map(slide => countClicksInSlide(slide));
  
  return {
    slideCount: contentSlides.length,
    clickCounts
  };
}

/**
 * Compare script sections with slides
 * @param {{ sectionCount: number, lineCounts: number[] }} scriptInfo
 * @param {{ slideCount: number, clickCounts: number[] }} slideInfo
 */
function compareContent(scriptInfo, slideInfo) {
  console.log('\nAnalyzing content synchronization:');
  console.log('----------------------------------------');
  
  // Compare section counts
  console.log(`Script sections: ${scriptInfo.sectionCount}`);
  console.log(`Content slides: ${slideInfo.slideCount}`);
  
  if (scriptInfo.sectionCount !== slideInfo.slideCount) {
    console.log('\n❌ Section count mismatch');
    return;
  }
  
  console.log('\n✅ Section counts match!\n');
  
  // Compare click counts for each section
  console.log('Analyzing click synchronization:');
  console.log('----------------------------------------');
  
  scriptInfo.lineCounts.forEach((lineCount, index) => {
    const clickCount = slideInfo.clickCounts[index] || 0;
    console.log(`\nSection ${index + 1}:`);
    console.log(`Script lines: ${lineCount}`);
    console.log(`Slide clicks: ${clickCount}`);
    
    if (lineCount - 1 !== clickCount) {
      console.log('❌ Click count mismatch');
    } else {
      console.log('✅ Click counts match');
    }
  });
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