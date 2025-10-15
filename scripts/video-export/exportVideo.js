#!/usr/bin/env node

import { Command } from 'commander';
import ora from 'ora';
import chalk from 'chalk';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';
import ffmpeg from 'fluent-ffmpeg';
import ffmpegPath from '@ffmpeg-installer/ffmpeg';
import ffprobePath from '@ffprobe-installer/ffprobe';
import { startServer, stopServer, killPortProcess } from './serverManager.js';
import { recordPresentation, estimateDuration } from './browserRecorder.js';
import { getNextVersion } from './versionManager.js';
import { getVideoInfo } from './videoProcessor.js';

// Set FFmpeg paths
ffmpeg.setFfmpegPath(ffmpegPath.path);
ffmpeg.setFfprobePath(ffprobePath.path);

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

// Global state for graceful shutdown
let isShuttingDown = false;
let currentExportState = {
  serverProcess: null,
  tempVideoPath: null,
  outputPath: null,
  deckId: null,
  browserContext: null,
  browser: null
};

/**
 * Handle graceful shutdown on interrupt
 */
async function handleShutdown(signal) {
  if (isShuttingDown) return;
  isShuttingDown = true;
  
  console.log(chalk.yellow(`\n\n${signal} received - attempting graceful shutdown...`));
  console.log(chalk.gray('This will take a few seconds to properly finalize the video...'));
  
  const { serverProcess, tempVideoPath, outputPath, deckId, browserContext, browser } = currentExportState;
  
  // Close browser
  if (browserContext || browser) {
    console.log('Closing browser...');
    try {
      if (browserContext) {
        await browserContext.close();
        console.log(chalk.gray('✓ Browser context closed'));
      }
      if (browser) {
        await browser.close();
        console.log(chalk.gray('✓ Browser closed'));
      }
      // Wait a bit for video file to be written
      await new Promise(resolve => setTimeout(resolve, 2000));
    } catch (error) {
      console.error(chalk.yellow('Warning closing browser:'), error.message);
    }
  }
  
  // Now try to save and finalize the video
  const tempDir = path.join(projectRoot, 'temp', 'video-export');
  try {
    // Find the most recent .webm file
    const files = await fs.readdir(tempDir);
    const webmFiles = files
      .filter(f => f.endsWith('.webm'))
      .map(f => ({
        name: f,
        path: path.join(tempDir, f),
        time: fs.statSync(path.join(tempDir, f)).mtime.getTime()
      }))
      .sort((a, b) => b.time - a.time);
    
    if (webmFiles.length > 0) {
      const latestVideo = webmFiles[0];
      const partialFilename = `${deckId}_PARTIAL_${Date.now()}.webm`;
      const partialPath = path.join(projectRoot, 'exports', 'videos', partialFilename);
      
      // Copy the raw video first
      await fs.copy(latestVideo.path, partialPath);
      const rawStats = await fs.stat(partialPath);
      const rawSizeMB = (rawStats.size / (1024 * 1024)).toFixed(2);
      
      console.log(chalk.green(`✓ Partial video saved: ${partialFilename} (${rawSizeMB}MB)`));
      console.log(chalk.gray(`   Location: exports/videos/${partialFilename}`));
      
      // Try to get duration info
      try {
        const { exec } = await import('child_process');
        const { promisify } = await import('util');
        const execAsync = promisify(exec);
        
        const { stdout } = await execAsync(
          `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${partialPath}"`
        );
        const duration = parseFloat(stdout);
        if (duration && !isNaN(duration)) {
          console.log(chalk.gray(`   Duration: ${Math.round(duration)}s`));
        } else {
          console.log(chalk.yellow(`   Note: Video may need repair to get duration (playable but incomplete metadata)`));
        }
      } catch (error) {
        console.log(chalk.gray(`   Duration: Unable to determine`));
      }
    } else {
      console.log(chalk.yellow('No video files found to save'));
    }
  } catch (error) {
    console.error(chalk.red('Failed to save partial video:'), error.message);
  }
  
  // Stop server
  if (serverProcess) {
    console.log('Stopping server...');
    try {
      await stopServer(serverProcess);
    } catch (error) {
      console.error('Error stopping server:', error.message);
    }
  }
  
  console.log(chalk.yellow('Shutdown complete'));
  process.exit(0);
}

// Register signal handlers
process.on('SIGINT', () => handleShutdown('SIGINT'));
process.on('SIGTERM', () => handleShutdown('SIGTERM'));

/**
 * Export a deck to video
 */
async function exportDeck(deckId, options) {
  const spinner = ora();
  let serverProcess = null;
  let tempVideoPath = null;
  
  // Update global state for shutdown handler
  currentExportState.deckId = deckId;

  try {
    console.log(chalk.gray('[Step 0] Cleaning up any existing processes...'));
    // Kill any existing export processes
    try {
      const { exec } = await import('child_process');
      const { promisify } = await import('util');
      const execAsync = promisify(exec);
      
      await execAsync('pkill -9 -f "slidev.*3030" 2>/dev/null || true');
      await execAsync('pkill -9 -f "playwright" 2>/dev/null || true');
      await execAsync('pkill -9 -f "chromium" 2>/dev/null || true');
      console.log(chalk.gray('✓ Cleaned up old processes'));
      
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (e) {
      // Ignore cleanup errors
    }
    
    console.log(chalk.gray('[Step 1] Validating deck...'));
    // Validate deck exists
    const deckPath = path.join(projectRoot, 'decks', deckId);
    const slidespath = path.join(deckPath, 'slides.md');
    
    if (!await fs.pathExists(slidespath)) {
      throw new Error(`Deck not found: ${deckId}\nExpected: ${slidespath}`);
    }

    spinner.start(`Preparing to export ${chalk.cyan(deckId)}...`);
    
    // Test mode notification
    if (options.test) {
      console.log(chalk.yellow('⚠️  TEST MODE: Recording will stop after 60 seconds'));
    }
    
    // Store deckId for graceful shutdown
    currentExportState.deckId = deckId;

    console.log(chalk.gray('[Step 2] Checking port 3030...'));
    // Kill any process using port 3030
    await killPortProcess(3030);

    console.log(chalk.gray('[Step 3] Getting version number...'));
    // Get version number
    const version = await getNextVersion(deckId);
    const outputFilename = `${deckId}_${version}.mp4`;
    const outputPath = path.join(projectRoot, 'exports', 'videos', outputFilename);

    console.log(chalk.gray(`Output: ${outputFilename}`));

    console.log(chalk.gray('[Step 4] Starting Slidev server...'));
    // Start Slidev server
    spinner.text = 'Starting Slidev server...';
    serverProcess = await startServer(deckId);
    currentExportState.serverProcess = serverProcess;
    currentExportState.outputPath = outputPath;
    spinner.succeed('Server started');

    console.log(chalk.gray('[Step 5] Estimating duration...'));
    // Estimate duration for timeout
    const estimatedDuration = await estimateDuration(deckId);
    console.log(chalk.gray(`Estimated duration: ${Math.round(estimatedDuration / 1000)}s`));

            console.log(chalk.gray('[Step 6] Recording video...'));
            const recordingMessage = options.test 
              ? 'Recording presentation (TEST MODE - 60 seconds)...' 
              : 'Recording presentation (this may take 10-20 minutes)...';
            spinner.start(recordingMessage);
            
            const recordingResult = await recordPresentation(deckId, {
              maxDuration: estimatedDuration + 60000, // Add 1 minute buffer
              width: parseInt(options.width || 1920, 10),
              height: parseInt(options.height || 1080, 10),
              testMode: options.test || false,
              onBrowserReady: ({ browser, context, page }) => {
                // Store for graceful shutdown
                currentExportState.browser = browser;
                currentExportState.browserContext = context;
                currentExportState.page = page;
              }
            });
            
            tempVideoPath = recordingResult.videoPath;
            currentExportState.tempVideoPath = tempVideoPath;
            spinner.succeed('Recording complete');

            console.log(chalk.gray('[Step 7] Converting to MP4 with 16:9 aspect ratio...'));
            spinner.start('Converting and scaling to fill 1920x1080...');
            
            await new Promise((resolve, reject) => {
              ffmpeg(tempVideoPath)
                .outputOptions([
                  '-vf scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080', // Scale to fill, then crop
                  '-c:v libx264',
                  '-preset medium',
                  '-crf 18',
                  '-pix_fmt yuv420p',
                  '-c:a aac',
                  '-b:a 192k',
                  '-movflags +faststart'
                ])
                .output(outputPath)
                .on('progress', (p) => {
                  if (p.percent) spinner.text = `Converting: ${p.percent.toFixed(1)}%`;
                })
                .on('end', () => {
                  spinner.succeed('MP4 ready (full frame 16:9)');
                  resolve();
                })
                .on('error', (err) => {
                  spinner.fail('Failed');
                  console.error(chalk.red('Error:'), err.message);
                  reject(err);
                })
                .run();
            });

    // Get video info
    const videoInfo = await getVideoInfo(outputPath);
    const sizeInMB = (videoInfo.size / (1024 * 1024)).toFixed(2);
    const durationMin = (videoInfo.duration / 60).toFixed(1);

    // Success!
    console.log('\n' + chalk.green('✓ Export completed successfully!'));
    console.log(chalk.gray('─'.repeat(50)));
    console.log(`${chalk.bold('File:')} ${outputFilename}`);
    console.log(`${chalk.bold('Path:')} ${outputPath}`);
    console.log(`${chalk.bold('Size:')} ${sizeInMB} MB`);
    console.log(`${chalk.bold('Duration:')} ${durationMin} minutes`);
    console.log(`${chalk.bold('Resolution:')} ${videoInfo.width}x${videoInfo.height}`);
    console.log(chalk.gray('─'.repeat(50)));
    console.log(chalk.gray('\nReturning control to shell...\n'));

  } catch (error) {
    spinner.fail(`Export failed: ${error.message}`);
    console.error('\n' + chalk.red('Error details:'));
    console.error(error);
    
    // Cleanup on error
    if (serverProcess) {
      try {
        await stopServer(serverProcess);
      } catch (e) {
        // Ignore
      }
    }
    
    process.exit(1);
  } finally {
    console.log(chalk.gray('Cleaning up...'));
    
    // Stop server
    if (serverProcess) {
      try {
        serverProcess.kill('SIGKILL'); // Force kill immediately
        console.log(chalk.gray('✓ Server stopped'));
      } catch (error) {
        // Ignore
      }
    }

    // Clean up temp files quickly
    if (tempVideoPath) {
      try {
        const tempDir = path.dirname(tempVideoPath);
        await fs.remove(tempDir);
        console.log(chalk.gray('✓ Cleaned up temporary files'));
      } catch (error) {
        // Ignore cleanup errors
      }
    }
    
    // Clear global state
    currentExportState = {
      serverProcess: null,
      tempVideoPath: null,
      outputPath: null,
      deckId: null,
      browser: null,
      browserContext: null
    };
    
    console.log(chalk.gray('✓ Export process complete'));
    
    // Force exit to return control
    setTimeout(() => {
      process.exit(0);
    }, 100);
  }
}

/**
 * List available decks
 */
async function listDecks() {
  try {
    const decksDir = path.join(projectRoot, 'decks');
    const entries = await fs.readdir(decksDir, { withFileTypes: true });
    
    const decks = [];
    for (const entry of entries) {
      if (entry.isDirectory() && !entry.name.startsWith('.')) {
        const slidesPath = path.join(decksDir, entry.name, 'slides.md');
        if (await fs.pathExists(slidesPath)) {
          decks.push(entry.name);
        }
      }
    }

    console.log(chalk.bold('\nAvailable decks:'));
    console.log(chalk.gray('─'.repeat(50)));
    decks.sort().forEach(deck => {
      console.log(`  ${chalk.cyan(deck)}`);
    });
    console.log(chalk.gray('─'.repeat(50)));
    console.log(`\nTotal: ${decks.length} decks\n`);
  } catch (error) {
    console.error('Error listing decks:', error);
    process.exit(1);
  }
}

// CLI Setup
const program = new Command();

program
  .name('export-video')
  .description('Export Slidev presentation decks to video')
  .version('1.0.0');

program
  .command('export')
  .description('Export a deck to video')
  .argument('<deckId>', 'Deck ID to export (e.g., FEN_GDC)')
  .option('-q, --quality <level>', 'Video quality: low, medium, high', 'medium')
  .option('--no-headless', 'Show browser window during recording')
  .option('--width <pixels>', 'Video width', '1920')
  .option('--height <pixels>', 'Video height', '1080')
  .option('--test', 'Test mode: record only 10 seconds')
  .option('--no-skip-reencode', 'Re-encode video with FFmpeg (slower but more control)')
  .action(async (deckId, options) => {
    await exportDeck(deckId, options);
  });

program
  .command('list')
  .description('List all available decks')
  .action(listDecks);

// Default action (export)
program
  .argument('[deckId]', 'Deck ID to export')
  .option('-q, --quality <level>', 'Video quality: low, medium, high', 'medium')
  .option('--no-headless', 'Show browser window during recording')
  .option('--width <pixels>', 'Video width', '1920')
  .option('--height <pixels>', 'Video height', '1080')
  .option('--test', 'Test mode: record only 10 seconds')
  .action(async (deckId, options) => {
    if (deckId) {
      await exportDeck(deckId, options);
    } else {
      program.help();
    }
  });

program.parse();

