#!/usr/bin/env node
/**
 * Full Export Script
 * Handles: PDF Export -> Google Drive Upload -> Supabase Cleanup
 */

import { spawn } from 'child_process';
import { createClient } from '@supabase/supabase-js';
import config from './youtube.config.js';

// Google Drive folder mapping
const FOLDER_IDS = {
  'FEN_STG': '1pomFooq5uIjdki-DQyv5_ub5ysuDfg-9',
  'FEN_HMM': 'LOOKUP_NEEDED',
  'FEN_HMP': 'LOOKUP_NEEDED',
  'FEN_GDC': 'LOOKUP_NEEDED'
};

const log = (msg) => console.log(`\n${msg}`);
const success = (msg) => console.log(`✅ ${msg}`);
const error = (msg) => console.error(`❌ ${msg}`);
const info = (msg) => console.log(`ℹ️  ${msg}`);

async function runExport(deckId) {
  log(`${'='.repeat(60)}`);
  log(`📄 EXPORTING PDF: ${deckId}`);
  log(`${'='.repeat(60)}`);
  
  return new Promise((resolve, reject) => {
    const exportProcess = spawn('npm', ['run', 'deck', 'export', deckId], {
      stdio: 'inherit',
      shell: true
    });

    let capturedOutput = '';
    
    exportProcess.on('close', (code) => {
      if (code === 0) {
        success('PDF Export completed');
        resolve();
      } else {
        error(`Export failed with code ${code}`);
        reject(new Error(`Export failed with code ${code}`));
      }
    });

    exportProcess.on('error', (err) => {
      error(`Export process error: ${err.message}`);
      reject(err);
    });
  });
}

async function getLatestPdfInfo(deckId) {
  log('🔍 Getting latest PDF info...');
  
  // Read the exports directory to find the latest version
  const { readdirSync } = await import('fs');
  const { join } = await import('path');
  
  const exportsDir = join(process.cwd(), 'exports');
  const files = readdirSync(exportsDir);
  
  // Find all PDFs for this deck
  const deckPdfs = files.filter(f => f.startsWith(deckId) && f.endsWith('.pdf'));
  
  if (deckPdfs.length === 0) {
    throw new Error(`No PDFs found for ${deckId}`);
  }
  
  // Sort to get the latest version
  deckPdfs.sort();
  const latestPdf = deckPdfs[deckPdfs.length - 1];
  const versionNumber = latestPdf.match(/_(\d+)\.pdf$/)[1];
  
  const filename = `${deckId}_${versionNumber.padStart(3, '0')}.pdf`;
  const supabaseUrl = `https://wzldwfbsadmnhqofifco.supabase.co/storage/v1/object/public/pdfs/${filename}`;
  
  info(`Latest PDF: ${filename}`);
  info(`Supabase URL: ${supabaseUrl}`);
  
  return {
    filename,
    supabaseUrl,
    baseFilename: filename.replace('.pdf', '')
  };
}

async function displayUploadInfo(deckId, pdfInfo) {
  const folderId = FOLDER_IDS[deckId];
  
  log(`${'='.repeat(60)}`);
  log(`📤 READY FOR GOOGLE DRIVE UPLOAD`);
  log(`${'='.repeat(60)}`);
  log(`Deck: ${deckId}`);
  log(`PDF File: ${pdfInfo.filename}`);
  log(`Supabase URL: ${pdfInfo.supabaseUrl}`);
  log(`Folder ID: ${folderId}`);
  log(`Base Filename (for upload): ${pdfInfo.baseFilename}`);
  log(`${'='.repeat(60)}`);
  
  // Return structured data
  return {
    deckId,
    filename: pdfInfo.filename,
    baseFilename: pdfInfo.baseFilename,
    supabaseUrl: pdfInfo.supabaseUrl,
    folderId: folderId !== 'LOOKUP_NEEDED' ? folderId : null,
    needsFolderLookup: folderId === 'LOOKUP_NEEDED'
  };
}

async function cleanupSupabase(filename) {
  log('🧹 Cleaning up Supabase...');
  
  const supabase = createClient(config.supabase.url, config.supabase.anonKey);
  const { error } = await supabase.storage
    .from('pdfs')
    .remove([filename]);

  if (error) {
    error(`Cleanup failed: ${error.message}`);
    throw error;
  }
  
  success('Cleaned up temporary file from Supabase');
}

async function main() {
  const deckId = process.argv[2];
  
  if (!deckId) {
    error('Please provide a deck ID');
    console.log('Usage: node full-export.mjs FEN_STG');
    process.exit(1);
  }

  try {
    // Step 1: Export PDF
    await runExport(deckId);
    
    // Step 2: Get PDF info
    const pdfInfo = await getLatestPdfInfo(deckId);
    
    // Step 3: Display upload info (AI will handle the actual upload)
    const uploadInfo = await displayUploadInfo(deckId, pdfInfo);
    
    // Output JSON for AI to parse
    log('\n--- JSON OUTPUT START ---');
    console.log(JSON.stringify(uploadInfo, null, 2));
    log('--- JSON OUTPUT END ---\n');
    
    info('Export complete! Waiting for AI to handle Google Drive upload and cleanup...');
    
  } catch (err) {
    error(`Fatal error: ${err.message}`);
    console.error(err);
    process.exit(1);
  }
}

main();

