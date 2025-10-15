import { chromium } from 'playwright-chromium';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Use system Chrome for perfect rendering + audio capture
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
  
  try {
    const url = `http://localhost:3030/1`;
    const tempDir = path.join(projectRoot, 'temp', 'video-export');
    await fs.ensureDir(tempDir);
    const outputPath = path.join(tempDir, `${deckId}_capture.webm`);
    
    console.log('🚀 Launching Chrome...');
    
    const chromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
    
    if (!fs.existsSync(chromePath)) {
      throw new Error('Google Chrome not found');
    }
    
    browser = await chromium.launch({
      headless: false,
      executablePath: chromePath,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--autoplay-policy=no-user-gesture-required',
        '--start-maximized',
        `--window-size=${width},${height}`,
      ],
    });

    context = await browser.newContext({
      viewport: null,
      ignoreHTTPSErrors: true,
    });

    page = await context.newPage();
    
    if (onBrowserReady) {
      onBrowserReady({ browser, context, page });
    }

    console.log(`Loading ${url}...`);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('.slidev-layout', { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(2000);
    
    console.log('✅ Page loaded');
    console.log('');
    console.log('⚠️  YOU HAVE 5 SECONDS:');
    console.log('    1. Press F to enter Slidev fullscreen (fills screen perfectly)');
    console.log('    2. Make sure presentation looks correct');
    console.log('');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    console.log('✅ Ready to capture');
    console.log('🎬 Starting capture...');
    console.log('⚠️  Screen picker will appear:');
    console.log('    1. Select "Chrome Tab"');
    console.log('    2. Check "Share tab audio"');
    console.log('    3. Click Share');
    
    // Start recording
    await page.evaluate(() => {
      return new Promise(async (resolve, reject) => {
        try {
          console.log('[Recorder] Requesting tab capture with audio...');
          
          const stream = await navigator.mediaDevices.getDisplayMedia({
            video: {
              width: { ideal: 1920 },
              height: { ideal: 1080 },
              frameRate: { ideal: 30 }
            },
            audio: true,
            preferCurrentTab: true
          });
          
          console.log('[Recorder] Stream acquired:', {
            video: stream.getVideoTracks().length,
            audio: stream.getAudioTracks().length,
            videoSettings: stream.getVideoTracks()[0]?.getSettings()
          });
          
          const recorder = new MediaRecorder(stream, {
            mimeType: 'video/webm;codecs=vp9,opus',
            videoBitsPerSecond: 5000000,
            audioBitsPerSecond: 192000
          });
          
          window.__chunks = [];
          
          recorder.ondataavailable = e => {
            if (e.data.size > 0) {
              window.__chunks.push(e.data);
            }
          };
          
          recorder.onstop = () => {
            const blob = new Blob(window.__chunks, { type: 'video/webm' });
            window.__blob = blob;
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'recording.webm';
            a.click();
            console.log('[Recorder] Saved:', blob.size, 'bytes');
          };
          
          recorder.start(1000);
          window.__recorder = recorder;
          console.log('[Recorder] Recording started!');
          
          resolve();
        } catch (error) {
          console.error('[Recorder] Error:', error.message);
          reject(error);
        }
      });
    });
    
    console.log('✅ Recording active');
    console.log('⏳ Waiting 1 second then starting playback...');
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    console.log('▶️  Starting playback...');
    await page.keyboard.press('a');
    
    // Wait for presentation to end by detecting the completion signal
    if (testMode) {
      console.log('⏱️  Recording for 60 seconds...');
      await new Promise(resolve => setTimeout(resolve, 60000));
    } else {
      console.log('⏱️  Monitoring presentation (waiting for completion signal)...');
      
      // Listen for the "[End Detection] Presentation Complete!" message
      const presentationComplete = new Promise((resolve) => {
        page.on('console', msg => {
          const text = msg.text();
          
          // Show all end detection messages
          if (text.includes('[End Detection]')) {
            console.log(`[Browser] ${text}`);
          }
          
          // Detect completion signal from SlideAudio.vue
          if (text.includes('[End Detection] Presentation Complete!')) {
            console.log('✅ Presentation complete signal received!');
            resolve();
          }
        });
      });
      
      // Wait for completion (with timeout)
      const timeout = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Presentation timeout')), maxDuration);
      });
      
      await Promise.race([presentationComplete, timeout]);
      
      // Extra buffer after completion signal
      console.log('⏱️  Adding 3 second buffer for cleanup...');
      await new Promise(resolve => setTimeout(resolve, 3000));
    }

    // Stop and save
    console.log('💾 Saving recording...');
    const download = page.waitForEvent('download', { timeout: 10000 });
    
    await page.evaluate(() => {
      if (window.__recorder) {
        window.__recorder.stop();
      }
    });
    
    const dl = await download;
    await dl.saveAs(outputPath);
    
    await browser.close();
    
    const stats = await fs.stat(outputPath);
    console.log(`✅ Saved: ${(stats.size / 1024 / 1024).toFixed(2)} MB`);

    return { videoPath: outputPath };

  } catch (error) {
    console.error('❌ Error:', error);
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
