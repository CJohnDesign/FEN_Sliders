import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';
import { promisify } from 'util';
import ffprobeStatic from '@ffprobe-installer/ffprobe';

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Get the duration of an audio file in milliseconds
 */
async function getAudioFileDuration(filePath) {
  try {
    const { stdout } = await execAsync(
      `"${ffprobeStatic.path}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${filePath}"`
    );
    const durationInSeconds = parseFloat(stdout.trim());
    return durationInSeconds * 1000; // Convert to milliseconds
  } catch (error) {
    console.error(`Error getting duration for ${filePath}:`, error.message);
    return 0;
  }
}

/**
 * Get all audio files for a deck with their durations
 * Returns an array of { slide, click, filename, duration } objects
 */
export async function getAudioTimeline(deckId, testMode = false) {
  const audioDir = path.join(projectRoot, 'decks', deckId, 'audio', 'oai');
  
  try {
    const files = await fs.readdir(audioDir);
    const mp3Files = files
      .filter(file => file.endsWith('.mp3'))
      .map(file => {
        const match = file.match(new RegExp(`${deckId}(\\d+)_(\\d+)\\.mp3`));
        if (match) {
          return {
            slide: parseInt(match[1], 10),
            click: parseInt(match[2], 10),
            filename: file,
            path: path.join(audioDir, file)
          };
        }
        return null;
      })
      .filter(Boolean);

    // Sort files by slide and click number
    mp3Files.sort((a, b) => {
      if (a.slide !== b.slide) {
        return a.slide - b.slide;
      }
      return a.click - b.click;
    });

    // In test mode, only use first few files
    const filesToProcess = testMode ? mp3Files.slice(0, 4) : mp3Files;

    // Get durations for all files
    console.log(`Getting durations for ${filesToProcess.length} audio files...`);
    const timeline = [];
    
    for (const file of filesToProcess) {
      const duration = await getAudioFileDuration(file.path);
      timeline.push({
        slide: file.slide,
        click: file.click,
        filename: file.filename,
        duration: duration
      });
    }

    // Calculate cumulative timing
    let cumulativeTime = 0;
    const timelineWithTimestamps = timeline.map(item => {
      const startTime = cumulativeTime;
      cumulativeTime += item.duration;
      return {
        ...item,
        startTime: startTime,
        endTime: cumulativeTime
      };
    });

    const totalDuration = cumulativeTime;
    console.log(`✓ Audio timeline generated: ${timeline.length} files, ${(totalDuration / 1000).toFixed(1)}s total`);

    return {
      timeline: timelineWithTimestamps,
      totalDuration: totalDuration
    };

  } catch (error) {
    console.error(`Error building audio timeline: ${error.message}`);
    throw error;
  }
}

/**
 * Generate a JavaScript snippet that can be injected into the page to handle timed playback
 */
export function generatePlaybackScript(timeline) {
  return `
window.__audioTimeline = ${JSON.stringify(timeline)};
window.__currentIndex = 0;
window.__timelineStartTime = null;
window.__playbackActive = false;

window.startTimedPlayback = function() {
  if (window.__playbackActive) return;
  
  window.__playbackActive = true;
  window.__timelineStartTime = Date.now();
  window.__currentIndex = 0;
  
  console.log('[Timed Playback] Starting with', window.__audioTimeline.length, 'audio segments');
  
  // Schedule all slide advances based on audio timeline
  window.__audioTimeline.forEach((segment, index) => {
    setTimeout(() => {
      if (!window.__playbackActive) return;
      
      console.log(\`[Timed Playback] Advancing to slide \${segment.slide}, click \${segment.click}\`);
      
      // Advance to next slide (trigger Slidev navigation)
      const nav = window.$slidev?.nav;
      if (nav && index > 0) { // Don't advance on first audio (already on slide 1)
        nav.next();
      }
      
      window.__currentIndex = index;
    }, segment.startTime);
  });
  
  // Mark completion after last audio
  const lastSegment = window.__audioTimeline[window.__audioTimeline.length - 1];
  setTimeout(() => {
    console.log('[Timed Playback] Playback complete!');
    console.log('[End Detection] Presentation Complete!');
    window.__playbackActive = false;
  }, lastSegment.endTime);
};

// Auto-start when 'A' key is pressed
document.addEventListener('keydown', (event) => {
  if (event.key.toLowerCase() === 'a' && !window.__playbackActive) {
    window.startTimedPlayback();
  }
});

console.log('[Timed Playback] Timeline loaded and ready');
`;
}


