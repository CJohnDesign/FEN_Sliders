import { chromium } from 'playwright-chromium';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';
import ffmpegPath from '@ffmpeg-installer/ffmpeg';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Record using FFmpeg screen capture (macOS)
 * Captures actual screen and system audio
 */
export async function recordPresentation(deckId, options = {}) {
  const {
    maxDuration = 1200000,
    width = 1920,
    height = 1080,
    testMode = false,
    onBrowserReady = null
  } = options;

  let browser;
  let context;
  let page;
  let ffmpegProc;
  
  try {
    console.log('Launching browser window...');
    
    // Launch HEADED browser
    browser = await chromium.launch({
      headless: false,
      args: [
        '--no-sandbox',
        '--autoplay-policy=no-user-gesture-required',
        `--window-size=${width},${height}`,
        '--start-fullscreen', // Fullscreen for clean capture
      ],
    });

    const url = `http://localhost:3030/1?deckId=${deckId}`;
    const tempDir = path.join(projectRoot, 'temp', 'video-export');
    await fs.ensureDir(tempDir);
    const outputPath = path.join(tempDir, `${deckId}_capture.mp4`);

    context = await browser.newContext({
      viewport: { width, height },
      ignoreHTTPSErrors: true,
    });

    page = await context.newPage();
    
    if (onBrowserReady) {
      onBrowserReady({ browser, context, page });
    }
    
    // Load page
    console.log(`Loading ${url}...`);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('.slidev-layout', { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(3000);
    
    console.log('✓ Page ready');
    
    // Start FFmpeg screen capture
    console.log('Starting FFmpeg screen capture...');
    console.log('⚠️  Please select the browser window when prompted');
    
    const ffmpegArgs = [
      '-f', 'avfoundation',
      '-capture_cursor', '0',
      '-framerate', '30',
      '-i', '1:0', // Screen 1, audio device 0
      '-c:v', 'libx264',
      '-preset', 'ultrafast',
      '-crf', '18',
      '-pix_fmt', 'yuv420p',
      '-c:a', 'aac',
      '-b:a', '192k',
      '-y',
      outputPath
    ];
    
    ffmpegProc = spawn(ffmpegPath.path.replace('/ffmpeg', ''), ffmpegArgs);
    
    ffmpegProc.stderr.on('data', (data) => {
      const line = data.toString();
      if (line.includes('frame=')) {
        process.stdout.write('.');
      }
    });
    
    // Wait for FFmpeg to start
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    console.log('\n✓ Recording started');
    console.log('Starting playback...');
    await page.keyboard.press('a');
    
    // Track completion
    let complete = false;
    page.on('console', (msg) => {
      if (msg.text().includes('[End Detection] Last audio complete')) {
        complete = true;
      }
    });
    
    // Wait
    if (testMode) {
      console.log('⏱️  Test: 60 seconds...');
      await new Promise(resolve => setTimeout(resolve, 60000));
    } else {
      const duration = testMode ? 60000 : maxDuration;
      await new Promise(resolve => setTimeout(resolve, duration));
    }

    // Stop FFmpeg
    console.log('\nStopping recording...');
    ffmpegProc.stdin.write('q');
    
    await new Promise((resolve) => {
      ffmpegProc.on('close', resolve);
      setTimeout(() => {
        ffmpegProc.kill('SIGTERM');
        resolve();
      }, 5000);
    });
    
    // Close browser
    await browser.close();
    console.log('✓ Recording complete');

    return { videoPath: outputPath };

  } catch (error) {
    if (ffmpegProc) ffmpegProc.kill();
    if (browser) try { await browser.close(); } catch (e) {}
    throw error;
  }
}

export async function estimateDuration(deckId) {
  const audioDir = path.join(projectRoot, 'decks', deckId, 'audio', 'oai');
  try {
    const files = await fs.readdir(audioDir);
    return files.filter(f => f.endsWith('.mp3')).length * 30 * 1000;
  } catch (error) {
    return 1200000;
  }
}

