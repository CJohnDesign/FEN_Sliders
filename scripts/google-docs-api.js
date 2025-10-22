#!/usr/bin/env node

/**
 * Google Docs API Integration
 * Handles creating and updating Google Docs with full content
 */

import { google } from 'googleapis';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer } from 'http';
import { exec } from 'child_process';
import readline from 'readline';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

// Scopes for Google Docs, Drive, and YouTube APIs
const SCOPES = [
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/drive.file',
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/youtube.upload'
];

const CREDENTIALS_PATH = path.join(projectRoot, 'credentials.json');
const TOKEN_PATH = path.join(projectRoot, 'token.json');

/**
 * Load saved credentials if available
 */
async function loadSavedCredentials() {
  try {
    const content = await fs.readFile(TOKEN_PATH, 'utf-8');
    const credentials = JSON.parse(content);
    return google.auth.fromJSON(credentials);
  } catch (err) {
    return null;
  }
}

/**
 * Save credentials after successful authentication
 */
async function saveCredentials(client) {
  const content = await fs.readFile(CREDENTIALS_PATH, 'utf-8');
  const keys = JSON.parse(content);
  const key = keys.installed || keys.web;
  const payload = JSON.stringify({
    type: 'authorized_user',
    client_id: key.client_id,
    client_secret: key.client_secret,
    refresh_token: client.credentials.refresh_token,
  });
  await fs.writeFile(TOKEN_PATH, payload);
}

/**
 * Open URL in default browser
 */
function openBrowser(url) {
  const start = process.platform === 'darwin' ? 'open' :
                process.platform === 'win32' ? 'start' : 'xdg-open';
  exec(`${start} "${url}"`);
}

/**
 * Authenticate with Google APIs using manual OAuth flow
 */
async function authenticate() {
  // Check if we have saved credentials
  let client = await loadSavedCredentials();
  
  if (client) {
    console.log('🔑 Using saved authentication token...\n');
    return client;
  }
  
  // No saved credentials - need to authenticate
  console.log('🔐 First-time authentication required\n');
  
  try {
    // Load credentials.json
    const credentials = JSON.parse(await fs.readFile(CREDENTIALS_PATH, 'utf-8'));
    const { client_id, client_secret, redirect_uris } = credentials.installed || credentials.web;
    
    // Create OAuth2 client
    const oAuth2Client = new google.auth.OAuth2(
      client_id,
      client_secret,
      'http://localhost:3000'
    );
    
    // Generate auth URL
    const authUrl = oAuth2Client.generateAuthUrl({
      access_type: 'offline',
      scope: SCOPES,
    });
    
    console.log('🌐 Opening browser for authentication...\n');
    console.log('📋 If the browser doesn\'t open, copy and paste this URL:\n');
    console.log('─'.repeat(80));
    console.log(authUrl);
    console.log('─'.repeat(80));
    console.log();
    
    // Open browser
    openBrowser(authUrl);
    
    // Start local server to receive callback
    const code = await new Promise((resolve, reject) => {
      const server = createServer((req, res) => {
        if (req.url.startsWith('/?code=')) {
          const code = new URL(req.url, 'http://localhost:3000').searchParams.get('code');
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end('<h1>✅ Authentication successful!</h1><p>You can close this window and return to the terminal.</p>');
          server.close();
          resolve(code);
        }
      }).listen(3000);
      
      setTimeout(() => {
        server.close();
        reject(new Error('Authentication timeout'));
      }, 120000); // 2 minute timeout
    });
    
    // Exchange code for tokens
    const { tokens } = await oAuth2Client.getToken(code);
    oAuth2Client.setCredentials(tokens);
    
    // Save credentials
    await saveCredentials(oAuth2Client);
    console.log('\n✅ Authentication successful! Token saved for future use.\n');
    
    return oAuth2Client;
  } catch (error) {
    console.error('\n❌ Authentication failed:', error.message);
    console.error('\nPlease ensure:');
    console.error('1. credentials.json exists in the project root');
    console.error('2. You have enabled Google Docs API and Google Drive API in GCP');
    console.error('3. You approve the OAuth consent screen in your browser');
    throw error;
  }
}

/**
 * Find a folder by name in Google Drive
 */
async function findFolder(drive, folderName, parentFolderId = null) {
  let query = `mimeType='application/vnd.google-apps.folder' and name='${folderName}' and trashed=false`;
  
  if (parentFolderId) {
    query += ` and '${parentFolderId}' in parents`;
  }
  
  const response = await drive.files.list({
    q: query,
    fields: 'files(id, name)',
    spaces: 'drive',
  });
  
  return response.data.files.length > 0 ? response.data.files[0] : null;
}

/**
 * Create a folder in Google Drive
 */
async function createFolder(drive, folderName, parentFolderId = null) {
  const fileMetadata = {
    name: folderName,
    mimeType: 'application/vnd.google-apps.folder',
  };
  
  if (parentFolderId) {
    fileMetadata.parents = [parentFolderId];
  }
  
  const folder = await drive.files.create({
    requestBody: fileMetadata,
    fields: 'id, name',
  });
  
  return folder.data;
}

/**
 * Find or create a folder (helper function)
 */
async function findOrCreateFolder(drive, folderName, parentFolderId = null) {
  // Try to find existing folder
  let folder = await findFolder(drive, folderName, parentFolderId);
  
  if (!folder) {
    console.log(`Creating folder: ${folderName}`);
    folder = await createFolder(drive, folderName, parentFolderId);
  } else {
    console.log(`Found existing folder: ${folderName} (${folder.id})`);
  }
  
  return folder;
}

/**
 * Ensure a folder exists (find or create) - supports nested 3-level structure
 */
async function ensureFolder(drive, folderName, parentFolderName = null, rootFolderName = null) {
  let currentFolderId = null;
  
  // Level 1: Root folder (e.g., "FirstEnroll || Videos")
  if (rootFolderName) {
    const rootFolder = await findOrCreateFolder(drive, rootFolderName, null);
    currentFolderId = rootFolder.id;
  }
  
  // Level 2: Parent/Base folder (e.g., "Product Videos")
  if (parentFolderName) {
    const parentFolder = await findOrCreateFolder(drive, parentFolderName, currentFolderId);
    currentFolderId = parentFolder.id;
  }
  
  // Level 3: Target/Deck folder (e.g., "FEN_HMM")
  const targetFolder = await findOrCreateFolder(drive, folderName, currentFolderId);
  
  return targetFolder;
}

/**
 * Find a Google Doc by name
 */
async function findDocument(drive, docName, folderId = null) {
  let query = `mimeType='application/vnd.google-apps.document' and name='${docName}' and trashed=false`;
  
  if (folderId) {
    query += ` and '${folderId}' in parents`;
  }
  
  const response = await drive.files.list({
    q: query,
    fields: 'files(id, name)',
    spaces: 'drive',
  });
  
  return response.data.files.length > 0 ? response.data.files[0] : null;
}

/**
 * Create a new Google Doc with content
 */
async function createDocument(docs, drive, title, content, folderId = null) {
  // Create empty document
  const doc = await docs.documents.create({
    requestBody: {
      title: title,
    },
  });
  
  const documentId = doc.data.documentId;
  
  // Move to folder if specified
  if (folderId) {
    await drive.files.update({
      fileId: documentId,
      addParents: folderId,
      fields: 'id, parents',
    });
  }
  
  // Add content to document
  await updateDocumentContent(docs, documentId, content);
  
  return doc.data;
}

/**
 * Update document content (replaces all content)
 */
async function updateDocumentContent(docs, documentId, content) {
  // First, get the document to find the end index
  const doc = await docs.documents.get({
    documentId: documentId,
  });
  
  const endIndex = doc.data.body.content[doc.data.body.content.length - 1].endIndex - 1;
  
  // Create batch update to delete old content and insert new
  const requests = [];
  
  // Delete all existing content (except the first newline character)
  if (endIndex > 1) {
    requests.push({
      deleteContentRange: {
        range: {
          startIndex: 1,
          endIndex: endIndex,
        },
      },
    });
  }
  
  // Insert new content
  requests.push({
    insertText: {
      location: {
        index: 1,
      },
      text: content,
    },
  });
  
  // Execute batch update
  await docs.documents.batchUpdate({
    documentId: documentId,
    requestBody: {
      requests: requests,
    },
  });
  
  console.log(`Updated document content (${content.length} characters)`);
}

/**
 * Get document content
 */
async function getDocumentContent(docs, documentId) {
  const doc = await docs.documents.get({
    documentId: documentId,
  });
  
  let content = '';
  
  if (doc.data.body && doc.data.body.content) {
    for (const element of doc.data.body.content) {
      if (element.paragraph && element.paragraph.elements) {
        for (const paragraphElement of element.paragraph.elements) {
          if (paragraphElement.textRun) {
            content += paragraphElement.textRun.content;
          }
        }
      }
    }
  }
  
  return content;
}

/**
 * Create or update a Google Doc
 */
async function createOrUpdateDocument(docs, drive, title, content, folderId = null) {
  // Find existing document
  const existingDoc = await findDocument(drive, title, folderId);
  
  if (existingDoc) {
    console.log(`Found existing document: ${title} (${existingDoc.id})`);
    
    // Get current content
    const currentContent = await getDocumentContent(docs, existingDoc.id);
    
    // Compare content
    if (currentContent.trim() === content.trim()) {
      console.log(`Content is identical, skipping update`);
      return existingDoc;
    }
    
    console.log(`Updating document with new content...`);
    await updateDocumentContent(docs, existingDoc.id, content);
    
    return existingDoc;
  } else {
    console.log(`Creating new document: ${title}`);
    return await createDocument(docs, drive, title, content, folderId);
  }
}

/**
 * Main function to sync deck documents
 */
async function syncDeckDocuments(deckId, options = {}) {
  try {
    console.log(`\n📄 Syncing Google Docs for ${deckId}\n`);
    
    // Authenticate
    const auth = await authenticate();
    const docs = google.docs({ version: 'v1', auth });
    const drive = google.drive({ version: 'v3', auth });
    
    // Read local files
    const scriptPath = path.join(projectRoot, 'decks', deckId, 'audio', 'audio_script.md');
    const slidesPath = path.join(projectRoot, 'decks', deckId, 'slides.md');
    
    if (!await fs.pathExists(scriptPath) || !await fs.pathExists(slidesPath)) {
      throw new Error(`Missing files for ${deckId}`);
    }
    
    const scriptContent = await fs.readFile(scriptPath, 'utf-8');
    const slidesContent = await fs.readFile(slidesPath, 'utf-8');
    
    // Ensure folder exists
    let folderId = null;
    if (options.folder || options.parentFolder || options.rootFolder) {
      const folder = await ensureFolder(
        drive,
        options.folder || deckId,
        options.parentFolder,
        options.rootFolder
      );
      folderId = folder.id;
    }
    
    // Create or update script document
    const scriptDocName = `${deckId}-Script`;
    console.log(`\n📝 Processing: ${scriptDocName}`);
    const scriptDoc = await createOrUpdateDocument(
      docs,
      drive,
      scriptDocName,
      scriptContent,
      folderId
    );
    
    // Create or update slides document
    const slidesDocName = `${deckId}-Slides`;
    console.log(`\n📝 Processing: ${slidesDocName}`);
    const slidesDoc = await createOrUpdateDocument(
      docs,
      drive,
      slidesDocName,
      slidesContent,
      folderId
    );
    
    console.log(`\n✅ Google Docs sync complete!\n`);
    console.log(`Script: https://docs.google.com/document/d/${scriptDoc.id}/edit`);
    console.log(`Slides: https://docs.google.com/document/d/${slidesDoc.id}/edit\n`);
    
    return {
      script: scriptDoc,
      slides: slidesDoc,
      folder: folderId,
    };
    
  } catch (error) {
    console.error(`\n❌ Error syncing documents:`, error.message);
    throw error;
  }
}

// CLI support
if (import.meta.url === `file://${process.argv[1]}`) {
  const deckId = process.argv[2];
  
  if (!deckId) {
    console.error('Usage: node google-docs-api.js <DECK_ID> [--folder=FolderName] [--parent-folder=ParentFolderName] [--root-folder=RootFolderName]');
    console.error('\nExamples:');
    console.error('  node google-docs-api.js FEN_HMM --folder=FEN_HMM');
    console.error('  node google-docs-api.js FEN_HMM --folder=FEN_HMM --parent-folder="Product Videos"');
    console.error('  node google-docs-api.js FEN_HMM --folder=FEN_HMM --parent-folder="Product Videos" --root-folder="FirstEnroll || Videos"');
    process.exit(1);
  }
  
  const options = {};
  for (let i = 3; i < process.argv.length; i++) {
    if (process.argv[i].startsWith('--folder=')) {
      options.folder = process.argv[i].split('=')[1];
    }
    if (process.argv[i].startsWith('--parent-folder=')) {
      options.parentFolder = process.argv[i].split('=')[1];
    }
    if (process.argv[i].startsWith('--root-folder=')) {
      options.rootFolder = process.argv[i].split('=')[1];
    }
  }
  
  syncDeckDocuments(deckId, options)
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}

export {
  authenticate,
  ensureFolder,
  findDocument,
  createDocument,
  updateDocumentContent,
  getDocumentContent,
  createOrUpdateDocument,
  syncDeckDocuments,
};

