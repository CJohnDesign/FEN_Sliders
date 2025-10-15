import { chromium } from 'playwright-chromium';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';
import { execSync } from 'child_process';
import ffmpegPath from '@ffmpeg-installer/ffmpeg';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Check if BlackHole is installed
 */
function checkBlackHole() {
  try {
    const devices = execSync('ffmpeg -f avfoundation -list_devices true -i "" 2>&1 || true').toString();
    const hasBlackHole = devices.includes('BlackHole');
    return hasBlackHole;
  } catch (e) {
    return false;
  }
}

/**
 * Get BlackHole device index
 */
function getBlackHoleIndex() {
  try {
    const output = execSync('ffmpeg -f avfoundation -list_devices true -i "" 2>&1 || true').toString();
    const lines = output.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes('BlackHole') && lines[i].includes('AVFoundation audio device')) {
        const match = lines[i].match(/\[(\d+)\]/);
        if (match) {
          return match[1];
        }
      }
    }
  } catch (e) {}
  return null;
}

/**
 * Record using BlackHole virtual audio device
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
  let page;
  let ffmpegProc;
  
  try {
    // Check for BlackHole
    console.log('🔍 Checking for BlackHole virtual audio device...');
    const hasBlackHole = checkBlackHole();
    
    if (!hasBlackHole) {
      console.log('⚠️  BlackHole not found. Install with: brew install blackhole-2ch');
      console.log('⚠️  Falling back to screen + microphone capture');
    } else {
      console.log('✅ BlackHole detected');
    }
    
    const blackholeIndex = getBlackHoleIndex();
    console.log(`BlackHole audio device index: ${blackholeIndex || 'not found'}`);

    const url = `http://localhost:3030/1?deckId=${deckId}`;
    const tempDir = path.join(projectRoot, 'temp', 'video-export');
    await fs.ensureDir(tempDir);
    const outputPath = path.join(tempDir, `${deckId}_capture.mp4`);

    console.log('🚀 Launching headed browser...');
    
    browser = await chromium.launch({
      headless: false,
      args: [
        '--no-sandbox',
        '--autoplay-policy=no-user-gesture-required',
        `--window-size=${width},${height}`,
        '--kiosk', // Fullscreen
      ],
    });

    const context = await browser.newContext({
      viewport: { width, height },
      ignoreHTTPSErrors: true,
    });

    page = await context.newPage();
    
    if (onBrowserReady) {
      onBrowserReady({ browser, page });
    }

    console.log(`Loading ${url}...`);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('.slidev-layout', { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(3000);
    
    console.log('✅ Page ready');
    console.log('\n🎥 Starting FFmpeg screen + audio capture...');
    console.log('📹 This will capture the browser window - keep it visible');
    
    // Start FFmpeg capture
    const ffmpegArgs = [
      '-f', 'avfoundation',
      '-capture_cursor', '0',
      '-framerate', '30',
      '-i', blackholeIndex ? `1:${blackholeIndex}` : '1:0', // Screen 1, BlackHole or default audio
      '-c:v', 'libx264',
      '-preset', 'ultrafast',
      '-crf', '18',
      '-pix_fmt', 'yuv420p',
      '-c:a', 'aac',
      '-b:a', '192k',
      '-y',
      outputPath
    ];
    
    console.log('FFmpeg command:', ffmpegArgs.join(' '));
    
    ffmpegProc = spawn(ffmpegPath.path, ffmpegArgs, {
      stdio: ['pipe', 'pipe', 'pipe']
    });
    
    ffmpegProc.stderr.on('data', (data) => {
      const line = data.toString();
      if (line.includes('Press [q]')) {
        console.log('✅ FFmpeg recording started');
      }
    });
    
    // Wait for FFmpeg to initialize
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    console.log('▶️  Starting playback...');
    await page.keyboard.press('a');
    
    // Wait
    if (testMode) {
      console.log('⏱️  60 seconds...');
      await new Promise(resolve => setTimeout(resolve, 60000));
    } else {
      await new Promise(resolve => setTimeout(resolve, maxDuration));
    }

    // Stop FFmpeg
    console.log('\n💾 Stopping recording...');
    ffmpegProc.stdin.write('q');
    
    await new Promise((resolve) => {
      ffmpegProc.on('close', (code) => {
        console.log(`FFmpeg exited with code ${code}`);
        resolve();
      });
      setTimeout(() => {
        if (ffmpegProc) {
          ffmpegProc.kill('SIGTERM');
          resolve();
        }
      }, 5000);
    });
    
    await browser.close();
    console.log('✅ Recording complete');
    
    const stats = await fs.stat(outputPath);
    console.log(`📊 File: ${(stats.size / 1024 / 1024).toFixed(2)} MB`);

    return { videoPath: outputPath };

  } catch (error) {
    console.error('❌ Error:', error);
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

