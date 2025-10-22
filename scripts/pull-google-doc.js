#!/usr/bin/env node

/**
 * Pull content from Google Docs back to local files
 */

import { google } from 'googleapis';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

const TOKEN_PATH = path.join(projectRoot, 'token.json');

async function loadSavedCredentials() {
  try {
    const content = await fs.readFile(TOKEN_PATH, 'utf-8');
    const credentials = JSON.parse(content);
    return google.auth.fromJSON(credentials);
  } catch (err) {
    throw new Error('No authentication found. Run sync-google-docs first.');
  }
}

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

async function pullDocument(deckId, docType) {
  try {
    // Authenticate
    const auth = await loadSavedCredentials();
    const docs = google.docs({ version: 'v1', auth });
    const drive = google.drive({ version: 'v3', auth });
    
    // Determine document name and local path
    let docName, localPath;
    if (docType === 'script') {
      docName = `${deckId}-Script`;
      localPath = path.join(projectRoot, 'decks', deckId, 'audio', 'audio_script.md');
    } else if (docType === 'slides') {
      docName = `${deckId}-Slides`;
      localPath = path.join(projectRoot, 'decks', deckId, 'slides.md');
    } else {
      throw new Error('Invalid doc type. Use "script" or "slides"');
    }
    
    // Find the document
    console.log(`\n📥 Pulling: ${docName}\n`);
    
    const query = `mimeType='application/vnd.google-apps.document' and name='${docName}' and trashed=false`;
    const response = await drive.files.list({
      q: query,
      fields: 'files(id, name)',
      spaces: 'drive',
    });
    
    if (response.data.files.length === 0) {
      throw new Error(`Document "${docName}" not found in Google Drive`);
    }
    
    const doc = response.data.files[0];
    console.log(`Found document: ${doc.name} (${doc.id})`);
    
    // Get content
    const content = await getDocumentContent(docs, doc.id);
    console.log(`Retrieved ${content.length} characters`);
    
    // Save to local file
    await fs.writeFile(localPath, content, 'utf-8');
    console.log(`✅ Saved to: ${localPath}\n`);
    
    return { docName, localPath, content };
    
  } catch (error) {
    console.error(`\n❌ Error pulling document:`, error.message);
    throw error;
  }
}

// CLI support
if (import.meta.url === `file://${process.argv[1]}`) {
  const deckId = process.argv[2];
  const docType = process.argv[3] || 'script'; // default to script
  
  if (!deckId) {
    console.error('Usage: node pull-google-doc.js <DECK_ID> [script|slides]');
    console.error('Example: node pull-google-doc.js FEN_STG script');
    process.exit(1);
  }
  
  pullDocument(deckId, docType)
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}

export { pullDocument };

