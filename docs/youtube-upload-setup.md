# YouTube Upload Setup

> **⚠️ CURRENTLY BLOCKED**: This feature is fully implemented but cannot be used yet due to limited FirstEnroll access. See "Current Blocker" section at the bottom of this document for details.

## Overview

Upload videos directly to YouTube using the Google API (no MCP/Zapier needed).

**Features:**
- ✅ Automatically extracts title from slides.md H1 heading
- ✅ Automatically extracts description from subtitle line
- ✅ Uploads as **unlisted** (not public)
- ✅ Sets **not made for kids**
- ✅ Uses same authentication as Google Drive/Docs
- ✅ **Enforces upload to FirstEnroll channel only**

**Status:** Feature complete, ready to activate when FirstEnroll admin access is granted.

## ⚠️ Current Blocker: FirstEnroll Access Limitations

**STATUS: Feature complete but currently unusable**

This YouTube upload integration is **fully implemented and ready**, but cannot be used yet due to access limitations:

### The Problem

- **Limited FirstEnroll Access**: Currently only have guest/contributor access to FirstEnroll channel
- **API Upload Permissions**: YouTube API upload requires channel management/admin permissions
- **Token Persistence**: Would need to re-authenticate with FirstEnroll admin account, which would overwrite the current working token used for Google Drive/Docs

### What's Needed to Activate

**Option 1: Full Admin Access** (Preferred)
- Grant full admin/manager access to FirstEnroll YouTube channel
- Can then authenticate once with admin account
- Single token will work for Drive, Docs, AND YouTube uploads

**Option 2: Shared Admin Token**
- A FirstEnroll admin authenticates on this machine
- Shares the resulting `token.json` file
- Would need to be refreshed periodically (tokens can expire)

**Option 3: Manual Upload** (Current Workaround)
- Continue to upload videos to Google Drive
- FirstEnroll admin manually uploads to YouTube
- Use the exported metadata (title/description from slides.md) for consistency

### What's Already Built

✅ Auto-extracts title from slides.md H1  
✅ Auto-extracts description from subtitle  
✅ Uploads as unlisted, not made for kids  
✅ Verifies FirstEnroll channel before upload  
✅ Returns video URLs and metadata  
✅ Integrated with export workflow  

---

## Setup Instructions (When Access is Granted)

### Step 1: Enable YouTube Data API v3

1. Go to your [Google Cloud Console](https://console.cloud.google.com/apis/library/youtube.googleapis.com?project=drive-and-docs-475818)
2. Make sure your project is selected: **drive-and-docs-475818**
3. Click **"Enable"** button
4. Wait for it to activate (~30 seconds)

### Step 2: Re-Authenticate with YouTube Scope (as FirstEnroll)

**IMPORTANT:** Make sure you authenticate with the correct Google account that manages FirstEnroll.

```bash
# Delete existing token
rm token.json

# Before running this, go to YouTube Studio and make sure you're signed in as FirstEnroll:
# https://studio.youtube.com/

# Run any script to re-authenticate (will include YouTube scope now)
node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos"

# Browser will open - MAKE SURE to:
# 1. Sign in with the Google account that manages FirstEnroll
# 2. Approve ALL the OAuth permissions (Docs, Drive, YouTube)
# 3. New token.json will be saved with YouTube permissions for FirstEnroll
```

### Step 3: Verify You're Authenticated as FirstEnroll

**Always run this before uploading to confirm you're uploading to FirstEnroll:**

```bash
node scripts/check-youtube-channel.js
```

This will show you:
- Which YouTube channel(s) you have access to
- Which channel is your default (where videos will upload)
- ✔ Confirmation if you're authenticated as FirstEnroll
- ⚠️ Warning if you're NOT authenticated as FirstEnroll

## Usage (When Activated)

### Basic Upload (Auto-extracts title and description from slides.md)

```bash
node scripts/upload-to-youtube.js exports/videos/FEN_STG_002.mp4
```

This will:
- Extract the **H1 title** from `decks/FEN_STG/slides.md` (e.g., "Stable Guard Plan Overview")
- Extract the **subtitle** as description (e.g., "Understanding the details and benefits of the Stable Guard Plans")
- Upload as **unlisted**
- Set **not made for kids**
- Upload to the **FirstEnroll channel** (will error if not FirstEnroll)
- Return YouTube video link

### Custom Title

```bash
node scripts/upload-to-youtube.js exports/videos/FEN_STG_002.mp4 "Custom Title"
```

### With Description

```bash
node scripts/upload-to-youtube.js exports/videos/FEN_STG_002.mp4 "Title" "This is the description"
```

## How It Works

### Title and Description Extraction

The script reads the first H1 heading and the following line from slides.md:

**slides.md:**
```markdown
# Stable Guard Plan Overview

Understanding the details and benefits of the **Stable Guard** Plans.
```

Becomes:
- **YouTube Title**: "Stable Guard Plan Overview"
- **YouTube Description**: "Understanding the details and benefits of the Stable Guard Plans"

The script automatically removes markdown formatting (like `**bold**`) from the description.

### Video Settings

All uploads use these settings:
- **Privacy**: Unlisted (not public, not private)
- **Made for Kids**: No
- **Category**: People & Blogs
- **Description**: Auto-generated or custom

### FirstEnroll Verification

Before every upload, the script:
1. Checks which YouTube channel you're authenticated as
2. Verifies the channel name includes "FirstEnroll"
3. **Stops and exits with error** if not FirstEnroll
4. Only proceeds if authenticated as FirstEnroll

### Output

After successful upload, you'll get:
- Video ID
- Watch URL: `https://www.youtube.com/watch?v={videoId}`
- Studio URL: `https://studio.youtube.com/video/{videoId}/edit`

## Full Export Workflow (When Activated)

```bash
# 1. Export PDF
node scripts/export-steps/01-export-pdf.js FEN_STG

# 2. Upload PDF to Drive
node scripts/upload-to-drive.js exports/FEN_STG_010.pdf FEN_STG "Product Videos"

# 3. Sync Google Docs
node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos"

# 4. Generate Audio (optional, costs money)
node scripts/export-steps/03-generate-audio.js FEN_STG

# 5. Export Video
node scripts/export-steps/04-export-video.js FEN_STG

# 6. Upload Video to Drive
node scripts/upload-to-drive.js exports/videos/FEN_STG_002.mp4 FEN_STG "Product Videos"

# 7. Upload Video to YouTube (BLOCKED - requires FirstEnroll admin access)
node scripts/upload-to-youtube.js exports/videos/FEN_STG_002.mp4
```

## Troubleshooting

### "No authentication token found"

You need to re-authenticate:
```bash
rm token.json
node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos"
```

### "Missing YouTube permissions"

The token was created without YouTube scope. Re-authenticate:
```bash
rm token.json
# Run any script to get new token with YouTube scope
```

### "YouTube API quota exceeded"

YouTube has daily upload quotas. Wait until tomorrow or request quota increase in GCP.

### "insufficientPermissions"

Make sure:
1. YouTube Data API v3 is enabled in GCP
2. You re-authenticated after enabling the API
3. You approved the YouTube scope during OAuth
4. **You have admin access to FirstEnroll channel**

### "Not authenticated as FirstEnroll"

The script detected you're logged in as a different channel. Follow the instructions to:
1. Switch to FirstEnroll in YouTube Studio
2. Delete token.json
3. Re-authenticate as FirstEnroll

## API Costs

- **YouTube uploads**: FREE (subject to quota limits)
- **Daily quota**: 10,000 units (1 upload = ~1,600 units, so ~6 videos/day)
- **Request quota increase**: Available in GCP Console if needed

## Security

- `credentials.json` and `token.json` are in `.gitignore`
- Never commit these files to Git
- Token gives full access to your Google Drive, Docs, and YouTube
- Keep credentials secure

## See Also

- `docs/complete-export-workflow.md` - Full export documentation
- `docs/google-docs-api-setup.md` - Google Cloud setup
- [YouTube Data API Docs](https://developers.google.com/youtube/v3/docs)

