#!/usr/bin/env node

/**
 * Upload files to Google Drive
 * Uses the same authentication as google-docs-api.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { google } from 'googleapis';
import { authenticate } from '@google-cloud/local-auth';
import chalk from 'chalk';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.join(__dirname, '..');

// Scopes for Google Drive and YouTube APIs
const SCOPES = [
  'https://www.googleapis.com/auth/drive.file',
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/youtube.upload'
];

const TOKEN_PATH = path.join(projectRoot, 'token.json');
const CREDENTIALS_PATH = path.join(projectRoot, 'credentials.json');

/**
 * Load saved credentials if they exist
 */
async function loadSavedCredentialsIfExist() {
  try {
    const content = fs.readFileSync(TOKEN_PATH, 'utf-8');
    const credentials = JSON.parse(content);
    return google.auth.fromJSON(credentials);
  } catch (err) {
    return null;
  }
}

/**
 * Save credentials for future use
 */
async function saveCredentials(client) {
  const content = fs.readFileSync(CREDENTIALS_PATH, 'utf-8');
  const keys = JSON.parse(content);
  const key = keys.installed || keys.web;
  const payload = JSON.stringify({
    type: 'authorized_user',
    client_id: key.client_id,
    client_secret: key.client_secret,
    refresh_token: client.credentials.refresh_token,
  });
  fs.writeFileSync(TOKEN_PATH, payload);
}

/**
 * Authenticate with Google Drive
 */
async function authorize() {
  let client = await loadSavedCredentialsIfExist();
  if (client) {
    console.log(chalk.green('🔑 Using saved authentication token...'));
    return client;
  }
  
  console.log(chalk.yellow('🔑 No saved token found. Starting authentication...'));
  client = await authenticate({
    scopes: SCOPES,
    keyfilePath: CREDENTIALS_PATH,
  });
  
  if (client.credentials) {
    await saveCredentials(client);
    console.log(chalk.green('✓ Authentication successful and saved'));
  }
  
  return client;
}

/**
 * Find folder by name in parent folder
 */
async function findFolder(drive, folderName, parentFolderId = null) {
  let query = `name='${folderName}' and mimeType='application/vnd.google-apps.folder' and trashed=false`;
  
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
 * Create folder if it doesn't exist
 */
async function findOrCreateFolder(drive, folderName, parentFolderId = null) {
  // First try to find existing folder
  const existing = await findFolder(drive, folderName, parentFolderId);
  if (existing) {
    console.log(chalk.gray(`  Found existing folder: ${folderName}`));
    return existing.id;
  }
  
  // Create new folder
  console.log(chalk.gray(`  Creating folder: ${folderName}`));
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
  
  return folder.data.id;
}

/**
 * Upload file to Google Drive
 */
async function uploadFile(drive, filePath, fileName, folderId) {
  const fileMetadata = {
    name: fileName,
    parents: [folderId],
  };
  
  const media = {
    mimeType: getMimeType(fileName),
    body: fs.createReadStream(filePath),
  };
  
  console.log(chalk.gray(`  Uploading: ${fileName}...`));
  
  const file = await drive.files.create({
    requestBody: fileMetadata,
    media: media,
    fields: 'id, name, webViewLink, size',
  });
  
  return file.data;
}

/**
 * Get MIME type based on file extension
 */
function getMimeType(filename) {
  const ext = path.extname(filename).toLowerCase();
  const mimeTypes = {
    '.pdf': 'application/pdf',
    '.mp4': 'video/mp4',
    '.mp3': 'audio/mpeg',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
  };
  return mimeTypes[ext] || 'application/octet-stream';
}

/**
 * Main function
 */
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 2) {
    console.error(chalk.red('Error: Missing required arguments'));
    console.log(chalk.gray('\nUsage: node upload-to-drive.js <file-path> <folder-name> [base-folder] [root-folder]'));
    console.log(chalk.gray('\nExamples:'));
    console.log(chalk.gray('  node upload-to-drive.js exports/FEN_STG_010.pdf FEN_STG'));
    console.log(chalk.gray('  node upload-to-drive.js exports/FEN_STG_010.pdf FEN_STG "Product Videos"'));
    console.log(chalk.gray('  node upload-to-drive.js exports/FEN_STG_010.pdf FEN_STG "Product Videos" "FirstEnroll || Videos"'));
    process.exit(1);
  }
  
  const filePath = args[0];
  const deckFolderName = args[1];
  const baseFolderName = args[2] || null;
  const rootFolderName = args[3] || null;
  
  // Resolve file path
  const fullPath = path.isAbsolute(filePath) 
    ? filePath 
    : path.join(projectRoot, filePath);
  
  if (!fs.existsSync(fullPath)) {
    console.error(chalk.red(`Error: File not found: ${fullPath}`));
    process.exit(1);
  }
  
  const fileName = path.basename(fullPath);
  const fileStats = fs.statSync(fullPath);
  const fileSizeMB = (fileStats.size / (1024 * 1024)).toFixed(2);
  
  console.log(chalk.bold.cyan('\n📤 Uploading to Google Drive'));
  console.log(chalk.gray('─'.repeat(60)));
  console.log(chalk.gray(`  File: ${fileName}`));
  console.log(chalk.gray(`  Size: ${fileSizeMB} MB`));
  
  // Build folder path display
  let folderPath = deckFolderName;
  if (baseFolderName) {
    folderPath = `${baseFolderName} → ${folderPath}`;
  }
  if (rootFolderName) {
    folderPath = `${rootFolderName} → ${folderPath}`;
  }
  console.log(chalk.gray(`  Path: ${folderPath}`));
  console.log();
  
  try {
    // Authenticate
    const auth = await authorize();
    const drive = google.drive({ version: 'v3', auth });
    
    // Build folder hierarchy from root to deck folder
    let currentFolderId = null;
    
    // Level 1: Root folder (e.g., "FirstEnroll || Videos")
    if (rootFolderName) {
      console.log(chalk.gray(`📁 Finding/creating root folder: ${rootFolderName}...`));
      currentFolderId = await findOrCreateFolder(drive, rootFolderName, null);
    }
    
    // Level 2: Base folder (e.g., "Product Videos")
    if (baseFolderName) {
      console.log(chalk.gray(`📁 Finding/creating base folder: ${baseFolderName}...`));
      currentFolderId = await findOrCreateFolder(drive, baseFolderName, currentFolderId);
    }
    
    // Level 3: Deck folder (e.g., "FEN_HMM")
    console.log(chalk.gray(`📁 Finding/creating deck folder: ${deckFolderName}...`));
    const deckFolderId = await findOrCreateFolder(drive, deckFolderName, currentFolderId);
    
    // Upload file to deck folder
    console.log(chalk.gray('📤 Uploading file...'));
    const uploadedFile = await uploadFile(drive, fullPath, fileName, deckFolderId);
    
    console.log(chalk.bold.green('\n✔ Upload successful!'));
    console.log(chalk.gray(`  File ID: ${uploadedFile.id}`));
    console.log(chalk.gray(`  View: ${uploadedFile.webViewLink}`));
    console.log(chalk.gray(`  Size: ${(uploadedFile.size / (1024 * 1024)).toFixed(2)} MB\n`));
    
    // Output JSON for agent
    console.log('--- UPLOAD_INFO_JSON ---');
    console.log(JSON.stringify({
      fileName: uploadedFile.name,
      fileId: uploadedFile.id,
      webViewLink: uploadedFile.webViewLink,
      size: uploadedFile.size,
      deckFolder: deckFolderName,
      baseFolder: baseFolderName,
      rootFolder: rootFolderName,
      fullPath: folderPath,
      status: 'success'
    }, null, 2));
    console.log('--- END_UPLOAD_INFO_JSON ---\n');
    
    process.exit(0);
  } catch (error) {
    console.error(chalk.red('\n✗ Upload failed:'), error.message);
    process.exit(1);
  }
}

main();

