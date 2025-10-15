# Video Export Quick Start Guide

## First Time Setup

1. **Verify FFmpeg is installed**
   ```bash
   npm list @ffmpeg-installer/ffmpeg
   ```
   Should show version 1.1.0 or higher.

2. **Verify Playwright is installed**
   ```bash
   npm list playwright-chromium
   ```
   Should show version 1.48.2 or higher.

3. **Ensure port 3030 is available**
   ```bash
   # Check if anything is running on port 3030
   lsof -i :3030
   ```
   Should return nothing. If something is running, stop it first.

## Quick Export

```bash
# Export a deck (example: FEN_GDC)
npm run export-video FEN_GDC
```

## What Happens

1. ✓ Validates deck exists
2. ✓ Gets next version number (e.g., 001)
3. ✓ Starts Slidev server on port 3030
4. ✓ Launches headless browser with video recording
5. ✓ Navigates to presentation
6. ✓ Presses 'A' to start automatic playback
7. ✓ Records entire presentation
8. ✓ Detects completion signal
9. ✓ Saves video to `exports/videos/FEN_GDC_001.mp4`
10. ✓ Stops server and cleans up

## Expected Timeline

- **Preparation**: 5-10 seconds
- **Server Start**: 10-20 seconds
- **Recording**: ~1.5x presentation length (10-15 minutes for 10-min deck)
- **Processing**: 5-10 seconds
- **Total**: ~15-20 minutes per deck

## Verify Output

After export completes:

```bash
# Check the file was created
ls -lh exports/videos/

# Play the video (macOS)
open exports/videos/FEN_GDC_001.mp4
```

Expected file size: 300-500MB for a 10-minute presentation.

## Troubleshooting First Export

### Issue: Port 3030 in use
```bash
# Find and kill the process using port 3030
lsof -ti :3030 | xargs kill -9
```

### Issue: Browser timeout
Try running with visible browser to debug:
```bash
npm run export-video FEN_GDC -- --no-headless
```

### Issue: No audio in slides
Verify audio files exist:
```bash
ls decks/FEN_GDC/audio/oai/
```

### Issue: Export fails immediately
Check the deck path exists:
```bash
ls decks/FEN_GDC/slides.md
```

## Advanced Usage

### High Quality Export
```bash
npm run export-video FEN_GDC -- --quality high --no-skip-reencode
```

### Custom Resolution
```bash
npm run export-video FEN_GDC -- --width 2560 --height 1440
```

### Debug with Visible Browser
```bash
npm run export-video FEN_GDC -- --no-headless
```

## List All Available Decks

```bash
npm run export-video list
```

## Batch Export (Future)

For now, export decks one at a time:

```bash
npm run export-video FEN_GDC
npm run export-video FEN_STG
npm run export-video FEN_HMM
```

## File Organization

```
exports/
├── videos/                    # Video exports (git ignored)
│   ├── FEN_GDC_001.mp4
│   ├── FEN_GDC_002.mp4
│   └── FEN_STG_001.mp4
└── *.pdf                      # PDF exports (git tracked)
```

## Success Indicators

After export, you should see:
```
✓ Server started
✓ Recording complete
✓ Video processed

✓ Export completed successfully!
──────────────────────────────────────────────────
File: FEN_GDC_001.mp4
Path: /Users/.../exports/videos/FEN_GDC_001.mp4
Size: 387.23 MB
Duration: 10.2 minutes
Resolution: 1920x1080
──────────────────────────────────────────────────
✓ Cleaned up temporary files
```

## Next Steps

1. Test with a small deck first (FEN_GDC has ~122 audio files)
2. Watch the exported video to verify quality
3. Check audio sync throughout the video
4. Adjust quality settings if needed
5. Export remaining decks

## Support

For issues or questions:
1. Check console output for error messages
2. Review `docs/headless-video-export.md` for detailed docs
3. Try with `--no-headless` to see what's happening
4. Verify all audio files exist in `decks/{DECK_ID}/audio/oai/`

