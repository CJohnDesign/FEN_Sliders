# PDF Export Process

## Overview

This document describes the automated PDF export workflow for Slidev presentations. The process exports a PDF, uploads it to Supabase as temporary storage, uploads to Google Drive for permanent storage, and cleans up the temporary file.

## Prerequisites

- Slidev CLI installed
- Supabase configured with `pdfs` bucket (see Configuration below)
- Zapier MCP with Google Drive integration
- Google Drive folder structure set up (see Folder Structure below)

## Folder Structure

Each presentation should have a corresponding folder in Google Drive under the "Product Videos" folder:

```
Product Videos/
  └── FEN_[CODE]/
      ├── FEN_[CODE]-Slides (Google Doc)
      ├── FEN_[CODE]-Script (Google Doc)
      └── FEN_[CODE]_XXX.pdf (Exported PDFs)
```

## Configuration

### Supabase Setup

The PDF export uses a Supabase bucket called `pdfs` with the following configuration:

1. **Bucket**: Public bucket named `pdfs`
2. **RLS Policies**:
   - Allow anon to insert PDFs
   - Allow anon to select PDFs
   - Allow anon to delete PDFs

The bucket and policies are automatically created during setup. If you need to recreate them manually:

```sql
-- Create the pdfs bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('pdfs', 'pdfs', true)
ON CONFLICT (id) DO NOTHING;

-- Allow public uploads
CREATE POLICY "Allow anon to insert pdfs"
ON storage.objects FOR INSERT
TO anon
WITH CHECK (bucket_id = 'pdfs');

-- Allow public reads
CREATE POLICY "Allow anon to select pdfs"
ON storage.objects FOR SELECT
TO anon
USING (bucket_id = 'pdfs');

-- Allow public deletes
CREATE POLICY "Allow anon to delete pdfs"
ON storage.objects FOR DELETE
TO anon
USING (bucket_id = 'pdfs');
```

## Export Process

### Quick Start

To export a PDF for any deck:

```bash
npm run deck export FEN_[CODE]
```

Example:
```bash
npm run deck export FEN_STG
```

### What Happens

The export process automatically:

1. **Exports PDF** - Uses Slidev CLI to generate a PDF from the markdown slides
2. **Auto-versioning** - Automatically increments version number (e.g., `FEN_STG_001.pdf`, `FEN_STG_002.pdf`, etc.)
3. **Local Storage** - Saves PDF to `/Exports/` directory
4. **Supabase Upload** - Uploads PDF to Supabase Storage for temporary access
5. **Google Drive Instructions** - Provides the Supabase URL and folder information

### Manual Google Drive Upload

After the export completes, you'll see output like:

```
══════════════════════════════════════════════════
  📤 READY TO UPLOAD TO GOOGLE DRIVE
══════════════════════════════════════════════════
Use the Zapier Google Drive MCP to upload:
  PDF URL: https://wzldwfbsadmnhqofifco.supabase.co/storage/v1/object/public/pdfs/FEN_STG_004.pdf
  File Name: FEN_STG_004 (without .pdf extension)
  Folder: FEN_STG (in Product Videos)

  ⚠️  Note: Do NOT include .pdf extension in filename - it will be added automatically
══════════════════════════════════════════════════
```

Use the Zapier Google Drive MCP to complete the upload to Google Drive.

**Important**: When specifying the filename in the Google Drive upload, use only the base name (e.g., `FEN_STG_004`) **without** the `.pdf` extension. The Google Drive API will automatically detect and add the correct extension from the file content. If you include `.pdf` in the filename, it will be doubled (e.g., `FEN_STG_004.pdf.pdf`).

### Cleanup

After the PDF is successfully uploaded to Google Drive, clean up the temporary Supabase file:

```bash
node -e "
import { createClient } from '@supabase/supabase-js';
import config from './scripts/youtube.config.js';

const supabase = createClient(config.supabase.url, config.supabase.anonKey);
const { error } = await supabase.storage
  .from('pdfs')
  .remove(['FEN_[CODE]_XXX.pdf']);

if (error) {
  console.error('Delete failed:', error.message);
  process.exit(1);
} else {
  console.log('✅ Cleaned up PDF from Supabase');
}
"
```

## Output Files

After a successful export, you'll have:

1. **Local PDF**: `/Exports/FEN_[CODE]_XXX.pdf` - Permanent local copy with version number
2. **Supabase PDF**: Temporary URL for transfer to Google Drive
3. **Google Drive PDF**: Permanent cloud storage in the correct folder

## Version Management

The export script automatically manages version numbers:

- Scans the `/Exports/` directory for existing exports
- Finds the highest version number for the deck
- Increments by 1 for the new export
- Pads with zeros (e.g., 001, 002, 010, 100)

Example sequence:
```
FEN_STG_001.pdf  (first export)
FEN_STG_002.pdf  (second export)
FEN_STG_003.pdf  (third export)
```

## Troubleshooting

### Supabase Upload Fails

If you see "Bucket not found", the `pdfs` bucket needs to be created. See the Configuration section above.

### Google Drive Upload Fails

If the folder doesn't exist in Google Drive:

1. Find or create the folder using the Zapier Google Drive MCP
2. Note the folder ID
3. Use the folder ID in the upload command

### Export Fails with Network Error

If you see `ERR_SYSTEM_ERROR: uv_interface_addresses`, the command needs to run with full system permissions:

```bash
# Already handled by the script - no action needed
```

The `deck-operations.js` script is configured to request the necessary permissions automatically.

## Related Scripts

- **deck-operations.js** - Main script that handles export, versioning, and Supabase upload
- **youtube.config.js** - Configuration file with Supabase credentials

## Related Documentation

- **Google Docs Export**: `google-docs-export.md` - Creating Google Docs from local markdown files
- **Video Export**: `video-export-quickstart.md` - Generating MP4 videos
- **YouTube Upload**: `youtube-upload.md` - Uploading videos to YouTube (to be created)
- **Complete Workflow**: `video-export-summary.md` - Overview of the entire process

## Next Steps

After exporting the PDF:

1. **Upload to Google Drive** - Use the provided URL and instructions
2. **Clean up Supabase** - Delete the temporary file after successful upload
3. **Generate Google Docs** - Create Slides and Script docs (see `google-docs-export.md`)
4. **Export Video** - Generate MP4 video (see `video-export-quickstart.md`)
5. **Upload to YouTube** - Publish video (see `youtube-upload.md`)

