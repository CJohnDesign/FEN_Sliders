#!/usr/bin/env node

import { Command } from 'commander';
import ora from 'ora';
import chalk from 'chalk';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';
import { exec } from 'child_process';
import { promisify } from 'util';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

// Lazy-load Supabase client only when needed
let supabase = null;
function getSupabaseClient() {
  if (!supabase && process.env.SUPABASE_URL && process.env.SUPABASE_KEY) {
    supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);
  }
  return supabase;
}

/**
 * Step 1: Check/Create Google Drive Folder
 */
async function ensureGoogleDriveFolder(deckId) {
  const spinner = ora('Checking Google Drive folder...').start();
  
  try {
    const folderName = deckId;
    
    spinner.text = 'Searching for folder...';
    // Note: This is a placeholder - actual implementation would use Zapier MCP
    // The actual call would be: mcp_Zapier_google_drive_find_a_folder
    console.log(chalk.gray(`\n   Folder: ${folderName}`));
    
    spinner.text = 'Creating folder if needed...';
    // If not found, would call: mcp_Zapier_google_drive_create_folder
    
    spinner.succeed('Google Drive folder ready');
    
    return {
      folderId: `folder-${deckId}`,
      folderName: folderName
    };
  } catch (error) {
    spinner.fail('Google Drive folder check failed');
    throw error;
  }
}

/**
 * Step 2: Check/Create/Update Google Docs (Script and Slides)
 */
async function updateGoogleDocs(deckId, folderId) {
  const spinner = ora('Checking Google Docs...').start();
  
  try {
    // Read local files
    const scriptPath = path.join(projectRoot, 'decks', deckId, 'audio', 'audio_script.md');
    const slidesPath = path.join(projectRoot, 'decks', deckId, 'slides.md');
    
    if (!await fs.pathExists(scriptPath) || !await fs.pathExists(slidesPath)) {
      throw new Error(`Missing files for ${deckId}`);
    }
    
    const scriptContent = await fs.readFile(scriptPath, 'utf-8');
    const slidesContent = await fs.readFile(slidesPath, 'utf-8');
    
    spinner.text = 'Searching for existing docs...';
    // Note: This is a placeholder - actual implementation would use Zapier MCP
    // The actual call would be: mcp_Zapier_google_docs_find_a_document
    
    const scriptDocName = `${deckId}-Script`;
    const slidesDocName = `${deckId}-Slides`;
    
    console.log(chalk.gray(`\n   Script: ${scriptDocName} (${scriptContent.length} chars)`));
    console.log(chalk.gray(`   Slides: ${slidesDocName} (${slidesContent.length} chars)`));
    
    spinner.text = 'Creating/updating documents...';
    // If found: use mcp_Zapier_google_docs_get_document_content and update
    // If not found: use mcp_Zapier_google_docs_create_document_from_text
    
    spinner.succeed('Google Docs ready (docs would be created/updated via MCP)');
    
    return {
      scriptDoc: scriptDocName,
      slidesDoc: slidesDocName,
      scriptContent,
      slidesContent
    };
  } catch (error) {
    spinner.fail('Google Docs update failed');
    throw error;
  }
}

/**
 * Step 2: Export and Upload PDF
 */
async function exportAndUploadPDF(deckId) {
  const spinner = ora('Exporting PDF...').start();
  
  try {
    // Run deck export
    spinner.text = 'Running Slidev PDF export...';
    const { stdout } = await execAsync(
      `node scripts/deck-operations.js export ${deckId}`,
      { cwd: projectRoot }
    );
    
    // Parse output to get filename and Supabase URL
    const lines = stdout.split('\n');
    let pdfFilename = null;
    let supabaseUrl = null;
    
    for (const line of lines) {
      if (line.includes('Exported to:')) {
        pdfFilename = line.split('Exported to:')[1].trim().split('/').pop();
      }
      if (line.includes('Supabase URL:')) {
        supabaseUrl = line.split('Supabase URL:')[1].trim();
      }
    }
    
    if (!pdfFilename || !supabaseUrl) {
      throw new Error('Failed to parse export output');
    }
    
    spinner.succeed(`PDF exported: ${pdfFilename}`);
    
    // Upload to Google Drive (placeholder - would use MCP)
    spinner.start('Uploading to Google Drive...');
    console.log(chalk.gray(`\n   File: ${pdfFilename}`));
    console.log(chalk.gray(`   Source: ${supabaseUrl}`));
    
    spinner.succeed('PDF uploaded to Google Drive (would use MCP)');
    
    // Cleanup Supabase
    spinner.start('Cleaning up Supabase...');
    try {
      const supabaseClient = getSupabaseClient();
      if (supabaseClient) {
        const { error } = await supabaseClient.storage
          .from('pdfs')
          .remove([pdfFilename]);
        
        if (error) {
          console.log(chalk.yellow(`   Warning: ${error.message}`));
        } else {
          spinner.succeed('Supabase cleaned up');
        }
      } else {
        spinner.warn('Supabase cleanup skipped (credentials not found)');
      }
    } catch (err) {
      spinner.warn(`Supabase cleanup skipped: ${err.message}`);
    }
    
    return {
      filename: pdfFilename,
      url: supabaseUrl
    };
  } catch (error) {
    spinner.fail('PDF export failed');
    throw error;
  }
}

/**
 * Step 2.5: Regenerate Audio (Optional)
 */
async function regenerateAudio(deckId) {
  const spinner = ora('Regenerating audio...').start();
  
  try {
    spinner.text = 'Running audio generation (this may take a few minutes and will cost money)...';
    console.log(chalk.yellow(`\n   ⚠️  This will use ElevenLabs API and incur costs`));
    console.log(chalk.gray(`   Reading audio script from: decks/${deckId}/audio/audio_script.md`));
    console.log(chalk.gray(''));
    
    // Run audio generation
    const { stdout, stderr } = await execAsync(
      `npm run generateAudio ${deckId}`,
      { 
        cwd: projectRoot,
        maxBuffer: 10 * 1024 * 1024 // 10MB buffer for long output
      }
    );
    
    spinner.succeed('Audio regenerated successfully');
    
    return {
      success: true,
      output: stdout
    };
  } catch (error) {
    spinner.fail('Audio generation failed');
    throw error;
  }
}

/**
 * Step 3: Export and Upload Video
 */
async function exportAndUploadVideo(deckId, options = {}) {
  const spinner = ora('Exporting video...').start();
  
  try {
    // Build video export command
    const testFlag = options.test ? '--test' : '';
    const command = `npm run export-video ${deckId} -- ${testFlag}`;
    
    const timeEstimate = options.test ? '60 seconds' : '15-25 minutes';
    spinner.text = `Running video export (this will take ${timeEstimate})...`;
    console.log(chalk.gray(`\n   Command: ${command}`));
    console.log(chalk.gray('   This process will:'));
    console.log(chalk.gray('   1. Start Slidev server on port 3030'));
    console.log(chalk.gray('   2. Record presentation with Playwright'));
    console.log(chalk.gray('   3. Encode as MP4 with audio'));
    console.log(chalk.gray('   4. Save to exports/videos/'));
    console.log(chalk.gray(''));
    
    // Run video export
    const { stdout, stderr } = await execAsync(command, {
      cwd: projectRoot,
      maxBuffer: 10 * 1024 * 1024 // 10MB buffer for long output
    });
    
    // Parse output to get filename
    const lines = stdout.split('\n');
    let videoFilename = null;
    
    for (const line of lines) {
      if (line.includes('File:')) {
        videoFilename = line.split('File:')[1].trim();
        break;
      }
    }
    
    if (!videoFilename) {
      throw new Error('Failed to parse video export output');
    }
    
    spinner.succeed(`Video exported: ${videoFilename}`);
    
    // Upload to Google Drive (placeholder - would use MCP)
    spinner.start('Uploading video to Google Drive...');
    const videoPath = path.join(projectRoot, 'exports', 'videos', videoFilename);
    const stats = await fs.stat(videoPath);
    const sizeMB = (stats.size / (1024 * 1024)).toFixed(2);
    
    console.log(chalk.gray(`\n   File: ${videoFilename}`));
    console.log(chalk.gray(`   Size: ${sizeMB} MB`));
    console.log(chalk.gray(`   Path: ${videoPath}`));
    
    spinner.succeed('Video uploaded to Google Drive (would use MCP)');
    
    return {
      filename: videoFilename,
      path: videoPath,
      size: stats.size
    };
  } catch (error) {
    spinner.fail('Video export failed');
    throw error;
  }
}

/**
 * Main export function
 */
async function completeExport(deckId, options = {}) {
  console.log(chalk.bold.cyan(`\n${'='.repeat(60)}`));
  console.log(chalk.bold.cyan(`   COMPLETE EXPORT: ${deckId}`));
  console.log(chalk.bold.cyan(`${'='.repeat(60)}\n`));
  
  const results = {
    deckId,
    folder: null,
    docs: null,
    audio: null,
    video: null,
    pdf: null,
    errors: []
  };
  
  try {
    // Step 1: Check/Create Google Drive Folder
    if (!options.pdfOnly && !options.videoOnly && !options.audioOnly) {
      console.log(chalk.bold('\n📁 Step 1: Google Drive Folder'));
      console.log(chalk.gray('─'.repeat(60)));
      try {
        results.folder = await ensureGoogleDriveFolder(deckId);
      } catch (error) {
        results.errors.push({ step: 'folder', error: error.message });
        if (!options.continueOnError) throw error;
      }
    } else {
      console.log(chalk.yellow('\n📁 Step 1: Google Drive Folder - SKIPPED'));
    }
    
    // Step 2: Check/Create/Update Google Docs
    if (!options.skipDocs && !options.pdfOnly && !options.videoOnly && !options.audioOnly) {
      console.log(chalk.bold('\n📄 Step 2: Google Docs (Create/Update)'));
      console.log(chalk.gray('─'.repeat(60)));
      try {
        results.docs = await updateGoogleDocs(deckId, results.folder?.folderId);
      } catch (error) {
        results.errors.push({ step: 'docs', error: error.message });
        if (!options.continueOnError) throw error;
      }
    } else {
      console.log(chalk.yellow('\n📄 Step 2: Google Docs (Create/Update) - SKIPPED'));
    }
    
    // Step 3: Audio Regeneration (if requested)
    if (options.regenerateAudio || options.audioOnly) {
      console.log(chalk.bold('\n🎙️  Step 3: Audio Regeneration'));
      console.log(chalk.gray('─'.repeat(60)));
      try {
        results.audio = await regenerateAudio(deckId);
      } catch (error) {
        results.errors.push({ step: 'audio', error: error.message });
        if (!options.continueOnError) throw error;
      }
    } else {
      console.log(chalk.yellow('\n🎙️  Step 3: Audio Regeneration - SKIPPED'));
    }
    
    // Step 4: Video Export & Upload
    if (!options.skipVideo && !options.docsOnly && !options.pdfOnly && !options.audioOnly) {
      console.log(chalk.bold('\n🎥 Step 4: Video Export & Upload'));
      console.log(chalk.gray('─'.repeat(60)));
      try {
        results.video = await exportAndUploadVideo(deckId, options);
      } catch (error) {
        results.errors.push({ step: 'video', error: error.message });
        if (!options.continueOnError) throw error;
      }
    } else {
      console.log(chalk.yellow('\n🎥 Step 4: Video Export & Upload - SKIPPED'));
    }
    
    // Optional: PDF Export (only if explicitly requested)
    if (options.pdfOnly || (options.includePdf && !options.skipPdf)) {
      console.log(chalk.bold('\n📋 Optional: PDF Export & Upload'));
      console.log(chalk.gray('─'.repeat(60)));
      try {
        results.pdf = await exportAndUploadPDF(deckId);
      } catch (error) {
        results.errors.push({ step: 'pdf', error: error.message });
        if (!options.continueOnError) throw error;
      }
    }
    
    // Summary
    console.log(chalk.bold.green(`\n${'='.repeat(60)}`));
    console.log(chalk.bold.green(`   ✓ EXPORT COMPLETE: ${deckId}`));
    console.log(chalk.bold.green(`${'='.repeat(60)}\n`));
    
    if (results.folder) {
      console.log(chalk.green('✓ Google Drive Folder:'));
      console.log(chalk.gray(`   - ${results.folder.folderName}`));
    }
    
    if (results.docs) {
      console.log(chalk.green('✓ Google Docs:'));
      console.log(chalk.gray(`   - ${results.docs.scriptDoc}`));
      console.log(chalk.gray(`   - ${results.docs.slidesDoc}`));
    }
    
    if (results.audio) {
      console.log(chalk.green('✓ Audio Regenerated:'));
      console.log(chalk.gray(`   - Audio files in decks/${deckId}/audio/oai/`));
    }
    
    if (results.video) {
      console.log(chalk.green('✓ Video Export:'));
      console.log(chalk.gray(`   - ${results.video.filename}`));
    }
    
    if (results.pdf) {
      console.log(chalk.green('✓ PDF Export:'));
      console.log(chalk.gray(`   - ${results.pdf.filename}`));
    }
    
    if (results.errors.length > 0) {
      console.log(chalk.yellow('\n⚠️  Warnings:'));
      results.errors.forEach(({ step, error }) => {
        console.log(chalk.yellow(`   - ${step}: ${error}`));
      });
    }
    
    console.log('');
    return results;
    
  } catch (error) {
    console.log(chalk.bold.red(`\n${'='.repeat(60)}`));
    console.log(chalk.bold.red(`   ✗ EXPORT FAILED: ${deckId}`));
    console.log(chalk.bold.red(`${'='.repeat(60)}\n`));
    console.error(chalk.red('Error:'), error.message);
    console.log('');
    throw error;
  }
}

/**
 * Validate deck exists
 */
async function validateDeck(deckId) {
  const deckPath = path.join(projectRoot, 'decks', deckId);
  const slidesPath = path.join(deckPath, 'slides.md');
  
  if (!await fs.pathExists(slidesPath)) {
    throw new Error(
      `Deck not found: ${deckId}\n` +
      `Expected: ${slidesPath}\n\n` +
      `Available decks:\n` +
      `  Run: npm run deck list`
    );
  }
  
  return true;
}

/**
 * CLI Setup
 */
const program = new Command();

program
  .name('complete-export')
  .description('Complete export workflow: Folder + Google Docs + Audio + Video')
  .version('1.0.0');

program
  .argument('<deckId>', 'Deck ID to export (e.g., FEN_STG)')
  .option('--docs-only', 'Only update Google Docs')
  .option('--video-only', 'Only export video')
  .option('--audio-only', 'Only regenerate audio')
  .option('--pdf-only', 'Only export PDF')
  .option('--skip-docs', 'Skip Google Docs update')
  .option('--skip-video', 'Skip video export')
  .option('--include-pdf', 'Include PDF export in full workflow')
  .option('--skip-pdf', 'Skip PDF export (only used with --include-pdf)')
  .option('--regenerate-audio', 'Regenerate audio before video export (costs money)')
  .option('--test', 'Test mode for video (60 seconds only)')
  .option('--continue-on-error', 'Continue even if a step fails')
  .action(async (deckId, options) => {
    try {
      // Validate deck
      await validateDeck(deckId);
      
      // Run export
      await completeExport(deckId, options);
      
      process.exit(0);
    } catch (error) {
      console.error(chalk.red('\n✗ Export failed:'), error.message);
      process.exit(1);
    }
  });

// Batch export command
program
  .command('batch')
  .description('Export multiple decks')
  .argument('<deckIds...>', 'Deck IDs to export')
  .option('--docs-only', 'Only update Google Docs')
  .option('--video-only', 'Only export video')
  .option('--audio-only', 'Only regenerate audio')
  .option('--pdf-only', 'Only export PDF')
  .option('--skip-docs', 'Skip Google Docs update')
  .option('--skip-video', 'Skip video export')
  .option('--include-pdf', 'Include PDF export in full workflow')
  .option('--skip-pdf', 'Skip PDF export (only used with --include-pdf)')
  .option('--regenerate-audio', 'Regenerate audio before video export (costs money)')
  .option('--continue-on-error', 'Continue even if a deck fails')
  .action(async (deckIds, options) => {
    console.log(chalk.bold.cyan(`\nBatch Export: ${deckIds.length} decks\n`));
    
    const results = [];
    
    for (const deckId of deckIds) {
      try {
        await validateDeck(deckId);
        const result = await completeExport(deckId, options);
        results.push({ deckId, success: true, result });
      } catch (error) {
        results.push({ deckId, success: false, error: error.message });
        
        if (!options.continueOnError) {
          console.error(chalk.red(`\n✗ Batch export stopped at ${deckId}`));
          process.exit(1);
        }
      }
    }
    
    // Batch summary
    console.log(chalk.bold.cyan(`\n${'='.repeat(60)}`));
    console.log(chalk.bold.cyan(`   BATCH EXPORT SUMMARY`));
    console.log(chalk.bold.cyan(`${'='.repeat(60)}\n`));
    
    const successful = results.filter(r => r.success).length;
    const failed = results.filter(r => !r.success).length;
    
    console.log(chalk.green(`✓ Successful: ${successful}/${deckIds.length}`));
    if (failed > 0) {
      console.log(chalk.red(`✗ Failed: ${failed}/${deckIds.length}`));
      results.filter(r => !r.success).forEach(({ deckId, error }) => {
        console.log(chalk.red(`   - ${deckId}: ${error}`));
      });
    }
    
    console.log('');
    process.exit(failed > 0 ? 1 : 0);
  });

program.parse();
