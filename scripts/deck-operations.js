import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

async function getNextVersionNumber(deckId) {
  try {
    const files = await fs.readdir(path.join(projectRoot, 'Exports'));
    const versionRegex = new RegExp(`${deckId}_(\\d{3})\\.pdf$`);
    
    const versions = files
      .filter(file => versionRegex.test(file))
      .map(file => parseInt(file.match(versionRegex)[1]));
    
    const maxVersion = Math.max(0, ...versions);
    return String(maxVersion + 1).padStart(3, '0');
  } catch {
    return '001';
  }
}

async function runDeckOperation() {
  const [operation, deckId] = process.argv.slice(2);
  
  if (!operation || !deckId) {
    console.error('Usage: node deck-operations.js <operation> <deckId>');
    console.error('Operations: dev, build, export, preview');
    process.exit(1);
  }

  const commands = {
    dev: `slidev decks/${deckId}/slides.md --open`,
    build: `slidev build decks/${deckId}/slides.md --out dist/${deckId}`,
    preview: `slidev decks/${deckId}/slides.md --remote`,
    export: async () => {
      const version = await getNextVersionNumber(deckId);
      return `slidev export decks/${deckId}/slides.md --output Exports/${deckId}_${version}.pdf`;
    }
  };

  try {
    const command = commands[operation];
    if (!command) {
      throw new Error(`Unknown operation: ${operation}`);
    }

    const finalCommand = typeof command === 'function' ? await command() : command;
    
    // Execute the command using the native Node.js exec
    const { exec } = await import('child_process');
    exec(finalCommand, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error: ${error.message}`);
        return;
      }
      if (stderr) {
        console.error(`Stderr: ${stderr}`);
        return;
      }
      console.log(`Operation completed successfully: ${stdout}`);
    });
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

runDeckOperation(); 