import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Get the next version number for a deck video export
 * Scans exports/videos/ directory for existing versions
 * Returns next version number padded to 3 digits (001, 002, etc.)
 */
export async function getNextVersion(deckId) {
  try {
    const videosDir = path.join(projectRoot, 'exports', 'videos');
    
    // Ensure directory exists
    await fs.mkdir(videosDir, { recursive: true });
    
    const files = await fs.readdir(videosDir);
    const versionRegex = new RegExp(`${deckId}_(\\d{3})\\.mp4$`);
    
    const versions = files
      .filter(file => versionRegex.test(file))
      .map(file => parseInt(file.match(versionRegex)[1]));
    
    const maxVersion = Math.max(0, ...versions);
    return String(maxVersion + 1).padStart(3, '0');
  } catch (error) {
    console.error('Error getting next version:', error);
    return '001';
  }
}

/**
 * Get all existing versions for a deck
 */
export async function getExistingVersions(deckId) {
  try {
    const videosDir = path.join(projectRoot, 'exports', 'videos');
    const files = await fs.readdir(videosDir);
    const versionRegex = new RegExp(`${deckId}_(\\d{3})\\.mp4$`);
    
    return files
      .filter(file => versionRegex.test(file))
      .map(file => file.match(versionRegex)[1])
      .sort();
  } catch (error) {
    return [];
  }
}

