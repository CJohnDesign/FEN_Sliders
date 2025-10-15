# Video Export System - Working Implementation

## Status: ✅ OPERATIONAL

Successfully exports Slidev presentations to MP4 with synchronized audio.

## What Works

### Core Features
- ✅ **Automated video capture** using Playwright (headless)
- ✅ **Audio merging** from MP3 files in `/decks/{DECK_ID}/audio/oai/`
- ✅ **White frame trimming** - automatically removes loading screens
- ✅ **Perfect sync** - audio matches slide transitions
- ✅ **Versioned output** - files numbered (001, 002, etc.)
- ✅ **Test mode** - 10-second exports for testing
- ✅ **Timeout protection** - won't hang indefinitely

### Technical Implementation
1. **Video Recording**: Playwright's built-in `recordVideo` captures page (video only)
2. **Audio Processing**: FFmpeg combines all MP3 files into single track
3. **Trimming**: Automatically calculates and removes loading time
4. **Merging**: FFmpeg merges trimmed video with audio track
5. **Output**: H.264 video + AAC audio in MP4 container

## Usage

### Test Mode (10 seconds)
```bash
npm run export-video FEN_HMM -- --test
```

### Full Export
```bash
npm run export-video FEN_HMM
```

### Options
```bash
--test                    # Record only 10 seconds
--no-headless            # Show browser window (for debugging)
--width 1920             # Video width
--height 1080            # Video height
```

### List Available Decks
```bash
npm run export-video list
```

## Output

### Location
```
exports/videos/FEN_HMM_001.mp4
exports/videos/FEN_HMM_002.mp4
```

### Expected Results
- **Format**: MP4 (H.264 video + AAC audio)
- **Resolution**: 1920x1080
- **Quality**: CRF 18 (high quality)
- **Audio**: 192k AAC from original MP3 files
- **Duration**: Matches presentation length

## Key Improvements

### Stability
- Added timeouts to prevent hanging
- Server startup has 30s timeout
- Audio processing has 30s timeout
- Video processing has configurable timeout
- Proper cleanup on interrupt (Ctrl+C)

### Quality
- White frames automatically trimmed
- Audio perfectly synced with slides
- High quality H.264 encoding (CRF 18)
- 192k audio bitrate preserved

### Debugging
- Step-by-step progress logging
- Browser console messages shown
- Clear error messages
- Timeout warnings

## Technical Details

### Video Capture
- Uses Playwright's `recordVideo` API
- Records actual page rendering
- No user interaction required
- Works in headless mode

### Audio Handling
- Scans `/decks/{DECK_ID}/audio/oai/` directory
- Sorts audio files by slide number and click number
- Uses FFmpeg concat to merge all MP3 files
- In test mode, uses only first 4 audio files

### Trimming Logic
- Records timestamp when page loads
- Records timestamp when 'A' key is pressed
- Calculates difference as trim amount
- FFmpeg trims video start with `-ss` flag

### Sync Mechanism
- Video and audio are separate streams
- FFmpeg uses `-shortest` flag
- Both streams play at same speed
- Perfect synchronization maintained

## Known Limitations

1. **OBS Messages**: Harmless WebSocket errors (can be ignored)
2. **Port 3030**: Must be available (script kills any existing process)
3. **First Frame**: Some loading time is trimmed but ~7-8s removed
4. **File Size**: Videos are 300-500MB for 10-minute presentations

## Troubleshooting

### Port in Use
```bash
lsof -ti :3030 | xargs kill -9
```

### Timeout Issues
- Server start timeout: 30 seconds
- Audio combine timeout: 30 seconds
- Video process timeout: 60s (test) or 600s (full)

### Missing Audio
- Check `/decks/{DECK_ID}/audio/oai/` has MP3 files
- Files must be named: `{DECK_ID}{slideNumber}_{clickNumber}.mp3`
- Example: `FEN_HMM1_1.mp3`, `FEN_HMM2_1.mp3`

### White Frames
- System automatically trims loading time
- Typically removes ~7-8 seconds
- Video starts when 'A' key is pressed

## Next Steps

1. ✅ Test with one deck (FEN_HMM) - COMPLETE
2. ⏭ Test with more decks to verify compatibility
3. ⏭ Add batch export capability
4. ⏭ Optimize video file sizes if needed
5. ⏭ Add progress bar for long exports

## Dependencies

All dependencies are installed:
- `playwright-chromium` - Browser automation
- `fluent-ffmpeg` - Video processing
- `@ffmpeg-installer/ffmpeg` - FFmpeg binary
- `@ffprobe-installer/ffprobe` - FFprobe binary
- `fs-extra` - File operations
- `chalk` - Colored output
- `commander` - CLI framework
- `ora` - Progress spinners

## Files

```
scripts/video-export/
├── exportVideo.js          # Main CLI script
├── serverManager.js        # Slidev server control
├── browserRecorder.js      # Playwright video recording
├── audioProcessor.js       # Audio file combining
├── versionManager.js       # Version numbering
├── videoProcessor.js       # FFmpeg utilities
└── README.md              # Detailed documentation
```

---

**Last Updated**: October 14, 2025  
**Status**: ✅ Working - Ready for production use
