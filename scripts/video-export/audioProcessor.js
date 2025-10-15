import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';
import { promisify } from 'util';
import ffmpegStatic from '@ffmpeg-installer/ffmpeg';

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Parse audio_script.md to get the ordered list of audio files
 */
async function parseAudioScript(deckId) {
  const audioScriptPath = path.join(projectRoot, 'decks', deckId, 'audio', 'audio_script.md');
  
  try {
    const content = await fs.readFile(audioScriptPath, 'utf-8');
    const audioFiles = [];
    
    // Parse lines that contain audio file references
    // Format examples:
    // - FEN_GDC1_1.mp3
    // - **FEN_GDC2_1.mp3**
    const lines = content.split('\n');
    for (const line of lines) {
      const match = line.match(new RegExp(`(${deckId}\\d+_\\d+\\.mp3)`, 'i'));
      if (match) {
        audioFiles.push(match[1]);
      }
    }
    
    return audioFiles;
  } catch (error) {
    console.error(`Error parsing audio script: ${error.message}`);
    // Fallback: read all MP3 files from the audio directory
    return await getAllAudioFiles(deckId);
  }
}

/**
 * Fallback: Get all audio files from the audio directory in sorted order
 */
async function getAllAudioFiles(deckId) {
  const audioDir = path.join(projectRoot, 'decks', deckId, 'audio', 'oai');
  
  try {
    const files = await fs.readdir(audioDir);
    const mp3Files = files
      .filter(f => f.endsWith('.mp3') && f.startsWith(deckId))
      .sort((a, b) => {
        // Sort by slide number then click number
        // Format: FEN_GDC1_1.mp3 -> [1, 1]
        const aMatch = a.match(/(\d+)_(\d+)\.mp3$/);
        const bMatch = b.match(/(\d+)_(\d+)\.mp3$/);
        
        if (!aMatch || !bMatch) return 0;
        
        const aSlide = parseInt(aMatch[1], 10);
        const aClick = parseInt(aMatch[2], 10);
        const bSlide = parseInt(bMatch[1], 10);
        const bClick = parseInt(bMatch[2], 10);
        
        if (aSlide !== bSlide) {
          return aSlide - bSlide;
        }
        return aClick - bClick;
      });
    
    return mp3Files;
  } catch (error) {
    console.error(`Error reading audio directory: ${error.message}`);
    return [];
  }
}

/**
 * Combine all audio files for a deck into a single audio file
 * @param {string} deckId - The deck ID
 * @param {boolean} testMode - If true, only use first ~10 seconds of audio
 */
export async function combineAudioFiles(deckId, testMode = false) {
  console.log(`Combining audio files for ${deckId}...`);
  
  // Get list of audio files in order
  let audioFiles = await parseAudioScript(deckId);
  
  // If parsing failed, use fallback to scan directory
  if (audioFiles.length === 0) {
    console.log('Audio script parsing found no files, using directory scan...');
    audioFiles = await getAllAudioFiles(deckId);
  }
  
  if (audioFiles.length === 0) {
    throw new Error(`No audio files found for ${deckId}`);
  }
  
  // In test mode, limit to first few audio files (~60 seconds)
  if (testMode) {
    // Take first 24 audio files (roughly 60 seconds)
    audioFiles = audioFiles.slice(0, 24);
    console.log(`Test mode: Using only first ${audioFiles.length} audio files (~60 seconds)`);
  } else {
    console.log(`Found ${audioFiles.length} audio files to combine`);
  }
  
  console.log('First few audio files:', audioFiles.slice(0, 3));
  
  const audioDir = path.join(projectRoot, 'decks', deckId, 'audio', 'oai');
  const tempDir = path.join(projectRoot, 'temp', 'video-export');
  await fs.mkdir(tempDir, { recursive: true });
  
  // Create a concat file for FFmpeg
  const concatFilePath = path.join(tempDir, `${deckId}_concat.txt`);
  const concatContent = audioFiles
    .map(file => `file '${path.join(audioDir, file)}'`)
    .join('\n');
  
  await fs.writeFile(concatFilePath, concatContent, 'utf-8');
  
  // Output path for combined audio
  const combinedAudioPath = path.join(tempDir, `${deckId}_combined_audio.mp3`);
  
  // Use FFmpeg to concatenate audio files
  const ffmpegCmd = `"${ffmpegStatic.path}" -f concat -safe 0 -i "${concatFilePath}" -c copy "${combinedAudioPath}"`;
  
  console.log('Running FFmpeg to combine audio...');
  try {
    // Add a timeout to prevent hanging (30 seconds should be plenty)
    const { stdout, stderr } = await Promise.race([
      execAsync(ffmpegCmd),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('FFmpeg audio combine timeout after 30s')), 30000)
      )
    ]);
    if (stderr && !stderr.includes('time=')) {
      console.log('FFmpeg output:', stderr);
    }
  } catch (error) {
    console.error('FFmpeg error:', error.message);
    throw new Error(`Failed to combine audio files: ${error.message}`);
  }
  
  // Verify output file exists
  const stats = await fs.stat(combinedAudioPath);
  if (stats.size === 0) {
    throw new Error('Combined audio file is empty');
  }
  
  console.log(`✓ Combined audio saved: ${combinedAudioPath} (${(stats.size / 1024 / 1024).toFixed(2)} MB)`);
  
  return combinedAudioPath;
}

/**
 * Get the duration of an audio file in seconds
 */
export async function getAudioDuration(audioPath) {
  const ffprobeCmd = `"${ffmpegStatic.path}" -i "${audioPath}" 2>&1 | grep "Duration" | cut -d ' ' -f 4 | sed s/,//`;
  
  try {
    const { stdout } = await execAsync(ffprobeCmd);
    const timeStr = stdout.trim(); // Format: HH:MM:SS.ms
    const [hours, minutes, seconds] = timeStr.split(':').map(parseFloat);
    return hours * 3600 + minutes * 60 + seconds;
  } catch (error) {
    console.warn(`Could not get audio duration: ${error.message}`);
    return 0;
  }
}
