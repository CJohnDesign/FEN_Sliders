# Google Docs API Setup Guide

This guide will help you set up the Google Docs API for automatic document synchronization.

## Prerequisites

- A Google Cloud account
- Node.js 18+ installed
- Access to Google Drive where you want to create documents

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Name it something like "FEN-Deck-Export"
4. Click **Create**

## Step 2: Enable Required APIs

1. In the Cloud Console, go to **APIs & Services** → **Library**
2. Search for and enable these APIs:
   - **Google Docs API**
   - **Google Drive API**

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - User Type: **External** (or Internal if you have a Google Workspace)
   - App name: `FEN Deck Export`
   - User support email: Your email
   - Developer contact: Your email
   - Click **Save and Continue**
   - Scopes: Click **Save and Continue** (we'll add scopes in code)
   - Test users: Add your Google account email
   - Click **Save and Continue**
4. Back to creating OAuth client ID:
   - Application type: **Desktop app**
   - Name: `FEN Deck Export Desktop`
   - Click **Create**
5. Click **DOWNLOAD JSON** (or the download icon)
6. Save the file as `credentials.json` in the **project root** directory (`/Users/cjohndesign/dev/FEN/credentials.json`)

## Step 4: Install Dependencies

Run this command to install the required packages:

```bash
npm install
```

This will install:
- `googleapis` - Official Google APIs client library
- `@google-cloud/local-auth` - Local authentication helper

## Step 5: Test the Setup

Try syncing a deck to Google Docs:

```bash
npm run sync-google-docs FEN_STG -- --parent-folder="Product Videos"
```

The first time you run this:
1. A browser window will open
2. Sign in to your Google account
3. Grant the requested permissions
4. The token will be saved to `token.json` for future use

## Usage

### Sync a single deck

```bash
# Basic sync (creates docs in root Drive)
npm run sync-google-docs FEN_STG

# Sync to a specific folder
npm run sync-google-docs FEN_STG -- --folder=FEN_STG

# Sync to a folder inside a parent folder
npm run sync-google-docs FEN_STG -- --folder=FEN_STG --parent-folder="Product Videos"
```

### What it does

For each deck, it will:
1. ✅ Find or create the specified Google Drive folder
2. ✅ Read the local `audio_script.md` and `slides.md` files
3. ✅ Search for existing Google Docs (`DECK_ID-Script` and `DECK_ID-Slides`)
4. ✅ Compare content - if different, update the docs
5. ✅ If docs don't exist, create them with full content
6. ✅ Return URLs to the created/updated documents

### Features

- **Full content sync** - No truncation issues like with MCP tools
- **Idempotent** - Only updates when content actually changes
- **Folder management** - Automatically finds or creates folders
- **Content comparison** - Won't update docs if content is identical
- **Error handling** - Clear error messages and recovery

## Security Notes

### Important Files

Add these to your `.gitignore` (if not already there):

```bash
echo "credentials.json" >> .gitignore
echo "token.json" >> .gitignore
```

- **credentials.json** - Contains your OAuth client credentials (sensitive)
- **token.json** - Contains your access/refresh tokens (very sensitive)

### Token Management

- The `token.json` file is created after first authentication
- It contains refresh tokens that allow the script to run without re-authenticating
- If you need to re-authenticate, delete `token.json` and run the script again
- Keep these files secure and never commit them to version control

## Troubleshooting

### "credentials.json not found"

Make sure you downloaded the OAuth credentials and saved them as `credentials.json` in the project root.

### "Access blocked: This app's request is invalid"

Make sure you:
1. Enabled both Google Docs API and Google Drive API
2. Configured the OAuth consent screen
3. Added your email as a test user (if using External user type)

### "The caller does not have permission"

Make sure the APIs are enabled in your Google Cloud project.

### "Browser doesn't open for authentication"

The script will print a URL in the console. Copy and paste it into your browser manually.

## Integration with Export Scripts

You can now update your export step scripts to use this instead of the MCP tools:

```javascript
import { syncDeckDocuments } from './google-docs-api.js';

// In your export script
const result = await syncDeckDocuments('FEN_STG', {
  folder: 'FEN_STG',
  parentFolder: 'Product Videos'
});

console.log(`Script Doc: ${result.script.id}`);
console.log(`Slides Doc: ${result.slides.id}`);
```

## Cost

Google Docs API and Google Drive API are **free** for normal usage levels. There are quotas but they're very generous for this use case.

## Next Steps

Once this is working, you can:
1. Update `scripts/export-steps/02-check-docs.js` to use this API directly
2. Remove dependency on Zapier MCP tools for Google Docs
3. Add this to your complete export workflow for reliable, automated doc syncing

