import fs from 'fs/promises';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function generateImages(deckKey) {
  try {
    const pdfPath = path.join(process.cwd(), `decks/${deckKey}/${deckKey}.pdf`);
    const outputDir = path.join(process.cwd(), `decks/${deckKey}/img`);

    // Ensure the output directory exists
    try {
      await fs.access(outputDir);
    } catch {
      await fs.mkdir(outputDir, { recursive: true });
    }

    // Convert PDF to images using pdftoppm (part of poppler-utils)
    // Format will be: {deckKey}-{page}.jpg
    const command = `pdftoppm -jpeg -r 300 "${pdfPath}" "${path.join(outputDir, deckKey)}"`;
    
    console.log('Converting PDF to images...');
    const { stdout, stderr } = await execAsync(command);
    
    if (stderr) {
      console.error('Warning during conversion:', stderr);
    }

    console.log('PDF conversion completed successfully!');
    console.log('Images have been saved to:', outputDir);
    
  } catch (error) {
    console.error('Error generating images:', error);
    if (error.message.includes('pdftoppm')) {
      console.error('\nPlease ensure poppler-utils is installed:');
      console.error('- On macOS: brew install poppler');
      console.error('- On Ubuntu/Debian: sudo apt-get install poppler-utils');
      console.error('- On Windows: Install from http://blog.alivate.com.au/poppler-windows/');
    }
  }
}

// Check if a deck key was provided as a command line argument
const deckKey = process.argv[2];
if (!deckKey) {
  console.error('Please provide a deck key as a command line argument.');
  process.exit(1);
}

generateImages(deckKey); 