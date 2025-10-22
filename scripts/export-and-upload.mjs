#!/usr/bin/env node
import { spawn, exec } from 'child_process';
import { promisify } from 'util';
import { createClient } from '@supabase/supabase-js';
import config from './youtube.config.js';
import fs from 'fs';
import path from 'path';

const execPromise = promisify(exec);

// Color output helpers
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m'
};

const log = (msg, color = colors.reset) => console.log(`${color}${msg}${colors.reset}`);

// Configuration for Google Drive folders
const GOOGLE_DRIVE_CONFIG = {
  FEN_STG: '1pomFooq5uIjdki-DQyv5_ub5ysuDfg-9',
  FEN_HMM: null, // Will be looked up
  FEN_HMP: null, // Will be looked up
  FEN_GDC: null  // Will be looked up
};

async function startDevServer(deckId) {
  log(`\n🚀 Starting dev server for ${deckId}...`, colors.blue);
  
  return new Promise((resolve, reject) => {
    const serverProcess = spawn('npm', ['run', 'deck', 'dev', deckId], {
      stdio: 'pipe',
      detached: false
    });

    let started = false;

    serverProcess.stdout.on('data', (data) => {
      const output = data.toString();
      if (output.includes('ready in') || output.includes('Local:') || output.includes('http://localhost')) {
        if (!started) {
          started = true;
          log('✅ Dev server started', colors.green);
          // Wait 2 more seconds to ensure everything is loaded
          setTimeout(() => resolve(serverProcess), 2000);
        }
      }
    });

    serverProcess.stderr.on('data', (data) => {
      // Ignore punycode deprecation warnings
      if (!data.toString().includes('punycode')) {
        console.error(data.toString());
      }
    });

    serverProcess.on('error', reject);

    // Timeout after 30 seconds
    setTimeout(() => {
      if (!started) {
        reject(new Error('Server failed to start within 30 seconds'));
      }
    }, 30000);
  });
}

async function exportPDF(deckId) {
  log(`\n📄 Exporting PDF for ${deckId}...`, colors.blue);
  
  return new Promise((resolve, reject) => {
    const exportProcess = spawn('npm', ['run', 'deck', 'export', deckId], {
      stdio: 'pipe'
    });

    let output = '';
    let supabaseUrl = null;

    exportProcess.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      process.stdout.write(text);

      // Extract Supabase URL
      const urlMatch = text.match(/https:\/\/wzldwfbsadmnhqofifco\.supabase\.co\/storage\/v1\/object\/public\/pdfs\/([^\s]+)/);
      if (urlMatch) {
        supabaseUrl = urlMatch[0];
      }
    });

    exportProcess.stderr.on('data', (data) => {
      const text = data.toString();
      // Ignore punycode deprecation warnings
      if (!text.includes('punycode') && !text.includes('DEP0040')) {
        process.stderr.write(text);
      }
    });

    exportProcess.on('close', (code) => {
      if (code === 0 && supabaseUrl) {
        const filename = supabaseUrl.split('/').pop();
        log(`✅ PDF exported: ${filename}`, colors.green);
        resolve({ supabaseUrl, filename });
      } else {
        reject(new Error(`Export failed with code ${code}`));
      }
    });
  });
}

async function findOrCreateGoogleDriveFolder(deckId) {
  log(`\n📁 Finding Google Drive folder for ${deckId}...`, colors.blue);
  
  // Check if we already have the folder ID
  if (GOOGLE_DRIVE_CONFIG[deckId]) {
    log(`✅ Using cached folder ID`, colors.green);
    return GOOGLE_DRIVE_CONFIG[deckId];
  }

  // This would need the Zapier MCP integration
  // For now, return null and we'll handle it separately
  log(`⚠️  Folder ID not configured for ${deckId}`, colors.yellow);
  return null;
}

async function uploadToGoogleDrive(supabaseUrl, filename, folderId) {
  log(`\n☁️  Uploading to Google Drive...`, colors.blue);
  
  // This needs to be handled by the AI assistant with Zapier MCP
  // Return the info needed for upload
  const baseFilename = filename.replace('.pdf', '');
  
  return {
    supabaseUrl,
    filename: baseFilename,
    folderId,
    ready: true
  };
}

async function cleanupSupabase(filename) {
  log(`\n🧹 Cleaning up Supabase...`, colors.blue);
  
  const supabase = createClient(config.supabase.url, config.supabase.anonKey);
  const { error } = await supabase.storage
    .from('pdfs')
    .remove([filename]);

  if (error) {
    log(`❌ Cleanup failed: ${error.message}`, colors.red);
    throw error;
  } else {
    log('✅ Cleaned up temporary file from Supabase', colors.green);
  }
}

async function stopDevServer(serverProcess) {
  log(`\n🛑 Stopping dev server...`, colors.blue);
  
  return new Promise((resolve) => {
    if (serverProcess && !serverProcess.killed) {
      serverProcess.kill('SIGTERM');
      
      // Force kill after 3 seconds if still running
      setTimeout(() => {
        if (!serverProcess.killed) {
          serverProcess.kill('SIGKILL');
        }
        resolve();
      }, 3000);
    } else {
      resolve();
    }
  });
}

async function exportDeck(deckId) {
  let serverProcess = null;
  
  try {
    log(`\n${'='.repeat(60)}`, colors.cyan);
    log(`  EXPORTING ${deckId}`, colors.cyan);
    log(`${'='.repeat(60)}`, colors.cyan);

    // Start dev server
    serverProcess = await startDevServer(deckId);

    // Export PDF (this will use the running server)
    const { supabaseUrl, filename } = await exportPDF(deckId);

    // Stop the dev server
    await stopDevServer(serverProcess);
    serverProcess = null;

    // Find Google Drive folder
    const folderId = await findOrCreateGoogleDriveFolder(deckId);

    // Prepare upload info
    const uploadInfo = await uploadToGoogleDrive(supabaseUrl, filename, folderId);

    log(`\n${'='.repeat(60)}`, colors.cyan);
    log(`  ✅ EXPORT COMPLETE FOR ${deckId}`, colors.green);
    log(`${'='.repeat(60)}`, colors.cyan);
    
    return {
      deckId,
      filename,
      supabaseUrl,
      folderId,
      uploadInfo,
      success: true
    };

  } catch (error) {
    log(`\n❌ Error exporting ${deckId}: ${error.message}`, colors.red);
    
    // Make sure to stop server on error
    if (serverProcess) {
      await stopDevServer(serverProcess);
    }
    
    return {
      deckId,
      success: false,
      error: error.message
    };
  }
}

async function main() {
  const deckId = process.argv[2];
  
  if (!deckId) {
    log('❌ Please provide a deck ID', colors.red);
    log('Usage: node export-and-upload.mjs FEN_STG', colors.yellow);
    process.exit(1);
  }

  log(`\n🎯 Starting automated export for ${deckId}`, colors.cyan);
  
  const result = await exportDeck(deckId);
  
  if (result.success) {
    log(`\n📤 Ready for Google Drive upload:`, colors.cyan);
    log(`   Supabase URL: ${result.supabaseUrl}`, colors.blue);
    log(`   Filename: ${result.filename}`, colors.blue);
    log(`   Folder ID: ${result.folderId || 'To be determined'}`, colors.blue);
    
    // Return the info as JSON for the AI to process
    console.log('\n--- UPLOAD INFO JSON ---');
    console.log(JSON.stringify(result, null, 2));
    console.log('--- END UPLOAD INFO ---');
  } else {
    log(`\n❌ Export failed for ${deckId}`, colors.red);
    process.exit(1);
  }
}

main().catch((error) => {
  log(`\n❌ Fatal error: ${error.message}`, colors.red);
  console.error(error);
  process.exit(1);
});

