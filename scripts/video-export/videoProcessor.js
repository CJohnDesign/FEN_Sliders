import ffmpeg from 'fluent-ffmpeg';
import ffmpegPath from '@ffmpeg-installer/ffmpeg';
import ffprobePath from '@ffprobe-installer/ffprobe';
import fs from 'fs-extra';
import path from 'path';

// Set FFmpeg paths
ffmpeg.setFfmpegPath(ffmpegPath.path);
ffmpeg.setFfprobePath(ffprobePath.path);

/**
 * Process and merge video with audio
 * @param {string} videoPath - Path to video file (no audio)
 * @param {string} outputPath - Path for final MP4
 * @param {string} audioPath - Path to audio file  
 * @param {object} options - FFmpeg options
 */
export async function processVideo(videoPath, outputPath, audioPath, options = {}) {
  const {
    videoCodec = 'libx264',
    audioCodec = 'aac',
    preset = 'medium',
    crf = 18,
    audioBitrate = '192k',
    pixelFormat = 'yuv420p'
  } = options;

  return new Promise(async (resolve, reject) => {
    try {
      // Ensure output directory exists
      await fs.ensureDir(path.dirname(outputPath));

      console.log('Merging video and audio with FFmpeg...');
      console.log(`  Video: ${videoPath}`);
      console.log(`  Audio: ${audioPath}`);
      console.log(`  Output: ${outputPath}`);

      ffmpeg()
        .input(videoPath)
        .input(audioPath)
        .outputOptions([
          `-c:v ${videoCodec}`,
          `-preset ${preset}`,
          `-crf ${crf}`,
          `-pix_fmt ${pixelFormat}`,
          `-c:a ${audioCodec}`,
          `-b:a ${audioBitrate}`,
          '-shortest' // End when shortest stream ends (critical for sync!)
        ])
        .output(outputPath)
        .on('start', (commandLine) => {
          console.log('FFmpeg command:', commandLine);
        })
        .on('progress', (progress) => {
          if (progress.percent) {
            process.stdout.write(`\rMerging: ${progress.percent.toFixed(1)}%`);
          }
        })
        .on('end', () => {
          console.log(`\n✓ Video with audio saved: ${outputPath}`);
          resolve(outputPath);
        })
        .on('error', (error) => {
          console.error('FFmpeg error:', error);
          reject(error);
        })
        .run();
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Get video duration in seconds
 */
export async function getVideoDuration(videoPath) {
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(videoPath, (error, metadata) => {
      if (error) {
        reject(error);
      } else {
        resolve(metadata.format.duration);
      }
    });
  });
}

/**
 * Get video file info
 */
export async function getVideoInfo(videoPath) {
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(videoPath, (error, metadata) => {
      if (error) {
        reject(error);
      } else {
        resolve({
          duration: metadata.format.duration,
          size: metadata.format.size,
          bitRate: metadata.format.bit_rate,
          format: metadata.format.format_name,
          width: metadata.streams[0]?.width,
          height: metadata.streams[0]?.height
        });
      }
    });
  });
}

