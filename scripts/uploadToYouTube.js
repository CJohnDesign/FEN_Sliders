#!/usr/bin/env node

/**
 * Upload videos to YouTube via Supabase Storage + Zapier MCP
 * 
 * Flow:
 * 1. Upload video to Supabase Storage (temp)
 * 2. Get public URL
 * 3. Upload to YouTube via MCP (uses URL)
 * 4. Delete from Supabase after success
 * 
 * Usage: node scripts/uploadToYouTube.js <videoPath> <title> [description]
 */

import fs from 'fs';
import path from 'path';
import { createClient } from '@supabase/supabase-js';
import { fileURLToPath } from 'url';
import chalk from 'chalk';
import config from './youtube.config.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Configuration
const SUPABASE_URL = config.supabase.url;
const SUPABASE_KEY = config.supabase.anonKey;
const SUPABASE_BUCKET = 'videos';

/**
 * Initialize Supabase client
 */
function initSupabase() {
  if (SUPABASE_KEY === 'YOUR_SUPABASE_ANON_KEY_HERE') {
    console.error(chalk.red('❌ Supabase not configured!'));
    console.error(`Update ${chalk.cyan('scripts/youtube.config.js')} with your Supabase anon key`);
    console.error(`Get it from: ${chalk.blue('https://supabase.com/dashboard/project/wzldwfbsadmnhqofifco/settings/api')}`);
    process.exit(1);
  }
  return createClient(SUPABASE_URL, SUPABASE_KEY);
}

/**
 * Upload file to Supabase Storage
 */
async function uploadToSupabase(supabase, videoPath) {
  const fileName = `temp-${Date.now()}-${path.basename(videoPath)}`;
  const fileBuffer = fs.readFileSync(videoPath);
  
  console.log(chalk.cyan('📤 Uploading to Supabase Storage...'));
  
  const { data, error } = await supabase.storage
    .from(SUPABASE_BUCKET)
    .upload(fileName, fileBuffer, {
      contentType: 'video/mp4',
      cacheControl: '3600',
      upsert: false
    });

  if (error) {
    throw new Error(`Supabase upload failed: ${error.message}`);
  }

  // Get public URL
  const { data: { publicUrl } } = supabase.storage
    .from(SUPABASE_BUCKET)
    .getPublicUrl(fileName);

  console.log(chalk.green('✅ Uploaded to Supabase'));
  console.log(chalk.gray(`   URL: ${publicUrl}`));
  
  return { fileName, publicUrl };
}

/**
 * Delete file from Supabase Storage
 */
async function deleteFromSupabase(supabase, fileName) {
  console.log(chalk.cyan('🗑️  Deleting from Supabase...'));
  
  const { error } = await supabase.storage
    .from(SUPABASE_BUCKET)
    .remove([fileName]);

  if (error) {
    console.error(chalk.yellow(`⚠️  Failed to delete: ${error.message}`));
  } else {
    console.log(chalk.green('✅ Cleaned up Supabase storage'));
  }
}

/**
 * Main
 */
async function main() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error(chalk.red('Usage: node uploadToYouTube.js <videoPath> <title> [description]'));
    console.error('');
    console.error('Examples:');
    console.error(chalk.gray('  npm run youtube-upload exports/videos/FEN_HMM_004.mp4 "Harmony Care Plan Overview"'));
    console.error(chalk.gray('  npm run youtube-upload video.mp4 "My Video" "This is the description"'));
    process.exit(1);
  }

  const [videoPath, title, description = ''] = args;

  // Check if video exists
  if (!fs.existsSync(videoPath)) {
    console.error(chalk.red(`❌ Video file not found: ${videoPath}`));
    process.exit(1);
  }

  let supabaseFileName = null;
  const supabase = initSupabase();

  try {
    // Step 1: Upload to Supabase
    const { fileName, publicUrl } = await uploadToSupabase(supabase, videoPath);
    supabaseFileName = fileName;

    // Step 2: Display instructions for YouTube upload
    console.log('');
    console.log(chalk.yellow('══════════════════════════════════════════════════'));
    console.log(chalk.yellow('  📺 READY TO UPLOAD TO YOUTUBE'));
    console.log(chalk.yellow('══════════════════════════════════════════════════'));
    console.log('');
    console.log(chalk.white('Use the Zapier YouTube MCP with these details:'));
    console.log('');
    console.log(chalk.cyan('  Video URL:'), chalk.white(publicUrl));
    console.log(chalk.cyan('  Title:'), chalk.white(title));
    console.log(chalk.cyan('  Description:'), chalk.white(description || '(none)'));
    console.log(chalk.cyan('  Privacy:'), chalk.white('unlisted'));
    console.log(chalk.cyan('  Made for Kids:'), chalk.white('false'));
    console.log('');
    console.log(chalk.gray('After successful upload, press ENTER to clean up Supabase storage...'));
    console.log(chalk.gray('Or press Ctrl+C to keep the file in Supabase'));
    console.log('');

    // Wait for user confirmation
    await new Promise((resolve) => {
      process.stdin.once('data', () => resolve());
    });

    // Step 3: Clean up Supabase
    await deleteFromSupabase(supabase, fileName);
    
    console.log('');
    console.log(chalk.green('✅ Complete!'));

  } catch (error) {
    console.error(chalk.red('❌ Error:', error.message));
    
    // Ask if user wants to clean up
    if (supabaseFileName) {
      console.log('');
      console.log(chalk.yellow('Press ENTER to delete from Supabase, or Ctrl+C to keep it...'));
      await new Promise((resolve) => {
        process.stdin.once('data', async () => {
          await deleteFromSupabase(supabase, supabaseFileName);
          resolve();
        });
      });
    }
    
    process.exit(1);
  }
}

main();
