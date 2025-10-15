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

## Recommended Solution: Playwright + FFmpeg

### Architecture Overview

```
┌─────────────────┐
│  Playwright     │
│  (Headless      │──┐
│   Chromium)     │  │
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

1. **Playwright** - Headless Chromium browser automation (already in project)
2. **FFmpeg** - Video encoding and audio sync
3. **Node.js** - Orchestration script

**Note**: Playwright is already installed in the project (`playwright-chromium`), so we'll use it instead of adding Puppeteer as a duplicate dependency.

## Implementation Approaches

### Option 1: Playwright with Native Video Recording (Recommended)

**Pros:**
- Captures browser exactly as it appears
- Handles animations and transitions
- Built-in video recording (no extra dependencies)
- Simple API
- Already installed in project

**Cons:**
- Performance overhead from running browser
- File sizes can be large
- Browser audio capture may need separate handling

```javascript
const { chromium } = require('playwright');
const path = require('path');

async function recordDeck(deckId) {
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: './temp/video-export',
      size: { width: 1920, height: 1080 }
    },
    // Disable audio capture as we'll add it separately with FFmpeg
    recordAudio: false
  });
  
  const page = await context.newPage();
  
  // Navigate to presentation
  // NOTE: Server must be running on localhost:3000 before executing
  await page.goto(`http://localhost:3000/decks/${deckId}/slides.md`, {
    waitUntil: 'networkidle',
  });
  
  // Wait for Slidev to fully load
  await page.waitForTimeout(2000);
  
  // Automate through slides
  await automatePresentation(page, deckId);
  
  // Close to save video
  await context.close();
  
  // Get the recorded video path
  const videoPath = await page.video().path();
  
  // Use FFmpeg to combine with audio
  await combineVideoWithAudio(videoPath, deckId);
  
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
  
  await page.goto(`http://localhost:3000/decks/${deckId}/slides.md`);
  
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

### Option 3: Alternative Approach - Direct FFmpeg Stream

For maximum control, stream frames directly to FFmpeg without storing intermediate files:

**Pros:**
- No intermediate storage needed
- Smallest disk footprint
- Real-time encoding

**Cons:**
- Most complex implementation
- Harder to debug
- No retry capability for failed frames

```javascript
const { chromium } = require('playwright');
const ffmpeg = require('fluent-ffmpeg');

async function streamToFFmpeg(deckId) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });
  
  // Set up FFmpeg stream
  const ffmpegProcess = ffmpeg()
    .input('pipe:0')
    .inputFormat('image2pipe')
    .inputFPS(30)
    .addInput(`./decks/${deckId}/audio/combined.mp3`)
    .output(`./exports/videos/${deckId}.mp4`)
    .videoCodec('libx264')
    .audioCodec('aac');
  
  // Navigate and capture frames directly to FFmpeg
  await page.goto(`http://localhost:3000/decks/${deckId}/slides.md`);
  
  // This approach requires more sophisticated frame timing
  // and is recommended only for advanced use cases
  
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

## Critical Project-Specific Requirements

### 1. Server Prerequisites
- **Slidev server MUST be running** on `http://localhost:3000` before executing video export
- The script will NOT start/stop the server automatically
- User should restart the server if needed: `npm run dev:FEN_STG` (or appropriate deck command)
- The script will validate server availability before starting export

### 2. Audio File Structure
- Audio files are located in `./decks/{DECK_ID}/audio/oai/`
- Files follow naming pattern: `{DECK_ID}{SECTION_NUMBER}_{CLICK_NUMBER}.mp3`
- Example: `FEN_STG1_1.mp3`, `FEN_STG2_1.mp3`, `FEN_STG2_2.mp3`
- Audio script is in `./decks/{DECK_ID}/audio/audio_script.md`
- Script sections are delimited by `---- Section Title ----`

### 3. Git Configuration
- Video files MUST be ignored by git (large file sizes)
- Add to `.gitignore`:
  ```
  # Video exports
  exports/videos/
  temp/video-export/
  ```
- Existing PDF exports in `exports/*.pdf` will remain tracked

### 4. Directory Structure
```
exports/
  ├── videos/              # New: Video exports (git ignored)
  │   ├── FEN_STG.mp4
  │   ├── FEN_HMM.mp4
  │   └── ...
  └── *.pdf                # Existing: PDF exports (git tracked)

temp/
  └── video-export/        # Temporary video files (git ignored)
      ├── frames/
      ├── audio/
      └── ...
```

## Proposed Script Structure

```
/scripts/
  /video-export/
    - exportVideo.js          # Main export script
    - audioProcessor.js       # Audio timing/combining
    - browserAutomation.js    # Playwright automation
    - videoEncoder.js         # FFmpeg operations
    - deckAnalyzer.js         # Parse deck structure & audio script
    - config.js               # Export settings
    - serverCheck.js          # Validate server is running
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
  serverUrl: 'http://localhost:3000',
  exportDir: './exports/videos',
  tempDir: './temp/video-export'
};
```

## Identified Issues & Recommendations

### Issues Found in Original Plan:
1. ❌ **Wrong Browser Library**: Plan used Puppeteer, but project already has Playwright
2. ❌ **Wrong Port**: Plan used 3030, but project uses 3000
3. ❌ **Wrong URL Pattern**: Plan didn't account for Slidev's deck structure
4. ❌ **No Git Ignore**: Plan didn't address version control for large video files
5. ❌ **No Export Subdirectory**: Videos mixed with PDFs in same directory
6. ❌ **Missing Audio Path Logic**: Plan assumed flexible paths, but structure is specific
7. ❌ **No Server Check**: Plan didn't validate server is running before export

### Improvements Made:
1. ✅ Use Playwright (already installed)
2. ✅ Correct server URL: `http://localhost:3000/decks/{DECK_ID}/slides.md`
3. ✅ Export to `./exports/videos/` subdirectory
4. ✅ Add git ignore rules for video files and temp directories
5. ✅ Document specific audio file structure
6. ✅ Add server validation step
7. ✅ Add proper error handling and cleanup

## Implementation Plan

### Phase 1: Setup & Infrastructure (1 day)
1. Install FFmpeg dependencies
2. Update `.gitignore` for video exports
3. Create directory structure (`exports/videos/`, `temp/video-export/`)
4. Set up basic config file
5. Implement server availability check

### Phase 2: Audio Processing (1 day)
1. Parse `audio_script.md` sections
2. Extract MP3 durations with FFprobe
3. Create audio file sequence
4. Implement audio concatenation with FFmpeg
5. Build timing map for automation

### Phase 3: Video Capture (1-2 days)
1. Set up Playwright with video recording
2. Implement slide automation based on audio timings
3. Handle transitions and animations
4. Capture full presentation run
5. Save temporary video file

### Phase 4: Video + Audio Combination (1 day)
1. Combine captured video with concatenated audio
2. Implement proper audio sync
3. Apply encoding settings (quality, bitrate, etc.)
4. Save final video to `exports/videos/`
5. Clean up temporary files

### Phase 5: CLI & UX (1 day)
1. Implement CLI: `node scripts/video-export/exportVideo.js FEN_STG`
2. Add progress indicators (using existing `ora` package)
3. Error handling and graceful failures
4. Quality validation
5. Batch processing support: `--all` or multiple deck IDs

### Phase 6: Optimization (1 day)
1. Caching for audio concatenation
2. Parallel processing for multiple decks (optional)
3. Incremental exports (only changed decks)
4. Compression optimization
5. Performance benchmarking

## Required Dependencies

```json
{
  "dependencies": {
    "fluent-ffmpeg": "^2.1.2",
    "@ffmpeg-installer/ffmpeg": "^1.1.0",
    "@ffprobe-installer/ffprobe": "^1.4.0",
    "fs-extra": "^11.0.0",
    "chalk": "^4.1.2",
    "commander": "^11.0.0"
  },
  "devDependencies": {
    "playwright-chromium": "^1.48.2"
  }
}
```

**Note**: `playwright-chromium` and `ora` are already installed in the project, so we only need to add FFmpeg-related packages.

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

## Key Risks & Mitigation Strategies

### Risk 1: Audio/Video Sync Drift
**Problem**: Cumulative timing errors causing audio to drift from video over 10+ minutes
**Mitigation**:
- Use exact audio file durations from FFprobe
- Add minimal buffer time (50-100ms max)
- Test with shorter decks first
- Implement sync validation checkpoints

### Risk 2: Browser Resource Issues
**Problem**: Headless browser crashes or hangs during long recordings
**Mitigation**:
- Increase Node.js memory: `NODE_OPTIONS=--max-old-space-size=4096`
- Monitor memory usage during recording
- Implement timeout detection and retry logic
- Consider splitting very long presentations

### Risk 3: Animation Timing
**Problem**: Slidev transitions not fully completing before next action
**Mitigation**:
- Wait for network idle after navigation
- Add configurable transition delay (100-300ms)
- Use Playwright's `waitForLoadState` properly
- Test with decks containing heavy animations

### Risk 4: Large File Sizes
**Problem**: Video files could be 500MB-1GB each
**Mitigation**:
- Already addressed: `.gitignore` configured
- Use appropriate CRF settings (18-23)
- Consider cloud storage for finals
- Keep only latest version locally

### Risk 5: FFmpeg Not Installed
**Problem**: System may not have FFmpeg installed
**Mitigation**:
- Use `@ffmpeg-installer/ffmpeg` package (includes binary)
- Provide installation instructions in README
- Add validation check before export
- Clear error messages if missing

## Final Recommendations

### Before Starting Implementation:
1. ✅ **Git ignore is now configured** - Video files won't be committed
2. ⚠️ **Test with ONE deck first** - Use FEN_STG (medium complexity)
3. ⚠️ **Ensure FFmpeg installation** - Test `ffmpeg -version` in terminal
4. ⚠️ **Server must be running** - Start with `npm run dev:FEN_STG`
5. ⚠️ **Disk space check** - Ensure 5-10GB free for temp files

### Implementation Priority:
1. **Phase 1 first** - Get infrastructure right (dirs, config, validation)
2. **Phase 2 critical** - Audio processing is the foundation
3. **Phase 3-4 core** - Basic video capture + combination
4. **Phase 5-6 polish** - Can be done incrementally

### Success Criteria:
- ✅ Video plays smoothly without stuttering
- ✅ Audio is perfectly synced throughout (no drift)
- ✅ All transitions and animations captured
- ✅ File size reasonable (<500MB for 10min video)
- ✅ Process completes in <30 minutes per deck
- ✅ No manual intervention required

### Alternative If This Fails:
If headless approach proves too problematic:
1. **OBS Studio Automation** - Script OBS via websocket
2. **Cloud Recording Service** - Use AWS Lambda + Playwright
3. **Hybrid Approach** - Manual recording with better tooling

## Conclusion

Headless video export is achievable and will significantly improve your workflow. The recommended approach using **Playwright + FFmpeg** provides the best balance of implementation complexity, quality, and reliability for this specific project.

**Key Advantages**:
- Uses existing dependencies (Playwright already installed)
- Works with current audio file structure
- Maintains quality of manual recordings
- Enables batch processing
- Eliminates human error

**Critical Success Factors**:
1. Precise audio synchronization using FFprobe durations
2. Proper git ignore configuration (✅ **DONE**)
3. Server availability validation
4. Appropriate error handling and cleanup
5. Testing with incremental complexity

The plan is now updated to match your project's specific structure, uses the correct port (3000), exports to the dedicated `exports/videos/` directory, and ensures video files won't be committed to git.

