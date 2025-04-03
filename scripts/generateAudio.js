import fs from 'fs/promises';
import path from 'path';
import dotenv from 'dotenv';

dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
  throw new Error('Missing OPENAI_API_KEY in environment variables. Please check your .env file.');
}

async function findMdFile(deckKey) {
  const possiblePaths = [
    path.join(process.cwd(), `decks/${deckKey}/audio/${deckKey}.md`),
    path.join(process.cwd(), `decks/${deckKey}/audio/audio_script.md`),
    // Add more potential paths if needed
  ];

  for (const filePath of possiblePaths) {
    try {
      await fs.access(filePath);
      return filePath;
    } catch (error) {
      continue;
    }
  }

  throw new Error(`Could not find markdown file for deck ${deckKey}. Searched in:\n${possiblePaths.join('\n')}`);
}

async function parseMdFile(filePath) {
  const content = await fs.readFile(filePath, 'utf-8');
  const sections = [];
  
  // Split content by the single line delimiter pattern: ---- Text ----
  const sectionRegex = /^----\s*(.*?)\s*----$/gm;
  const parts = content.split(sectionRegex);
  
  // Remove first element if it's empty (content before first delimiter)
  if (parts[0].trim() === '') {
    parts.shift();
  }
  
  // Process parts in pairs (title and content)
  for (let i = 0; i < parts.length; i += 2) {
    const title = parts[i];
    const text = parts[i + 1]?.trim();
    
    if (title && text) {
      // Split the text into paragraphs (split by double newline)
      const paragraphs = text.split(/\n\n+/).filter(p => p.trim());
      
      // Create a section for each paragraph
      paragraphs.forEach((paragraph, pIndex) => {
        sections.push({
          title: `${title}_click_${pIndex + 1}`,
          text: paragraph.trim(),
          slideNumber: (i / 2) + 1,
          clickNumber: pIndex + 1
        });
      });
    }
  }
  
  return sections;
}

// Add filename validation
const validateFilename = (deckKey, slideNumber, clickNumber) => {
  if (!deckKey.match(/^FEN_[A-Z]{2,4}$/)) {
    throw new Error(`Invalid deckKey format: ${deckKey}`);
  }
  
  const cleanClick = String(clickNumber)
    .replace(/[^0-9_]/g, '')
    .replace(/_{2,}/g, '_');
    
  return `${deckKey}${slideNumber}_${cleanClick}.mp3`;
};

async function generateAudio(deckKey, specificSlide = null, specificClick = null) {
  try {
    const baseUrl = 'https://api.openai.com/v1/audio/speech';
    
    // Find the markdown file
    const mdFilePath = await findMdFile(deckKey);
    console.log(`Found script at: ${mdFilePath}`);
    
    const sections = await parseMdFile(mdFilePath);

    // Create the output directory if it doesn't exist
    const outputDir = path.join(process.cwd(), `decks/${deckKey}/audio/oai`);
    await fs.mkdir(outputDir, { recursive: true });

    // Filter sections based on slide and click numbers
    let sectionsToProcess = sections;
    if (specificSlide) {
      sectionsToProcess = sections.filter(section => section.slideNumber === specificSlide);
      if (sectionsToProcess.length === 0) {
        throw new Error(`No slide found with number ${specificSlide}`);
      }
    }
    if (specificClick) {
      sectionsToProcess = sectionsToProcess.filter(section => section.clickNumber === specificClick);
      if (sectionsToProcess.length === 0) {
        throw new Error(`No click ${specificClick} found for slide ${specificSlide}`);
      }
    }

    // Process each section in order
    for (const section of sectionsToProcess) {
      if (!section.text) continue; // Skip empty sections

      const response = await fetch(baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
          model: 'tts-1',
          input: section.text,
          voice: 'nova',
          response_format: 'mp3'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`API request failed: ${response.statusText}\n${JSON.stringify(errorData)}`);
      }

      const audioBuffer = Buffer.from(await response.arrayBuffer());
      
      // Modify the output filename generation
      const outputFileName = validateFilename(deckKey, section.slideNumber, section.clickNumber);
      await fs.writeFile(
        path.join(outputDir, outputFileName),
        audioBuffer
      );

      console.log(`Generated audio file: ${outputFileName} for section: ${section.title}`);
    }

    console.log('Audio generation completed successfully!');
  } catch (error) {
    console.error('Error generating audio:', error);
  }
}

// Update argument handling
const deckKey = process.argv[2];
const specificSlide = process.argv[3] ? parseInt(process.argv[3], 10) : null;
const specificClick = process.argv[4] ? parseInt(process.argv[4], 10) : null;

if (!deckKey) {
  console.error('Please provide a deck key as a command line argument.');
  process.exit(1);
}

generateAudio(deckKey, specificSlide, specificClick); 