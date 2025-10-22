# Complete Export Workflow for FEN Decks (AI-Controlled)

## Overview

This document outlines the **AI-controlled** end-to-end workflow for exporting FEN presentation decks. The AI agent manages each step using individual scripts and Google API routes.

## Key Principles

1. **AI-Managed Process**: The AI executes each step and monitors progress
2. **Modular Architecture**: Individual scripts for each step (docs, PDF, audio, video, uploads)
3. **Google API Integration**: Native Google Cloud Platform APIs via OAuth for docs and drive operations
4. **Error Recovery**: AI detects issues and retries or reports problems
5. **User Control**: Simple natural language commands ("Export FEN_STG")

## Export Steps

1. **Google Docs Sync**: Syncing script and slides to Google Docs (auto-creates folders, docs)
2. **PDF Export**: Creating PDF slides from presentation
3. **PDF Upload**: Uploading PDF to Google Drive
4. **Audio Generation** (optional): Creating narration files from audio scripts with sanitization
5. **Video Export** (optional): Recording and encoding presentation videos
6. **Video Upload** (optional): Uploading videos to Google Drive

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI-CONTROLLED EXPORT WORKFLOW                 │
│                                                                   │
│  User: "Export FEN_STG"                                          │
│  AI: Manages entire process step-by-step                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  Step 1: Check/Create Folders          │
        │  AI runs: 01-check-folder.js           │
        │                                        │
        │  - Search for deck folder in Drive     │
        │  - Create folder if not found          │
        │  - Create parent folder if needed      │
        │  - Return folder ID                    │
        │                                        │
        │  Script: export-steps/01-check-        │
        │          folder.js                     │
        │  Time: ~5-10 seconds                   │
        │  Cost: $0                              │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  Step 2: Check/Update Google Docs      │
        │  AI runs: 02-check-docs.js             │
        │                                        │
        │  - Read local markdown files           │
        │  - Search for existing Google Docs     │
        │  - Compare content                     │
        │  - Create new or update existing docs  │
        │  - Return Google Doc URLs              │
        │                                        │
        │  Script: export-steps/02-check-docs.js │
        │  Time: ~10-30 seconds                  │
        │  Cost: $0                              │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  Step 3: PDF Export & Upload           │
        │  AI runs: 03-export-pdf.js             │
        │                                        │
        │  - Use Slidev's export command         │
        │  - Export complete slides (no clicks)  │
        │  - Auto-version (e.g., _010.pdf)       │
        │  - Upload to Google Drive folder       │
        │  - Return Drive view link              │
        │                                        │
        │  Script: export-steps/03-export-pdf.js │
        │  Time: ~30-60 seconds                  │
        │  Cost: $0                              │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │   Step 4: Audio Generation (Optional)  │
        │  AI runs: 04-generate-audio.js         │
        │                                        │
        │  - Sanitize script (replace forbidden  │
        │    words like "comprehensive")         │
        │  - Check slide/script sync             │
        │  - Delete old audio files              │
        │  - Generate new audio via ElevenLabs   │
        │  - Save to audio/oai/ directory        │
        │                                        │
        │  Script: export-steps/04-generate-     │
        │          audio.js                      │
        │  Time: ~2-5 minutes                    │
        │  Cost: ⚠️ $0.30-$1.00 per deck         │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  Step 5: Video Export & Upload         │
        │     (Optional)                         │
        │  AI runs: 05-export-video.js           │
        │                                        │
        │  - Start Slidev server (port 3030)     │
        │  - Record with Playwright + Audio      │
        │  - Encode as MP4 (1920x1080)           │
        │  - Auto-version (e.g., _001.mp4)       │
        │  - Upload video to Google Drive        │
        │  - Stop server and cleanup             │
        │                                        │
        │  Script: export-steps/05-export-       │
        │          video.js                      │
        │  Time: ~15-25 minutes                  │
        │  Cost: $0                              │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │         AI Reports Results             │
        │  - Shows completion status             │
        │  - Reports any errors                  │
        │  - Provides file paths/URLs            │
        └────────────────────────────────────────┘
```

## Prerequisites

### Required Tools
- **Node.js**: v18.0.0 or higher
- **FFmpeg**: For video encoding (installed via `@ffmpeg-installer/ffmpeg`)
- **Playwright Chromium**: For headless recording (installed)
- **Google Cloud Project**: For Google Docs/Drive API access

### Environment Variables
Create a `.env` file in the project root:
```bash
# Required for audio generation
OPENAI_API_KEY=your_openai_key

# Optional: for PDF export
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Google Cloud Setup

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or use existing

2. **Enable APIs**
   - Enable Google Docs API
   - Enable Google Drive API

3. **Create OAuth Credentials**
   - Create OAuth 2.0 client ID (Desktop app)
   - Download credentials as `credentials.json`
   - Place in project root directory

4. **First-Time Authentication**
   ```bash
   npm run sync-google-docs FEN_STG
   ```
   - Browser opens for OAuth consent
   - Sign in and grant permissions
   - Token saved to `token.json` for future use

See full setup guide: `docs/google-docs-api-setup.md`

### File Structure
Each deck should have:
```
decks/FEN_[CODE]/
  ├── slides.md              # Presentation slides
  ├── audio/
  │   ├── audio_script.md    # Audio script with sections
  │   ├── config.json        # Audio configuration
  │   └── oai/               # Generated audio files (MP3s)
  │       ├── FEN_[CODE]1_1.mp3
  │       ├── FEN_[CODE]1_2.mp3
  │       └── ...
  └── img/                   # Images used in slides
```

## Step 1: Google Docs Sync (AI-Managed)

### What The AI Does
1. Runs `node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos" --root-folder="FirstEnroll || Videos"`
2. Monitors output for success/errors
3. Reports Google Doc URLs and folder ID to user

### What The Script Does
- Authenticates with Google APIs using OAuth (uses saved token if available)
- Finds or creates 3-level folder structure:
  - Root folder: `FirstEnroll || Videos`
  - Base folder: `Product Videos`
  - Deck folder: `FEN_STG` (or whatever deck you're exporting)
- Reads local markdown files (`audio_script.md`, `slides.md`)
- Searches for existing Google Docs by name
- Compares content to detect changes
- Creates new docs or updates existing ones
- Returns folder ID and Google Doc URLs

### Folder Structure
All exports are organized in a 3-level hierarchy:
```
FirstEnroll || Videos (root)
  └─ Product Videos (base)
      └─ FEN_STG (deck-specific)
          ├─ FEN_STG-Script (Google Doc)
          ├─ FEN_STG-Slides (Google Doc)
          ├─ FEN_STG_010.pdf
          └─ FEN_STG_001.mp4
```

### Script Location
`scripts/google-docs-api.js`

### Key Features
- **Full Content Sync**: No truncation, handles large documents
- **Smart Updates**: Only updates if content changed
- **Auto-Folder Creation**: Creates folder structure as needed
- **No Character Limits**: Direct Google API, no content truncation
- **OAuth Authentication**: Secure authentication with token reuse

### Files Involved
- Source: `/decks/FEN_[CODE]/audio/audio_script.md`
- Source: `/decks/FEN_[CODE]/slides.md`
- Target: Google Docs in Drive (auto-created or updated)
- Auth: `credentials.json` (OAuth setup)
- Token: `token.json` (saved authentication)
- Script: `scripts/google-docs-api.js`

### Time & Cost
- **Time**: ~15-40 seconds
- **Cost**: $0

---

## Step 2: PDF Export (AI-Managed)

### What The AI Does
1. Runs `node scripts/export-steps/03-export-pdf.js FEN_STG`
2. Monitors export progress
3. Reports PDF file path and size
4. Uploads to Google Drive: `node scripts/upload-to-drive.js exports/FEN_STG_xxx.pdf FEN_STG "Product Videos" "FirstEnroll || Videos"`

### What The Script Does
- Validates deck exists
- Gets next version number (auto-increment)
- Runs Slidev's built-in export command
- Exports complete slides without incremental clicks
- Saves to `exports/` with versioned filename
- Verifies output size

### Script Location
`scripts/export-steps/03-export-pdf.js`

### Key Features
- **Auto-Versioning**: Never overwrites existing PDFs
- **Complete Slides**: Shows final state of each slide (no v-clicks)
- **Fast Export**: Uses Slidev's optimized export
- **Size Verification**: Warns if PDF is suspiciously small

### Files Involved
- Source: `/decks/FEN_[CODE]/slides.md`
- Output: `/exports/FEN_[CODE]_[VERSION].pdf`
- Script: `scripts/export-steps/03-export-pdf.js`

### Time & Cost
- **Time**: ~30-60 seconds
- **Cost**: $0

---

## Step 3: PDF Upload to Google Drive (AI-Managed)

### What The AI Does
1. Runs `node scripts/upload-to-drive.js exports/FEN_STG_xxx.pdf FEN_STG "Product Videos" "FirstEnroll || Videos"`
2. Monitors upload progress
3. Reports Google Drive view link

### What The Script Does
- Authenticates with Google Drive API (uses saved token)
- Finds or creates the 3-level folder structure:
  - Root: `FirstEnroll || Videos`
  - Base: `Product Videos`
  - Deck: `FEN_STG`
- Uploads PDF file to the deck-specific folder
- Returns Drive file ID and view link

### Script Location
`scripts/upload-to-drive.js`

### Key Features
- **Native Google API**: Direct uploads, efficient streaming
- **Folder Auto-Find**: Locates folder by name
- **OAuth Authentication**: Secure authentication with token reuse
- **Fast Uploads**: Efficient streaming upload

### Files Involved
- Source: `/exports/FEN_[CODE]_[VERSION].pdf`
- Target: Google Drive folder
- Script: `scripts/upload-to-drive.js`

### Time & Cost
- **Time**: ~5-10 seconds
- **Cost**: $0

---

## Step 4: Audio Generation (Optional, AI-Managed)

### What The AI Does
1. Runs `node scripts/export-steps/04-generate-audio.js FEN_STG`
2. Monitors progress and sync check results
3. Reports any errors (sync issues, API failures, etc.)
4. Confirms successful audio generation

### What The Script Does
1. **Sanitize Script**: Replaces forbidden words (e.g., "comprehensive" → "extensive") with case preservation
2. **Sync Check**: Runs `deckSyncCounter.js` to verify alignment (**aborts if fails**)
3. **Delete Old Audio**: Removes all `.mp3` files from `audio/oai/`
4. **Generate Audio**: Calls OpenAI TTS API for each script section (model: tts-1, voice: nova)
5. **Save Files**: Writes MP3 files with naming pattern `FEN_[CODE][SECTION]_[CLICK].mp3`

### Script Location
`scripts/export-steps/04-generate-audio.js`

### Script Sanitization (Step 4.1)

Before generating audio, the script automatically sanitizes the `audio_script.md` file by replacing forbidden words:

**Forbidden Word Replacements:**
- `comprehensive` → `extensive`
- `Comprehensive` → `Extensive`
- `COMPREHENSIVE` → `EXTENSIVE`

**Why:** We never use "comprehensive" in any context. The sanitization ensures text-to-speech APIs never speak this word.

**How It Works:**
1. Reads `decks/{DECK_ID}/audio/audio_script.md`
2. Performs case-sensitive replacements
3. Writes sanitized content back to the same file
4. Reports number of replacements made

**Script Location:** `scripts/sanitize-script.js`

### Sync Check Requirements (Step 4.2)
The sync checker verifies:
- Each audio section has a matching slide
- Section headers align between script and slides
- No missing or extra sections

**Audio generation will abort if sync check doesn't pass.**

**Video export will also abort if sync check doesn't pass** (added to Step 5 as well).

### Audio File Naming
Generated files follow the pattern:
- `FEN_STG1_1.mp3` - Section 1, Click 1
- `FEN_STG1_2.mp3` - Section 1, Click 2  
- `FEN_STG2_1.mp3` - Section 2, Click 1

### When to Regenerate Audio
- ✅ After updating audio script content
- ✅ After changing voice settings
- ✅ Before exporting a new video with updated narration
- ❌ **NOT** needed if only slides/visuals changed

### Files Involved
- Input: `/decks/FEN_[CODE]/audio/audio_script.md`
- Config: `/decks/FEN_[CODE]/audio/config.json`
- Output: `/decks/FEN_[CODE]/audio/oai/*.mp3`
- Script: `scripts/export-steps/04-generate-audio.js`
- Sync: `scripts/deckSyncCounter.js`
- Generator: `scripts/generateAudio.js`

### Time & Cost
- **Time**: ~2-5 minutes depending on script length
- **Cost**: ⚠️ **OpenAI TTS API credits** (~$0.015 per 1000 characters)
  - Typical 10-min presentation (20,000-40,000 characters): ~$0.30-0.60
- **Use Sparingly**: Only regenerate when audio script changes

## Step 5: Video Export (Optional, AI-Managed)

### ⚠️ IMPORTANT: Fullscreen Your Browser
**Before starting video export**, make sure to fullscreen your browser window for proper recording dimensions (1920x1080).

### What The AI Does
1. Runs `node scripts/export-steps/05-export-video.js FEN_STG`
2. Monitors progress (server start, recording, encoding)
3. Reports video file path and size
4. Handles errors (port conflicts, timeout issues)

### What The Script Does
1. **Sync Check**: Verifies slides and audio script are aligned (aborts if not)
2. **Version Detection**: Checks `exports/videos/` for existing videos, auto-increments
3. **Process Cleanup**: Kills any existing Slidev/Playwright processes on port 3030
4. **Server Start**: Launches Slidev on port 3030 with the target deck
5. **Duration Estimation**: Calculates total audio duration for proper timeout
6. **Playwright Recording**:
   - Launches headless Chromium (1920x1080)
   - Navigates to `http://localhost:3030`
   - Records video with built-in recorder
   - Plays audio files synchronized with slide advances
7. **Video Conversion**: Converts to MP4 with proper aspect ratio
8. **Server Stop**: Kills Slidev process
9. **Cleanup**: Removes temporary files

### Script Location
`scripts/export-steps/05-export-video.js`

### Audio Synchronization
Audio files in `decks/FEN_[CODE]/audio/oai/` are matched to script sections:
1. Reads `audio_script.md` to get section structure
2. Matches sections to audio files by naming pattern
3. Uses FFprobe to get exact duration of each audio file
4. Waits for audio duration + small buffer (100ms) before advancing

### Video Quality Settings
| Setting | Value | Description |
|---------|-------|-------------|
| Resolution | 1920x1080 | Full HD 16:9 |
| Video Codec | libx264 | H.264 (widely compatible) |
| CRF | 18 | High quality (0-51 scale, lower = better) |
| Preset | medium | Encoding speed vs compression |
| Audio Codec | aac | AAC audio (widely compatible) |
| Audio Bitrate | 192k | High quality audio |

### Files Involved
- Input: `/decks/FEN_[CODE]/slides.md`
- Audio: `/decks/FEN_[CODE]/audio/oai/*.mp3`
- Output: `/exports/videos/FEN_[CODE]_[VERSION].mp4`
- Temporary: `/temp/video-export/`
- Scripts: `scripts/export-steps/05-export-video.js`, `scripts/video-export/exportVideo.js`

### Test Mode
Use `--test` flag for 60-second video (quick verification):
- AI runs: `node scripts/export-steps/05-export-video.js FEN_STG --test`
- Time: ~2-3 minutes
- Use when: Verifying video setup before full export
- **Remember**: Fullscreen your browser window before test export too!

### Time & Cost
- **Time**: ~15-25 minutes per 10-minute video (or ~2-3 minutes in test mode)
- **File Size**: ~300-500 MB per 10-minute video at medium-high quality
- **Cost**: $0
- **Versioning**: Automatic, cannot overwrite existing versions
- **Audio Sync**: Critical - uses exact FFprobe durations
- **Port Management**: Automatically kills processes on port 3030 before starting

---

## Step 6: Video Upload to Google Drive (Optional, AI-Managed)

### What The AI Does
1. Runs `node scripts/upload-to-drive.js exports/videos/FEN_STG_xxx.mp4 FEN_STG "Product Videos" "FirstEnroll || Videos"`
2. Monitors upload progress
3. Reports Google Drive view link

### What The Script Does
- Authenticates with Google Drive API (uses saved token)
- Finds or creates the 3-level folder structure
- Uploads video file to the deck-specific folder
- Returns Drive file ID and view link

### Script Location
`scripts/upload-to-drive.js`

### Key Features
- **Native Google API**: Direct uploads, efficient streaming
- **Large File Support**: Handles large video files (300-500 MB+)
- **OAuth Authentication**: Secure authentication with token reuse
- **Progress Tracking**: Shows upload progress for large files

### Files Involved
- Source: `/exports/videos/FEN_[CODE]_[VERSION].mp4`
- Target: Google Drive folder
- Script: `scripts/upload-to-drive.js`

### Time & Cost
- **Time**: ~30-120 seconds (depending on file size and connection speed)
- **Cost**: $0

## How AI Manages The Full Workflow

### Natural Language Commands
You simply tell the AI what you need:
- "Export FEN_STG" → Standard workflow (PDF + Drive + Docs)
- "Full export FEN_STG" → Complete workflow (PDF + Drive + Docs + Video)
- "Export FEN_STG with audio" → Full workflow with audio regeneration
- "Just PDF for FEN_STG" → PDF export and upload only
- "Just sync FEN_STG docs" → Docs sync only
- "Export FEN_STG video only" → Video export only
- "Test video for FEN_STG" → Test mode video

### What The AI Does
1. **Interprets your request**: Determines which steps are needed
2. **Executes scripts sequentially**:
   - Docs sync (if needed): `node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos" --root-folder="FirstEnroll || Videos"`
   - PDF export (if needed): `node scripts/export-steps/03-export-pdf.js FEN_STG`
   - PDF upload (if needed): `node scripts/upload-to-drive.js exports/FEN_STG_xxx.pdf FEN_STG "Product Videos" "FirstEnroll || Videos"`
   - Audio gen (if requested): `node scripts/export-steps/04-generate-audio.js FEN_STG`
   - Video export (if needed): `node scripts/export-steps/05-export-video.js FEN_STG [--test]`
   - Video upload (if needed): `node scripts/upload-to-drive.js exports/videos/FEN_STG_xxx.mp4 FEN_STG "Product Videos" "FirstEnroll || Videos"`
3. **Monitors output**: Watches for errors, success messages, file paths
4. **Reports results**: Shows you Google Drive links, Google Doc URLs, video paths, any errors
5. **Handles errors**: Retries or provides guidance if something fails

### Multiple Deck Support
Tell AI to export multiple decks:
- "Export FEN_STG, FEN_HMM, FEN_HMP, and FEN_GDC"
- AI runs the workflow for each deck sequentially
- Reports progress and results for each
- Continues even if one deck fails

## Troubleshooting (AI Will Help With These)

### Common Issues

#### Authentication Failed
**Error**: `No authentication found` or `credentials.json not found`  
**What AI does**: 
- Prompts you to set up Google Cloud OAuth credentials
- Points you to `docs/google-docs-api-setup.md`
- Runs authentication flow when credentials are ready
- Saves token to `token.json` for future use

**Your action**: Set up Google Cloud project and download credentials.json

#### Sync Check Failed
**Error**: `Sync check failed` or `Audio script and slides out of sync`  
**What AI does**: 
- Runs `node scripts/deckSyncCounter.js FEN_STG` to show misalignment
- Reports which sections don't match
- Waits for you to fix the issue

**Your action**: Fix slide headers or audio script sections to match

#### Video Export Hangs
**Error**: Server doesn't respond or process hangs  
**What AI does**: 
- Attempts to kill existing processes: `pkill -9 -f "slidev.*3030"`
- Clears port: `lsof -ti:3030 | xargs kill -9`
- Retries the export

**Your action**: Wait for AI to retry, or manually kill processes if needed

#### Port 3030 Already in Use
**Error**: `EADDRINUSE: address already in use :::3030`  
**What AI does**: 
- Video export script automatically kills existing processes
- If that fails, AI runs manual cleanup commands
- Retries the export

**Your action**: None - AI handles this automatically

#### EMFILE: Too Many Open Files
**Error**: `EMFILE: too many open files, watch`  
**What this means**: Slidev's file watcher is trying to monitor too many files
**What AI does**: 
- Retries with different approach
- May suggest increasing system file limits

**Your action**: Let AI handle retry, or increase system limits if persistent

### Performance Tips

1. **Batch Processing**: Tell AI to export multiple decks
   - "Export FEN_STG, FEN_HMM, FEN_HMP, and FEN_GDC"
   - AI runs them sequentially with progress reports

2. **Skip Unchanged Steps**: Be specific about what you need
   - "Just sync FEN_STG docs" → Skips video export
   - "Export FEN_STG video only" → Skips docs sync

3. **Test First**: Verify setup before full export
   - "Test video export for FEN_STG"
   - AI uses `--test` flag for 60-second video

4. **Monitor Resources**: AI will report if issues arise
   - Disk space warnings
   - Memory issues
   - Long-running processes

## File Outputs

### After Complete Export

```
/Users/cjohndesign/dev/FEN/
├── credentials.json            # Google OAuth credentials (DO NOT COMMIT)
├── token.json                  # Saved auth token (DO NOT COMMIT)
│
├── exports/
│   ├── FEN_STG_010.pdf        # Latest PDF export
│   ├── FEN_STG_009.pdf        # Previous version
│   └── videos/
│       ├── FEN_STG_001.mp4    # Latest video export
│       └── FEN_STG_002.mp4    # Previous version
│
├── decks/FEN_STG/
│   ├── slides.md               # Source slides
│   └── audio/
│       ├── audio_script.md     # Source script
│       └── oai/
│           ├── FEN_STG1_1.mp3  # Generated audio
│           └── ...
│
└── Google Drive (FirstEnroll || Videos → Product Videos → FEN_STG/)
    ├── FEN_STG_010.pdf         # Latest PDF
    ├── FEN_STG_001.mp4         # Latest video
    ├── FEN_STG-Script (Doc)    # Synced script
    └── FEN_STG-Slides (Doc)    # Synced slides
```

## Version Control

### Git Ignore Rules
```gitignore
# Authentication
credentials.json
token.json

# Large video files
exports/videos/
temp/video-export/

# Keep PDFs but not videos
!exports/*.pdf

# Environment
.env
```

### Versioning Strategy
- **Automatic Versioning**: All exports auto-increment (001, 002, 003...)
- **No Overwrites**: Each export creates a new version
- **Manual Cleanup**: Periodically remove old versions to save space
- **Google Drive**: Keep only latest version (manually delete old)

## Time Estimates

Per deck, expect:
- **PDF Export**: 30-60 seconds
- **Google Drive Upload**: 5-10 seconds
- **Google Drive Folder Check**: 5-10 seconds
- **Google Docs Sync**: 10-30 seconds
- **Audio Regeneration**: 2-5 minutes (⚠️ costs money)
- **Video Export**: 15-25 minutes (for 10-minute presentation)
- **Standard Export (PDF + Docs)**: ~1-2 minutes per deck
- **Full Export (PDF + Docs + Video)**: ~16-27 minutes per deck
- **Full Export With Audio**: ~20-35 minutes per deck

For 4 decks (FEN_STG, FEN_HMM, FEN_HMP, FEN_GDC):
- **Standard (PDF + Docs)**: ~5-10 minutes
- **Full (with video, no audio)**: ~1.5-2 hours
- **Full (with video + audio)**: ~2-2.5 hours

## Best Practices

1. **Be Clear With AI**: Tell AI exactly what you need
   - "Export FEN_STG" = standard workflow (PDF + Drive + Docs)
   - "Full export FEN_STG" = complete workflow (PDF + Drive + Docs + Video)
   - "Export FEN_STG with audio" = include audio regeneration
   - "Just PDF for FEN_STG" = PDF export and upload only
   - "Just sync docs for FEN_STG" = docs only

2. **Regenerate Audio Strategically**: Only when audio script changes (saves money)
   - AI will ask if you're sure before regenerating audio
   - ~$0.30-0.60 per deck in OpenAI TTS API costs

3. **Test Video First**: Verify setup before full export
   - "Test video for FEN_STG"
   - 60-second video in ~2-3 minutes
   - **Remember to fullscreen browser window first!**

4. **Monitor First Export**: Watch AI's output on first export
   - Catch issues early
   - AI will report errors clearly

5. **Keep Local Copies**: Don't delete local exports until verified
   - Videos auto-version (_001, _002, etc.)
   - AI reports file paths

6. **Use Two-Way Sync**: Edit in Google Docs for collaboration
   - "Pull FEN_STG from Google Docs"
   - AI downloads changes to local files

7. **Check Sync Before Audio**: AI checks automatically
   - Sync must pass before audio generation
   - AI reports misalignments

8. **Batch Similar Decks**: AI handles sequential processing
   - "Export FEN_STG, FEN_HMM, and FEN_HMP"
   - AI continues even if one fails

## Next Steps

1. **Set Up Google Cloud** (One-Time Setup)
   - Follow guide: `docs/google-docs-api-setup.md`
   - Create OAuth credentials
   - Download `credentials.json` to project root
   - AI will handle first-time authentication

2. **Run Test Export**
   - Tell AI: "Test video export for FEN_STG"
   - AI runs 60-second test video
   - Verify quality and setup

3. **Review Outputs**
   - AI provides Google Docs URLs
   - AI reports video file paths
   - Check quality and synchronization

4. **Standard Export**
   - Tell AI: "Export FEN_STG"
   - AI runs standard workflow (PDF + Drive + Docs)
   - ~1-2 minutes total

5. **Full Export** (if you need video)
   - Tell AI: "Full export FEN_STG with video"
   - AI runs complete workflow (PDF + Drive + Docs + Video)
   - ~16-27 minutes total

6. **Batch Export** (if needed)
   - Tell AI: "Export FEN_STG, FEN_HMM, FEN_HMP, and FEN_GDC"
   - AI processes each deck sequentially
   - Time varies based on what's included

## Support

### Getting Help

**Tell the AI about any issues!** The AI will:
- Diagnose the problem
- Check relevant logs
- Suggest solutions
- Retry operations
- Point you to relevant documentation

### Documentation Resources
- `docs/complete-export-quick-reference.md` - Quick reference for AI workflows
- `docs/google-docs-api-setup.md` - Google Cloud OAuth setup
- `docs/script-slide-synchronization.md` - Sync issues and fixes
- `docs/headless-video-export.md` - Video export technical details
