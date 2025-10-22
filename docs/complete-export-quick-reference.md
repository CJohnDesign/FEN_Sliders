# Complete Export - Quick Reference (AI-Controlled)

## Overview

This workflow is **AI-controlled and modular**. The AI agent manages each step of the export process using individual scripts and Google API routes. This approach provides better error handling, visibility, and control compared to monolithic export scripts.

## Workflow Philosophy

1. **AI manages the process** - The AI calls individual scripts step-by-step
2. **Modular execution** - Each step is independent and can be run separately
3. **Native Google APIs** - Uses Google Cloud Platform APIs directly via Node.js scripts
4. **Visibility** - Each step shows clear output and progress
5. **Error recovery** - If a step fails, the AI can retry or adjust

## Export Steps (AI-Controlled)

The AI will execute these steps in sequence:

### Step 1 & 2: Google Docs Sync (Combined)
**Script**: `scripts/google-docs-api.js`  
**What it does**: 
- Authenticates with Google Drive & Docs APIs using OAuth
- Finds or creates 3-level folder structure:
  - Root folder: `FirstEnroll || Videos`
  - Base folder: `Product Videos`
  - Deck folder: `FEN_STG` (or whatever deck you're exporting)
- Reads local `audio_script.md` and `slides.md`
- Searches for existing Google Docs  
- Compares content to detect changes
- Creates new docs or updates existing ones
- Returns folder ID and Google Doc URLs

**Folder Path**: `FirstEnroll || Videos` → `Product Videos` → `FEN_STG`

**Time**: ~15-40 seconds  
**Cost**: $0

### Step 3: PDF Export
**Script**: `scripts/export-steps/03-export-pdf.js`  
**What it does**: 
- Uses Slidev's built-in export command
- Exports complete slides (no incremental clicks)
- Auto-versions output (e.g., `FEN_STG_010.pdf`)
- Saves to `exports/` directory

**Time**: ~30-60 seconds  
**Cost**: $0

### Step 3b: Upload PDF to Google Drive
**Script**: `scripts/upload-to-drive.js`  
**What it does**:
- Authenticates with Google Drive API (uses saved OAuth token)
- Finds the deck folder from Step 1
- Uploads PDF to the folder
- Returns Google Drive view link

**Time**: ~5-10 seconds  
**Cost**: $0

### Step 4: Audio Generation with Sanitization (Optional)
**Script**: `scripts/export-steps/04-generate-audio.js`  
**What it does**:
- Sanitizes script (replaces "comprehensive" → "extensive")
- Checks slide/script synchronization
- Deletes old audio files
- Generates new audio via OpenAI TTS API
- Saves MP3 files to `audio/oai/`

**Time**: ~2-5 minutes  
**Cost**: ⚠️ OpenAI TTS API credits (~$0.015 per 1000 characters)

### Step 5: Video Export (Optional)
**Script**: `scripts/export-steps/05-export-video.js`  
**What it does**:
- **Checks slide/script sync** (aborts if misaligned)
- Starts Slidev server on port 3030
- Records presentation with Playwright
- Encodes as MP4 with audio sync
- Auto-versions output (e.g., `FEN_STG_001.mp4`)
- Saves to `exports/videos/` directory

**⚠️ IMPORTANT**: Fullscreen your browser window before video export starts for proper recording dimensions!

**Time**: ~15-25 minutes  
**Cost**: $0

### Step 5b: Upload Video to Google Drive (Optional)
**Script**: `scripts/upload-to-drive.js`  
**What it does**:
- Authenticates with Google Drive API (uses saved OAuth token)
- Finds the deck folder from Step 1
- Uploads video file to the folder
- Returns Google Drive view link

**Time**: ~30-120 seconds (depending on file size)  
**Cost**: $0

## Available Flags for Individual Steps

### Audio Generation
- No flags needed - always regenerates all audio

### Video Export  
- `--test` - Test mode (60 seconds instead of full length)

## Common Workflows (AI-Managed)

The AI will ask you which workflow you need, then execute the appropriate steps.

### 1. Standard Export (Docs + PDF)
**What AI does**:
1. Runs `node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos" --root-folder="FirstEnroll || Videos"`
2. Runs `node scripts/export-steps/03-export-pdf.js FEN_STG`
3. Runs `node scripts/upload-to-drive.js exports/FEN_STG_xxx.pdf FEN_STG "Product Videos" "FirstEnroll || Videos"`

**Includes**: Google Docs Sync + PDF Export + Drive Upload  
**Time**: ~1-2 minutes  
**Cost**: $0

---

### 2. Full Export (Docs + PDF + Video)
**What AI does**:
1. Runs `node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos" --root-folder="FirstEnroll || Videos"`
2. Runs `node scripts/export-steps/03-export-pdf.js FEN_STG`
3. Runs `node scripts/upload-to-drive.js exports/FEN_STG_xxx.pdf FEN_STG "Product Videos" "FirstEnroll || Videos"`
4. Runs `node scripts/export-steps/05-export-video.js FEN_STG`
5. Runs `node scripts/upload-to-drive.js exports/videos/FEN_STG_xxx.mp4 FEN_STG "Product Videos" "FirstEnroll || Videos"`

**Includes**: Docs Sync + PDF Export + Drive Upload + Video Export + Drive Upload  
**Time**: ~17-29 minutes  
**Cost**: $0

---

### 3. Full Export with Audio Regeneration
**What AI does**:
1. Runs `node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos" --root-folder="FirstEnroll || Videos"`
2. Runs `node scripts/export-steps/03-export-pdf.js FEN_STG`
3. Runs `node scripts/upload-to-drive.js exports/FEN_STG_xxx.pdf FEN_STG "Product Videos" "FirstEnroll || Videos"`
4. Runs `node scripts/export-steps/04-generate-audio.js FEN_STG`
5. Runs `node scripts/export-steps/05-export-video.js FEN_STG`
6. Runs `node scripts/upload-to-drive.js exports/videos/FEN_STG_xxx.mp4 FEN_STG "Product Videos" "FirstEnroll || Videos"`

**Includes**: Docs Sync + PDF Export + Drive Upload + Audio Generation + Video Export + Drive Upload  
**Time**: ~22-37 minutes  
**Cost**: ⚠️ OpenAI TTS API credits

---

### 4. PDF Only
**What AI does**:
1. Runs `node scripts/export-steps/03-export-pdf.js FEN_STG`
2. Runs `node scripts/upload-to-drive.js exports/FEN_STG_xxx.pdf FEN_STG "Product Videos" "FirstEnroll || Videos"`

**Includes**: PDF Export + Drive Upload  
**Time**: ~40-70 seconds  
**Cost**: $0  
**Use When**: Only need PDF updated

---

### 5. Docs Only
**What AI does**:
1. Runs `node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos" --root-folder="FirstEnroll || Videos"`

**Includes**: Google Docs Sync only (auto-creates 3-level folder structure if needed)  
**Time**: ~15-40 seconds  
**Cost**: $0  
**Use When**: Only need to update Google Docs

---

### 6. Video Re-export (No Audio Changes)
**What AI does**:
1. Runs `node scripts/export-steps/05-export-video.js FEN_STG`
2. Runs `node scripts/upload-to-drive.js exports/videos/FEN_STG_xxx.mp4 FEN_STG "Product Videos" "FirstEnroll || Videos"`

**Includes**: Video Export + Drive Upload only  
**Time**: ~16-26 minutes  
**Cost**: $0  
**Use When**: Slides changed, need new video, audio unchanged

---

### 7. Audio + Video (After Script Changes)
**What AI does**:
1. Runs `node scripts/export-steps/04-generate-audio.js FEN_STG`
2. Runs `node scripts/export-steps/05-export-video.js FEN_STG`
3. Runs `node scripts/upload-to-drive.js exports/videos/FEN_STG_xxx.mp4 FEN_STG "Product Videos" "FirstEnroll || Videos"`

**Includes**: Audio Generation + Video Export + Drive Upload  
**Time**: ~20-32 minutes  
**Cost**: ⚠️ OpenAI TTS API credits  
**Use When**: Audio script changed, need new audio + video

---

### 8. Audio Only (No Exports)
**What AI does**:
1. Runs `node scripts/export-steps/04-generate-audio.js FEN_STG`

**Includes**: Audio generation only  
**Time**: ~2-5 minutes  
**Cost**: ⚠️ OpenAI TTS API credits  
**Use When**: Testing audio changes before committing to full export

---

### 9. Test Video Export
**What AI does**:
1. Runs `node scripts/export-steps/05-export-video.js FEN_STG --test`

**Includes**: 60-second video test (no upload)  
**Time**: ~2-3 minutes  
**Cost**: $0  
**Use When**: Verifying video setup before full export

---

### 10. Multiple Decks (Sequential)
**What AI does**:
- Executes chosen workflow for each deck sequentially
- Continues even if one fails (reports all results at end)

**Time**: Varies by number of decks  
**Cost**: Depends on whether audio regeneration is included  
**Use When**: Need to update multiple decks

---

## Decision Tree (AI Uses This)

```
Did audio script change?
│
├─ YES → AI regenerates audio (⚠️ costs money)
│   │
│   └─ What else do you need?
│       │
│       ├─ Everything → AI runs: Docs → Audio → Video
│       │
│       └─ Just Audio + Video → AI runs: Audio → Video
│
└─ NO → What do you need to export?
    │
    ├─ Everything → AI runs: Docs → Video
    │
    ├─ Just Docs → AI runs: Docs only
    │
    ├─ Just Video → AI runs: Video only
    │
    └─ Test Video → AI runs: Video (--test mode)
```

## Editing Workflow

### Local-First Workflow (Recommended)
1. **Edit local files** in your editor
   - `decks/FEN_STG/slides.md`
   - `decks/FEN_STG/audio/audio_script.md`

2. **Tell AI to export** (e.g., "Export FEN_STG with audio regeneration")
   - AI will sync docs to Google Drive
   - AI will regenerate audio if requested
   - AI will export video

### Google Docs-First Workflow
1. **Edit in Google Docs** (easier for collaboration)
   - AI can provide you the Google Doc URLs

2. **Tell AI to pull changes** (e.g., "Pull FEN_STG from Google Docs")
   - AI will download updated content to local files

3. **Tell AI to export** as needed

---

## Script Sanitization

**Automatic word replacement happens before audio generation.**

### Forbidden Words
- `comprehensive` → automatically replaced with `extensive`
- Preserves casing: `Comprehensive` → `Extensive`, `COMPREHENSIVE` → `EXTENSIVE`

### Why?
We **never** use "comprehensive" in any context (slides, audio scripts, or documentation). The sanitization ensures text-to-speech APIs never speak this word.

### How It Works
1. Runs automatically during Step 4 (Audio Regeneration)
2. Replaces forbidden words in `audio_script.md`
3. Reports number of replacements made
4. Proceeds with audio generation

### Manual Usage
If you need to sanitize without generating audio:
```bash
node scripts/sanitize-script.js FEN_STG
```

**Script Location**: `scripts/sanitize-script.js`

---

## Cost Guide

| Action | Cost | When It Costs |
|--------|------|--------------|
| PDF Export | $0 | Never |
| Google Drive Upload | $0 | Never |
| Google Drive Folder Check | $0 | Never |
| Google Docs Sync (Push/Pull) | $0 | Never |
| Video Export | $0 | Never |
| **Audio Regeneration** | **⚠️ OpenAI TTS** | **Every time you regenerate audio** |

**Audio costs vary based on:**
- Script length (characters)
- OpenAI TTS pricing: ~$0.015 per 1000 characters (tts-1 model)
- Typical 10-min presentation: ~$0.30-0.60

## Time Guide

| Step | Time |
|------|------|
| PDF Export | 30-60 seconds |
| Google Drive Upload | 5-10 seconds |
| Google Drive Folder Check | 5-10 seconds |
| Google Docs Sync | 10-30 seconds |
| Audio Regeneration (⚠️ costs) | 2-5 minutes |
| Video Export (10-min video) | 15-25 minutes |
| Video Test Mode | 2-3 minutes |

## Tips

### 💡 Save Money
- Only use `--regenerate-audio` when audio script actually changed
- Test with `--audio-only` first before full export
- Don't regenerate audio for visual-only changes

### ⚡ Save Time
- Use `--docs-only` for quick Google Docs updates
- Use `--video-only` when you only need to regenerate video
- Use `--test` to verify video setup before full export
- Use `--continue-on-error` for batch exports so one failure doesn't stop everything

### ✅ Best Practice Workflow
1. Update slides and/or audio script (locally or in Google Docs)
2. If edited in Google Docs: Tell AI to pull changes
3. Tell AI what you need exported
4. AI handles the rest:
   - Syncs to Google Docs (if needed)
   - Regenerates audio (if requested)
   - Exports video
   - Reports results and any errors

## Examples by Scenario (Tell AI Your Need)

### Scenario: "I updated the slides but not the audio script"
**You say**: "Export FEN_STG"  
**AI does**: Check folders → Update docs → Export & upload PDF

✅ No audio or video  
💰 Cost: $0  
⏱️ Time: ~1-2 minutes

---

### Scenario: "I need everything including video"
**You say**: "Full export FEN_STG with video"  
**AI does**: Check folders → Update docs → Export & upload PDF → Export & upload video

✅ Complete export  
💰 Cost: $0  
⏱️ Time: ~16-27 minutes

---

### Scenario: "I updated the audio script"
**You say**: "Export FEN_STG with audio regeneration and video"  
**AI does**: Check folders → Update docs → Export & upload PDF → Generate audio → Export & upload video

⚠️ Regenerates audio  
💰 Cost: OpenAI TTS API credits (~$0.30-0.60)  
⏱️ Time: ~20-35 minutes

---

### Scenario: "I only need a PDF"
**You say**: "Export FEN_STG PDF only"  
**AI does**: Check folders → Export & upload PDF

✅ Fastest option  
💰 Cost: $0  
⏱️ Time: ~40-70 seconds

---

### Scenario: "I only need to update Google Docs"
**You say**: "Sync FEN_STG to Google Docs"  
**AI does**: Check folders → Update docs

✅ Quick sync  
💰 Cost: $0  
⏱️ Time: ~15-40 seconds

---

### Scenario: "I edited the script in Google Docs"
**You say**: "Pull FEN_STG from Google Docs, then export with audio"  
**AI does**: Pull from Google → Generate audio → Export & upload video

✅ Two-way sync  
💰 Cost: OpenAI TTS API credits  
⏱️ Time: ~20-35 minutes

---

### Scenario: "I want to test the video export setup"
**You say**: "Test video export for FEN_STG"  
**AI does**: Video export & upload in test mode (60 seconds)

✅ Quick verification  
💰 Cost: $0  
⏱️ Time: ~2-3 minutes

---

### Scenario: "I need to export 4 decks"
**You say**: "Export FEN_STG, FEN_HMM, FEN_HMP, and FEN_GDC"  
**AI does**: Runs full workflow for each deck sequentially

✅ AI manages the queue  
💰 Cost: $0 (unless audio regeneration requested - then OpenAI TTS charges apply)  
⏱️ Time: ~1.5-2 hours

## Troubleshooting

The AI will detect and often fix these issues automatically, but here's what might happen:

### "Authentication required" or "credentials.json not found"
- Need to set up Google Cloud OAuth credentials first
- See `docs/google-docs-api-setup.md` for full setup guide
- AI will run authentication flow and save token for future use

### "Audio script and slides out of sync"
- AI will check sync before audio generation
- You'll need to fix slide headers or audio script sections to match
- Audio generation will fail if sync check doesn't pass

### "Audio generation failed"
- Check OpenAI API key (OPENAI_API_KEY) in `.env`
- Verify API credits are available
- Ensure sync check passed (slides match audio script)
- Check audio script syntax is correct

### "Video export hangs"
- AI will kill existing processes on port 3030 before starting
- If it still hangs, manually kill: `lsof -ti:3030 | xargs kill -9`
- Let AI retry the command

### "Port 3030 already in use"
- Video export script automatically kills existing processes
- If it fails, manually kill: `lsof -ti:3030 | xargs kill -9`
- Tell AI to retry

### "Video export doesn't return/complete" (FIXED)
- **Issue**: The video export script was calling `process.exit(0)` after completion, killing the terminal session
- **Root Cause**: In `scripts/video-export/exportVideo.js`, the script was force-exiting instead of returning naturally
- **Fix Applied**: 
  - Removed `process.exit(0)` from successful completion path (line 357)
  - Changed error handling to throw errors instead of calling `process.exit(1)` (line 309)
  - Script now completes naturally and returns control to wrapper
- **Status**: Fixed as of 2025-10-21. Video exports should now properly return and continue to upload step.

## Setup Requirements

### First-Time Setup

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Google Cloud Setup** (for Google Docs sync)
   - Create Google Cloud project
   - Enable Google Docs API and Google Drive API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download as `credentials.json` in project root
   - See full guide: `docs/google-docs-api-setup.md`

3. **Environment Variables**
   ```bash
   # Create .env file
   OPENAI_API_KEY=your_key_here
   ```

4. **First Authentication**
   - AI will handle authentication on first run
   - Browser will open for Google OAuth
   - Token saved to `token.json` for future use

## See Also

- Full documentation: `docs/complete-export-workflow.md`
- Google Docs API setup: `docs/google-docs-api-setup.md`
- Script/slide sync guide: `docs/script-slide-synchronization.md`
- Video export details: `docs/headless-video-export.md`
