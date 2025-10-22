# Google Docs Export Process

## Overview

This document describes the first step in the video export workflow: creating Google Docs versions of your presentation slides and audio scripts. This allows for easy editing, sharing, and collaboration before generating the final video.

## Prerequisites

- Access to the Zapier MCP with Google Drive and Google Docs integrations configured
- Local Slidev presentation with:
  - `slides.md` - The presentation slides in markdown format
  - `audio/audio_script.md` - The audio narration script

## Folder Structure

Each presentation should have a corresponding folder in Google Drive under the "Product Videos" folder with the following structure:

```
Product Videos/
  └── FEN_[CODE]/
      ├── FEN_[CODE]-Slides (Google Doc)
      └── FEN_[CODE]-Script (Google Doc)
```

Example:
- `FEN_HMM/` - Harmony Care Plan
- `FEN_HMP/` - Harmony Care Plus
- `FEN_STG/` - Stable Guard

## Process

### Step 1: Create the Google Drive Folder

If the folder doesn't already exist in Google Drive:

```javascript
// Use the Zapier MCP to create the folder
mcp_Zapier_google_drive_create_folder({
  title: "FEN_[CODE]",
  folder: "1EenwYgUL7HsKwbxHliJto_IF4M1GBp4_" // Product Videos folder ID
})
```

Save the returned folder ID for the next step.

### Step 2: Create the Slides Google Doc

The slides doc contains the presentation content from `slides.md`:

```javascript
// Use the Zapier MCP to create the document
mcp_Zapier_google_docs_create_document_from_text({
  title: "FEN_[CODE]-Slides",
  folder: "[FOLDER_ID_FROM_STEP_1]",
  file: "[CONTENT_FROM_slides.md]"
})
```

**Note**: The API requires the full content to be sent in the request. Read the local `slides.md` file first, then pass its contents to the API.

### Step 3: Create the Script Google Doc

The script doc contains the narration from `audio/audio_script.md`:

```javascript
// Use the Zapier MCP to create the document
mcp_Zapier_google_docs_create_document_from_text({
  title: "FEN_[CODE]-Script",
  folder: "[FOLDER_ID_FROM_STEP_1]",
  file: "[CONTENT_FROM_audio/audio_script.md]"
})
```

## Example: Creating Docs for FEN_STG

Here's a complete example for creating the Stable Guard documents:

```bash
# 1. Local files are at:
#    - /Users/cjohndesign/dev/FEN/decks/FEN_STG/slides.md
#    - /Users/cjohndesign/dev/FEN/decks/FEN_STG/audio/audio_script.md

# 2. Create the Google Drive folder:
#    Product Videos/FEN_STG/

# 3. Read local files and create Google Docs:
#    - FEN_STG-Slides (from slides.md)
#    - FEN_STG-Script (from audio_script.md)
```

## Output

After completion, you'll have:

1. A new folder in Google Drive under "Product Videos"
2. Two Google Docs ready for editing:
   - **Slides doc** - Contains the presentation content with all markdown formatting preserved
   - **Script doc** - Contains the audio narration organized by slide section

## Next Steps

After creating the Google Docs:

1. **Review & Edit** - Team members can review and edit the content in Google Docs
2. **Video Export** - Use `npm run export-video` to generate the video (see `video-export-quickstart.md`)
3. **YouTube Upload** - Use `npm run youtube-upload` to publish the video (see `youtube-upload.md`)

## Notes

- The Google Docs creation process reads from your local markdown files and sends the content to the Google Docs API
- This is the only way to programmatically create Google Docs - there's no direct "import file" option
- Large files may take 2-3 minutes to process
- If the API times out, simply retry the document creation

## PDF Export Workflow

### Complete Process for PDF Export and Upload

For exporting the Slidev presentation itself as a PDF:

```bash
# 1. Start the dev server (in background)
npm run deck dev FEN_[CODE]

# 2. Wait 5 seconds for server to spin up
sleep 5

# 3. Export PDF (this also uploads to Supabase automatically)
npm run deck export FEN_[CODE]
```

The export command will:
1. Generate a versioned PDF (e.g., `FEN_IVCH_001.pdf`)
2. Save it locally to `/Exports/`
3. Upload it to Supabase storage automatically
4. Provide a Supabase URL for Google Drive upload

### Uploading PDF to Google Drive

After the PDF export completes, upload to Google Drive:

```javascript
mcp_Zapier_google_drive_upload_file({
  file: "[SUPABASE_URL_FROM_EXPORT]",
  folder: "[FOLDER_ID]",
  new_name: "FEN_[CODE]_001"  // Without .pdf extension
})
```

**Important**: Do not include `.pdf` in the filename - it will be added automatically.

## Troubleshooting

### Folder Already Exists

If the folder already exists, you'll need to find it first:

```javascript
mcp_Zapier_google_drive_find_a_folder({
  title: "FEN_[CODE]"
})
```

Use the returned folder ID to create the documents.

### Document Already Exists

If a document with the same name already exists, the API will create a new document with the same name. You may want to delete or rename the old one first.

### API Timeout

If the Google Docs creation times out (especially for large scripts), use the alternative approach:

**Solution**: Use `mcp_Zapier_google_drive_create_file_from_text` with `convert: true` instead:

```javascript
mcp_Zapier_google_drive_create_file_from_text({
  title: "FEN_[CODE]-Script",
  folder: "[FOLDER_ID]",
  file: "[CONTENT]",
  convert: "true"  // Converts plain text to Google Doc
})
```

This method is more reliable for larger files and will create a Google Doc without timing out.

## Related Documentation

- **Video Export**: `video-export-quickstart.md` - How to generate MP4 videos from Slidev presentations
- **YouTube Upload**: `youtube-upload.md` - How to upload videos to YouTube (to be created)
- **Complete Workflow**: `video-export-summary.md` - Overview of the entire process

