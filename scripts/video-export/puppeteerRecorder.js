import puppeteer from 'puppeteer';
import { PuppeteerScreenRecorder } from 'puppeteer-screen-recorder';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Use Puppeteer Screen Recorder - designed for audio/video capture
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
  let recorder;
  
  try {
    console.log('🚀 Launching Puppeteer with audio support...');
    
    browser = await puppeteer.launch({
      headless: 'new', // New headless supports more features
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--autoplay-policy=no-user-gesture-required',
        '--use-fake-ui-for-media-stream',
        '--enable-usermedia-screen-capturing',
        `--window-size=${width},${height}`,
      ],
      defaultViewport: { width, height }
    });

    page = await browser.newPage();
    await page.setViewport({ width, height });
    
    const url = `http://localhost:3030/1?deckId=${deckId}`;
    const tempDir = path.join(projectRoot, 'temp', 'video-export');
    await fs.ensureDir(tempDir);
    const outputPath = path.join(tempDir, `${deckId}_capture.mp4`);

    if (onBrowserReady) {
      onBrowserReady({ browser, page });
    }

    console.log(`Loading ${url}...`);
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 });
    
    await page.waitForSelector('.slidev-layout', { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(3000);
    
    console.log('✅ Page loaded');
    
    // Force audio to work
    await page.evaluate(() => {
      if (window.Howler) {
        window.Howler.mute(false);
        window.Howler.volume(1.0);
        if (window.Howler.ctx && window.Howler.ctx.state === 'suspended') {
          window.Howler.ctx.resume();
        }
      }
    });

    console.log('🎥 Starting screen recorder with audio...');
    
    recorder = new PuppeteerScreenRecorder(page, {
      followNewTab: false,
      fps: 30,
      videoFrame: {
        width,
        height
      },
      aspectRatio: '16:9',
      recordDurationLimit: testMode ? 65 : maxDuration / 1000,
    });

    await recorder.start(outputPath);
    console.log('✅ Recording started (video + audio)');

    // Start playback
    console.log('▶️  Starting playback...');
    await page.keyboard.press('a');

    // Wait
    if (testMode) {
      console.log('⏱️  Test: 60 seconds...');
      await new Promise(resolve => setTimeout(resolve, 60000));
    } else {
      await new Promise(resolve => setTimeout(resolve, maxDuration));
    }

    // Stop
    console.log('💾 Stopping recording...');
    await recorder.stop();
    console.log('✅ Recording stopped');

    await browser.close();
    console.log('✅ Browser closed');
    
    const stats = await fs.stat(outputPath);
    console.log(`📊 File size: ${(stats.size / 1024 / 1024).toFixed(2)} MB`);

    return { videoPath: outputPath };

  } catch (error) {
    console.error('❌ Error:', error);
    if (recorder) {
      try { await recorder.stop(); } catch (e) {}
    }
    if (browser) {
      try { await browser.close(); } catch (e) {}
    }
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

