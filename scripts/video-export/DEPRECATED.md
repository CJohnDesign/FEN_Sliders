# Deprecated Files

**⚠️ WARNING: The following files in this directory are DEPRECATED and should NOT be used.**

These files are preserved for historical reference and documentation of approaches that were explored but ultimately not adopted. They contain valuable learnings about what didn't work well.

## Deprecated Files

### 🚫 blackholeRecorder.js
**Status:** DEPRECATED  
**Reason:** Used BlackHole virtual audio device (macOS only)  
**Replaced by:** `browserRecorder.js` with MediaRecorder API  
**Issues:**
- macOS specific (not cross-platform)
- Requires external software installation (BlackHole)
- Complex audio routing
- Unreliable audio sync

---

### 🚫 browserRecorderCDP.js
**Status:** DEPRECATED  
**Reason:** Used Chrome DevTools Protocol for audio capture  
**Replaced by:** `browserRecorder.js` with MediaRecorder API  
**Issues:**
- Complex CDP implementation
- Inconsistent audio capture
- Browser-specific API
- More prone to race conditions

---

### 🚫 dualBrowserRecorder.js
**Status:** DEPRECATED  
**Reason:** Experimental dual-browser approach  
**Replaced by:** Single browser with `browserRecorder.js`  
**Issues:**
- Overly complex
- Synchronization issues between browsers
- Higher resource usage
- No clear benefit over single browser

---

### 🚫 puppeteerRecorder.js
**Status:** DEPRECATED  
**Reason:** Used Puppeteer instead of Playwright  
**Replaced by:** `browserRecorder.js` with Playwright  
**Issues:**
- Less stable headless rendering
- Worse automation reliability
- Less active development
- Playwright has better features

---

### 🚫 ffmpegRecorder.js
**Status:** DEPRECATED  
**Reason:** Direct FFmpeg screen capture approach  
**Replaced by:** `browserRecorder.js` with MediaRecorder API  
**Issues:**
- Platform-specific screen capture
- Complex audio device selection
- No browser interaction needed
- MediaRecorder is simpler and more reliable

---

### 🚫 audioTimingHelper.js
**Status:** DEPRECATED  
**Reason:** Manual audio synchronization helper  
**Replaced by:** Browser audio capture (no manual sync needed)  
**Issues:**
- Required manual timing adjustments
- Prone to drift over long presentations
- Extra processing step
- Not needed with proper browser audio capture

---

### 🚫 audioTimingProcessor.js
**Status:** DEPRECATED  
**Reason:** Manual audio synchronization processor  
**Replaced by:** Browser audio capture (no manual sync needed)  
**Issues:**
- Complex audio processing logic
- Unreliable for long videos
- Required careful tuning per deck
- Not needed with proper browser audio capture

---

### 🚫 audioProcessor.js
**Status:** POSSIBLY DEPRECATED  
**Reason:** Audio processing utilities (may not be needed)  
**Replaced by:** May not be needed with current approach  
**Status:** Needs review before removal  
**Issues:**
- Unclear if still used
- May have been for manual audio processing

---

## Current Implementation

### ✅ Active Files (Use These)

1. **exportVideo.js** - Main CLI and orchestration
2. **browserRecorder.js** - Playwright + MediaRecorder API recording
3. **serverManager.js** - Slidev server lifecycle
4. **versionManager.js** - Version numbering
5. **videoProcessor.js** - FFmpeg post-processing
6. **README.md** - Documentation

### Why This Approach Works

**Simple & Reliable:**
- Single browser with MediaRecorder API
- Captures actual browser audio (perfect sync)
- No external dependencies (BlackHole, etc.)
- Cross-platform compatible
- Minimal moving parts

**Key Insight:**
The winning approach was to use the browser's built-in `getDisplayMedia()` and MediaRecorder APIs to capture both video and audio directly from the browser, ensuring perfect synchronization without any manual timing adjustments.

---

## Cleanup Plan

### Phase 1: Mark as Deprecated ✅ DONE
- Add this DEPRECATED.md file
- Document why each file is deprecated

### Phase 2: Future Cleanup (When Confident)
After the current implementation has been stable for a few weeks:
1. Move deprecated files to `scripts/video-export/deprecated/` folder
2. Update documentation to reference deprecated folder
3. Eventually remove deprecated folder entirely

### Phase 3: Historical Archive
If needed for reference:
1. Keep one final copy in a separate `docs/video-export-history/` folder
2. Include documentation of what was tried and why it didn't work
3. Valuable for future development decisions

---

## What We Learned

### Key Lessons

1. **Simpler is Better**
   - The simplest solution (browser MediaRecorder) was the most reliable
   - Complex multi-step processes introduced failure points
   - Every abstraction layer added potential for bugs

2. **Use Platform Features**
   - Browser APIs (getDisplayMedia, MediaRecorder) are well-tested
   - External tools (BlackHole) add dependencies
   - CDP is powerful but overkill for this use case

3. **Perfect is the Enemy of Good**
   - Manual audio sync seemed like a good idea initially
   - In practice, it was fragile and required constant tuning
   - Capturing real audio from the start was the right approach

4. **Cross-Platform from Day 1**
   - macOS-specific solutions (BlackHole) limited adoption
   - Web APIs work everywhere
   - Less platform-specific code = fewer bugs

---

## Questions?

If you're considering using one of these deprecated files:
1. Check `README.md` for current best practices
2. Review this deprecation notice for why it's deprecated
3. Consider if your use case is truly different
4. Likely, the current implementation already handles your needs

**Still need help?** Check the main documentation or commit history.

