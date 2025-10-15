import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';
import ffmpeg from 'fluent-ffmpeg';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Merge video with individual audio files at precise timestamps
 * Uses measured timing data to place each audio exactly where it was played
 */
export async function mergeVideoWithTimedAudio(videoPath, deckId, audioEvents, trimStart, outputPath, testMode = false) {
  const audioDir = path.join(projectRoot, 'decks', deckId, 'audio', 'oai');
  
  console.log('Building audio timeline...');
  
  const audioTimeline = [];
  
  for (let i = 0; i < audioEvents.length; i++) {
    const event = audioEvents[i];
    const audioFile = `${deckId}${event.slide}_${event.click}.mp3`;
    const audioPath = path.join(audioDir, audioFile);
    
    if (await fs.pathExists(audioPath)) {
      // Adjust: event.timestamp is absolute from recording start
      // Subtract trim point to get position in final video
      // Add progressive delay: 50ms per track to compensate for browser processing
      const baseTime = event.timestamp - trimStart;
      const progressiveDelay = i * 0.05; // 50ms per track
      const adjustedTime = baseTime + progressiveDelay;
      
      if (adjustedTime >= 0) {
        audioTimeline.push({
          file: audioPath,
          startTime: adjustedTime,
          slide: event.slide,
          click: event.click
        });
        console.log(`  ${event.slide}_${event.click} at ${adjustedTime.toFixed(2)}s (+${(progressiveDelay * 1000).toFixed(0)}ms progressive)`);
      }
    } else {
      console.log(`  ⚠️  Not found: ${audioFile}`);
    }
  }
  
  console.log(`✓ Mapped ${audioTimeline.length} audio files to exact timestamps`);
  
  console.log(`✓ Trimming video at ${trimStart.toFixed(2)}s`);
  
  // Build FFmpeg command with multiple audio inputs
  return new Promise((resolve, reject) => {
    const cmd = ffmpeg();
    
    // Add trimmed video input
    cmd.input(videoPath)
      .inputOptions([`-ss ${trimStart}`]);
    
    // Add each audio file as an input
    audioTimeline.forEach(audio => {
      cmd.input(audio.file);
    });
    
    // Build complex filter to overlay all audio at precise times
    let filterComplex = '';
    const audioStreams = [];
    
    audioTimeline.forEach((audio, index) => {
      const inputIndex = index + 1; // +1 because video is input 0
      const startTime = audio.startTime;
      
      if (startTime >= 0) {
        // Delay this audio to its precise timestamp
        filterComplex += `[${inputIndex}:a]adelay=${Math.round(startTime * 1000)}|${Math.round(startTime * 1000)}[a${index}];`;
        audioStreams.push(`[a${index}]`);
        
        console.log(`  Audio ${audio.slide}_${audio.click} at ${startTime.toFixed(2)}s`);
      }
    });
    
    // Mix all audio streams together
    if (audioStreams.length > 0) {
      filterComplex += `${audioStreams.join('')}amix=inputs=${audioStreams.length}:duration=longest[aout]`;
    }
    
    const outputOptions = [
      '-map 0:v', // Use video from first input (trimmed)
    ];
    
    if (audioStreams.length > 0) {
      outputOptions.push(
        `-filter_complex ${filterComplex}`,
        '-map [aout]' // Use mixed audio output
      );
    }
    
    outputOptions.push(
      '-c:v libx264',
      '-preset medium',
      '-crf 18',
      '-pix_fmt yuv420p',
      '-c:a aac',
      '-b:a 192k',
      '-movflags +faststart'
    );
    
    cmd.outputOptions(outputOptions)
      .output(outputPath)
      .on('start', (cmdLine) => {
        console.log('Starting FFmpeg with individual audio timing...');
      })
      .on('progress', (progress) => {
        if (progress.percent) {
          console.log(`Processing: ${progress.percent.toFixed(1)}%`);
        }
      })
      .on('end', () => {
        console.log('✓ Video merged with individually-timed audio tracks');
        resolve();
      })
      .on('error', (error) => {
        console.error('FFmpeg error:', error.message);
        reject(error);
      })
      .run();
  });
}

