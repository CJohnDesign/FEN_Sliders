import { chromium } from 'playwright-chromium';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Dual browser approach:
 * - Headless: perfect video rendering
 * - Headed: capture actual Howler audio
 * Both play simultaneously, then merge
 */
export async function recordPresentation(deckId, options = {}) {
  const {
    maxDuration = 1200000,
    width = 1920,
    height = 1080,
    testMode = false,
    onBrowserReady = null
  } = options;

  let headlessBrowser, headedBrowser;
  let headlessContext, headedContext;
  let headlessPage, headedPage;
  
  try {
    const url = `http://localhost:3030/1?deckId=${deckId}`;
    const tempDir = path.join(projectRoot, 'temp', 'video-export');
    await fs.ensureDir(tempDir);
    const videoPath = path.join(tempDir, `${deckId}_video.webm`);
    const audioPath = path.join(tempDir, `${deckId}_audio.webm`);

    console.log('🎬 DUAL BROWSER APPROACH');
    console.log('Starting Browser 1: HEADLESS (perfect video)...');
    
    // Browser 1: HEADLESS for perfect video
    headlessBrowser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--autoplay-policy=no-user-gesture-required'],
    });

    headlessContext = await headlessBrowser.newContext({
      viewport: { width, height },
      ignoreHTTPSErrors: true,
      recordVideo: {
        dir: tempDir,
        size: { width, height }
      }
    });

    headlessPage = await headlessContext.newPage();
    
    console.log('Loading in headless browser...');
    await headlessPage.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await headlessPage.waitForSelector('.slidev-layout', { timeout: 10000 }).catch(() => {});
    await headlessPage.waitForTimeout(3000);
    console.log('✅ Headless ready (video recording active)');

    // Browser 2: HEADED for audio capture
    console.log('\nStarting Browser 2: HEADED (audio capture)...');
    
    headedBrowser = await chromium.launch({
      headless: false,
      args: [
        '--no-sandbox',
        '--autoplay-policy=no-user-gesture-required',
        '--use-fake-ui-for-media-stream',
        `--window-size=${width},${height}`,
      ],
    });

    headedContext = await headedBrowser.newContext({
      viewport: { width, height },
      ignoreHTTPSErrors: true,
    });

    headedPage = await headedContext.newPage();
    
    console.log('Loading in headed browser...');
    await headedPage.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await headedPage.waitForSelector('.slidev-layout', { timeout: 10000 }).catch(() => {});
    await headedPage.waitForTimeout(3000);
    console.log('✅ Headed ready');
    
    if (onBrowserReady) {
      onBrowserReady({ 
        browser: headlessBrowser, 
        context: headlessContext, 
        page: headlessPage,
        headedBrowser,
        headedPage 
      });
    }

    // Set up audio capture in HEADED browser
    console.log('\n🎤 Setting up audio capture in headed browser...');
    
    await headedPage.evaluate(() => {
      return new Promise(async (resolve) => {
        // Create audio context
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const dest = ctx.createMediaStreamDestination();
        
        if (ctx.state === 'suspended') {
          await ctx.resume();
        }
        
        console.log('[Audio] AudioContext ready:', ctx.state);
        
        // Hook Howler
        const OrigHowl = window.Howl;
        if (OrigHowl) {
          window.Howl = function(...args) {
            const howl = new OrigHowl(...args);
            const origPlay = howl.play.bind(howl);
            
            howl.play = function() {
              const id = origPlay();
              const sound = howl._soundById(id);
              
              if (sound && sound._node && !sound._captured) {
                try {
                  const src = ctx.createMediaElementSource(sound._node);
                  src.connect(dest);
                  src.connect(ctx.destination);
                  sound._captured = true;
                  console.log('[Audio] ✅ Captured Howler audio!');
                } catch (e) {
                  console.log('[Audio] Route error:', e.message);
                }
              }
              return id;
            };
            return howl;
          };
        }
        
        // Create audio-only recorder
        const rec = new MediaRecorder(dest.stream, {
          mimeType: 'audio/webm;codecs=opus',
          audioBitsPerSecond: 192000
        });
        
        window.__audioChunks = [];
        
        rec.ondataavailable = e => {
          if (e.data.size > 0) {
            window.__audioChunks.push(e.data);
            console.log('[Audio] Chunk:', e.data.size);
          }
        };
        
        rec.onstop = () => {
          const blob = new Blob(window.__audioChunks, { type: 'audio/webm' });
          window.__audioBlob = blob;
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'audio.webm';
          a.click();
          console.log('[Audio] Saved, size:', blob.size);
        };
        
        rec.start(1000);
        window.__audioRecorder = rec;
        console.log('[Audio] Recording started');
        
        resolve();
      });
    });
    
    console.log('✅ Audio capture ready');

    // Sync both browsers - press A simultaneously
    console.log('\n▶️  STARTING PLAYBACK IN BOTH BROWSERS SIMULTANEOUSLY...');
    await Promise.all([
      headlessPage.keyboard.press('a'),
      headedPage.keyboard.press('a')
    ]);
    console.log('✅ Both playing');

    // Wait for completion
    if (testMode) {
      console.log('⏱️  Recording for 60 seconds...');
      await new Promise(resolve => setTimeout(resolve, 60000));
    } else {
      await new Promise(resolve => setTimeout(resolve, maxDuration));
    }

    console.log('\n💾 Finalizing...');
    
    // Stop audio recording
    const audioDownload = headedPage.waitForEvent('download', { timeout: 10000 });
    await headedPage.evaluate(() => {
      if (window.__audioRecorder) {
        window.__audioRecorder.stop();
      }
    });
    
    const audioDl = await audioDownload;
    await audioDl.saveAs(audioPath);
    console.log(`✅ Audio saved: ${audioPath}`);
    
    // Get video
    const video = headlessPage.video();
    await headlessPage.close();
    await headedPage.close();
    await headlessContext.close();
    await headedContext.close();
    await headlessBrowser.close();
    await headedBrowser.close();
    console.log('✅ Both browsers closed');
    
    const tempVideoPath = await video.path();
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    if (tempVideoPath !== videoPath) {
      await fs.move(tempVideoPath, videoPath, { overwrite: true });
    }
    
    console.log(`✅ Video saved: ${videoPath}`);
    
    // Check file sizes
    const vStats = await fs.stat(videoPath);
    const aStats = await fs.stat(audioPath);
    console.log(`\n📊 Captured:`);
    console.log(`   Video: ${(vStats.size / 1024 / 1024).toFixed(2)} MB`);
    console.log(`   Audio: ${(aStats.size / 1024 / 1024).toFixed(2)} MB`);

    return { 
      videoPath,
      audioPath
    };

  } catch (error) {
    console.error('❌ Error:', error);
    if (headlessBrowser) try { await headlessBrowser.close(); } catch (e) {}
    if (headedBrowser) try { await headedBrowser.close(); } catch (e) {}
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

