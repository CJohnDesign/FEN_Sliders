# Video Export System

Automated headless video export for Slidev presentation decks.

## Overview

This system automatically exports presentation videos by:
1. Starting a Slidev server on port 3030
2. Recording the presentation in a headless browser
3. Triggering automatic playback via the 'A' key
4. Detecting presentation completion
5. Saving versioned MP4 files

## Usage

### Export a Single Deck

```bash
# Using npm script
npm run export-video FEN_GDC

# Or directly
node scripts/video-export/exportVideo.js FEN_STG

# With options
npm run export-video FEN_HMM -- --quality high
```

### List Available Decks

```bash
npm run export-video list
```

### Command Options

```bash
-q, --quality <level>   Video quality: low, medium, high (default: medium)
--no-headless          Show browser window during recording
--width <pixels>       Video width (default: 1920)
--height <pixels>      Video height (default: 1080)
--no-skip-reencode     Re-encode with FFmpeg (slower but more control)
```

## How It Works

### 1. Automatic Playback
The system leverages existing automation in `SlideAudio.vue`:
- Pressing 'A' starts automatic playback
- Audio plays and slides advance automatically
- OBS connection attempts are ignored (they fail gracefully)

### 2. Completion Detection
Monitors browser console for completion signal:
- Console log: `"[End Detection] Last audio complete, stopping OBS recording..."`
- Falls back to timeout if signal not detected

### 3. Server Management
- Automatically starts Slidev on port 3030
- Waits for server to be ready
- Stops server when export completes

### 4. Video Processing
- Records at 1920x1080 by default
- Saves to `exports/videos/`
- Versioned like PDFs: `FEN_GDC_001.mp4`, `FEN_GDC_002.mp4`, etc.

## Output

Videos are saved to: `exports/videos/{DECK_ID}_{VERSION}.mp4`

Example:
- `exports/videos/FEN_GDC_001.mp4`
- `exports/videos/FEN_STG_001.mp4`

Expected:
- Size: ~300-500MB for 10-minute presentation
- Duration: 15-20 minutes to export
- Quality: Identical to manual recording

## Files

- `exportVideo.js` - Main CLI script
- `serverManager.js` - Start/stop Slidev server
- `browserRecorder.js` - Playwright recording automation
- `versionManager.js` - Version numbering
- `videoProcessor.js` - FFmpeg post-processing

## Troubleshooting

### Port 3030 Already in Use
Stop any running Slidev servers before exporting.

### Browser Timeout
If presentation doesn't complete:
- Check that all audio files exist
- Verify `audio_script.md` is properly formatted
- Try with `--no-headless` to see what's happening

### OBS Connection Errors (Ignore)
OBS connection will fail in headless mode - this is expected and safe to ignore.

### Video Quality Issues
Try `--no-skip-reencode` to re-encode with FFmpeg for better quality control.

## Requirements

- Node.js 18+
- FFmpeg (installed automatically via npm)
- Playwright Chromium (already installed)
- Slidev server
- Properly configured deck with audio files

## Git

Video files are automatically ignored (see `.gitignore`):
- `exports/videos/` - Video output
- `temp/video-export/` - Temporary files

