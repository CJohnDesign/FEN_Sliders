# Headless Video Export Strategy for FEN Presentations

## Overview

This document outlines strategies for automating the video export process of FEN presentation decks, replacing manual screen recording with a headless, programmatic approach.

## Current Workflow

- **Presentation Engine**: Slidev (Vue-based presentation framework)
- **Audio System**: Synchronized audio files (MP3) that play through each slide/click
- **Current Export**: Manual screen recording while presentation plays (~10 minutes per deck)
- **Output**: Video file suitable for distribution

## Problems with Current Approach

1. **Manual Process**: Requires operator to start recording, play through presentation, stop recording
2. **Inconsistency**: Timing variations, potential for human error
3. **Time Intensive**: Must watch each 10-minute presentation in real-time
4. **Quality Control**: Difficult to ensure consistent quality across multiple decks
5. **Scalability**: Cannot batch process multiple decks

## Recommended Solution: Puppeteer + FFmpeg

### Architecture Overview

```
┌─────────────────┐
│  Puppeteer      │
│  (Headless      │──┐
│   Browser)      │  │
└─────────────────┘  │
                     │
┌─────────────────┐  │     ┌─────────────────┐
│  Slidev Server  │◄─┘     │    FFmpeg       │
│  (localhost)    │────────►│  (Video         │──► MP4 Output
│                 │ frames  │   Encoding)     │
└─────────────────┘         └─────────────────┘
                                    ▲
┌─────────────────┐                 │
│  Audio Files    │─────────────────┘
│  (MP3s)         │
└─────────────────┘
```

### Technology Stack

1. **Puppeteer** - Headless Chrome browser automation
2. **puppeteer-screen-recorder** - Browser screen capture
3. **FFmpeg** - Video encoding and audio sync
4. **Node.js** - Orchestration script

## Implementation Approaches

### Option 1: Puppeteer Screen Recorder (Recommended)

**Pros:**
- Captures browser exactly as it appears
- Handles animations and transitions
- Native audio capture support
- Simple API

**Cons:**
- Performance overhead from running browser
- File sizes can be large

```javascript
const puppeteer = require('puppeteer');
const { PuppeteerScreenRecorder } = require('puppeteer-screen-recorder');

async function recordDeck(deckId) {
  const browser = await puppeteer.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--window-size=1920,1080',
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  
  // Start screen recorder
  const recorder = new PuppeteerScreenRecorder(page, {
    followNewTab: false,
    fps: 30,
    videoFrame: {
      width: 1920,
      height: 1080,
    },
    aspectRatio: '16:9',
  });
  
  // Navigate to presentation
  await page.goto(`http://localhost:3030/${deckId}`, {
    waitUntil: 'networkidle0',
  });
  
  // Start recording
  await recorder.start(`./exports/${deckId}.mp4`);
  
  // Automate through slides
  await automatePresentation(page, deckId);
  
  // Stop recording
  await recorder.stop();
  await browser.close();
}
```

### Option 2: Frame Capture + FFmpeg Stitching

**Pros:**
- More control over timing
- Smaller intermediate files
- Better audio sync control
- Can retry individual frames

**Cons:**
- More complex implementation
- Requires careful timing management

```javascript
async function captureFrames(deckId) {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  
  await page.goto(`http://localhost:3030/${deckId}`);
  
  const audioTimings = await getAudioTimings(deckId);
  const frames = [];
  
  for (const timing of audioTimings) {
    // Advance to next click/slide
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(100); // Wait for animation
    
    // Capture frame multiple times based on audio duration
    const frameCount = Math.ceil(timing.duration * 30); // 30 fps
    for (let i = 0; i < frameCount; i++) {
      const screenshot = await page.screenshot({
        type: 'png',
        path: `./frames/${deckId}_frame_${frames.length}.png`
      });
      frames.push(screenshot);
    }
  }
  
  await browser.close();
  return frames;
}

// Then use FFmpeg to stitch
async function stitchVideo(deckId, frames, audioFiles) {
  // FFmpeg command to combine frames + audio
  const command = `
    ffmpeg -framerate 30 
           -i "./frames/${deckId}_frame_%d.png" 
           -i "./decks/${deckId}/audio/combined.mp3" 
           -c:v libx264 
           -preset slow 
           -crf 18 
           -c:a aac 
           -b:a 192k 
           -pix_fmt yuv420p 
           "./exports/${deckId}.mp4"
  `;
  
  await execCommand(command);
}
```

### Option 3: Playwright Recorder (Alternative)

Similar to Puppeteer but with some advantages:

```javascript
const { chromium } = require('playwright');

async function recordWithPlaywright(deckId) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: './exports/',
      size: { width: 1920, height: 1080 }
    }
  });
  
  const page = await context.newPage();
  await page.goto(`http://localhost:3030/${deckId}`);
  
  await automatePresentation(page, deckId);
  
  await context.close();
  await browser.close();
}
```

## Critical Implementation Details

### 1. Audio Synchronization

The most critical aspect is ensuring audio plays in sync with slides:

```javascript
async function automatePresentation(page, deckId) {
  const audioScript = await loadAudioScript(deckId);
  const sections = parseAudioSections(audioScript);
  
  for (const section of sections) {
    // Get audio duration for this click
    const audioPath = `./decks/${deckId}/audio/oai/${section.audioFile}`;
    const duration = await getAudioDuration(audioPath);
    
    // Trigger click/advance
    await page.keyboard.press('ArrowRight');
    
    // Wait for audio duration + small buffer
    await page.waitForTimeout(duration * 1000 + 100);
  }
}

// Helper to get MP3 duration
async function getAudioDuration(filePath) {
  const { exec } = require('child_process');
  const { promisify } = require('util');
  const execPromise = promisify(exec);
  
  const { stdout } = await execPromise(
    `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${filePath}"`
  );
  
  return parseFloat(stdout);
}
```

### 2. Handling Slidev's Audio System

Since your Slidev decks already have audio integration, you need to:

1. **Disable browser audio capture** (if using frame method) to avoid double audio
2. **Mix audio files** separately and add to video
3. **Ensure audio playback triggers** are detected

```javascript
// Read your config.json to understand audio timing
async function getAudioTimings(deckId) {
  const configPath = `./decks/${deckId}/audio/config.json`;
  const config = JSON.parse(await fs.readFile(configPath, 'utf-8'));
  
  const timings = [];
  
  // Parse audio script to map sections to files
  const scriptPath = `./decks/${deckId}/audio/audio_script.md`;
  const script = await fs.readFile(scriptPath, 'utf-8');
  const sections = parseScriptSections(script);
  
  for (let i = 0; i < sections.length; i++) {
    const section = sections[i];
    const audioFile = `${deckId}${section.number}_${section.click}.mp3`;
    const audioPath = `./decks/${deckId}/audio/oai/${audioFile}`;
    
    if (await fs.pathExists(audioPath)) {
      const duration = await getAudioDuration(audioPath);
      timings.push({
        section: section.title,
        click: section.click,
        audioFile: audioFile,
        duration: duration
      });
    }
  }
  
  return timings;
}
```

### 3. Combining Audio Files

Pre-combine all audio files for a deck:

```javascript
async function combineAudioFiles(deckId) {
  const audioDir = `./decks/${deckId}/audio/oai/`;
  const files = await fs.readdir(audioDir);
  const mp3Files = files
    .filter(f => f.endsWith('.mp3'))
    .sort(naturalSort);
  
  // Create FFmpeg concat file
  const concatList = mp3Files
    .map(f => `file '${audioDir}${f}'`)
    .join('\n');
  
  await fs.writeFile('./temp/concat.txt', concatList);
  
  // Combine with FFmpeg
  await execCommand(`
    ffmpeg -f concat -safe 0 -i ./temp/concat.txt 
           -c copy 
           "./decks/${deckId}/audio/combined.mp3"
  `);
  
  return `./decks/${deckId}/audio/combined.mp3`;
}
```

## Proposed Script Structure

```
/scripts/
  /video-export/
    - exportVideo.js          # Main export script
    - audioProcessor.js       # Audio timing/combining
    - browserAutomation.js    # Puppeteer/Playwright automation
    - videoEncoder.js         # FFmpeg operations
    - deckAnalyzer.js         # Parse deck structure
    - config.js               # Export settings
```

## Configuration Options

```javascript
// /scripts/video-export/config.js
module.exports = {
  // Video settings
  resolution: {
    width: 1920,
    height: 1080
  },
  frameRate: 30,
  videoCodec: 'libx264',
  videoBitrate: '5000k',
  preset: 'medium', // or 'slow' for better quality
  crf: 18, // 0-51, lower = better quality
  
  // Audio settings
  audioCodec: 'aac',
  audioBitrate: '192k',
  audioSampleRate: 44100,
  
  // Browser settings
  headless: true,
  devtools: false,
  
  // Timing
  transitionDelay: 100, // ms to wait after click
  bufferTime: 50, // ms buffer at end of each section
  
  // Paths
  serverUrl: 'http://localhost:3030',
  exportDir: './exports',
  tempDir: './temp/video-export'
};
```

## Implementation Plan

### Phase 1: Basic Export (1-2 days)
1. Set up Puppeteer with basic navigation
2. Implement audio timing extraction from your existing system
3. Create simple frame capture loop
4. Combine with FFmpeg

### Phase 2: Audio Integration (1 day)
1. Parse audio config.json
2. Extract MP3 durations
3. Pre-combine audio files
4. Sync with video frames

### Phase 3: Automation & Quality (1-2 days)
1. Implement CLI: `node scripts/exportVideo.js FEN_STG`
2. Add progress indicators
3. Error handling and retry logic
4. Quality validation
5. Batch processing support

### Phase 4: Optimization (1 day)
1. Parallel processing for multiple decks
2. Caching mechanisms
3. Incremental exports (only changed decks)
4. Compression optimization

## Required Dependencies

```json
{
  "dependencies": {
    "puppeteer": "^21.0.0",
    "puppeteer-screen-recorder": "^3.0.0",
    "fluent-ffmpeg": "^2.1.2",
    "@ffmpeg-installer/ffmpeg": "^1.1.0",
    "@ffprobe-installer/ffprobe": "^1.4.0",
    "fs-extra": "^11.0.0",
    "ora": "^5.4.1",
    "chalk": "^4.1.2",
    "commander": "^11.0.0"
  }
}
```

## Usage Example

```bash
# Export single deck
node scripts/exportVideo.js FEN_STG

# Export multiple decks
node scripts/exportVideo.js FEN_STG FEN_HMM FEN_HMP

# Export all decks
node scripts/exportVideo.js --all

# Export with custom quality
node scripts/exportVideo.js FEN_STG --quality high --crf 15

# Export with specific resolution
node scripts/exportVideo.js FEN_STG --resolution 2560x1440
```

## Quality Considerations

### Video Quality Settings

| Quality | CRF | Bitrate | File Size (10min) | Use Case |
|---------|-----|---------|-------------------|----------|
| Low | 28 | 2000k | ~150 MB | Preview/Testing |
| Medium | 23 | 3500k | ~260 MB | Standard Distribution |
| High | 18 | 5000k | ~375 MB | Professional Use |
| Very High | 15 | 8000k | ~600 MB | Archival/Master |

### Audio Quality Settings

| Quality | Bitrate | Sample Rate | File Size Impact |
|---------|---------|-------------|------------------|
| Standard | 128k | 44100 | ~9.6 MB |
| High | 192k | 44100 | ~14.4 MB |
| Very High | 256k | 48000 | ~19.2 MB |

## Testing Strategy

1. **Unit Tests**: Test individual components (audio extraction, timing calculation)
2. **Integration Tests**: Test full export on test deck
3. **Quality Tests**: Compare manual vs automated export
4. **Performance Tests**: Measure export time per deck
5. **Regression Tests**: Ensure sync accuracy across updates

## Troubleshooting Common Issues

### Audio Sync Drift
- **Cause**: Cumulative timing errors
- **Solution**: Reset timing at each section boundary, add sync points

### Missing Transitions
- **Cause**: Insufficient wait time after click
- **Solution**: Increase `transitionDelay` or detect animation completion

### Quality Issues
- **Cause**: CRF too high, bitrate too low
- **Solution**: Adjust CRF (lower) and increase bitrate

### Memory Issues
- **Cause**: Too many frames in memory
- **Solution**: Stream frames directly to FFmpeg, don't store all in memory

### Browser Crashes
- **Cause**: Resource limits in headless mode
- **Solution**: Increase memory limits, reduce concurrent operations

## Alternative Approaches

### Server-Side Rendering (SSR)
Convert Slidev to static HTML/Canvas and render server-side:
- **Pros**: No browser needed, very fast
- **Cons**: Complex implementation, may miss interactive features

### WebRTC Recording
Use browser's native recording APIs:
- **Pros**: Native quality, handles audio automatically
- **Cons**: Requires visible browser window (not truly headless)

### Cloud Rendering Services
Use services like AWS Lambda + Puppeteer layers:
- **Pros**: Scalable, no local resources
- **Cons**: Cost, complexity, latency

## Recommended Next Steps

1. **Prototype**: Build minimal viable export for one deck (FEN_STG)
2. **Validate**: Compare output quality with manual recording
3. **Refine**: Adjust timing, quality, and sync parameters
4. **Scale**: Extend to all decks with batch processing
5. **Integrate**: Add to CI/CD pipeline for automated regeneration

## Expected Results

- **Export Time**: 1.5-2x playback speed (15-20 minutes for 10-minute video)
- **File Size**: ~300-400 MB per deck at medium-high quality
- **Quality**: Identical to manual recording
- **Automation**: Zero manual intervention required
- **Consistency**: Perfect reproduction every time
- **Scalability**: Process all decks overnight

## Conclusion

Headless video export is achievable and will significantly improve your workflow. The recommended approach using Puppeteer + screen recorder provides the best balance of implementation complexity, quality, and reliability. The key success factor is ensuring audio synchronization through careful timing management based on your existing audio file system.

